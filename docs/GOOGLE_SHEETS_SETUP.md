# Google Sheets Setup (do this when ready — not required to keep building)

The code already works against a fake in-memory Sheets client (see tests).
When you're ready to connect a REAL Google Sheet, do this:

## 1. Create the spreadsheet
Create one Google Sheet. Add these tabs (exact names, all-caps):
`BUSINESSES`, `PRODUCTS`, `SERVICES`, `FAQ`, `POLICIES`, `BUSINESS_RULES`,
`VOCABULARY`, `CUSTOMERS`, `ORDERS`, `CONVERSATIONS`, `APPOINTMENTS`,
`LEARNING_QUEUE`.

First row of each tab = column headers (see `docs/ARCHITECTURE.md` sheet
column lists, or ask me and I'll paste the exact header row for any tab).

`CONVERSATIONS` tab columns (Phase 6 — persistent per-customer memory):
`business_id, customer_id, last_intent, last_color, last_size, last_keywords, updated_at`

## 2. Create a Google service account (so the bot can read/write)
1. Go to https://console.cloud.google.com/
2. Create a project (any name).
3. Enable "Google Sheets API" and "Google Drive API" for that project.
4. Go to "IAM & Admin" → "Service Accounts" → "Create Service Account".
5. After creating it, open it → "Keys" tab → "Add Key" → "Create new key" → JSON.
   A `.json` file downloads — this is a secret credential file.
6. Open the downloaded JSON, copy the `client_email` value (looks like
   `xxxx@xxxx.iam.gserviceaccount.com`).
7. Open your Google Sheet → click "Share" → paste that email → give "Editor"
   access.

## 3. Put the credential file in the project (never in chat)
1. Rename the downloaded file to `service-account.json`.
2. Put it inside `backend/` folder (it's already in `.gitignore`, so it
   won't be pushed to GitHub).
3. Copy `backend/.env.example` to `backend/.env` and fill:
   ```
   GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
   GOOGLE_SPREADSHEET_ID=your_spreadsheet_id_here
   ```
   (The spreadsheet ID is the long code in the sheet's URL between
   `/d/` and `/edit`.)

## 4. Tell me
Just tell me "Google Sheets connected" — do NOT paste the JSON file
contents or spreadsheet ID's secret parts here. I'll then run a real
connection test against your sheet.
