from fastapi import FastAPI, UploadFile, File
import httpx
import chromadb
from pydantic import BaseModel
from config.config import settings

app = FastAPI()

client = chromadb.HttpClient(host="chromadb", port=8000)
collection = client.get_or_create_collection("documents")

class QueryRequest(BaseModel):
    prompt: str

@app.get("/")
def home():
    return {"message": "Welcome to the Sanctum Gateway!"}

def query_ollama(query: str):
    embedded_query = httpx.post(
        settings["ollama"]["host"] + "/api/embeddings",
        json={"model": settings["ollama"]["embedding_model"], "prompt": query},
        timeout=120.0
    )
    query_embeddings = embedded_query.json()["embedding"]

    results = collection.query(
        query_embeddings=[query_embeddings],
        n_results= settings["retrieval"]["n_results"]
    )

    chunks = results["documents"][0]
    context = "\n".join(chunks)

    response = httpx.post(
        settings["ollama"]["host"] + "/api/generate",
        json={
            "model": settings["ollama"]["model"],
            "prompt": f"Use the following context to answer the question.\n\nContext:\n{context}\n\nQuestion: {query}",
            "stream": False,
        },
        timeout=120.0
    )
    return {"answer": response.json()["response"]}

@app.post("/query")
def run_query(query: QueryRequest):
    return query_ollama(query.prompt)

@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    content = await file.read()
    files = {"file": (file.filename, content, file.content_type)}
    response = httpx.post(
        "http://ingestion:8001/ingest",
        files=files,
        timeout=120.0
    )
    return response.json()