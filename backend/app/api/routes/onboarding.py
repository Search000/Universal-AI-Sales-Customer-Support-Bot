import logging

from flask import Blueprint

logger = logging.getLogger(__name__)

onboarding_bp = Blueprint("onboarding", __name__)


_PAGE = """<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Notun Client Add Koro</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Work+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --cream: #FAF6EF;
    --ink: #20261F;
    --teal: #175E4C;
    --teal-dark: #0F4437;
    --gold: #C98A2C;
    --hairline: #E3DCC9;
    --muted: #6B6759;
    --error: #B3261E;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--cream);
    color: var(--ink);
    font-family: 'Work Sans', sans-serif;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px 16px;
  }
  .panel {
    width: 100%;
    max-width: 560px;
    background: #fff;
    border: 1px solid var(--hairline);
    border-radius: 10px;
    padding: 40px;
  }
  h1 {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 28px;
    margin: 0 0 6px;
    color: var(--ink);
  }
  .subtitle {
    color: var(--muted);
    margin: 0 0 32px;
    font-size: 15px;
    line-height: 1.5;
  }
  label {
    display: block;
    font-size: 14px;
    font-weight: 500;
    margin: 18px 0 6px;
  }
  label.req::after { content: " *"; color: var(--error); }
  input, select {
    width: 100%;
    padding: 11px 13px;
    font-size: 15px;
    font-family: inherit;
    border: 1px solid var(--hairline);
    border-radius: 6px;
    background: var(--cream);
    color: var(--ink);
  }
  input:focus, select:focus {
    outline: 2px solid var(--teal);
    outline-offset: 1px;
    background: #fff;
  }
  .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  button {
    margin-top: 28px;
    width: 100%;
    padding: 14px;
    background: var(--teal);
    color: #fff;
    border: none;
    border-radius: 6px;
    font-family: inherit;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
  }
  button:hover { background: var(--teal-dark); }
  button:disabled { background: var(--muted); cursor: not-allowed; }
  .msg {
    margin-top: 20px;
    padding: 16px;
    border-radius: 6px;
    font-size: 14px;
    line-height: 1.6;
    display: none;
  }
  .msg.show { display: block; }
  .msg.success { background: #EAF3EE; border: 1px solid var(--teal); }
  .msg.error { background: #FBEBE9; border: 1px solid var(--error); color: var(--error); }
  .biz-id {
    font-family: monospace;
    font-size: 18px;
    font-weight: 600;
    background: #fff;
    padding: 4px 10px;
    border-radius: 4px;
    display: inline-block;
    margin: 6px 0;
  }
  .owner-key-box {
    background: var(--cream);
    border: 1px solid var(--hairline);
    border-radius: 6px;
    padding: 14px 16px;
    margin-bottom: 28px;
  }
  .owner-key-box label { margin-top: 0; }
</style>
</head>
<body>
  <div class="panel">
    <h1>Notun Client Add Koro</h1>
    <p class="subtitle">Ekhane new client-er business toiri korle system nijei ekta business_id banabe, ar sathe sathe bot use korar jonno ready hoye jabe.</p>

    <div class="owner-key-box">
      <label for="ownerKey">Owner API Key</label>
      <input type="password" id="ownerKey" placeholder="tomar .env-er OWNER_API_KEY" autocomplete="off">
    </div>

    <form id="bizForm">
      <label class="req" for="bizName">Business Name</label>
      <input type="text" id="bizName" required placeholder="e.g. Rupa Fashion">

      <label class="req" for="bizType">Business Type</label>
      <input type="text" id="bizType" required placeholder="e.g. clothing, salon, restaurant">

      <div class="row2">
        <div>
          <label for="phone">Phone</label>
          <input type="text" id="phone" placeholder="01700000000">
        </div>
        <div>
          <label for="email">Email</label>
          <input type="email" id="email" placeholder="optional">
        </div>
      </div>

      <label for="address">Address</label>
      <input type="text" id="address" placeholder="optional">

      <div class="row2">
        <div>
          <label for="hours">Opening Hours</label>
          <input type="text" id="hours" placeholder="e.g. 10am-9pm">
        </div>
        <div>
          <label for="currency">Currency</label>
          <input type="text" id="currency" value="BDT">
        </div>
      </div>

      <label for="lang">Default Language</label>
      <select id="lang">
        <option value="bn">Bangla</option>
        <option value="en">English</option>
      </select>

      <button type="submit" id="submitBtn">Business Toiri Koro</button>
    </form>

    <div class="msg" id="resultMsg"></div>
  </div>

<script>
const form = document.getElementById('bizForm');
const msg = document.getElementById('resultMsg');
const btn = document.getElementById('submitBtn');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  msg.className = 'msg';
  btn.disabled = true;
  btn.textContent = 'Toiri Hocche...';

  const ownerKey = document.getElementById('ownerKey').value.trim();
  const payload = {
    business_name: document.getElementById('bizName').value.trim(),
    business_type: document.getElementById('bizType').value.trim(),
    phone: document.getElementById('phone').value.trim(),
    email: document.getElementById('email').value.trim(),
    address: document.getElementById('address').value.trim(),
    opening_hours: document.getElementById('hours').value.trim(),
    currency: document.getElementById('currency').value.trim() || 'BDT',
    default_language: document.getElementById('lang').value,
  };

  try {
    const resp = await fetch('/dashboard/businesses', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': ownerKey,
      },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();

    if (!resp.ok) {
      msg.className = 'msg error show';
      msg.textContent = 'Error: ' + (data.error || 'kichu ekta bhul hoyeche');
    } else {
      msg.className = 'msg success show';
      msg.innerHTML =
        'Business toiri hoye geche.<br>Business ID: <span class="biz-id">' +
        data.business.business_id +
        '</span><br>Ei ID diye ekhon /test/message ba onno kono channel-e ei client-er jonno bot chalu kora jabe.';
      form.reset();
      document.getElementById('currency').value = 'BDT';
    }
  } catch (err) {
    msg.className = 'msg error show';
    msg.textContent = 'Network error: server-e connect kora jayni.';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Business Toiri Koro';
  }
});
</script>
</body>
</html>
"""


@onboarding_bp.get("/dashboard/onboard")
def onboarding_page():
    """Public page shell — no business data lives here. The actual
    create-business call from this page's JS still requires the owner API
    key, enforced server-side by /dashboard/businesses."""
    return _PAGE, 200, {"Content-Type": "text/html; charset=utf-8"}
