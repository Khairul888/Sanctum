from fastapi import Header, HTTPException
from config.config import settings
import sys
sys.path.append("/app")

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings["auth"]["api_key"]:
        raise HTTPException(status_code=403, detail="Invalid API key")
