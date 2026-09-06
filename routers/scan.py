import os
import httpx
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import jinja2

load_dotenv()

PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY")
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_API_KEY}"

router = APIRouter()

templates = Jinja2Templates(
    env=jinja2.Environment(
        loader=jinja2.FileSystemLoader("templates"),
        autoescape=True,
        cache_size=0,
    )
)


@router.get("/scan", response_class=HTMLResponse)
def scan_form(request: Request):
    return templates.TemplateResponse(request, "scan.html", {})


@router.post("/scan", response_class=HTMLResponse)
async def scan_photo(request: Request, photo: UploadFile = File(...)):
    if not PLANTNET_API_KEY:
        return templates.TemplateResponse(
            request,
            "scan.html",
            {"error": "PlantNet API key is not configured. Check your .env file."},
        )

    image_bytes = await photo.read()

    files = {"images": (photo.filename, image_bytes, photo.content_type)}
    data = {"organs": "leaf"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(PLANTNET_URL, files=files, data=data)
    except httpx.RequestError:
        return templates.TemplateResponse(
            request,
            "scan.html",
            {"error": "Could not reach PlantNet. Please try again."},
        )

    if response.status_code != 200:
        return templates.TemplateResponse(
            request,
            "scan.html",
            {"error": f"PlantNet couldn't identify this photo (status {response.status_code}). Try a clearer image."},
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
            request,
            "scan.html",
            {"error": "No matches found. Try a clearer photo of a leaf or flower."},
        )

    return templates.TemplateResponse(
        request, "scan.html", {"results": results}
    )