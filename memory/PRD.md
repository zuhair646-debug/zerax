# Zerax — Multi-tenant AI Commerce Platform (PRD)

## Original Problem Statement
Build "Zerax" — a multi-tenant Saudi/Arab AI commerce platform with:
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
- **Video Studio** (5 tabs, fullscreen, dark Zerax theme):
  1. Script (Gemini storyboard with 44 dialects + 12 voices)
  2. Scenes (editable storyboard, approve per scene)
  3. Images (Gemini Nano Banana, approve per image, 8pts each)
  4. Voice (Zerax TTS, preview before approve, 5pts)
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
- Test creds: `owner@zerax.com` / `owner123` (admin), any phone + OTP `1234` (customer)

### 🟡 MOCKED (functional UI, no live backend)
- admin.html login uses localStorage (no JWT)
- Products + orders use seed data (no MongoDB sync between admin/customer)
- Social OAuth not implemented (toggles save to localStorage)
- Service activations are localStorage flags only
- Auto-dispatch endpoint /api/delivery/auto-assign falls back to simulation

### 🟢 LATEST (Feb 10, 2026 · Dark Theme + Sandbox Wave — LAUNCH-READY)
- **🌙 Zerax Unified Dark Theme** (`/mockups/zerax-theme.css`):
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
  - 6 Shipping Providers (Aramex/SMSA/Naqel/DHL/J&T/Zerax Fleet)
  - Beautiful PSP-branded checkout pages (Tabby green, Tamara purple, etc.)
  - Smoke-tested end-to-end: Tabby payment → Aramex label → 5-event delivery timeline

### 🔴 PENDING (Priority Order)

**P1 — CRITICAL NEXT**
- Zerax Landing Page (marketing site) — promised next
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
- **DB**: MongoDB `zerax_prod` inside `zerax-mongo-1`
- **Backend**: Uvicorn inside `zerax-backend-1` (auto-pip-install on start)
- **JWT_SECRET**: Fixed via `.env` (no token loss on restart)
- **AI**: Fully working via direct provider keys (Claude/Gemini/OpenAI)
- **Image serving**: `/static/uploads/` → `/opt/zerax/data/uploads/` (persistent volume)
- **Gzip**: HTML/CSS/JS compressed 4-5x (admin.html 506 KB → 123 KB)

## Test Credentials
- Admin panel: `owner@zerax.com` / `owner123` (real JWT)
- Driver app: phone `0552222222` / OTP `1234`
- VPS SSH: `ssh -i /root/.ssh/zerax_deploy root@91.98.154.148`

