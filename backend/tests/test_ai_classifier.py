"""
AI classifier tests — exercise the deterministic rule-based fallback.

OpenAI is not called because OPENAI_API_KEY is empty in test env.
"""
from app.services.ai_classifier import classify_lead


def test_overdue_accounts_classified():
    result = classify_lead({"accounts_overdue": True, "company_name": "ACME"})
    assert result["category"] == "Overdue Accounts"
    assert result["urgency"] == "urgent"
    assert "ACME" in result["summary"]


def test_confirmation_overdue_classified():
    result = classify_lead({"confirmation_overdue": True, "company_name": "X"})
    assert result["category"] == "Overdue Confirmation Statement"
    assert result["urgency"] == "high"


def test_newly_incorporated_classified():
    result = classify_lead({"newly_incorporated": True, "company_name": "Y"})
    assert result["category"] == "Newly Incorporated"


def test_construction_sic_classified():
    result = classify_lead({"sic_code": "43210", "company_name": "Build Co"})
    assert result["category"] == "CIS / Construction"


def test_landlord_sic_classified():
    result = classify_lead({"sic_code": "68209", "company_name": "Property Co"})
    assert result["category"] == "Landlord Tax"


def test_ecommerce_sic_classified():
    result = classify_lead({"sic_code": "47190", "company_name": "Shop"})
    assert result["category"] == "eCommerce Accounting"


def test_estimated_value_formatted():
    result = classify_lead({"estimated_value_gbp": 2500, "company_name": "X"})
    assert "£" in result["estimated_value"]
    assert "2,500" in result["estimated_value"]


def test_fallback_default_category():
    result = classify_lead({"company_name": "Unknown Inc"})
    assert result["category"] == "General Compliance"
    assert result["urgency"] == "low"
