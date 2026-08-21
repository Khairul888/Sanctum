import httpx
from config.config import settings
from applications import store as applications_store
from user_profile import store as profile_store
from .job_search import get_cached_result, _fetch_jobs

MAX_BATCH_APPLY = 5

COVER_LETTER_PROMPT_PREFIX = (
    "Write a concise, tailored cover letter (3-4 short paragraphs, no "
    "placeholders, ready to send) for the candidate below applying to the "
    "job below. Use only facts present in the candidate profile — do not "
    "invent experience.\n\n"
    "--- CANDIDATE PROFILE ---\n"
)
COVER_LETTER_PROMPT_MIDDLE = "\n--- JOB ---\n"
COVER_LETTER_PROMPT_SUFFIX = "\n--- END ---"


def save_job(index) -> str:
    try:
        index = int(index)
    except (TypeError, ValueError):
        return f"'{index}' is not a valid job index. Use the [N] number from job_search results."

    job = get_cached_result(index)
    if not job:
        return f"No job at index {index} from the most recent job_search results. Run job_search again first."

    application = applications_store.save_job(
        title=job["title"], company=job["company"], url=job["url"],
        location=job.get("location") or None, salary=job.get("salary") or None,
    )
    return (
        f"Saved (application id {application['id']}): {application['title']} at "
        f"{application['company']}. Status: {application['status']}."
    )


def _format_profile(profile: dict) -> str:
    lines = [
        f"Name: {profile.get('name') or 'unknown'}",
        f"Location: {profile.get('location') or 'unknown'}",
        f"Summary: {profile.get('summary') or 'none'}",
        f"Skills: {', '.join(profile.get('skills') or []) or 'none listed'}",
    ]
    for job in profile.get("work_history") or []:
        lines.append(
            f"- {job.get('title', '')} at {job.get('company', '')} "
            f"({job.get('start_date', '')}–{job.get('end_date', '')}): {job.get('description', '')}"
        )
    for edu in profile.get("education") or []:
        lines.append(f"- {edu.get('degree', '')} in {edu.get('field', '')}, {edu.get('institution', '')}")
    return "\n".join(lines)


def _generate_cover_letter(profile: dict, job_summary: str) -> str:
    prompt = (
        COVER_LETTER_PROMPT_PREFIX + _format_profile(profile) +
        COVER_LETTER_PROMPT_MIDDLE + job_summary +
        COVER_LETTER_PROMPT_SUFFIX
    )
    response = httpx.post(
        settings["ollama"]["host"] + "/api/chat",
        json={
            "model": settings["ollama"]["model"],
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def draft_cover_letter(application_id, job_description: str = "") -> str:
    try:
        application_id = int(application_id)
    except (TypeError, ValueError):
        return f"'{application_id}' is not a valid application id. Use the id returned by save_job."

    application = applications_store.get_application(application_id)
    if not application:
        return f"No saved application found with id {application_id}. Use save_job first."

    profile = profile_store.get_profile()
    if not profile:
        return "No resume profile is stored yet — ask the user to upload one on the Resume screen first."

    job_summary = f"{application['title']} at {application['company']}"
    if application.get("location"):
        job_summary += f" ({application['location']})"
    if job_description:
        job_summary += f"\n\n{job_description}"

    cover_letter = _generate_cover_letter(profile, job_summary)

    applications_store.update_application(
        application_id, cover_letter=cover_letter, status="cover_letter_drafted"
    )
    return cover_letter


def apply_to_top_matches(count=3, query: str = "", location: str = "") -> str:
    try:
        count = max(1, min(int(count), MAX_BATCH_APPLY))
    except (TypeError, ValueError):
        count = 3

    profile = profile_store.get_profile()
    if not profile:
        return "No resume profile is stored yet — ask the user to upload one on the Resume screen first."

    if not query:
        query = ", ".join(profile.get("skills") or [])
        if not query:
            return "The stored profile has no skills listed to search with — ask the user to fill that in."
    if not location:
        location = profile.get("location") or ""

    jobs = _fetch_jobs(query, location)
    if isinstance(jobs, str):
        return jobs
    if not jobs:
        return f"No matching jobs found for '{query}' in '{location or 'any location'}'."

    blocks = []
    for job in jobs[:count]:
        application = applications_store.save_job(
            title=job["title"], company=job["company"], url=job["url"],
            location=job.get("location") or None, salary=job.get("salary") or None,
        )
        job_summary = f"{application['title']} at {application['company']}"
        if application.get("location"):
            job_summary += f" ({application['location']})"

        cover_letter = _generate_cover_letter(profile, job_summary)
        applications_store.update_application(
            application["id"], cover_letter=cover_letter, status="cover_letter_drafted"
        )

        blocks.append(
            f"[application id {application['id']}] {application['title']} at {application['company']}\n"
            f"{application['url']}\n\nCover letter:\n{cover_letter}"
        )

    header = (
        f"Found, saved, and drafted cover letters for {len(blocks)} job(s) matching the resume. "
        "None of these have been submitted — automatic submission isn't built yet, so each one "
        "still needs to be submitted manually:\n\n"
    )
    return header + "\n\n---\n\n".join(blocks)


def list_applications() -> str:
    applications = applications_store.list_applications()
    if not applications:
        return "No jobs have been saved or applied to yet."

    lines = []
    for app in applications:
        lines.append(
            f"[{app['id']}] {app['title']} at {app['company']} "
            f"({app.get('location') or 'unknown location'}) — status: {app['status']}"
        )
    return "\n".join(lines)
