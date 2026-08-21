import httpx
from config.config import settings


def job_search(query: str, location: str = "") -> str:
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

    results = response.json().get("results", [])
    if not results:
        return "No matching jobs found."

    listings = []
    for job in results:
        title = job.get("title", "Unknown title")
        company = job.get("company", {}).get("display_name", "Unknown company")
        job_location = job.get("location", {}).get("display_name", "Unknown location")
        salary = job.get("salary_min")
        salary_part = f" — salary from {salary:.0f}" if salary else ""
        url = job.get("redirect_url", "")
        listings.append(f"{title} at {company} ({job_location}){salary_part}\n{url}")

    return "\n\n".join(listings)
