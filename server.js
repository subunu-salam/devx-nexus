/* ══════════════════════════════════════════════════════════
   DEVX NEXUS — API + REAL-TIME SERVER WITH OPENAI CONCIERGE
   Supports: Live Inventory, Smart Alternatives, Multi-language,
   Recipe Prompts, and Dynamic Cart Building.
══════════════════════════════════════════════════════════ */
require('dotenv').config();
const express = require('express');
const http = require('http');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { Server } = require('socket.io');
const OpenAI = require('openai');
const Groq = require('groq-sdk');

const PORT = process.env.PORT || 3000;
const ADMIN_PIN = process.env.ADMIN_PIN || '1234';
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, 'data');
const DB_FILE = path.join(DATA_DIR, 'db.json');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

/* ══════════════════════════════════════════════════════════
   LLM LAYER — Groq Llama 3.1 (primary) → OpenAI (fallback)
   Both SDKs expose the same `chat.completions.create` shape,
   so the concierge calls one unified interface.
══════════════════════════════════════════════════════════ */
const isPlaceholder = k => !k || /your-.*-key-here/i.test(k) || k.trim() === '';
const GROQ_KEY = process.env.GROQ_API_KEY;
const OPENAI_KEY = process.env.OPENAI_API_KEY;

// maxRetries:0 + a short timeout make rate-limited/slow calls fail FAST and drop
// to the instant keyword fallback, instead of the SDK silently retrying with
// exponential backoff (the main cause of the long "thinking" delays).
const groq = !isPlaceholder(GROQ_KEY) ? new Groq({ apiKey: GROQ_KEY, maxRetries: 0, timeout: 12000 }) : null;
const openai = !isPlaceholder(OPENAI_KEY) ? new OpenAI({ apiKey: OPENAI_KEY, maxRetries: 0, timeout: 12000 }) : null;

// Choose the active provider: Groq Llama 3.1 first, OpenAI as fallback.
const LLM = groq
  ? { client: groq, model: 'llama-3.1-8b-instant', name: 'Groq Llama 3.1' }
  : openai
  ? { client: openai, model: 'gpt-4o-mini', name: 'OpenAI gpt-4o-mini' }
  : null;
// Whisper transcriber for voice input (Groq preferred, OpenAI fallback).
const TRANSCRIBER = groq
  ? { client: groq, model: 'whisper-large-v3' }
  : openai
  ? { client: openai, model: 'whisper-1' }
  : null;

console.log('[nexus] LLM provider:', LLM ? LLM.name : 'NONE (keyword fallback only — add GROQ_API_KEY)');

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

/* ══════════════════════════════════════════════════════════
   AI GROCERY CONCIERGE
   Pipeline:  Intent Classification → Product Search
              → Conversation Memory → LLM (strict JSON)
   The LLM may ONLY pick products that exist in live inventory,
   which eliminates hallucinated items.
══════════════════════════════════════════════════════════ */

/* ── 1. Conversation Memory (per session) ── */
const SESSIONS = new Map();          // session_id -> [{ role, content }, ...]
const MEM_TURNS = 8;                 // remember last 8 messages (4 exchanges)
const SESSION_TTL = 1000 * 60 * 60;  // forget a session after 1h idle
const SESSION_SEEN = new Map();      // session_id -> last activity ts

