import fitz


def load_img(file_path):
    with fitz.open(file_path) as file:
        pdf_bytes = file.convert_to_pdf()
        pdf_doc = fitz.open("pdf", pdf_bytes)
        page = pdf_doc[0]
        textpage = page.get_textpage_ocr()
        content = page.get_text(textpage=textpage)
    return content
