"""RAG intent routing: educational vs personal financing questions."""

from app.services.rag_service import (
    _is_educational_or_survey,
    _is_financing_question,
    _is_personal_business_question,
)


def test_bnpl_survey_detected_as_educational():
    q = (
        "Category 6: Advanced\n"
        "16. How does a flat fee BNPL model differ from percentage-of-sale?\n"
        "17. What SLAs do providers offer?\n"
        "18. How do refunds work?\n"
        "19. Impact on LTV and CAC?\n"
    )
    assert _is_educational_or_survey(q)


def test_sanitized_single_line_still_educational():
    from app.services.guardrail_service import sanitize_text

    q = (
        "16. How does flat fee BNPL differ from percentage? "
        "17. What SLAs? 18. Refunds? 19. LTV and CAC?"
    )
    assert _is_educational_or_survey(sanitize_text(q))


def test_us_focused_list_educational():
    q = "I am testing with this list of general US-focused BNPL questions about SLAs and refunds."
    assert _is_educational_or_survey(q)


def test_personal_financing_not_educational():
    q = "Should I use BNPL for my business to buy RM 50000 equipment?"
    assert _is_personal_business_question(q)
    assert not _is_educational_or_survey(q)
    assert _is_financing_question(q)


def test_simple_open_bnpl_question():
    q = "What is BNPL and how does it work for retailers?"
    assert not _is_educational_or_survey(q)
    assert _is_financing_question(q)