function getMemory(sid) {
  if (!SESSIONS.has(sid)) SESSIONS.set(sid, []);
  SESSION_SEEN.set(sid, Date.now());
  return SESSIONS.get(sid);
}
function pushMemory(sid, role, content) {
  const h = getMemory(sid);
  h.push({ role, content });
  while (h.length > MEM_TURNS) h.shift();
}
// Track which product groups we've already shown in a session, so follow-up
// "add drinks / also / more" requests only surface NEW items, never repeats.
const SUGGESTED = new Map();               // session_id -> Set(groupKey)
function suggestedSet(sid) {
  if (!SUGGESTED.has(sid)) SUGGESTED.set(sid, new Set());
  return SUGGESTED.get(sid);
}
const ADDON_RE = /\b(add|also|more|another|extra|plus|include|as well|too|instead|swap|to go with|alongside|with (that|it)|something (else|sweet)|dessert|drinks?)\b/i;
// Remember if we just asked the shopper a clarifying question, so their next
// message is treated as the ANSWER (and we don't loop asking again).
const PENDING_CLARIFY = new Map();   // session_id -> last clarify question
// periodic cleanup of idle sessions
setInterval(() => {
  const now = Date.now();
  for (const [sid, ts] of SESSION_SEEN) {
    if (now - ts > SESSION_TTL) { SESSIONS.delete(sid); SESSION_SEEN.delete(sid); }
  }
}, 1000 * 60 * 10).unref();

/* ── 2. Intent Classification ── */
function classifyIntent(q) {
  const t = ' ' + q.toLowerCase() + ' ';
  if (/(recipe|cook|dish|ingredient|make .*(for|dinner|lunch)|biryani|briyani|mandi|kabsa|machboos|curry|pasta|salad|bake|grill|bbq|barbecue|iftar|suhoor)/.test(t))
    return 'recipe_assistance';
  if (/(healthy|diet|low[\s-]?cal|low[\s-]?fat|protein|fitness|gym|nutriti|weight|keto|vegan|clean eating|sugar[\s-]?free)/.test(t))
    return 'healthy_recommendation';
  if (/(where|which aisle|which shelf|find the|locate|location of|navigat|how do i get to)/.test(t))
    return 'navigation';
  if (/(cheaper|cheapest|budget|under aed|less than|discount|offer|deal|save money|affordable|any alternative|something else)/.test(t))
    return 'shopping_help';
  if (/^\s*(hi|hii|hey|hello|salaam|salam|marhaba|thanks|thank you|thx|good (morning|evening|afternoon)|how are you|who are you|what can you do)\b/.test(q.toLowerCase()))
    return 'general_conversation';
  return 'product_search';
}

// Common dishes with clearly distinct variants — we deterministically ask which
// one (guarantees the behavior the small model is inconsistent about, and saves
// an LLM call). Only applied to English prompts; other languages go to the LLM.
const AMBIGUOUS_DISHES = {
  biryani: ['Chicken Biryani', 'Mutton Biryani', 'Prawn Biryani', 'Vegetable Biryani'],
  curry:   ['Chicken Curry', 'Fish Curry', 'Vegetable Curry', 'Paneer Curry'],
  pasta:   ['Chicken Pasta', 'Creamy Alfredo', 'Veg Pasta'],
  pizza:   ['Chicken Pizza', 'Margherita', 'Veg Pizza'],
  mandi:   ['Chicken Mandi', 'Mutton Mandi'],
  kabsa:   ['Chicken Kabsa', 'Mutton Kabsa']
};
function ambiguousDish(prompt) {
  const t = ' ' + prompt.toLowerCase() + ' ';
  if (/\b(chicken|mutton|lamb|prawn|shrimp|veg|vegetable|fish|beef|egg|paneer|mushroom|margherita)\b/.test(t)) return null;
  for (const [dish, opts] of Object.entries(AMBIGUOUS_DISHES)) {
    if (new RegExp('\\b' + dish + '\\b').test(t)) return { dish, opts };
  }
  return null;
}

// Detect the script of the CURRENT message so we can lock the reply language
// (the model was drifting to Hindi because earlier messages were Hindi).
function detectLang(text) {
  if (/[ऀ-ॿ]/.test(text)) return 'Hindi';
  if (/[؀-ۿ]/.test(text)) return 'Arabic/Urdu';
  if (/[ഀ-ൿ]/.test(text)) return 'Malayalam';
  if (/[஀-௿]/.test(text)) return 'Tamil';
  if (/[ঀ-৿]/.test(text)) return 'Bengali';
  return 'English';
}

