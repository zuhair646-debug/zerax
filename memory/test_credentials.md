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

Last updated: 2026-06-19 (Session 9 — login fix)
