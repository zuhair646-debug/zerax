# Zenrex Farm — PRD (Updated 2026-06-20)

## Problem Statement
Arabic-first AI builder for websites/apps/images/videos with credits-based pricing, Stripe payments, background-task persistence, and exportable codebase. Deployed on Hetzner VPS (zenrex.ai).

## Current Status — Healthy, Production Live ✅
- Domain: https://zenrex.ai
- Backend: Docker compose, MongoDB local
- Frontend: React PWA, Service Worker v9
- Stripe: Official `stripe` SDK with proxy support (no more emergentintegrations.payments dependency)

## Pricing (USD)
| Package | Price | Credits | Type |
|---|---|---|---|
| Free signup | $0 | 200 | one-time bonus |
| **Ready Sites Trial** | **$9** | **500** | one-off (7 days) |
| **Ready Sites Purchase** | **$79** | **5,000** | one-off (full ownership) |
| Project Pack | $49 | 5,000 | one-off |
| Starter | $19/mo | 2,000 | subscription |
| Pro | $69/mo | 8,000 | subscription |
| Studio | $199/mo | 25,000 | subscription |

**Service costs (`SERVICE_COSTS`):** Image 100 / Video 10s 1,200 / Text 1k tokens 30 / Chat msg 10

## Architecture
### Triple-Layer Credit Guard
1. **Per-endpoint:** `pricing.credits.charge_user(service_key)` atomic deduction + ledger
2. **Backend Middleware:** `credits_guard.py` returns 402 on AI endpoints if `users.credits == 0`
3. **Frontend Global Toast:** `<GlobalCreditsGuard />` calm bottom-right pill on all AI/chat routes

### Stripe Integration (Independent)
- New shim: `/app/backend/modules/billing/stripe_shim.py` uses official `stripe==14.4.0` SDK
- Removed dependency on `emergentintegrations.payments.stripe`
- Auto-routes through Emergent's Stripe proxy if key starts with `sk_test_emergent`
- Works with real Stripe keys (sk_test_xxx or sk_live_xxx) for full independence

### Ready Sites Pay-First Flow (NEW)
1. User picks category → `/ready-sites/preview/{id}`
2. Clicks "Continue" → `/ready-sites/purchase?category=X`
3. Chooses Trial ($9) or Purchase ($79)
4. **Redirected to Stripe Checkout** (USD)
5. After payment → success URL `/billing/success?session_id=…`
6. Billing webhook AUTO-CREATES the FreeBuild project with category context
7. BillingSuccess page polls status, gets `project_id` field, redirects to `/freebuild/chat/{id}?source=ready-sites`
8. User lands in chat with AI greeting asking for store name + logo

## Recent Completed Work (2026-06-20 session)
- Hero Z logo removed | `/pricing` loads PricingV2 | Stripe import made lazy
- **Credits pivot:** PACKAGES simplified, deduction unified, `/generate/video` fixed
- **3-layer guard:** middleware + per-endpoint charge + global toast
- **Calm UI banners:** smaller pill-style, single tap to /pricing
- **Ready Sites paywall:** Trial/Purchase now redirect to Stripe (USD) — no free trial without payment
- **Stripe shim:** independent from emergentintegrations, supports both proxy and real Stripe keys
- **End-to-end verified:** signup→200 credits, Ready Sites checkout returns real Stripe URL on prod

## Pending — P1
- 🍋 **LemonSqueezy variant IDs** — user needs to create 2 products in LemonSqueezy dashboard:
  1. "Ready Sites Trial" — $9 USD (one-time)
  2. "Ready Sites Purchase" — $79 USD (one-time)
  Then set `LEMONSQUEEZY_VARIANT_TRIAL` + `LEMONSQUEEZY_VARIANT_PURCHASE` in prod `.env`
- 🍋 **LemonSqueezy webhook endpoint** must be registered in their dashboard:
  `https://zenrex.ai/api/ready-sites/lemonsqueezy/webhook` (events: order_created)
- 🪙 Top-up credits packs (1,000 credits for $9 etc.)
- 💸 Refund credits if external API (OpenAI/Sora) fails after deduction
- 🟢 File upload UI red→green indicator in FreeBuildChat
- 📧 Email Verification on Registration (Resend)
- 🔄 Chat Session Reconnection (SSE re-attach)
- 📱 Wire `CreditsBlockedBanner` inline in other chat pages

## Pending — P2
- Sticky in-page section navigator
- Multi-page generated sites (`/about`, `/contact`)
- Visual Guardian (Vision LLM)
- CI/CD pipeline
- Backfill existing free users to 200 credits

## Refactoring Backlog
- Split FreeBuildChat.js (4500+ lines)
- Split FreeBuild backend chat module
- Consolidate POINTS_CONFIG (server.py)

## Test Credentials
- Admin: admin@zenrex.ai / Zenrex@2026 (PROD DB only)
- Prod Test User: test_zenrex_2026@example.com / Test@Pass2026!

## Deployment
`bash /app/deploy/deploy.sh zenrex.ai` — backend recreate ~3 min for pip install.

## Verified End-to-End (curl on production zenrex.ai)
- ✅ Fresh signup → 200 credits hadyya
- ✅ /api/billing/packages → 6 packages (Trial + Purchase + Project + Starter + Pro + Studio)
- ✅ Ready Sites Trial checkout → real Stripe URL `cs_test_…`
- ✅ Ready Sites Purchase checkout → real Stripe URL
- ✅ Credits=0 → 402 across all AI endpoints
- ✅ Owner/admin/super_admin bypass works
- ✅ Auth endpoints unaffected
