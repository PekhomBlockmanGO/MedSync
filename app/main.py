"""
Medication Management App — FastAPI Application.

Provides REST API endpoints for user management, medication tracking,
dose scheduling, and adherence logging.
"""

from dotenv import load_dotenv
load_dotenv()

import logging
import secrets
import string
import json
import io
from PIL import Image
from datetime import date, datetime, timedelta

import bcrypt
from fastapi import Depends, FastAPI, HTTPException, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import Base, engine, get_db
from app.models import (
    AdherenceLog,
    AdherenceStatus,
    Family,
    Medication,
    Schedule,
    User,
    UserRole,
)
from app.schemas import (
    AdherenceLogResponse,
    CaregiverAlertResponse,
    DashboardScheduleResponse,
    FamilyCreate,
    FamilyResponse,
    MedicationCreate,
    MedicationResponse,
    ScheduleCreate,
    ScheduleResponse,
    UserCreate,
    UserResponse,
)

# ---------------------------------------------------------------------------
# App & config
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# Create all tables on startup (good enough for dev; use Alembic in prod)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Medication Management API",
    description="Backend API for managing family medication inventories, "
                "dosing schedules, and adherence tracking.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")


# ---------------------------------------------------------------------------
# GET /  — Redirect to interactive API docs
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root():
    """Redirect the root URL to the Swagger UI docs page."""
    return RedirectResponse(url="/docs")


# ---------------------------------------------------------------------------
# Password hashing helpers  (using bcrypt directly — passlib is incompatible
# with bcrypt >= 4.1 on Python 3.13)
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain-text password against a stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# POST /families/  — Create a new family
# ---------------------------------------------------------------------------

@app.post(
    "/families/",
    response_model=FamilyResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Families"],
    summary="Create a new family group",
)
def create_family(family_in: FamilyCreate, db: Session = Depends(get_db)):
    """
    Create a new family group with an auto-generated unique join code.

    The join code can later be shared with other users so they can
    join the same family.
    """
    # Generate a unique 6-character alphanumeric join code
    alphabet = string.ascii_uppercase + string.digits
    while True:
        join_code = "".join(secrets.choice(alphabet) for _ in range(6))
        # Ensure no other family already has this code
        existing = db.execute(
            select(Family).where(Family.join_code == join_code)
        ).scalar_one_or_none()
        if existing is None:
            break

    db_family = Family(
        name=family_in.name,
        join_code=join_code,
    )
    db.add(db_family)
    db.commit()
    db.refresh(db_family)
    return db_family


# ---------------------------------------------------------------------------
# POST /users/  — Create a new user
# ---------------------------------------------------------------------------

