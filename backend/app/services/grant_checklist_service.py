"""Grant application document checklists."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.gov_aid import GovFinancialAid
from app.schemas import ChecklistItem, GrantChecklistResponse

_DEFAULT_CHECKLIST = [
    ChecklistItem(document="SSM business registration (Form 9/13)", required=True, tip="Must be active"),
    ChecklistItem(document="Latest 6 months bank statements", required=True),
    ChecklistItem(document="Management accounts / P&L", required=True),
    ChecklistItem(document="Company profile & project proposal", required=True),
    ChecklistItem(document="Quotations for equipment/software", required=False, tip="If claiming capex"),
    ChecklistItem(document="Bumiputera certificate", required=False, tip="If scheme requires Bumiputera status"),
]


_SCHEME_EXTRAS: dict[str, list[ChecklistItem]] = {
    "MDEC": [
        ChecklistItem(document="Digital adoption plan", required=True, tip="Align with MDEC SAG categories"),
        ChecklistItem(document="Vendor invoices (cloud/SaaS)", required=False),
    ],
    "MATRADE": [
        ChecklistItem(document="Export market research", required=True),
        ChecklistItem(document="Proforma invoices from buyers", required=False),
    ],
    "TEKUN": [
        ChecklistItem(document="IC of directors / guarantors", required=True),
        ChecklistItem(document="Business premise photos", required=False),
    ],
}


def get_checklist(db: Session, grant_id: int) -> GrantChecklistResponse | None:
    row = db.query(GovFinancialAid).filter(GovFinancialAid.id == grant_id).first()
    if not row:
        return None

    items = list(_DEFAULT_CHECKLIST)
    agency_key = (row.agency or "")[:20].upper()
    for key, extras in _SCHEME_EXTRAS.items():
        if key in (row.agency or "").upper() or key in (row.scheme_name or "").upper():
            items.extend(extras)
            break

    deadline = "Rolling — check portal for intake windows"
    if row.digitalisation_only:
        deadline = "MDEC intake: typically quarterly"

    return GrantChecklistResponse(
        scheme_id=row.id,
        scheme_name=row.scheme_name,
        agency=row.agency,
        deadline_label=deadline,
        contact_email=f"info@{row.agency.lower().replace(' ', '')}.gov.my" if row.agency else None,
        contact_phone="1300-888-000",
        apply_url=f"https://www.{row.agency.split()[0].lower()}.gov.my" if row.agency else None,
        checklist=items,
    )
