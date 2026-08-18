from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
import httpx
import chromadb
from pydantic import BaseModel
from config.config import settings
from middleware.auth import verify_api_key
from middleware.audit_log import audit_log_middleware
from starlette.middleware.base import BaseHTTPMiddleware
from memory import store

app = FastAPI()
app.add_middleware(BaseHTTPMiddleware, dispatch=audit_log_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store.init_db()

client = chromadb.HttpClient(host="chromadb", port=8000)
collection = client.get_or_create_collection("documents")


class QueryRequest(BaseModel):
    prompt: str


@app.get("/")
def home():
    return {"message": "Welcome to the Sanctum Gateway!"}


def generate_with_history(query: str, extra_context: str = None):
    turns = store.get_recent_turns(settings["memory"]["max_short_term_turns"])
    history = store.format_history(turns)

    prompt_parts = []
    if history:
        prompt_parts.append(f"Conversation so far:\n{history}")
    if extra_context:
        prompt_parts.append(
            f"Use the following context to answer the question.\n\nContext:\n{extra_context}"
        )
    prompt_parts.append(f"Question: {query}")

    response = httpx.post(
        settings["ollama"]["host"] + "/api/generate",
        json={
            "model": settings["ollama"]["model"],
            "prompt": "\n\n".join(prompt_parts),
            "stream": False,
        },
        timeout=120.0
    )
    answer = response.json()["response"]

    store.add_turn("user", query)
    store.add_turn("assistant", answer)

    return answer


def query_plain(query: str):
    return {"answer": generate_with_history(query)}


def query_rag(query: str):
    embedded_query = httpx.post(
        settings["ollama"]["host"] + "/api/embeddings",
        json={"model": settings["ollama"]["embedding_model"], "prompt": query},
        timeout=120.0
    )
    query_embeddings = embedded_query.json()["embedding"]

    results = collection.query(
        query_embeddings=[query_embeddings],
        n_results=settings["retrieval"]["n_results"]
    )

    chunks = results["documents"][0]
    context = "\n".join(chunks)

    return {"answer": generate_with_history(query, extra_context=context)}


@app.post("/query")
def run_query(query: QueryRequest, api_key: str = Depends(verify_api_key)):
    return query_plain(query.prompt)


@app.post("/query/rag")
def run_query_rag(query: QueryRequest, api_key: str = Depends(verify_api_key)):
    return query_rag(query.prompt)


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
