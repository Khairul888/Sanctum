from fastapi import FastAPI, UploadFile, File
import httpx
import chromadb
from pydantic import BaseModel

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
        "http://ollama:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": query},
        timeout=120.0
    )
    query_embeddings = embedded_query.json()["embedding"]

    results = collection.query(
        query_embeddings=[query_embeddings],
        n_results=3
    )

    chunks = results["documents"][0]
    context = "\n".join(chunks)

    response = httpx.post(
        "http://ollama:11434/api/generate",
        json={
            "model": "llama3.2",
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