"""
Multi-channel alert dispatcher with branded email templates.

Each channel is a thin function that takes a structured payload and
delivers. Errors are logged and persisted on the Alert row; they
never crash the worker.

For email deliverability in production:
  - Verify your sending domain in Resend
  - Add SPF: `v=spf1 include:_spf.resend.com ~all`
  - Add DKIM records as instructed by Resend dashboard
  - Add DMARC: `v=DMARC1; p=quarantine; rua=mailto:dmarc@dennisandassociates.co.uk`
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import resend
from sqlalchemy.orm import Session

from app.config import settings
from app.models.alert import Alert, AlertChannel, AlertStatus
from app.models.lead import Lead

logger = logging.getLogger(__name__)


URGENCY_EMOJI = {
    "urgent": "🚨",
    "high": "⚡",
    "medium": "📍",
    "low": "·",
}


# --- Message builders ---

def render_lead_message(lead: Lead) -> tuple[str, str]:
    """(title, markdown-body) for Slack/Telegram."""
    co = lead.company
    emoji = URGENCY_EMOJI.get(lead.urgency, "·")
    title = f"{emoji} New {lead.urgency.upper()} lead: {co.company_name if co else 'company'}"
    bits = [
        f"*Category:* {lead.ai_category or lead.lead_type}",
        f"*Lead score:* {lead.lead_score}/100",
        f"*Company:* {co.company_name if co else 'n/a'} ({co.company_number if co else ''})",
        f"*Sector:* {co.sic_description or co.sic_code or 'n/a'}" if co else "",
        f"*Location:* {co.locality or co.postal_code or 'n/a'}" if co else "",
        (
            f"*Estimated value:* £{int(lead.estimated_value_gbp):,}/year"
            if lead.estimated_value_gbp
            else ""
        ),
        "",
        f"_{lead.summary or ''}_",
    ]
    body = "\n".join(b for b in bits if b)
    return title, body


def render_lead_email_html(lead: Lead) -> str:
    """Branded HTML email body. Editorial style, matches the dashboard."""
    co = lead.company
    emoji = URGENCY_EMOJI.get(lead.urgency, "·")
    company_name = co.company_name if co else "Company"
    cn = co.company_number if co else "—"
    category = lead.ai_category or lead.lead_type
    sector = (co.sic_description or co.sic_code or "—") if co else "—"
    location = (co.locality or co.postal_code or "—") if co else "—"
    value = (
        f"£{int(lead.estimated_value_gbp):,}/year"
        if lead.estimated_value_gbp
        else "—"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{company_name} · D&amp;A Compliance Radar</title>
</head>
<body style="margin:0;padding:0;background:#fdfcf8;font-family:Georgia,serif;color:#091428;">
  <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background:#fdfcf8;padding:40px 20px;">
    <tr><td align="center">
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="background:#ffffff;border:1px solid rgba(20,38,72,0.15);max-width:600px;">

        <!-- Header -->
        <tr><td style="background:#142648;padding:24px 32px;">
          <table width="100%"><tr>
            <td style="color:#f7f3e9;font-size:11px;letter-spacing:2px;text-transform:uppercase;font-family:'Helvetica Neue',sans-serif;">
              Compliance Radar
            </td>
            <td align="right" style="color:#c89b3c;font-size:11px;letter-spacing:2px;text-transform:uppercase;font-family:'Helvetica Neue',sans-serif;">
              {lead.urgency.upper()}
            </td>
          </tr></table>
        </td></tr>

        <!-- Title -->
        <tr><td style="padding:40px 32px 8px;">
          <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#506a8e;margin-bottom:8px;font-family:'Helvetica Neue',sans-serif;">
            New {lead.urgency} lead {emoji}
          </div>
          <h1 style="margin:0;font-size:32px;line-height:1.1;font-weight:500;color:#091428;font-family:Georgia,'Bodoni Moda',serif;">
            {company_name}
          </h1>
          <div style="color:#506a8e;font-size:13px;margin-top:8px;font-family:'Courier New',monospace;">
            {cn}
          </div>
        </td></tr>

        <!-- Summary -->
        <tr><td style="padding:24px 32px;">
          <p style="margin:0;font-size:15px;line-height:1.6;color:#1c3258;font-style:italic;">
            {lead.summary or ''}
          </p>
        </td></tr>

        <!-- Facts grid -->
        <tr><td style="padding:0 32px;">
          <table width="100%" cellspacing="0" cellpadding="0" style="border-top:1px solid rgba(20,38,72,0.12);">
            {_render_email_fact_rows([
              ("Category", category),
              ("Lead score", f"{lead.lead_score}/100"),
              ("Sector", sector),
              ("Location", location),
              ("Estimated value", value),
            ])}
          </table>
        </td></tr>

        <!-- CTA -->
        <tr><td style="padding:32px;">
          <a href="#" style="display:inline-block;background:#142648;color:#f7f3e9;padding:14px 28px;text-decoration:none;font-size:14px;font-family:'Helvetica Neue',sans-serif;font-weight:500;">
            Open in Compliance Radar →
          </a>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:24px 32px;background:#f7f3e9;border-top:1px solid rgba(20,38,72,0.1);">
          <table width="100%"><tr>
            <td style="font-size:11px;color:#506a8e;font-family:'Helvetica Neue',sans-serif;letter-spacing:1px;">
              Dennis &amp; Associates Accountants
            </td>
            <td align="right" style="font-size:11px;color:#506a8e;font-family:'Helvetica Neue',sans-serif;">
              Sent {datetime.now(timezone.utc).strftime('%d %b %Y · %H:%M UTC')}
            </td>
          </tr></table>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _render_email_fact_rows(facts: list[tuple[str, str]]) -> str:
    rows = []
    for label, value in facts:
        rows.append(
            f"""<tr>
              <td style="padding:12px 0;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#506a8e;font-family:'Helvetica Neue',sans-serif;width:40%;border-bottom:1px solid rgba(20,38,72,0.08);">{label}</td>
              <td style="padding:12px 0;font-size:14px;color:#091428;font-family:'Helvetica Neue',sans-serif;border-bottom:1px solid rgba(20,38,72,0.08);">{value}</td>
            </tr>"""
        )
    return "\n".join(rows)


# --- Channels ---

def send_slack(title: str, body: str) -> None:
    if not settings.slack_webhook_url:
        raise RuntimeError("SLACK_WEBHOOK_URL not configured")
    payload = {
        "text": title,
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": title}},
            {"type": "section", "text": {"type": "mrkdwn", "text": body}},
        ],
    }
    r = httpx.post(settings.slack_webhook_url, json=payload, timeout=10.0)
    r.raise_for_status()


def send_telegram(title: str, body: str) -> None:
    if not (settings.telegram_bot_token and settings.telegram_chat_id):
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not configured")
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    text = f"*{title}*\n\n{body}"
    r = httpx.post(
        url,
        json={
            "chat_id": settings.telegram_chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        },
        timeout=10.0,
    )
    r.raise_for_status()


def send_email_for_lead(lead: Lead, title: str) -> None:
    if not (settings.resend_api_key and settings.alert_to_email_list):
        raise RuntimeError("RESEND_API_KEY / ALERT_TO_EMAILS not configured")
    resend.api_key = settings.resend_api_key
    html = render_lead_email_html(lead)
    resend.Emails.send(
        {
            "from": settings.alert_from_email,
            "to": settings.alert_to_email_list,
            "subject": title,
            "html": html,
        }
    )


def dispatch_lead_alert(
    db: Session,
    lead: Lead,
    channels: Optional[list[str]] = None,
    alert_type: str = "high_value_lead",
) -> list[Alert]:
    title, body = render_lead_message(lead)
    selected = channels or _auto_select_channels()
    created: list[Alert] = []

    for channel in selected:
        alert = Alert(
            lead_id=lead.id,
            alert_channel=channel,
            alert_type=alert_type,
            payload=json.dumps({"title": title, "body": body}),
            sent_status=AlertStatus.PENDING.value,
        )
        db.add(alert)
        db.flush()
        try:
            if channel == AlertChannel.SLACK.value:
                send_slack(title, body)
            elif channel == AlertChannel.TELEGRAM.value:
                send_telegram(title, body)
            elif channel == AlertChannel.EMAIL.value:
                send_email_for_lead(lead, title)
            alert.sent_status = AlertStatus.SENT.value
            alert.sent_at = datetime.now(timezone.utc)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Alert %s failed", channel)
            alert.sent_status = AlertStatus.FAILED.value
            alert.error_message = str(exc)[:1000]
        created.append(alert)

    db.commit()
    return created


def _auto_select_channels() -> list[str]:
    selected: list[str] = []
    if settings.slack_webhook_url:
        selected.append(AlertChannel.SLACK.value)
    if settings.telegram_bot_token and settings.telegram_chat_id:
        selected.append(AlertChannel.TELEGRAM.value)
    if settings.resend_api_key and settings.alert_to_email_list:
        selected.append(AlertChannel.EMAIL.value)
    return selected
