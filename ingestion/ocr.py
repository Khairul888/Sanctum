from paddleocr import PaddleOCR

_ocr = PaddleOCR(use_angle_cls=True, lang="en")


def run_ocr(image_path: str) -> str:
    result = _ocr.ocr(image_path, cls=True)
    lines = []
    for page in result:
        if not page:
            continue
        for _, (text, _confidence) in page:
            lines.append(text)
    return "\n".join(lines)
