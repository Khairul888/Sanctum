import chromadb
from loaders.txt_loader import load_txt
from loaders.pdf_loader import load_pdf
from loaders.image_loader import load_img
from embedder import embed_chunk
from chunker import chunk_text

client = chromadb.HttpClient(host="chromadb", port=8000)
collection = client.get_or_create_collection("documents")

def ingest_document(file_path):
    if file_path.endswith('.txt'):
        content = load_txt(file_path)
    elif file_path.endswith('.pdf'):
        content =  load_pdf(file_path)
    elif file_path.endswith(('.jpg', '.png', 'jpeg')):
        content =  load_img(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")
    
    chunks = chunk_text(content)

    for i, chunk in enumerate(chunks):
        embedding = embed_chunk(chunk)
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"chunk_{i}"]
        )
   