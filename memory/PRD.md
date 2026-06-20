# Zenrex Farm — PRD (Updated 2026-06-20)

## Problem Statement
Arabic-first AI builder for websites/apps/images/videos with credits-based pricing, Stripe payments, background-task persistence, and exportable codebase. Deployed on Hetzner VPS (zenrex.ai).

## Current Status — Healthy, Production Live
- Domain: https://zenrex.ai
- Backend: Docker compose on VPS, MongoDB local
- Frontend: React PWA, Service Worker v8 (network-first, cache-busting)
- LLM: Claude Sonnet 4.5 via Emergent LLM key

## Pricing — CREDITS-BASED with TRIPLE-LAYER GUARD
| Tier | Price | Credits |
|---|---|---|
| Free signup | $0 | 200 (bonus, one-time) |
| Project Pack | $49 | 5,000 (one-time) |
| Starter | $19/mo | 2,000 |
| Pro | $69/mo | 8,000 (most popular) |
| Studio | $199/mo | 25,000 |

**Service costs (`modules/pricing/catalog.py` `SERVICE_COSTS`):**
- Image: 100 credits | Video 10s: 1,200 | AI text 1k tokens: 30 | Chat msg: 10

## Three-Layer Credit Guard Architecture
1. **Per-endpoint deduction** — `pricing.credits.charge_user(service_key)` atomically decrements `users.credits` and logs to `credit_transactions`.
2. **Backend Middleware** — `/app/backend/middleware/credits_guard.py` intercepts ALL POST/PUT/PATCH requests to AI endpoints (regex-matched) and returns HTTP 402 with friendly Arabic message when `credits == 0`. Bypass: owner/admin/super_admin.
3. **Frontend Global Toast** — `<GlobalCreditsGuard />` mounted in `App.js`. Calm fixed-bottom-right pill on AI/chat routes when blocked. Single tap → `/pricing`. Dismissable for 10 min. Routes covered: freebuild, build, chat, ai, companion, avatar, studio, app-builder, mobile-app, video-studio, image-studio, image-generator, games, web-games, operator, new-request, agent.
4. **In-chat Banner** — `<CreditsBlockedBanner />` (calm pill-style) replaces input row in FreeBuildChat when blocked. Compact single-tap surface.

## Recent Completed Work (2026-06-20 session)
- Removed redundant centered Z logo from landing hero
- Fixed `/pricing` to load PricingV2 directly
- Made `emergentintegrations.payments.stripe` import lazy
- **CREDITS PIVOT** — Packages simplified, PricingV2 rewritten, deduction unified
- `/generate/video` now deducts credits (was bug)
- StorageIndicator → small popover (not modal)
- `super_admin` added to owner-bypass
- **GLOBAL CREDITS GUARD MIDDLEWARE** — all AI endpoints protected
- **Calm Banner** — small, single-tap, no overwhelming visuals
- **GlobalCreditsGuard component** — one toast covers all chat/AI pages

## Verified End-to-End (testing agent iteration_48 + curl):
- ✅ Signup → 200 credits
- ✅ Chat 1k tokens deducts 30 (500→470)
- ✅ Image deducts 100 (500→400)
- ✅ Video 10s deducts 1,200 (2000→800)
- ✅ Credits=0 → 402 on `/api/ai-core/chat`, `/api/generate/image` (both prod + preview)
- ✅ Owner/admin/super_admin bypass
- ✅ Auth endpoints unaffected
- ✅ Transactions logged to `credit_transactions`

## Pending — P1
- 🪙 Top-up credits packs (1,000 credits for $9, etc.)
- 🟢 File Upload UI red→green indicator
- 📧 Email Verification on Registration (Resend)
- 🔄 Chat Session Reconnection (SSE re-attach)
- 💸 Credit refund on external API failure (image/video)
- 🔒 Replace `emergentintegrations.payments.stripe` with official `stripe`

## Pending — P2
- Sticky in-page section navigator (waiting on screenshot from user)
- Multi-page generated sites
- Visual Guardian
- CI/CD pipeline
- Backfill existing free users to 200 credits

## Tech Stack
React, FastAPI, MongoDB, Stripe, Resend, Emergent LLM (Claude Sonnet 4.5), PWA Service Worker, SSE.

## Test Credentials
- Admin: admin@zenrex.ai / Zenrex@2026 (PROD DB only)
- Prod Test User: test_zenrex_2026@example.com / Test@Pass2026!

## Deployment
`bash /app/deploy/deploy.sh zenrex.ai` — builds React, rsyncs to VPS, reloads nginx, recreates backend. Backend recreate ~3 min for pip install.
