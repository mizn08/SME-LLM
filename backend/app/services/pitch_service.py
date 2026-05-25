"""Sales pitch / bank letter generator (EN + BM)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.services import data_processor, forecast_service


def generate_pitch(
    db: Session,
    sme_id: int,
    lang: str = "en",
    tone: str = "formal",
) -> str:
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        return "SME not found."

    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    fc = forecast_service.forecast_runway(db, sme_id)
    runway = float(fc.get("runway_days_est") or kpis.get("days_cash_on_hand", 0))
    revenue = kpis.get("revenue_mtd_rm", 0)
    burn = kpis.get("burn_rate_monthly_rm", 0)
    ratio = kpis.get("current_ratio", 1)

    greeting = "Yang Berhormat / Puan / Encik," if tone == "formal" else "Hello,"
    if lang == "ms":
        greeting = "Yang Berhormat / Puan / Encik," if tone == "formal" else "Assalamualaikum dan salam sejahtera,"

    if lang == "ms":
        body = f"""{greeting}

Saya menulis bagi pihak {sme.business_name}, sebuah perniagaan dalam sektor {sme.industry}.

**Ringkasan kewangan**
- Hasil bulan semasa: RM {revenue:,.0f}
- Belanja bulanan (anggaran): RM {burn:,.0f}
- Nisbah kecairan: {ratio:.2f}
- Anggaran hari tunai: {runway:.0f}

Kami memohon pertimbangan untuk pembiayaan / geran yang menyokong pertumbuhan berterusan, terutamanya untuk digitalisasi dan aliran tunai operasi.

Terima kasih atas pertimbangan anda.

Hormat kami,
{sme.business_name}
"""
    else:
        closings = "Respectfully yours," if tone == "formal" else "Best regards,"
        body = f"""{greeting}

I am writing on behalf of **{sme.business_name}**, operating in the **{sme.industry}** sector in Malaysia.

**Financial snapshot (from uploaded transactions)**
- Revenue (current month): RM {revenue:,.0f}
- Estimated monthly burn: RM {burn:,.0f}
- Liquidity ratio: {ratio:.2f}
- Estimated cash runway: {runway:.0f} days

We seek your consideration for financing or grant support to strengthen working capital, fund essential equipment, and sustain operations while preserving cash flow.

We are happy to provide bank statements, SSM registration, and management accounts upon request.

{closings}
{sme.business_name}
"""

    return body.strip()
