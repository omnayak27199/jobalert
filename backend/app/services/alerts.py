from __future__ import annotations

"""Email and WhatsApp alert delivery for matching jobs."""

import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

import httpx
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.job import Job
from app.models.user import AlertLog, User, UserPreferences
from app.services.job_matcher import job_matches_user, score_job_for_user

logger = logging.getLogger(__name__)


def _parse_json_list(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def job_matches_preferences(job: Job, prefs: UserPreferences) -> bool:
    from app.services.job_matcher import job_matches_preferences as _match

    return _match(job, prefs)


def get_matching_users(db: Session, job: Job) -> List[User]:
    users = (
        db.query(User)
        .options(joinedload(User.preferences), joinedload(User.profile))
        .filter(User.is_active == True)  # noqa: E712
        .all()
    )
    matched = []
    for user in users:
        if job_matches_user(job, user):
            matched.append(user)
    return matched


def _already_sent(db: Session, user_id: int, job_id: int, channel: str) -> bool:
    return (
        db.query(AlertLog)
        .filter(
            AlertLog.user_id == user_id,
            AlertLog.job_id == job_id,
            AlertLog.channel == channel,
        )
        .first()
        is not None
    )


def _log_alert(db: Session, user_id: int, job_id: int, channel: str) -> None:
    db.add(AlertLog(user_id=user_id, job_id=job_id, channel=channel))


def _format_job_email(jobs: List[Job], user: User) -> str:
    lines = ["<h2>Jobs matching your profile — IndiaJob.in</h2>", "<ul>"]
    for job in jobs:
        last = job.last_date.strftime("%d %b %Y") if job.last_date else "Check notification"
        match = score_job_for_user(job, user)
        reason = match.reasons[0] if match.reasons else "Profile match"
        lines.append(
            f"<li><strong>{job.title}</strong> ({match.score}% match — {reason})<br>"
            f"Org: {job.organization} | Last Date: {last}<br>"
            f'<a href="https://indiajob.in/job/{job.id}">View Full Details</a></li>'
        )
    lines.append("</ul><p><small>Update profile at indiajob.in/account</small></p>")
    return "\n".join(lines)


def send_email(to: str, subject: str, html_body: str) -> bool:
    if not settings.smtp_host or not settings.smtp_user:
        logger.info("SMTP not configured — would email %s: %s", to, subject)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password or "")
            server.sendmail(settings.smtp_from, to, msg.as_string())
        return True
    except Exception as e:
        logger.error("Email send failed to %s: %s", to, e)
        return False


def send_whatsapp(phone: str, message: str) -> bool:
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.info("Twilio not configured — would WhatsApp %s: %s", phone, message[:80])
        return False
    try:
        to = phone if phone.startswith("whatsapp:") else f"whatsapp:+91{phone.lstrip('+')}"
        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{settings.twilio_account_sid}/Messages.json"
        )
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                data={
                    "From": settings.twilio_whatsapp_from,
                    "To": to,
                    "Body": message,
                },
            )
            response.raise_for_status()
        return True
    except Exception as e:
        logger.error("WhatsApp send failed to %s: %s", phone, e)
        return False


def _format_whatsapp(jobs: List[Job], user: User) -> str:
    lines = ["🔔 *IndiaJob.in — Matches for your profile*\n"]
    for job in jobs[:5]:
        last = job.last_date.strftime("%d %b %Y") if job.last_date else "See notification"
        match = score_job_for_user(job, user)
        lines.append(f"• *{job.title}* ({match.score}%)\n  {job.organization} | Last: {last}")
    if len(jobs) > 5:
        lines.append(f"\n+{len(jobs) - 5} more at indiajob.in/account")
    return "\n".join(lines)


async def dispatch_alerts_for_new_jobs(db: Session, new_jobs: List[Job]) -> dict:
    """Send personalized alerts when new jobs match candidate profiles."""
    email_sent = 0
    whatsapp_sent = 0

    user_job_map: dict[int, List[Job]] = {}

    for job in new_jobs:
        for user in get_matching_users(db, job):
            user_job_map.setdefault(user.id, []).append(job)

    for user_id, jobs in user_job_map.items():
        user = (
            db.query(User)
            .options(joinedload(User.preferences), joinedload(User.profile))
            .filter(User.id == user_id)
            .first()
        )
        if not user or not user.preferences:
            continue

        prefs = user.preferences
        pending_email = [
            j for j in jobs
            if prefs.email_alerts and not _already_sent(db, user.id, j.id, "email")
        ]
        pending_wa = [
            j for j in jobs
            if prefs.whatsapp_alerts and user.phone
            and not _already_sent(db, user.id, j.id, "whatsapp")
        ]

        if pending_email:
            ok = send_email(
                user.email,
                f"IndiaJob: {len(pending_email)} job(s) matching your profile",
                _format_job_email(pending_email, user),
            )
            if ok:
                for j in pending_email:
                    _log_alert(db, user.id, j.id, "email")
                email_sent += 1

        if pending_wa:
            ok = send_whatsapp(user.phone, _format_whatsapp(pending_wa, user))
            if ok:
                for j in pending_wa:
                    _log_alert(db, user.id, j.id, "whatsapp")
                whatsapp_sent += 1

    db.commit()
    return {"email_users": email_sent, "whatsapp_users": whatsapp_sent}
