from config.config import settings


def chunk_text(text, chunk_size=settings["chunking"]
               ["chunk_size"], overlap=settings["chunking"]["overlap"]):
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks
