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
