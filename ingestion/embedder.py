import httpx
from config.config import settings


def embed_chunk(text):
    response = httpx.post(settings["ollama"]["host"] + "/api/embeddings", json={"model": settings["ollama"]["embedding_model"],
                          "prompt": text, },
                          timeout=120.0)
    return response.json()["embedding"]
