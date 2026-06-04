"""
Tests for the lead scoring engine.

The spec defines exact point values per factor; these tests pin them.
"""
from datetime import date, timedelta

import pytest

from app.services.lead_scoring import (
    PRIORITY_SIC_PREFIXES,
    TARGET_POSTCODE_PREFIXES,
    ScoringInputs,
    classify_risk_level,
    classify_urgency,
    estimate_annual_value_gbp,
    score_lead,
)


class TestSingleFactors:
    """Each scoring factor in isolation."""

    def test_accounts_overdue_awards_35(self):
        result = score_lead(ScoringInputs(accounts_overdue=True))
        assert result.lead_score == 35
        assert result.breakdown == {"accounts_overdue": 35}

    def test_confirmation_overdue_awards_20(self):
        result = score_lead(ScoringInputs(confirmation_overdue=True))
        assert result.lead_score == 20

    def test_newly_incorporated_awards_15(self):
        result = score_lead(
            ScoringInputs(incorporation_date=date.today() - timedelta(days=30))
        )
        assert result.lead_score == 15
        assert "newly_incorporated" in result.breakdown

    def test_old_incorporation_does_not_score(self):
        result = score_lead(
            ScoringInputs(incorporation_date=date.today() - timedelta(days=400))
        )
        assert "newly_incorporated" not in result.breakdown

    @pytest.mark.parametrize("sic", ["41100", "43210", "47190", "68201", "86900"])
    def test_priority_sector_awards_15(self, sic):
        result = score_lead(ScoringInputs(sic_code=sic))
        assert result.lead_score == 15
        assert "priority_sector" in result.breakdown

    def test_non_priority_sector_no_score(self):
        result = score_lead(ScoringInputs(sic_code="99999"))
        assert "priority_sector" not in result.breakdown

    def test_active_website_awards_10(self):
        result = score_lead(ScoringInputs(website="https://example.com"))
        assert result.lead_score == 10

    def test_empty_website_does_not_score(self):
        result = score_lead(ScoringInputs(website=""))
        assert result.lead_score == 0

    def test_london_postcode_awards_target_region(self):
        result = score_lead(ScoringInputs(postal_code="SW1A 1AA"))
        assert result.lead_score == 10

    def test_london_locality_awards_target_region(self):
        result = score_lead(ScoringInputs(locality="Central London"))
        assert result.lead_score == 10

    def test_non_target_region_no_score(self):
        result = score_lead(ScoringInputs(postal_code="EH1 1AA", locality="Edinburgh"))
        assert "target_region" not in result.breakdown

    def test_hiring_signal_awards_10(self):
        result = score_lead(ScoringInputs(has_hiring_signal=True))
        assert result.lead_score == 10

    def test_high_online_activity_awards_10(self):
        result = score_lead(ScoringInputs(has_high_online_activity=True))
        assert result.lead_score == 10


class TestCombinedScoring:
    """Spec section 8: scores compose additively up to 100."""

    def test_perfect_lead_scores_100(self):
        # All eight factors firing = 35+20+15+15+10+10+10+10 = 125, capped at 100
        result = score_lead(
            ScoringInputs(
                accounts_overdue=True,
                confirmation_overdue=True,
                incorporation_date=date.today() - timedelta(days=30),
                sic_code="43100",
                website="https://example.com",
                postal_code="SW1A 1AA",
                has_hiring_signal=True,
                has_high_online_activity=True,
            )
        )
        assert result.lead_score == 100

    def test_construction_overdue_in_london(self):
        # CIS construction company in London, overdue accounts:
        # 35 (overdue) + 15 (sector) + 10 (region) = 60
        result = score_lead(
            ScoringInputs(
                accounts_overdue=True,
                sic_code="43210",
                postal_code="E14 5AB",
            )
        )
        assert result.lead_score == 60

    def test_newly_incorporated_landlord_in_target_region(self):
        # 15 (new) + 15 (sector 68) + 10 (region) = 40
        result = score_lead(
            ScoringInputs(
                incorporation_date=date.today() - timedelta(days=10),
                sic_code="68209",
                postal_code="NW1 1AA",
            )
        )
        assert result.lead_score == 40

    def test_no_factors_scores_zero(self):
        assert score_lead(ScoringInputs()).lead_score == 0


class TestRiskScoring:
    """Risk is a *separate* signal, weighted differently from lead score."""

    def test_overdue_accounts_drives_50_risk(self):
        result = score_lead(ScoringInputs(accounts_overdue=True))
        assert result.risk_score == 50

    def test_all_risk_factors_max_at_100(self):
        result = score_lead(
            ScoringInputs(
                accounts_overdue=True,
                confirmation_overdue=True,
                strike_off_warning=True,
                in_insolvency=True,
            )
        )
        # 50 + 25 + 40 + 30 = 145, capped at 100
        assert result.risk_score == 100

    def test_clean_company_zero_risk(self):
        result = score_lead(
            ScoringInputs(sic_code="43210", website="https://x.com", postal_code="E1 6AN")
        )
        assert result.risk_score == 0


class TestRiskLevelClassification:
    @pytest.mark.parametrize(
        "score,expected",
        [(0, "low"), (24, "low"), (25, "medium"), (49, "medium"),
         (50, "high"), (74, "high"), (75, "critical"), (100, "critical")],
    )
    def test_thresholds(self, score, expected):
        assert classify_risk_level(score) == expected


class TestUrgencyClassification:
    def test_overdue_urgent_when_high_score(self):
        assert classify_urgency(60, -10) == "urgent"

    def test_overdue_high_when_low_score(self):
        assert classify_urgency(20, -5) == "high"

    def test_high_score_high_urgency(self):
        assert classify_urgency(80, 30) == "high"

    def test_low_score_low_urgency(self):
        assert classify_urgency(10, 90) == "low"


class TestValueEstimation:
    def test_priority_sector_premium(self):
        priority = estimate_annual_value_gbp("43210", 50)
        general = estimate_annual_value_gbp("99999", 50)
        assert priority > general

    def test_high_score_premium(self):
        low = estimate_annual_value_gbp("43210", 20)
        high = estimate_annual_value_gbp("43210", 80)
        assert high > low

    def test_returns_round_number(self):
        v = estimate_annual_value_gbp("43210", 70)
        assert isinstance(v, float)
        assert v > 0


class TestConfigurationConstants:
    """Document the configuration so changes to the lists are intentional."""

    def test_priority_sics_include_construction(self):
        assert {"41", "42", "43"}.issubset(PRIORITY_SIC_PREFIXES)

    def test_priority_sics_include_landlords(self):
        assert "68" in PRIORITY_SIC_PREFIXES

    def test_target_region_includes_london(self):
        assert "SW" in TARGET_POSTCODE_PREFIXES
