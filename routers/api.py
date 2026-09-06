from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Plant, CareLog

router = APIRouter(prefix="/api")


class PlantOut(BaseModel):
    id: int
    name: str
    species: Optional[str] = None
    location: Optional[str] = None
    watering_interval_days: int
    last_watered: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class PlantCreate(BaseModel):
    name: str
    species: Optional[str] = None
    location: Optional[str] = None
    watering_interval_days: int = 7
    notes: Optional[str] = None


@router.get("/plants", response_model=list[PlantOut])
def list_plants(db: Session = Depends(get_db)):
    return db.query(Plant).order_by(Plant.name).all()


@router.get("/plants/{plant_id}", response_model=PlantOut)
def get_plant(plant_id: int, db: Session = Depends(get_db)):
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    return plant


@router.post("/plants", response_model=PlantOut, status_code=201)
def create_plant_api(payload: PlantCreate, db: Session = Depends(get_db)):
    plant = Plant(**payload.model_dump(), last_watered=datetime.utcnow())
    db.add(plant)
    db.commit()
    db.refresh(plant)
    return plant


@router.post("/plants/{plant_id}/water", response_model=PlantOut)
def water_plant_api(plant_id: int, db: Session = Depends(get_db)):
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    plant.last_watered = datetime.utcnow()
    db.add(CareLog(plant_id=plant_id, action="watered"))
    db.commit()
    db.refresh(plant)
    return plant


@router.delete("/plants/{plant_id}", status_code=204)
def delete_plant_api(plant_id: int, db: Session = Depends(get_db)):
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    db.delete(plant)
    db.commit()