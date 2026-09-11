from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import jinja2

from database import get_db
from models import User
from deps import get_current_user
from payments import client, PLAN_IDS

router = APIRouter()

templates = Jinja2Templates(
    env=jinja2.Environment(
        loader=jinja2.FileSystemLoader("templates"),
        autoescape=True,
        cache_size=0,
    )
)


@router.get("/checkout/{plan}", response_class=HTMLResponse)
def checkout(plan: str, request: Request, user: User = Depends(get_current_user)):
    plan_id = PLAN_IDS.get(plan)
    if not plan_id:
        raise HTTPException(status_code=404, detail="Unknown plan")

    subscription = client.subscription.create({
        "plan_id": plan_id,
        "customer_notify": 1,
        "total_count": 12,
    })

    return templates.TemplateResponse(request, "checkout.html", {
        "key_id": client.auth[0],
        "subscription_id": subscription["id"],
        "plan": plan,
        "plan_label": "Basic" if plan == "basic" else "Pro",
        "user_name": user.full_name,
        "user_email": user.email,
    })


@router.post("/checkout/verify")
async def verify(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    data = await request.json()
    try:
        client.utility.verify_subscription_payment_signature({
            "razorpay_subscription_id": data.get("razorpay_subscription_id"),
            "razorpay_payment_id": data.get("razorpay_payment_id"),
            "razorpay_signature": data.get("razorpay_signature"),
        })
    except Exception:
        return {"success": False}

    user.plan = data.get("plan")
    user.razorpay_subscription_id = data.get("razorpay_subscription_id")
    db.commit()
    return {"success": True}