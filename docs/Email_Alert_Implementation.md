# SU-DRISHTI — Email Alert Implementation

**Status: pipeline repaired and tested 2026-10-01. Live delivery to a real
inbox was NOT performed (no credentials configured) — trigger, content,
attachment, dedup and failure logic are all tested; only the final SMTP
handshake awaits user credentials. "Working" is NOT claimed for delivery.**

## 0. Root cause of the reported problem
The incident was detected but no email arrived because **no SMTP credentials
exist anywhere**: no `.env` file, no `EMAIL_*`/`SENTINEL_*` variables set.
`is_configured()` is therefore False on every run, so the dispatcher takes
the simulation branch and never opens an SMTP connection. The detection →
verification → evidence → database chain was intact; only the last hop was
a no-op. Secondary gaps fixed today: no evidence pre-check (a missing file
would previously still "attempt"), no canonical send function, email limited
to HIGH/CRITICAL while the spec requires every CONFIRMED incident.

## 1. Email architecture
```
TemporalStore (src/incident_store.py)
  -- on brand-new CONFIRMED row, EVERY risk tier --> send_incident_email()
  -- extensions of the same incident never re-enter this branch
send_incident_email (src/alerts/email_alert.py)
  -- NOT_SENT when unconfigured | FAILED when evidence missing
  -- EmailAlertDispatcher: smtplib SMTP + STARTTLS, never raises
Dashboard: shows stored alert_status (Email Sent only when status == 'sent')
Manual test: python -m src.alerts.email_test
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
**and** no open row for the same (type, track) — for EVERY risk tier
(policy changed today per spec: one CONFIRMED incident = one email).
`main.py` (webcam path) was not modified; it still emails HIGH/CRITICAL only
(minor inconsistency, noted for Day 3).

## 4. Duplicate prevention
One row-creation ⇒ at most one `send_incident_email()` call. Continuations
update the row in place (no new email). A genuinely new incident (gap >
45 frames or new track) creates a new row ⇒ exactly one new email. Keyed by
incident row id, not by frame count.

## 5. Error handling
`send_incident_email()` returns SENT / FAILED / NOT_SENT and never raises:
missing evidence ⇒ FAILED without contacting SMTP; unconfigured ⇒ NOT_SENT;
SMTP errors ⇒ FAILED with the non-sensitive error logged. Store maps these
to `sent` / `failed` / `not configured` in the outcome/timeline/report.
The incident row and evidence are always written, so a mail failure can
never lose an incident or crash analysis. Password absence in logs is
asserted by test.

## 6. Testing results (no network, no real credentials, no DB writes)
`tests/test_email_alerts.py` 5/5 pass:
- TEST 1 (noisy single frame): 0 rows, 0 emails.
- TEST 2 (persistent intrusion): 1 row, exactly 1 email; subject
  `SU-DRISHTI | Confirmed Safety Incident: INTRUSION [CRITICAL]`, body has
  all spec fields, JPEG attached.
- TEST 3 (same incident, 200 frames): still 1 row, still 1 email.
- TEST 4 (new incident after 500-frame gap): 2nd row, 2nd email.
- TEST 5 (unreachable SMTP 127.0.0.1:1): False, no exception; raising
  callback still saves the row.
`tests/test_email_send_path.py` 3/3 pass:
- TEST E (missing evidence file): no SMTP attempt, FAILED logged.
- All-confirmed policy: LOW person incident → exactly 1 email.
- Secrecy: failed send log contains no password.
Manual test `python -m src.alerts.email_test` (TEST A): finds newest real
evidence, reports NOT_SENT with config guidance (exit 2) when unconfigured.
End-to-end video run (TEST B/C live logic): 30 frames → 2 confirmed rows +
evidence, both attempted exactly once, honestly recorded as `not configured`.
TEST D/F covered by TEST 4/5 above.

## 7. Remaining step for the user
Set the five variables (Gmail App Password required), run
`python -m src.alerts.email_test` (expect SENT + inbox arrival), then one
video analysis and confirm receipt. Until then the system honestly reports
`not configured`. TEST A inbox arrival is still unverified — delivery is
NOT claimed working.
