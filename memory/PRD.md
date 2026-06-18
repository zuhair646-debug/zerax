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

- **2026-06-18 (v34 — COMPREHENSIVE PARENT DASHBOARD + Audio/Video fixes)**:
  Complete rebuild of parent dashboard from scratch (no widget relocations).
  Fixes for audio overlap, slow video preload, broken category filter, camera permissions.
  
  **Backend additions**:
  - `POST /kids/video-metadata`: yt-dlp --dump-json title/thumb/duration without download
  - `GET /kids/parent-summary`: aggregated kids+stats endpoint
  
  **Frontend `parent-final-v34` (282KB total page)**:
  - **Audio fix**: `enforceSingleVideo()` pauses all others when one plays + IntersectionObserver aggressively pauses off-screen videos
  - **Preload speedup**: real `<link rel="preload" as="video">` for next 2 + preload=auto only for current ±2 + strips harmful crossOrigin
  - **Category filter works**: drawer → `zkApplyCategory(id)` → display:none on non-matching slides + scroll to first visible
  - **9-tab parent dashboard** (Videos/Cats/Tasks/Dhikr/Prayers/Kids/Stats/Bot/Settings) all self-contained, no relocations
  - **Camera permission wrapper**: friendly modal with retry on NotAllowedError/NotFoundError/etc + auto-fallback constraints
  - **Sticky red Logout button** on parent bar
  - **Video URL preview**: paste URL → 🔍 معاينة → see title/thumb/duration → 📥 download + AI categorize
  - **Stats panel**: per-kid cards with total points, monthly SAR, prayer/task recording counts, recent activity ledger + recordings with ▶ playback link
  - Child UI completely untouched (4-tab UX preserved)
  
  **SW bumped** to `zenrex-kids-v10-v34`.


  Major restructure of parent dashboard into a proper control center plus
  P0 bug fixes for audio and video preload.
  
  **Backend additions (`/opt/zerax/backend/modules/freebuild/freebuild_chat.py`)**:
  - **`/kids/categories` (GET/POST/DELETE)**: Parent-managed video categories.
    Defaults seeded per parent: الكل, ألعاب, قرآن, تعليمي.
  - **`/kids/parent-tasks` (GET/POST/DELETE)**: Parent-managed daily tasks.
    Includes `needs_camera` flag, `points` per task, `icon`. Defaults seeded.
  - **`/kids/auto-categorize` (POST)**: Single video AI categorization via
    Claude Haiku 4.5 (Emergent LLM Key). Reads video title, returns category id.
  - **`/kids/auto-categorize/all` (POST)**: Batch categorize all uncategorized
    approved videos (max 50/call). Uses helper `_categorize_one`.
  - **Fallback**: When LLM unavailable, falls back to keyword matching.
  - **Default categories/tasks** are auto-seeded on first GET call per parent.
  
  **Frontend `parent-console-v33` section**:
  - **AUDIO FIX**: Removes harmful `crossOrigin='anonymous'` set by v22 (was
    preventing playback on Chrome Android per v25 PRD note). Force-unmutes
    all videos on first user tap (touchstart/click capture once).
  - **VIDEO PRELOAD FIX**: Prefetches next 2 videos as no-cors fetch warm-up,
    sets `preload="auto"` only for current+next-2, `preload="metadata"` for rest.
    Eliminates the slow-to-start issue.
  - **Categories drawer**: Pills bar (`.pills-bar`) hidden. Replaced with
    floating `🏷️` button (`#v33-cat-fab`) → opens bottom sheet drawer.
    Selecting a category triggers the existing pill click for filter logic.
  - **Parent dashboard restructure**: 7 tabs strip at top of parent-page:
    🎬 Videos / 🏷️ Categories / 🎯 Tasks / 📿 Dhikr / 🕌 Prayers / 📊 Stats / ⚙️ Settings.
    Legacy parent UI is relocated into the appropriate tabs.
  - **Logout button**: Prominent red button on parent bar (sticky top) + 
    full-width button in Settings tab. Clears all localStorage + reloads.
  - **Categories CRUD UI**: Inline form (icon + title) + list with delete buttons.
    System categories (like "الكل") can't be deleted.
  - **Tasks CRUD UI**: Inline form (icon + title + points + needs_camera) + list.
    Soft-delete (sets `is_active=false`).
  - **Stats tab**: Per-child cards showing total points, today, streak, monthly SAR.
    Recent activity ledger. Pulls from `/kids/points/summary`.
  - **AI button**: "🤖 إعادة تصنيف الفيديوهات الموجودة" in Videos tab
    calls `/kids/auto-categorize/all` to retro-categorize all videos.
  - **Service Worker bumped** to `zenrex-kids-v9-v33`.
  
  **Child UI untouched** (per user instruction). Only parent role sees the
  new dashboard via `body[data-zk-role="parent"]` CSS selector.
  
  **Verified end-to-end**:
  - `GET /kids/categories`: returns 4-5 default + custom categories ✓
  - `GET /kids/parent-tasks`: returns 6 default tasks ✓
  - `POST /kids/auto-categorize` (single): Claude Haiku correctly tagged
    "تحصَّن بالقرآن العظيم" → category=`quran` ✓
  - `POST /kids/auto-categorize/all` (batch): 25 videos categorized in ~60s ✓
  - Pills-bar `display: none`, FAB + drawer present in DOM ✓

