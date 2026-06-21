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

## Recent Completed Work (2026-06-20 → 2026-06-21 session)
- Hero Z logo removed | `/pricing` loads PricingV2 | Stripe import made lazy
- **Credits pivot:** PACKAGES simplified, deduction unified, `/generate/video` fixed
- **3-layer guard:** middleware + per-endpoint charge + global toast
- **Calm UI banners:** smaller pill-style, single tap to /pricing
- **Ready Sites paywall:** PayPal + LemonSqueezy (Stripe fully removed)
- **End-to-end verified:** signup→200 credits, Ready Sites checkout returns real PayPal URL on prod
- **FreeBuild streaming agent now deducts credits per turn** — fixed root cause of "credits not deducting"
- **Removed all role-based credit bypasses** — owner/admin/super_admin no longer skip credit deduction
- **🆕 8 LemonSqueezy variants live + connected on VPS** (1817088 → 1817151)
- **🆕 Custom amount: tiered bonus** — $5–$10K range with progressive gifts up to +500K @ $10K
- **🆕 Pricing UI: strikethrough base + green new total + bonus pill** for cross-cultural clarity
- **🆕 Float credits killed** — backend rounds to int + DB normalized + UI displays integers only
- **🆕 Dashboard/Navbar jitter fixed** — single source `useCreditsGuard`, removed promo top-transition, removed duplicate `/auth/me` fetch
- **🆕 2026-06-21 — UNIVERSAL 50-credit gate enforced across ALL AI chat surfaces (NO role bypass, even owners pay):**
  - `/api/freebuild-chat/project/{pid}/agent-chat-stream` → 402 if balance < 50 (admin bypass removed)
  - `/api/freebuild-chat/project/{pid}/chat` (non-streaming) → 402 if balance < 50 (gate added)
  - `/api/video-studio/chat` → 402 if balance < 50 (gate added)
  - `/api/video-studio/production/producer-chat` → 402 if balance < 50 (gate added)
  - `/api/games/project/{pid}/chat` → 402 with structured detail, owner bypass removed
  - Floor charge `MIN_TURN_CHARGE_TOKENS=1500` on all 3 freebuild agent code paths so credits ALWAYS deduct, even when provider returns zero token counts (root cause of "AI generates for free" bug)
- **🆕 2026-06-21 — PHASES_BY_MODE fix:** `FreeBuildChat.js` sidebar now uses `getPhases(project?.mode)` instead of hardcoded website phases, so APP projects show app phases (تدفق الشاشات / هوية التطبيق / بناء الشاشات / محاكي الجوال) — verified by testing agent

## 🆕 Storage Subscription System (2026-06-21)

Unified storage billing — separated from AI credits. One MB pool across every surface (websites/apps/games/images/videos).

### Plans (monthly recurring via LemonSqueezy)
| Tier | Price | Storage |
|---|---|---|
| Free | $0 | 250 MB |
| Starter | $7/mo | 3 GB |
| Plus ⭐ | $14/mo | 15 GB |
| Pro | $29/mo | 75 GB |
| Studio | $59/mo | 300 GB |

### Grace Period & Recovery
- Payment fail → 10-day grace (email reminders at day 1/5/8 via Resend)
- After grace → files moved to `archived` status (kept on server)
- Archive retention: 6 months → eligible for purge
- Recovery fees: $5 (<1GB) / $15 (1-10GB) / $35 (10-50GB) / $79 (+50GB)
- User must pay recovery fee + renew subscription to regain access

### Implementation
- New module: `/app/backend/modules/storage_billing/__init__.py`
- New collection: `storage_subscriptions` ({user_id, plan_id, status, lemon_subscription_id, current_period_end, grace_started_at, archived_at, archived_size_mb})
- Background loop: hourly check for past_due → archive after 10 days
- New endpoints:
  - `GET /api/storage/plans` — list plans + recovery tiers
  - `GET /api/storage/subscription` — current sub status
  - `POST /api/storage/checkout` — start subscription checkout
  - `POST /api/storage/recovery/checkout` — start one-time recovery
  - `POST /api/storage/webhook` — LemonSqueezy events (subscription_created, payment_failed, cancelled, recovery order)
- Updated `/api/freebuild-chat/storage/usage`:
  - Removed project count limit (unified GB-based quota)
  - Added subscription_status, grace_days_left, archived fields
  - Single helper `_user_total_bytes()` for accurate measurement
- New frontend page: `/billing/storage` with full plan comparison + recovery flow
- Updated `StorageIndicator.js`: context-aware warnings (no more false "تجاوزت الحد" when only over project count)

### Required Owner Action
Create 8 LemonSqueezy Variants and add to `/app/backend/.env`:
- `LEMONSQUEEZY_STORAGE_STARTER` / `_PLUS` / `_PRO` / `_STUDIO` (Subscription products)
- `LEMONSQUEEZY_RECOVERY_SMALL` / `_MEDIUM` / `_LARGE` / `_XL` (One-time products)
- **🆕 Floating language picker + support widget removed** — cleaner pages
- **🆕 Mobile chat overhaul:** PhaseHeaderPill (animated on phase change), credits + storage popovers visible on mobile, send button always visible, attach supports all file types
- **🆕 Hard credit gate (50 credits min) before any AI turn** in `/agent-chat-stream` + `PendingResumeBanner` ("إكمل ➜") that resumes the user's saved message after recharge
- **🆕 Markdown rendering — mobile-safe:** tables overflow-x-auto, links break-all, words wrap, lists fully styled
- **🆕 Storage popover opens from left on mobile** (was off-screen)
- **🆕 Strict Phase Protocol + Completeness Rule** added to system prompt: AI must complete sentences before tool calls, cannot skip phases, must use competitor research with URLs in Discovery
- **🆕 Apps Builder cleaned + unified:** 3 options (Flutter ⭐ recommended, React Native, Native Swift/Kotlin). Removed "تطبيق قابل للإكمال" (lives in its own /projects/continue section). On selection, creates a FreeBuild project with `mode='app'` and redirects to `/freebuild/chat/<pid>` — SAME chat UX as websites.

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
- ✅ Ready Sites Trial checkout → real PayPal URL
- ✅ Ready Sites Purchase checkout → real PayPal URL
- ✅ Credits=0 → 402 across all AI endpoints
- ✅ `charge_user` now deducts from admin/owner accounts too (10100 → 10085 confirmed)
- ✅ FreeBuild streaming agent now tracks input/output tokens via `final_msg.usage`
- ✅ Auth endpoints unaffected
