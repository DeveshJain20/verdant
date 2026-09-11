from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import Base, engine
from routers import plants, api, scan, auth, marketing, billing
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Verdant - AI Plant Diagnosis")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(marketing.router)
app.include_router(auth.router)
app.include_router(plants.router)
app.include_router(api.router)
app.include_router(scan.router)
app.include_router(billing.router)