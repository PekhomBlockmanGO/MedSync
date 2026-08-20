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
from typing import Optional

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
    HealthDocument,
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
    FamilyMemberCreate,
    FamilyResponse,
    HealthDocumentCreate,
    HealthDocumentResponse,
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

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        loc = err.get("loc", [])
        field = loc[-1] if loc else "field"
        msg = err.get("msg", "")
        if field == "password" or "8 characters" in msg.lower():
            messages.append("Password must be at least 8 characters long.")
        else:
            messages.append(f"{field}: {msg}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": ", ".join(messages)},
    )


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
    # Verify the family exists (auto-create a default family if missing)
    family = db.get(Family, user_in.family_id)
    if not family:
        family = db.execute(select(Family)).scalars().first()
        if not family:
            alphabet = string.ascii_uppercase + string.digits
            join_code = "".join(secrets.choice(alphabet) for _ in range(6))
            family = Family(name=f"{user_in.name}'s Family", join_code=join_code)
            db.add(family)
            db.commit()
            db.refresh(family)

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
        family_id=family.id,
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
                items = json.load(f)
                changed = False
                for idx, item in enumerate(items, 1):
                    if "id" not in item:
                        item["id"] = idx
                        changed = True
                if changed:
                    save_stock(items)
                return items
        except Exception:
            pass
    return []

def save_stock(data):
    with open(STOCK_DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.post("/api/medications")
def add_medication_to_stock(med: StockMedication):
    stock = load_stock()
    med_dict = med.dict()
    next_id = max([int(m.get("id", 0)) for m in stock], default=0) + 1
    med_dict["id"] = next_id
    stock.append(med_dict)
    save_stock(stock)
    return {"status": "success", "data": med_dict}

@app.get("/api/medications")
def get_stock_medications():
    return load_stock()

@app.get("/api/medications/expiry-warnings")
def get_stock_expiry_warnings():
    stock = load_stock()
    now = date.today()
    soon_threshold = now + timedelta(days=30)
    warnings = []
    
    for item in stock:
        exp_str = item.get("expiry_date")
        if not exp_str:
            continue
        try:
            if "/" in exp_str:
                parts = exp_str.split("/")
                exp_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
            elif "-" in exp_str and len(exp_str.split("-")[0]) == 2:
                parts = exp_str.split("-")
                exp_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
            else:
                exp_date = date.fromisoformat(exp_str)
                
            if exp_date < now:
                warnings.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "expiry_date": exp_str,
                    "status": "expired",
                    "message": f"⚠️ Medicine Expired: {item.get('name')} expired on {exp_str}."
                })
            elif exp_date <= soon_threshold:
                warnings.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "expiry_date": exp_str,
                    "status": "expiring_soon",
                    "message": f"⚠️ Medicine Expiring Soon: {item.get('name')} expires on {exp_str}."
                })
        except Exception:
            pass
            
    return warnings

@app.delete("/api/medications/{index}")
def delete_stock_medication(index: int):
    stock = load_stock()
    if 0 <= index < len(stock):
        deleted = stock.pop(index)
        save_stock(stock)
        return {"status": "success", "deleted": deleted}
    raise HTTPException(status_code=404, detail="Medication index out of bounds")

class RemoveStockQty(BaseModel):
    remove_quantity: int = 1
    remove_all: bool = False

@app.post("/api/medications/{index}/remove")
def remove_stock_quantity(index: int, payload: RemoveStockQty):
    stock = load_stock()
    if 0 <= index < len(stock):
        med = stock[index]
        try:
            current_qty = int(med.get("quantity") or 1)
        except (ValueError, TypeError):
            current_qty = 1

        if payload.remove_all or payload.remove_quantity >= current_qty:
            deleted = stock.pop(index)
            save_stock(stock)
            return {"status": "success", "action": "deleted", "item": deleted}
        else:
            new_qty = current_qty - payload.remove_quantity
            med["quantity"] = new_qty
            save_stock(stock)
            return {"status": "success", "action": "updated", "remaining_quantity": new_qty, "item": med}

    raise HTTPException(status_code=404, detail="Medication index out of bounds")


# ---------------------------------------------------------------------------
# Calendar Tasks Endpoints
# ---------------------------------------------------------------------------

tasks_db = []
task_counter = 1

class TaskModel(BaseModel):
    stock_id: int | None = None
    patient_name: str | None = None
    medicine_name: str
    dosage: int | str | None = None
    time_slots: list[str]
    repeat_days: list[str]

