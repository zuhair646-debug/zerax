# Test Credentials

## Audit Test User (created Feb 8 2026 — for non-owner E2E tests)
- Email: `audit_1780793976@test.com`
- Password: `Test1234!`
- Role: regular user
- Starting credits: 20

## Merchant Control Panel (Real Backend Auth — Feb 2026)
- URL: `${REACT_APP_BACKEND_URL}/mockups/admin.html`
- Login: `owner@zenrex.ai` / `owner123` (real JWT via `/api/auth/login`)
- Products now persist to MongoDB via `/api/store/products` (per-merchant scoped by `merchant_id`)
- Customer login on storefront: any phone, OTP = `1234` (real backend via `/api/store/customer/request-otp` + `/verify-otp`)
- Wishlist + Reviews sync to MongoDB when customer is logged in

## Platform Owner (Admin)
- URL: `/login`
- Email: `owner@zenrex.ai`
- Password: `owner123`
- **Note**: Domain migrated from `@zitex.com` to `@zenrex.ai` during the Zenrex rebrand (Feb 16 2026).

## 📧 Owner Notification Email (Jun 11 2026)
- **Personal Gmail (receives all forwarded mail)**: `zenrex.ai@gmail.com`
- All domain emails (`owner@zenrex.ai`, `support@zenrex.ai`, `hello@zenrex.ai`, `info@zenrex.ai`) should forward to this Gmail via Porkbun Email Forwarding.

## 🌐 Production VPS (Hetzner — Jun 11 2026)
- **Public URL**: `http://91.98.154.148`
- **SSH**: `ssh -i /root/.ssh/zenrex_deploy root@91.98.154.148`
- **Admin/Merchant dashboard**: `http://91.98.154.148/mockups/admin.html`
- **Customer storefront**: `http://91.98.154.148/mockups/app_mode_full.html`
- **Driver app**: `http://91.98.154.148/mockups/driver_app.html`
- **Same credentials apply** (owner@zenrex.ai/owner123, phone/OTP=1234)
- **JWT_SECRET**: `zenrex-prod-jwt-secret-2026-hetzner-91-98-154-148` (fixed across restarts)
- **DB**: MongoDB `zenrex_prod` inside `zenrex-mongo-1` container
- **Owner seeded via**: `docker exec zenrex-backend-1 python /app/scripts/seed_owner.py`
- **Nginx config**: `/etc/nginx/sites-enabled/zenrex` (gzip enabled — 4-5x smaller payloads)
- **⚠️ LLM Blocker**: ~~EMERGENT_LLM_KEY restricted to Emergent platform~~ **RESOLVED Jun 11 2026** via direct-SDK shim (`backend/direct_llm_shim.py`).
  - When `USE_DIRECT_LLM=1` is set, `emergentintegrations.llm.chat` is transparently redirected to direct provider calls using `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_DIRECT_KEY` from `.env`.
  - **All 20+ files using `LlmChat` keep working unchanged** — the shim mimics the same interface (`with_model`, `with_params`, `send_message`, `send_message_multimodal_response`).
  - Supported providers: `anthropic` (Claude Sonnet 4.5/4.6) · `gemini` (text + Nano Banana image gen) · `openai` (GPT-4o/GPT-5).
  - Automatic fallback chain: if primary provider fails, the shim tries the others.
  - Image generation uses `gemini-3.1-flash-image` (Nano Banana current production model).
  - On Emergent's preview/dev environment: leave `USE_DIRECT_LLM` unset to continue using the universal key.

## Demo Site — Cozy Cafe Demo

### Client Dashboard (for end-client to manage their site)
- Login URL: `/client/cozy-cafe-demo`
- Password: `WKDWkG0d`

### Public URLs
- Public site: `/sites/cozy-cafe-demo`
- Shareable preview: `/api/websites/share/05VuNbyO9McTmt9Z_Hz68CG4KH0`

### Site Customer (registered via the public site's auth)
- Name: أحمد الزهراني
- Phone: `0501122334`
- Password: `pass123`

### Delivery Driver (registered via client dashboard)
- Name: فهد السائق
- Phone: `0559988776`
- Password: `drv123`

## Auth Flow Notes
- Platform auth: `Authorization: Bearer <jwt>` (existing)
- Client auth: `Authorization: ClientToken <token>` (from `/client/login`)
- Site-customer auth: `Authorization: SiteToken <token>` (from `/public/{slug}/auth/*`)
- Driver auth: `Authorization: DriverToken <token>` (from `/driver/login`)

## Stripe Subscription Gate Test User (Website Studio paywall)
- Email: `gatetest@zenrex.ai`
- Password: `test123`
- Role: client (non-owner — hits paywall)
- Has active `studio_monthly` subscription (paid via Stripe test card 4242 4242 4242 4242, 12/34, 123, ZIP 12345)
- Owner bypasses the gate automatically (no payment required)

