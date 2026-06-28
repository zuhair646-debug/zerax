# Zenrex Continuation Mode — Roadmap

Last updated: 2026-02-06

## ✅ DONE (Production-ready)

### Core architecture
- [x] Sandbox isolation (`/opt/zerax/sandboxes/{pid}/`)
- [x] Snapshot system with millisecond-precision timestamps (no collisions)
- [x] Tamper-evident audit log (SHA-256 chain)
- [x] AES-128 Fernet encryption for all customer credentials
- [x] Paywall guard ($150/month) on every write tool + endpoint layer
- [x] `mark_first_update` tool that triggers the subscription banner
- [x] Defense-in-depth: HTTP endpoints check paywall BEFORE tool dispatch

### Tools the AI engineer has (53 total, 22 continuation-specific)
**Continuation Site (12):**
clone_remote_repo, ftp_sync_pull, create_snapshot, list_snapshots, restore_snapshot, list_sandbox_files, read_sandbox_file, propose_sandbox_change, push_to_review_branch, deploy_to_live_vps, deploy_to_live_ftp, mark_first_update

**Continuation App (10):**
detect_project_stack, run_sandbox_command, submit_to_app_store, delete_sandbox_file, move_sandbox_file, apply_patch, get_continuation_status, inspect_saved_credentials, read_continuation_audit, lookup_domain_knowledge

### Stack detection (25+ stacks)
Flutter · React Native (bare + Expo) · Capacitor · Ionic · Cordova · NativeScript · .NET MAUI · Android Native (Kotlin/Java) · iOS Native (Swift/ObjC) · Electron · Tauri · Next.js · Vue/Nuxt · React (Vite/CRA) · Node.js (Express/Fastify/NestJS/Koa/Hono) · Python (FastAPI/Django/Flask) · Go · Rust · Java Spring · .NET · PHP Laravel/Symfony · Ruby Rails · Unity · Unreal · Godot · WordPress — supports monorepos.

### Domain expertise (17 verticals)
banking · lending · stocks_trading · ecommerce · food_delivery · healthcare · education · real_estate · beauty_salons · construction · government_services · logistics_shipping · automotive · social_networking · fitness_wellness · media_entertainment · travel_tourism

Each domain provides: typical sections + Saudi/GCC compliance (SAMA, ZATCA, SDAIA, REGA, MOH, CMA) + common integrations (Nafath, SADAD, Mada, Tabby, Tamara, SIMAH, Yakeen, Ejar) + security critical + pitfalls + KPIs + recommended stacks + anti-patterns.

### Providers catalog (35 total)
- 6 Git providers (GitHub, GitLab, Bitbucket, Gitea, …)
- 14 hosting providers (Hetzner, DO, AWS EC2, Vercel, cPanel, Hostinger, …)
- 4 build services (EAS, Codemagic, Bitrise, GitHub Actions)
- 9 app stores (Play, App Store Connect, Firebase Distribution, TestFlight, MS Store, Steam, itch.io, Amazon, Huawei)
- 2 signing (Android Keystore, iOS Provisioning Profile)

### Frontend
- [x] `/freebuild/continue` — website continuation landing
- [x] `/freebuild/continue-app` — mobile/native app continuation landing
- [x] 4-step onboarding wizard with encrypted credential capture
- [x] Sandbox preview panel + audit log viewer
- [x] Direct deploy modal (SSH/FTP with confirmation)
- [x] PR-based deploy (creates GitHub branch + PR)
- [x] Phone-frame style stacks badges (25 visible)

### Tests
- [x] 66 unit tests, all passing
- [x] E2E #1: 12-step real Zenrex frontend codebase (clone, edit, snapshot, paywall, restore)
- [x] E2E #2: 11-step monorepo (Flutter + Go) with stack detection
- [x] Engineer coverage audit: 28/28 capabilities = 100%
- [x] Security test: inspect_saved_credentials never leaks secrets

---

## 🟡 P1 — Next priority (blocked on user input)

- [ ] **GitHub OAuth app** — replace manual PAT pasting (blocked: need Client ID/Secret)
- [ ] **Vercel OAuth app** — same (blocked: need credentials)
- [ ] **`sandbox.zenrex.ai` DNS + certbot** — for visual preview before approve (blocked: need DNS A-record)
- [ ] **Real Stripe key on preview env** to test $150 checkout end-to-end (current key is placeholder)

---

## 🟢 P2 — Engineering capacity available

### Auto-Rollback
- [ ] After `deploy_to_live_vps`, hit `/api/health` on customer domain; if status != 200 in 30s, auto-restore last snapshot + reverse rsync
- [ ] Configurable health endpoint per project (default `/api/health`, `/healthz`, `/`)

