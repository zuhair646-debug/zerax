# Zenrex Farm — PRD (Product Requirements Document)

## Original Problem Statement
Deploy Zenrex Farm to the cloud, expand the Zenrex AI Brain to specialized modes, sever ties with Emergent integrations for 100% independence, and build a unified Brand Manager. Within Zenrex Farm, develop a "Kids PWA" — a TikTok-style video aggregator for kids with strict Parent/Child roles, automated targeted scraping, pre-caching for instant playback, and dedicated sections for prayers and rewards.

## User
- **Owner**: Zoheer Z. (Saudi, Arabic Saudi dialect preferred)
- **Children**: Hussein (~10 yrs, older, fuller face, voluminous curly hair) & Abbas (~7-8 yrs, younger, slimmer face, tidier curls)

## Production Infrastructure
- **VPS**: Hetzner — `91.98.154.148`, domain `zenrex.ai`
- **SSH key**: `/root/.ssh/zerax_deploy`
- **Web root**: `/opt/zerax/frontend/build/` (React build) + `/var/www/pwa_kids/` (Kids PWA assets)
- **Backend**: Docker compose at `/opt/zerax` (FastAPI + MongoDB)
- **Deploy script**: `/app/deploy/deploy.sh`

## Kids PWA (Production Status)
- **URL**: `https://zenrex.ai/kids`
- **Manifest**: `/var/www/pwa_kids/manifest.webmanifest` → name "زنركس كيدز برو"
- **Service Worker**: `/var/www/pwa_kids/sw.js` (v5 — bumped Jun 18, 2026)
- **Icons**: `/var/www/pwa_kids/icon-192.png`, `icon-512.png`
- **Auth**: Parent (`zoheer@zenrex.ai` / `Zenrex@2026`), Child accounts in MongoDB
- **Features Live**: Parent dashboard (dynamic kid mgmt, manual URL download, auto-bot config),
  Child TikTok-style feed with SW media caching, achievements tab, prayer tab.

## Changelog
- **2026-06-18**: Generated custom anime PWA logo featuring father (white thobe + glasses) and
  two sons (casual hoodies, peace sign + thumbs-up) on Jeddah Corniche evening background with
  metal railing. Deployed `icon-192.png` & `icon-512.png` to `/var/www/pwa_kids/`. SW bumped v4→v5.
  Old icons backed up as `.bak.<timestamp>`. All approved variations preserved at
  `/app/frontend/public/logo_previews/` (logo_v9_corniche_evening.png is the deployed one).
- **2026-06-18**: Fixed Kids PWA install bug — `/kids` was loading the main Zenrex manifest +
  stale `data:` URI manifest with scope `/`, causing iOS/Android to install it as the main app
  shortcut instead of a separate PWA. Cleaned the published-site HTML in MongoDB — removed 3
  bad manifest links, stale `<section id="head">`, root-scope SW registration. Injected proper
  `<link rel="manifest" data-pwa="kids" data-real="1" href="/kids/manifest.webmanifest">` plus
  apple-touch-icon + apple-mobile-web-app-capable. Fix script at `/app/logo_gen/fix_kids_pwa.py`.

- **2026-06-18**: Added "مكتبة الفيديوهات المعتمدة" section to Parent Dashboard so the parent
  can see ALL approved videos (previously only the empty Pending queue was shown — appeared as
  if videos disappeared). Endpoint: `/api/freebuild-chat/kids/bot/approved` returns 26 docs.
  Each card has video preview + preview link + delete button.

- **2026-06-18 (MAJOR CLEANUP)**: Removed ~200KB of obsolete duplicate sections from
  `freebuild_published_sites.zenrex-kids-pro` HTML (308KB → ~108KB = 64% reduction).
  Backup preserved in same doc as `backup_html_pre_cleanup_v1`. Removed sections:
  `bot-page`, `bottom-nav-update`, `bottom-nav-fixed`, `pwa-sw-inline`, `fixes-core`,
  `init-app-fix`, `bot-save-fix`, `auto-scheduler`, `approval-system`, `reference-samples`,
  `add-by-url`, `cookies-link`, `approval-preview`, `onetime-cleanup`, `ui-bugfixes-v6`,
  `ui-cleanup-v7`, `directed-scraping-v9`, `auth-roles-v10`, `kids-experience-v12/v13/v16`,
  `dynamic-children-v19`, plus 2 dead `<script>` blocks binding to removed `#bot-submit`.
  Fixed JS syntax error from orphan `}).catch(...)` left by earlier SW removal.
  Exposed `window.APP_STATE`, `window.renderVideos`, `window.loadApproved` so post-cleanup
  sections (v17/v18/v22 etc.) can access them. Result: app loads with 0 JS errors,
  approved videos render in parent dash (26 cards) and child feed (26 playing videos),
  bottom nav clean (3 buttons), URL-download triggers immediate refresh. Live sections:
  `auth-roles-v11`, `pwa-install-v8`, `kids-experience-v17`, `parent-add-video-v18`,
  `zk-clean-slate`, `bot-config-v20`, `server-children-v21`, `video-preload-v22`.
- **2026-06 (prior)**: Built full Parent/Child backend auth, dynamic child mgmt widget,
  fullscreen TikTok video UI, yt-dlp fallback chain `/best`, manual URL downloader,
  auto-bot config UI (cookies + keywords + targeted usernames), deep DB purge of
  `big_buck_bunny` mocks, SW v3/v4 caching strategy, 1-year HTTP cache for videos.

## Open Issues / Backlog
### P0 (None currently)

### P1 — Prayer Recording Audio Overlap
- Father's audio playback bleeds into child's microphone recording.
- Needs Acoustic Echo Cancellation, headphone prompt, or UI lock during playback.
- Status: NOT STARTED.

### P1 — Failed (Red) Video Downloads Not Cleaned Up
- User reports: videos that failed to download still show as red/failed in DB.
- Previous agent claimed fix but user confirmed it's NOT done.
- Action: Audit `freebuild_media_assets` collection, build cleanup job for failed entries,
  add admin UI to bulk-purge red items.
- Status: NOT STARTED (user explicitly said "نعالجها بعدين").

### P2 — Points & Rewards System
- UI for achievements exists but backend logic for tracking prayer completion → points/money
  needs to be tied to child's DB record.
- Status: NOT STARTED.

### Future / Backlog
- Automated Travian Account Registration via 2captcha.
- Backblaze B2 integration for storage when Hetzner VPS fills up (currently ~3%).
- Mobile native iOS app wrapper for App Store.

## Architecture Notes
- Monolithic PWA HTML file approaches 300k chars — use `search_replace` carefully.
- All backend routes prefixed `/api`.
- MongoDB collections: `users` (parents + dynamic kids), `freebuild_media_assets`.
- Service Worker: Network-first for HTML, Cache-first for media (1-year HTTP cache).

## Test Credentials
- Parent: `zoheer@zenrex.ai` / `Zenrex@2026`
- Child 1: `حسين@kids.zenrex.ai` / `1234`
- Child 2: `عباس@kids.zenrex.ai` / `5678`

## Recent Logo Reference Assets
- Final approved logo: `/app/frontend/public/logo_previews/logo_v9_corniche_evening.png`
- All variations: `/app/frontend/public/logo_previews/logo_v{5..9}_*.png`
- Master 1024px: `/app/logo_gen/final_icons/icon-1024.png`
- Source reference photos: `/app/logo_gen/real_*.jpg`, `/app/logo_gen/jeddah_*.jpg`
- Generation scripts: `/app/logo_gen/gen_v{2..9}.py`
