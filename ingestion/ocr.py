from paddleocr import PaddleOCR

_ocr = PaddleOCR(use_angle_cls=True, lang="en", enable_mkldnn=False)


def run_ocr(image_path: str) -> str:
    result = _ocr.ocr(image_path)
    lines = []
    for page in result:
        lines.extend(page.get("rec_texts", []))
    return "\n".join(lines)