## Changelog

- **2026-06-18 (v32 — Real points engine + production polish)**:
  Closed the loop on the points/rewards system end-to-end so kids' actions
  actually persist server-side instead of localStorage-only.
  
  **Backend changes (`/opt/zerax/backend/modules/freebuild/freebuild_chat.py`)**:
  - **Relaxed child_email validation**: Now accepts any `@kids.*` domain (was hardcoded
    to `@kids.local`). Fixes upload 403 for the real `@kids.zenrex.ai` accounts.
  - **`POST /kids/recordings/upload`**: New fields `rec_type` (prayer|task|dhikr),
    `task_id`, `task_title`, `points`. Auto-awards points (default: prayer=10, task=5)
    on successful upload by inserting into new `kids_points` ledger.
  - **`POST /kids/points/award`** (NEW): Client-driven point award.
    Form: `child_email`, `kind`, `value`, `meta_json`. Returns running total.
  - **`GET /kids/points/summary?child_email=...`** (NEW): Real totals, today/week
    breakdown, by_kind aggregation, streak (consecutive days), monthly SAR.
  - **`GET /kids/achievements`**: Refactored to use real `kids_points` + 
    `kids_recordings` collections (dropped hardcoded `hussain@kids.local` baselines).
  
  **Frontend `production-polish-v32` section (in MongoDB published HTML)**:
  - **Hide reactions on non-home tabs**: Real CSS selectors targeting
    `.side-controls`, `#share-btn`, `#comment-drawer` (v31 had wrong selectors).
  - **Backend points sync**: Intercepts `window.alert` calls matching dhikr/task
    completion messages and POSTs to `/kids/points/award`. Also wraps `window.fetch`
    so any task recording upload gets `rec_type=task` + correct `points` injected.
  - **Live profile stats**: Pulls from `/kids/points/summary` on profile tab,
    overrides localStorage display with real total, streak, and adds a
    "today" pill (`#v32-today-pill`).
  - **Strong headphones warning** (`#v32-headphones`): Red banner shown on prayer
    card click ("لازم تلبس السماعة... عشان صوت أبوك ما يدخل في تسجيل صلاتك").
  - **Auto-pause home videos when leaving home tab** (battery + audio focus).
  - **Service Worker bumped** to `zenrex-kids-v8-v32` to force update on existing
    PWA installs.
  
  **Verified end-to-end via prod curl + Playwright**:
  - `POST /kids/points/award` returns running total.
  - `GET /kids/points/summary` returns correct aggregations by kind + streak.
  - `POST /kids/recordings/upload` with `rec_type=task` awards points automatically.
  - `GET /kids/achievements` shows real prayer/task counts.
  - CSS `display:none` confirmed on `.side-controls` when body[data-tab=profile].
  - Login API works for `حسين@kids.zenrex.ai` with PIN 1234.


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

