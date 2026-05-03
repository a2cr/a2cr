import hmac
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import JSONResponse

from models.schemas import SaveRequest, SaveResponse, LoadResponse, ListItem, HandoffResponse
import services.context as ctx_service
from services.config import get_config
from services.exceptions import AppError

router = APIRouter()


def verify_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_api_key", "message": "Invalid API key"},
        )
    expected = get_config().api_key
    if not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_api_key", "message": "Invalid API key"},
        )


@router.post("/v1/context/save", status_code=201)
def save(req: SaveRequest, _: None = Depends(verify_api_key)) -> SaveResponse:
    result = ctx_service.save_context(
        slot_name=req.slot_name,
        content_dict=req.content.model_dump(),
        original_length=req.original_length,
        model_source=req.model_source,
    )
    return SaveResponse(
        slot_name=result.slot_name,
        expires_at=result.expires_at,
        compressed_tokens=result.compressed_tokens,
        saved_tokens=result.saved_tokens,
    )


@router.get("/v1/context/list")
def list_contexts(_: None = Depends(verify_api_key)) -> list[ListItem]:
    results = ctx_service.list_contexts()
    return [
        ListItem(
            slot_name=r.slot_name,
            expires_at=r.expires_at,
            updated_at=r.updated_at,
            size_bytes=r.size_bytes,
            compressed_tokens=r.compressed_tokens,
            model_source=r.model_source,
        )
        for r in results
    ]


@router.get("/v1/context/{slot_name}/handoff")
def get_handoff(slot_name: str, _: None = Depends(verify_api_key)) -> HandoffResponse:
    result = ctx_service.get_handoff(slot_name)
    return HandoffResponse(slot_name=result.slot_name, handoff_text=result.handoff_text)


@router.get("/v1/context/{slot_name}")
def load(slot_name: str, _: None = Depends(verify_api_key)) -> LoadResponse:
    result = ctx_service.load_context(slot_name)
    return LoadResponse(
        slot_name=result.slot_name,
        content=result.content,
        expires_at=result.expires_at,
        compressed_tokens=result.compressed_tokens,
        model_source=result.model_source,
        load_count=result.load_count,
    )


@router.delete("/v1/context/{slot_name}")
def delete(slot_name: str, _: None = Depends(verify_api_key)):
    ctx_service.delete_context(slot_name)
    return {"message": "deleted"}
