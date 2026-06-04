"""Tests for the dedicated compliance risk engine."""
from datetime import date, timedelta

import pytest

from app.services.risk_engine import (
    RiskInputs,
    predict_strike_off_window_days,
    score_compliance_risk,
    should_alert_on_risk,
)


class TestCleanCompany:
    def test_clean_company_scores_zero(self):
        r = score_compliance_risk(RiskInputs())
        assert r.risk_score == 0
        assert r.risk_level == "low"
        assert r.breakdown == {}
        assert r.rationale == []


class TestOverdueAccountsTiers:
    def test_30d_overdue_only(self):
        r = score_compliance_risk(RiskInputs(accounts_overdue_days=30))
        assert r.risk_score == 25
        assert r.risk_level == "medium"

    def test_90d_overdue_adds_band(self):
        r = score_compliance_risk(RiskInputs(accounts_overdue_days=90))
        # 25 (30d) + 15 (90d) = 40
        assert r.risk_score == 40

    def test_180d_overdue_max_tier(self):
        r = score_compliance_risk(RiskInputs(accounts_overdue_days=200))
        # 25 + 15 + 15 = 55
        assert r.risk_score == 55
        assert r.risk_level == "high"
        assert "strike-off threshold approaching" in r.rationale[-1].lower()


class TestStrikeOffSignals:
    def test_explicit_strike_off_warning(self):
        r = score_compliance_risk(RiskInputs(strike_off_warning=True))
        assert r.risk_score == 30
        assert r.risk_level == "medium"

    def test_strike_off_plus_overdue_is_critical(self):
        r = score_compliance_risk(
            RiskInputs(
                strike_off_warning=True,
                accounts_overdue_days=200,
                confirmation_overdue_days=60,
            )
        )
        # 25+15+15 (accounts) + 15 (conf 30d) + 30 (warning) = 100 (capped)
        assert r.risk_score == 100
        assert r.risk_level == "critical"


class TestStatusSignals:
    @pytest.mark.parametrize(
        "status,expected_min",
        [("dissolved", 50), ("in liquidation", 35), ("administration", 30)],
    )
    def test_status_drives_risk(self, status, expected_min):
        r = score_compliance_risk(RiskInputs(status=status))
        assert r.risk_score >= expected_min

    def test_active_status_no_extra_risk(self):
        r = score_compliance_risk(RiskInputs(status="active"))
        assert r.risk_score == 0


class TestBehaviouralSignals:
    def test_no_filings_24mo(self):
        old = date.today() - timedelta(days=800)
        r = score_compliance_risk(RiskInputs(last_filing_date=old))
        assert r.risk_score == 15

    def test_recent_filing_no_penalty(self):
        recent = date.today() - timedelta(days=60)
        r = score_compliance_risk(RiskInputs(last_filing_date=recent))
        assert r.risk_score == 0

    def test_officer_churn_threshold(self):
        # 2 changes: no penalty
        r = score_compliance_risk(RiskInputs(officer_changes_12mo=2))
        assert r.risk_score == 0
        # 3 changes: penalty
        r = score_compliance_risk(RiskInputs(officer_changes_12mo=3))
        assert r.risk_score == 10

    def test_dormant_reactivation(self):
        r = score_compliance_risk(RiskInputs(became_active_within_180d=True))
        assert r.risk_score == 10


class TestLevelThresholds:
    @pytest.mark.parametrize(
        "score,expected",
        [(0, "low"), (24, "low"), (25, "medium"), (49, "medium"),
         (50, "high"), (74, "high"), (75, "critical"), (100, "critical")],
    )
    def test_thresholds(self, score, expected):
        # Build a fake result by constructing inputs that hit the score
        # exactly — easier to just test the classifier via a few crafted cases.
        from app.services.risk_engine import _classify_level
        assert _classify_level(score) == expected


class TestStrikeOffWindowPrediction:
    def test_no_overdue_returns_none(self):
        assert predict_strike_off_window_days(RiskInputs()) is None

    def test_strike_off_warning_returns_zero(self):
        assert (
            predict_strike_off_window_days(RiskInputs(strike_off_warning=True)) == 0
        )

    def test_accounts_window(self):
        # 100 days overdue → 80 days until 180-day threshold
        assert (
            predict_strike_off_window_days(RiskInputs(accounts_overdue_days=100)) == 80
        )

    def test_confirmation_more_imminent_wins(self):
        # Confirmation 14d threshold vs accounts 180d threshold:
        # accounts overdue 10d → 170 days; confirmation overdue 5d → 9 days.
        # min is 9.
        result = predict_strike_off_window_days(
            RiskInputs(accounts_overdue_days=10, confirmation_overdue_days=5)
        )
        assert result == 9


class TestAlertGating:
    def test_critical_alerts(self):
        r = score_compliance_risk(
            RiskInputs(status="dissolved", accounts_overdue_days=300)
        )
        assert should_alert_on_risk(r)

    def test_low_risk_no_alert(self):
        r = score_compliance_risk(RiskInputs())
        assert not should_alert_on_risk(r)

    def test_60_plus_alerts(self):
        # 25+15+15 (accounts 180d) + 15 (conf 30d) = 70
        r = score_compliance_risk(
            RiskInputs(accounts_overdue_days=200, confirmation_overdue_days=30)
        )
        assert should_alert_on_risk(r)


class TestRationaleProvided:
    def test_rationale_explains_each_factor(self):
        r = score_compliance_risk(
            RiskInputs(
                accounts_overdue_days=200,
                strike_off_warning=True,
            )
        )
        # 3 accounts tiers + 1 strike-off = 4 rationale lines
        assert len(r.rationale) == 4
        assert any("strike-off" in line.lower() for line in r.rationale)
