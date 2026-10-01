"""Tests for IncidentEngine: verification states, risk levels, dedup cooldown."""
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.incident_engine import IncidentEngine


def test_verification_lifecycle():
    e = IncidentEngine(required_frames={"intrusion": 3}, cooldowns={"intrusion": 60})
    r1 = e.process_event("intrusion", 0.86, track_id=1, in_restricted_zone=True)
    assert r1["state"] == "SUSPECTED", r1
    assert not r1["should_alert"]
    r2 = e.process_event("intrusion", 0.88, track_id=1, in_restricted_zone=True)
    assert r2["state"] == "VERIFYING", r2
    assert not r2["should_alert"]
    r3 = e.process_event("intrusion", 0.90, track_id=1, in_restricted_zone=True)
    assert r3["state"] == "CONFIRMED", r3
    assert r3["should_alert"], "3rd consecutive frame must confirm + alert"
    print(f"[PASS] lifecycle SUSPECTED->VERIFYING->CONFIRMED, risk={r3['risk_level']}")


def test_duplicate_prevention():
    e = IncidentEngine(required_frames={"person": 2}, cooldowns={"person": 60})
    e.process_event("person", 0.9, track_id=7)
    r = e.process_event("person", 0.9, track_id=7)
    assert r["should_alert"], "first confirmation must alert"
    # Same person keeps appearing -> must NOT alert again within cooldown.
    for _ in range(5):
        r = e.process_event("person", 0.9, track_id=7)
        assert not r["should_alert"], "duplicate within cooldown must be suppressed"
    print("[PASS] duplicate/cooldown suppression (Detection != Event)")


def test_risk_levels():
    e = IncidentEngine()
    lvl, score, _ = e.compute_risk("person", 0.85, 1.0, "MONITORED", False)
    assert lvl == "LOW", (lvl, score)
    lvl, score, _ = e.compute_risk("fall", 0.85, 4.0, "MONITORED", False)
    assert lvl == "HIGH", (lvl, score)
    lvl, score, _ = e.compute_risk("fire", 0.85, 5.0, "RESTRICTED", True, multi_present=True)
    assert lvl == "CRITICAL", (lvl, score)
    print("[PASS] risk tiers LOW / HIGH / CRITICAL")


if __name__ == "__main__":
    test_verification_lifecycle()
    test_duplicate_prevention()
    test_risk_levels()
    print("--- INCIDENT ENGINE TESTS PASSED ---")