@app.post(
    "/users/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
    summary="Register a new user",
)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.

    - Validates that the referenced family exists.
    - Hashes the plain-text password before persisting.
    - Returns the created user **without** the password hash.
    """
    # Verify the family exists
    family = db.get(Family, user_in.family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family with id {user_in.family_id} not found. "
                   f"Create a family first via POST /families/.",
        )

    # Check for duplicate email
    existing = db.execute(
        select(User).where(User.email == user_in.email)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A user with email '{user_in.email}' already exists.",
        )

    db_user = User(
        family_id=user_in.family_id,
        role=user_in.role,
        name=user_in.name,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# ---------------------------------------------------------------------------
# POST /users/login  — Authenticate a user
# ---------------------------------------------------------------------------

from pydantic import BaseModel

class UserLogin(BaseModel):
    email: str
    password: str

@app.post(
    "/users/login",
    response_model=UserResponse,
    tags=["Users"],
    summary="Login a user",
)
def login_user(login_in: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user.
    """
    # Demo bypass
    if login_in.email in ("pekky@test.com", "mom@test.com"):
        user = db.execute(
            select(User).where(User.email == login_in.email)
        ).scalar_one_or_none()
        
        if not user:
            # Create the demo user on the fly
            family = db.execute(select(Family).where(Family.name == "Demo Family")).scalar_one_or_none()
            if not family:
                family = Family(name="Demo Family", join_code="DEMO12")
                db.add(family)
                db.commit()
                db.refresh(family)
            
            user = User(
                family_id=family.id,
                role=UserRole.patient if login_in.email == "pekky@test.com" else UserRole.caregiver,
                name="Pekky" if login_in.email == "pekky@test.com" else "Mom",
                email=login_in.email,
                password_hash=hash_password(login_in.password or "demo")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    user = db.execute(
        select(User).where(User.email == login_in.email)
    ).scalar_one_or_none()
    
    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    return user


# ---------------------------------------------------------------------------
# POST /medications/  — Add a medication to a user's inventory
# ---------------------------------------------------------------------------

@app.post(
    "/medications/",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Medications"],
    summary="Add a new medication",
)
def create_medication(med_in: MedicationCreate, db: Session = Depends(get_db)):
    """
    Add a new medication entry for a specific user.

    Validates that the owning user exists before inserting.
    """
    # Verify the user exists
    user = db.get(User, med_in.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {med_in.user_id} not found.",
        )

    db_med = Medication(
        user_id=med_in.user_id,
        name=med_in.name,
        gtin=med_in.gtin,
        batch_number=med_in.batch_number,
        dosage_mg=med_in.dosage_mg,
        stock_quantity=med_in.stock_quantity,
        expiry_date=med_in.expiry_date,
    )
    db.add(db_med)
    db.commit()
    db.refresh(db_med)
    return db_med


# ---------------------------------------------------------------------------
# POST & GET /api/medications  — Global Stock Inventory
# ---------------------------------------------------------------------------
from pydantic import BaseModel
import os
import json

STOCK_DB_FILE = "stock_db.json"

class StockMedication(BaseModel):
    gtin: str | None = None
    name: str | None = None
    batch_number: str | None = None
    dosage: str | int | None = None
    quantity: str | int | None = None
    expiry_date: str | None = None

def load_stock():
    if os.path.exists(STOCK_DB_FILE):
        try:
            with open(STOCK_DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_stock(data):
    with open(STOCK_DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.post("/api/medications")
def add_medication_to_stock(med: StockMedication):
    stock = load_stock()
    stock.append(med.dict())
    save_stock(stock)
    return {"status": "success", "data": med}

@app.get("/api/medications")
def get_stock_medications():
    return load_stock()


# ---------------------------------------------------------------------------
# Calendar Tasks Endpoints
# ---------------------------------------------------------------------------
import datetime

tasks_db = []
task_counter = 1

class TaskModel(BaseModel):
    patient_name: str | None = None
    medicine_name: str
    dosage: int | str | None = None
    time_slots: list[str]
    repeat_days: list[str]

@app.post("/api/tasks")
def create_task(task: TaskModel):
    global task_counter
    new_task = task.dict()
    new_task["id"] = task_counter
    new_task["taken_dates"] = []
    task_counter += 1
    tasks_db.append(new_task)
    return {"status": "success", "data": new_task}

@app.get("/api/tasks")
def get_tasks():
    return tasks_db

@app.put("/api/tasks/memory/{task_id}/take")
def take_task_memory(task_id: int):
    today_str = datetime.date.today().isoformat()
    for task in tasks_db:
        if task["id"] == task_id:
            if today_str not in task["taken_dates"]:
                task["taken_dates"].append(today_str)
            return {"status": "success", "task_id": task_id, "taken_dates": task["taken_dates"]}
    raise HTTPException(status_code=404, detail="Task not found")


# ---------------------------------------------------------------------------
# POST /api/analyze-medication  — AI Medicine Scanner (OpenAI)
# ---------------------------------------------------------------------------

import os
from openai import OpenAI

_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.post("/api/analyze-medication")
async def analyze_medication(file: UploadFile = File(...)):
    """
    Process an uploaded image of a medicine package back label.
    Uses OpenAI GPT-4o-mini to extract structured medication details
    and returns JSON with keys: gtin, name, batch_number, dosage, expiry_date.
    """
    try:
        file_bytes = await file.read()
        base64_image = base64.b64encode(file_bytes).decode("utf-8")

        # Determine MIME type from upload, fallback to jpeg
        mime_type = file.content_type or "image/jpeg"
        image_url = f"data:{mime_type};base64,{base64_image}"

        system_prompt = (
            "You are a pharmaceutical data extraction assistant. "
            "You will be given an image of the back of a medicine package. "
            "Analyze the image and extract the following fields accurately:\n"
            "1) Product GTIN or barcode number\n"
            "2) Medicine Name\n"
            "3) Batch Number or Lot number\n"
            "4) Dosage in mg (just the numeric value as an integer)\n"
            "5) Expiry Date in DD-MM-YYYY format\n\n"
            "Return ONLY a single raw JSON object with exactly these keys: "
            "'gtin', 'name', 'batch_number', 'dosage', 'expiry_date'. "
            "If a field cannot be determined from the image, set its value to null. "
            "Do NOT wrap the output in markdown, code fences, backticks, or HTML."
        )

        response = _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                },
            ],
            max_tokens=512,
        )

        text = response.choices[0].message.content.strip()
        # Strip any accidental markdown fencing
        text = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)

        # Normalise keys to the exact contract the frontend expects
        return {
            "gtin": parsed.get("gtin"),
            "name": parsed.get("name"),
            "batch_number": parsed.get("batch_number"),
            "dosage": parsed.get("dosage"),
            "expiry_date": parsed.get("expiry_date"),
        }

    except json.JSONDecodeError as e:
        logger.error("Failed to parse OpenAI response as JSON: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail="AI returned an unparseable response. Please try again.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("analyze-medication error: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /schedules/  — Create a dosing schedule
# ---------------------------------------------------------------------------

@app.post(
    "/schedules/",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Schedules"],
    summary="Create a dosing schedule for a medication",
)
def create_schedule(sched_in: ScheduleCreate, db: Session = Depends(get_db)):
    """
    Create a new dosing schedule for a medication.

    - Validates that the referenced medication exists.
    - Automatically creates a **pending** adherence log entry for today
      so the dose immediately appears on the dashboard.
    """
    # Verify the medication exists
    medication = db.get(Medication, sched_in.medication_id)
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication with id {sched_in.medication_id} not found.",
        )

    db_schedule = Schedule(
        medication_id=sched_in.medication_id,
        time_slot=sched_in.time_slot,
        repeat_days=sched_in.repeat_days,
    )
    db.add(db_schedule)
    db.flush()  # assigns db_schedule.id before we reference it below

    # Auto-generate today's adherence log entry
    today = date.today()
    db_log = AdherenceLog(
        schedule_id=db_schedule.id,
        scheduled_date=today,
        status=AdherenceStatus.pending,
    )
    db.add(db_log)

    db.commit()
    db.refresh(db_schedule)
    return db_schedule


# ---------------------------------------------------------------------------
# GET /dashboard/{user_id}/schedule  — Today's schedule for a user
# ---------------------------------------------------------------------------

@app.get(
    "/dashboard/{user_id}/schedule",
    response_model=list[DashboardScheduleResponse],
    tags=["Dashboard"],
    summary="Get today's medication schedule with status",
)
def get_today_schedule(user_id: int, db: Session = Depends(get_db)):
    """
    Fetch all medication schedules for a user that are active today,
    along with each dose's current adherence status and medication details.

    A schedule matches if its `repeat_days` field contains the current
    abbreviated weekday name (e.g. "Mon") or the keyword "daily".
    """
    # Verify the user exists
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found.",
        )

    today = date.today()
    today_abbr = today.strftime("%a")  # e.g. "Mon", "Tue", …

    # Fetch schedules with their medication and today's adherence logs
    schedules = (
        db.execute(
            select(Schedule)
            .join(Medication, Schedule.medication_id == Medication.id)
            .options(
                joinedload(Schedule.medication),
                joinedload(Schedule.adherence_logs),
            )
            .where(Medication.user_id == user_id)
        )
        .unique()
        .scalars()
        .all()
    )

    # Filter to schedules that match today and build response
    results = []
    for s in schedules:
        if "daily" not in s.repeat_days.lower() and today_abbr not in s.repeat_days:
            continue

        # Find today's adherence log for this schedule (if any)
        todays_log = next(
            (log for log in s.adherence_logs if log.scheduled_date == today),
            None,
        )

        results.append({
            "schedule_id": s.id,
            "time_slot": s.time_slot,
            "repeat_days": s.repeat_days,
            "medication": s.medication,
            "adherence_status": todays_log.status if todays_log else AdherenceStatus.pending,
            "adherence_log_id": todays_log.id if todays_log else None,
        })

    return results


