# Test Credentials

## Local Preview Environment

### Owner Account (full admin access)
- **Email:** owner@zerax.com
- **Password:** owner123
- **Role:** owner
- **Credits:** 10000 (replenish via `db.users.updateOne({email:"owner@zerax.com"}, {$set:{credits:10000}})`)

### Admin Account (alternative)
- **Email:** admin@zenrex.ai
- **Password:** Zenrex@2026
- **Note:** May not work on local preview (used on production)

### Test User
- **Email:** test_zenrex_2026@example.com
- **Password:** Test@Pass2026!
- **Note:** Created on live production

## Production (zenrex.ai)
Same credentials as above. owner@zerax.com is the master admin.

## Useful MongoDB Commands

```bash
# Reset owner credits
python3 -c "
import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
async def main():
    cli = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
    db = cli[os.environ.get('DB_NAME', 'test_database')]
    await db.users.update_one({'email':'owner@zerax.com'}, {'\$set':{'credits':10000}})
asyncio.run(main())
"

# Drop a user's credits to test 402 gate
db.users.updateOne({email:"owner@zerax.com"}, {$set:{credits:4}})

# Clear storage subscription (reset to free)
db.storage_subscriptions.deleteMany({user_id:"<uid>"})
```

## Storage Pricing (Feb 2026 — linear, PayPal-only)
- 10MB Free
- 50MB → $5
- 100MB → $10
- 150MB → $15
- 200MB → $20
- 300MB → $30
- 500MB → $50
- 1GB → $100
- Lemon Squeezy fully removed. PayPal is the sole processor.
