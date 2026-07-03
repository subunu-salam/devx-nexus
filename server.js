/* ══════════════════════════════════════════════════════════
   DEVX NEXUS — API + REAL-TIME SERVER
   Serves:  /            customer app
            /admin       store operations platform (PIN protected writes)
            /api/*       REST API
            Socket.IO    real-time push to every connected device
   Storage: JSON file (DATA_DIR/db.json) with atomic writes.
   Env:     PORT (default 3000), ADMIN_PIN (default 1234), DATA_DIR
══════════════════════════════════════════════════════════ */
const express = require('express');
const http = require('http');
const path = require('path');
const fs = require('fs');
const { Server } = require('socket.io');

const PORT = process.env.PORT || 3000;
const ADMIN_PIN = process.env.ADMIN_PIN || '1234';
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, 'data');
const DB_FILE = path.join(DATA_DIR, 'db.json');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

/* ── storage ── */
const KEYS = ['devx-catalog', 'devx-orders', 'devx-offers', 'devx-notifs-customer', 'devx-activity'];
let db = {
  'devx-catalog': null,
  'devx-orders': [],
  'devx-offers': [],
  'devx-notifs-customer': [],
  'devx-activity': [],
  'devx-order-count': 0
};

function load() {
  try {
    if (fs.existsSync(DB_FILE)) {
      db = Object.assign(db, JSON.parse(fs.readFileSync(DB_FILE, 'utf8')));
      console.log('[nexus] state loaded from', DB_FILE);
    }
  } catch (e) { console.error('[nexus] load failed:', e.message); }
}
let saveT = null;
function save() {
  clearTimeout(saveT);
  saveT = setTimeout(() => {
    try {
      fs.mkdirSync(DATA_DIR, { recursive: true });
      const tmp = DB_FILE + '.tmp';
      fs.writeFileSync(tmp, JSON.stringify(db));
      fs.renameSync(tmp, DB_FILE);
    } catch (e) { console.error('[nexus] save failed:', e.message); }
  }, 150);
}

/* ── seed catalog on first boot ── */
function seedCatalog() {
  if (db['devx-catalog'] && db['devx-catalog'].length) return;
  try {
    const seed = JSON.parse(fs.readFileSync(path.join(__dirname, 'seed.json'), 'utf8'));
    db['devx-catalog'] = seed.map((p, i) => Object.assign({}, p, { stock: p.stock != null ? p.stock : (18 + ((i * 7) % 30)) }));
    save();
    console.log('[nexus] catalog seeded:', db['devx-catalog'].length, 'products');
  } catch (e) { console.error('[nexus] seed failed:', e.message); }
}

/* ── helpers ── */
const isAdmin = req => (req.headers['x-admin-pin'] || '') === ADMIN_PIN;
function broadcast(changed) { io.emit('sync', changed); }
function activity(type, msg) {
  db['devx-activity'].unshift({ type, msg, at: new Date().toISOString() });
  db['devx-activity'] = db['devx-activity'].slice(0, 120);
}
function notify(type, title, msg, cid) {
  db['devx-notifs-customer'].unshift({
    id: 'n' + Date.now() + Math.random().toString(36).slice(2, 6),
    type, title, msg, cid: cid || null, at: new Date().toISOString()
  });
  db['devx-notifs-customer'] = db['devx-notifs-customer'].slice(0, 60);
}
function publicState(cid) {
  return {
    'devx-catalog': db['devx-catalog'],
    'devx-offers': db['devx-offers'],
    'devx-activity': [],
    'devx-notifs-customer': db['devx-notifs-customer'].filter(n => !n.cid || n.cid === cid),
    'devx-orders': db['devx-orders'].filter(o => o.cid === cid)
  };
}
function fullState() {
  const s = {};
  KEYS.forEach(k => s[k] = db[k]);
  return s;
}

/* ── middleware ── */
app.use(express.json({ limit: '2mb' }));
app.use((req, res, next) => { res.set('Cache-Control', 'no-store'); next(); });

/* ── API ── */
app.get('/api/health', (req, res) => res.json({ ok: true, orders: db['devx-orders'].length, products: (db['devx-catalog'] || []).length }));

app.get('/api/state', (req, res) => {
  if (isAdmin(req)) return res.json(fullState());
  if (req.headers['x-admin-pin']) return res.status(401).json({ error: 'wrong pin' });
  res.json(publicState(req.query.cid || ''));
});

/* Customer places an order — server is the source of truth:
   assigns the ID, reserves stock atomically, notifies, broadcasts. */
app.post('/api/orders', (req, res) => {
  const o = req.body || {};
  if (!Array.isArray(o.items) || !o.items.length) return res.status(400).json({ error: 'empty order' });
  if (!['delivery', 'pickup'].includes(o.mode)) return res.status(400).json({ error: 'bad mode' });

  db['devx-order-count'] += 1;
  o.id = 'NX-' + String(db['devx-order-count']).padStart(4, '0');
  o.date = new Date().toISOString();
  o.status = 'new';
  o.history = [{ s: 'new', at: o.date }];

  /* stock reservation + honest totals re-check */
  const cat = db['devx-catalog'] || [];
  let sub = 0;
  for (const it of o.items) {
    const p = cat.find(x => x.id === it.id);
    if (!p) return res.status(400).json({ error: 'unknown product ' + it.id });
    if (p.stock != null && p.stock < it.qty) return res.status(409).json({ error: p.name + ': only ' + p.stock + ' left' });
    it.price = p.price; it.name = p.name; it.loc = p.loc; it.unit = p.unit;
    sub += p.price * it.qty;
  }
  o.sub = Math.round(sub * 100) / 100;
  o.fee = o.mode === 'delivery' ? 10 : 0;
  o.total = Math.round((o.sub + o.fee) * 100) / 100;
  o.items.forEach(it => { const p = cat.find(x => x.id === it.id); if (p.stock != null) p.stock = Math.max(0, p.stock - it.qty); });

  db['devx-orders'].unshift(o);
  activity('order', `New ${o.mode} order ${o.id} — ${(o.customer && o.customer.name) || 'Guest'} — AED ${o.total}`);
  notify('order', 'Order ' + o.id + ' placed',
    o.mode === 'delivery'
      ? "We're preparing your delivery. Track it live in My Orders."
      : 'Reserved at ' + ((o.branch || '').split('—')[1] || 'the store').trim() + '. Your pickup pass is ready.',
    o.cid);
  save();
  broadcast({ 'devx-orders': db['devx-orders'], 'devx-catalog': db['devx-catalog'], 'devx-notifs-customer': db['devx-notifs-customer'], 'devx-activity': db['devx-activity'] });
  res.json({ order: o, state: publicState(o.cid || '') });
});

/* Admin writes (catalog, orders, offers, notifs, activity) — PIN required */
app.post('/api/admin/set', (req, res) => {
  if (!isAdmin(req)) return res.status(401).json({ error: 'unauthorized' });
  const { key, value } = req.body || {};
  if (!KEYS.includes(key)) return res.status(400).json({ error: 'bad key' });
  db[key] = value;
  save();
  broadcast({ [key]: value });
  res.json({ ok: true });
});

/* ── static frontends ── */
app.use(express.static(path.join(__dirname, 'public')));
app.get('/admin', (req, res) => res.sendFile(path.join(__dirname, 'public', 'admin.html')));

load();
seedCatalog();
server.listen(PORT, () => {
  console.log(`[nexus] DevX Nexus running  →  http://localhost:${PORT}   (admin: /admin, PIN: ${ADMIN_PIN})`);
});
