"""Email send-path tests: evidence gate, all-confirmed policy, secrecy."""
import io
import sys
import smtplib
from contextlib import redirect_stdout
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test_email_alerts import FakeSMTP, configured_dispatcher, intrusion  # noqa
from src.incident_store import TemporalStore
from src.incident_engine import IncidentEngine
from src.event_filter import EventFilter
from src.alerts.email_alert import send_incident_email


def test_E_missing_evidence_no_send():
    real = smtplib.SMTP
    smtplib.SMTP = FakeSMTP
    try:
        FakeSMTP.sent_messages = []
        buf = io.StringIO()
        with redirect_stdout(buf):
            status = send_incident_email(
                {"event_type": "fire", "confidence": 0.9,
                 "event_time": "2026-10-01 10:00:00",
                 "image_path": "screenshots/does_not_exist_xyz.jpg",
                 "risk_level": "CRITICAL", "status": "CONFIRMED"},
                dispatcher=configured_dispatcher())
        assert status == "FAILED", status
        assert len(FakeSMTP.sent_messages) == 0, "must not send without evidence"
        assert "not found" in buf.getvalue().lower()
        print("[PASS] TEST E: missing evidence -> no send, FAILED logged")
    finally:
        smtplib.SMTP = real


def test_all_confirmed_low_emails():
    real = smtplib.SMTP
    smtplib.SMTP = FakeSMTP
    try:
        FakeSMTP.sent_messages = []
        eng = IncidentEngine(required_frames={"person": 2}, cooldowns={"person": 0.0})
        fil = EventFilter(important_objects={"person"}, min_confidence=0.40,
                          default_cooldown=0.0, critical_cooldown=0.0)
        ids = {"n": 0}
        s = TemporalStore(engine=eng, event_filter=fil,
                          save_fn=lambda *a, **k: (ids.__setitem__("n", ids["n"] + 1),
                                                   ids["n"])[1],
                          update_fn=lambda *a, **k: None,
                          capture_fn=lambda f, n: str(
                              Path(__file__).resolve().parent / "LUT_never_used"),
                          dispatcher=configured_dispatcher(), fps=10.0)
        # use tmp evidence that exists
        import test_email_alerts as T
        s.capture_fn = lambda f, n: str(T.SHOT)
        for f in range(4):
            s.observe("person", 0.9, track_id=1, frame_idx=f, source="test")
        assert s.rows_created == 1
        assert len(FakeSMTP.sent_messages) == 1, "LOW confirmed still emails once"
        print("[PASS] all-confirmed: LOW person incident -> exactly 1 email")
    finally:
        smtplib.SMTP = real


def test_password_never_logged():
    # real smtplib against an unreachable server: genuine failure path
    from src.alerts.email_alert import EmailAlertDispatcher
    d = EmailAlertDispatcher(smtp_server="127.0.0.1", smtp_port=1,
                             sender_email="a@b.c",
                             sender_password="SUPERSECRET123",
                             default_recipient="r@s.t")
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert d.send_alert("fire", 0.9, "2026-10-01 10:00:00",
                            "screenshots/nope.jpg", "CRITICAL") is False
    assert "SUPERSECRET123" not in buf.getvalue(), "password leaked!"
    print("[PASS] password never appears in logs")


if __name__ == "__main__":
    test_E_missing_evidence_no_send()
    test_all_confirmed_low_emails()
    test_password_never_logged()
    print("--- EMAIL SEND-PATH TESTS PASSED ---")
