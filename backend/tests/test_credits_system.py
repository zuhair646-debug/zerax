"""
Iteration 48 — Credits-based pricing chain end-to-end verification.

Covers:
- /api/billing/packages credit amounts
- /api/auth/register signup bonus = 200 credits
- /api/usage/credits + /api/usage/me
- /api/generate/image deduction via charge_user('image_gpt_standard') = 100 credits
- /api/generate/video deduction via charge_user('video_sora_10s') = 1200 credits
- Quota block when credits == 0
- credit_transactions ledger entries
- Owner/admin bypass (no deduction)

Note: Uses async motor to manipulate `free_images`/`free_videos` to 0 so the
credits-path of the endpoint is exercised. External OpenAI/Sora calls may fail
(500) but the credit deduction happens BEFORE the external call.
"""
import os
import uuid
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or "https://ai-cinematic-hub-2.preview.emergentagent.com"
BASE_URL = BASE_URL.rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN_EMAIL = "admin@zenrex.ai"
ADMIN_PASSWORD = "Zenrex@2026"
LOCAL_OWNER_EMAIL = "owner@zerax.com"
LOCAL_OWNER_PASSWORD = "owner123"


# ─── Helpers ─────────────────────────────────────────────────────────────
def _api(path):
    return f"{BASE_URL}/api{path}"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def new_user(session):
    """Register a brand-new test user and return token + user info."""
    email = f"TEST_credits_{uuid.uuid4().hex[:8]}@example.com"
    password = "Test@Pass2026!"
    r = session.post(_api("/auth/register"), json={
        "email": email,
        "password": password,
        "name": "Credits Test User",
        "country": "SA",
        "gender": "male",
    })
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    user = data.get("user") or {}
    user_id = user.get("id")
    assert token, f"no token in register response: {data}"
    assert user_id, f"no user.id in register response: {data}"
    return {"token": token, "user_id": user_id, "email": email, "password": password, "user": user}


def auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ─── DB helpers (direct motor) ───────────────────────────────────────────
async def _set_user_fields(user_id, fields):
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    await db.users.update_one({"id": user_id}, {"$set": fields})
    client.close()


async def _get_user(user_id):
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    client.close()
    return u


async def _count_debit_tx(user_id, reason_prefix=None):
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    q = {"user_id": user_id, "type": "debit"}
    if reason_prefix:
        q["reason"] = {"$regex": f"^{reason_prefix}"}
    n = await db.credit_transactions.count_documents(q)
    last = await db.credit_transactions.find_one(q, {"_id": 0}, sort=[("ts", -1)])
    client.close()
    return n, last


# ═════════════════════════════════════════════════════════════════════════
# 1. /api/billing/packages — credit amounts
# ═════════════════════════════════════════════════════════════════════════
class TestPackages:
    def test_packages_returns_4_with_credits(self, session):
        r = session.get(_api("/billing/packages"))
        assert r.status_code == 200, r.text
        data = r.json()
        pkgs = {p["id"]: p for p in data.get("packages", [])}
        expected = {
            "project_pack": 5000,
            "tier_starter_monthly": 2000,
            "tier_pro_monthly": 8000,
            "tier_studio_monthly": 25000,
        }
        for pid, credits in expected.items():
            assert pid in pkgs, f"missing package {pid}"
            assert pkgs[pid]["credits"] == credits, f"{pid} credits = {pkgs[pid].get('credits')}, expected {credits}"


