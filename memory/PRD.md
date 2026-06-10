# Zerax — Multi-tenant AI Commerce Platform (PRD)

## Original Problem Statement
Build "Zerax", a multi-tenant AI platform that includes:
1. Conversational FreeBuild chat interface for building sites/apps from scratch
2. Smart Orchestrator unifying AI models (Anthropic Claude)
3. Ready Sites module (template-first)
4. Integrated Video Studio for AI-generated promo videos
5. Driver App + Delivery management (Haversine + dynamic pricing)
6. Global & local payment gateway catalog (Tabby, Tamara, Klarna, Alipay, Stripe…)
7. Standalone professional Admin Dashboard `admin.html` with real-time KPIs and 4-stage AI chat workspace

## Current Implementation Status (Feb 2026)

### ✅ Completed
- `admin.html` (Merchant Control Panel) — RTL Arabic, sidebar nav, KPIs, top products, recent orders, orders/customers/delivery/payroll/gateways/settings pages
- **Video Studio AI** — Full studio inside admin panel:
  - Language picker (Saudi/Egyptian/MSA/English/French/Hindi)
  - Voice picker with preview (5 Zerax voices via OpenAI TTS)
  - Tone & duration selectors with cost estimator
  - 5-stage workspace: Script text · Event scenario · AI images · Audio · Final video
  - Real Gemini Nano Banana image generation per scene
  - ffmpeg video assembly with TTS narration
  - Publish-to-social flow
- **Social Media Connections** — 8 platforms (Instagram, TikTok, X, Snapchat, YouTube, FB, WhatsApp Business, Telegram) with connect/disconnect + recent posts table
- **Interactive Dashboard Chart** — SVG line chart with hover tooltips showing day-specific income + delta % comparison
- **Clickable everything** — KPIs jump to relevant pages, top products open product editor, notifications dropdown, user menu dropdown, global search filters products
- Backend routers: `image_studio_router.py`, `video_studio_router.py`, `delivery_router.py`, `payment_gateways_router.py`, `payroll_router.py`
- Driver PWA + Delivery tracking (`driver_app.html`, `track.html`)
- Global payment gateways catalog with per-country filtering

### 🟡 Mocked / Static (functional UI but no live DB)
- `admin.html` login is local-only (`merchant@zerax.com / zerax2026`); no JWT enforcement
- Products list and recent orders use `MOCK_PRODUCTS` / seeded data
- Social media accounts are localStorage-only (no real OAuth)

### 🔴 Pending (Priority Order)

**P1**
- JWT login + MongoDB persistence for admin.html (replace localStorage)
- Hook product CRUD to real `/api/products` endpoints
- Replace seeded recent orders with `/api/orders?limit=5`

**P2**
- Tabby & Tamara live payment execution APIs
- ZATCA Phase-2 e-invoicing (XML + PDF/A-3 + QR)
- Real OAuth for social media accounts (Meta/Google/X APIs)

**P3**
- Unify AI agents via `claude_core.py` orchestrator
- Voice agent / Call-center AI via LiveKit + ElevenLabs

## Code Architecture
- `/app/backend/routers/` — FastAPI routers prefixed with `/api`
- `/app/backend/modules/payments/` — gateway catalogs and enrichment
- `/app/frontend/public/mockups/` — vanilla HTML SPAs (`admin.html`, `app_mode_full.html`, `driver_app.html`, `track.html`, `index.html`)
- `/app/frontend/src/` — React main shell (FreeBuild, Ready Sites, App Studio…)

## Key API Endpoints
- `POST /api/image-studio/generate` — Gemini Nano Banana image gen
- `POST /api/promo-video/storyboard` — Storyboard scene generation
- `POST /api/promo-video/generate` — TTS + ffmpeg video assembly
- `GET /api/payments/by-country?country=SA` — Gateway catalog
- `GET /api/delivery/stats|orders|drivers` — Delivery dashboard
- `POST /api/payroll/run` — Process driver payouts

## Tech Stack
FastAPI + MongoDB · Vanilla HTML/JS (mockups) + React (main app) · Gemini Nano Banana (Emergent LLM Key) · OpenAI TTS · ffmpeg · Chart via SVG

## Test Credentials
- Admin panel: `merchant@zerax.com` / `zerax2026` (local-only)
- Driver app: phone `0552222222` / OTP `1234`
