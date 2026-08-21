import os
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import httpx
from pydantic import BaseModel
from config.config import settings
from middleware.auth import verify_api_key
from middleware.audit_log import audit_log_middleware
from starlette.middleware.base import BaseHTTPMiddleware
from memory import store
from tools import TOOL_DEFINITIONS, TOOL_DISPATCH
from user_profile import store as profile_store
from user_profile.extractor import extract_profile
from applications import store as applications_store

app = FastAPI()
app.add_middleware(BaseHTTPMiddleware, dispatch=audit_log_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store.init_db()
profile_store.init_db()
applications_store.init_db()

BASE_SYSTEM_PROMPT = (
    "You are Sanctum, a local-first assistant. Your tools: rag_search searches "
    "the user's own ingested documents; web_search searches the public "
    "internet for current information; job_search finds current job listings "
    "by title/keywords and optional location, returning listings numbered "
    "[1], [2], etc; save_job(index) records the job at that [N] position from "
    "the most recent job_search results into the user's tracked applications "
    "and returns its application id — never retype a job's title/company/url "
    "yourself, always reference it by its search result index; "
    "draft_cover_letter writes and saves a tailored cover letter for a saved "
    "application id, using the user's resume profile; apply_to_top_matches is "
    "the preferred tool whenever the user asks you to find/apply to jobs "
    "matching their resume in one request — it deterministically searches, "
    "saves, and drafts cover letters for the top matches in one call and "
    "returns the real results, which you must relay back close to verbatim "
    "(do not summarize from memory, do not invent additional jobs or "
    "companies not present in its output); prepare_application(application_id) "
    "opens a saved application's job page in a real browser and fills in "
    "what it confidently can from the resume profile — use this only when "
    "the user specifically asks to fill in / start / work on an application "
    "form, not as part of the default find-jobs flow; list_applications "
    "shows every job the user has saved/applied to with its status. Only "
    "call a tool when you need information you don't already have.\n\n"
    "IMPORTANT — you cannot actually submit job applications yet (that "
    "capability doesn't exist). Neither apply_to_top_matches nor "
    "prepare_application ever submits anything — prepare_application only "
    "fills the form and saves a screenshot for review, and deliberately "
    "never fills resume/file uploads, consent checkboxes, or demographic "
    "questions, which the user must handle themselves. Never claim you "
    "submitted or applied to a job on the user's behalf — only that you "
    "found/saved/drafted/filled it, and that they still need to finish and "
    "submit it manually. Whenever the user asks what they've applied to, "
    "saved, or the status of their applications, use list_applications "
    "rather than relying on conversation memory.\n\n"
    "If the user's current message includes attached file content, it is "
    "already provided directly in their message — use it as-is and do not "
    "call rag_search to look for it. Do not call a tool for greetings, "
    "opinions, or general knowledge you already know."
)


def _build_system_prompt() -> str:
    profile = profile_store.get_profile()
    if not profile:
        return BASE_SYSTEM_PROMPT

    skills = ", ".join(profile.get("skills") or []) or "none listed"
    recent_titles = ", ".join(
        f'{w["title"]} at {w["company"]}' for w in (profile.get("work_history") or [])[:2] if w.get("title")
    ) or "none listed"

    profile_context = (
        "\n\nThe user's profile, already extracted from their resume, is "
        "available below — use it directly, do not call rag_search to look "
        "for this information:\n"
        f"Name: {profile.get('name') or 'unknown'}\n"
        f"Location: {profile.get('location') or 'unknown'}\n"
        f"Skills: {skills}\n"
        f"Recent roles: {recent_titles}\n"
        "If the user just wants to browse/search jobs (not save or apply), "
        "call job_search directly using these skills/titles as the query and "
        "their location as the location. If they ask you to find/apply to "
        "jobs matching their resume, use apply_to_top_matches instead (see "
        "above) — it already reads this same profile itself."
    )
    return BASE_SYSTEM_PROMPT + profile_context


class Attachment(BaseModel):
    filename: str
    text: str


class QueryRequest(BaseModel):
    prompt: str
    attachment: Optional[Attachment] = None


@app.get("/")
def home():
    return {"message": "Welcome to the Sanctum Gateway!"}


def _chat(messages, with_tools: bool):
    payload = {
        "model": settings["ollama"]["model"],
        "messages": messages,
        "stream": False,
    }
    if with_tools:
        payload["tools"] = TOOL_DEFINITIONS
    response = httpx.post(
        settings["ollama"]["host"] + "/api/chat", json=payload, timeout=120.0
    )
    return response.json()["message"]


def _is_degenerate(content: str) -> bool:
    # llama3.2 sometimes emits an empty/near-empty JSON stub instead of real
    # text when tools are attached but it decides not to call one.
    return not content or content.strip() in ("{}", "{ }")


def _build_user_content(query: str, attachment: Optional[Attachment]) -> str:
    if not attachment:
        return query
    return (
        f'The user has attached a file named "{attachment.filename}". Its extracted '
        f"contents are included below for direct reference — this is not something "
        f"you need to search for.\n\n"
        f"--- BEGIN ATTACHMENT: {attachment.filename} ---\n"
        f"{attachment.text}\n"
        f"--- END ATTACHMENT ---\n\n"
        f"{query}"
    )


def generate_with_tools(query: str, attachment: Optional[Attachment] = None):
    turns = store.get_recent_turns(settings["memory"]["max_short_term_turns"])
    user_content = _build_user_content(query, attachment)
    messages = [
        {"role": "system", "content": _build_system_prompt()},
        *turns,
        {"role": "user", "content": user_content},
    ]

    tools_used = []
    max_rounds = settings["agent"]["max_tool_rounds"]
    answer = None

    for _ in range(max_rounds):
        message = _chat(messages, with_tools=True)
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            answer = message["content"]
            break

        messages.append(message)
        for call in tool_calls:
            name = call["function"]["name"]
            arguments = call["function"]["arguments"]
            result = TOOL_DISPATCH[name](**arguments)
            tools_used.append(name)
            messages.append({"role": "tool", "content": result})
    else:
        answer = _chat(messages, with_tools=False)["content"]

    if _is_degenerate(answer):
        answer = _chat(messages, with_tools=False)["content"]

    store.add_turn("user", user_content)
    store.add_turn("assistant", answer)

    return {"answer": answer, "tools_used": tools_used}


@app.post("/query/agent")
def run_query_agent(query: QueryRequest, api_key: str = Depends(verify_api_key)):
    return generate_with_tools(query.prompt, query.attachment)


@app.post("/attach")
async def attach(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    content = await file.read()
    files = {"file": (file.filename, content, file.content_type)}
    try:
        response = httpx.post("http://ingestion:8001/extract", files=files, timeout=120.0)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"ingestion service unreachable: {e}")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json().get("detail", "extraction failed"))
    return response.json()


