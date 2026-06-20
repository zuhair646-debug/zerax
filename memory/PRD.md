# Zenrex Farm — PRD (Updated 2026-06-20)

## Problem Statement
Arabic-first AI builder for websites/apps/images/videos with credits-based pricing, Stripe payments, background-task persistence, and exportable codebase. Deployed on Hetzner VPS (zenrex.ai).

## Current Status — Healthy, Production Live
- Domain: https://zenrex.ai
- Backend: Docker compose on VPS, MongoDB local
- Frontend: React PWA, Service Worker v7 (network-first, cache-busting)
- LLM: Claude Sonnet 4.5 via Emergent LLM key

## Pricing — CREDITS-BASED with GLOBAL GUARD (verified end-to-end ✅)
| Tier | Price | Credits |
|---|---|---|
| Free signup | $0 | 200 (bonus, one-time) |
| Project Pack | $49 | 5,000 (one-time) |
| Starter | $19/mo | 2,000 (refills monthly) |
| Pro | $69/mo | 8,000 (most popular) |
| Studio | $199/mo | 25,000 |

**Service costs (catalog `modules/pricing/catalog.py` `SERVICE_COSTS`):**
- Image (GPT/Nano Banana): 100 credits
- Video (Sora 10s): 1,200 credits
- AI text (1k tokens): 30 credits
- Chat message: 10 credits

## Credits Architecture
1. **Per-endpoint deduction** — `pricing.credits.charge_user(service_key)` atomically decrements `users.credits` and logs to `credit_transactions`.
2. **Global Guard Middleware** — `/app/backend/middleware/credits_guard.py` intercepts ALL POST requests matching AI endpoints (chat/generate/agent-chat/etc.) and returns HTTP 402 with friendly Arabic message if `users.credits == 0`. Owners/admins/super_admins bypass.
3. **Frontend hook** — `useCreditsGuard()` polls `/api/usage/credits` every 25s. Returns `{credits, isBlocked, unlimited}`.
4. **UI block** — When `isBlocked=true`, the chat input in `FreeBuildChat.js` is **replaced** by `<CreditsBlockedBanner />` (3 quick recharge cards + main CTA). Send function short-circuits with redirect to `/pricing`. On 402 response, hook re-polls instantly.
5. **Navbar badge** — Always-visible credit pill, turns red+pulse if balance < 50.

**Endpoints covered by Credits Guard (regex):**
freebuild chat (project/{id}/{chat,agent-chat,agent-chat-stream}), freebuild-v2, ai-core/chat, ai/chat, companion (chat, voice-chat), avatar/chat, merchant/avatar/{slug}/chat, autocoder, mobile-app-builder, video-studio (chat, producer-chat), app-studio/producer-chat, agent/chat, games/project/{id}/chat, generate/{image,video}

## Recent Completed Work (2026-06-20 session)
- Removed redundant centered Z logo from landing hero
- Fixed `/pricing` to load PricingV2 directly
- Made `emergentintegrations.payments.stripe` import lazy
- **CREDITS-BASED PRICING PIVOT**
  - PACKAGES simplified — only credits, no fake features
  - PricingV2.jsx rewritten: simple cards (price + credits + button)
  - usage_meter.py unified with `pricing.credits.charge_user()` 
  - `/generate/video` now deducts credits (was bug)
  - CreditsBadge in Navbar (polls 20s, red+pulse if < 50)
  - StorageIndicator: small popover instead of full-screen modal
  - usage_events now stores `credits_used` for month aggregation
  - super_admin added to owner-bypass tuple
- **GLOBAL CREDITS GUARD MIDDLEWARE (NEW)**
  - Created `/app/backend/middleware/credits_guard.py`
  - Intercepts all AI endpoints, returns 402 if credits=0
  - Verified working: fresh user (200 credits) → chat succeeds; same user with credits=0 → 402 across both `/api/ai-core/chat` and `/api/generate/image`
- **FRONTEND BLOCK UI**
  - Created `useCreditsGuard` hook + `CreditsBlockedBanner` component
  - Wired into FreeBuildChat: input row entirely replaced by banner when blocked
  - Send function short-circuits to `/pricing` if blocked, also handles 402 responses instantly

## Pending — P1
- 🪙 **Top-up credits packs** (one-time small purchases like 1,000 credits for $9)
- 🟢 **File Upload UI red→green** indicator in FreeBuildChat.js
- 📧 **Email Verification on Registration** — Resend API
- 🔄 **Chat Session Reconnection** — re-attach to SSE stream after reload
- 💸 **Credit refund on external API failure** for /generate/image and /generate/video
- 🔒 **Replace `emergentintegrations.payments.stripe`** with official `stripe` SDK
- 📱 Apply `CreditsBlockedBanner` to other chat pages (Companion, AppStudio, AvatarChat, etc.) — middleware blocks at the backend but UX is best when each page shows the banner inline

## Pending — P2
- Sticky in-page section navigator for landing page (waiting on user screenshot)
- Multi-page generated sites (`/about`, `/contact`) for SEO
- Visual Guardian (Vision LLM)
- CI/CD pipeline (GitHub Actions → VPS)
- Backfill existing free users to 200 credits (legacy were 20)

## Refactoring Backlog
- Split FreeBuildChat.js (4500+ lines) into smaller components
- Split FreeBuild chat backend (3300+ lines) into routers/services
- Consolidate POINTS_CONFIG and PRICING_CONFIG (server.py)

## Tech Stack
React, FastAPI, MongoDB, Stripe, Resend, Emergent LLM (Claude Sonnet 4.5), PWA Service Worker, SSE.

## Test Credentials
- Admin: admin@zenrex.ai / Zenrex@2026 (only on PROD DB, not preview)
- Prod Test User: test_zenrex_2026@example.com / Test@Pass2026!

## Deployment
`bash /app/deploy/deploy.sh zenrex.ai` — builds React, rsyncs to VPS, reloads nginx, recreates backend container.
Backend recreate takes ~3 min (pip install) → health check 502s briefly.
