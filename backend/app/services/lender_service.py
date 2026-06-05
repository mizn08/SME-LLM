"""Malaysian lender directory — static + DB catalog, eligibility, smart search."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.bnpl import BNPLOffer
from app.models.credit_line import CreditLineOffer
from app.models.gov_aid import GovFinancialAid
from app.models.sme import SMEProfile
from app.schemas import LenderItem
from app.services import data_processor

# Synonyms for search (query token -> extra terms to match)
_SEARCH_SYNONYMS: dict[str, list[str]] = {
    "madani": ["madani", "harapan", "pmks", "kusukop", "ekonomi"],
    "grant": ["grant", "geran", "gov", "scheme", "voucher", "subsidy"],
    "geran": ["grant", "geran", "scheme"],
    "digital": ["digital", "digitalisation", "mdec", "tech", "software"],
    "mdec": ["mdec", "digital", "digitalisation"],
    "mara": ["mara", "bumiputera"],
    "tekun": ["tekun", "micro", "pemulih"],
    "islamic": ["islamic", "shariah", "musharakah", "murabahah", "bank islam", "bank rakyat"],
    "bnpl": ["bnpl", "pay later", "paylater", "installment", "atome", "grab", "spay"],
    "loan": ["loan", "credit", "financing", "micro"],
    "cgc": ["cgc", "guarantee"],
}

_STATIC_LENDERS: list[LenderItem] = [
    LenderItem(
        id="atome",
        name="Atome",
        product_type="bnpl",
        max_amount_rm=50000,
        typical_rate_label="0% if paid on time (merchant fees)",
        min_revenue_rm=5000,
        islamic_compliant=False,
        apply_url="https://www.atome.my/",
        notes="BNPL pay in 3 for retail and equipment partners.",
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
        notes="BNPL instalments for approved merchants.",
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
        notes="BNPL for inventory and marketplace purchases.",
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
        notes="Micro-financing TEKUN Pembiayaan for Bumiputera SMEs.",
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
        id="bank_islam",
        name="Bank Islam SME Musharakah",
        product_type="islamic",
        max_amount_rm=500000,
        typical_rate_label="Islamic partnership financing",
        min_revenue_rm=12000,
        islamic_compliant=True,
        apply_url="https://www.bankislam.com/",
        notes="MicroCredit and Musharakah for Malaysian SMEs.",
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
        notes="CGC Digitalisation Facility and bank loan guarantees.",
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
    LenderItem(
        id="mara_static",
        name="MARA Pembiayaan",
        product_type="micro_credit",
        max_amount_rm=250000,
        typical_rate_label="Concessionary rates",
        min_revenue_rm=0,
        bumiputera_preferred=True,
        islamic_compliant=False,
        apply_url="https://www.mara.gov.my/",
        notes="MARA modal pusingan and entrepreneur financing.",
    ),
    LenderItem(
        id="madani_static",
        name="Geran Digital PMKS MADANI",
        product_type="grant",
        max_amount_rm=5000,
        typical_rate_label="Grant — no repayment",
        min_revenue_rm=0,
        islamic_compliant=False,
        apply_url="https://www.kuskop.gov.my/",
        notes="MADANI digital grant KUSKOP MDEC matching for PMKS micro SMEs.",
    ),
]


def _search_blob(item: LenderItem) -> str:
    parts = [
        item.name,
        item.product_type,
        item.typical_rate_label,
        item.notes,
        item.id.replace("_", " "),
    ]
    return " ".join(parts).lower()


def _expand_query_tokens(query: str) -> set[str]:
    raw = re.findall(r"[a-z0-9]+", (query or "").lower())
    tokens = set(raw)
    for t in list(tokens):
        for key, syns in _SEARCH_SYNONYMS.items():
            if t == key or t in key or key in t:
                tokens.update(syns)
    return tokens


def search_lenders(lenders: list[LenderItem], query: str) -> list[LenderItem]:
    """Fuzzy token search across name, type, notes."""
    tokens = _expand_query_tokens(query)
    if not tokens:
        return lenders
    scored: list[tuple[int, LenderItem]] = []
    for item in lenders:
        blob = _search_blob(item)
        score = sum(2 if t in item.name.lower() else 1 for t in tokens if t in blob)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    return [item for _, item in scored]


def _gov_to_lender(g: GovFinancialAid) -> LenderItem:
    islamic = "islamic" in (g.aid_type or "").lower() or "shariah" in (g.description or "").lower()
    return LenderItem(
        id=f"gov-{g.id}",
        name=g.scheme_name,
        product_type="grant" if g.aid_type == "grant" else "micro_credit",
        max_amount_rm=float(g.max_amount_rm) if g.max_amount_rm else None,
        typical_rate_label=g.interest_rate_label or "See scheme",
        min_revenue_rm=0,
        bumiputera_preferred=bool(g.requires_bumiputera),
        islamic_compliant=islamic,
        apply_url="https://www.gov.my/",
        notes=f"{g.agency}: {g.description or ''} {g.industry_keywords or ''}".strip(),
    )


def _bnpl_to_lender(b: BNPLOffer) -> LenderItem:
    return LenderItem(
        id=f"bnpl-{b.id}",
        name=b.name,
        product_type="bnpl",
        max_amount_rm=float(b.max_amount_rm),
        typical_rate_label=f"{b.effective_monthly_rate_pct}% / month effective",
        min_revenue_rm=0,
        islamic_compliant=False,
        apply_url="https://www.atome.my/",
        notes=f"BNPL by {b.provider}. Tenure up to {b.max_tenure_months} months.",
    )


def _credit_to_lender(c: CreditLineOffer) -> LenderItem:
    return LenderItem(
        id=f"credit-{c.id}",
        name=c.name,
        product_type="micro_credit",
        max_amount_rm=float(c.max_amount_rm),
        typical_rate_label=f"{c.annual_interest_rate_pct}% p.a.",
        min_revenue_rm=0,
        islamic_compliant="islamic" in (c.name or "").lower(),
        apply_url="https://www.cgc.com.my/",
        notes=f"{c.provider}: {c.eligibility_summary or ''}",
    )


def catalog_lenders(db: Session | None, *, islamic_only: bool = False) -> list[LenderItem]:
    """Full directory: static lenders + DB grants, BNPL, micro-credit."""
    seen: set[str] = set()
    out: list[LenderItem] = []

    def add(item: LenderItem) -> None:
        key = item.name.lower().strip()
        if key in seen:
            return
        if islamic_only and not item.islamic_compliant:
            return
        seen.add(key)
        out.append(item)

    for item in _STATIC_LENDERS:
        add(item)

    if db is not None:
        for g in db.query(GovFinancialAid).all():
            add(_gov_to_lender(g))
        for b in db.query(BNPLOffer).all():
            add(_bnpl_to_lender(b))
        for c in db.query(CreditLineOffer).all():
            add(_credit_to_lender(c))

    return out


def list_all_lenders(islamic_only: bool = False, db: Session | None = None) -> list[LenderItem]:
    return catalog_lenders(db, islamic_only=islamic_only)


def _is_eligible(
    lender: LenderItem,
    *,
    sme: SMEProfile | None,
    annual_revenue_rm: float,
    islamic_only: bool,
) -> bool:
    if islamic_only and not lender.islamic_compliant:
        return False
    if lender.min_revenue_rm and annual_revenue_rm < lender.min_revenue_rm * 0.5:
        return False
    if lender.bumiputera_preferred and sme and not getattr(sme, "bumiputera_flag", False):
        return False
    return True


def matched_lenders(
    db: Session,
    sme_id: int,
    islamic_only: bool = False,
    query: str | None = None,
) -> list[LenderItem]:
    catalog = catalog_lenders(db, islamic_only=False)
    if query and query.strip():
        found = search_lenders(catalog, query)
        if islamic_only:
            found = [l for l in found if l.islamic_compliant]
        return found

    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    revenue = float(kpis.get("revenue_mtd_rm", 0)) * 12

    matched: list[LenderItem] = []
    for lender in catalog:
        if _is_eligible(lender, sme=sme, annual_revenue_rm=revenue, islamic_only=islamic_only):
            matched.append(lender)

    if matched:
        return matched
    return catalog_lenders(db, islamic_only=islamic_only)[:8]
