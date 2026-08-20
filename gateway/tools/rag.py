import httpx
import chromadb
from config.config import settings

_client = chromadb.HttpClient(
    host=settings["chromadb"]["host"], port=settings["chromadb"]["port"]
)
collection = _client.get_or_create_collection(settings["chromadb"]["collection"])


def rag_search(query: str) -> str:
    embedded_query = httpx.post(
        settings["ollama"]["host"] + "/api/embeddings",
        json={"model": settings["ollama"]["embedding_model"], "prompt": query},
        timeout=120.0,
    )
    query_embeddings = embedded_query.json()["embedding"]

    results = collection.query(
        query_embeddings=[query_embeddings],
        n_results=settings["retrieval"]["n_results"],
    )

    chunks = results["documents"][0]
    if not chunks:
        return "No relevant documents found."
    return "\n".join(chunks)