### Stripe Webhook (close the payment loop)
- [ ] Webhook endpoint `/api/stripe/webhook/continuation` validates signature
- [ ] On `checkout.session.completed` → flip `continuation_unlocked=True`
- [ ] On `customer.subscription.deleted` → revert to locked
- [ ] Audit trail of every subscription event

### Triple-redundancy backups
- [ ] Local sandbox snapshots (already exists)
- [ ] Git branch backups on customer's repo (`zenrex-backup/YYYYMMDD`)
- [ ] S3-compatible storage backup (Wasabi / Cloudflare R2 / Backblaze B2)

### Storage billing cron
- [ ] Monthly job calculating `continuation_storage_mb` per project
- [ ] If > 5GB → upgrade tier, notify customer

### Real app-store integrations (currently manual-steps only)
- [ ] Play Console direct upload via fastlane supply (Google Service Account JSON)
- [ ] App Store Connect via fastlane pilot / deliver (API Key + Issuer)
- [ ] Microsoft Store via MSStore API
- [ ] Huawei AppGallery via fastlane huawei
- [ ] Steam via steamcmd
- [ ] itch.io via butler

### Phone-frame preview in chat (for apps)
- [ ] Iframe-style phone mockup rendering the running RN/Flutter app
- [ ] QR code → opens app in Expo Go on customer's phone
- [ ] Live-reload from sandbox edits

### Refactoring (technical debt)
- [ ] Split `freebuild_chat.py` (9,500 lines) → 4 modules: routes, models, business_logic, utils
- [ ] Split `freebuild_agent.py` (11,500 lines) → tool_loops, system_prompts, helpers, validators

---

## 🔵 P3 — Future, nice-to-have

### Domain knowledge expansion
- [ ] Add 10 more verticals: agritech, insurtech, energy, telecom, hospitality, religious_apps, marketplace_c2c, freelance_marketplace, donation_platforms, kids_education
- [ ] Per-region variants (UAE, Egypt, Qatar — different regulators)

### Stack detection deepening
- [ ] Per-stack lint rules (e.g. detect Flutter null-safety violations automatically)
- [ ] Vulnerability scan (Snyk/Trivy) on detected dependencies
- [ ] Outdated dependency alerts (npm outdated, pub outdated, pip-audit)

### AI engineer capabilities
- [ ] `run_security_scan` — Bandit/Semgrep/Trivy on the sandbox
- [ ] `generate_test_suite` — given a code file, AI proposes pytest/jest tests
- [ ] `optimize_bundle_size` — analyze and fix bloat in mobile bundles
- [ ] `migrate_to_latest` — major version upgrades with breaking-change handling

### Customer portal
- [ ] Self-service dashboard: see all continuation projects, subscriptions, audit logs, snapshots
- [ ] Download monthly subscription PDF invoice (ZATCA-compliant)
- [ ] Cancel subscription button (with 7-day cool-off Saudi consumer law)

### Marketing/conversion
- [ ] Public landing page: testimonials, case studies, ROI calculator
- [ ] "How it works" 2-min video
- [ ] Affiliate program for agencies referring continuation customers

---

## File map

```
/app/backend/modules/freebuild/
  continuation_tools.py             — site tools (12)
  continuation_app_tools.py         — app tools (10) + domain KB loader
  continuation_stack_detector.py    — universal stack detection (25+)
  continuation_audit.py             — SHA-256 audit log
  continuation_help.py              — help/escalation modal API
  secure_credentials.py             — AES-128 Fernet encryption
  freebuild_chat.py                 — HTTP routes (9.5k lines, needs split)
  freebuild_agent.py                — AI loop + system prompts (11.5k lines)
  cortex_tools.py                   — tool registry

/app/backend/data/
  continuation_providers.json       — 35 providers (git/host/build/store/signing)
  continuation_domain_knowledge.json — 17 industry playbooks

/app/backend/tests/
  test_continuation_paywall.py        (10 tests)
  test_continuation_direct_deploy.py  (5 tests)
  test_continuation_app_tools.py      (30 tests — detector + whitelist + handlers)
  test_continuation_gap_tools.py      (10 tests — delete/move/patch/status/inspect/audit)
  test_continuation_domain_knowledge.py (11 tests)
  test_continuation_e2e_real.py       (12-step E2E on real Zenrex code)
  test_continuation_app_e2e.py        (11-step E2E on Flutter+Go monorepo)
  test_engineer_coverage_audit.py     (capability coverage script)

/app/frontend/src/pages/
  FreeBuildContinue.jsx                — site continuation landing
  FreeBuildContinueApp.jsx             — app continuation landing
  ContinuationOnboarding.jsx           — 4-step wizard
  ContinuationPreviewPanel.jsx         — sandbox file viewer + deploy controls
```
