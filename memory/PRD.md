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

### 🟡 MOCKED (functional UI, no live backend)
- admin.html login uses localStorage (no JWT)
- Products + orders use seed data (no MongoDB sync between admin/customer)
- Social OAuth not implemented (toggles save to localStorage)
- Service activations are localStorage flags only
- Auto-dispatch endpoint /api/delivery/auto-assign falls back to simulation

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
Gemini Nano Banana (Emergent LLM Key) · OpenAI TTS · ffmpeg · Web Speech API

## Test Credentials
- Admin panel: `merchant@zerax.com` / `zerax2026` (localStorage only)
- Driver app: phone `0552222222` / OTP `1234`
