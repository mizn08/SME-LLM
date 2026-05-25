"""Static Malaysian lender directory with eligibility matching."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.schemas import LenderItem
from app.services import data_processor

_LENDERS: list[LenderItem] = [
    LenderItem(
        id="atome",
        name="Atome",
        product_type="bnpl",
        max_amount_rm=50000,
        typical_rate_label="0% if paid on time (merchant fees)",
        min_revenue_rm=5000,
        islamic_compliant=False,
        apply_url="https://www.atome.my/",
        notes="Pay in 3 for retail and equipment partners.",
    ),
    LenderItem(
        id="grab_paylater",
        name="Grab PayLater",
        product_type="bnpl",
        max_amount_rm=30000,
        typical_rate_label="0–18% p.a. depending on tenure",
        min_revenue_rm=3000,
        islamic_compliant=False,
        apply_url="https://www.grab.com/my/paylater/",
        notes="4-month instalments for approved merchants.",
    ),
    LenderItem(
        id="shopee_spay",
        name="Shopee SPayLater",
        product_type="bnpl",
        max_amount_rm=20000,
        typical_rate_label="Tiered fees up to 12 months",
        min_revenue_rm=2000,
        islamic_compliant=False,
        apply_url="https://shopee.com.my/",
        notes="Best for inventory and marketplace purchases.",
    ),
    LenderItem(
        id="tekun",
        name="TEKUN Nasional",
        product_type="micro_credit",
        max_amount_rm=50000,
        typical_rate_label="From 4% p.a. (conventional)",
        min_revenue_rm=0,
        bumiputera_preferred=True,
        islamic_compliant=False,
        apply_url="https://www.tekun.gov.my/",
        notes="Micro-financing for Bumiputera SMEs.",
    ),
    LenderItem(
        id="bank_rakyat",
        name="Bank Rakyat",
        product_type="islamic",
        max_amount_rm=250000,
        typical_rate_label="Islamic financing — profit rate",
        min_revenue_rm=10000,
        islamic_compliant=True,
        apply_url="https://www.bankrakyat.com.my/",
        notes="Shariah-compliant working capital and asset financing.",
    ),
    LenderItem(
        id="cgc",
        name="Credit Guarantee Corp (CGC)",
        product_type="micro_credit",
        max_amount_rm=500000,
        typical_rate_label="Guaranteed loans via partner banks",
        min_revenue_rm=50000,
        islamic_compliant=False,
        apply_url="https://www.cgc.com.my/",
        notes="For SMEs needing bank loans with partial guarantee.",
    ),
    LenderItem(
        id="agrobank",
        name="Agrobank",
        product_type="islamic",
        max_amount_rm=200000,
        typical_rate_label="Islamic agri financing",
        min_revenue_rm=5000,
        islamic_compliant=True,
        apply_url="https://www.agrobank.com.my/",
        notes="Agriculture and agrifood value chain.",
    ),
]


def list_all_lenders(islamic_only: bool = False) -> list[LenderItem]:
    if islamic_only:
        return [l for l in _LENDERS if l.islamic_compliant]
    return list(_LENDERS)


def matched_lenders(db: Session, sme_id: int, islamic_only: bool = False) -> list[LenderItem]:
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    revenue = float(kpis.get("revenue_mtd_rm", 0)) * 12  # annualise rough

    matched: list[LenderItem] = []
    for lender in _LENDERS:
        if islamic_only and not lender.islamic_compliant:
            continue
        if lender.min_revenue_rm and revenue < lender.min_revenue_rm * 0.5:
            continue
        if lender.bumiputera_preferred and sme and not getattr(sme, "bumiputera_flag", False):
            continue
        matched.append(lender)
    return matched if matched else list_all_lenders(islamic_only)[:3]
