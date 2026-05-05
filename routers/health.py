from fastapi import APIRouter

router = APIRouter()


@router.get("/v1/health")
def health():
    return {"status": "🟢 正常稼働中"}
