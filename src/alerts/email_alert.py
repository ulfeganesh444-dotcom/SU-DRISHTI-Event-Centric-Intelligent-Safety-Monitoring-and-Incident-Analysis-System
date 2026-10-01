"""
Email Alert Dispatcher for SU-DRISHTI.
Sends urgent safety incident notifications with attached forensic screenshot evidence.

Note:
Requires standard SMTP credentials (e.g. Gmail App Password).
If credentials are not configured, runs in audit simulation mode.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()  # reads project .env if present; missing file is fine
except ImportError:  # python-dotenv optional; plain env vars still work
    pass


def _env(*names: str, default: str = "") -> str:
    """First set variable wins (new EMAIL_* names take precedence)."""
    for n in names:
        v = os.getenv(n, "")
        if v:
            return v
    return default


class EmailAlertDispatcher:
    """Dispatches emergency email alerts with visual evidence attachment."""

    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None,
        default_recipient: Optional[str] = None
    ):
        self.smtp_server = smtp_server or _env("SMTP_SERVER", "SENTINEL_SMTP_SERVER",
                                                 default="smtp.gmail.com")
        self.smtp_port = int(smtp_port or _env("SMTP_PORT", "SENTINEL_SMTP_PORT",
                                               default="587"))
        self.sender_email = sender_email or _env("EMAIL_SENDER", "SENTINEL_SENDER_EMAIL")
        self.sender_password = sender_password or _env("EMAIL_PASSWORD", "SENTINEL_SENDER_PASS")
        self.default_recipient = default_recipient or _env("EMAIL_RECEIVER",
                                                           "SENTINEL_ALERT_RECIPIENT")

    def is_configured(self) -> bool:
        """Returns True if sender credentials and recipient are populated."""
        return bool(self.sender_email and self.sender_password and self.default_recipient)

    def send_alert(
        self,
        object_name: str,
        confidence: float,
        event_time: str,
        image_path: str,
        severity: str = "CRITICAL",
        recipient: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        duration_sec: float = 0.0,
        source: str = "",
        status: str = "CONFIRMED",
        subject: Optional[str] = None,
    ) -> bool:
        """
        Send an email notification for a CONFIRMED safety incident.

        Call only after temporal verification confirms the incident; the
        incident store guarantees one call per confirmed incident. Extra
        incident fields are optional so older call sites keep working.

        Returns:
            bool: True if the SMTP server accepted the message, else False.
            Never raises: failures are logged and returned, so video
            analysis, database writes and the dashboard keep running.
        """
        target_recipient = recipient or self.default_recipient

        if not self.is_configured():
            print(
                f"[ALERT SIMULATION] Email notification for {severity} event '{object_name}' "
                f"at {event_time}. (SMTP not configured. Provide credentials to enable live sending)."
            )
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = target_recipient
            msg["Subject"] = subject or (f"SU-DRISHTI | Confirmed Safety Incident: "
                                               f"{object_name.upper()} [{severity}]")

            # Evidence pre-check first: the attached-line is only claimed when
            # a real file is attached.
            img_file = Path(image_path) if image_path else None
            attached = bool(img_file is not None and img_file.exists())

            body = f"""SU-DRISHTI
Event-Centric Intelligent Safety Monitoring

A safety incident has been confirmed.

Incident Type: {object_name.upper()}
Confidence: {confidence:.2f}
Start Time: {start_time or event_time}
End Time: {end_time or event_time}
Duration: {duration_sec:.1f} s
Source: {source or 'unknown'}
Status: {status}
Risk: {severity}
Evidence ref: {image_path or 'none captured'}
"""
            if attached:
                body += "\nEvidence image is attached to this email.\n"
            body += ("\nPlease review the incident and take appropriate action.\n\n"
                     "This email was generated automatically by SU-DRISHTI.\n")
            msg.attach(MIMEText(body, "plain"))

            if attached:
                with open(img_file, "rb") as f:
                    img_data = f.read()
                    image_attachment = MIMEImage(img_data, name=img_file.name)
                    msg.attach(image_attachment)

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            print(f"[EMAIL ALERT SENT] Dispatched to {target_recipient}")
            return True

        except Exception as e:
            print(f"[ALERT ERROR] Failed to send email alert: {e}")
            return False


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def send_incident_email(incident: dict,
                        dispatcher: Optional["EmailAlertDispatcher"] = None,
                        recipient: Optional[str] = None) -> str:
    """Send ONE email for ONE confirmed incident. Never raises.

    Steps (spec): take confirmed incident facts -> resolve the real evidence
    file -> refuse to send when evidence is missing -> send via dispatcher ->
    return status. Passwords never appear in logs (only the incident type,
    recipient address and error text are printed).

    Args:
        incident: dict with event_type/object_name, confidence,
            start_time/event_time, end_time, duration_sec, source,
            risk_level/severity, status, image_path/evidence_path.
        dispatcher: EmailAlertDispatcher (default: fresh one from env).
        recipient: override recipient address.

    Returns:
        "SENT" | "FAILED" | "NOT_SENT" (not configured).
    """
    d = dispatcher or EmailAlertDispatcher()
    itype = str(incident.get("event_type") or incident.get("object_name") or "unknown")

    if not d.is_configured():
        print(f"[ALERT SIMULATION] '{itype}' confirmed but SMTP not configured; "
              f"email NOT_SENT. Set EMAIL_SENDER/EMAIL_PASSWORD/EMAIL_RECEIVER.")
        return "NOT_SENT"

    raw_path = str(incident.get("image_path") or incident.get("evidence_path") or "")
    resolved: Optional[Path] = None
    for cand in (Path(raw_path), PROJECT_ROOT / raw_path):
        if raw_path and cand.exists() and cand.is_file():
            resolved = cand
            break
    if resolved is None:
        print(f"[ALERT ERROR] Evidence not found for '{itype}': '{raw_path}'. "
              f"Email not sent; incident record and evidence handling continue.")
        return "FAILED"

    try:
        ok = d.send_alert(
            itype,
            float(incident.get("confidence", 0.0) or 0.0),
            str(incident.get("event_time") or incident.get("start_time") or ""),
            str(resolved),
            str(incident.get("risk_level") or incident.get("severity") or "MEDIUM"),
            recipient=recipient or incident.get("recipient") or None,
            start_time=str(incident.get("start_time") or ""),
            end_time=str(incident.get("end_time") or ""),
            duration_sec=float(incident.get("duration_sec", 0.0) or 0.0),
            source=str(incident.get("source") or ""),
            status=str(incident.get("status") or "CONFIRMED"),
        )
        return "SENT" if ok else "FAILED"
    except Exception as e:
        print(f"[ALERT ERROR] send_incident_email failed for '{itype}': {e}")
        return "FAILED"