@app.post("/memory/reset")
def reset_memory(api_key: str = Depends(verify_api_key)):
    store.reset_conversation()
    return {"message": "Conversation memory has been reset"}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...),
                 api_key: str = Depends(verify_api_key)):
    content = await file.read()
    files = {"file": (file.filename, content, file.content_type)}
    response = httpx.post(
        "http://ingestion:8001/ingest",
        files=files,
        timeout=120.0
    )
    return response.json()


@app.post("/profile/resume")
async def upload_resume(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    content = await file.read()

    files = {"file": (file.filename, content, file.content_type)}
    try:
        extract_response = httpx.post("http://ingestion:8001/extract", files=files, timeout=120.0)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"ingestion service unreachable: {e}")
    if extract_response.status_code != 200:
        raise HTTPException(
            status_code=extract_response.status_code,
            detail=extract_response.json().get("detail", "extraction failed"),
        )
    resume_text = extract_response.json()["text"]

    profile = extract_profile(resume_text)
    profile_store.save_profile(profile, source_filename=file.filename)

    files = {"file": (file.filename, content, file.content_type)}
    httpx.post("http://ingestion:8001/ingest", files=files, timeout=120.0)

    return profile


@app.get("/profile")
def get_profile(api_key: str = Depends(verify_api_key)):
    profile = profile_store.get_profile()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile has been created yet")
    return profile


@app.put("/profile")
def update_profile(profile: dict, api_key: str = Depends(verify_api_key)):
    return profile_store.save_profile(profile)


@app.get("/applications")
def list_applications_route(api_key: str = Depends(verify_api_key)):
    return applications_store.list_applications()


@app.get("/applications/{application_id}/screenshot")
def get_application_screenshot(application_id: int, api_key: str = Depends(verify_api_key)):
    path = f"/app/data/screenshots/{application_id}.png"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="No screenshot saved for this application")
    return FileResponse(path, media_type="image/png")
