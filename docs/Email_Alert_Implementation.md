# SU-DRISHTI — Email Alert Implementation

**Status: implemented and tested 2026-10-01. Live delivery to a real inbox
was NOT performed (no credentials configured) — all trigger/content/failure
logic is tested; only the final SMTP handshake awaits user credentials.**

## 1. Email architecture
```
TemporalStore (src/incident_store.py)
  -- on brand-new CONFIRMED row, HIGH/CRITICAL only --> email callback
  -- extensions of the same incident never re-enter this branch
EmailAlertDispatcher (src/alerts/email_alert.py)
  -- smtplib SMTP + STARTTLS --> Gmail (or configured server)
  -- returns True/False, never raises
Dashboard: shows stored alert_status (Email Sent only when status == 'sent')
```

## 2. SMTP configuration (.env, never in code)
Copy `.env.example` to `.env` and fill in. New names take precedence;
legacy `SENTINEL_*` names still work (backward compatible):

| Variable | Meaning | Gmail value |
|---|---|---|
| EMAIL_SENDER | sender address | your Gmail address |
| EMAIL_PASSWORD | Gmail **App Password** (not login password) | 16-char app password |
| EMAIL_RECEIVER | default recipient | guard address |
| SMTP_SERVER | SMTP host | smtp.gmail.com |
| SMTP_PORT | SMTP port | 587 |

`python-dotenv` (added to requirements.txt) loads `.env` automatically.
No password appears in code, logs, README, or dashboard.

## 3. Confirmation-trigger logic
Email fires only inside the store's row-creation branch: verification state
CONFIRMED **and** cooldown passed **and** whitelist/confidence filter passed
**and** risk HIGH/CRITICAL **and** no open row for the same (type, track).
LOW/MEDIUM incidents are stored with evidence but do not email (existing
risk-gating, preserved). `main.py` (webcam path) was not modified; it calls
the same dispatcher with the same confirm-gating.

## 4. Duplicate prevention
One row-creation ⇒ at most one `email_fn` call. Continuations update the row
in place (no new email). A genuinely new incident (gap > 45 frames or new
track) creates a new row ⇒ exactly one new email. Keyed by incident row id,
not by frame count.

## 5. Error handling
Dispatcher catches all SMTP errors, logs `[ALERT ERROR] ...`, returns False.
Store additionally guards the callback, records
`alert_status = "failed/not configured"`, and continues. The incident row
and evidence are always written before/while email is attempted, so a mail
failure can never lose an incident or crash analysis.

## 6. Testing results (tests/test_email_alerts.py, 5/5 pass, no network/DB)
- TEST 1 (noisy single frame): 0 rows, 0 emails.
- TEST 2 (persistent intrusion): 1 row, exactly 1 email; subject
  `SU-DRISHTI | Confirmed Safety Incident: INTRUSION [CRITICAL]`, body
  contains confidence/start/end/duration/source/risk, JPEG attached.
- TEST 3 (same incident, 200 frames): still 1 row, still 1 email.
- TEST 4 (new incident after 500-frame gap): 2nd row, 2nd email.
- TEST 5 (unreachable SMTP 127.0.0.1:1): returns False, no exception;
  store with raising callback still saves the row and records failure status.

## 7. Remaining step for the user
Set the five variables (Gmail App Password required), run one video
analysis on a clip containing a HIGH/CRITICAL event, and confirm receipt.
Until then the system honestly reports `failed/not configured`.
