# ──────────────────────────────────────────
# Zitex Backend — Environment Variables
# ──────────────────────────────────────────
# Copy this file to `.env` and fill in real values.
# DO NOT commit `.env` to git.

# MongoDB connection (Atlas free cluster works great)
MONGO_URL=mongodb+srv://USER:PASSWORD@cluster.mongodb.net
DB_NAME=zitex_production

# JWT signing secret — change this to a long random string before deploy
JWT_SECRET=change-me-to-a-long-random-string-min-32-chars

# Allowed CORS origins (comma-separated). Use your Vercel frontend URL in production.
# Example: CORS_ORIGINS=https://zitex.vercel.app,https://www.your-domain.com
CORS_ORIGINS=*

# Emergent Universal LLM Key (one key for OpenAI / Claude / Gemini)
# Get from: https://platform.emergent.sh → Profile → Universal Key
EMERGENT_LLM_KEY=

# Stripe — for the platform subscription gate ($50/mo studio access)
# Get from: https://dashboard.stripe.com → Developers → API keys
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Optional: ElevenLabs (text-to-speech). Leave empty to disable.
ELEVENLABS_API_KEY=

# Optional: Public app URL (used for Stripe redirects, share links).
# Set to the production URL once deployed.
PUBLIC_APP_URL=
