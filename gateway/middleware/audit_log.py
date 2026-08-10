from fastapi import Request
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sacntum.audit")

async def audit_log_middleware(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    
    logger.info({
        "timestamp": start_time.isoformat(),
        "method": request.method,
        "endpoint": request.url.path,
        "api_key": request.headers.get("x-api-key", "none"),
        "status_code": response.status_code,
    })
    
    return response