from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.config import is_web_runtime
from services.db import get_web_engine
from services.schema_readiness import check_schema_readiness

router = APIRouter()


@router.get("/v1/health")
@router.get("/api/v1/health")
def health():
    return {"status": "ok"}


@router.get("/api/v1/health/readiness")
def readiness():
    if not is_web_runtime():
        return {"status": "ok", "ready": True, "checks": {"runtime": True}}

    result = check_schema_readiness(get_web_engine())
    body = {
        "status": "ok" if result.ready else "not_ready",
        "ready": result.ready,
        "checks": result.checks,
        "missing": result.missing,
    }
    if result.ready:
        return body
    return JSONResponse(status_code=503, content=body)