const INTENT_GUIDE = {
  product_search:        'Find and recommend the matching products from inventory.',
  recipe_assistance:     'List the ingredient products needed for the dish, only ones that exist in inventory.',
  healthy_recommendation:'Recommend the healthiest in-stock options (fresh produce, lean protein, whole grains, low-sugar).',
  shopping_help:         'Help the shopper save money — suggest cheaper in-stock alternatives or budget-friendly picks.',
  navigation:            'Tell the shopper where items are using each product\'s "loc" (aisle/shelf). You may include product_ids you reference.',
  general_conversation:  'Reply warmly and briefly. Only include product_ids if the shopper actually asked for items.'
};

/* ── 3. Product Search (runs before the LLM) ── */
const STOPWORDS = new Set(['for','the','and','want','need','make','some','with','please','you','get','have','would','like','can','could','buy','shop','give','show','find','what','which','that','this','from','into','your','our','ingredients','recipe','something','anything','add','also','more']);
// Map casual words to store categories so "cold drinks" finds Beverages even
// without an exact name match (used to keep the keyword fallback useful).
const CAT_SYNONYMS = {
  'Beverages': ['drink','drinks','soda','sodas','cola','pepsi','coke','beverage','beverages','juice','juices','soft'],
  'Snacks': ['snack','snacks','chips','crisps','munchies','nachos','popcorn','wafer','wafers'],
  'Tea & Coffee': ['tea','coffee','karak','chai','nescafe'],
  'Bakery': ['bread','dessert','desserts','cake','sweet','sweets','bun','croissant'],
  'Dairy & Chilled': ['dairy','milk','yogurt','yoghurt','cheese','laban','butter','labneh'],
  'Fresh Produce': ['vegetable','vegetables','veg','fruit','fruits','produce'],
  'Fresh Meat': ['meat','chicken','beef','mutton','lamb','fish','seafood'],
  'Household': ['cleaning','detergent','soap','tissue','household','cleaner'],
  'Frozen': ['frozen','ice cream','icecream'],
  'Spices': ['spice','spices','masala']
};
function impliedCats(query) {
  const t = ' ' + query.toLowerCase() + ' ';
  const cats = [];
  for (const [cat, words] of Object.entries(CAT_SYNONYMS)) {
    if (words.some(w => t.includes(' ' + w) || t.includes(w + ' ') || t.includes(w + 's'))) cats.push(cat);
  }
  return cats;
}
function searchProducts(query, catalog) {
  const t = query.toLowerCase();
  const cats = impliedCats(query);
  const terms = t.split(/\s+/).filter(w => w.length > 2 && !STOPWORDS.has(w));
  return catalog
    .map(p => {
      let s = 0;
      const name = (p.name || '').toLowerCase();
      const cat  = (p.cat  || '').toLowerCase();
      const brand= (p.brand|| '').toLowerCase();
      const grp  = (p.group|| '').toLowerCase();
      terms.forEach(w => {
        if (name.includes(w))  s += 3;
        if (cat.includes(w))   s += 2;
        if (grp.includes(w))   s += 1;
        if (brand.includes(w)) s += 1;
      });
      if (cats.includes(p.cat)) s += 2;    // casual-word -> category match
      return { p, s };
    })
    .filter(x => x.s > 0)
    .sort((a, b) => b.s - a.s)
    .map(x => x.p);
}

/* ── Variant / group model ──────────────────────────────────
   A "group" = a shopper NEED (e.g. "basmati-rice") that spans
   several brands AND sizes. This is what powers:
     • generic queries  ("I want rice")  -> show all options
     • recipe queries    ("make biryani") -> auto-pick best value,
                                             offer the rest as swaps
   With a large catalog we DON'T inject every SKU into the prompt.
   Instead we inject one compact line per group (a "store menu"),
   which keeps prompts small and lets the model see the whole store.
─────────────────────────────────────────────────────────────*/
function inStock(p) { return p.stock == null || p.stock > 0; }

