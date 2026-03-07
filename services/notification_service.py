from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.engine import Engine


class SMSProvider(Protocol):
    def send_sms(self, phone_number: str, message: str) -> tuple[bool, str]:
        """Return success and provider response."""


class EmailProvider(Protocol):
    def send_email(self, email_address: str, subject: str, body: str) -> tuple[bool, str]:
        """Return success and provider response."""


class NoOpSMSProvider:
    def send_sms(self, phone_number: str, message: str) -> tuple[bool, str]:
        return True, "no-op provider"


class NoOpEmailProvider:
    def send_email(self, email_address: str, subject: str, body: str) -> tuple[bool, str]:
        return True, "no-op provider"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _is_valid_phone(value: str | None) -> bool:
    if not value:
        return False
    digits = re.sub(r"\D", "", value)
    return len(digits) >= 10


def _is_valid_email(value: str | None) -> bool:
    if not value:
        return False
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value) is not None


def _log_notification(
    engine: Engine,
    appointment_key: str,
    channel: str,
    status: str,
    provider: str,
    event_type: str,
    performed_by: str,
    response_payload: str | None = None,
    error_message: str | None = None,
    sent_at: str | None = None,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO gt_notification_log (
                    log_id, appointment_key, channel, status, provider,
                    sent_at, error_message, response_payload, event_type, performed_by
                ) VALUES (
                    :log_id, :appointment_key, :channel, :status, :provider,
                    :sent_at, :error_message, :response_payload, :event_type, :performed_by
                )
                """
            ),
            {
                "log_id": str(uuid.uuid4()),
                "appointment_key": appointment_key,
                "channel": channel,
                "status": status,
                "provider": provider,
                "sent_at": sent_at,
                "error_message": error_message,
                "response_payload": response_payload,
                "event_type": event_type,
                "performed_by": performed_by,
            },
        )


def _fetch_appointment(engine: Engine, appointment_key: str):
    q = text(
        """
        SELECT appointment_key, first_name, last_name, testing_datetime, location,
               mobile_phone, email_address, preferred_contact_method,
               sms_opt_in, email_opt_in, last_sms_sent_at, last_email_sent_at
        FROM gt_appointments
        WHERE appointment_key = :appointment_key
        """
    )
    with engine.begin() as conn:
        return conn.execute(q, {"appointment_key": appointment_key}).mappings().one_or_none()


def send_checkin_sms(
    engine: Engine,
    appointment_key: str,
    message: str,
    provider: SMSProvider | None = None,
    performed_by: str = "SYSTEM",
) -> dict:
    appt = _fetch_appointment(engine, appointment_key)
    if not appt:
        return {"status": "failed", "reason": "Appointment not found"}

    if appt.get("last_sms_sent_at"):
        _log_notification(
            engine,
            appointment_key,
            "sms",
            "skipped",
            "system",
            "checkin_notification",
            performed_by,
            error_message="Duplicate prevention: SMS already sent for this appointment.",
        )
        return {"status": "skipped", "reason": "SMS already sent"}

    if not bool(appt.get("sms_opt_in")):
        _log_notification(
            engine,
            appointment_key,
            "sms",
            "skipped",
            "system",
            "checkin_notification",
            performed_by,
            error_message="SMS opt-in is not enabled.",
        )
        return {"status": "skipped", "reason": "SMS opt-in disabled"}

    phone = appt.get("mobile_phone")
    if not _is_valid_phone(phone):
        _log_notification(
            engine,
            appointment_key,
            "sms",
            "failed",
            "system",
            "checkin_notification",
            performed_by,
            error_message="Missing or invalid mobile phone.",
        )
        return {"status": "failed", "reason": "Missing or invalid mobile phone"}

    sms_provider = provider or NoOpSMSProvider()
    ok, response = sms_provider.send_sms(phone_number=str(phone), message=message)
    sent_at = _now() if ok else None

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE gt_appointments
                SET last_sms_sent_at = :last_sms_sent_at,
                    sms_status = :sms_status,
                    notification_error = :notification_error
                WHERE appointment_key = :appointment_key
                """
            ),
            {
                "appointment_key": appointment_key,
                "last_sms_sent_at": sent_at,
                "sms_status": "sent" if ok else "failed",
                "notification_error": None if ok else response,
            },
        )

    _log_notification(
        engine,
        appointment_key,
        "sms",
        "sent" if ok else "failed",
        type(sms_provider).__name__,
        "checkin_notification",
        performed_by,
        response_payload=response,
        error_message=None if ok else response,
        sent_at=sent_at,
    )
    return {"status": "sent" if ok else "failed", "response": response}