# ---------------------------------------------------------------------------
# PUT /adherence/{log_id}/take  — Mark a dose as taken
# ---------------------------------------------------------------------------

@app.put(
    "/api/tasks/{task_id}/take",
    tags=["Adherence"],
    summary="Mark a dose as taken (Alias)",
)
def mark_dose_taken_alias(task_id: int, db: Session = Depends(get_db)):
    return mark_dose_taken(task_id, db)

@app.put(
    "/adherence/{log_id}/take",
    tags=["Adherence"],
    summary="Mark a dose as taken",
)
def mark_dose_taken(log_id: int, db: Session = Depends(get_db)):
    """
    Mark an adherence log entry as **taken** and decrement the associated
    medication's stock quantity by 1.
    """
    # Load the adherence log with its schedule → medication eagerly
    log = (
        db.execute(
            select(AdherenceLog)
            .options(
                joinedload(AdherenceLog.schedule)
                .joinedload(Schedule.medication)
            )
            .where(AdherenceLog.id == log_id)
        )
        .unique()
        .scalar_one_or_none()
    )

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Adherence log with id {log_id} not found.",
        )

    if log.status == AdherenceStatus.taken:
        return {"status": "success", "task_id": log_id, "message": "Already marked as taken"}

    medication = log.schedule.medication

    if medication.stock_quantity <= 0:
        # Don't error out completely, just mark it taken and maybe log it.
        pass
    else:
        # Decrement stock
        medication.stock_quantity -= 1

    # Update the log
    log.status = AdherenceStatus.taken
    log.logged_at = datetime.utcnow()

    db.commit()
    db.refresh(log)
    return {"status": "success", "task_id": log_id}


