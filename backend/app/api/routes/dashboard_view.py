"""
Owner Dashboard — visual UI (Phase 12 follow-up).

The /dashboard/* JSON API (dashboard.py, learning.py, follow_up.py) already
existed but had no browser-facing page — an owner had no way to actually
*see* their data without calling the API by hand. This adds one page shell,
same pattern as onboarding.py: a public static shell (no business data
baked in) that calls the already-protected JSON endpoints client-side with
the owner's API key. Registered as its own blueprint (not dashboard_bp) so
it is NOT gated by dashboard_bp's before_request — the page itself has
nothing to protect; every real data call still requires X-API-Key,
enforced server-side same as always.
"""
import logging

from flask import Blueprint

logger = logging.getLogger(__name__)

dashboard_view_bp = Blueprint("dashboard_view", __name__)


_PAGE = """<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Owner Dashboard</title>
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
    padding: 24px 16px 60px;
  }
  .wrap { max-width: 1100px; margin: 0 auto; }
  h1 {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 26px;
    margin: 0 0 4px;
  }
  .subtitle { color: var(--muted); margin: 0 0 22px; font-size: 14px; }
  .topbar {
    background: #fff;
    border: 1px solid var(--hairline);
    border-radius: 10px;
    padding: 16px 20px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: flex-end;
    margin-bottom: 18px;
  }
  .field { display: flex; flex-direction: column; gap: 4px; }
  .field label { font-size: 12px; color: var(--muted); font-weight: 500; }
  .field input {
    padding: 9px 11px;
    font-size: 14px;
    font-family: inherit;
    border: 1px solid var(--hairline);
    border-radius: 6px;
    background: var(--cream);
    color: var(--ink);
    min-width: 220px;
  }
  .field input:focus { outline: 2px solid var(--teal); outline-offset: 1px; background: #fff; }
  button.reload {
    padding: 10px 18px;
    background: var(--teal);
    color: #fff;
    border: none;
    border-radius: 6px;
    font-family: inherit;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }
  button.reload:hover { background: var(--teal-dark); }
  button.reload:disabled { background: var(--muted); cursor: not-allowed; }
  .tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 16px;
  }
  .tab {
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 500;
    border: 1px solid var(--hairline);
    border-radius: 20px;
    background: #fff;
    color: var(--ink);
    cursor: pointer;
  }
  .tab.active { background: var(--teal); color: #fff; border-color: var(--teal); }
  .panel {
    background: #fff;
    border: 1px solid var(--hairline);
    border-radius: 10px;
    padding: 20px;
    min-height: 200px;
  }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
  .card {
    background: var(--cream);
    border: 1px solid var(--hairline);
    border-radius: 8px;
    padding: 14px 16px;
  }
  .card .num { font-family: 'Fraunces', serif; font-size: 26px; font-weight: 600; color: var(--teal-dark); }
  .card .label { font-size: 12px; color: var(--muted); margin-top: 2px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td {
    text-align: left;
    padding: 8px 10px;
    border-bottom: 1px solid var(--hairline);
    vertical-align: top;
  }
  th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; }
  tr:hover td { background: var(--cream); }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    background: var(--cream);
    border: 1px solid var(--hairline);
  }
  .empty, .error, .loading { color: var(--muted); font-size: 14px; padding: 20px 0; }
  .error { color: var(--error); }
  .table-wrap { overflow-x: auto; }
  .actions button {
    font-size: 12px;
    padding: 5px 10px;
    border-radius: 5px;
    border: 1px solid var(--hairline);
    background: var(--cream);
    cursor: pointer;
    margin-right: 6px;
  }
  .actions button.approve { border-color: var(--teal); color: var(--teal-dark); }
  .actions button.reject { border-color: var(--error); color: var(--error); }
</style>
</head>
<body>
<div class="wrap">
  <h1>Owner Dashboard</h1>
  <p class="subtitle">Shob business data ekhane dekho — conversations, orders, products, learning queue, follow-up, ar analytics.</p>

  <div class="topbar">
    <div class="field">
      <label for="ownerKey">Owner API Key</label>
      <input type="password" id="ownerKey" placeholder="tomar .env-er OWNER_API_KEY" autocomplete="off">
    </div>
    <div class="field">
      <label for="businessId">Business ID</label>
      <input type="text" id="businessId" placeholder="biz_xxxxxxxx">
    </div>
    <button class="reload" id="reloadBtn">Reload</button>
  </div>

  <div class="tabs" id="tabs"></div>
  <div class="panel" id="panel"><div class="loading">Owner API Key ar Business ID diye "Reload" chapo.</div></div>
</div>

<script>
const TABS = [
  { key: 'analytics',    label: 'Analytics',   path: '/dashboard/analytics' },
  { key: 'conversations',label: 'Conversations',path: '/dashboard/conversations' },
  { key: 'orders',       label: 'Orders',      path: '/dashboard/orders' },
  { key: 'products',     label: 'Products',    path: '/dashboard/products' },
  { key: 'services',     label: 'Services',    path: '/dashboard/services' },
  { key: 'faq',          label: 'FAQ',         path: '/dashboard/faq' },
  { key: 'policies',     label: 'Policies',    path: '/dashboard/policies' },
  { key: 'vocabulary',   label: 'Vocabulary',  path: '/dashboard/vocabulary' },
  { key: 'learning',     label: 'Learning Queue', path: '/learning' },
  { key: 'abandoned_conversations', label: 'Abandoned Chats', path: '/follow-up/abandoned-conversations' },
  { key: 'abandoned_orders',        label: 'Abandoned Orders', path: '/follow-up/abandoned-orders' },
  { key: 'segments',     label: 'Segments',    path: '/follow-up/segments' },
  { key: 'settings',     label: 'Settings',    path: '/dashboard/settings' },
];

let activeTab = 'analytics';
const tabsEl = document.getElementById('tabs');
const panelEl = document.getElementById('panel');

TABS.forEach(t => {
  const b = document.createElement('div');
  b.className = 'tab' + (t.key === activeTab ? ' active' : '');
  b.textContent = t.label;
  b.dataset.key = t.key;
  b.addEventListener('click', () => {
    activeTab = t.key;
    [...tabsEl.children].forEach(c => c.classList.toggle('active', c.dataset.key === activeTab));
    loadActiveTab();
  });
  tabsEl.appendChild(b);
});

function ownerKey() { return document.getElementById('ownerKey').value.trim(); }
function businessId() { return document.getElementById('businessId').value.trim(); }

async function apiGet(path) {
  const bid = businessId();
  const url = path + (path.includes('?') ? '&' : '?') + 'business_id=' + encodeURIComponent(bid);
  const resp = await fetch(url, { headers: { 'X-API-Key': ownerKey() } });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.error || ('HTTP ' + resp.status));
  return data;
}

async function apiPost(path, body) {
  const resp = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': ownerKey() },
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.error || ('HTTP ' + resp.status));
  return data;
}

function renderTable(rows) {
  if (!rows || rows.length === 0) return '<div class="empty">Kono data nei.</div>';
  const cols = Object.keys(rows[0]);
  let html = '<div class="table-wrap"><table><thead><tr>';
  cols.forEach(c => html += '<th>' + c + '</th>');
  html += '</tr></thead><tbody>';
  rows.forEach(r => {
    html += '<tr>';
    cols.forEach(c => {
      let v = r[c];
      if (v === null || v === undefined) v = '';
      html += '<td>' + String(v).replace(/</g, '&lt;') + '</td>';
    });
    html += '</tr>';
  });
  html += '</tbody></table></div>';
  return html;
}

function renderAnalytics(a) {
  const cards = [
    ['Total Conversations', a.total_conversations],
    ['Needs Human', a.conversations_needing_human],
    ['Total Orders', a.total_orders],
    ['Total Revenue', a.total_revenue],
    ['Products', a.total_products],
    ['Services', a.total_services],
    ['Pending Learning', a.pending_learning_queue],
  ];
  let html = '<div class="cards">';
  cards.forEach(([label, num]) => {
    html += '<div class="card"><div class="num">' + (num ?? '-') + '</div><div class="label">' + label + '</div></div>';
  });
  html += '</div>';
  if (a.orders_by_status && Object.keys(a.orders_by_status).length) {
    html += '<h3 style="margin-top:20px;font-size:14px;">Orders by status</h3>';
    html += Object.entries(a.orders_by_status).map(([k, v]) => '<span class="badge">' + k + ': ' + v + '</span> ').join('');
  }
  return html;
}

function renderLearningQueue(entries) {
  if (!entries || entries.length === 0) return '<div class="empty">Kono pending term nei.</div>';
  let html = '<div class="table-wrap"><table><thead><tr><th>Term</th><th>Detected Meaning</th><th>Context</th><th>Confidence</th><th>Actions</th></tr></thead><tbody>';
  entries.forEach(e => {
    html += '<tr>' +
      '<td>' + (e.term || '') + '</td>' +
      '<td>' + (e.detected_meaning || '') + '</td>' +
      '<td>' + (e.context || '') + '</td>' +
      '<td>' + (e.confidence || '') + '</td>' +
      '<td class="actions">' +
      '<button class="approve" data-id="' + e.learning_id + '">Approve</button>' +
      '<button class="reject" data-id="' + e.learning_id + '">Reject</button>' +
      '</td></tr>';
  });
  html += '</tbody></table></div>';
  return html;
}

function attachLearningActions() {
  panelEl.querySelectorAll('.approve').forEach(btn => {
    btn.addEventListener('click', async () => {
      const meaning = prompt('Approved meaning likhe daw:');
      if (meaning === null) return;
      try {
        await apiPost('/learning/' + btn.dataset.id + '/approve', { business_id: businessId(), meaning });
        loadActiveTab();
      } catch (e) { alert('Error: ' + e.message); }
    });
  });
  panelEl.querySelectorAll('.reject').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        await apiPost('/learning/' + btn.dataset.id + '/reject', { business_id: businessId() });
        loadActiveTab();
      } catch (e) { alert('Error: ' + e.message); }
    });
  });
}

async function loadActiveTab() {
  if (!ownerKey() || !businessId()) {
    panelEl.innerHTML = '<div class="error">Owner API Key ar Business ID dite hobe.</div>';
    return;
  }
  panelEl.innerHTML = '<div class="loading">Loading...</div>';
  const tab = TABS.find(t => t.key === activeTab);
  try {
    const data = await apiGet(tab.path);
    if (tab.key === 'analytics') {
      panelEl.innerHTML = renderAnalytics(data);
    } else if (tab.key === 'learning') {
      panelEl.innerHTML = renderLearningQueue(data.pending);
      attachLearningActions();
    } else if (tab.key === 'settings') {
      panelEl.innerHTML = renderTable([data.settings]);
    } else if (tab.key === 'abandoned_orders') {
      const rows = (data.abandoned_orders || []).map(r => ({ ...r.order, hours_since_created: r.hours_since_created }));
      panelEl.innerHTML = renderTable(rows);
    } else {
      const key = Object.keys(data).find(k => Array.isArray(data[k]));
      panelEl.innerHTML = renderTable(key ? data[key] : []);
    }
  } catch (e) {
    panelEl.innerHTML = '<div class="error">Error: ' + e.message + '</div>';
  }
}

document.getElementById('reloadBtn').addEventListener('click', loadActiveTab);
</script>
</body>
</html>
"""


@dashboard_view_bp.get("/dashboard/view")
def dashboard_view_page():
    """Public page shell — no business data lives here. Every real data
    call this page makes still goes through the existing owner-key-gated
    JSON endpoints (dashboard.py / learning.py / follow_up.py)."""
    return _PAGE, 200, {"Content-Type": "text/html; charset=utf-8"}