@app.post("/api/tasks")
def create_task(task: TaskModel):
    global task_counter
    stock = load_stock()
    
    # Backend Validation: Verify medicine exists in Stock Inventory
    stock_item = None
    if task.stock_id is not None:
        stock_item = next((m for m in stock if m.get("id") == task.stock_id), None)
    
    if not stock_item and task.medicine_name:
        stock_item = next((m for m in stock if m.get("name", "").strip().lower() == task.medicine_name.strip().lower()), None)
        
    if not stock_item and len(stock) > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Medicine '{task.medicine_name}' does not exist in Stock Inventory. Please add it to Stock Inventory first."
        )

    new_task = task.dict()
    new_task["id"] = task_counter
    if stock_item:
        new_task["stock_id"] = stock_item.get("id")
        new_task["medicine_name"] = stock_item.get("name")
        if not new_task.get("dosage"):
            new_task["dosage"] = stock_item.get("dosage")
    new_task["taken_dates"] = []
    task_counter += 1
    tasks_db.append(new_task)
    return {"status": "success", "data": new_task}

@app.get("/api/tasks")
def get_tasks():
    return tasks_db

@app.put("/api/tasks/memory/{task_id}/take")
def take_task_memory(task_id: int):
    today_str = date.today().isoformat()
    for task in tasks_db:
        if task["id"] == task_id:
            if today_str not in task["taken_dates"]:
                task["taken_dates"].append(today_str)
                # Deduct 1 unit from Stock Inventory quantity when dose is taken!
                stock = load_stock()
                target_stock = None
                if task.get("stock_id"):
                    target_stock = next((m for m in stock if m.get("id") == task.get("stock_id")), None)
                if not target_stock and task.get("medicine_name"):
                    target_stock = next((m for m in stock if m.get("name", "").strip().lower() == task.get("medicine_name", "").strip().lower()), None)
                
                if target_stock:
                    try:
                        cur_qty = int(target_stock.get("quantity") or 0)
                        if cur_qty > 0:
                            target_stock["quantity"] = cur_qty - 1
                            save_stock(stock)
                    except (ValueError, TypeError):
                        pass

            return {"status": "success", "task_id": task_id, "taken_dates": task["taken_dates"]}
    raise HTTPException(status_code=404, detail="Task not found")


# ---------------------------------------------------------------------------
# POST /api/analyze-medication  — AI Medicine Scanner (OpenAI)
# ---------------------------------------------------------------------------

import os
from openai import OpenAI

def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set in environment.",
        )
    return OpenAI(api_key=api_key)

