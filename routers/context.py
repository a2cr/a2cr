import hmac
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import JSONResponse

from models.schemas import SaveRequest, SaveResponse, LoadResponse, ListItem, HandoffResponse
import services.context as ctx_service
from services.config import get_config, is_legacy_local_api_enabled
from services.exceptions import AppError


def require_legacy_local_api_enabled() -> None:
    if not is_legacy_local_api_enabled():
        raise AppError(
            "legacy_local_api_disabled",
            (
                "The legacy local SQLite WorkBaton API is disabled. "
                "Use the A2CR SaaS /api/v1 context API through the local stdio MCP wrapper."
            ),
            410,
        )


router = APIRouter(dependencies=[Depends(require_legacy_local_api_enabled)])


def build_resume_context_call(slot_name: str, slot_number: Optional[int] = None) -> str:
    return f'resume_context(slot_name="{slot_name}")'


def get_service_url() -> str:
    return os.environ.get("A2CR_SERVICE_URL", "http://localhost:8000")


def build_resume_prompt(
    slot_name: str,
    slot_number: Optional[int] = None,
    service_url: str = "http://localhost:8000",
) -> str:
    slot_number_hint = (
        f"Slot番号対応済みなら resume_context(slot_number={slot_number}) "
        "でも読み込めます。\n"
        if slot_number is not None
        else ""
    )
    return (
        f"A2CR service: {service_url}\n"
        "A2CR MCPツールを使ってください。HTTP APIを直接推測して呼び出さないでください。\n"
        f"まず {build_resume_context_call(slot_name, slot_number)} "
        "を実行して、A2CRから引き継ぎ文脈を読み込んでください。\n"
        f"{slot_number_hint}"
        "読み込み後は、作業に必要なプロジェクトファイルを通常通り参照して構いません。\n"
        "回答はこのメッセージの言語に合わせてください。"
    )


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
        content_dict=req.content.model_dump() if req.content else None,
        original_length=req.original_length,
        model_source=req.model_source,
        slot_number=req.slot_number,
        encrypted_content=req.encrypted_content.model_dump() if req.encrypted_content else None,
    )
    return SaveResponse(
        slot_name=result.slot_name,
        slot_number=result.slot_number,
        expires_at=result.expires_at,
        compressed_tokens=result.compressed_tokens,
        saved_tokens=result.saved_tokens,
        resume_context_call=build_resume_context_call(result.slot_name, result.slot_number),
        resume_prompt=build_resume_prompt(
            result.slot_name,
            slot_number=result.slot_number,
            service_url=get_service_url(),
        ),
    )


@router.get("/v1/context/list")
def list_contexts(_: None = Depends(verify_api_key)) -> list[ListItem]:
    results = ctx_service.list_contexts()
    return [
        ListItem(
            slot_name=r.slot_name,
            slot_number=r.slot_number,
            encryption_mode=r.encryption_mode,
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


@router.get("/v1/context/slot/{slot_number}")
def load_by_slot_number(slot_number: int, _: None = Depends(verify_api_key)) -> LoadResponse:
    result = ctx_service.load_context(slot_number=slot_number)
    return LoadResponse(
        slot_name=result.slot_name,
        slot_number=result.slot_number,
        encryption_mode=result.encryption_mode,
        content=result.content,
        encrypted_content=result.encrypted_content,
        expires_at=result.expires_at,
        compressed_tokens=result.compressed_tokens,
        model_source=result.model_source,
        load_count=result.load_count,
    )


@router.get("/v1/context/{slot_name}")
def load(slot_name: str, _: None = Depends(verify_api_key)) -> LoadResponse:
    result = ctx_service.load_context(slot_name=slot_name)
    return LoadResponse(
        slot_name=result.slot_name,
        slot_number=result.slot_number,
        encryption_mode=result.encryption_mode,
        content=result.content,
        encrypted_content=result.encrypted_content,
        expires_at=result.expires_at,
        compressed_tokens=result.compressed_tokens,
        model_source=result.model_source,
        load_count=result.load_count,
    )


@router.delete("/v1/context/{slot_name}")
def delete(slot_name: str, _: None = Depends(verify_api_key)):
    ctx_service.delete_context(slot_name)
    return {"message": "deleted"}
