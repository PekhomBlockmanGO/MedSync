import os
import hmac
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from sqlalchemy.orm import Session
import razorpay

from app.database import get_db
from app.models import Family, User, Subscription, Payment
from app.schemas import CheckoutRequest, SubscriptionResponse, PaymentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["payments"])

def get_razorpay_client():
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        return None
    return razorpay.Client(auth=(key_id, key_secret))

# Constants for plan mapping
PLAN_MAPPING = {
    "family_monthly": {
        "id": os.getenv("RAZORPAY_FAMILY_MONTHLY_PLAN_ID"),
        "price": 149,
        "name": "MedSync Family (Monthly)"
    },
    "family_yearly": {
        "id": os.getenv("RAZORPAY_FAMILY_YEARLY_PLAN_ID"),
        "price": 1499,
        "name": "MedSync Family (Yearly)"
    },
    "care_monthly": {
        "id": os.getenv("RAZORPAY_CARE_MONTHLY_PLAN_ID"),
        "price": 299,
        "name": "MedSync Care+ (Monthly)"
    },
    "care_yearly": {
        "id": os.getenv("RAZORPAY_CARE_YEARLY_PLAN_ID"),
        "price": 2999,
        "name": "MedSync Care+ (Yearly)"
    }
}

@router.get("/subscription/plans")
def get_plans():
    """Return available plans and pricing."""
    return {
        "family": {
            "monthly": PLAN_MAPPING.get("family_monthly"),
            "yearly": PLAN_MAPPING.get("family_yearly")
        },
        "care": {
            "monthly": PLAN_MAPPING.get("care_monthly"),
            "yearly": PLAN_MAPPING.get("care_yearly")
        }
    }

@router.get("/subscription/{family_id}", response_model=SubscriptionResponse)
def get_subscription(family_id: int, db: Session = Depends(get_db)):
    """Get the current subscription for a household."""
    sub = db.query(Subscription).filter(Subscription.family_id == family_id).first()
    if not sub:
        # Return default free plan
        return SubscriptionResponse(
            id=0,
            family_id=family_id,
            user_id=0,
            plan="free",
            billing_cycle=None,
            status="active"
        )
    return sub

@router.post("/payment/create-checkout")
def create_checkout(req: CheckoutRequest, family_id: int, user_id: int, db: Session = Depends(get_db)):
    """Initialize a Razorpay Subscription for the given plan."""
    client = get_razorpay_client()
    if not client:
        raise HTTPException(status_code=500, detail="Razorpay not configured on server.")

    plan_key = f"{req.plan}_{req.billing_cycle}"
    plan_data = PLAN_MAPPING.get(plan_key)
    
    if not plan_data or not plan_data["id"]:
        raise HTTPException(status_code=400, detail="Invalid plan or plan not configured.")

    try:
        # Create subscription in Razorpay
        sub_options = {
            "plan_id": plan_data["id"],
            "total_count": 120, # E.g., 10 years
            "customer_notify": 1,
            "notes": {
                "family_id": str(family_id),
                "user_id": str(user_id),
                "plan": req.plan,
                "billing_cycle": req.billing_cycle
            }
        }
        razorpay_sub = client.subscription.create(sub_options)
        
        # We don't save to DB until payment succeeds (or we can save as 'created')
        return {
            "subscription_id": razorpay_sub["id"],
            "key": os.getenv("RAZORPAY_KEY_ID"),
            "amount": plan_data["price"] * 100, # mostly not used for sub UI, but good to have
            "currency": "INR",
            "name": "MedSync",
            "description": plan_data["name"]
        }
    except Exception as e:
        logger.error(f"Error creating checkout: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment/verify")
