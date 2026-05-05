from fastapi import APIRouter

router = APIRouter()


@router.get("/v1/health")
@router.get("/api/v1/health")
def health():
    return {"status": "ok"}
