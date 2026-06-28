from fastapi import FastAPI
import httpx
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    prompt: str

@app.get("/")
def home():
    return {"message": "Welcome to the Sanctum Gateway!"}   

def query_ollama(query: str):
    response = httpx.post("http://ollama:11434/api/generate", json=
                          {"model": "llama3.2",
                            "prompt": query,
                            "stream": False,},
                            timeout=120.0)
    return response.json()

@app.post("/query")
def run_query(query: QueryRequest):
    return query_ollama(query.prompt)