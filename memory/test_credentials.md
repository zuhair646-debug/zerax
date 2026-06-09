# Test Credentials

## Audit Test User (created Feb 8 2026 — for non-owner E2E tests)
- Email: `audit_1780793976@test.com`
- Password: `Test1234!`
- Role: regular user
- Starting credits: 20

## Platform Owner (Admin)
- URL: `/login`
- Email: `owner@zerax.com`
- Password: `owner123`

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
- Email: `gatetest@zerax.com`
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
- **🔑 Current passcode (Jun 2026)**: `zerax2026`
- **Recovery codes** (use once each if you forget the passcode):
  - `5702-2746-0033-A0B1`
  - `60F3-BBB7-2628-CE0E`
  - `8709-73CF-1C0E-FCDC`
  - `47D8-124D-3183-3BE9`
  - `832D-222C-D803-0402`
  - `6266-B1DE-07D6-7912`
- First visit shows **Setup screen** → owner picks passcode (≥6 chars) → system generates 6 one-time recovery codes
- Subsequent visits show **Lock screen** → enter passcode → 4-hour session token
- Session token stored client-side in `localStorage.zerax_autocoder_session` and sent in `X-AutoCoder-Token` header
- Forgot passcode? → "نسيت كلمة السر؟" → enter recovery code + new passcode (consumes the recovery code; if all 6 used, system regenerates a fresh batch)
- All actions audited in `autocoder_audit` collection (visible via `GET /api/autocoder/audit`)
- Tools available to the AI: `read_file`, `write_file`, `edit_file`, `delete_file`, `list_dir`, `search_code`, `run_command` (full bash), `restart_service`, `git_status`, `git_diff`, `git_commit_push`
- Backend uses Claude Sonnet 4.5 via owner's `ANTHROPIC_API_KEY` (synced from Railway production)