def send_checkin_email(
    engine: Engine,
    appointment_key: str,
    subject: str,
    body: str,
    provider: EmailProvider | None = None,
    performed_by: str = "SYSTEM",
) -> dict:
    appt = _fetch_appointment(engine, appointment_key)
    if not appt:
        return {"status": "failed", "reason": "Appointment not found"}

    if appt.get("last_email_sent_at"):
        _log_notification(
            engine,
            appointment_key,
            "email",
            "skipped",
            "system",
            "checkin_notification",
            performed_by,
            error_message="Duplicate prevention: Email already sent for this appointment.",
        )
        return {"status": "skipped", "reason": "Email already sent"}

    if not bool(appt.get("email_opt_in")):
        _log_notification(
            engine,
            appointment_key,
            "email",
            "skipped",
            "system",
            "checkin_notification",
            performed_by,
            error_message="Email opt-in is not enabled.",
        )
        return {"status": "skipped", "reason": "Email opt-in disabled"}

    email = appt.get("email_address")
    if not _is_valid_email(email):
        _log_notification(
            engine,
            appointment_key,
            "email",
            "failed",
            "system",
            "checkin_notification",
            performed_by,
            error_message="Missing or invalid email address.",
        )
        return {"status": "failed", "reason": "Missing or invalid email"}

    email_provider = provider or NoOpEmailProvider()
    ok, response = email_provider.send_email(email_address=str(email), subject=subject, body=body)
    sent_at = _now() if ok else None

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE gt_appointments
                SET last_email_sent_at = :last_email_sent_at,
                    email_status = :email_status,
                    notification_error = :notification_error
                WHERE appointment_key = :appointment_key
                """
            ),
            {
                "appointment_key": appointment_key,
                "last_email_sent_at": sent_at,
                "email_status": "sent" if ok else "failed",
                "notification_error": None if ok else response,
            },
        )

    _log_notification(
        engine,
        appointment_key,
        "email",
        "sent" if ok else "failed",
        type(email_provider).__name__,
        "checkin_notification",
        performed_by,
        response_payload=response,
        error_message=None if ok else response,
        sent_at=sent_at,
    )
    return {"status": "sent" if ok else "failed", "response": response}


def build_checkin_sms_message(appt: dict) -> str:
    return (
        f"OCSS Check-In Confirmed: {appt.get('testing_datetime', '')}. "
        f"Location: {appt.get('location') or 'OCSS Lobby'}."
    )


def build_checkin_email_message(appt: dict) -> tuple[str, str]:
    subject = "OCSS Genetic Testing Check-In Confirmation"
    body = (
        "Your check-in is confirmed.\n"
        f"Appointment: {appt.get('testing_datetime', '')}\n"
        f"Location: {appt.get('location') or 'OCSS Lobby'}\n"
    )
    return subject, body


def send_checkin_notifications(engine: Engine, appointment_key: str, performed_by: str = "SYSTEM") -> dict:
    appt = _fetch_appointment(engine, appointment_key)
    if not appt:
        return {"sms": {"status": "failed"}, "email": {"status": "failed"}}

    pref = str(appt.get("preferred_contact_method") or "none").lower()
    sms_message = build_checkin_sms_message(dict(appt))
    email_subject, email_body = build_checkin_email_message(dict(appt))

    results = {}
    if pref in {"sms", "both"}:
        results["sms"] = send_checkin_sms(
            engine=engine,
            appointment_key=appointment_key,
            message=sms_message,
            performed_by=performed_by,
        )
    else:
        results["sms"] = {"status": "skipped", "reason": "Preference disabled"}

    if pref in {"email", "both"}:
        results["email"] = send_checkin_email(
            engine=engine,
            appointment_key=appointment_key,
            subject=email_subject,
            body=email_body,
            performed_by=performed_by,
        )
    else:
        results["email"] = {"status": "skipped", "reason": "Preference disabled"}

    _log_notification(
        engine,
        appointment_key,
        "system",
        "completed",
        "workflow",
        "checkin_notification",
        performed_by,
        response_payload=json.dumps(results),
    )
    return results


def resend_checkin_notifications(engine: Engine, appointment_key: str, performed_by: str = "STAFF") -> dict:
    """Force a resend by clearing prior sent timestamps first."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE gt_appointments
                SET last_sms_sent_at = NULL,
                    last_email_sent_at = NULL,
                    sms_status = NULL,
                    email_status = NULL,
                    notification_error = NULL
                WHERE appointment_key = :appointment_key
                """
            ),
            {"appointment_key": appointment_key},
        )

    _log_notification(
        engine,
        appointment_key,
        "system",
        "queued",
        "workflow",
        "checkin_notification_resend",
        performed_by,
        response_payload="Manual resend requested by staff.",
    )
    return send_checkin_notifications(engine, appointment_key, performed_by=performed_by)
