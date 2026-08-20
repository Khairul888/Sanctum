import os
import tempfile
import fitz  # PyMuPDF
from ocr import run_ocr


def load_pdf(file_path):
    content = ""
    with fitz.open(file_path) as file:
        for page in file:
            text = page.get_text()
            if not text.strip():
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                page.get_pixmap().save(tmp_path)
                try:
                    text = run_ocr(tmp_path)
                finally:
                    os.remove(tmp_path)
            content += text
    return content
