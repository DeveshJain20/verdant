from datetime import datetime, timedelta
import jinja2
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Plant, CareLog, User
from deps import get_current_user

router = APIRouter()

templates = Jinja2Templates(
    env=jinja2.Environment(
        loader=jinja2.FileSystemLoader("templates"),
        autoescape=True,
        cache_size=0,
    )
)


def days_until_next_watering(plant: Plant) -> int:
    if not plant.last_watered:
        return 0
    due_date = plant.last_watered + timedelta(days=plant.watering_interval_days)
    delta = due_date - datetime.utcnow()
    return delta.days


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plants = db.query(Plant).filter(Plant.owner_id == user.id).order_by(Plant.name).all()
    plant_data = []
    for p in plants:
        days_left = days_until_next_watering(p)
        plant_data.append({
            "plant": p,
            "days_left": days_left,
            "needs_water": days_left <= 0,
        })
    return templates.TemplateResponse(
        request, "index.html", {"plant_data": plant_data, "user": user}
    )


@router.get("/plants/new", response_class=HTMLResponse)
def new_plant_form(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "add_plant.html", {"user": user})


@router.post("/plants/new")
def create_plant(
    name: str = Form(...),
    species: str = Form(""),
    location: str = Form(""),
    watering_interval_days: int = Form(7),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plant = Plant(
        owner_id=user.id,
        name=name,
        species=species,
        location=location,
        watering_interval_days=watering_interval_days,
        notes=notes,
        last_watered=datetime.utcnow(),
    )
    db.add(plant)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/plants/{plant_id}", response_class=HTMLResponse)
def plant_detail(plant_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plant = db.query(Plant).filter(Plant.id == plant_id, Plant.owner_id == user.id).first()
    logs = (
        db.query(CareLog)
        .filter(CareLog.plant_id == plant_id)
        .order_by(CareLog.date.desc())
        .all()
    )
    return templates.TemplateResponse(
        request, "plant_detail.html", {"plant": plant, "logs": logs, "user": user}
    )


@router.post("/plants/{plant_id}/water")
def water_plant(plant_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plant = db.query(Plant).filter(Plant.id == plant_id, Plant.owner_id == user.id).first()
    if plant:
        plant.last_watered = datetime.utcnow()
        log = CareLog(plant_id=plant_id, action="watered")
        db.add(log)
        db.commit()
    return RedirectResponse(url=f"/plants/{plant_id}", status_code=303)


@router.post("/plants/{plant_id}/delete")
def delete_plant(plant_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plant = db.query(Plant).filter(Plant.id == plant_id, Plant.owner_id == user.id).first()
    if plant:
        db.delete(plant)
        db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)