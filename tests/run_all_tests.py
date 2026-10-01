"""
Unified Test Runner for SU-DRISHTI.
Executes all unit and integration tests and outputs a structured health report.
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TEST_FILES = [
    "tests/test_env.py",
    "tests/test_database.py",
    "tests/test_logger_and_screenshot.py",
    "tests/test_event_filter.py",
    "tests/test_person_detection.py",
    "tests/test_safety_modules.py",
]

def run_all():
    print("=" * 60)
    print("SU-DRISHTI — AUTOMATED TEST SUITE")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test in TEST_FILES:
        full_path = PROJECT_ROOT / test
        print(f"\n[RUNNING] {test}...")
        res = subprocess.run([sys.executable, str(full_path)], cwd=str(PROJECT_ROOT))
        if res.returncode == 0:
            print(f"[RESULT] {test} -> PASSED")
            passed += 1
        else:
            print(f"[RESULT] {test} -> FAILED (Code {res.returncode})")
            failed += 1
            
    print("\n" + "=" * 60)
    print(f"TEST RUN COMPLETED: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_all()