# ═════════════════════════════════════════════════════════════════════════
# 2. /api/auth/register signup bonus = 200
# ═════════════════════════════════════════════════════════════════════════
class TestSignupBonus:
    def test_new_user_gets_200_credits(self, new_user):
        # Verify via DB
        u = asyncio.run(_get_user(new_user["user_id"]))
        assert u is not None
        assert u.get("credits") == 200, f"signup credits = {u.get('credits')}, expected 200"

    def test_usage_credits_endpoint(self, session, new_user):
        r = session.get(_api("/usage/credits"), headers=auth(new_user["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("credits") == 200, f"credits={data.get('credits')}"
        assert data.get("unlimited") is False
        assert data.get("tier") == "free"


# ═════════════════════════════════════════════════════════════════════════
# 3. /api/usage/me
# ═════════════════════════════════════════════════════════════════════════
class TestUsageMe:
    def test_usage_me_returns_credits_tier(self, session, new_user):
        r = session.get(_api("/usage/me"), headers=auth(new_user["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "credits" in data
        assert data["credits"] == 200
        assert "month_credits" in data
        assert "today" in data
        assert data.get("tier") == "free"
        assert data.get("quota", {}).get("allowed") is True


# ═════════════════════════════════════════════════════════════════════════
# 4. /api/generate/image deducts 100 credits
# ═════════════════════════════════════════════════════════════════════════
class TestImageDeduction:
    def test_image_deducts_100_credits(self, session, new_user):
        uid = new_user["user_id"]
        # Force free_images=0, give 500 credits so deduction is observable
        asyncio.run(_set_user_fields(uid, {"free_images": 0, "credits": 500}))

        # Snapshot debit count BEFORE
        n_before, _ = asyncio.run(_count_debit_tx(uid, "service:image_gpt_standard"))

        # Call generate/image — external OpenAI call may fail (500) but
        # deduction happens FIRST and we verify via DB balance + ledger.
        r = session.post(
            _api("/generate/image?prompt=test+credits+deduction+please+ignore"),
            headers=auth(new_user["token"]),
        )
        # We don't assert status (OpenAI may fail in preview); we assert deduction.

        u = asyncio.run(_get_user(uid))
        new_bal = u.get("credits")
        assert new_bal == 400, f"after image: balance={new_bal}, expected 400 (500-100). status={r.status_code}"

        n_after, last_tx = asyncio.run(_count_debit_tx(uid, "service:image_gpt_standard"))
        assert n_after == n_before + 1, f"expected +1 image debit, got {n_after - n_before}"
        assert last_tx["amount"] == 100
        assert last_tx["balance_after"] == 400
        assert last_tx["reason"] == "service:image_gpt_standard"


# ═════════════════════════════════════════════════════════════════════════
# 5. /api/generate/video deducts 1200 credits
# ═════════════════════════════════════════════════════════════════════════
class TestVideoDeduction:
    def test_video_deducts_1200_credits(self, session, new_user):
        uid = new_user["user_id"]
        # Force free_videos=0, give 2000 credits
        asyncio.run(_set_user_fields(uid, {"free_videos": 0, "credits": 2000}))

        n_before, _ = asyncio.run(_count_debit_tx(uid, "service:video_sora_10s"))

        r = session.post(
            _api("/generate/video?prompt=test+credits+deduction+please+ignore"),
            headers=auth(new_user["token"]),
        )
        # ignore status; verify deduction
        u = asyncio.run(_get_user(uid))
        new_bal = u.get("credits")
        assert new_bal == 800, f"after video: balance={new_bal}, expected 800 (2000-1200). status={r.status_code}"

        n_after, last_tx = asyncio.run(_count_debit_tx(uid, "service:video_sora_10s"))
        assert n_after == n_before + 1, f"expected +1 video debit, got {n_after - n_before}"
        assert last_tx["amount"] == 1200
        assert last_tx["balance_after"] == 800

    def test_video_insufficient_credits_returns_402(self, session, new_user):
        uid = new_user["user_id"]
        # Set credits below cost
        asyncio.run(_set_user_fields(uid, {"free_videos": 0, "credits": 100}))
        r = session.post(
            _api("/generate/video?prompt=insufficient+test"),
            headers=auth(new_user["token"]),
        )
        assert r.status_code == 402, f"expected 402 insufficient credits, got {r.status_code} {r.text}"


# ═════════════════════════════════════════════════════════════════════════
# 6. Zero-credit blocking — check_quota
# ═════════════════════════════════════════════════════════════════════════
class TestQuotaBlockZeroCredits:
    def test_usage_me_blocks_when_zero(self, session, new_user):
        uid = new_user["user_id"]
        asyncio.run(_set_user_fields(uid, {"credits": 0}))
        r = session.get(_api("/usage/me"), headers=auth(new_user["token"]))
        assert r.status_code == 200
        q = r.json().get("quota", {})
        assert q.get("allowed") is False, f"expected blocked, got {q}"
        assert q.get("reason") == "no_credits"
        assert "message" in q

    def test_usage_credits_zero(self, session, new_user):
        # already 0 from above
        r = session.get(_api("/usage/credits"), headers=auth(new_user["token"]))
        assert r.status_code == 200
        assert r.json().get("credits") == 0


# ═════════════════════════════════════════════════════════════════════════
# 7. Owner / admin NEVER charged
# ═════════════════════════════════════════════════════════════════════════
class TestOwnerBypass:
    def _try_login(self, session, email, password):
        r = session.post(_api("/auth/login"), json={"email": email, "password": password})
        return r

    def test_admin_login_and_image_no_deduction(self, session):
        # Try local owner first, fall back to admin
        candidates = [
            (LOCAL_OWNER_EMAIL, LOCAL_OWNER_PASSWORD),
            (ADMIN_EMAIL, ADMIN_PASSWORD),
        ]
        token = None
        uid = None
        used_email = None
        for email, pwd in candidates:
            r = self._try_login(session, email, pwd)
            if r.status_code == 200:
                data = r.json()
                token = data.get("access_token") or data.get("token")
                uid = (data.get("user") or {}).get("id")
                used_email = email
                if token and uid:
                    break
        if not token or not uid:
            pytest.skip("No owner/admin login available in this env")

        # Verify role
        u = asyncio.run(_get_user(uid))
        role = (u or {}).get("role", "")
        assert role in ("owner", "admin", "super_admin"), f"login user {used_email} role={role}, not owner/admin"

        bal_before = (u or {}).get("credits", 0) or 0

        # Force free_images=0 so the credits branch would otherwise trigger
        asyncio.run(_set_user_fields(uid, {"free_images": 0}))

        r = session.post(
            _api("/generate/image?prompt=owner+bypass+test"),
            headers=auth(token),
        )
        # Don't care about status (external API may fail). Verify no deduction.

        u2 = asyncio.run(_get_user(uid))
        bal_after = (u2 or {}).get("credits", 0) or 0
        assert bal_after == bal_before, (
            f"owner was charged! before={bal_before} after={bal_after}"
        )


# ═════════════════════════════════════════════════════════════════════════
# 8. Chat deduction path (text_claude_1k) — direct unit invocation
# This is the same code path freebuild_chat → record_usage → charge_user uses.
# We invoke it directly so we don't depend on the freebuild project flow.
# ═════════════════════════════════════════════════════════════════════════
class TestChatDeductionPath:
    def test_record_usage_deducts_text_claude_credits(self, new_user):
        """record_usage(tokens_in=600, tokens_out=400) → multiplier=1.0 → 30 credits."""
        uid = new_user["user_id"]

        async def _run():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            # Set known balance
            await db.users.update_one({"id": uid}, {"$set": {"credits": 500}})
            from modules.ai_core.usage_meter import record_usage
            result = await record_usage(
                db, uid, project_id="test_proj", section="test_section",
                tokens_in=600, tokens_out=400,
                model_label="test-claude",
            )
            user = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1})
            last_tx = await db.credit_transactions.find_one(
                {"user_id": uid, "reason": "service:text_claude_1k"},
                {"_id": 0}, sort=[("ts", -1)],
            )
            client.close()
            return result, user, last_tx

        result, user, last_tx = asyncio.run(_run())
        assert result.get("ok") is True, f"record_usage failed: {result}"
        # 30 credits * (1000/1000) = 30
        assert user["credits"] == 470, f"expected 500-30=470, got {user['credits']}"
        assert last_tx is not None
        assert last_tx["amount"] == 30.0
        assert last_tx["balance_after"] == 470
        assert last_tx["meta"]["multiplier"] == 1.0

    def test_record_usage_partial_multiplier(self, new_user):
        """tokens=500 → multiplier=0.5 → 15 credits."""
        uid = new_user["user_id"]

        async def _run():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            await db.users.update_one({"id": uid}, {"$set": {"credits": 500}})
            from modules.ai_core.usage_meter import record_usage
            await record_usage(
                db, uid, project_id=None, section="chat",
                tokens_in=300, tokens_out=200,
            )
            user = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1})
            client.close()
            return user

        user = asyncio.run(_run())
        # 30 * 0.5 = 15
        assert user["credits"] == 485, f"expected 500-15=485, got {user['credits']}"

    def test_record_usage_no_credits_returns_error(self, new_user):
        """When user has 0 credits, record_usage returns ok:false reason:no_credits."""
        uid = new_user["user_id"]

        async def _run():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            await db.users.update_one({"id": uid}, {"$set": {"credits": 0}})
            from modules.ai_core.usage_meter import record_usage, check_quota
            result = await record_usage(
                db, uid, project_id=None, section="chat",
                tokens_in=500, tokens_out=500,
            )
            quota = await check_quota(db, uid)
            client.close()
            return result, quota

        result, quota = asyncio.run(_run())
        assert result.get("ok") is False
        assert result.get("error") == "no_credits"
        assert quota.get("allowed") is False
        assert quota.get("reason") == "no_credits"


# ═════════════════════════════════════════════════════════════════════════
# 9. Ledger schema verification
# ═════════════════════════════════════════════════════════════════════════
class TestLedgerSchema:
    def test_credit_transactions_have_required_fields(self, new_user):
        uid = new_user["user_id"]
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]

        async def _check():
            txs = await db.credit_transactions.find(
                {"user_id": uid, "type": "debit"}, {"_id": 0}
            ).to_list(length=20)
            return txs

        txs = asyncio.run(_check())
        client.close()
        assert len(txs) >= 1, "no debit transactions found for test user"
        for tx in txs:
            assert tx.get("type") == "debit"
            assert "amount" in tx
            assert "balance_after" in tx
            assert tx.get("reason", "").startswith("service:")
            assert "ts" in tx