- **2026-06-18 (v25 — CRITICAL PRODUCTION FIX: Video Playback)**:
  Root cause of "videos spin forever and don't play" diagnosed and fully fixed.
  
  **3 layered issues found**:
  1. **HEVC codec everywhere**: 26 of 27 downloaded TikTok videos were H.265/HEVC.
     Most browsers (Chrome on Android, Firefox, older iOS) cannot decode HEVC.
     This is the PRIMARY cause of infinite buffering on mobile.
  2. **Service Worker was caching media** (v5/v6): SW was caching video files which
     broke Range requests — cached 200 responses can't satisfy Range, causing infinite
     buffering after first load. nginx already serves videos with `Cache-Control: max-age=31536000 immutable`
     so HTTP cache handles it perfectly; SW caching was harmful.
  3. **`muted=false` + `crossOrigin='anonymous'`** prevented mobile autoplay + forced
     unnecessary CORS mode.
  
  **Fixes applied**:
  - **Batch transcoded all 27 videos** HEVC → H.264 (libx264 High profile, yuv420p) via
    background ffmpeg. Space went from ~30MB HEVC + ~80MB temp → 18MB H.264. HEVC backups deleted.
  - **SW v7** (`/var/www/pwa_kids/sw.js`): COMPLETE REWRITE. Media files now pass-through
    (no SW interception). Only HTML + manifest + icons cached. Range requests work natively.
    SW activate clears all old `zenrex-kids-v5/v6/media-v1` caches.
  - **yt-dlp download endpoint** (`POST /media/download`) updated to:
    `-f bv*[height<=720][ext=mp4][vcodec*=avc1]+ba[ext=m4a]/...` + `-S vcodec:h264` +
    `--recode-video mp4` + `--postprocessor-args "-c:v libx264 -preset fast -crf 23 -c:a aac -movflags +faststart"`.
    All future downloads will be H.264 + faststart (instant playback, no remux needed).
  - **Frontend video creation**: `muted=true`, `playsinline`, `webkit-playsinline`, `preload=auto`,
    `loop=true` for TikTok-style continuous playback. Removed harmful `crossOrigin='anonymous'`.
  - **New section `video-playback-fix-v25`**:
    * Tap-to-unmute floating banner
    * Auto-detect stuck videos (>8s no progress) → force reload
    * Error overlay with retry button per video
    * Defensive: clears any leftover `media-v1` / `v5` / `v6` caches on every page load
    * Forces SW update on existing PWA installs

- **2026-06-18 (PRAYER MODULE v23)**: Built new Prayer Studio. Parent dashboard gets 5 prayer
  cards (Fajr/Dhuhr/Asr/Maghrib/Isha) with 🎤 سجّل button → records voice via MediaRecorder
  (audio/webm + echoCancellation). Backend adds `DELETE /kids/audio/{id}`, `POST /kids/audio/{id}/prayer`,
  `POST /kids/audio/{id}/order`. Child side has fullscreen camera studio (`#pc-shell`): tap a
  prayer tile → camera opens (front default, flip button) + parent's audio plays via Audio() →
  video+mic recording starts (echoCancellation on child mic; headphones recommended for clean
  audio isolation) → auto-stops at 16 minutes → uploads to `/kids/recordings/upload` for parent review.