# ---------------------------------------------------------------------------
# GET /alerts/check-missed  — Caregiver Alerts for missed doses
# ---------------------------------------------------------------------------

@app.get(
    "/alerts/check-missed",
    response_model=list[CaregiverAlertResponse],
    tags=["Alerts"],
    summary="Check for missed doses and alert caregivers",
)
def check_missed_doses(db: Session = Depends(get_db)):
    """
    Scan today's adherence logs for doses that are still **pending** but whose
    scheduled `time_slot` has already passed by more than 1 hour.

    For each missed dose the endpoint:
    1. Identifies the patient via Schedule → Medication → User.
    2. Finds every **caregiver** in the patient's family.
    3. Prints a prominent alert to the server terminal.
    4. Collects the alerts into a JSON response list.
    """
    now = datetime.now()
    today = now.date()
    cutoff_time = (now - timedelta(hours=1)).time()

    # Fetch today's pending logs with schedule, medication, and user loaded
    pending_logs = (
        db.execute(
            select(AdherenceLog)
            .options(
                joinedload(AdherenceLog.schedule)
                .joinedload(Schedule.medication)
                .joinedload(Medication.user)
            )
            .where(
                AdherenceLog.scheduled_date == today,
                AdherenceLog.status == AdherenceStatus.pending,
            )
        )
        .unique()
        .scalars()
        .all()
    )

    alerts: list[dict] = []

    for log in pending_logs:
        schedule = log.schedule

        # Only flag if the scheduled time is more than 1 hour in the past
        if schedule.time_slot >= cutoff_time:
            continue

        medication = schedule.medication
        patient = medication.user

        # Explicitly query caregivers in the same family
        caregivers = (
            db.execute(
                select(User).where(
                    User.family_id == patient.family_id,
                    User.role == UserRole.caregiver
                )
            )
            .scalars()
            .all()
        )

        for cg in caregivers:
            message = (
                f"ALERT: {cg.name}, {patient.name} missed their "
                f"{medication.name} at {schedule.time_slot.strftime('%H:%M')}!"
            )

            # Log a prominent alert to the server terminal
            logger.warning("\n" + "=" * 60)
            logger.warning("  [ALERT]  %s", message)
            logger.warning("=" * 60 + "\n")

            alerts.append({
                "caregiver_name": cg.name,
                "patient_name": patient.name,
                "medication_name": medication.name,
                "scheduled_time": schedule.time_slot,
                "message": message,
            })

    return alerts
