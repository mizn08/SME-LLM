"""Additional feature endpoints: spending, BNPL sim, timeline, draft, guided, bank summary."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.application_tracker import ApplicationTracker
from app.models.prediction import PredictionLog
from app.models.sme import SMEProfile
from app.schemas import (
    ApplicationDraftRequest,
    ApplicationDraftResponse,
    BankStatementSummaryResponse,
    BnplRepaymentRequest,
    BnplRepaymentResponse,
    FinancingTimelineResponse,
    GuidedAdvisoryRequest,
    GuidedAdvisoryResponse,
    RepaymentMonth,
    SpendingCategoryItem,
    SpendingCategoryResponse,
    TimelineItem,
)
from app.services import (
    application_draft_service,
    bank_statement_service,
    data_processor,
    guided_advisory_service,
)

router = APIRouter(tags=["features"])


@router.get("/sme/{sme_id}/spending-categories", response_model=SpendingCategoryResponse)
def spending_categories(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    df = data_processor.load_transactions_df(db, sme_id)
    rows = data_processor.spending_by_category(df)
    total = sum(r["amount_rm"] for r in rows)
    return SpendingCategoryResponse(
        sme_id=sme_id,
        categories=[SpendingCategoryItem(**r) for r in rows],
        total_expense_rm=round(total, 2),
    )


@router.post("/bnpl/repayment", response_model=BnplRepaymentResponse)
def bnpl_repayment(body: BnplRepaymentRequest):
    principal = body.amount_rm
    monthly_rate = body.annual_rate_pct / 100 / 12
    n = body.tenure_months
    if monthly_rate <= 0:
        payment = principal / n
    else:
        payment = principal * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)

    schedule: list[RepaymentMonth] = []
    balance = principal
    total_interest = 0.0
    for m in range(1, n + 1):
        interest = balance * monthly_rate
        princ = payment - interest
        balance = max(0, balance - princ)
        total_interest += interest
        schedule.append(
            RepaymentMonth(
                month=m,
                payment_rm=round(payment, 2),
                principal_rm=round(princ, 2),
                interest_rm=round(interest, 2),
                balance_rm=round(balance, 2),
            )
        )

    return BnplRepaymentResponse(
        amount_rm=principal,
        annual_rate_pct=body.annual_rate_pct,
        tenure_months=n,
        monthly_payment_rm=round(payment, 2),
        total_interest_rm=round(total_interest, 2),
        total_cost_rm=round(principal + total_interest, 2),
        schedule=schedule,
    )


@router.get("/sme/{sme_id}/financing-timeline", response_model=FinancingTimelineResponse)
def financing_timeline(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")

    items: list[TimelineItem] = []
    preds = (
        db.query(PredictionLog)
        .filter(PredictionLog.sme_id == sme_id)
        .order_by(PredictionLog.created_at.desc())
        .limit(20)
        .all()
    )
    for p in preds:
        amt = float((p.request_payload or {}).get("purchase_amount", 0))
        items.append(
            TimelineItem(
                id=f"pred-{p.id}",
                kind="prediction",
                title=p.product_name,
                subtitle=p.recommendation_type,
                status="completed",
                amount_rm=amt,
                created_at=p.created_at.isoformat(),
            )
        )

    apps = (
        db.query(ApplicationTracker)
        .filter(ApplicationTracker.sme_id == sme_id)
        .order_by(ApplicationTracker.updated_at.desc())
        .all()
    )
    for a in apps:
        items.append(
            TimelineItem(
                id=f"app-{a.id}",
                kind="application",
                title=a.product_name,
                subtitle=a.product_type,
                status=a.status,
                amount_rm=None,
                created_at=a.created_at.isoformat(),
            )
        )

    items.sort(key=lambda x: x.created_at, reverse=True)
    return FinancingTimelineResponse(sme_id=sme_id, items=items)


@router.post("/sme/{sme_id}/application-draft", response_model=ApplicationDraftResponse)
def application_draft(
    sme_id: int, body: ApplicationDraftRequest, db: Session = Depends(get_db)
):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    draft = application_draft_service.generate_draft(
        db,
        sme_id,
        body.product_type,
        body.purchase_amount,
        body.purchase_category,
    )
    if draft.get("error"):
        raise HTTPException(404, draft["error"])
    return ApplicationDraftResponse(sme_id=sme_id, draft=draft)


@router.post("/guided-advisory", response_model=GuidedAdvisoryResponse)
def guided_advisory(body: GuidedAdvisoryRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == body.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return guided_advisory_service.run_guided_advisory(db, body)


@router.get("/sme/{sme_id}/bank-statement-summary", response_model=BankStatementSummaryResponse)
def bank_statement_summary(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    data = bank_statement_service.summarize_statement(db, sme_id)
    return BankStatementSummaryResponse(**data)
