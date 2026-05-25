from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.bnpl import BNPLOffer
from app.models.credit_line import CreditLineOffer
from app.models.gov_aid import GovFinancialAid
from app.models.sme import SMEProfile


def seed_reference_data(db: Session) -> None:
    if db.query(SMEProfile).first():
        return

    smes = [
        SMEProfile(
            business_name="Kopi Maju Enterprise",
            industry="F&B retail",
            bumiputera_flag=True,
            veteran_flag=False,
            annual_revenue_rm=840_000,
            employee_count=8,
        ),
        SMEProfile(
            business_name="Harapan Agro Supplies",
            industry="Agriculture wholesale",
            bumiputera_flag=True,
            veteran_flag=False,
            annual_revenue_rm=1_200_000,
            employee_count=15,
        ),
        SMEProfile(
            business_name="Urban Digital Services Sdn Bhd",
            industry="IT services",
            bumiputera_flag=False,
            veteran_flag=False,
            annual_revenue_rm=2_400_000,
            employee_count=22,
        ),
    ]
    db.add_all(smes)
    db.flush()

    from app.services.bnpl_catalog_service import load_catalog

    if db.query(BNPLOffer).count() == 0:
        bnpl = [
            BNPLOffer(
                name=p["plan_label"],
                provider=p["provider"],
                max_amount_rm=float(p["max_amount_rm"]),
                max_tenure_months=int(p["max_tenure_months"]),
                interest_free_days=int(p.get("interest_free_days", 0)),
                effective_monthly_rate_pct=float(p.get("effective_monthly_rate_pct", 0)),
                notes=p.get("description"),
            )
            for p in load_catalog()
        ]
        db.add_all(bnpl)

    credits = [
        CreditLineOffer(
            name="Bank Islam SME Musharakah",
            provider="Bank Islam",
            product_type="islamic",
            max_amount_rm=300_000,
            annual_interest_rate_pct=4.5,
            max_tenure_months=60,
            approval_speed_days=25,
            eligibility_summary="Shariah-compliant profit-sharing facility",
        ),
        CreditLineOffer(
            name="TEKUN Mikro",
            provider="TEKUN Nasional",
            product_type="micro_credit",
            max_amount_rm=50_000,
            annual_interest_rate_pct=6.0,
            max_tenure_months=36,
            approval_speed_days=21,
            eligibility_summary="Malaysian citizen SME; business > 6 months",
        ),
        CreditLineOffer(
            name="MARA Niaga",
            provider="MARA",
            product_type="micro_credit",
            max_amount_rm=200_000,
            annual_interest_rate_pct=5.5,
            max_tenure_months=60,
            approval_speed_days=30,
            eligibility_summary="Bumiputera SME focus sectors",
        ),
        CreditLineOffer(
            name="Agrobank Micro",
            provider="Agrobank",
            product_type="micro_credit",
            max_amount_rm=150_000,
            annual_interest_rate_pct=5.8,
            max_tenure_months=84,
            approval_speed_days=28,
            eligibility_summary="Agri-food and rural supply chain",
        ),
        CreditLineOffer(
            name="JHEV Vendor Financing",
            provider="JHEV",
            product_type="micro_credit",
            max_amount_rm=100_000,
            annual_interest_rate_pct=4.8,
            max_tenure_months=48,
            approval_speed_days=35,
            eligibility_summary="Veteran / veteran-related enterprises",
        ),
        CreditLineOffer(
            name="Funding Societies SME Term Loan",
            provider="Funding Societies",
            product_type="b2b_credit",
            max_amount_rm=500_000,
            annual_interest_rate_pct=12.0,
            max_tenure_months=24,
            approval_speed_days=10,
            eligibility_summary="P2P financing; credit assessment online",
        ),
        CreditLineOffer(
            name="UOB BizMoney",
            provider="UOB",
            product_type="b2b_credit",
            max_amount_rm=250_000,
            annual_interest_rate_pct=9.5,
            max_tenure_months=36,
            approval_speed_days=14,
            eligibility_summary="Secured/unsecured lines for SMEs",
        ),
        CreditLineOffer(
            name="Dropee Trade Credit",
            provider="Dropee",
            product_type="b2b_credit",
            max_amount_rm=80_000,
            annual_interest_rate_pct=11.0,
            max_tenure_months=12,
            approval_speed_days=7,
            eligibility_summary="B2B marketplace buyers",
        ),
    ]
    db.add_all(credits)

    gov = [
        GovFinancialAid(
            scheme_name="Geran Digital PMKS MADANI",
            agency="KUSKOP / MDEC",
            aid_type="grant",
            max_amount_rm=5_000,
            interest_rate_label="N/A (grant)",
            tenure_months=None,
            approval_speed_label="8–12 weeks",
            requires_bumiputera=False,
            requires_veteran=False,
            industry_keywords="digital,software,it",
            digitalisation_only=True,
            description="Matching grant for digital adoption by PMKS.",
        ),
        GovFinancialAid(
            scheme_name="MDEC Digitalisation Grant",
            agency="MDEC",
            aid_type="grant",
            max_amount_rm=50_000,
            interest_rate_label="N/A (grant)",
            tenure_months=None,
            approval_speed_label="2–3 months",
            requires_bumiputera=False,
            requires_veteran=False,
            industry_keywords="technology,services",
            digitalisation_only=True,
            description="Tech adoption matching for eligible digital projects.",
        ),
        GovFinancialAid(
            scheme_name="SME Digitalisation Initiative (Bumiputera)",
            agency="Various ministries",
            aid_type="grant",
            max_amount_rm=30_000,
            interest_rate_label="N/A (grant)",
            tenure_months=None,
            approval_speed_label="6–10 weeks",
            requires_bumiputera=True,
            requires_veteran=False,
            industry_keywords="",
            digitalisation_only=True,
            description="Digital tools voucher/grant for Bumiputera SMEs.",
        ),
        GovFinancialAid(
            scheme_name="TEKUN Pembiayaan Skim Pemulih",
            agency="TEKUN",
            aid_type="soft_loan",
            max_amount_rm=10_000,
            interest_rate_label="0% during moratorium",
            tenure_months=36,
            approval_speed_label="3–6 weeks",
            requires_bumiputera=False,
            requires_veteran=False,
            industry_keywords="",
            digitalisation_only=False,
            description="Soft loan for micro enterprises in targeted sectors.",
        ),
        GovFinancialAid(
            scheme_name="MARA Pembiayaan Modal Pusingan",
            agency="MARA",
            aid_type="soft_loan",
            max_amount_rm=250_000,
            interest_rate_label="Concessionary",
            tenure_months=60,
            approval_speed_label="4–8 weeks",
            requires_bumiputera=True,
            requires_veteran=False,
            industry_keywords="",
            digitalisation_only=False,
            description="Working capital for Bumiputera entrepreneurs.",
        ),
    ]
    db.add_all(gov)
    db.commit()
