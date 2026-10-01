"""Day 2 tests: temporal verification + event grouping + dedup (no camera/DB).

Controlled detection sequences fed frame-by-frame into TemporalStore:
 1. single-frame noise      -> 0 rows
 2. persistent detection    -> 1 row, measured confirmation delay
 3. long continuous event   -> still 1 row (extended in place)
 4. disappear briefly, return -> still 1 row
 5. disappear long / new track -> separate rows
 6. baseline mode           -> frame-level rows (comparison arm)
 7. evidence captured only on creation
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.incident_store import TemporalStore
from src.incident_engine import IncidentEngine
from src.event_filter import EventFilter


class Fakes:
    def __init__(self):
        self.saved = []      # kwargs per insert
        self.updated = []    # kwargs per extension
        self.captures = 0
        self.emails = 0
        self._id = 0

    def save(self, *a, **k):
        self._id += 1
        self.saved.append(k)
        return self._id

    def update(self, *a, **k):
        self.updated.append(k)

    def capture(self, frame, name):
        self.captures += 1
        return f"screenshots/{name}_test.jpg"

    def email(self, *a, **k):
        self.emails += 1
        return True


def make_store(fakes, mode="proposed"):
    eng = IncidentEngine(required_frames={"person": 3, "intrusion": 3},
                         cooldowns={"person": 0.0, "intrusion": 0.0})
    fil = EventFilter(important_objects={"person", "intrusion"},
                      min_confidence=0.40, default_cooldown=0.0,
                      critical_cooldown=0.0)
    return TemporalStore(mode=mode, engine=eng, event_filter=fil,
                         save_fn=fakes.save, update_fn=fakes.update,
                         capture_fn=fakes.capture, email_fn=fakes.email,
                         fps=10.0, reopen_gap_frames=45, close_gap_frames=45)


def feed(store, et, conf, tid, frames, start=0):
    outs = [store.observe(et, conf, track_id=tid, frame_idx=f,
                          annotated=None, source="test")
            for f in range(start, start + frames)]
    return outs


def test_1_noise():
    f, s = Fakes(), make_store(Fakes())
    s = make_store(f)
    feed(s, "person", 0.9, 1, 1)
    assert s.rows_created == 0, "one-frame noise must not confirm"
    print("[PASS] 1. single-frame noise -> 0 rows")


def test_2_persistent():
    f = Fakes()
    s = make_store(f)
    outs = feed(s, "person", 0.9, 1, 10)
    assert s.rows_created == 1, s.metrics()
    created = [o for o in outs if o["action"] == "created"][0]
    assert created["delay_frames"] == 2, created  # confirmed on 3rd frame
    print(f"[PASS] 2. persistent 10 frames -> 1 row, delay={created['delay_frames']} frames")


def test_3_long_continuous():
    f = Fakes()
    s = make_store(f)
    feed(s, "person", 0.9, 1, 200)
    assert s.rows_created == 1, s.metrics()
    assert s.rows_extended > 0
    assert f.updated[-1]["duration_sec"] == 20.0, f.updated[-1]
    assert f.captures == 1, "evidence only at creation"
    print(f"[PASS] 3. 200 frames -> 1 row, {s.rows_extended} extensions, "
          f"final duration={f.updated[-1]['duration_sec']}s, captures={f.captures}")


def test_4_brief_gap():
    f = Fakes()
    s = make_store(f)
    feed(s, "person", 0.9, 1, 10)
    feed(s, "person", 0.0, 999, 0)  # no-op guard (no frames)
    outs = [s.observe("person", 0.9, track_id=1, frame_idx=frm, source="test")
            for frm in range(15, 25)]  # 5-frame gap, then return
    assert s.rows_created == 1, s.metrics()
    print("[PASS] 4. 5-frame gap then return -> still 1 row")


def test_5_long_gap_and_two_tracks():
    f = Fakes()
    s = make_store(f)
    feed(s, "person", 0.9, 1, 10, start=0)
    feed(s, "person", 0.9, 1, 10, start=200)   # 190-frame gap -> separate
    assert s.rows_created == 2, s.metrics()
    f2 = Fakes()
    s2 = make_store(f2)
    for frm in range(10):
        s2.observe("person", 0.9, track_id=1, frame_idx=frm, source="test")
        s2.observe("person", 0.88, track_id=2, frame_idx=frm, source="test")
    assert s2.rows_created == 2, s2.metrics()
    print("[PASS] 5. long gap -> 2 rows; two tracks -> 2 rows")


def test_6_baseline():
    f = Fakes()
    s = make_store(f, mode="baseline")
    feed(s, "person", 0.9, 1, 5)
    assert s.rows_created == 5, s.metrics()
    assert all(k.get("event_status") == "DETECTED" for k in f.saved)
    print("[PASS] 6. baseline mode -> 5 frames = 5 DETECTED rows (comparison arm)")


if __name__ == "__main__":
    test_1_noise()
    test_2_persistent()
    test_3_long_continuous()
    test_4_brief_gap()
    test_5_long_gap_and_two_tracks()
    test_6_baseline()
    print("--- INCIDENT STORE TESTS PASSED ---")
