# Architecture — Universal AI Sales & Customer Support Bot

## 1. Goal
One AI engine serving many businesses (clothing, salon, restaurant, etc.) without
hard-coding any business type into the code. Business facts live in data
(Google Sheets now, swappable DB later), never in the AI prompt as "truth"
the model invents.

## 2. Folder structure

```
backend/
  main.py                     # entrypoint: python main.py
  requirements.txt
  .env.example                # template, real .env is gitignored
  app/
    __init__.py                # Flask app factory
    config.py                  # all config from env vars, no hardcoding
    api/
      routes/
        health.py              # /health endpoint (Phase 1)
                                # businesses.py, products.py, etc added later phases
    core/                      # cross-cutting logic: business isolation guard,
                                # authority-order resolver, prompt-injection filter
    integrations/
      sheets/                  # Google Sheets client (Phase 2)
      facebook/                # Messenger webhook (Phase 10)
      whatsapp/                # WhatsApp webhook (Phase 11)
    services/                  # business logic: knowledge engine, order engine,
                                # learning engine, memory (Phases 3, 6, 7, 8)
    models/                    # data classes / schemas for Business, Product,
                                # Order, etc. (mirrors Google Sheets columns)
  tests/                       # pytest tests, one file per module
docs/
  ARCHITECTURE.md              # this file
```

## 3. Configuration strategy
- All secrets and environment-specific values come from `backend/.env`
  (gitignored). `.env.example` documents required keys with empty values.
- `app/config.py` is the single place code reads config from — no module
  reads `os.getenv` directly elsewhere.
- No credentials are ever placed in code, prompts, or chat.

## 4. Module boundaries
- **api/routes** — HTTP layer only. Parses requests, calls services, returns
  JSON. No business logic here.