- **2026-06-18 (v24 — 4 user fixes)**:
  1. **Main feed loads for parent too**: `loadAndShuffleChildFeed` now accepts both parent & child
     roles (parent can verify what the kid sees). Random shuffle on every load (Fisher-Yates).
  2. **Inline preview modal** (`#vpm-modal`): Replaced `window.open()` redirect for preview buttons.
     Plays video/audio in a centered black modal — no more redirecting to main Zenrex app.
     Reusable via `window.previewMedia(url, title, type)`.
  3. **Prayer audio supports file upload**: Each prayer card now has 📁 رفع button + 🎤 سجّل button.
     File upload shows confirmation with duration + size + prayer name before uploading.
     Supports any audio/* format. No size limit beyond FastAPI default (~100MB), good for 20+ min recordings.
  4. **YouTube cookies upload UI**: Added prominent red box in URL-download section with step-by-step
     Arabic instructions on how to export cookies via "Get cookies.txt LOCALLY" Chrome extension.
     One-click upload to `POST /media/cookies/upload?platform=youtube`. Fixes YouTube bot-detection.
  
  **Parent side** (in Parent Dashboard, section `pm-parent-1`):
    - 5 prayer cards: الفجر / الظهر / العصر / المغرب / العشاء (each with emoji icon)
    - Tap "🎤 سجّل" → records parent's voice via MediaRecorder (audio/webm)
    - Tap "▶" to preview, "🗑" to delete
    - Status shows "✅ مسجّل" or "لم يُسجّل بعد"
    - Uses echoCancellation + noiseSuppression at capture
    - Backend: POST `/api/freebuild-chat/kids/audio/upload` (existing) +
      `POST /kids/audio/{aid}/prayer` (NEW — tag with prayer id) +
      `DELETE /kids/audio/{aid}` (NEW)
  
  **Child side** (full-screen overlay `#pc-shell` triggered from nav prayer button):
    - Sees 5 prayer tiles in same order as parent's recordings
    - Disabled prayers grayed out if parent hasn't recorded yet
    - Tap a tile → opens fullscreen camera studio
    - Front camera default, "🔄" button switches front/back
    - "●" button starts: video+audio recording (echoCancellation enabled for child mic) +
      parent's audio plays via Audio() element through earphones
    - Timer counter, **auto-stop at 16 minutes** (configurable)
    - Mute/unmute parent audio button (🔊/🔇)
    - On stop: uploads child's recording via `POST /api/freebuild-chat/kids/recordings/upload`
      with audio_track = prayer name → parent can review in their dashboard
    - HEADPHONES REQUIRED warning shown on the screen ("🎧 تأكد من توصيل السماعات قبل البدء")
  
  **Architecture decision**: Since child uses Bluetooth/wired headphones, parent's audio
  goes directly into the child's ear (not played through speakers) → mic only picks up
  child's voice. echoCancellation = belt-and-suspenders defense for any acoustic leakage.

- **2026-06-18 (UI cleanup)**: Removed orphan "عنوان الفيديو / التصنيف" floating overlay
  from bottom-right corner (legacy `.video-info` div, hidden via `display:none`).
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

### P1 — TikTok Channel Bulk Importer (commercially valuable)
- Single field: paste channel URL → "اسحب كل القناة" button → background job pulls all videos
- Uses existing `yt-dlp` infra + cookies. Progress bar via WebSocket or polling.
- Cleaner UX than current bot-config-v20 widget.
- Status: NOT STARTED.

### P1 — Prayer Module — Reorder UI
- Parent can record per prayer, but cannot YET drag-reorder the 5 cards (currently fixed order Fajr→Isha).
- If needed: add `order` field via existing `POST /kids/audio/{aid}/order` endpoint (already created).

### P1 — Prayer Recordings Review Tab
- Parent dashboard needs a tab showing kid's prayer-recordings (`kids_recordings` collection).
- Endpoint `GET /api/freebuild-chat/kids/recordings` already exists — just needs UI.

### P1 — Failed (Red) Video Downloads Not Cleaned Up
- User reports: videos that failed to download still show as red/failed in DB.
- Previous agent claimed fix but user confirmed it's NOT done.
- Action: Audit `freebuild_media_assets` collection, build cleanup job for failed entries,
  add admin UI to bulk-purge red items.
- Status: NOT STARTED (user explicitly said "نعالجها بعدين").

### P2 — Points & Rewards System
- ✅ **DONE (2026-06-18, v32)**: Real `kids_points` ledger + `/kids/points/award`,
  `/kids/points/summary`, `/kids/achievements` all use real DB data. Frontend syncs
  via fetch interception + alert hooks. Profile shows live total + today pill.

### Future / Backlog
- Automated Travian Account Registration via 2captcha.
- Backblaze B2 integration for storage when Hetzner VPS fills up (currently ~3%).
- Mobile native iOS app wrapper for App Store.

## Commercial Export Plan (Future)
The current Kids PWA serves as a prototype for a multi-tenant commercial product:
- Strip out: prayer module + achievements (those are personal).
- Keep: parent-child auth, TikTok channel bulk import, video moderation flow,
  approved feed, custom branding (logo per tenant).
- Sell as a FreeBuild template: "تطبيق فيديو آمن للأطفال بإشراف ولي الأمر".
- Tenants get their own slug under `/s/{tenant-slug}` with their own branding.

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