// Build group -> members map. Ungrouped items become their own solo group.
function buildGroups(catalog) {
  const groups = new Map();
  for (const p of catalog) {
    const key = p.group || ('solo-' + p.id);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(p);
  }
  return groups;
}

// Best-value default within a group:
//   1) in stock   2) on deal wins (biggest saving)   3) then lowest price.
// Shoppers still get every other brand/size as swappable alternatives,
// and can raise the quantity — so "value-first" is a safe, predictable default.
function bestValue(members) {
  const avail = members.filter(inStock);
  const pool = avail.length ? avail : members;
  return pool.slice().sort((a, b) => {
    const da = a.deal ? 1 : 0, dbb = b.deal ? 1 : 0;
    if (da !== dbb) return dbb - da;                       // deals first
    const sa = a.was ? (a.was - a.price) : 0, sb = b.was ? (b.was - b.price) : 0;
    if (sa !== sb) return sb - sa;                         // bigger saving
    return a.price - b.price;                              // then cheaper
  })[0];
}

function compact(p) {
  return {
    id: p.id, name: p.name, brand: p.brand || null, unit: p.unit,
    price: p.price, was: p.was || null, cat: p.cat, img: p.img || null,
    loc: p.loc || null, stock: p.stock != null ? p.stock : null,
    group: p.group || null, deal: !!p.deal
  };
}

// Other in-stock brands/sizes in the same group (for the "▾ other options" swap).
function alternativesFor(product, groups) {
  const key = product.group || ('solo-' + product.id);
  const members = groups.get(key) || [];
  return members
    .filter(m => m.id !== product.id && inStock(m))
    .sort((a, b) => a.price - b.price)
    .slice(0, 6)
    .map(compact);
}

// One terse line per group for the prompt "store menu".
// Format: group-key | Name | Category | AEDmin-max
// The model returns group-keys (short strings) which keeps the prompt small
// enough for Groq's free-tier token limit, and the backend expands each key
// into the best-value SKU + alternatives.
// Flat comma-separated list of group-keys. Keys are self-descriptive, so this
// is compact (stays under Groq's free-tier token/min cap) AND unambiguous —
// a category-grouped format made the model return category names by mistake.
function storeMenu(groups) {
  const keys = [];
  for (const [key] of groups) {
    if (key.startsWith('solo-')) continue;
    keys.push(key);
  }
  return keys.join(', ');
}

/* Tolerant JSON extraction from an LLM response. */
function parseLLMJson(text) {
  if (!text) return null;
  let s = text.trim().replace(/^```(?:json)?/i, '').replace(/```$/, '').trim();
  try { return JSON.parse(s); } catch (_) {}
  const a = s.indexOf('{'), b = s.lastIndexOf('}');
  if (a !== -1 && b !== -1 && b > a) {
    try { return JSON.parse(s.slice(a, b + 1)); } catch (_) {}
  }
  return null;
}

/* Build a plan row from a group's members: best-value default SKU,
   the requested quantity, and swappable alternatives. */
function rowFromMembers(members, qty, groups) {
  const def = bestValue(members);               // enforce value-first default
  return {
    p: compact(def),
    qty: Math.max(1, Math.min(20, parseInt(qty, 10) || 1)),
    alternatives: alternativesFor(def, groups)
  };
}
/* Build a plan row from any single product (resolves to its group first). */
function resolveRow(picked, qty, groups) {
  const key = picked.group || ('solo-' + picked.id);
  const members = groups.get(key) || [picked];
  return rowFromMembers(members, qty, groups);
}

/* ── Voice transcription (Whisper) ──
   The browser records mic audio and POSTs it here; we transcribe with Whisper,
   which auto-detects the language. Far more reliable than the browser's built-in
   speech API (which often fails with a network error). */