def verify_payment(
    razorpay_payment_id: str,
    razorpay_subscription_id: str,
    razorpay_signature: str,
    family_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Verify Razorpay signature and activate subscription."""
    client = get_razorpay_client()
    if not client:
        raise HTTPException(status_code=500, detail="Razorpay not configured.")

    try:
        # Verify the signature
        client.utility.verify_subscription_payment_signature({
            'razorpay_subscription_id': razorpay_subscription_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
        
        # Get subscription details from Razorpay to know what plan it is
        r_sub = client.subscription.fetch(razorpay_subscription_id)
        notes = r_sub.get("notes", {})
        plan = notes.get("plan", "family")
        billing_cycle = notes.get("billing_cycle", "monthly")
        
        # Update or create subscription in MedSync DB
        sub = db.query(Subscription).filter(Subscription.family_id == family_id).first()
        if not sub:
            sub = Subscription(
                family_id=family_id,
                user_id=user_id
            )
            db.add(sub)
            
        sub.plan = plan
        sub.billing_cycle = billing_cycle
        sub.status = "active"
        sub.razorpay_subscription_id = razorpay_subscription_id
        
        # In a real app we'd parse current_start and current_end from r_sub
        sub.current_period_start = datetime.now()
        sub.current_period_end = datetime.now() + (timedelta(days=365) if billing_cycle == 'yearly' else timedelta(days=30))
        sub.cancel_at_period_end = 0

        # Save payment record
        payment = Payment(
            family_id=family_id,
            user_id=user_id,
            subscription_id=sub.id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
            amount=PLAN_MAPPING[f"{plan}_{billing_cycle}"]["price"],
            currency="INR",
            status="paid",
            method="razorpay"
        )
        db.add(payment)
        
        db.commit()
        return {"status": "success", "message": "Subscription activated successfully"}
        
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except Exception as e:
        db.rollback()
        logger.error(f"Verification error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment/razorpay/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Razorpay webhooks for async state updates."""
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not webhook_secret:
        return {"status": "ignored", "reason": "No webhook secret configured"}
        
    payload = await request.body()
    signature = request.headers.get("x-razorpay-signature")
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
        
    client = get_razorpay_client()
    try:
        client.utility.verify_webhook_signature(payload.decode('utf-8'), signature, webhook_secret)
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
    data = json.loads(payload)
    event = data.get("event")
    
    # Very basic idempotent handling of 'subscription.charged' or 'subscription.cancelled'
    if event == "subscription.charged":
        sub_id = data['payload']['subscription']['entity']['id']
        pay_id = data['payload']['payment']['entity']['id']
        amount = data['payload']['payment']['entity']['amount'] / 100.0
        
        # Check idempotency
        existing_payment = db.query(Payment).filter(Payment.razorpay_payment_id == pay_id).first()
        if not existing_payment:
            sub = db.query(Subscription).filter(Subscription.razorpay_subscription_id == sub_id).first()
            if sub:
                new_payment = Payment(
                    family_id=sub.family_id,
                    user_id=sub.user_id,
                    subscription_id=sub.id,
                    razorpay_payment_id=pay_id,
                    amount=amount,
                    currency="INR",
                    status="paid",
                    method="webhook"
                )
                db.add(new_payment)
                sub.status = "active"
                db.commit()
                
    elif event == "subscription.cancelled":
        sub_id = data['payload']['subscription']['entity']['id']
        sub = db.query(Subscription).filter(Subscription.razorpay_subscription_id == sub_id).first()
        if sub:
            sub.status = "cancelled"
            sub.cancel_at_period_end = 1
            db.commit()

    return {"status": "ok"}

@router.post("/subscription/cancel")
def cancel_subscription(family_id: int, db: Session = Depends(get_db)):
    """Cancel a subscription at period end."""
    sub = db.query(Subscription).filter(Subscription.family_id == family_id).first()
    if not sub or sub.status != "active" or not sub.razorpay_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription to cancel.")
        
    client = get_razorpay_client()
    if client:
        try:
            # cancel_at_cycle_end=1
            client.subscription.cancel(sub.razorpay_subscription_id, {"cancel_at_cycle_end": 1})
        except Exception as e:
            logger.error(f"Failed to cancel at razorpay: {e}")
            
    sub.cancel_at_period_end = 1
    db.commit()
    return {"status": "success", "message": "Subscription will be cancelled at the end of the billing period."}

@router.get("/billing/history")
def get_billing_history(family_id: int, db: Session = Depends(get_db)):
    """Get payment history."""
    payments = db.query(Payment).filter(Payment.family_id == family_id).order_by(Payment.created_at.desc()).all()
    return payments