- **integrations/** — talks to external platforms (Google Sheets, Meta APIs).
  Each integration is isolated so Sheets can later be swapped for
  Postgres/SQLite without touching services or api layers.
- **services/** — the actual business logic (knowledge retrieval, order
  creation, learning queue, memory). This is where BUSINESS_ID filtering and
  the "authority order" rule (verified data > vocabulary > conversation >
  language knowledge > AI inference) get enforced.
- **core/** — shared guards used by every service: business isolation check,
  prompt-injection filter, safe-response fallback when data is missing.
- **models/** — typed representations of each Google Sheet row (Business,
  Product, Service, FAQ, Policy, Order, etc.).

## 5. Data flow (per incoming message)

```
Platform webhook (FB/WhatsApp)
   -> api/routes (verify signature, parse sender + business_id)
   -> core.business_isolation (lock retrieval to this business_id)
   -> services.knowledge_engine (fetch product/service/FAQ/policy from Sheets,
      filtered by business_id)
   -> services.language_engine (understand Bangla/English/Banglish, but only
      to pick which lookup to run — never to invent a fact)
   -> services.response_engine (build prompt: SYSTEM RULES + BUSINESS CONFIG +
      RETRIEVED DATA + CONVERSATION + MESSAGE; call AI; if data missing,
      return safe fallback / trigger human handover)
   -> services.order_engine / services.memory (only if retrieved data supports it)
   -> platform webhook reply
```

## 6. Security strategy (baseline, expanded in Phase 14)
- Webhook signature verification before processing any Facebook/WhatsApp payload.
- business_id always required and validated before any Sheets read — a
  request without it is rejected, never defaulted to "any business."
- Customer messages are treated as untrusted input: they can shift what the
  bot looks up, never what the bot believes is true business data.
- No secret values in logs, prompts, or responses.
- `.env` and any service-account JSON files are gitignored.

## 7. What Phase 1 delivers (this phase)
- Folder skeleton above.
- A runnable Flask app with one endpoint: `GET /health` → `{"status": "ok"}`.
- Config loading wired to environment variables.
- One passing test proving the app starts and responds.

No Google Sheets, AI calls, or platform integrations yet — those are Phases
2 onward, one at a time.

## 8. What Phase 8 delivers (Learning Engine)

Implements the LEARNING_QUEUE described in master-prompt section 8, with
one hard rule enforced in code: **no code path other than
`LearningEngine.approve()` is allowed to write a VOCABULARY row.**

- `models/learning_queue.py` — `LearningQueueEntry`, mirrors the
  `LEARNING_QUEUE` sheet tab (learning_id, business_id, term,
  possible_meaning, context, confidence, source, status, created_at,
  approved_by, approved_at, reviewed_at).
- `integrations/sheets/repository.py` — CRUD for `LEARNING_QUEUE`, plus
  `save_vocabulary()` (the only writer for `VOCABULARY`, only ever called
  from the approve path).
- `services/learning_engine.py`:
  - `find_unrecognized_keywords()` — of the keywords the language engine
    pulled out of a message, returns the ones that don't match any known
    product/service name or already-approved vocabulary for *this*
    business_id.
  - `record_unknown_term()` — queues a candidate as `pending`. Repeated
    mentions of the same term don't create duplicate pending rows (a
    customer repeating a claim still doesn't make it a fact — master rule
    #7).
  - `approve()` — requires an explicit human-supplied meaning; writes an
    approved `VOCABULARY` row and marks the queue entry `approved`.
  - `reject()` — closes the entry with no vocabulary created.
- `services/message_pipeline.py` — when a product/order lookup comes back
  empty, unrecognized keywords from that message are queued automatically
  (best-effort; a learning-queue failure never breaks the customer-facing
  reply).
- `api/routes/learning.py` — owner-only endpoints: `GET /learning`,
  `POST /learning/<id>/approve`, `POST /learning/<id>/reject`.

Tested: known-word vs unknown-word detection, per-business isolation of
the queue, duplicate-suppression, approve requiring a meaning, double
approve/reject rejected, and the end-to-end route flow
(message → queued → approved → resolvable vocabulary).

## 9. What Phase 9 delivers (Human Handover)

Implements master-prompt section 20/21: a `human_required` status the
pipeline computes every turn, without ever changing what the AI is allowed
to claim about business facts.

- `services/language_engine.py` — new `HUMAN_HANDOVER` intent, checked with
  the *highest* priority (before greeting/price/etc). Fires on explicit
  requests for a person ("human", "কাউকে দেন", "ম্যানেজার"...) or angry
  language ("সার্ভিস খারাপ", "scam", "রিফান্ড দেন"...). `meta.reason` is
  `human_request` or `angry_customer`.
- `services/human_handover.py` — pure decision function `evaluate()`.
  Triggers, in priority order:
  1. `HUMAN_HANDOVER` intent → always required (reason from meta).
  2. Order intent with no order engine wired → `unsupported_request`.
  3. A flatly-missing fact (currently: policy not found →
     `SAFE_FALLBACK`) → `business_data_unavailable`, immediately (no need
     to wait for a repeat — we already know we don't have it).
  4. Two or more consecutive unresolved turns for the same customer (e.g.
     repeated product-not-found misses) → `repeated_misunderstanding`.
  A single "product not found" miss does *not* escalate by itself — the
  bot's own self-service fallback (ask for a photo) gets a chance first.
- `models/conversation_memory.py` / `services/memory_service.py` — the
  `CONVERSATIONS` row now also tracks `unresolved_count`, `human_required`,
  `human_required_reason`, so the streak survives restarts exactly like
  entity context does (Phase 6). Without a memory_service, the same
  bookkeeping falls back to an in-memory dict per pipeline instance (same
  degrade pattern as the Phase 4 entity context).
- `services/message_pipeline.py` — every `handle_message()` result now
  includes `human_required` (bool) and `human_required_reason`
  (str|None) alongside the existing fields.

Tested: intent priority over greeting, all four trigger types, single-miss
vs repeated-miss behavior, streak reset after a resolved turn, and
per-customer isolation of the handover status.
