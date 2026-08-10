import fitz  # PyMuPDF


def load_pdf(file_path):
    content = ""
    with fitz.open(file_path) as file:
        for page in file:
            text = page.get_text()
            if not text.strip():
                text = page.get_text("text", ocr=True)
            content += text
    return content
