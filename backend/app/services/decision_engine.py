"""Rule + ML hybrid decision engine for BNPL vs micro-credit vs grants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.bnpl import BNPLOffer
from app.models.credit_line import CreditLineOffer
from app.models.gov_aid import GovFinancialAid
from app.models.sme import SMEProfile
from app.services import ml_predictor


@dataclass
class DecisionResult:
    recommendation_type: str
    product_name: str
    explanation: str
    cash_preserved_rm: float
    additional_cost_rm: float
    confidence: float
    shap_values: list[dict[str, Any]]
    ml_probability: float


def _eligible_gov_schemes(
    db: Session,
    sme: SMEProfile,
    purchase_category: str,
) -> list[GovFinancialAid]:
    schemes = db.query(GovFinancialAid).all()
    cat = purchase_category.lower()
    digital_hit = any(
        k in cat for k in ("digital", "software", "it", "cloud", "computer", "tech", "erp")
    )
    eligible: list[GovFinancialAid] = []
    for g in schemes:
        if g.requires_bumiputera and not sme.bumiputera_flag:
            continue
        if g.requires_veteran and not sme.veteran_flag:
            continue
        if g.digitalisation_only and not digital_hit:
            continue
        if g.industry_keywords:
            keys = [k.strip().lower() for k in g.industry_keywords.split(",") if k.strip()]
            if keys and not any(k in sme.industry.lower() or k in cat for k in keys):
                continue
        eligible.append(g)
    return eligible


def _bnpl_effective_cost(offer: BNPLOffer, amount: float, tenure_months: int) -> float:
    if tenure_months <= 0:
        tenure_months = offer.max_tenure_months
    rate = offer.effective_monthly_rate_pct / 100.0
    if offer.interest_free_days >= 30 * tenure_months:
        return 0.0
    return float(amount * rate * tenure_months)


def _credit_cost(offer: CreditLineOffer, amount: float, tenure_months: int) -> float:
    r = offer.annual_interest_rate_pct / 100.0
    return float(amount * r * (tenure_months / 12.0))


def decide(
    db: Session,
    sme: SMEProfile,
    kpis: dict[str, float],
    purchase_amount: float,
    purchase_category: str,
    selected_bnpl_plan: Optional[str],
) -> DecisionResult:
    features = ml_predictor.build_feature_vector(kpis, purchase_amount, purchase_category)
    ml_prob, _dbg = ml_predictor.predict_probability(features)
    shap = ml_predictor.compute_shap_top3(features)
    burn = max(kpis.get("burn_rate_monthly_rm", 1.0), 1.0)
    purchase_to_burn = purchase_amount / burn
    days_cash = kpis.get("days_cash_on_hand", 0.0)
    net_cash = float(kpis.get("net_operating_cash_rm", 0.0))

    eligible_grants = [
        g
        for g in _eligible_gov_schemes(db, sme, purchase_category)
        if (g.aid_type or "").lower() == "grant"
    ]

    if net_cash < 0 and days_cash < 30:
        if eligible_grants:
            best_grant = max(eligible_grants, key=lambda g: float(g.max_amount_rm or 0))
            cap = float(best_grant.max_amount_rm or 0)
            if purchase_amount <= cap:
                return DecisionResult(
                    recommendation_type="Grant",
                    product_name=best_grant.scheme_name,
                    explanation=(
                        f"Your 90-day net cash is RM {net_cash:,.2f} with {days_cash:.0f} days runway. "
                        f"{best_grant.scheme_name} (max RM {cap:,.0f}) is non-repayable and fits your "
                        f"RM {purchase_amount:,.0f} {purchase_category} purchase without adding monthly debt."
                    ),
                    cash_preserved_rm=float(purchase_amount),
                    additional_cost_rm=0.0,
                    confidence=0.85,
                    shap_values=shap,
                    ml_probability=round(ml_prob, 4),
                )
            if cap >= purchase_amount * 0.25:
                gap = purchase_amount - cap
                return DecisionResult(
                    recommendation_type="Grant",
                    product_name=best_grant.scheme_name,
                    explanation=(
                        f"90-day net cash RM {net_cash:,.2f}; runway {days_cash:.0f} days. "
                        f"Apply for {best_grant.scheme_name} (up to RM {cap:,.0f}) first, then bridge "
                        f"RM {gap:,.0f} only after cash stabilises — avoid BNPL while burn is "
                        f"RM {burn:,.0f}/month."
                    ),
                    cash_preserved_rm=cap,
                    additional_cost_rm=0.0,
                    confidence=0.75,
                    shap_values=shap,
                    ml_probability=round(ml_prob, 4),
                )
        return DecisionResult(
            recommendation_type="Hold",
            product_name="Defer purchase — stabilise cash",
            explanation=(
                f"90-day net cash RM {net_cash:,.2f} and {days_cash:.0f} days runway. "
                f"Monthly burn RM {burn:,.2f} — adding instalments would strain cash further. "
                "Improve inflows or cut top expense categories before financing."
            ),
            cash_preserved_rm=0.0,
            additional_cost_rm=0.0,
            confidence=0.8,
            shap_values=shap,
            ml_probability=round(ml_prob, 4),
        )

    # For smaller purchases with enough runway, prefer cash to avoid needless financing.
    if ml_prob < 0.5 or (purchase_to_burn <= 0.35 and days_cash >= 21):
        return DecisionResult(
            recommendation_type="Cash",
            product_name="Pay with operating cash",
            explanation=(
                "Modelled financing need is below threshold. Paying cash avoids fees "
                "and keeps liabilities unchanged based on your current liquidity profile."
            ),
            cash_preserved_rm=0.0,
            additional_cost_rm=0.0,
            confidence=round(1.0 - ml_prob, 3),
            shap_values=shap,
            ml_probability=round(ml_prob, 4),
        )

    eligible_grants = [
        g
        for g in _eligible_gov_schemes(db, sme, purchase_category)
        if (g.aid_type or "").lower() == "grant"
    ]
    if eligible_grants:
        best_grant = max(eligible_grants, key=lambda g: float(g.max_amount_rm or 0))
        cap = float(best_grant.max_amount_rm or 0)
        if purchase_amount <= cap:
            return DecisionResult(
                recommendation_type="Grant",
                product_name=best_grant.scheme_name,
                explanation=(
                    f"You appear eligible for {best_grant.scheme_name} (max RM {cap:,.0f}). "
                    "Grants preserve cash for operations — verify documents with the agency."
                ),
                cash_preserved_rm=float(purchase_amount),
                additional_cost_rm=0.0,
                confidence=round(min(0.95, 0.55 + ml_prob / 4), 3),
                shap_values=shap,
                ml_probability=round(ml_prob, 4),
            )

    bnpl_offers = [o for o in db.query(BNPLOffer).all() if purchase_amount <= o.max_amount_rm]
    credit_offers = db.query(CreditLineOffer).all()

    chosen_bnpl: Optional[BNPLOffer] = None
    if selected_bnpl_plan:
        for o in bnpl_offers:
            if o.name == selected_bnpl_plan or o.provider in selected_bnpl_plan:
                chosen_bnpl = o
                break
    if chosen_bnpl is None and bnpl_offers:
        chosen_bnpl = min(
            bnpl_offers,
            key=lambda o: _bnpl_effective_cost(o, purchase_amount, min(6, o.max_tenure_months)),
        )

    tenure_guess = 6
    if chosen_bnpl:
        tenure_guess = min(tenure_guess, chosen_bnpl.max_tenure_months)

    days_ok = kpis.get("days_cash_on_hand", 0) >= tenure_guess * 7

    candidates: list[tuple[str, str, float, float, str]] = []
    if chosen_bnpl:
        cost = _bnpl_effective_cost(chosen_bnpl, purchase_amount, tenure_guess)
        monthly = (purchase_amount + cost) / max(tenure_guess, 1)
        avg_rev = burn * float(kpis.get("current_ratio", 1))  # proxy if no revenue in kpis
        if days_cash < 45 and monthly > max(burn * 0.1, 500):
            pass  # skip BNPL — unaffordable
        else:
            candidates.append(
                (
                    "BNPL",
                    chosen_bnpl.name,
                    cost,
                    float(purchase_amount) * 0.6,
                    (
                        f"Spreads RM {purchase_amount:,.0f} over {tenure_guess} months "
                        f"(~RM {monthly:,.0f}/mo). Extra financing cost RM {cost:,.2f}."
                    ),
                )
            )
    for c in credit_offers:
        if purchase_amount > c.max_amount_rm:
            continue
        cost = _credit_cost(c, purchase_amount, min(tenure_guess, c.max_tenure_months))
        candidates.append(
            (
                "MicroCredit",
                c.name,
                cost,
                float(purchase_amount) * 0.4,
                f"{c.provider} line—compare APR and covenant requirements.",
            )
        )

    if not candidates:
        return DecisionResult(
            recommendation_type="Cash",
            product_name="Pay with operating cash",
            explanation="No suitable BNPL or micro-credit product found for this amount.",
            cash_preserved_rm=0.0,
            additional_cost_rm=0.0,
            confidence=0.55,
            shap_values=shap,
            ml_probability=round(ml_prob, 4),
        )

    def sort_key(x: tuple[str, str, float, float, str]) -> float:
        _, _, cost, cash_p, _ = x
        return cost - 0.0001 * cash_p

    best = min(candidates, key=sort_key)
    rec_type, name, add_cost, cash_preserved, blurb = best

    if not days_ok and rec_type == "MicroCredit":
        alt = next((c for c in candidates if c[0] == "BNPL"), None)
        if alt:
            rec_type, name, add_cost, cash_preserved, blurb = alt

    explanation = (
        f"{blurb} Estimated incremental financing cost RM {add_cost:,.2f} vs paying upfront. "
        f"Days cash on hand: {kpis.get('days_cash_on_hand', 0):.1f}."
    )

    return DecisionResult(
        recommendation_type=rec_type,
        product_name=name,
        explanation=explanation,
        cash_preserved_rm=round(cash_preserved, 2),
        additional_cost_rm=round(add_cost, 2),
        confidence=round(min(0.95, 0.5 + ml_prob / 3), 3),
        shap_values=shap,
        ml_probability=round(ml_prob, 4),
    )
