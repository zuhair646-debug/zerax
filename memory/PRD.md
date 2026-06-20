# Zenrex Farm — PRD (Updated 2026-06-20)

## Problem Statement
Arabic-first AI builder for websites/apps/images/videos with credits-based pricing, Stripe payments, background-task persistence, and exportable codebase. Deployed on Hetzner VPS (zenrex.ai).

## Current Status — Healthy, Production Live
- Domain: https://zenrex.ai
- Backend: Docker compose on VPS, MongoDB local
- Frontend: React PWA, Service Worker v6 (network-first, cache-busting)
- LLM: Claude Sonnet 4.5 via Emergent LLM key

## Pricing — CREDITS-BASED (verified end-to-end ✅)
| Tier | Price | Credits |
|---|---|---|
| Free signup | $0 | 200 (bonus, one-time) |
| Project Pack | $49 | 5,000 (one-time) |
| Starter | $19/mo | 2,000 (refills monthly) |
| Pro | $69/mo | 8,000 (most popular) |
| Studio | $199/mo | 25,000 |

**Service costs (catalog: `modules/pricing/catalog.py` `SERVICE_COSTS`):**
- Image (GPT/Nano Banana): 100 credits
- Video (Sora 10s): 1,200 credits
- AI text (1k tokens): 30 credits
- Chat message: 10 credits

**Pricing chain — verified 14/14 by testing agent (iteration_48):**
- ✅ /api/billing/packages returns correct credit amounts
- ✅ Signup → 200 credit bonus
- ✅ Image gen: 500→400 (deducted 100)
- ✅ Video gen: 2000→800 (deducted 1200)
- ✅ Chat 1k tokens: 500→470 (deducted 30)
- ✅ Insufficient credits → 402 Payment Required
- ✅ Zero credits → check_quota blocks with friendly upgrade prompt
- ✅ Owner/admin/super_admin bypass works
- ✅ All deductions logged in `credit_transactions` collection

## Recent Completed Work (2026-06-20 session)
- Removed redundant centered Z logo from landing hero
- Fixed `/pricing` to load PricingV2 directly
- Made `emergentintegrations.payments.stripe` import lazy (billing module no longer fails to load when SDK unavailable)
- **CREDITS-BASED PRICING PIVOT**
  - PACKAGES dict simplified — only credits, no fake "12 projects", "WhatsApp support", etc.
  - PricingV2.jsx rewritten: simple cards (price + credits + button only)
  - usage_meter.py unified with `pricing.credits.charge_user()` — single source of truth (SERVICE_COSTS)
  - `/generate/video` now deducts credits for paid users (was bug — only blocked free users before)
  - `/generate/image` already deducts; both also log charge_method to activity feed
  - CreditsBadge in Navbar (top-right) — polls every 20s, red+pulse if balance < 50
  - StorageIndicator refactored: small popover instead of full-screen modal
  - usage_events now includes `credits_used` field for accurate month_credits aggregation
  - super_admin role added to owner-bypass tuple in `credits.charge_user`
  - Fixed KeyError risk: PACKAGES["studio_monthly"] → "tier_studio_monthly"

## Pending — P1
- 🪙 **Top-up credits packs** (one-time small purchases like 1,000 credits for $9)
- 🟢 **File Upload UI red→green** indicator in FreeBuildChat.js
- 📧 **Email Verification on Registration** — Resend API
- 🔄 **Chat Session Reconnection** — re-attach to SSE stream after reload
- 💸 **Credit refund on external API failure** for /generate/image and /generate/video
- 🔒 **Replace `emergentintegrations.payments.stripe`** with official `stripe` SDK

## Pending — P2
- Wire credit deduction into `/api/ai-core/chat` (smart_chat) — currently bypasses credits system
- Sticky in-page section navigator for landing page (waiting on user clarification)
- Multi-page generated sites (`/about`, `/contact`) for SEO
- Visual Guardian (Vision LLM)
- CI/CD pipeline (GitHub Actions → VPS)
- Backfill existing free users to 200 credits (legacy were 20)

## Refactoring Backlog
- Split FreeBuildChat.js (4500+ lines) into smaller components
- Split FreeBuild chat backend (3300+ lines) into routers/services
- Consolidate POINTS_CONFIG (server.py L299) and PRICING_CONFIG (L1694) — risk of drift

## Tech Stack
React, FastAPI, MongoDB, Stripe, Resend, Emergent LLM (Claude Sonnet 4.5), PWA Service Worker, SSE.

## Test Credentials
- Admin: admin@zenrex.ai / Zenrex@2026
- Prod Test User: test_zenrex_2026@example.com / Test@Pass2026!

## Deployment
`bash /app/deploy/deploy.sh zenrex.ai` — builds React, rsyncs to VPS, reloads nginx, recreates backend container.
Backend recreate triggers fresh pip install (~3 min) → health check 502 briefly, settles ~3 min after.
