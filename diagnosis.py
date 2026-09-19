import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


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
            max_tokens=500,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
        data["health_score"] = int(data.get("health_score", 70))
        data["recovery_chance"] = int(data.get("recovery_chance", 70))
        return data
    except Exception:
        return {
            "health_score": 70,
            "recovery_chance": 70,
            "common_issues": ["Diagnosis unavailable right now."],
            "prevention": ["Please try scanning again in a moment."],
            "treatment": [],
        }