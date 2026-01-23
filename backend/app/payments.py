# app/payments.py
import os
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import stripe
from datetime import datetime, timedelta

from .database import SessionLocal
from .dependencies import get_db
from . import crud

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")  # Set in your env

class CreateCheckoutRequest(BaseModel):
    plan: str  # e.g., "pro_monthly" or "pro_yearly"
    user_email: str  # Pass the user's email for tracking

# Simple plan-to-price mapping (use Stripe Price IDs in production)
PLAN_PRICE_MAP = {
    "pro_monthly": {
        "name": "DeepVerify Pro (Monthly)",
        "amount": 1900,    # cents
        "currency": "usd",
    },
    "pro_yearly": {
        "name": "DeepVerify Pro (Yearly)",
        "amount": 17900,
        "currency": "usd",
    },
}

@router.post("/create-checkout-session")
async def create_checkout_session(payload: CreateCheckoutRequest, db: Session = Depends(get_db)):
    plan = payload.plan
    if plan not in PLAN_PRICE_MAP:
        raise HTTPException(status_code=400, detail="Unknown plan")

    plan_info = PLAN_PRICE_MAP[plan]

    try:
        # Create a Checkout Session:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": plan_info["currency"],
                        "product_data": {"name": plan_info["name"]},
                        "unit_amount": plan_info["amount"],
                    },
                    "quantity": 1,
                }
            ],
            success_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/indexloggedin?checkout=success",
            cancel_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/membership?checkout=cancel",
            customer_email=payload.user_email,
            metadata={"plan": plan, "user_email": payload.user_email},
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stripe-webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events to upgrade user membership after successful payment.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        if webhook_secret:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        else:
            # For development without webhook secret
            import json
            event = json.loads(payload)
            print("⚠️ WARNING: Webhook signature verification disabled (set STRIPE_WEBHOOK_SECRET)")

        # Handle the checkout.session.completed event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            
            # Get user email and plan from metadata
            user_email = session.get("customer_email") or session.get("metadata", {}).get("user_email")
            plan = session.get("metadata", {}).get("plan", "pro_monthly")
            
            if user_email:
                # Find user by email
                user = crud.get_user_by_email(db, user_email)
                
                if user:
                    # Calculate expiration date
                    if plan == "pro_yearly":
                        expiration_date = datetime.utcnow() + timedelta(days=365)
                    else:  # pro_monthly
                        expiration_date = datetime.utcnow() + timedelta(days=30)
                    
                    # Update user membership
                    user.membership_status = "Pro"
                    user.membership_expiry = expiration_date
                    db.commit()
                    
                    print(f"✅ Upgraded user {user_email} to Pro (expires: {expiration_date})")
                else:
                    print(f"❌ User not found: {user_email}")
            else:
                print("❌ No user email in session metadata")

        return {"status": "success"}

    except ValueError as e:
        # Invalid payload
        print(f"⚠️ Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"⚠️ Signature verification failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manual-upgrade")
async def manual_upgrade(user_email: str, plan: str = "pro_monthly", db: Session = Depends(get_db)):
    """
    Manual membership upgrade endpoint for testing/admin use.
    """
    user = crud.get_user_by_email(db, user_email)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate expiration date
    if plan == "pro_yearly":
        expiration_date = datetime.utcnow() + timedelta(days=365)
    else:  # pro_monthly
        expiration_date = datetime.utcnow() + timedelta(days=30)
    
    # Update user membership
    user.membership_status = "Pro"
    user.membership_expiry = expiration_date
    db.commit()
    
    return {
        "success": True,
        "message": f"User {user_email} upgraded to Pro",
        "expires": expiration_date.isoformat()
    }
