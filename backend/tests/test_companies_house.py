"""Companies House parsing tests — no network."""
from datetime import date, timedelta

from app.services.companies_house import (
    extract_company_fields,
    extract_compliance_fields,
    parse_date,
)


def _profile_fixture(overrides: dict | None = None) -> dict:
    today = date.today()
    profile = {
        "company_number": "12345678",
        "company_name": "ACME LIMITED",
        "company_status": "active",
        "type": "ltd",
        "sic_codes": ["43210"],
        "date_of_creation": "2020-03-15",
        "registered_office_address": {
            "address_line_1": "1 Test Street",
            "locality": "London",
            "postal_code": "SW1A 1AA",
            "country": "England",
        },
        "accounts": {
            "next_due": (today - timedelta(days=10)).isoformat(),  # overdue
            "last_accounts": {"made_up_to": "2023-12-31"},
        },
        "confirmation_statement": {
            "next_due": (today + timedelta(days=30)).isoformat(),
            "last_made_up_to": "2024-03-15",
        },
        "has_charges": False,
        "has_insolvency_history": False,
    }
    if overrides:
        profile.update(overrides)
    return profile


class TestParseDate:
    def test_valid_iso(self):
        assert parse_date("2024-03-15") == date(2024, 3, 15)

    def test_none(self):
        assert parse_date(None) is None

    def test_empty_string(self):
        assert parse_date("") is None

    def test_malformed(self):
        assert parse_date("not-a-date") is None


class TestExtractCompanyFields:
    def test_basic_extraction(self):
        fields = extract_company_fields(_profile_fixture())
        assert fields["company_number"] == "12345678"
        assert fields["company_name"] == "ACME LIMITED"
        assert fields["status"] == "active"
        assert fields["sic_code"] == "43210"
        assert fields["incorporation_date"] == date(2020, 3, 15)
        assert fields["locality"] == "London"
        assert fields["postal_code"] == "SW1A 1AA"

    def test_missing_sic_codes(self):
        fields = extract_company_fields(_profile_fixture({"sic_codes": []}))
        assert fields["sic_code"] is None

    def test_missing_address(self):
        fields = extract_company_fields(
            _profile_fixture({"registered_office_address": {}})
        )
        assert fields["locality"] is None


class TestExtractComplianceFields:
    def test_detects_overdue_accounts(self):
        fields = extract_compliance_fields(_profile_fixture())
        assert fields["accounts_overdue"] is True

    def test_not_overdue_when_future_due_date(self):
        future = (date.today() + timedelta(days=60)).isoformat()
        profile = _profile_fixture({"accounts": {"next_due": future}})
        fields = extract_compliance_fields(profile)
        assert fields["accounts_overdue"] is False

    def test_picks_earliest_deadline(self):
        # accounts overdue (past), confirmation future → next_deadline = accounts
        fields = extract_compliance_fields(_profile_fixture())
        assert fields["next_deadline"] is not None
        assert fields["next_deadline"] < date.today()

    def test_days_until_deadline_negative_when_overdue(self):
        fields = extract_compliance_fields(_profile_fixture())
        assert fields["days_until_next_deadline"] is not None
        assert fields["days_until_next_deadline"] < 0

    def test_insolvency_flag_propagates(self):
        fields = extract_compliance_fields(
            _profile_fixture({"has_insolvency_history": True})
        )
        assert fields["in_insolvency"] is True