app.post('/api/transcribe',
  express.raw({ type: ['audio/webm', 'audio/ogg', 'audio/mp4', 'audio/mpeg', 'audio/wav', 'application/octet-stream'], limit: '20mb' }),
  async (req, res) => {
    if (!TRANSCRIBER) return res.status(503).json({ error: 'no transcription provider configured' });
    if (!req.body || !req.body.length) return res.status(400).json({ error: 'empty audio' });
    const tmp = path.join(os.tmpdir(), 'nx-voice-' + Date.now() + '.webm');
    // Language hint (ISO-639-1 like en/hi/ml/ar/ta) greatly improves accuracy
    // for non-English speech vs. auto-detect on short clips.
    const lang = (req.query.lang || '').toString().slice(0, 2).toLowerCase();
    try {
      fs.writeFileSync(tmp, req.body);
      const opts = { file: fs.createReadStream(tmp), model: TRANSCRIBER.model, temperature: 0 };
      if (lang && lang !== 'au') opts.language = lang;   // 'au' = auto → omit
      const r = await TRANSCRIBER.client.audio.transcriptions.create(opts);
      res.json({ text: (r && r.text ? r.text : '').trim() });
    } catch (e) {
      console.error('[nexus] transcribe error:', e.message);
      res.status(500).json({ error: 'transcription failed' });
    } finally {
      fs.unlink(tmp, () => {});
    }
  });

