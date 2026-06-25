# SignSetu QA Assessment — NPTEL Summer Internship 2026

Automated API test suite for the **SignSetu Video Caption Processing Pipeline**,
built as part of the NPTEL Summer Internship selection process under
**Prof. Bala Ramadurai, IIT Madras**.

## Candidate Details

- **Name:** Barkavi
- **GitHub:** Barkavi26
- **Email:** pbarkavi1@gmail.com
- **Base URL Tested:** https://qa-testing-navy.vercel.app

## Project Structure
SignSetu_Assessment/

├── test_api.py                 

├── test_vulnerabilities.py    

├── .gitignore

└── README.md

## Setup & Run

```bash
# Install dependency
pip install requests

# Run happy path lifecycle test
python test_api.py

# Run full vulnerability + bonus bug tests
python test_vulnerabilities.py
```

No framework needed. Works directly with **Python 3.11+**.

## Testing Strategy

### 1. Happy Path — Full Lifecycle (test_api.py)
Tests the complete intended workflow end-to-end:
Auth → Create Video → Trigger Captions → Poll Status → Fetch Captions → Delete
### 2. Async Handling
Caption processing is asynchronous. The suite uses a polling loop that
calls `GET /api/videos/{id}` every 3 seconds for up to 20 attempts, waiting
for `status: completed`.

This revealed two critical bugs:
- **Bug #4** — Token expires in 5 seconds, breaking the polling loop
- **Bug B4** — Re-authentication fails due to StateCollision, making the async workflow impossible to complete

### 3. Vulnerability Hunting (test_vulnerabilities.py)
Actively tries to break the system by testing:

- Missing / fake / expired auth tokens
- Duplicate operations (double delete, double trigger)
- Fetching captions before and after processing
- SQL injection in the title field
- Invalid limit parameter values (negative, zero, string, huge number)
- Missing required headers (X-Candidate-ID)
- IDOR — cross-candidate resource access attempt
- Token expiry consistency across all endpoints
- StateCollision — session reuse behavior

### 4. Cleanup
Every test that creates a resource deletes it after itself.
The suite is **fully repeatable** across unlimited runs.

## Bugs Found

### Critical Bugs (5/5 Found)

| # | Bug | Endpoint | Expected | Actual |
|---|-----|----------|----------|--------|
| 1 | Captions before processing return 200 | `GET /api/captions?videoId={id}` | 400 or 404 | `200 []` |
| 2 | Double delete succeeds both times | `DELETE /api/videos/{id}` | 404 on 2nd delete | `204` both times |
| 3 | Duplicate caption trigger accepted | `POST /api/videos/{id}/process-captions` | 409 Conflict | `202` both times |
| 4 | Token expires in 5 seconds — too short for async workflow | `POST /api/auth` | >60s expiry | 5 seconds only |
| 5 | Captions never stored after processing | `GET /api/captions?videoId={id}` | Actual caption data | `200 []` always |

### Bonus Bugs (4 Found)

| # | Bug | Endpoint | Expected | Actual |
|---|-----|----------|----------|--------|
| B1 | Fake/expired token accepted on list endpoint | `GET /api/videos` | 401 or 403 | `200` |
| B2 | Invalid limit values silently accepted | `GET /api/videos?limit=-1/0/abc` | 400 | `200 []` |
| B3 | Token expiry inconsistently enforced across endpoints | `GET /api/videos` vs `GET /api/videos/{id}` | Consistent 401 | Only some endpoints validate |
| B4 | StateCollision — candidate ID permanently blocked after one use, no session cleanup endpoint exists | `POST /api/auth` | Reusable ID | `409 StateCollision` forever |

## Key Findings Summary

- **Entire async pipeline is broken** — token expires in 5 seconds but
  StateCollision prevents re-authentication, making polling impossible
  (Bugs 4 & B4 together)

- **Captions never work** — processing triggers successfully but status
  never updates and captions are never stored (Bugs 4 & 5)

- **Authentication inconsistently enforced** — fake tokens accepted on
  the list endpoint but rejected on individual resource endpoints (B1 & B3)

- **No idempotency guards** on critical operations — double delete and
  duplicate caption processing both silently succeed (Bugs 2 & 3)

- **Silent 200s mask errors** — the API returns `200 []` in failure cases
  instead of appropriate 4xx error codes (Bugs 1 & 5)

## Test Results Summary

| Test | Result |
|------|--------|
| Invalid video ID → 404 | ✅ Pass |
| Missing auth token → 401 | ✅ Pass |
| Missing X-Candidate-ID → 400 | ✅ Pass |
| SQL injection — server stable | ✅ Pass |
| Process captions on deleted video → 404 | ✅ Pass |
| IDOR cross-candidate access blocked | ✅ Pass |
| Captions before processing → 200 [] | 🐛 Bug #1 |
| Double delete → 204 both times | 🐛 Bug #2 |
| Duplicate trigger → 202 both times | 🐛 Bug #3 |
| Token expires in 5 seconds | 🐛 Bug #4 |
| Captions never stored | 🐛 Bug #5 |
| Fake token accepted on list | 🐛 Bonus B1 |
| Invalid limit accepted | 🐛 Bonus B2 |
| Token expiry inconsistent | 🐛 Bonus B3 |
| StateCollision — no session cleanup | 🐛 Bonus B4 |

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.11 | Language |
| requests | HTTP client |
| Plain scripts | No framework — maximum clarity and portability |