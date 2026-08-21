import httpx
from config.config import settings

# Results from the most recent job_search call, indexed 1..N. Lets save_job
# reference a listing by index instead of requiring the model to retype its
# title/company/url exactly — that transcription step is where a small local
# model reliably introduces errors (blank/garbled fields).
_last_results = []


def get_cached_result(index: int):
    if 1 <= index <= len(_last_results):
        return _last_results[index - 1]
    return None


def _fetch_jobs(query: str, location: str = ""):
    # Returns a list of job dicts, or a string error message for callers to
    # pass straight through as their own tool result.
    app_id = settings["jobs"]["adzuna_app_id"]
    app_key = settings["jobs"]["adzuna_app_key"]
    if not app_id or not app_key:
        return "Job search is not configured (missing ADZUNA_APP_ID/ADZUNA_APP_KEY)."

    country = settings["jobs"]["country"]
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": settings["jobs"]["n_results"],
        "content-type": "application/json",
    }
    if location:
        params["where"] = location

    # Adzuna's `what` param ANDs every word together, so a comma-separated
    # list of skills (rather than a short job-title phrase) matches almost
    # nothing. Treat comma-separated queries as a keyword list and OR them
    # via `what_or` instead, so any matching skill surfaces a result.
    if "," in query:
        keywords = [term.strip() for term in query.split(",") if term.strip()]
        params["what_or"] = " ".join(keywords)
    else:
        params["what"] = query

    try:
        response = httpx.get(
            f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
            params=params,
            timeout=settings["jobs"]["timeout_seconds"],
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return f"Job search failed: {exc}"

    jobs = []
    for job in response.json().get("results", []):
        salary = job.get("salary_min")
        jobs.append({
            "title": job.get("title", "Unknown title"),
            "company": job.get("company", {}).get("display_name", "Unknown company"),
            "location": job.get("location", {}).get("display_name", "Unknown location"),
            "salary": f"{salary:.0f}" if salary else "",
            "url": job.get("redirect_url", ""),
        })
    return jobs


def job_search(query: str, location: str = "") -> str:
    jobs = _fetch_jobs(query, location)
    if isinstance(jobs, str):
        return jobs
    if not jobs:
        return "No matching jobs found."

    global _last_results
    _last_results = jobs

    listings = []
    for i, job in enumerate(jobs, start=1):
        salary_part = f" — salary from {job['salary']}" if job["salary"] else ""
        listings.append(f"[{i}] {job['title']} at {job['company']} ({job['location']}){salary_part}\n{job['url']}")
    return "\n\n".join(listings)
