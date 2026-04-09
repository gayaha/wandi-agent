"""Render failure alerts — sends email notifications on critical pipeline errors.

Uses Resend HTTP API (no SDK needed, just httpx).
Set RESEND_API_KEY and ALERT_EMAIL_TO in env to enable.
When not configured, alerts are logged but not sent.
"""

import logging
from typing import Any

import httpx

import config

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_render_failure_alert(
    record_id: str,
    error: str,
    context: dict[str, Any] | None = None,
) -> None:
    """Send email alert when a render fails after retries.

    Args:
        record_id: Airtable record ID that failed.
        error: Error message describing the failure.
        context: Optional dict with extra info (client_id, batch_id, etc).
    """
    if not config.RESEND_API_KEY or not config.ALERT_EMAIL_TO:
        logger.warning(
            f"[alert] Render failure for {record_id} — alert not sent "
            f"(RESEND_API_KEY or ALERT_EMAIL_TO not configured)"
        )
        return

    ctx = context or {}
    client_name = ctx.get("client_name", "unknown")
    batch_id = ctx.get("batch_id", "N/A")
    video_url = ctx.get("video_url", "N/A")

    subject = f"Wandi Render Failure — {record_id}"

    html_body = f"""
    <div style="font-family: sans-serif; direction: rtl; text-align: right;">
        <h2 style="color: #e53e3e;">כשלון רנדר</h2>
        <table style="border-collapse: collapse; width: 100%;">
            <tr><td style="padding: 8px; font-weight: bold;">Record ID:</td>
                <td style="padding: 8px; direction: ltr;">{record_id}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Client:</td>
                <td style="padding: 8px;">{client_name}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Batch:</td>
                <td style="padding: 8px; direction: ltr;">{batch_id}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Error:</td>
                <td style="padding: 8px; color: #e53e3e; direction: ltr;">{error}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Video URL (if uploaded):</td>
                <td style="padding: 8px; direction: ltr;">{video_url}</td></tr>
        </table>
        <p style="margin-top: 16px; color: #718096;">
            הוידאו רונדר אבל לא נשמר בצורה תקינה.
            יש לבדוק את הלוגים ולעדכן ידנית אם צריך.
        </p>
    </div>
    """

    payload = {
        "from": config.ALERT_EMAIL_FROM,
        "to": [config.ALERT_EMAIL_TO],
        "subject": subject,
        "html": html_body,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {config.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            logger.info(f"[alert] Render failure email sent for {record_id}")
    except Exception as e:
        logger.error(f"[alert] Failed to send email for {record_id}: {e}")


async def send_airtable_failure_alert(
    record_id: str,
    video_url: str,
    error: str,
    context: dict[str, Any] | None = None,
) -> None:
    """Send email alert when Airtable update fails after retries.

    The video was rendered and uploaded successfully but couldn't be saved
    to Airtable. Includes the video URL so the team can fix manually.
    """
    if not config.RESEND_API_KEY or not config.ALERT_EMAIL_TO:
        logger.warning(
            f"[alert] Airtable failure for {record_id} — alert not sent "
            f"(RESEND_API_KEY or ALERT_EMAIL_TO not configured)"
        )
        return

    ctx = context or {}
    client_name = ctx.get("client_name", "unknown")

    subject = f"Wandi Airtable Update Failed — {record_id}"

    html_body = f"""
    <div style="font-family: sans-serif; direction: rtl; text-align: right;">
        <h2 style="color: #dd6b20;">כשלון עדכון Airtable</h2>
        <p>הוידאו רונדר בהצלחה אבל לא נשמר ב-Airtable.</p>
        <table style="border-collapse: collapse; width: 100%;">
            <tr><td style="padding: 8px; font-weight: bold;">Record ID:</td>
                <td style="padding: 8px; direction: ltr;">{record_id}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Client:</td>
                <td style="padding: 8px;">{client_name}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Error:</td>
                <td style="padding: 8px; color: #e53e3e; direction: ltr;">{error}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Video URL:</td>
                <td style="padding: 8px; direction: ltr;">
                    <a href="{video_url}">{video_url[:80]}...</a>
                </td></tr>
        </table>
        <p style="margin-top: 16px; color: #718096;">
            יש לעדכן את הרקורד ב-Airtable ידנית עם ה-URL למעלה.
        </p>
    </div>
    """

    payload = {
        "from": config.ALERT_EMAIL_FROM,
        "to": [config.ALERT_EMAIL_TO],
        "subject": subject,
        "html": html_body,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {config.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            logger.info(f"[alert] Airtable failure email sent for {record_id}")
    except Exception as e:
        logger.error(f"[alert] Failed to send email for {record_id}: {e}")
