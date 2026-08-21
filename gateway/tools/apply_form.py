import json
import os
import base64
import httpx
from config.config import settings
from applications import store as applications_store
from user_profile import store as profile_store
from .applications import _format_profile, _generate_cover_letter

BROWSER_SERVICE = "http://browser:8002"
BROWSER_TIMEOUT = 30.0
SCREENSHOT_DIR = "/app/data/screenshots"

# Never auto-fill these — voluntary/protected demographic questions, consent
# checkboxes, and file/password inputs all require the user's own explicit
# input rather than an automated guess.
EXCLUDED_LABEL_KEYWORDS = [
    "gender", "race", "ethnic", "hispanic", "latino", "veteran", "disability",
    "sexual orientation", "pronoun", "agree", "consent", "acknowledge",
    "terms of service", "privacy policy",
]
EXCLUDED_TYPES = {"file", "password", "checkbox", "hidden"}
EXCLUDED_TAGS = {"button"}

MAPPING_PROMPT_PREFIX = (
    "You are filling out a job application form for the candidate below. "
    "Given their profile, their cover letter for this job, and the list of "
    "form fields, decide which fields you can confidently fill and what "
    "value to use. Respond with a single JSON object of this exact shape:\n"
    '{"fields": [{"label": "First Name*", "value": "some value"}]}\n'
    "The \"label\" of each item you return MUST be copied exactly, character "
    "for character, from a \"label\" in the FORM FIELDS list below — never "
    "invent a field or change its wording. Only include a field if you are "
    "confident of the correct value from the profile/cover letter — omit "
    "anything unclear rather than guessing. For a field with an \"options\" "
    "list, your value must be one of those exact option strings. For a "
    "field of type \"combobox\" with no options listed, use the short, "
    "natural wording you'd expect the real option to have (e.g. 'Yes', "
    "'No', a specific number, a country name).\n\n"
    "--- CANDIDATE PROFILE ---\n"
)
MAPPING_PROMPT_MIDDLE = "\n--- COVER LETTER FOR THIS JOB ---\n"
MAPPING_PROMPT_FIELDS = "\n--- FORM FIELDS ---\n"


def _is_excluded(field: dict) -> bool:
    if field.get("type") in EXCLUDED_TYPES or field.get("tag") in EXCLUDED_TAGS:
        return True
    label = (field.get("label") or "").lower()
    return any(keyword in label for keyword in EXCLUDED_LABEL_KEYWORDS)


def _map_fields_to_values(fields: list, profile: dict, cover_letter: str) -> dict:
    # Only fields with a real, non-empty label are offered to the model —
    # otherwise it has nothing reliable to copy back for the grounding check
    # below, and would have to invent an identifier instead.
    candidates = [f for f in fields if f.get("label") and not _is_excluded(f)]
    if not candidates:
        return {}

    trimmed = [
        {
            "label": f["label"], "type": f["type"],
            "required": f["required"], "options": f.get("options"),
        }
        for f in candidates
    ]
    prompt = (
        MAPPING_PROMPT_PREFIX + _format_profile(profile) +
        MAPPING_PROMPT_MIDDLE + (cover_letter or "(none)") +
        MAPPING_PROMPT_FIELDS + json.dumps(trimmed, indent=2)
    )
    response = httpx.post(
        settings["ollama"]["host"] + "/api/chat",
        json={
            "model": settings["ollama"]["model"],
            "messages": [{"role": "user", "content": prompt}],
            "format": "json",
            "stream": False,
            # A default-temperature pass tends to answer only the first
            # couple of fields and stop; a low temperature produces a
            # complete, deterministic run through every candidate field.
            "options": {"temperature": 0.1},
        },
        timeout=120.0,
    )
    response.raise_for_status()
    content = response.json()["message"]["content"]
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {}

    # Ground the response against the real candidate labels — the model can
    # still hallucinate a label that was never offered, so anything that
    # doesn't exactly match a real candidate is dropped rather than acted on.
    valid_labels = {f["label"] for f in candidates}
    mapping = {}
    for item in parsed.get("fields", []):
        label, value = item.get("label"), item.get("value")
        if label in valid_labels and value not in (None, ""):
            mapping[label] = value
    return mapping


def _find_field_by_label(fields: list, label: str):
    return next((f for f in fields if f["label"] == label), None)


