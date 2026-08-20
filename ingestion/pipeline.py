import uuid
import chromadb
from loaders.txt_loader import load_txt
from loaders.pdf_loader import load_pdf
from ocr import run_ocr
from vision import describe_image
from embedder import embed_chunk
from chunker import chunk_text

client = chromadb.HttpClient(host="chromadb", port=8000)
collection = client.get_or_create_collection("documents")


def extract_text(file_path: str) -> str:
    if file_path.endswith('.txt'):
        return load_txt(file_path)
    elif file_path.endswith('.pdf'):
        return load_pdf(file_path)
    elif file_path.endswith(('.jpg', '.jpeg', '.png')):
        ocr_text = run_ocr(file_path)
        caption = describe_image(file_path)
        parts = []
        if ocr_text.strip():
            parts.append(f"Text found in image:\n{ocr_text}")
        parts.append(f"Visual description:\n{caption}")
        return "\n\n".join(parts)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")


def ingest_document(file_path):
    content = extract_text(file_path)
    chunks = chunk_text(content)

    for i, chunk in enumerate(chunks):
        embedding = embed_chunk(chunk)
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{uuid.uuid4()}_chunk_{i}"]
        )
