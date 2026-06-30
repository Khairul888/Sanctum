import httpx

def embed_chunk(text):
    response = httpx.post("http://ollama:11434/api/embeddings", json=
                          {"model": "nomic-embed-text",
                          "prompt": text,},
                            timeout=120.0)
    return response.json()["embedding"]