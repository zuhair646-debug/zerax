# Test Credentials — Production zenrex.ai

## 🔑 Admin Owner Account (Production)
- **Email**: `admin@zenrex.ai`
- **Password**: `Zenrex@2026`
- **Role**: `owner`
- **URL**: https://zenrex.ai/login

## 🔑 Secondary Owner
- **Email**: `zoheer@zenrex.ai`
- **Role**: `owner`
- (password not reset)

## 🛠️ Local Preview (Emergent)
- **Email**: `owner@zerax.com`
- **Password**: `owner123`
- For testing in Emergent preview environment only.

## 📌 Notes
- Production DB: MongoDB Atlas (`zerax_prod` database)
- Backend connects via `MONGO_URL` env var (Atlas connection string)
- If login fails on production, reset via:
  ```bash
  scp -i /root/.ssh/zerax_deploy /tmp/reset_admin.py root@91.98.154.148:/tmp/
  ssh -i /root/.ssh/zerax_deploy root@91.98.154.148 "docker compose -f /opt/zerax/docker-compose.yml cp /tmp/reset_admin.py backend:/tmp/ && docker compose -f /opt/zerax/docker-compose.yml exec -T backend python3 /tmp/reset_admin.py"
  ```

Last updated: 2026-06-19 (Session 15 — Test customer added)

## 🧪 Test Customer (for quota/billing verification)
- **Email**: `test_zenrex_2026@example.com`
- **Password**: `Test@Pass2026!`
- **Status**: Free tier — currently OVER cap (61,398 / 50,000 tokens, blocked)
- **Use case**: Verify upgrade flow via `/pricing/v2`
- **Note**: Created on preview env; for production, register the same email manually OR reset their tokens via:
  ```python
  await db.usage_daily.delete_many({"user_id": "<uid>"})
  ```
