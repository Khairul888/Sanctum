import fitz  # PyMuPDF

def load_pdf(file_path):
    pdf_document = fitz.open(file_path)
    content = ""
    for page in pdf_document:
        content += page.get_text()
    return content