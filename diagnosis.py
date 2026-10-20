import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def _extra():
    return {"reasoning_effort": "low"} if "gpt-oss" in MODEL else {}


def _parse_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model reply")
    return json.loads(text[start:end + 1])


def _clamp(value, default):
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return default


def get_diagnosis(common_name: str, scientific_name: str) -> dict:
    prompt = f"""You are a plant pathology expert. A user scanned a plant identified as:
Common name: {common_name}
Scientific name: {scientific_name}

Respond ONLY with valid JSON, no markdown, no preamble, in exactly this structure:
{{
  "health_score": <integer 0-100, realistic estimated health for a typical plant of this species showing common signs of stress>,
  "recovery_chance": <integer 0-100, estimated percent chance of full recovery with proper treatment>,
  "common_issues": ["issue 1", "issue 2", "issue 3"],
  "prevention": ["tip 1", "tip 2", "tip 3"],
  "treatment": ["step 1", "step 2", "step 3"]
}}

Keep each item to one short sentence, specific to this species. health_score and recovery_chance must be integers only."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1500,
            extra_body=_extra(),
        )
        text = (response.choices[0].message.content or "").strip()
        data = _parse_json(text)
        data["health_score"] = _clamp(data.get("health_score"), 70)
        data["recovery_chance"] = _clamp(data.get("recovery_chance"), 70)
        return data
    except Exception as e:
        print(f"[diagnosis] Groq call failed with model {MODEL}: {type(e).__name__}: {e}", flush=True)
        return {
            "health_score": 70,
            "recovery_chance": 70,
            "common_issues": ["Diagnosis unavailable right now."],
            "prevention": ["Please try scanning again in a moment."],
            "treatment": [],
        }