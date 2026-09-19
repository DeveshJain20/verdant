import os
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, UploadFile, File, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import jinja2

from diagnosis import get_diagnosis
from database import get_db
from models import User
from deps import get_current_user

load_dotenv()

PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY")
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_API_KEY}"

FREE_SCAN_LIMIT = 3
BASIC_MONTHLY_LIMIT = 10

router = APIRouter()

templates = Jinja2Templates(
    env=jinja2.Environment(
        loader=jinja2.FileSystemLoader("templates"),
        autoescape=True,
        cache_size=0,
    )
)


def reset_if_new_month(user: User, db: Session):
    now = datetime.utcnow()
    if not user.monthly_reset_at or (now - user.monthly_reset_at) >= timedelta(days=30):
        user.monthly_scan_count = 0
        user.monthly_reset_at = now
        db.commit()


def get_scan_status(user: User, db: Session):
    if user.plan == "free":
        used = user.scan_count
        if used >= FREE_SCAN_LIMIT:
            return {"blocked": True, "reveal": None, "scans_left": 0}
        reveal = "full" if used == 0 else ("issues_only" if used == 1 else "name_only")
        return {"blocked": False, "reveal": reveal, "scans_left": FREE_SCAN_LIMIT - used}

    if user.plan == "basic":
        reset_if_new_month(user, db)
        if user.monthly_scan_count >= BASIC_MONTHLY_LIMIT:
            return {"blocked": True, "reveal": None, "scans_left": 0}
        return {"blocked": False, "reveal": "full", "scans_left": BASIC_MONTHLY_LIMIT - user.monthly_scan_count}

    return {"blocked": False, "reveal": "full", "scans_left": None}


@router.get("/scan", response_class=HTMLResponse)
def scan_form(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    status = get_scan_status(user, db)
    return templates.TemplateResponse(request, "scan.html", {"user": user, "scan_status": status})


@router.post("/scan", response_class=HTMLResponse)
async def scan_photo(
    request: Request,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    status = get_scan_status(user, db)

    if status["blocked"]:
        msg = (
            "You've used all 3 free scans. Upgrade to Basic or Pro for more."
            if user.plan == "free"
            else "You've used all 10 scans this month. Upgrade to Pro for unlimited scans."
        )
        return templates.TemplateResponse(request, "scan.html", {"user": user, "scan_status": status, "error": msg})

    if not PLANTNET_API_KEY:
        return templates.TemplateResponse(
            request, "scan.html", {"user": user, "scan_status": status, "error": "PlantNet API key is not configured."}
        )

    image_bytes = await photo.read()
    files = {"images": (photo.filename, image_bytes, photo.content_type)}
    data = {"organs": "leaf"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(PLANTNET_URL, files=files, data=data)
    except httpx.RequestError:
        return templates.TemplateResponse(
            request, "scan.html", {"user": user, "scan_status": status, "error": "Could not reach PlantNet. Please try again."}
        )

    if response.status_code != 200:
        return templates.TemplateResponse(
            request, "scan.html",
            {"user": user, "scan_status": status, "error": "We couldn't identify a plant in that photo — try a clear, well-lit shot of a leaf or flower."},
        )

    payload = response.json()
    raw_results = payload.get("results", [])[:5]

    results = []
    for r in raw_results:
        species = r.get("species", {})
        common_names = species.get("commonNames", [])
        results.append({
            "common_name": common_names[0] if common_names else species.get("scientificNameWithoutAuthor", "Unknown"),
            "scientific_name": species.get("scientificNameWithoutAuthor", ""),
            "confidence_pct": round(r.get("score", 0) * 100, 1),
        })

    if not results:
        return templates.TemplateResponse(
            request, "scan.html",
            {"user": user, "scan_status": status, "error": "We couldn't identify a plant in that photo — this scanner works best with a clear shot of a leaf or flower (not faces or objects 🙂)."},
        )

    top_match = results[0]
    reveal = status["reveal"]

    diagnosis = None
    if reveal in ("full", "issues_only"):
        diagnosis = get_diagnosis(top_match["common_name"], top_match["scientific_name"])

    if user.plan == "free":
        user.scan_count += 1
    elif user.plan == "basic":
        user.monthly_scan_count += 1
    db.commit()

    show_upgrade_popup = user.plan == "free" and reveal == "name_only"
    next_status = get_scan_status(user, db)

    return templates.TemplateResponse(
        request, "scan.html",
        {
            "user": user,
            "scan_status": next_status,
            "results": results,
            "diagnosis": diagnosis,
            "top_match": top_match,
            "reveal": reveal,
            "show_upgrade_popup": show_upgrade_popup,
        },
    )