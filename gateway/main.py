from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
from config.config import settings
from middleware.auth import verify_api_key
from middleware.audit_log import audit_log_middleware
from starlette.middleware.base import BaseHTTPMiddleware
from memory import store
from tools import TOOL_DEFINITIONS, TOOL_DISPATCH

app = FastAPI()
app.add_middleware(BaseHTTPMiddleware, dispatch=audit_log_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store.init_db()

SYSTEM_PROMPT = (
    "You are Sanctum, a local-first assistant. You have access to two tools: "
    "rag_search, which searches the user's own ingested documents, and "
    "web_search, which searches the public internet for current information. "
    "Only call a tool when you need information you don't already have — use "
    "rag_search for questions about the user's own documents, and web_search "
    "for current or real-time facts. Do not call a tool for greetings, "
    "opinions, or general knowledge you already know."
)


class QueryRequest(BaseModel):
    prompt: str


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


def generate_with_tools(query: str):
    turns = store.get_recent_turns(settings["memory"]["max_short_term_turns"])
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *turns, {"role": "user", "content": query}]

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

    store.add_turn("user", query)
    store.add_turn("assistant", answer)

    return {"answer": answer, "tools_used": tools_used}


@app.post("/query/agent")
def run_query_agent(query: QueryRequest, api_key: str = Depends(verify_api_key)):
    return generate_with_tools(query.prompt)


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
