# Phase 14 — Security / QA / Production Review

Audit date: this phase. Scope: everything built in Phases 0–13.

## Method
Read every route, every write-path to Google Sheets, every webhook
handler, and every place a customer's raw message can travel to, looking
specifically for the checklist in the master prompt (auth, secrets,
business isolation, prompt injection, data leakage, API errors, webhook
security, rate limiting, logging, Sheets/Meta permissions, hallucination,
cross-business tests).

## Findings and fixes

| # | Area | Finding | Fix |
|---|------|---------|-----|
| 1 | Authentication | `/dashboard/*`, `/learning/*`, `/follow-up/*`, and `/test/message` had **no authentication** — anyone who knew a `business_id` could read all of a business's conversations/orders/customers, or approve vocabulary, or chat as a test customer (which can trigger real Gemini/Sheets calls). | Added `OWNER_API_KEY` (shared-secret `X-API-Key` header), enforced via `before_request` on each of those blueprints. Health checks and webhooks are intentionally exempt (see #2, #4). |
| 2 | Webhook auth | Facebook/WhatsApp webhook signature check was already correct (HMAC-SHA256, constant-time compare) **when `META_APP_SECRET` is set** — but if left unset in a real (production) deployment, the webhook would silently accept **unsigned** traffic, letting anyone POST fake "customer messages". | If `APP_ENV=production` and `META_APP_SECRET` is empty, the webhook now refuses all POSTs with `503` and logs a `CRITICAL` line, instead of accepting unsigned events. |
| 3 | Timing side-channel | The GET webhook verify-token comparison (`token == META_VERIFY_TOKEN`) used plain `==`, not constant-time. | Switched to `hmac.compare_digest`. |
| 4 | Data leakage — spreadsheet formula injection | Raw customer text (e.g. an unrecognized word + its surrounding message, stored in `LEARNING_QUEUE.term`/`context`) is written to a real Google Sheet. A message starting with `=`, `+`, `-`, or `@` can become a **live formula** (e.g. `=HYPERLINK(...)`, DDE payloads) the moment the owner opens the sheet — a well-known "CSV/Sheets injection" class of attack. | Added `sanitize_row()`, applied to every row in `GoogleSheetsClient.upsert_row` (the single chokepoint every write passes through) — any value starting with a formula character is prefixed with `'` so spreadsheet software renders it as plain text. |
| 5 | Prompt injection | `response_engine` already scopes Gemini strictly to `RETRIEVED_DATA` and never lets it answer when there's no verified data — good. But there was no check that the model's *output* hadn't leaked the system-prompt scaffolding if an injection attempt partially succeeded. | Added a leakage scrub: if the AI's reply contains markers like `SYSTEM_RULES`, `RETRIEVED_DATA`, or `you are a customer support assistant`, the reply is discarded and the safe deterministic draft is used instead. |
| 6 | Rate limiting | No limits anywhere — a single caller could hammer the webhooks or `/test/message` (each of which can trigger a Gemini call and a Sheets write) with no cost. | Added a lightweight in-memory per-IP fixed-window limiter (`RATE_LIMIT_PER_MINUTE`, default 60/min), applied to both webhook POST routes and `/test/message`. Documented limitation: single-process only — a multi-instance deployment needs a shared store instead. |
| 7 | Secrets in repo | Checked `.gitignore`, `.env.example`, and full git history for committed secrets/tokens/service-account files. | Clean — nothing committed, `.env` and `*.json` (service-account keys) are gitignored. No change needed. |
| 8 | Business isolation | Re-checked: every repository method requires `business_id` and raises `BusinessIdRequiredError` if missing; every dashboard/follow-up/learning route enforces it too. | Already correct (Phases 1–13); Phase 13's new follow-up engine tested for the same isolation. No change needed, re-verified with tests. |
| 9 | Error handling | Webhooks always ack `200`/log-and-drop rather than crash on a bad event; `/test/message` and dashboard routes return clean 400s on missing params and 500 only on truly unexpected errors (logged, not leaked to the caller). | Already correct. No change needed. |
| 10 | Logging | Checked for secrets in log lines (tokens, API keys) — none found; only IDs and truncated response bodies are logged. | No change needed. |

## What is intentionally NOT fixed here (out of scope / requires your input)
- **Multi-instance rate limiting / shared session store** — needs Redis or
  similar, which conflicts with the "zero paid software" requirement
  unless you're fine running Redis locally too. Flag this if you ever
  scale to more than one server process.
- **OWNER_API_KEY rotation / multiple keys per business owner** — current
  design is a single shared secret for the whole server, matching the
  project's current single-operator scope. If you eventually have
  multiple business owners each needing separate dashboard logins, that's
  a bigger auth system (Phase 15+ material, not silently added here).

## New environment variables (see `backend/.env.example`)
```
OWNER_API_KEY=            # required before going live — protects dashboard/learning/follow-up/test-message
RATE_LIMIT_PER_MINUTE=60  # per-IP cap on webhook + test/message calls
```

## Your action before going live
1. Generate a long random string for `OWNER_API_KEY` and put it in
   `backend/.env`. Never commit `.env`.
2. Make sure `META_APP_SECRET` is set once you connect real Facebook/WhatsApp
   apps (Phases 10–11 already required this for signature checking; Phase 14
   now also refuses unsigned webhook traffic entirely in production if it's
   missing).
3. Any dashboard/automation tool you build that calls
   `/dashboard/*`, `/learning/*`, `/follow-up/*`, or `/test/message` must
   send header `X-API-Key: <OWNER_API_KEY>`.

## Test coverage added this phase
23 new tests in `backend/tests/test_phase14_security.py`: owner-key
enforcement (present/absent/wrong key, per blueprint), health/webhooks
staying key-free, sheet-value/row sanitization (including a mocked real
`GoogleSheetsClient.upsert_row` call), rate limiter behavior and its
429 response, webhook production guard, constant-time token compare, and
prompt-leakage scrubbing.

**Total suite: 220/220 passing.**
