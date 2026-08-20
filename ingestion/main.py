from fastapi import FastAPI, UploadFile, File, HTTPException
import tempfile
import os
from pipeline import ingest_document, extract_text

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


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    content = await file.read()

    suffix = os.path.splitext(file.filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text = extract_text(tmp_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.remove(tmp_path)

    return {"filename": file.filename, "text": text}
