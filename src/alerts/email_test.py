"""Manual SMTP verification for SU-DRISHTI (Step 8).

Sends "SU-DRISHTI | Email Test" with the newest REAL evidence image from
screenshots/, without requiring YOLO or a real incident:

    python -m src.alerts.email_test [--to guard@example.com]

Exit codes: 0 = SENT (check the inbox), 1 = FAILED, 2 = NOT_SENT (no creds).
Needs EMAIL_SENDER / EMAIL_PASSWORD / EMAIL_RECEIVER in env or project .env.
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.alerts.email_alert import EmailAlertDispatcher


def newest_evidence() -> Path | None:
    shots = sorted((PROJECT_ROOT / "screenshots").glob("*.jpg"),
                   key=lambda p: p.stat().st_mtime)
    return shots[-1] if shots else None


def main() -> int:
    ap = argparse.ArgumentParser(description="SU-DRISHTI manual email test")
    ap.add_argument("--to", default=None, help="override recipient address")
    args = ap.parse_args()

    d = EmailAlertDispatcher()
    print(f"[CONFIG] server={d.smtp_server}:{d.smtp_port} "
          f"sender={'set' if d.sender_email else 'MISSING'} "
          f"recipient={args.to or d.default_recipient or 'MISSING'}")

    shot = newest_evidence()
    if shot is None:
        print("[ALERT ERROR] no evidence images in screenshots/; run analysis first.")
        return 1
    print(f"[EVIDENCE] {shot.name}")

    ok = d.send_alert("email-test", 1.0, "manual-test", str(shot), "MEDIUM",
                      recipient=args.to or None, source="manual SMTP test",
                      status="CONFIRMED",
                      subject="SU-DRISHTI | Email Test")
    if ok:
        print("[RESULT] SENT — check the recipient inbox (with attachment).")
        return 0
    if not d.is_configured():
        print("[RESULT] NOT_SENT — set EMAIL_SENDER/EMAIL_PASSWORD/EMAIL_RECEIVER.")
        return 2
    print("[RESULT] FAILED — see [ALERT ERROR] above (password never printed).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