def prepare_application(application_id) -> str:
    try:
        application_id = int(application_id)
    except (TypeError, ValueError):
        return f"'{application_id}' is not a valid application id. Use the id returned by save_job."

    application = applications_store.get_application(application_id)
    if not application:
        return f"No saved application found with id {application_id}. Use save_job first."
    if not application.get("url"):
        return f"Application {application_id} has no URL to open."

    profile = profile_store.get_profile()
    if not profile:
        return "No resume profile is stored yet — ask the user to upload one on the Resume screen first."

    cover_letter = application.get("cover_letter")
    if not cover_letter:
        job_summary = f"{application['title']} at {application['company']}"
        cover_letter = _generate_cover_letter(profile, job_summary)
        applications_store.update_application(application_id, cover_letter=cover_letter)

    try:
        session_id = httpx.post(f"{BROWSER_SERVICE}/session", timeout=BROWSER_TIMEOUT).json()["session_id"]
    except httpx.HTTPError as exc:
        return f"Browser service is unreachable: {exc}"

    try:
        nav = httpx.post(
            f"{BROWSER_SERVICE}/session/{session_id}/navigate",
            json={"url": application["url"]}, timeout=BROWSER_TIMEOUT,
        )
        if nav.status_code != 200:
            return f"Could not open the application page: {nav.json().get('detail', nav.text)}"

        fields = httpx.get(f"{BROWSER_SERVICE}/session/{session_id}/fields", timeout=BROWSER_TIMEOUT).json()["fields"]
        mapping = _map_fields_to_values(fields, profile, cover_letter)

        filled, skipped = [], []
        for label, value in mapping.items():
            # A prior action can reflow the page and shift every index after
            # it, so every field is re-resolved by label against a fresh
            # read right before acting on it, never a stale snapshot.
            current = httpx.get(f"{BROWSER_SERVICE}/session/{session_id}/fields", timeout=BROWSER_TIMEOUT).json()["fields"]
            current_field = _find_field_by_label(current, label)
            if not current_field:
                skipped.append({"label": label, "reason": "field no longer present on the page"})
                continue

            action = "select_combobox" if current_field["type"] == "combobox" else "fill"
            resp = httpx.post(
                f"{BROWSER_SERVICE}/session/{session_id}/{action}",
                json={"index": current_field["index"], "value": value}, timeout=BROWSER_TIMEOUT,
            )
            # Some fields carry role="combobox" purely for accessibility and
            # never produce a role="option" list (e.g. address autocomplete)
            # — plain fill() is the correct action for those, so retry with
            # it before giving up.
            if resp.status_code != 200 and action == "select_combobox":
                resp = httpx.post(
                    f"{BROWSER_SERVICE}/session/{session_id}/fill",
                    json={"index": current_field["index"], "value": value}, timeout=BROWSER_TIMEOUT,
                )
            if resp.status_code == 200:
                filled.append({"label": label, "value": value})
            else:
                skipped.append({"label": label, "reason": resp.json().get("detail", "fill failed")})

        for field in fields:
            if not field.get("label"):
                continue
            if field["label"] in mapping:
                continue
            reason = "requires your own input" if _is_excluded(field) else "could not confidently determine a value"
            skipped.append({"label": field["label"], "reason": reason})

        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        screenshot_resp = httpx.get(f"{BROWSER_SERVICE}/session/{session_id}/screenshot", timeout=BROWSER_TIMEOUT)
        png_bytes = base64.b64decode(screenshot_resp.json()["image_base64"])
        with open(os.path.join(SCREENSHOT_DIR, f"{application_id}.png"), "wb") as f:
            f.write(png_bytes)
    finally:
        httpx.delete(f"{BROWSER_SERVICE}/session/{session_id}", timeout=BROWSER_TIMEOUT)

    applications_store.update_application(
        application_id,
        status="filled",
        filled_fields=json.dumps({"filled": filled, "skipped": skipped}),
    )

    summary = (
        f"Filled {len(filled)} field(s) on the application for {application['title']} at "
        f"{application['company']}. Left {len(skipped)} field(s) for you to review/complete "
        f"yourself (resume upload, consent checkboxes, and demographic questions are never "
        f"auto-filled). A screenshot of the filled form has been saved. "
        f"Nothing has been submitted — this still needs to be submitted manually."
    )
    return summary
