"""
📲 EAS Build Cortex — triggers Expo EAS Build for the customer's project.

Flow:
  1. We generate a Capacitor (or Expo) project files
  2. We zip + upload to user's Expo account via EAS API
  3. EAS builds APK/IPA in the cloud (8-12 min)
  4. We poll status + return download URL to the customer

Requires: EAS_ACCESS_TOKEN from credential vault.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("zenrex.eas_build")

_EAS_API = "https://api.expo.dev/v2"


async def get_user_info(eas_token: str) -> Optional[Dict[str, Any]]:
    """Verify token + get account info."""
    try:
        async with httpx.AsyncClient(timeout=15) as cl:
            r = await cl.get(f"{_EAS_API}/me", headers={"Authorization": f"Bearer {eas_token}"})
        if r.status_code == 200:
            return r.json().get("data")
    except Exception as e:
        logger.warning(f"[eas] user_info failed: {e}")
    return None


async def list_projects(eas_token: str, account_id: str) -> list:
    try:
        async with httpx.AsyncClient(timeout=15) as cl:
            r = await cl.get(f"{_EAS_API}/accounts/{account_id}/projects",
                              headers={"Authorization": f"Bearer {eas_token}"})
        if r.status_code == 200:
            return r.json().get("data", [])
    except Exception as e:
        logger.warning(f"[eas] list_projects: {e}")
    return []


async def trigger_build(
    eas_token: str,
    project_id: str,
    platform: str = "android",  # or "ios"
    build_profile: str = "preview",
) -> Optional[Dict[str, Any]]:
    """Trigger a build. Returns {build_id, status_url} or None."""
    if platform not in ("android", "ios"):
        return {"error": "platform must be android or ios"}
    try:
        async with httpx.AsyncClient(timeout=30) as cl:
            r = await cl.post(
                f"{_EAS_API}/projects/{project_id}/builds",
                headers={"Authorization": f"Bearer {eas_token}", "Content-Type": "application/json"},
                json={"platform": platform, "profile": build_profile},
            )
        if r.status_code in (200, 201):
            data = r.json().get("data") or r.json()
            return {
                "build_id": data.get("id"),
                "status": data.get("status"),
                "platform": platform,
            }
        return {"error": f"HTTP {r.status_code}", "body": r.text[:300]}
    except Exception as e:
        logger.warning(f"[eas] trigger_build failed: {e}")
        return {"error": str(e)}


async def get_build_status(eas_token: str, build_id: str) -> Optional[Dict[str, Any]]:
    """Get current build status + download URL when ready."""
    try:
        async with httpx.AsyncClient(timeout=15) as cl:
            r = await cl.get(f"{_EAS_API}/builds/{build_id}",
                              headers={"Authorization": f"Bearer {eas_token}"})
        if r.status_code == 200:
            data = r.json().get("data") or r.json()
            return {
                "status": data.get("status"),
                "artifact_url": data.get("artifacts", {}).get("buildUrl"),
                "platform": data.get("platform"),
                "queue_position": data.get("queuePosition"),
            }
    except Exception as e:
        logger.warning(f"[eas] get_build_status: {e}")
    return None


async def wait_for_build(eas_token: str, build_id: str, max_wait_sec: int = 900) -> Optional[Dict[str, Any]]:
    """Poll build status until finished or timeout (default 15 min)."""
    waited = 0
    while waited < max_wait_sec:
        st = await get_build_status(eas_token, build_id)
        if st and st.get("status") in ("FINISHED", "ERRORED", "CANCELED"):
            return st
        await asyncio.sleep(15)
        waited += 15
    return {"status": "wait_timeout", "build_id": build_id}


def render_user_instructions_ar(build_id: str, platform: str, status_url: str) -> str:
    return f"""🎉 **بناء التطبيق بدأ!**

- **المعرّف:** `{build_id}`
- **المنصة:** {platform}
- **الوقت المتوقع:** 8-12 دقيقة
- **متابعة:** {status_url}

📲 لما يخلص، سأرسل لك رابط تحميل الـ APK/IPA مباشرة هنا.
"""
