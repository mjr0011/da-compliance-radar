# Compliance, GDPR, PECR

This platform processes data about UK companies and the people who run them. Both UK GDPR and PECR apply. Read this before going live with outreach.

## What data is processed

| Data | Source | Legal basis |
|---|---|---|
| Company name, number, registered address, filing history | Companies House (public register) | Public task / legitimate interest |
| SIC code, status, officer changes | Companies House | As above |
| Website, phone number | Google Places API | Public; legitimate interest |
| Business email | Hunter.io (B2B catch-alls) | Legitimate interest, with LIA |
| Director names (if surfaced) | Companies House | Public register; legitimate interest |

We do **not** process special-category data, financial account contents, payment data, or anything outside the public register / public business profiles.

## Lawful basis

Outreach to UK businesses for accountancy services is typically grounded in **Article 6(1)(f) — legitimate interests**. The ICO's B2B marketing guidance is the authoritative reference:

> https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/business-to-business-marketing/

Before the first outbound campaign, complete a **Legitimate Interest Assessment (LIA)** covering:

1. **Purpose test** — is the interest genuine? (Yes: D&A is an accountancy firm contacting businesses about accountancy services they likely need.)
2. **Necessity test** — is processing necessary to that interest? (Yes: identification of overdue filings or new incorporations is otherwise manual.)
3. **Balancing test** — does the individual's interest, rights, or freedoms override D&A's? (Document the answer; B2B contact data has lower expectation of privacy than personal contact data, but is not zero.)

Keep the signed LIA on file. Review annually.

## PECR — electronic marketing

PECR governs *how* the firm contacts a prospect, separately from GDPR's *whether*.

- **Corporate subscribers** (Ltd, LLP, plc, gov bodies): unsolicited B2B email and calls are generally permitted, subject to:
  - clear identification of the sender
  - a working opt-out in every electronic message
  - honouring the CTPS (corporate telephone preference service) before any call
- **Sole traders and partnerships**: treated as individuals under PECR. Soft opt-in or prior consent is required for email and SMS.

The platform's suppression list (the `suppression` table) is the technical implementation of opt-outs. Anything in that table must never appear in outbound flows.

### What this means in practice

- The CRM sync step (`push_lead_to_crm`) writes a Deal, not a Contact, when no business email is on file. Don't backfill personal emails without confirming PECR status.
- Before live outreach: implement CTPS suppression (https://www.tpsonline.org.uk/ctps) for the phone-call channel. Not in this build.
- Every outbound email template must include a one-click unsubscribe and a postal address for the firm.

## Suppression list

Schema: `suppression(company_number?, email?, domain?, reason, added_by, created_at)`.

Lookups happen in `app.workers.tasks._is_suppressed` and gate **lead creation**, not alert dispatch. This means a suppressed entity never reaches the dashboard for outreach decisions in the first place.

To add an entry via SQL until the admin UI ships:

```sql
INSERT INTO suppression (company_number, reason, added_by, created_at)
VALUES ('12345678', 'Customer opt-out via email 2025-01-04', 'jane@dennisandassociates.co.uk', now());
```

## Data subject requests

Article 15 (access) and 17 (erasure) requests are rare for purely public-register data but they can happen. Workflow:

- **Access request** → export every row in `companies`, `compliance`, `leads`, `alerts` keyed to that company number, plus any director name match in `notes` / `summary`. Return as CSV.
- **Erasure request** → set `is_active = false` on the relevant company (you may need a column added; not in v0), add to suppression, redact any natural-person mentions in `leads.notes`. We do not delete the company row itself because it's derived from a public register and we have a legitimate interest in maintaining accurate records of our monitoring activity, but we stop further processing.

Log every DSR in the firm's existing GDPR register.

## Retention

- **Companies / compliance**: retained while we monitor the company. Removed within 30 days of removing from monitoring.
- **Leads**: 24 months after final status change (won/lost/rejected), then archived.
- **Alerts**: 12 months. Older rows can be pruned with a SQL job.
- **Users**: retained while active; deactivated accounts retained 6 months for audit.

These periods are defaults — confirm with the firm's data protection lead.

## ICO registration

Dennis & Associates must be registered with the ICO as a data controller. Reference: https://ico.org.uk/for-organisations/data-protection-fee/

## What is *not* compliant out-of-the-box

- **CTPS suppression** is not implemented. Do not run telephone outreach until it is. The Suppression Source enum already includes `CTPS_MATCH` so the workflow is ready; you just need a job that loads the daily CTPS file and creates entries.
- **Cookie consent banner** is not implemented for the dashboard. Internal-only use makes this less urgent, but if the dashboard is ever exposed externally, it needs one.

## What is now in place

The hardening pass added the missing GDPR primitives:

### Audit log (`audit_log` table)

Append-only record of every security-relevant event. Captures actor (id, email, IP, user-agent), event type, target resource, and detail blob. Surfaced in the admin UI at `/admin/audit-log` (admin role only). Used for:

- DSAR Article 15 responses ("show me every action your platform took on data about me")
- Incident reconstruction
- ICO breach-notification timelines (Article 33: within 72 hours)
- SOC 2 / ISO 27001 evidence collection when the firm pursues those certifications

Rows are never updated or deleted by application code.

### Enhanced suppression list (`suppression` table)

The basic suppression list has been extended with three GDPR-essential fields:

- `source` — one of `USER_OPT_OUT`, `CTPS_MATCH`, `CLIENT_REQUEST`, `DSR_ERASURE`, `MANUAL`. Feeds compliance reports and proves *why* an entity is suppressed.
- `lawful_basis` — free-text reference to the ICO basis (e.g. `Art. 17(1)(c)` for an erasure request based on objection).
- `request_received_at` — timestamp of when the data subject contacted the firm. The Article 12 one-month response clock starts here.

Surfaced at `/admin/suppression` (admin + manager). Mutations write to the audit log.

### Refresh tokens, lockout, structured login events

Authentication now produces both an access token (short) and a refresh token (30 days). Five failed login attempts in 15 minutes lock the account for 30 minutes. Every login attempt — success, failure, lockout — writes an audit-log entry with IP and user-agent. Token refresh attempts (success and failure) are also logged. This satisfies the firm's obligation under Article 32 to protect personal data with appropriate security measures.

## Disclaimer

This document is internal guidance, not legal advice. Confirm everything with the firm's solicitor and the ICO's published guidance before launching outbound campaigns.