/* ── 4. The endpoint ── */
app.post('/api/concierge', async (req, res) => {
  // Accept both the frontend's {prompt} and the spec's {message}; session_id optional.
  const body = req.body || {};
  const prompt = (body.prompt || body.message || '').trim();
  const sessionId = body.session_id || body.sid || 'anon';
  if (!prompt) return res.status(400).json({ error: 'empty prompt' });

  const catalog = db['devx-catalog'] || [];
  const intent = classifyIntent(prompt);
  const replyLang = detectLang(prompt);   // lock reply to the CURRENT message's language
  const history = getMemory(sessionId);
  const groups = buildGroups(catalog);
  // An "add-on" is a follow-up like "add drinks", "also snacks", "anything cheaper"
  // — only true when there's prior context in this session.
  const addOn = history.length > 0 && ADDON_RE.test(prompt);
  const already = suggestedSet(sessionId);
  // "Refine" requests ("cheaper", "instead", "swap") genuinely need prior context.
  // "Add a new thing" requests ("add drinks", "some snacks") do NOT — and feeding
  // the old recipe history just makes a small model repeat it. So for those, we
  // send the model a clean slate (no history) to keep it focused on the new ask.
  const wantsRefine = /\b(cheaper|cheapest|instead|swap|replace|budget|less|alternative|other brand|other size)\b/i.test(prompt);
  const historyForLLM = (addOn && !wantsRefine) ? [] : history;
  // If we just asked a clarifying question, this message is the ANSWER — proceed
  // to recommend and do NOT ask again.
  const pendingQuestion = PENDING_CLARIFY.get(sessionId) || '';
  const answeringClarify = !!pendingQuestion;

  // Keyword candidates — used to prioritise and as a no-LLM fallback plan.
  const candidates = searchProducts(prompt, catalog);

  let reply = '';
  let followUp = '';
  let suggestions = [];
  let plan = [];
  let clarify = '';
  let recipe = null;
  let usedLLM = false;
  let llmError = '';

  // Deterministic clarify for a bare ambiguous dish (English only) — guarantees
  // "biryani -> which type?" and avoids a wasted LLM call.
  const amb = (!answeringClarify && !addOn && replyLang === 'English') ? ambiguousDish(prompt) : null;
  if (amb) {
    reply = `Sure — let's make ${amb.dish}!`;
    clarify = `Which ${amb.dish} would you like to make?`;
    suggestions = amb.opts;
    PENDING_CLARIFY.set(sessionId, clarify);
    pushMemory(sessionId, 'user', prompt);
    pushMemory(sessionId, 'assistant', reply + ' ' + clarify);
    return res.json({
      key: 'ai_concierge', intent, reply, clarify, recipe: null,
      follow_up: '', suggestions, plan: [], products: [], meta: null,
      total: 0, session_id: sessionId, model: 'rule'
    });
  }

  if (LLM && catalog.length) {
    const systemPrompt =
`You are "DevX AI Concierge", a friendly grocery assistant for a UAE supermarket.

REPLY LANGUAGE: Write reply, clarify, options, follow_up, suggestions and any recipe text ONLY in ${replyLang}. Ignore the language of earlier messages — match THIS message.

Return STRICT JSON only (no markdown), exact shape:
{"reply":"1-2 sentences","clarify":"","options":[],"recipe":null,"items":[{"group":"basmati-rice","qty":1}],"follow_up":"","suggestions":["",""]}

RULES:
- "group" MUST be one of the exact comma-separated keys in STORE MENU below (e.g. basmati-rice, whole-chicken, onions). Never invent a key. Pick ONE key per need — the app shows the brands/sizes.
- SCOPE: You help with SUPERMARKET shopping — food & groceries, household, cleaning, personal care, baby, pet, stationery & office (pens, notebooks...), electrical & batteries, kitchen & dining, plus recipes, meal/shopping planning and store navigation. The STORE MENU is the source of truth for what we stock. If the shopper wants a product, help them find it. If the specific item is NOT in the STORE MENU, say we don't currently stock it and optionally suggest a close item we DO have — do NOT show unrelated products. Only DECLINE actual non-shopping questions (weather, news, general knowledge, jokes, math): briefly say you help with shopping at this store. Do not refuse a normal product just because it isn't food — supermarkets sell pens, batteries, etc.
- Every "suggestions" / follow-up you offer MUST be a product or category we actually stock (in the STORE MENU). Never suggest something we don't sell (e.g. don't offer "Naan Bread" unless a naan key exists).
- CLARIFY is ONLY for a missing DISH variant (e.g. bare "biryani" -> Chicken/Mutton/Prawn/Vegetable; bare "cake" -> flavor). NEVER clarify about brand, size, quantity, or which type of an ingredient (e.g. "which rice?") — the app auto-picks the best value and shows the other options. If the dish/product is already specified ("chicken biryani", "basmati rice"), DO NOT clarify — return items. Ask AT MOST ONCE.${answeringClarify ? ' The current message ANSWERS your previous question — return items now, clarify:"".' : ''}
- items = the shopper's CART: the product groups with sensible quantities. When the shopper NAMES or ASKS FOR a product ("AA batteries", "do you have naan", "I need milk"), you MUST put that product's group in items right away — never just describe it or ask "would you like to add it" while leaving items empty. For a DISH, include the CORE ingredients across categories and pick ONE protein (e.g. biryani -> basmati-rice, ONE chicken group, onions, tomatoes, plain-yogurt, sunflower-oil, biryani-masala, garam-masala). Do NOT add several cuts of the same meat.
- "suggestions" and "options" must be short HUMAN-READABLE phrases (e.g. "AAA batteries", "Add cold drinks"), NEVER raw group-keys like "aaa-battery".
- recipe: fill title + 4-8 steps ONLY if the shopper explicitly asks for a recipe / how to cook / steps. For "cart", "ingredients", "what do I need", "build a cart", "suggest a cart" -> recipe MUST be null (just items).
- ADD-ON ("add", "also", "more"): return ONLY the new groups, never repeat earlier items.${addOn ? ' This IS an add-on — only new items, clarify:"".' : ''}
- Never mention prices (the app shows them). Keep follow_up short and proactive.

STORE MENU:
${storeMenu(groups)}`;

    const messages = [
      { role: 'system', content: systemPrompt },
      ...historyForLLM.slice(-4),   // last 2 exchanges only → smaller/faster request
      { role: 'user', content: prompt }
    ];

    try {
      // One quick retry on a rate-limit hiccup, so a transient 429 becomes a
      // slightly-slower success instead of the "I'm busy" message.
      let completion, attempt = 0;
      while (true) {
        try {
          completion = await LLM.client.chat.completions.create({
            model: LLM.model,
            messages,
            temperature: 0.3,
            max_tokens: 500,
            response_format: { type: 'json_object' }
          });
          break;
        } catch (err) {
          if (attempt < 1 && (err.status === 429 || /rate.?limit/i.test(err.message || ''))) {
            attempt++;
            await new Promise(r => setTimeout(r, 2500));
            continue;
          }
          throw err;
        }
      }
      const raw = completion.choices?.[0]?.message?.content || '';
      const parsed = parseLLMJson(raw);
      if (parsed && typeof parsed.reply === 'string') {
        reply = parsed.reply;
        followUp = typeof parsed.follow_up === 'string' ? parsed.follow_up : '';
        clarify = typeof parsed.clarify === 'string' ? parsed.clarify.trim() : '';
        if (answeringClarify) clarify = '';   // never re-ask after an answer
        suggestions = Array.isArray(parsed.suggestions)
          ? parsed.suggestions.filter(s => typeof s === 'string').slice(0, 4) : [];
        // Recipe steps (only when the shopper asked for a recipe).
        if (parsed.recipe && Array.isArray(parsed.recipe.steps) && parsed.recipe.steps.length) {
          recipe = {
            title: typeof parsed.recipe.title === 'string' ? parsed.recipe.title : '',
            steps: parsed.recipe.steps.filter(s => typeof s === 'string').slice(0, 10)
          };
        }
        // Always try to build the product list from items.
        let items = [];
        if (Array.isArray(parsed.items)) {
          items = parsed.items.map(it => ({ group: it.group, id: it.id, qty: it.qty }));
        } else if (Array.isArray(parsed.product_ids)) {
          items = parsed.product_ids.map(id => ({ id, qty: 1 }));
        }
        const seenGroups = new Set(), seenNames = new Set();
        for (const it of items) {
          let gkey = null, members = null;
          if (it.group && groups.has(it.group)) {
            gkey = it.group; members = groups.get(gkey);
          } else if (it.id != null) {
            const picked = catalog.find(p => String(p.id) === String(it.id));
            if (picked) { gkey = picked.group || ('solo-' + picked.id); members = groups.get(gkey) || [picked]; }
          }
          if (!members || seenGroups.has(gkey)) continue;   // one row per need
          const row = rowFromMembers(members, it.qty, groups);
          const nm = (row.p.name || '').toLowerCase();
          if (seenNames.has(nm)) continue;                  // no duplicate product names
          seenGroups.add(gkey); seenNames.add(nm);
          plan.push(row);
          if (plan.length >= 12) break;
        }
        // Products win: if we have products to show, don't block on a clarify.
        if (plan.length) {
          clarify = '';
        } else if (clarify) {
          const opts = Array.isArray(parsed.options) ? parsed.options.filter(s => typeof s === 'string').slice(0, 4) : [];
          if (opts.length) suggestions = opts;
          followUp = '';
        }
        usedLLM = true;
      }
    } catch (error) {
      llmError = (error && (error.status === 429 || /rate.?limit|too many|quota/i.test(error.message || ''))) ? 'rate' : 'other';
      console.error('[nexus] LLM (' + LLM.name + ') warning:', error.message);
    }
  }

  // Fallback when no LLM configured or the call failed / returned bad JSON.
  // IMPORTANT: never dump random products for things we don't understand.
  if (!usedLLM) {
    if (llmError === 'rate') {
      reply = "I'm handling a lot of requests right now — please try again in a few seconds.";
    } else if (intent === 'general_conversation') {
      reply = "Hi! I'm your DevX AI Concierge. Tell me what you'd like to cook or shop for and I'll pull the right items from our shelves.";
      suggestions = ['Ingredients for biryani', 'Something healthy', 'Snacks for movie night'];
    } else if (candidates.length) {
      // We DID match real products to the words — safe to show them.
      const seenGroups = new Set();
      for (const p of candidates) {
        const gkey = p.group || ('solo-' + p.id);
        if (seenGroups.has(gkey)) continue;
        seenGroups.add(gkey);
        plan.push(resolveRow(p, 1, groups));
        if (plan.length >= 6) break;
      }
      reply = 'Here are the matches from our live store inventory:';
      followUp = 'Would you like me to add anything else or show other brands?';
    } else {
      // No match and not chit-chat: DON'T guess. Ask, don't dump.
      reply = "I didn't quite catch that. I can help you find products, plan a recipe, or build a shopping list — what are you looking for?";
      suggestions = ['Ingredients for a dish', 'Something healthy', 'Household items'];
    }
  }

  // NOTE: when the LLM succeeds we TRUST its item list. If it returned no items
  // that is deliberate (off-topic question or a clarifying question), so we must
  // NOT force-add keyword matches — that was causing random products to appear
  // for unrelated questions.

  // Safety net: on an add-on request, drop any rows whose group was already
  // shown earlier this session, so the model can't repeat the previous list.
  const rowGroup = r => r.p.group || ('solo-' + r.p.id);
  if (addOn && plan.length) {
    const fresh = plan.filter(r => !already.has(rowGroup(r)));
    if (fresh.length) plan = fresh;   // keep only new items; if all repeats, leave as-is
  }

  // Honest handling when an add-on request resolved to nothing (item not stocked):
  // don't let the model claim it "added" a product that isn't there.
  if (usedLLM && addOn && !clarify && !plan.length) {
    reply = "Sorry, we don't stock that one. Want me to suggest something similar we do carry?";
  }

  // Humanize any suggestion that leaked through as a raw group-key.
  const humanize = s => {
    if (groups.has(s)) return groups.get(s)[0].name;
    if (/^[a-z0-9]+(-[a-z0-9]+)+$/.test(s)) return s.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    return s;
  };
  suggestions = suggestions.map(humanize);

  // Remember the groups we're showing now (for future add-on filtering).
  plan.forEach(r => already.add(rowGroup(r)));

  const total = plan.reduce((sum, r) => sum + (r.p.price * r.qty), 0);

  // Track pending clarify so the NEXT message is treated as the answer.
  if (clarify) PENDING_CLARIFY.set(sessionId, clarify);
  else PENDING_CLARIFY.delete(sessionId);

  // Save this exchange to memory (store the plain reply text).
  pushMemory(sessionId, 'user', prompt);
  pushMemory(sessionId, 'assistant', reply + (followUp ? ' ' + followUp : ''));

  res.json({
    key: 'ai_concierge',
    intent,
    reply,
    clarify,
    recipe,
    follow_up: followUp,
    suggestions,
    plan,
    products: plan.map(x => x.p),   // spec-compatible field
    meta: null,
    total,
    session_id: sessionId,
    model: usedLLM ? LLM.name : 'keyword-fallback'
  });
});

/* Customer places an order */
app.post('/api/orders', (req, res) => {
  const o = req.body || {};
  if (!Array.isArray(o.items) || !o.items.length) return res.status(400).json({ error: 'empty order' });
  if (!['delivery', 'pickup'].includes(o.mode)) return res.status(400).json({ error: 'bad mode' });

  db['devx-order-count'] += 1;
  o.id = 'NX-' + String(db['devx-order-count']).padStart(4, '0');
  o.date = new Date().toISOString();
  o.status = 'new';
  o.history = [{ s: 'new', at: o.date }];

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

/* Admin writes — PIN required */
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
  console.log(`[nexus] DevX Nexus running  →  http://localhost:${PORT}  (admin: /admin, PIN: ${ADMIN_PIN})`);
});
