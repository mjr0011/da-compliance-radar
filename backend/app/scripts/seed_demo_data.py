"""
Demo data seeder.

Populates a freshly-migrated database with a realistic spread of
fictional UK Ltd companies plus their derived compliance rows,
leads, alerts, suppression entries, and audit-log history.

The data is generated deterministically (random.seed) so the same
counts and shapes appear every run — useful for screenshots and
investor demos.

Usage:
    docker compose exec backend python -m app.scripts.seed_demo_data
    docker compose exec backend python -m app.scripts.seed_demo_data --companies 2000
    docker compose exec backend python -m app.scripts.seed_demo_data --reset

What it generates (defaults):
    1,000 companies (mostly London-postcoded, priority sectors weighted)
      ~  300 compliance rows with overdue accounts
      ~  200 overdue confirmation statements
      ~   50 strike-off warnings
      ~   20 in-insolvency
    ~  280 leads (companies with lead_score >= 40)
    ~  450 alerts (Slack/Telegram/Email mix)
       12 suppression entries (varied sources)
    ~  120 audit-log entries (spread across the last 30 days)

Lead scores and risk scores are computed by the real `score_lead()`
function, so the seeded data is internally consistent with the
production scoring logic.
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import delete

from app.database import SessionLocal
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.company import Company
from app.models.compliance import Compliance
from app.models.lead import Lead
from app.models.stream_state import StreamState
from app.models.suppression import SuppressionEntry, SuppressionSource
from app.services.ai_classifier import classify_lead
from app.services.lead_scoring import (
    ScoringInputs,
    classify_risk_level,
    classify_urgency,
    estimate_annual_value_gbp,
    score_lead,
)

# Deterministic output — same demo every run.
random.seed(42)


# =============================================================
# Name generator
# =============================================================

LONDON_PLACES = [
    "Camden", "Highbury", "Vauxhall", "Shoreditch", "Battersea", "Mayfair",
    "Hackney", "Islington", "Wandsworth", "Greenwich", "Kennington", "Brixton",
    "Holborn", "Soho", "Bloomsbury", "Marylebone", "Pimlico", "Belgravia",
    "Notting Hill", "Chelsea", "Fulham", "Putney", "Clapham", "Peckham",
    "Bermondsey", "Dalston", "Stoke Newington", "Hampstead", "Cricklewood",
    "Tooting", "Bow", "Stratford", "Walthamstow", "Wapping", "Whitechapel",
    "Bethnal Green", "Aldgate", "Spitalfields", "Hoxton",
]
NON_LONDON_PLACES = [
    "Reading", "Oxford", "Cambridge", "Brighton", "Bristol", "Leeds",
    "Manchester", "Birmingham", "Glasgow", "Edinburgh", "Cardiff",
]
NAME_NOUNS = [
    "Construction", "Holdings", "Property", "Trading", "Services", "Studios",
    "Consultants", "Bakeries", "Logistics", "Care", "Health", "Capital",
    "Estates", "Developments", "Solutions", "Partners", "Group", "Foods",
    "Spirits", "Cabs", "Retail", "Stationers", "Bicycles", "Coffee",
    "Interiors", "Builders", "Plumbing", "Electrics", "Roofing", "Lettings",
]
NAME_ADJECTIVES = [
    "Pixel", "Quill", "Ink", "Cobble", "Penny", "Mercer", "Vale", "Thornbury",
    "Pine", "Oak", "Willow", "Ridge", "Crown", "Royal", "Northern", "Sterling",
    "Ironside", "Saffron", "Velvet", "Copper", "Granite", "Cedar",
]
NAME_SURNAMES = [
    "Mercer", "Vale", "Thornbury", "Whitfield", "Hargreaves", "Pemberton",
    "Ashworth", "Holloway", "Eastman", "Barrington", "Foxworth", "Cliveden",
]

LONDON_POSTCODES = [
    ("SW1A 1AA", "Westminster"),  ("SW9 6DE", "Vauxhall"),
    ("EC2N 4DL", "City of London"), ("EC1V 9HD", "Old Street"),
    ("E14 5AB", "Canary Wharf"),  ("E2 7DG", "Bethnal Green"),
    ("E8 4DA", "Hackney"),         ("N1 6BS", "Islington"),
    ("N5 1AR", "Highbury"),        ("NW1 7JE", "Camden Town"),
    ("NW5 1QX", "Kentish Town"),   ("NW3 1HG", "Hampstead"),
    ("W1D 3QF", "Soho"),           ("W2 1JU", "Paddington"),
    ("WC1B 3DG", "Bloomsbury"),    ("WC2H 9JR", "Covent Garden"),
    ("SE1 9SG", "Southwark"),      ("SE15 5RS", "Peckham"),
    ("SW11 5TR", "Battersea"),     ("SW3 5SR", "Chelsea"),
    ("SW18 2PT", "Wandsworth"),    ("SE10 9NN", "Greenwich"),
    ("E1 6AN", "Whitechapel"),     ("E20 1EJ", "Stratford"),
]
NON_LONDON_POSTCODES = [
    ("M2 3WQ", "Manchester"),  ("B1 1HQ", "Birmingham"),
    ("LS1 4AP", "Leeds"),      ("EH1 1AA", "Edinburgh"),
    ("BS1 5UH", "Bristol"),    ("CB2 1TN", "Cambridge"),
]

# SIC codes weighted to D&A priority sectors
SIC_WEIGHTED = (
    # construction / CIS
    [("41100", "Development of building projects")] * 4
    + [("43210", "Electrical installation")] * 4
    + [("43220", "Plumbing, heat and air-conditioning installation")] * 3
    + [("43390", "Other building completion and finishing")] * 3
    # property / landlords
    + [("68100", "Buying and selling of own real estate")] * 3
    + [("68201", "Renting and operating of housing association real estate")] * 4
    + [("68209", "Other letting and operating of own or leased real estate")] * 5
    # ecommerce
    + [("47190", "Other retail sale in non-specialised stores")] * 3
    + [("47910", "Retail sale via mail order houses or via Internet")] * 4
    # care / health
    + [("86900", "Other human health activities")] * 2
    + [("87300", "Residential care activities for the elderly and disabled")] * 3
    + [("88100", "Social work activities without accommodation for the elderly")] * 2
    # consultants
    + [("70220", "Business and other management consultancy activities")] * 3
    + [("62020", "Information technology consultancy activities")] * 2
    # hospitality
    + [("56101", "Licensed restaurants")] * 2
    + [("56301", "Licensed clubs")] * 1
    + [("55100", "Hotels and similar accommodation")] * 1
    # general
    + [("62090", "Other information technology service activities")] * 2
    + [("10710", "Manufacture of bread; fresh pastry goods and cakes")] * 1
    + [("47710", "Retail sale of clothing in specialised stores")] * 1
)


def generate_company_name() -> str:
    """Build a plausible UK Ltd company name."""
    pattern = random.choices(
        ["place_noun", "two_surnames", "adj_noun", "the_noun_company", "place_noun_group"],
        weights=[40, 20, 20, 10, 10],
    )[0]
    suffix = random.choice(["Ltd", "Limited"])
    if pattern == "place_noun":
        return f"{random.choice(LONDON_PLACES + NON_LONDON_PLACES)} {random.choice(NAME_NOUNS)} {suffix}"
    if pattern == "two_surnames":
        a, b = random.sample(NAME_SURNAMES, 2)
        return f"{a} & {b} {suffix}"
    if pattern == "adj_noun":
        return f"{random.choice(NAME_ADJECTIVES)} {random.choice(NAME_NOUNS)} {suffix}"
    if pattern == "the_noun_company":
        return f"The {random.choice(NAME_NOUNS)} Company {suffix}"
    return f"{random.choice(LONDON_PLACES)} {random.choice(NAME_NOUNS)} Group"


def generate_crn() -> str:
    """Realistic-looking 8-digit Companies House number."""
    # Most modern English/Welsh CRNs are 8 digits starting 0 or 1.
    first = random.choice(["0", "1", "1", "1"])
    rest = "".join(random.choices("0123456789", k=7))
    return first + rest


def generate_postcode() -> tuple[str, str]:
    """Weighted toward London."""
    if random.random() < 0.85:
        return random.choice(LONDON_POSTCODES)
    return random.choice(NON_LONDON_POSTCODES)


def generate_incorporation_date() -> date:
    """Heavy on 2018–2024, some older."""
    if random.random() < 0.8:
        days_ago = random.randint(30, 365 * 6)  # within last 6 years
    else:
        days_ago = random.randint(365 * 6, 365 * 20)  # 6–20 years
    return date.today() - timedelta(days=days_ago)


# =============================================================
# Compliance state generator
# =============================================================


def generate_compliance_fields(incorp: date) -> dict:
    """Roll the compliance dice for a single company."""
    today = date.today()

    # Accounts: due 9 months after year-end. We'll pick a notional year-end
    # and offset. ~30% are past their next-due date.
    year_end_offset_months = random.choice([3, 6, 9, 12])  # quarterly year ends are common
    year_end = date(today.year, year_end_offset_months, 28)
    if year_end > today:
        year_end = date(today.year - 1, year_end_offset_months, 28)
    accounts_due = year_end + timedelta(days=270)  # ≈ 9 months
    accounts_overdue = accounts_due < today and random.random() < 0.35

    # Confirmation statement: anniversary of incorporation, due 14 days after
    cs_anniversary_year = today.year if incorp.replace(year=today.year) >= today else today.year - 1
    try:
        cs_anniversary = incorp.replace(year=cs_anniversary_year)
    except ValueError:  # 29 Feb on a non-leap year
        cs_anniversary = date(cs_anniversary_year, incorp.month, 28)
    cs_due = cs_anniversary + timedelta(days=14)
    if cs_due > today:
        cs_due = cs_due - timedelta(days=365)  # use last year's date as recent past
    confirmation_overdue = cs_due < today - timedelta(days=14) and random.random() < 0.20

    strike_off_warning = (accounts_overdue or confirmation_overdue) and random.random() < 0.10
    in_insolvency = random.random() < 0.02
    has_charges = random.random() < 0.15

    # Pick the earliest still-active deadline as next_deadline
    candidates = []
    if accounts_due:
        candidates.append(accounts_due)
    if cs_due:
        candidates.append(cs_due)
    next_deadline = min(candidates) if candidates else None
    days_until = (next_deadline - today).days if next_deadline else None

    last_filing_date = incorp + timedelta(days=random.randint(180, 1800))

    return {
        "accounts_due_date": accounts_due,
        "accounts_overdue": accounts_overdue,
        "confirmation_due_date": cs_due,
        "confirmation_overdue": confirmation_overdue,
        "strike_off_warning": strike_off_warning,
        "in_insolvency": in_insolvency,
        "has_charges": has_charges,
        "next_deadline": next_deadline,
        "days_until_next_deadline": days_until,
        "last_filing_date": last_filing_date,
    }


# =============================================================
# Lead summary templates (per AI category)
# =============================================================

LEAD_SUMMARIES = {
    "Overdue Accounts": [
        "Annual accounts {days} days overdue. Filed late in {late_count} of last 4 years. Strong candidate for compliance outreach.",
        "Year-end accounts overdue {days} days. Director appointed recently; possible administrative gap.",
        "Statutory filing missed by {days} days. CIS-registered with active subcontractors — risk of HMRC review.",
    ],
    "Overdue Confirmation Statement": [
        "Confirmation statement overdue {days} days. Two-strike risk; first overdue notice already issued.",
        "Annual confirmation gap of {days} days. PSC declaration likely also outstanding.",
    ],
    "Newly Incorporated": [
        "Incorporated {days} days ago. No accountant on PSC register. Typical first-year compliance support need: VAT, payroll, year-end forecasting.",
        "New company, {days} days old. First confirmation statement due in {cs_days} days — natural onboarding opportunity.",
    ],
    "CIS / Construction": [
        "Construction company with CIS scheme active. Monthly returns required; subcontractor payments suggest ongoing compliance workload.",
        "Building services firm, registered for CIS. Annual scheme review and year-end CIS reconciliation routinely outsourced.",
    ],
    "Landlord Tax": [
        "Letting company with portfolio of {portfolio} properties. ATED filing required; MTD ITSA preparation likely.",
        "Property holding company. Capital allowances, ATED, and corporation tax interaction makes this a high-fee engagement.",
    ],
    "eCommerce Accounting": [
        "Online retail. OSS/IOSS thresholds likely breached for EU sales. Marketplace VAT compliance is a recurring engagement.",
        "eCommerce trader with multi-channel revenue. Inventory accounting and marketplace fee reconciliation are typical pain points.",
    ],
    "General Compliance": [
        "Moderate compliance risk with multiple converging signals. Worth a discovery call within the next two weeks.",
        "Lead score driven by sector + region match. Standard fact-find recommended before outreach.",
    ],
}

CATEGORY_TO_CRM_STAGE = {
    "Overdue Accounts": "qualified",
    "Overdue Confirmation Statement": "qualified",
    "Newly Incorporated": "new",
    "CIS / Construction": "qualified",
    "Landlord Tax": "qualified",
    "eCommerce Accounting": "new",
    "General Compliance": "new",
}


def generate_lead_summary(category: str, days: int, incorp: date) -> str:
    template = random.choice(LEAD_SUMMARIES.get(category, LEAD_SUMMARIES["General Compliance"]))
    today = date.today()
    return template.format(
        days=days,
        late_count=random.randint(2, 4),
        cs_days=random.randint(30, 300),
        portfolio=random.randint(3, 24),
    )


# =============================================================
# Main seeder
# =============================================================


def seed(*, n_companies: int = 1000, reset: bool = False) -> None:
    db = SessionLocal()
    try:
        if reset:
            print("→ Resetting demo data (preserving users)…")
            db.execute(delete(Alert))
            db.execute(delete(Lead))
            db.execute(delete(Compliance))
            db.execute(delete(Company))
            db.execute(delete(SuppressionEntry))
            db.execute(delete(AuditLog))
            db.execute(delete(StreamState))
            db.commit()

        # ---- Companies + compliance ----
        print(f"→ Generating {n_companies:,} companies + compliance rows…")
        companies: list[Company] = []
        for _ in range(n_companies):
            postcode, locality = generate_postcode()
            sic_code, sic_desc = random.choice(SIC_WEIGHTED)
            incorp = generate_incorporation_date()
            comp_fields = generate_compliance_fields(incorp)

            # Score via the real engine so scores are coherent with prod logic
            today = date.today()
            scoring = score_lead(
                ScoringInputs(
                    accounts_overdue=comp_fields["accounts_overdue"],
                    confirmation_overdue=comp_fields["confirmation_overdue"],
                    strike_off_warning=comp_fields["strike_off_warning"],
                    in_insolvency=comp_fields["in_insolvency"],
                    incorporation_date=incorp,
                    sic_code=sic_code,
                    website=f"https://example-{generate_crn()[:6]}.co.uk" if random.random() < 0.55 else "",
                    postal_code=postcode,
                    locality=locality,
                    has_hiring_signal=random.random() < 0.18,
                    has_high_online_activity=random.random() < 0.22,
                )
            )

            company = Company(
                company_number=generate_crn(),
                company_name=generate_company_name(),
                status=random.choices(
                    ["active", "active", "active", "dormant", "liquidation"],
                    weights=[80, 8, 6, 4, 2],
                )[0],
                company_type="ltd",
                sic_code=sic_code,
                sic_description=sic_desc,
                incorporation_date=incorp,
                address_line_1=f"{random.randint(1, 250)} {random.choice(['High Street', 'Old Street', 'King Road', 'Church Lane', 'Mill Road'])}",
                locality=locality,
                postal_code=postcode,
                country="England" if locality not in ("Edinburgh", "Glasgow", "Cardiff") else None,
                website=f"https://example-{generate_crn()[:6]}.co.uk" if random.random() < 0.55 else None,
                lead_score=scoring.lead_score,
                risk_score=scoring.risk_score,
            )
            db.add(company)
            db.flush()  # need id for compliance FK

            compliance = Compliance(
                company_id=company.id,
                **comp_fields,
                risk_level=classify_risk_level(scoring.risk_score),
            )
            db.add(compliance)
            companies.append(company)

        db.commit()
        print(f"  ✓ {len(companies):,} companies committed")

        # ---- Leads (companies with score >= 40) ----
        print("→ Generating leads for high-scoring companies…")
        lead_count = 0
        alert_count = 0
        lead_candidates = [c for c in companies if c.lead_score >= 40]
        random.shuffle(lead_candidates)

        for company in lead_candidates[: int(len(lead_candidates) * 0.85)]:  # not every candidate becomes a lead
            comp = db.query(Compliance).filter(Compliance.company_id == company.id).first()
            if not comp:
                continue

            ai = classify_lead(
                {
                    "company_name": company.company_name,
                    "sic_code": company.sic_code,
                    "accounts_overdue": comp.accounts_overdue,
                    "confirmation_overdue": comp.confirmation_overdue,
                    "newly_incorporated": (
                        company.incorporation_date
                        and (date.today() - company.incorporation_date).days <= 365
                    ),
                    "estimated_value_gbp": estimate_annual_value_gbp(company.sic_code or "", company.lead_score),
                }
            )

            urgency = classify_urgency(company.lead_score, comp.days_until_next_deadline or 365)
            value = estimate_annual_value_gbp(company.sic_code or "", company.lead_score)
            days = abs(comp.days_until_next_deadline or 30)
            summary = generate_lead_summary(ai["category"], days, company.incorporation_date or date.today())

            status = random.choices(
                ["new", "qualified", "contacted", "in_progress", "won", "lost", "rejected"],
                weights=[40, 25, 15, 10, 5, 3, 2],
            )[0]

            crm_provider = None
            crm_external_id = None
            crm_synced_at = None
            if status in ("qualified", "contacted", "in_progress", "won"):
                crm_provider = random.choice(["hubspot", "pipedrive"])
                crm_external_id = f"deal_{random.randint(100000, 999999)}"
                crm_synced_at = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 240))

            created_at = datetime.now(timezone.utc) - timedelta(
                hours=random.randint(1, 24 * 30)
            )

            lead = Lead(
                company_id=company.id,
                source="companies_house_compliance",
                lead_type=ai["category"],
                summary=summary,
                ai_category=ai["category"],
                urgency=urgency,
                estimated_value_gbp=value,
                lead_score=company.lead_score,
                status=status,
                crm_provider=crm_provider,
                crm_external_id=crm_external_id,
                crm_synced_at=crm_synced_at,
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(lead)
            db.flush()
            lead_count += 1

            # 1–3 alerts per high-scoring lead
            if company.lead_score >= 60:
                for channel in random.sample(["slack", "email", "telegram"], k=random.randint(1, 3)):
                    sent_status = random.choices(
                        ["sent", "sent", "sent", "failed", "pending"],
                        weights=[80, 5, 5, 7, 3],
                    )[0]
                    sent_at = (
                        created_at + timedelta(seconds=random.randint(5, 60))
                        if sent_status == "sent"
                        else None
                    )
                    error_message = (
                        random.choice([
                            "Slack webhook timeout (Slack API 503)",
                            "Telegram chat_id invalid",
                            "Email bounce: 550 5.1.1 No such user",
                        ])
                        if sent_status == "failed"
                        else None
                    )
                    db.add(
                        Alert(
                            lead_id=lead.id,
                            alert_channel=channel,
                            alert_type="high_value_lead" if company.lead_score >= 70 else "qualified_lead",
                            sent_status=sent_status,
                            sent_at=sent_at,
                            error_message=error_message,
                            created_at=created_at,
                        )
                    )
                    alert_count += 1

        db.commit()
        print(f"  ✓ {lead_count:,} leads, {alert_count:,} alerts committed")

        # ---- Suppression list ----
        print("→ Generating suppression list…")
        suppression_seeds = [
            ("12345678", None, None, SuppressionSource.USER_OPT_OUT,
             "GDPR Art. 21", "Email reply: please remove from outreach"),
            ("23456789", None, None, SuppressionSource.CLIENT_REQUEST,
             None, "Existing client — managed by Sarah's team"),
            (None, "marketing@example.com", None, SuppressionSource.USER_OPT_OUT,
             "GDPR Art. 21", "Unsubscribe link clicked"),
            (None, None, "competitor-firm.co.uk", SuppressionSource.MANUAL,
             None, "Competitor — do not contact"),
            ("34567890", None, None, SuppressionSource.CTPS_MATCH,
             "PECR Reg. 21", "Listed on Corporate TPS — telephone outreach blocked"),
            ("45678901", None, None, SuppressionSource.DSR_ERASURE,
             "GDPR Art. 17(1)(c)", "Erasure request received 2025-11-12; 30-day clock"),
            ("56789012", None, None, SuppressionSource.CLIENT_REQUEST,
             None, "Group company — handled directly by partners"),
            (None, "do-not-contact@firm.co.uk", None, SuppressionSource.MANUAL,
             None, "Personal request via LinkedIn"),
            ("67890123", None, None, SuppressionSource.USER_OPT_OUT,
             "GDPR Art. 21", "Phone call from director — explicit opt-out"),
            (None, None, "internal-test-domain.local", SuppressionSource.MANUAL,
             None, "Internal test domain"),
            ("78901234", None, None, SuppressionSource.CTPS_MATCH,
             "PECR Reg. 21", "CTPS match on monthly sweep"),
            (None, "noreply@example.com", None, SuppressionSource.MANUAL,
             None, "No-reply mailbox — never contact"),
        ]
        for crn, email, domain, source, basis, reason in suppression_seeds:
            db.add(
                SuppressionEntry(
                    company_number=crn,
                    email=email,
                    domain=domain,
                    source=source.value,
                    lawful_basis=basis,
                    reason=reason,
                    added_by="seed@dennisandassociates.co.uk",
                    created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90)),
                )
            )
        db.commit()
        print(f"  ✓ {len(suppression_seeds)} suppression entries committed")

        # ---- Audit log ----
        print("→ Generating audit-log history…")
        audit_events = []
        now = datetime.now(timezone.utc)
        for i in range(120):
            ts = now - timedelta(
                days=random.randint(0, 29),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            event_type = random.choices(
                [
                    "auth.login.success", "auth.login.success", "auth.login.success",
                    "auth.login.failed",
                    "auth.logout",
                    "auth.token.refresh", "auth.token.refresh",
                    "lead.status.changed",
                    "suppression.added",
                    "user.created",
                ],
                weights=[30, 30, 30, 8, 12, 15, 15, 10, 5, 3],
            )[0]
            actor_email = random.choice([
                "admin@dennisandassociates.co.uk",
                "sarah@dennisandassociates.co.uk",
                "james@dennisandassociates.co.uk",
                None,  # anonymous / unknown
            ])
            detail = None
            if event_type == "lead.status.changed":
                detail = json.dumps({
                    "from": random.choice(["new", "qualified"]),
                    "to": random.choice(["contacted", "in_progress", "won"]),
                })
            elif event_type == "auth.login.failed":
                detail = json.dumps({"attempt": random.randint(1, 5), "max": 5})
            audit_events.append(
                AuditLog(
                    event_type=event_type,
                    actor_email=actor_email,
                    actor_ip=f"{random.randint(10, 250)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}",
                    actor_user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    detail=detail,
                    created_at=ts,
                )
            )
        db.add_all(audit_events)
        db.commit()
        print(f"  ✓ {len(audit_events)} audit-log entries committed")

        print()
        print("Demo data seeded successfully.")
        print()
        _print_summary(db)
    finally:
        db.close()


def _print_summary(db) -> None:
    """Console summary so the operator can confirm the shape."""
    from sqlalchemy import func, select

    counts = {
        "Companies":  db.execute(select(func.count(Company.id))).scalar_one(),
        "Compliance": db.execute(select(func.count(Compliance.id))).scalar_one(),
        "Leads":      db.execute(select(func.count(Lead.id))).scalar_one(),
        "Alerts":     db.execute(select(func.count(Alert.id))).scalar_one(),
        "Suppression":db.execute(select(func.count(SuppressionEntry.id))).scalar_one(),
        "Audit log":  db.execute(select(func.count(AuditLog.id))).scalar_one(),
    }
    width = max(len(k) for k in counts)
    for k, v in counts.items():
        print(f"  {k:<{width}}  {v:>6,}")


# =============================================================
# CLI
# =============================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--companies", type=int, default=1000, help="how many companies to generate (default 1000)")
    parser.add_argument("--reset", action="store_true", help="wipe existing data first (preserves users)")
    args = parser.parse_args()
    seed(n_companies=args.companies, reset=args.reset)


if __name__ == "__main__":
    main()
