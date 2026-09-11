import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))

PLAN_IDS = {
    "basic": os.getenv("RAZORPAY_BASIC_PLAN_ID"),
    "pro": os.getenv("RAZORPAY_PRO_PLAN_ID"),
}