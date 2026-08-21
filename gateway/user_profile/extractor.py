import json
import httpx
from config.config import settings

PROFILE_SCHEMA_EXAMPLE = {
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "summary": "",
    "skills": ["..."],
    "work_history": [
        {"company": "", "title": "", "start_date": "", "end_date": "", "description": ""}
    ],
    "education": [
        {"institution": "", "degree": "", "field": "", "year": ""}
    ],
}

EXTRACTION_PROMPT_PREFIX = (
    "Extract structured profile data from the resume text below. Respond with a "
    "single JSON object matching exactly this shape (use empty strings/lists for "
    "anything not present in the resume, do not invent information):\n\n"
    f"{json.dumps(PROFILE_SCHEMA_EXAMPLE, indent=2)}\n\n"
    "Resume text:\n"
    "--- BEGIN RESUME ---\n"
)
EXTRACTION_PROMPT_SUFFIX = "\n--- END RESUME ---"


def extract_profile(resume_text: str) -> dict:
    prompt = EXTRACTION_PROMPT_PREFIX + resume_text + EXTRACTION_PROMPT_SUFFIX
    payload = {
        "model": settings["ollama"]["model"],
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",
        "stream": False,
    }
    response = httpx.post(
        settings["ollama"]["host"] + "/api/chat", json=payload, timeout=120.0
    )
    response.raise_for_status()
    content = response.json()["message"]["content"]
    return json.loads(content)
