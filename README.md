# DevX Nexus — AI Supermarket Platform

One deployable product, three surfaces:

| URL | What it is |
|---|---|
| `/` | Customer app — AI concierge, smart budget carts, store navigation, pickup pass |
| `/admin` | Store Operations platform (CRM) — orders, pickup counter, scanner, inventory, offers, customers |
| `/store-entry-qr.html` | Printable store-entrance poster — QR auto-points to your live URL |

Everything is connected in real time through the Node server (REST API + Socket.IO push):
customer order → appears in admin instantly (with sound) · admin publishes offer / adds product /
changes price / updates order status → customer app updates and gets a notification within a second,
on any device, anywhere.

## Run locally (your MacBook)

```bash
cd devx-nexus
npm install
npm start
```

Open http://localhost:3000 (customer) and http://localhost:3000/admin (PIN: **1234**) in two windows.

## Deploy to Render (free)

1. Push this folder to a GitHub repo:
   ```bash
   cd devx-nexus
   git init && git add -A && git commit -m "DevX Nexus v1"
   git remote add origin https://github.com/YOURNAME/devx-nexus.git
   git push -u origin main
   ```
2. On https://dashboard.render.com → **New → Web Service** → pick the repo.
   Render reads `render.yaml` automatically (build `npm install`, start `node server.js`).
   Or set them manually. Set env var **ADMIN_PIN** to your own PIN.
3. Done. Your product is live at `https://your-app.onrender.com`
   - customers: that URL (share it / print the QR poster page)
   - staff: `…/admin`

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `PORT` | 3000 | server port (Render sets this automatically) |
| `ADMIN_PIN` | 1234 | protects all admin writes (server-side check) |
| `DATA_DIR` | ./data | where db.json is stored |

## Important production notes (be honest with your client)

- **Data persistence on Render free tier is ephemeral** — the JSON database resets when the
  service redeploys or restarts. For real production attach a Render Disk (persistent, paid)
  and set `DATA_DIR=/var/data`, or migrate storage to Postgres (the storage layer is isolated
  in `server.js` — load/save — so swapping it is contained).
- **Demo data**: the 47 products, prices, brands and the 6 historical orders are sample data.
  Replace them via `/admin → Inventory` (add/edit products, click an image to change it) or by
  editing `seed.json` before first deploy.
- **Payments are not integrated** — orders are cash-on-delivery/pickup style. Stripe/Telr/etc.
  is the natural next step.
- The AI concierge is a deterministic on-device engine (budget parser + scenario library +
  brand scoring). No API keys needed, works offline, fully explainable — see README-LOGIC.
- Customer identity is a per-device ID (no signup friction — right for labour customers).
  OTP/WhatsApp login can be layered on later.

## Files

```
server.js          API + Socket.IO + storage
seed.json          initial product catalog
public/index.html  customer app (works standalone too — falls back to local demo mode)
public/admin.html  store platform (same dual-mode)
public/store-entry-qr.html  printable poster
render.yaml        Render blueprint
```