@app.post("/api/analyze-medication")
async def analyze_medication(file: UploadFile = File(...)):
    """
    Process an uploaded image of a medicine package back label.
    Uses OpenAI GPT-4o-mini to extract structured medication details
    and returns JSON with keys: gtin, name, batch_number, dosage, expiry_date.
    """
    client = _get_openai_client()
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

        response = client.chat.completions.create(
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
    if medication:
        if medication.stock_quantity > 0:
            medication.stock_quantity -= 1

        # Also decrement Stock Inventory (stock_db.json)
        stock = load_stock()
        target_stock = next((m for m in stock if m.get("name", "").strip().lower() == medication.name.strip().lower()), None)
        if target_stock:
            try:
                cur_qty = int(target_stock.get("quantity") or 0)
                if cur_qty > 0:
                    target_stock["quantity"] = cur_qty - 1
                    save_stock(stock)
            except (ValueError, TypeError):
                pass

    # Update the log
    log.status = AdherenceStatus.taken
    log.logged_at = datetime.now()

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


# ---------------------------------------------------------------------------
# GET & POST /families/{family_id}/members  — Family Member Management
# ---------------------------------------------------------------------------

@app.get(
    "/families/{family_id}/members",
    response_model=list[UserResponse],
    tags=["Families"],
    summary="Get all members of a family",
)
def get_family_members(family_id: int, db: Session = Depends(get_db)):
    """Fetch all individual member profiles in a family household."""
    family = db.get(Family, family_id)
    if not family:
        raise HTTPException(status_code=404, detail=f"Family {family_id} not found.")
    members = db.execute(
        select(User).where(User.family_id == family_id).order_by(User.id.asc())
    ).scalars().all()
    return members


@app.post(
    "/families/{family_id}/members",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Families"],
    summary="Add a new family member to household",
)
def add_family_member(family_id: int, member_in: FamilyMemberCreate, db: Session = Depends(get_db)):
    """Add a new individual profile (e.g. Father, Mother, Son) to the household."""
    family = db.get(Family, family_id)
    if not family:
        raise HTTPException(status_code=404, detail=f"Family {family_id} not found.")

    # Check for code uniqueness within family
    code = member_in.member_code.strip().upper()
    existing_code = db.execute(
        select(User).where(User.family_id == family_id, User.member_code == code)
    ).scalar_one_or_none()
    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Member code '{code}' is already used by {existing_code.name} in this household.",
        )

    dummy_email = f"member_{code.lower()}_{secrets.token_hex(4)}@household.local"

    db_user = User(
        family_id=family_id,
        role=member_in.role,
        name=member_in.name.strip(),
        designation=member_in.designation.strip(),
        member_code=code,
        email=dummy_email,
        password_hash=hash_password("member123"),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# ---------------------------------------------------------------------------
# GET /calendar/family/{family_id}  — Household Calendar Data
# ---------------------------------------------------------------------------

@app.get(
    "/calendar/family/{family_id}",
    tags=["Dashboard"],
    summary="Get all scheduled medications for family calendar display",
)
def get_family_calendar(family_id: int, db: Session = Depends(get_db)):
    """Retrieve scheduled doses across all family members for stacked calendar display."""
    users = db.execute(select(User).where(User.family_id == family_id)).scalars().all()
    user_ids = [u.id for u in users]
    user_map = {u.id: {"name": u.name, "designation": u.designation, "member_code": u.member_code} for u in users}

    if not user_ids:
        return []

    schedules = (
        db.execute(
            select(Schedule)
            .join(Medication, Schedule.medication_id == Medication.id)
            .options(
                joinedload(Schedule.medication),
                joinedload(Schedule.adherence_logs),
            )
            .where(Medication.user_id.in_(user_ids) | (Medication.family_id == family_id))
        )
        .unique()
        .scalars()
        .all()
    )

    results = []
    today = date.today()
    for s in schedules:
        user_id = s.medication.user_id
        member_info = user_map.get(user_id, {"name": "Household", "designation": "Shared", "member_code": "ALL"})

        todays_log = next(
            (log for log in s.adherence_logs if log.scheduled_date == today),
            None,
        )

        results.append({
            "schedule_id": s.id,
            "user_id": user_id,
            "member_name": member_info["name"],
            "member_designation": member_info["designation"],
            "member_code": member_info["member_code"],
            "time_slot": str(s.time_slot),
            "repeat_days": s.repeat_days,
            "medication_id": s.medication.id,
            "medication_name": s.medication.name,
            "dosage_mg": s.medication.dosage_mg,
            "stock_quantity": s.medication.stock_quantity,
            "adherence_status": todays_log.status if todays_log else AdherenceStatus.pending,
            "adherence_log_id": todays_log.id if todays_log else None,
        })

    return results


# ---------------------------------------------------------------------------
# GET & POST & DELETE /health-documents/  — Digital Medical Vault
# ---------------------------------------------------------------------------

@app.get(
    "/health-documents/family/{family_id}",
    response_model=list[HealthDocumentResponse],
    tags=["Health Documents"],
    summary="Get prescriptions and health reports for a family",
)
def get_health_documents(family_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Retrieve all digital medical records (prescriptions, reports) for household."""
    query = select(HealthDocument).where(HealthDocument.family_id == family_id)
    if user_id:
        query = query.where(HealthDocument.user_id == user_id)
    docs = db.execute(query.order_by(HealthDocument.upload_date.desc())).scalars().all()
    return docs


@app.post(
    "/health-documents/",
    response_model=HealthDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Health Documents"],
    summary="Upload a prescription or health report",
)
def create_health_document(doc_in: HealthDocumentCreate, db: Session = Depends(get_db)):
    """Store a digital medical report/prescription linked to a family member."""
    user = db.get(User, doc_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {doc_in.user_id} not found.")

    db_doc = HealthDocument(
        family_id=doc_in.family_id,
        user_id=doc_in.user_id,
        title=doc_in.title.strip(),
        document_type=doc_in.document_type.strip(),
        file_name=doc_in.file_name.strip(),
        mime_type=doc_in.mime_type.strip(),
        file_data=doc_in.file_data,
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc


@app.delete(
    "/health-documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Health Documents"],
    summary="Delete a health report or prescription",
)
def delete_health_document(doc_id: int, db: Session = Depends(get_db)):
    """Delete a stored medical document."""
    doc = db.get(HealthDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return None

