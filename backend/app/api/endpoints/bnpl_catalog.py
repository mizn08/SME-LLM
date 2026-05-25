from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import bnpl_catalog_service, marketplace_service

router = APIRouter(tags=["bnpl"])


@router.get("/bnpl/providers")
def bnpl_providers():
    providers = bnpl_catalog_service.list_bnpl_providers()
    return {"providers": providers, "count": len(providers)}


@router.get("/bnpl/plan-choices")
def bnpl_plan_choices():
    return {"choices": bnpl_catalog_service.plan_choices()}


@router.get("/marketplace/providers")
def marketplace_providers(bnpl_only: bool = False):
    return {"providers": marketplace_service.list_providers(bnpl_only=bnpl_only)}


@router.post("/marketplace/seed-offers")
def seed_offers(db: Session = Depends(get_db)):
    """Populate bnpl_offer from catalog (insert if empty, else sync missing)."""
    n = bnpl_catalog_service.seed_bnpl_offers(db)
    if n:
        return {"status": "ok", "inserted": n, "synced": 0}
    sync = bnpl_catalog_service.sync_bnpl_offers(db)
    return {"status": "ok", "inserted": 0, "synced": sync["added"], "total_offers": sync["total"]}
