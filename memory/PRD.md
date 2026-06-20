# Zenrex Farm — PRD (Updated 2026-06-20)

## Problem Statement
Arabic-first AI builder for websites/apps/images/videos with credits-based pricing, Stripe payments, background-task persistence, and exportable codebase. Deployed on Hetzner VPS (zenrex.ai).

## Current Status — Healthy, Production Live
- Domain: https://zenrex.ai
- Backend: Docker compose on VPS, MongoDB local
- Frontend: React PWA, Service Worker v5 (network-first, cache-busting)
- LLM: Claude Sonnet 4.5 via Emergent LLM key

## Pricing Model — CREDITS-BASED (2026-06-20 pivot)
Simple price → credits. No feature lists, no projects/month, no fake promises.
- Free signup: **200 credits** bonus (~$1 of value)
- Project Pack: **$49** → **5,000 credits** (one-time, never expires)
- Starter: **$19/month** → **2,000 credits** (refills on renewal)
- Pro: **$69/month** → **8,000 credits** (most popular)
- Studio: **$199/month** → **25,000 credits**

**Credit economics:** 1 credit ≈ $0.005 actual LLM cost (~500 AI tokens). Margin floor ~37%, typical 60%+.
- Field: `users.credits` (existing field, also used for image/video deduction)
- Deduction: `usage_meter.record_usage()` → `$inc credits: -ceil(cost_usd * 200)`
- Block: `check_quota()` → blocks if `credits <= 0`, friendly upgrade prompt
- Endpoint: `GET /api/usage/credits` (lightweight, polled by navbar badge every 20s)

## Recent Completed Work (2026-06-20 session)
- Removed redundant centered Z logo from landing hero
- Fixed `/pricing` to load PricingV2 directly (was loading old Pricing.js)
- Made `emergentintegrations` import lazy in `billing/routes.py` (module was failing to load on prod since SDK is intentionally uninstalled for 100% independence — only checkout creation needs it now)
- **Major pivot: credits-based pricing**
  - Removed all `tier_quota_projects`, `tier_quota_mb`, `daily_token_cap` from packages
  - PricingV2.jsx completely rewritten: simple cards (price + credits + button only)
  - Webhook fulfillment now adds credits to `users.credits` instead of setting quotas
  - usage_meter deducts credits on every AI call
  - check_quota now blocks when `credits <= 0`
  - CreditsBadge added to Navbar (top-right next to Pricing link)
  - Quota-exceeded chat message updated with new tier prices

## Pending — P1
- 🟢 **File Upload UI red→green status indicator** in FreeBuildChat.js
- 📧 **Email Verification on Registration** — Resend API, OTP/link, `is_verified` field, block login until verified
- 🔄 **Chat Session Reconnection** — re-attach to SSE stream after page reload
- 💳 **Replace `emergentintegrations.payments.stripe`** with official `stripe` SDK for full independence
- 🪙 **Top-up credits packs** (one-time small purchases like 1,000 credits for $9)

## Pending — P2
- Multi-page architecture for generated sites (`/about`, `/contact`) for SEO
- Visual Guardian (screenshot + Vision LLM bug detection)
- CI/CD pipeline (GitHub Actions → VPS)
- Backfill existing free users to 200 credits (currently at legacy 20)

## Refactoring Backlog
- Split FreeBuildChat.js (4500+ lines) into smaller components
- Dedupe webhook vs. polling user-upgrade logic in billing/routes.py

## Tech Stack
React, FastAPI, MongoDB, Stripe, Resend, Emergent LLM (Claude Sonnet 4.5), PWA Service Worker, SSE.

## Test Credentials
- Admin: admin@zenrex.ai / Zenrex@2026
- Prod Test User: test_zenrex_2026@example.com / Test@Pass2026!

## Deployment
`bash /app/deploy/deploy.sh zenrex.ai` — builds React, rsyncs to VPS, reloads nginx, recreates backend container.
Backend recreate triggers fresh pip install (~3 min) → health check may 502 briefly, settles ~2-3 min after.