## Stripe Test Card
- Number: `4242 4242 4242 4242`
- Expiry: any future date (e.g., `12/34`)
- CVC: any 3 digits (e.g., `123`)
- ZIP: any (e.g., `12345`)

## Zitex Auto-Coder (برمجة زيتاكس) — Owner-Only Codebase Agent
- Route: `/admin/autocoder` (requires `is_owner=true` user)
- **🔑 Current passcode (Jun 2026)**: `zenrex2026`
- **Recovery codes** (use once each if you forget the passcode):
  - `5702-2746-0033-A0B1`
  - `60F3-BBB7-2628-CE0E`
  - `8709-73CF-1C0E-FCDC`
  - `47D8-124D-3183-3BE9`
  - `832D-222C-D803-0402`
  - `6266-B1DE-07D6-7912`
- First visit shows **Setup screen** → owner picks passcode (≥6 chars) → system generates 6 one-time recovery codes
- Subsequent visits show **Lock screen** → enter passcode → 4-hour session token
- Session token stored client-side in `localStorage.zenrex_autocoder_session` and sent in `X-AutoCoder-Token` header
- Forgot passcode? → "نسيت كلمة السر؟" → enter recovery code + new passcode (consumes the recovery code; if all 6 used, system regenerates a fresh batch)
- All actions audited in `autocoder_audit` collection (visible via `GET /api/autocoder/audit`)
- Tools available to the AI: `read_file`, `write_file`, `edit_file`, `delete_file`, `list_dir`, `search_code`, `run_command` (full bash), `restart_service`, `git_status`, `git_diff`, `git_commit_push`
- Backend uses Claude Sonnet 4.5 via owner's `ANTHROPIC_API_KEY` (synced from Railway production)

## App-Mode Mockup (Merchant Admin Control Panel + Video Studio + Delivery)
- **Landing page (unified)**: `${REACT_APP_BACKEND_URL}/mockups/index.html` — 3 cards: Merchant ACP / Driver App / Customer Track
- **Customer tracking**: `${REACT_APP_BACKEND_URL}/mockups/track.html?id=<order_id>` — public Leaflet map with live driver location, ETA, status timeline
- **Driver app**: `${REACT_APP_BACKEND_URL}/mockups/driver_app.html` — phone+OTP login (5 demo phones, OTP=1234)
- **Merchant ACP**: `${REACT_APP_BACKEND_URL}/mockups/app_mode_full.html` — click ♛ to open
- ACP delivery tab has 5 sub-sections: 📦 الطلبات · 🧑‍✈️ السائقون · 🏬 الفروع · 💰 الرواتب · ⚙️ التسعير
- Recharge: click `+ شحن` inside ACP → modal with 4 packages + 5 payment methods (mada/visa/mc/apple_pay/stc_pay)

### Public API endpoints (no auth required)
- `GET  /api/promo-video/health` · `POST /api/promo-video/storyboard` · `POST /api/promo-video/generate` · `GET /api/promo-video/packages` · `POST /api/promo-video/recharge` (MOCKED gateway)
- `POST /api/image-studio/product-info` (Gemini)
- **Delivery (16+ endpoints)**:
  - Drivers CRUD: `GET/POST /api/delivery/drivers`, `PATCH/DELETE /api/delivery/drivers/{id}` (driver now has employment_type, share_per_delivery_sar OR monthly_salary_sar, payout_method, payout_account, country)
  - Driver auth: `POST /api/delivery/driver/login` (returns OTP=1234), `POST /api/delivery/driver/verify-otp`, `GET /api/delivery/driver/me`, `GET /api/delivery/driver/feed`
  - Orders: `GET/POST /api/delivery/orders`, `PATCH /api/delivery/orders/{id}/assign`, `PATCH .../status`, `POST .../location`, `GET .../track` (public, returns driver+location+timeline)
  - **NEW**: `POST /api/delivery/calculate-fee` — Haversine distance + fee breakdown + driver/merchant share preview. Body: `{customer_lat, customer_lng, total_sar, branch_id?}`
  - **NEW**: `GET/POST /api/delivery/branches`, `DELETE /api/delivery/branches/{id}` — branch GPS coords used as distance origin
  - **NEW**: `GET/POST /api/delivery/payouts?driver_id=` — payout history + record wage transfers. Decrements `balance_pending_sar` on commission drivers.
  - **NEW**: `GET /api/delivery/payout-methods?country=SA|AE|EG|KW|BH|QA|OM|IQ` — country-specific payout methods (STC Pay, urpay, PayBy, Vodafone Cash, InstaPay, KNET, ZainCash, etc.)
  - **NEW**: `GET /api/delivery/countries` — 8 supported countries with currency codes
  - Settings: `GET/PATCH /api/delivery/settings` (now includes per_km_sar, base_fee_sar, min_fee_sar, max_fee_sar, driver_share_default_pct, use_distance_pricing toggle)


