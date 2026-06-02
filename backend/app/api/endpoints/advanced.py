from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import RequirementParseResponse, RlAdviseRequest, RlAdviseResponse
from app.services import (
    document_ai_service,
    llm_finetune_service,
    ocr_service,
    requirement_parser_service,
    rl_policy_service,
)

router = APIRouter(tags=["v3-advanced"])


@router.post("/rl/advise", response_model=RlAdviseResponse)
def rl_advise(payload: RlAdviseRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    if payload.reward is not None and payload.action:
        rl_policy_service.update_policy(
            db,
            sme_id=payload.sme_id,
            purchase_amount=payload.purchase_amount,
            action=payload.action,
            reward=payload.reward,
        )
    out = rl_policy_service.select_action(db, payload.sme_id, payload.purchase_amount)
    return RlAdviseResponse(**out)


@router.get("/llm/finetune/status")
def finetune_status():
    return llm_finetune_service.finetune_status()


@router.post("/llm/generate")
def llm_generate(prompt: str, max_tokens: int = 256):
    return llm_finetune_service.generate_local(prompt, max_tokens=max_tokens)


@router.post("/upload-invoice")
async def upload_invoice(
    sme_id: Annotated[int, Form()],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    raw = await file.read()
    result = document_ai_service.extract_structured(raw)
    if result.get("error") and not result.get("parsed_rows"):
        raise HTTPException(400, result["error"])
    return {
        "sme_id": sme_id,
        "ocr": result,
        "csv_preview": ocr_service.rows_to_csv_bytes(result.get("parsed_rows", [])).decode("utf-8")[:2000],
        "hint": "Import parsed rows via Upload CSV after reviewing dates and amounts.",
    }


@router.post("/requirements/parse", response_model=RequirementParseResponse)
async def parse_requirements(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith((".pdf", ".txt", ".docx")):
        raise HTTPException(400, "Supported file types: .pdf, .txt, .docx")
    raw = await file.read()
    parsed = requirement_parser_service.parse_requirement_file(raw, filename)
    return RequirementParseResponse(**parsed)
