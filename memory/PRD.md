# Zenrex Farm — PRD (Updated 2026-06-20)

## Problem Statement
Arabic-first AI builder that creates websites, apps, images and videos with strict token tracking, freemium paywalls (Stripe), background-task persistence, Zenrex branding, and exportable codebase. Deployed on Hetzner VPS (zenrex.ai).

## Current Status — Healthy, Production Live
- Domain: https://zenrex.ai
- Backend: Docker compose on VPS (91.98.154.148), MongoDB local
- Frontend: React PWA, Service Worker v4 (network-first, cache-busting)
- LLM: Claude Sonnet 4.5 via Emergent LLM key

## Completed (Recent Session)
- Native App Builder (PWA) with mobile-phone iframe preview
- My Projects continuation dashboard
- Storage Quota indicator + tracking
- ConnectionHelpModal with API key guides
- Resume Reminders email scheduler
- Site-to-App Wizard (scan + convert)
- TermsGate for legal agreements
- Token Meter (usage_meter.py) — 50k cap for free users
- AdminUsageDashboard
- ReadySitesPreview gallery (25 templates)
- Pricing V2 with Launch Promo tiers ($49 / $19 / $69 / $199)
- Service Worker v4 cache-bust deployed
- 2026-06-20: Removed redundant centered Z logo from landing hero (clean homepage) + bumped SW to v4 — deployed to prod ✓

## Pending — P1
- **File Upload UI red→green status indicator** in FreeBuildChat.js (icon turns green when file attached)
- **Email Verification on Registration** — integrate Resend API, send OTP/link, add `is_verified` field, block login until verified
- **Chat Session Reconnection** — re-attach to SSE stream after page reload (recurring issue)

## Pending — P2
- Multi-page architecture for generated sites (`/about`, `/contact`) for SEO
- Visual Guardian (screenshot + Vision LLM bug detection)
- CI/CD pipeline (GitHub Actions → VPS)

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
Note: backend container recreate triggers fresh pip install (~3 min) — health check may 502 for 2-3 min after deploy, then settles healthy.
