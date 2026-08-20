import base64
import httpx
from config.config import settings


def describe_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    response = httpx.post(
        settings["ollama"]["host"] + "/api/chat",
        json={
            "model": settings["ollama"]["vision_model"],
            "messages": [
                {
                    "role": "user",
                    "content": "Describe what is depicted in this image in detail.",
                    "images": [image_b64],
                }
            ],
            "stream": False,
        },
        timeout=120.0,
    )
    return response.json()["message"]["content"]
