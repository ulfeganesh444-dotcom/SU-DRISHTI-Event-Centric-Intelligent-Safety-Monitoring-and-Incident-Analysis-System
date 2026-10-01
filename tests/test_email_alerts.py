"""Email-alert tests (Step 6). No network, no real credentials, no DB writes.

A recording SMTP stub captures the MIME message so content is asserted for
real; TEST 5 uses a genuinely unreachable server to prove graceful failure.
"""
import sys
import smtplib
import tempfile
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.incident_store import TemporalStore
from src.incident_engine import IncidentEngine
from src.event_filter import EventFilter
from src.alerts.email_alert import EmailAlertDispatcher

TMP = Path(tempfile.gettempdir()) / "sudrishti_mailtest"
TMP.mkdir(exist_ok=True)
SHOT = TMP / "evidence.jpg"
cv2.imwrite(str(SHOT), np.zeros((10, 10, 3), dtype=np.uint8))


class FakeSMTP:
    sent_messages = []

    def __init__(self, *a, **k):
        pass

    def starttls(self):
        pass

    def login(self, *a):
        pass

    def send_message(self, msg):
        FakeSMTP.sent_messages.append(msg)

    def quit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def make_store(email_fn, mode="proposed"):
    eng = IncidentEngine(required_frames={"intrusion": 3, "person": 5},
                         cooldowns={"intrusion": 0.0, "person": 0.0})
    fil = EventFilter(important_objects={"intrusion", "person"},
                      min_confidence=0.40, default_cooldown=0.0,
                      critical_cooldown=0.0)
    ids = {"n": 0}

    def save(*a, **k):
        ids["n"] += 1
        return ids["n"]

    return TemporalStore(mode=mode, engine=eng, event_filter=fil,
                         save_fn=save, update_fn=lambda *a, **k: None,
                         capture_fn=lambda f, n: str(SHOT),
                         dispatcher=configured_dispatcher(), fps=10.0), ids


def intrusion(store, tid, frames, start=0):
    return [store.observe("intrusion", 0.9, track_id=tid, frame_idx=f,
                          source="test", in_restricted_zone=True)
            for f in range(start, start + frames)]


def configured_dispatcher():
    return EmailAlertDispatcher(smtp_server="smtp.gmail.com", smtp_port=587,
                                sender_email="sender@example.com",
                                sender_password="dummy",
                                default_recipient="guard@example.com")


def test_1_noise_no_email():
    real = smtplib.SMTP
    smtplib.SMTP = FakeSMTP
    try:
        FakeSMTP.sent_messages = []
        d = configured_dispatcher()
        s, _ = make_store(d.send_alert)
        s.observe("intrusion", 0.9, track_id=1, frame_idx=0, source="test",
                  in_restricted_zone=True)  # single noisy frame
        assert s.rows_created == 0 and len(FakeSMTP.sent_messages) == 0
        print("[PASS] TEST 1: noisy single detection -> no row, no email")
    finally:
        smtplib.SMTP = real


def test_2_one_email_with_content():
    real = smtplib.SMTP
    smtplib.SMTP = FakeSMTP
    try:
        FakeSMTP.sent_messages = []
        d = configured_dispatcher()
        s, _ = make_store(d.send_alert)
        intrusion(s, 1, 6)
        assert s.rows_created == 1
        assert len(FakeSMTP.sent_messages) == 1, "exactly one email"
        msg = FakeSMTP.sent_messages[0]
        assert msg["Subject"] == \
            "SU-DRISHTI | Confirmed Safety Incident: INTRUSION [CRITICAL]", msg["Subject"]
        assert msg["To"] == "guard@example.com"
        parts = {p.get_content_type(): p for p in msg.walk()}
        body = parts["text/plain"].get_payload(decode=True).decode()
        for needle in ("Incident Type", "Confidence", "Start Time", "End Time",
                         "Duration", "Source", "Status: CONFIRMED", "Risk:",
                         "Evidence image is attached", "test"):
            assert needle in body, needle
        assert "image/jpeg" in parts, "evidence attached"
        print("[PASS] TEST 2: confirmed incident -> exactly 1 email, "
              "subject/body/attachment verified")
    finally:
        smtplib.SMTP = real


def test_3_continuation_no_resend():
    real = smtplib.SMTP
    smtplib.SMTP = FakeSMTP
    try:
        FakeSMTP.sent_messages = []
        d = configured_dispatcher()
        s, _ = make_store(d.send_alert)
        intrusion(s, 1, 200)  # same incident, 200 frames
        assert s.rows_created == 1
        assert len(FakeSMTP.sent_messages) == 1, "still exactly one email"
        print("[PASS] TEST 3: 200-frame continuation -> still 1 email")
    finally:
        smtplib.SMTP = real


def test_4_new_incident_new_email():
    real = smtplib.SMTP
    smtplib.SMTP = FakeSMTP
    try:
        FakeSMTP.sent_messages = []
        d = configured_dispatcher()
        s, _ = make_store(d.send_alert)
        intrusion(s, 1, 6, start=0)
        intrusion(s, 1, 6, start=500)  # long gap -> genuinely new incident
        assert s.rows_created == 2
        assert len(FakeSMTP.sent_messages) == 2, "one email per incident"
        print("[PASS] TEST 4: new incident after gap -> second email")
    finally:
        smtplib.SMTP = real


def test_5_smtp_failure_graceful():
    # genuinely unreachable server, no mocks: must return False, not raise
    d = EmailAlertDispatcher(smtp_server="127.0.0.1", smtp_port=1,
                             sender_email="a@b.c", sender_password="x",
                             default_recipient="r@s.t")
    assert d.send_alert("intrusion", 0.9, "2026-10-01 10:00:00",
                        str(SHOT), "HIGH") is False
    # store keeps the row and continues even if the callback itself raises
    def boom(incident):
        raise RuntimeError("smtp down")

    eng = IncidentEngine(required_frames={"intrusion": 3, "person": 5},
                         cooldowns={"intrusion": 0.0, "person": 0.0})
    fil = EventFilter(important_objects={"intrusion", "person"},
                      min_confidence=0.40, default_cooldown=0.0,
                      critical_cooldown=0.0)
    ids = {"n": 0}

    def save(*a, **k):
        ids["n"] += 1
        return ids["n"]

    s = TemporalStore(engine=eng, event_filter=fil, save_fn=save,
                      update_fn=lambda *a, **k: None,
                      capture_fn=lambda f, n: str(SHOT),
                      email_sender=boom, fps=10.0)
    outs = intrusion(s, 1, 6)
    assert ids["n"] == 1, "incident still saved"
    created = [o for o in outs if o["action"] == "created"]
    assert len(created) == 1
    assert created[0].get("alert_status") == "failed"
    print("[PASS] TEST 5: SMTP failure -> False, row saved, pipeline continues")


if __name__ == "__main__":
    test_1_noise_no_email()
    test_2_one_email_with_content()
    test_3_continuation_no_resend()
    test_4_new_incident_new_email()
    test_5_smtp_failure_graceful()
    print("--- EMAIL ALERT TESTS PASSED ---")
