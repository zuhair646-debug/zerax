# Zenrex — Multi-tenant AI Commerce Platform (PRD)

## Original Problem Statement
Build "Zenrex" — a multi-tenant Saudi/Arab AI commerce platform with:
1. Conversational FreeBuild chat interface for building sites/apps from scratch
2. Smart Orchestrator unifying AI models (Anthropic Claude)
3. Ready Sites module (template-first)
4. Integrated Video Studio for AI-generated promo videos
5. Driver App + Delivery management (Haversine + dynamic pricing)
6. Global & local payment gateway catalog
7. Standalone professional Admin Dashboard with real-time KPIs and AI workspace

## Financial Model (Confirmed by User — Feb 2026)
**Tech-partner only, NO commission on sales.** Revenue from:
- 💳 Monthly subscriptions (99-299 SAR/month tiers)
- ⚡ AI point packs (1000/2000/5000/10000)
- 🚚 Delivery service fees (from drivers' withdrawals, not merchants)
- 🛠️ One-time add-ons: domain, custom email, premium template, mobile app

## Current State (Feb 2026)

### ✅ COMPLETED in admin.html (Merchant Control Panel)
- **Dashboard**: Live KPIs (clickable), interactive SVG chart with hover tooltips,
  Top Products clickable, recent orders, **AI Weekly Report card** (dismissible)
- **Products + Product Studio** (3 tabs, fullscreen toggle):
  + **Stock management** (Feb 2026): SKU, low-stock threshold alert, out-of-stock badges
  + **Expiry tracking** (Feb 2026): manufacturing date, expiry date, "ينتهي خلال X يوم" warning, color-coded badges on cards
- **PDF Reports** (Feb 2026, NEW):
  + 6 report types: Sales, Products, Customers, Inventory, ZATCA, Monthly Summary
  + Real PDF generation via jsPDF (downloadable A4)
  + WhatsApp share button (wa.me with formatted summary text)
  + Email share button (mailto: prefilled)
- **ZATCA Phase 2 E-Invoice** (Feb 2026, NEW, mock):
  + Merchant config: VAT (15-digit), CR, name (ar/en), address
  + CSR generation + CSID upload UI
  + Environment switch (Sandbox / Production)
  + Sample invoice generator with valid UBL 2.1 XML structure
  + Real TLV QR code (tags 1-5) rendered via qrcode.js
  + PDF/A-3 download (with embedded XML reference)
- **Campaign Builder** (Feb 2026, NEW):
  + 5-step wizard modal (basic info → audience → message → channels → budget)
  + Audience targeting: segments (VIP/new/inactive/repeat/all), interests (7 categories), age range, gender
  + 6 send channels (WhatsApp/SMS/Email/Push/Instagram/Snapchat) with per-channel cost
  + Live audience + cost estimation
  + Coupon attachment, preview button, scheduled launch
- **Original Product Studio** (kept):
  1. Basic Info — image upload, name, price, stock, category
  2. Creative Studio — 5 types (product/logo/banner/section/animated) +
     bg-color/frame-color/aspect pickers
  3. Deep AI Analysis — 12 sections: title, what's new, comparison, features,
     benefits, usage steps, side effects, specs, colors, sizes, warranty, official URL
- **Video Studio** (5 tabs, fullscreen, dark Zenrex theme):
  1. Script (Gemini storyboard with 44 dialects + 12 voices)
  2. Scenes (editable storyboard, approve per scene)
  3. Images (Gemini Nano Banana, approve per image, 8pts each)
  4. Voice (Zenrex TTS, preview before approve, 5pts)
  5. Final Video (ffmpeg merge, 30pts on click only)
  + Working mic (Web Speech API, dialect-aware)
  + Voice preview button
  + Real-time cost estimator
- **Delivery** with auto-dispatch:
  - Master toggle + per-order auto-assign button
  - Settings: radius, grouping, max orders/driver, priority, withdraw fee
  - Driver pay model per driver (commission % or monthly salary + bonus)
  - 5 payout methods (bank/STC Pay/urpay/PayPal/cash)
- **Smart Management**:
  - Auto-post to 7 social platforms (Instagram, TikTok, X, Snapchat, FB, WhatsApp, Telegram)
  - Customizable post template with variables
  - 5 timing options (immediate/+15min/+1hr/peak/manual)
  - Smart Replies: 2 modes (canned free / AI 1pt per reply)
  - Personality config, daily limit, auto-handoff to human
- **Services Catalog** (7 services with auto-activation):
  1. Custom domain (99 SAR/year)
  2. Branded email (49 SAR/year)
  3. Premium template (199 SAR one-time)
  4. iOS/Android app (999 SAR one-time)
  5. Smart delivery (79 SAR/month)
  6. VIP support (99 SAR/month)
  7. AI Premium Claude Opus (149 SAR/month)
- **Social Media** page (8 platforms with connect/disconnect + recent posts)
- **Recharge modal** (4 packages: 1k/2k/5k/10k)
- **Wallet** default 5000 points + auto-boost on low balance
- **Notifications & user dropdown menus**
- **Global search** filters products

### ✅ COMPLETED in app_mode_full.html (Customer Storefront)
- Rich product detail page with deep AI analysis renderer (`buildRichAnalysisClientHTML`)
- Light-themed cards matching customer-facing aesthetic
- 8 dynamic sections rendered when analysis exists
- Falls back to legacy info.html for old products
- **P1 Customer Features (Feb 2026)**:
  - ❤ Wishlist: heart toggle on every product card, dedicated wishlist page + bnav tab, badge in header
  - 🔐 OTP Login modal: phone-based auth (demo OTP `1234`), session persisted in localStorage, account-page shows logged-in state + logout
  - ⭐ Product Reviews: per-product reviews with 5-star picker + text, requires login, avg rating displayed, stored per product key
  - 🎟️ Coupons: 3 codes seeded (`WELCOME10` 10%, `SAVE50` flat 50, `FREESHIP` flat 25) with live cart total recalc including tax-on-discounted-base
  - 🔗 Share Wishlist (NEW): `?wl=p1,p5,...` URL deep-link, WhatsApp/native share, clipboard fallback, auto-import on visit
  - Fixed pre-existing `pdJump()` orphan code that was breaking the page

### ✅ MongoDB + JWT Integration Phase 1 (Feb 2026)
- New router `/app/backend/routers/store_router.py` (registered in server.py):
  - `GET /api/store/health`
  - `POST /api/store/customer/request-otp` · `POST /api/store/customer/verify-otp` · `GET /api/store/customer/me`
  - `GET/POST/PUT/DELETE /api/store/products` (merchant-scoped via JWT)
  - `GET/POST /api/store/wishlist` (per-customer)
  - `GET /api/store/reviews/{pid}` · `POST /api/store/reviews`
- `admin.html`: real `/api/auth/login` flow, JWT stored in localStorage, all products CRUD goes through API
- `app_mode_full.html`: real customer OTP via backend, wishlist + reviews sync to MongoDB when logged in
- Mongo collections used: `users` (existing), `store_products`, `customers`, `customer_otps`, `customer_wishlists`, `product_reviews`
- Test creds: `owner@zenrex.ai` / `owner123` (admin), any phone + OTP `1234` (customer)

### 🟡 MOCKED (functional UI, no live backend)
- admin.html login uses localStorage (no JWT)
- Products + orders use seed data (no MongoDB sync between admin/customer)
- Social OAuth not implemented (toggles save to localStorage)
- Service activations are localStorage flags only
- Auto-dispatch endpoint /api/delivery/auto-assign falls back to simulation

### 🟢 LATEST (Feb 10, 2026 · Dark Theme + Sandbox Wave — LAUNCH-READY)
- **🌙 Zenrex Unified Dark Theme** (`/mockups/zenrex-theme.css`):
  - Single source of truth via CSS variables (`--zx-*`)
  - Deep navy-black bg (`#0a0a14`), elegant violet/amber accents, subtle borders
  - Injected into `admin.html`, `app_mode_full.html`, `driver_app.html`
  - Onboarding modal redesigned dark with radial gradient hero + per-step accent tints
  - Custom themed scrollbars · luxurious shadows · `.zx-btn-primary/.zx-card/.zx-input` utilities
- **🎨 Theme Router** (`/api/theme/*`):
  - `GET /defaults` — platform default dark theme
  - `GET /merchant/me` + `PUT /merchant/me` — per-merchant theme override (colors/fonts/radius/buttons)
  - `GET /by-merchant/{id}` — public; customer storefront + driver app fetch merchant theme automatically
  - `POST /merchant/reset` — restore platform default
- **🏖️ Sandbox Router** (`/api/sandbox/*`): Full end-to-end test mode for ALL checkout
  - 10 Payment Gateways (Tabby/Tamara/Mada/STC Pay/HyperPay/Moyasar/Stripe/PayPal/ApplePay/COD)
  - 6 Shipping Providers (Aramex/SMSA/Naqel/DHL/J&T/Zenrex Fleet)
  - Beautiful PSP-branded checkout pages (Tabby green, Tamara purple, etc.)
  - Smoke-tested end-to-end: Tabby payment → Aramex label → 5-event delivery timeline

### 🔴 PENDING (Priority Order)

**P1 — CRITICAL NEXT**
- Zenrex Landing Page (marketing site) — promised next
- MongoDB persistence for admin.html ↔ app_mode_full.html sync
- JWT real auth on admin.html

**P2**
- Real OAuth (Meta/Google/X) for social connections
- Backend: /api/delivery/auto-assign with Haversine + nearest driver logic
- Backend: /api/social/auto-post (Meta Graph, TikTok Business, Twitter API)
- Backend: /api/replies/smart (Gemini-powered DM responder)
- Tabby/Tamara live payment execution
- ZATCA Phase 2 (XML + PDF/A-3 + QR)

**P3**
- ElevenLabs voice integration (cinematic quality)
- claude_core orchestrator for unified AI agents
- LiveKit voice agent / call-center AI
- Voice/Video section on main marketing site

## Tech Stack
FastAPI + MongoDB · Vanilla HTML/JS mockups + React main app ·
**Direct-SDK LLM (Jun 2026)**: Anthropic Claude Sonnet 4.5/4.6 · Google Gemini 2.5/3.1 (text + Nano Banana image gen) · OpenAI GPT-4o/5 · OpenAI Whisper · ElevenLabs Arabic TTS · ffmpeg · Web Speech API ·
**Bypass shim**: `backend/direct_llm_shim.py` transparently replaces `emergentintegrations.llm.chat` when `USE_DIRECT_LLM=1`, making the platform 100% independent of Emergent's platform.

## Production Deployment (Hetzner VPS — Jun 11 2026)
- **IP**: `91.98.154.148`
- **Stack**: Docker (`docker-compose.yml`) + Nginx (gzip + caching + uploads)
- **DB**: ⭐ **MongoDB Atlas M2** (`cluster0.1tkzj4x.mongodb.net`) DB=`zerax_prod` — migrated Jun 11 2026 (146 docs). Local `zerax-mongo-1` kept as fallback backup.
- **Backend**: Uvicorn inside `zerax-backend-1` (auto-pip-install on start)
- **JWT_SECRET**: Fixed via `.env` (no token loss on restart)
- **AI**: Fully working via direct provider keys (Claude/Gemini/OpenAI/FAL.ai 1.5s)
- **Image serving**: `/static/uploads/` → `/opt/zenrex/data/uploads/` (persistent volume)
- **Gzip**: HTML/CSS/JS compressed 4-5x (admin.html 506 KB → 123 KB)
- **All keys**: ANTHROPIC, GEMINI, OPENAI, ELEVENLABS, FAL — all active

## Driver Experience v2 (Jun 11 2026) — MAJOR REWRITE
**Backend** (`backend/routers/driver_config_router.py`):
- `GET/PUT /api/delivery/config` — per-merchant feature toggles + branding (42 features in 9 sections)
- `POST /api/delivery/config/reset` — restore defaults
- `GET/POST/PATCH/DELETE /api/delivery/config/branches[/{id}]` — full branches CRUD with map coords + capacity status
- `GET /api/delivery/config/public` — driver-facing config (no merchant secrets)
- Mongo collection: `driver_configs` (one doc per merchant)

**Frontend** — Driver app (`frontend/public/mockups/driver_app.html`):
- Sidebar with 9 sections: Map · Orders · Earnings · AI Coach · Achievements · Leaderboard · Profile · Settings · Support
- Live multi-branch Leaflet map with capacity colors (green=active, blue=available, amber=busy, gray=closed)
- Real-time Surge banner, heat alert toast, prayer pause overlay, driver pulse marker
- Earnings chart, instant pay, fuel calc, tip QR, weekly streak tracker
- AI Coach with rotating tips, voice command FAB, route memory
- 10 unlockable achievement badges, weekly leaderboard with gold/silver/bronze
- Floating SOS button, theme toggle, glance mode, PWA manifest
- All 42 features gated by merchant config flags

**Frontend** — Merchant config (`frontend/public/mockups/driver_manager.html`):
- 9 tabs: General · Earnings · Orders · AI · Saudi · Wellbeing · Gamification · Branches · Feature Order
- 42 toggles + numeric fields (streak amount/count, weekly challenge, surge multiplier, etc.)
- Branding picker (primary/accent colors, logo URL, app name)
- Branch map with click-to-add + capacity selector + delete
- Drag-and-drop section ordering
- SOS emergency contacts (up to 3 phones)
- Linked from admin.html → Delivery page → "إدارة تطبيق السائق" button

## Test Credentials
- Admin panel: `owner@zenrex.ai` / `owner123` (real JWT)
- Driver app: phone `0552222222` / OTP `1234`
- VPS SSH: `ssh -i /root/.ssh/zenrex_deploy root@91.98.154.148`


## 🚀 VPS Performance Fix — Jun 11 2026

**Issue**: Site reported as severely slow on Hetzner VPS deployment.

**Root Cause Identified**:
- Server resources were FINE (load 0.01, CPU 99% idle, 14GB RAM free, backend container 247MB, mongo 175MB).
- Bottleneck was 100% client-side: HTML mockups had **0 lazy-loaded images** while triggering 25+ visible `<img>` tags + 4 synchronous CDN scripts on every page load.
- Browser was fetching all images in parallel on first paint, choking the rendering pipeline.

**Fix Applied** (deployed to VPS):
1. Added `loading="lazy" decoding="async"` to **56 static `<img>` tags** across 6 mockup files.
2. Auto-applied to all dynamically-injected images (innerHTML templates) via browser default → now 254 images total are lazy.
3. Changed banner-video `preload="auto" autoplay` → `preload="none"` (no eager video download).
4. Added `defer` to 4 CDN scripts in `admin.html` (lucide, jspdf, html2canvas, qrcodejs) → non-blocking.

**Result** (measured from external network):
- `app_mode_full.html`: TTFB 235ms, total 567ms (110KB gzipped) — DOMContentLoaded in **0.07s** in browser.
- `admin.html`: TTFB 230ms, total 560ms — DOMContentLoaded in **0.06s**.
- No more 25+ parallel image fetches on initial render.


### 📦 Phase 2 — Inline JS Extraction (Jun 11 2026)

Extracted the single huge inline `<script>` block from each large mockup into an external `.js` file so the browser can cache it for 7 days (`Cache-Control: public, immutable, max-age=604800`).

**Files created**:
- `frontend/public/mockups/app_mode_full.js` — 263KB / 3842 lines (extracted from `app_mode_full.html`)
- `frontend/public/mockups/admin.js` — 273KB / 3441 lines (extracted from `admin.html`)

**HTML file size reduction (uncompressed)**:
- `app_mode_full.html`: 432KB → **161KB** (-63%)
- `admin.html`: 508KB → **235KB** (-54%)

**Cold-cache visit** (first time, both files downloaded in parallel + gzipped):
- HTML: 34KB gzipped in ~340ms
- JS: 76KB gzipped in ~450ms
- DOMContentLoaded: **0.05–0.09s** in headless Chromium.

**Warm-cache visit** (repeat visit):
- Only the HTML is fetched (~34KB gzipped). JS is loaded instantly from disk cache.
- Time to interactive: **~150ms** (essentially TTFB only).

**Verified**:
- All global JS functions (`getUser`, `translateReview`, etc.) still defined post-extraction.
- No JS console errors on either page.
- Visual layout identical (welcome modal, banner, categories, login form all rendering correctly).


## 🚀 Full React App Deployed to VPS — Jun 11 2026

**Discovery**: Until this point, the VPS at `91.98.154.148` was serving ONLY the static HTML mockups (admin, app_mode_full, driver_app). The actual standalone **React Zenrex platform** (FreeBuild, Smart Orchestrator, Ready Sites, AI Chat workspace, Image Studio, Video Studio, Auto-Coder) had never been deployed to VPS — it only lived on the Emergent preview URL.

**Fix Applied**:
1. Built React app with `REACT_APP_BACKEND_URL=http://91.98.154.148` so API calls go through VPS Nginx.
2. Stripped `.map` files (15MB savings).
3. rsynced `build/` (76MB) → `/opt/zenrex/frontend/build/` on VPS.
4. Rewrote Nginx config (`/etc/nginx/sites-available/zenrex`):
   - `root` switched from `frontend/public` → `frontend/build`
   - Added SPA fallback `try_files $uri $uri/ /index.html` for React Router
   - Kept `/api/` proxy → `127.0.0.1:8001`
   - Kept `/mockups/` location intact (admin.html, app_mode_full.html, driver_app.html still work)
   - Added 1-year `Cache-Control: public, immutable` for hashed CRA bundles in `/static/`
5. `nginx -t && systemctl reload nginx` → all green.

**Verified**:
- `http://91.98.154.148/` → React Zenrex homepage loads (DOMContentLoaded 0.09s), title "Zenrex | منصة الإبداع بالذكاء الاصطناعي", no JS errors.
- `http://91.98.154.148/api/store/health` → 200 in 234ms, payload `{"ok":true,"products":1,"customers":1,"reviews":0}`.
- `http://91.98.154.148/mockups/admin.html` → still 200 (mockups preserved).
- Main JS bundle (`main.2ea727e7.js`): cached 1 year + gzip + immutable.


## 🔑 Critical Env Fix — USE_DIRECT_LLM Activated on VPS (Jun 11 2026 04:44)

**Issue**: Although the .env file had `USE_DIRECT_LLM=1`, the running container was started before the value was injected — so the shim was NEVER active. All AI calls would silently fall back to the dead `EMERGENT_LLM_KEY` (restricted from VPS).

**Fix**:
1. Confirmed `USE_DIRECT_LLM=1` in `/opt/zenrex/backend/.env`.
2. Pinned it permanently in `docker-compose.yml` `environment:` block (survives `.env` rewrites).
3. `docker compose up -d --force-recreate backend` (90s rebuild with pip install).

**Verified live on VPS**:
- `POST /api/auth/login owner@zenrex.ai / owner123` → 200 + JWT (191 chars)
- `POST /api/ai/chat` → `{"content":"أهلاً","agent":"freebuild","model_used":"claude-opus-4-5","cost_estimate_usd":0.025065}`
- `POST /api/store/reviews/translate` → `{"ok":true,"translated":"هذا المنتج رائع"}` (Gemini direct)
- **VPS is now 100% independent from Emergent platform.** No Emergent network calls in any AI path.

### Login Credentials (user confusion noted)
The previous email `owner@zitex.com` (pre-rebrand) returns 401 — the correct email post-rebrand is `owner@zenrex.ai` / `owner123`.


## 🎨 Full Rebrand: Zerax → Zenrex (Jun 11 2026)

User purchased `zenrex.ai` from Porkbun (registered until Jun 11 2028) and asked for a global rebrand.

**Scope of rename**:
- **236 source files** updated via `rebrand.py` script (Pass 1: email/domain refs + whole-word "Zerax").
- **87 additional files** updated via `rebrand2.py` (Pass 2: compound identifiers — `ZeraxClient` → `ZenrexClient`, `ZERAX_CREDITS` → `ZENREX_CREDITS`, etc.).
- **10 source files renamed**: `ZeraxDuo.js` → `ZenrexDuo.js`, `ZeraxShowcase.js` → `ZenrexShowcase.js`, `zerax-logo.png` → `zenrex-logo.png`, 4 test files, etc.
- **2 directories renamed**: `backend/modules/zerax_ai` → `zenrex_ai`, `backend/static/zerax_logos` → `zenrex_logos`.
- **CSS theme** renamed: `zerax-theme.css` → `zenrex-theme.css`.
- **Nginx config** renamed: `nginx-zerax.conf` → `nginx-zenrex.conf`.
- **Database**: `users.email` migration — `owner@zerax.com` → `owner@zenrex.ai` (Mongo `updateMany` with `$replaceAll`).
- **All `@zerax.com` / `zerax.app` / `zerax.com` / etc. references** → `@zenrex.ai` / `zenrex.ai`.
- **Old `.zip` backups** removed (zerax-railway.zip, zerax-source-code.zip, zerax-independent.zip).

**React rebuild**: `REACT_APP_BACKEND_URL=https://zenrex.ai yarn build` — 32s, no errors.

**VPS deployment**:
- rsync'd new build + backend code to Hetzner.
- Updated Nginx config with `server_name zenrex.ai www.zenrex.ai _`.
- Restarted backend container — health check 200 OK.
- Verified frontend: page title `"Zenrex | منصة الإبداع بالذكاء الاصطناعي"`, all UI rebranded, no JS errors.

**Login verified**:
- ✅ `owner@zenrex.ai` / `owner123` → 200 OK + JWT (191 chars)
- ❌ `owner@zerax.com` → 401 Invalid credentials (as expected)

**New tooling**:
- Created `/app/deploy/deploy.sh` — one-command deploy script for future updates (`bash deploy.sh zenrex.ai`).

**Pending (user action required)**:
- ~~Add DNS A records in Porkbun~~ ✅ DONE (Jun 11 2026 12:35).
- ~~Provision Let's Encrypt SSL~~ ✅ DONE — `https://zenrex.ai` live with auto-renewal.

## 🔒 SSL/HTTPS Live (Jun 11 2026 12:50)

- **Certbot installed** on VPS and configured for Nginx.
- **Let's Encrypt certificate** issued for `zenrex.ai` + `www.zenrex.ai`, expires Sep 9 2026.
- **Auto-renewal** scheduled by certbot systemd timer (no manual work needed).
- **HTTP → HTTPS redirect** active (301 redirect on port 80).
- **Backend CORS** updated to allow `https://zenrex.ai` + `https://www.zenrex.ai`.
- **React rebuild** with final `REACT_APP_BACKEND_URL=https://zenrex.ai` deployed.

**Final verification**:
- `https://zenrex.ai` → 200 OK, title "Zenrex | منصة الإبداع بالذكاء الاصطناعي", green lock, no JS errors.
- `https://zenrex.ai/api/store/health` → 200 OK with `{"ok":true,...}`.
- Login: `owner@zenrex.ai` / `owner123` → JWT issued.

## 📧 Owner Email Forwarding (Porkbun → Gmail)
- All `@zenrex.ai` mail forwards to **`zenrex.ai@gmail.com`** via Porkbun Email Forwarding.

## 🎨 Color System Overhaul (Jun 11 2026)
**Bug fix + major enhancement to Product Studio color picker.**

### Root cause of "hex → white image" bug
Previous code sent raw hex like `#000000` inside the Gemini prompt: `"isolated product shot on a #000000 background"`. Gemini AI cannot reliably parse hex codes in natural-language prompts → defaults to white.

### Fix + Enhancements
1. **Hex → English color name resolver** (`psHexToName()`): every hex is converted to a Gemini-friendly natural name (e.g., `#000000` → `"pure black"`, `#7c3aed` → `"vibrant purple"`). Falls back to brightness/RGB analysis for unknown hex (e.g., `"warm reddish tone"`).
2. **6 categorized color palettes** (~50 named colors):
   - ⚪ أساسي (basics: 6 colors)
   - 🔥 دافي (warm: 8 colors)
   - ❄️ بارد (cool: 8 colors)
   - 🌸 باستيل (pastels: 8 colors)
   - ⚡ نيون (vibrant: 8 colors)
   - 💎 فاخر (luxury: 8 colors)
3. **Custom Color Tool**: merchant adds their own brand colors via "+ أضف لون" modal (Arabic name + English name + hex). Hover preset to show name in tooltip; click ✕ to delete.
4. **Persistence**: custom palette saved to `localStorage.zx_custom_colors` AND synced to MongoDB via `PUT /api/theme/merchant/me` with `custom_palette: [{ar,en,hex},...]` field on `merchant_themes` doc.
5. **Cross-device sync**: `psHydrateCustomColorsFromServer()` pulls latest palette on every studio open.
6. **Customer-store integration**: storefront fetches merchant theme via `/api/theme/by-merchant/{merchant_id}` — custom_palette is now part of the public theme response.

### Files touched
- `frontend/public/mockups/admin.js` — color palette logic, hex→name resolver, custom color modal
- `frontend/public/mockups/admin.html` — CSS for categorized presets, custom color modal styling
- `backend/routers/theme_router.py` — added `custom_palette: Optional[list]` to `ThemeIn` model + save logic


## MongoDB Atlas Migration (Jun 11 2026) ⭐
- **Status**: ✅ COMPLETE & VERIFIED IN PRODUCTION
- **Cluster**: `cluster0.1tkzj4x.mongodb.net` (M2 Shared, Free tier eligible)
- **User**: `zenrex_admin`
- **DB**: `zerax_prod` (kept legacy name for backward-compat with code)
- **Migrated**: 146 documents across 24 collections (users, orders, products, pricing_plans, etc.)
- **IP Access**: `0.0.0.0/0` (allow all — can be tightened to `91.98.154.148/32` later)
- **Connection** via `docker-compose.yml` env: `MONGO_URL=mongodb+srv://zenrex_admin:***@cluster0.1tkzj4x.mongodb.net/...`
- **Verified**: Write test passed (created order from production frontend → confirmed in Atlas)
- **Fallback**: Local `zerax-mongo-1` container still running with snapshot in `/tmp/mongo_backup` and persistent volume `/opt/zerax/data/mongo` — can revert by editing docker-compose.
- **Compose backup**: `/opt/zerax/docker-compose.yml.bak.<timestamp>` (pre-migration version)








