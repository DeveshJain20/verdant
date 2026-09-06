from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import jinja2

from database import get_db
from models import ContactMessage
from deps import get_optional_user

router = APIRouter()

templates = Jinja2Templates(
    env=jinja2.Environment(
        loader=jinja2.FileSystemLoader("templates"),
        autoescape=True,
        cache_size=0,
    )
)


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user=Depends(get_optional_user)):
    return templates.TemplateResponse(request, "marketing_home.html", {"user": user})


@router.get("/about", response_class=HTMLResponse)
def about(request: Request, user=Depends(get_optional_user)):
    return templates.TemplateResponse(request, "about.html", {"user": user})


@router.get("/services", response_class=HTMLResponse)
def services(request: Request, user=Depends(get_optional_user)):
    return templates.TemplateResponse(request, "services.html", {"user": user})


@router.get("/faq", response_class=HTMLResponse)
def faq(request: Request, user=Depends(get_optional_user)):
    return templates.TemplateResponse(request, "faq.html", {"user": user})


@router.get("/contact", response_class=HTMLResponse)
def contact_form(request: Request, user=Depends(get_optional_user)):
    return templates.TemplateResponse(request, "contact.html", {"user": user})


@router.post("/contact", response_class=HTMLResponse)
def contact_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(""),
    message: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    entry = ContactMessage(name=name, email=email, subject=subject, message=message)
    db.add(entry)
    db.commit()
    return templates.TemplateResponse(request, "contact.html", {"success": True, "user": user})