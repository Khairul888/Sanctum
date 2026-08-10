from fastapi import FastAPI, UploadFile, File
import tempfile
import os
from pipeline import ingest_document

app = FastAPI()


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    content = await file.read()

    suffix = os.path.splitext(file.filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        ingest_document(tmp_path)
    finally:
        os.remove(tmp_path)

    return {"message": "Document ingested successfully",
            "filename": file.filename}
