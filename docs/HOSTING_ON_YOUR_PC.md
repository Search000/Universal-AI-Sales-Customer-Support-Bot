# Hosting on your own PC (stage before a paid server)

## Why this exists
Deploying normally needs a real server + domain + SSL (money). Since
that's not available right now, the bot runs on your own PC instead.
This works fine for local testing and for `/test/message`, but it has
one hard limit: **Facebook/WhatsApp webhooks require a public HTTPS
URL**, and your PC does not have one by default. So this stage gets you
production-quality *local* hosting — Phases 2/3 (real FB/WhatsApp) still
need one extra free step when you're ready for them (see below).

## 1. Run it properly (not `python main.py`)
`python main.py` is Flask's dev server — single-threaded, auto-reloads,
not meant for real traffic. Use the new production-style entrypoint
instead:

```
cd backend
pip install -r requirements.txt --break-system-packages
python run_production.py
```

Or just double-click `backend\start_server.bat` on Windows.

This uses **waitress** (a real WSGI server that works on Windows,
unlike gunicorn) and serves on `0.0.0.0:8000` by default (change
`APP_PORT` in `.env` if needed).

## 2. Keep it running after you close the terminal / restart your PC
Use Windows Task Scheduler:
1. Open Task Scheduler → Create Task.
2. General tab: name it "AI Bot Server", check "Run whether user is
   logged on or not".
3. Triggers tab: New → "At startup".
4. Actions tab: New → Program/script: `python`, Arguments:
   `run_production.py`, Start in: the full path to your `backend`
   folder (e.g. `E:\Wbot1\WBot\backend`).
5. Save. It will now start automatically every time the PC boots, even
   before you log in.

## 3. When you're ready to connect real Facebook/WhatsApp (later)
You'll need a public HTTPS URL pointing at this PC. Two free options
until there's budget for a real domain/server:
- **Cloudflare Tunnel** (free, no account limits that matter here) —
  exposes `localhost:8000` as a stable `https://...trycloudflare.com`
  or your own subdomain if you have any domain.
- **ngrok** free tier — quick to set up, but the free URL changes every
  restart, which is annoying for a webhook you register once with Meta.

Either way: your PC must stay on and connected to the internet for the
bot to keep responding to real customer messages. This is the actual
tradeoff of PC-hosting vs. a real server — worth knowing before going
live with real customers, not after.

## 4. Moving to a real server later
When there's budget: any small VPS (or a free-tier cloud instance) works.
Nothing in the code needs to change — copy the `backend/` folder, set
the same `.env` values, get a domain + SSL (or use the platform's
built-in HTTPS), point Meta's webhook at the new URL, done.
