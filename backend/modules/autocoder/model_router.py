"""
Smart Model Router — pick the cheapest capable model for each task.

The router decides WHICH model+provider to use based on:
  • task_type (coding/writing/reasoning/vision/long_context/quick_qa/translation/arabic)
  • required_context (tokens needed)
  • required_capabilities (vision, function_calling, json_mode)
  • language hint (Arabic, English, code)
  • budget hint ('cheap' | 'balanced' | 'best')

Priority ladder per task (left=preferred=cheapest acceptable):

    coding         → Kimi K2.6 → Claude Sonnet → GPT-4o
    long_context   → Kimi K2.6 (256K) → Claude Sonnet → GPT-4o
    creative_write → Claude Sonnet → GPT-4o → Kimi
    reasoning_hard → GPT-5/4o → Claude Opus → Kimi
    quick_qa       → Groq Llama → Gemini Flash → GPT-4o-mini
    vision         → GPT-4o → Gemini 3 Flash → Claude Sonnet
    arabic         → Claude Sonnet → GPT-4o → Gemini

Auto-fallback: if a provider returns rate-limit / 402 / 5xx / suspended → next in chain.
Tracks usage in `model_router_usage` collection for cost analytics.
"""
from __future__ import annotations
import os
import time
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Per-1M-token pricing (Feb 2026, USD). Lower = cheaper.
MODELS: Dict[str, Dict[str, Any]] = {
    # ─────────── Moonshot Kimi (Chinese — excellent coding & 256K context) ───────────
    "kimi-k2.6": {
        "provider": "moonshot",
        "base_url": "https://api.moonshot.ai/v1",
        "context": 256_000,
        "input_per_1m": 0.73,
        "output_per_1m": 3.40,
        "capabilities": {"function_calling": True, "json_mode": True, "vision": False},
        "good_at": ["coding", "long_context", "agentic", "tools"],
    },
    "kimi-k2.5": {
        "provider": "moonshot",
        "base_url": "https://api.moonshot.ai/v1",
        "context": 128_000,
        "input_per_1m": 0.30,
        "output_per_1m": 1.20,
        "capabilities": {"function_calling": True, "json_mode": True, "vision": False},
        "good_at": ["coding", "long_context"],
    },
    "moonshot-v1-128k-vision-preview": {
        "provider": "moonshot",
        "base_url": "https://api.moonshot.ai/v1",
        "context": 128_000,
        "input_per_1m": 0.30,
        "output_per_1m": 1.20,
        "capabilities": {"function_calling": True, "json_mode": True, "vision": True},
        "good_at": ["vision", "long_context"],
    },
    # ─────────── DeepSeek V3.2 (Chinese — design/creative powerhouse, very cheap) ───────────
    "deepseek-chat": {
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "context": 128_000,
        "input_per_1m": 0.27,
        "output_per_1m": 1.10,
        "capabilities": {"function_calling": True, "json_mode": True, "vision": False},
        "good_at": ["design", "ui_ux", "creative_write", "coding", "arabic"],
    },
    "deepseek-reasoner": {
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "context": 128_000,
        "input_per_1m": 0.55,
        "output_per_1m": 2.19,
        "capabilities": {"function_calling": False, "json_mode": True, "vision": False},
        "good_at": ["reasoning_hard", "math", "coding"],
    },
    # ─────────── Zhipu GLM-4.6 (Chinese — best design/UI generation as of Feb 2026) ───────────
    "glm-4.6": {
        "provider": "zhipu",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "context": 200_000,
        "input_per_1m": 0.60,
        "output_per_1m": 2.20,
        "capabilities": {"function_calling": True, "json_mode": True, "vision": True},
        "good_at": ["design", "ui_ux", "vision", "creative_write", "arabic"],
    },
    # ─────────── OpenAI ───────────
    "gpt-4o": {
        "provider": "openai",
        "context": 128_000,
        "input_per_1m": 2.50,
        "output_per_1m": 10.00,
        "capabilities": {"function_calling": True, "json_mode": True, "vision": True},
        "good_at": ["creative", "reasoning", "vision", "arabic"],
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "context": 128_000,
        "input_per_1m": 0.15,
        "output_per_1m": 0.60,
        "capabilities": {"function_calling": True, "json_mode": True, "vision": True},
        "good_at": ["quick_qa", "classification", "simple"],
    },
    "gpt-5": {
        "provider": "openai",
        "context": 400_000,
        "input_per_1m": 1.25,
        "output_per_1m": 10.00,
        "capabilities": {"function_calling": True, "json_mode": True, "vision": True},
        "good_at": ["reasoning_hard", "creative", "vision"],
    },
    # ─────────── Anthropic Claude ───────────
    "claude-sonnet-4-5": {
        "provider": "anthropic",
        "context": 200_000,
        "input_per_1m": 3.00,
        "output_per_1m": 15.00,
        "capabilities": {"function_calling": True, "json_mode": False, "vision": True},
        "good_at": ["arabic", "creative_write", "coding", "agentic"],
    },
    "claude-opus-4-5": {
        "provider": "anthropic",
        "context": 200_000,
        "input_per_1m": 15.00,
        "output_per_1m": 75.00,
        "capabilities": {"function_calling": True, "json_mode": False, "vision": True},
        "good_at": ["arabic", "creative_write", "reasoning_hard", "agentic"],
    },
    # ─────────── Groq (FREE tier — super fast) ───────────
    "llama-3.3-70b-versatile": {
        "provider": "groq",
        "context": 128_000,
        "input_per_1m": 0.59,
        "output_per_1m": 0.79,
        "capabilities": {"function_calling": True, "json_mode": True, "vision": False},
        "good_at": ["quick_qa", "speed", "simple"],
    },
    # ─────────── Gemini 2.5 Pro (premium quality) ───────────
    "gemini-2.5-pro": {
        "provider": "gemini",
        "context": 2_000_000,
        "input_per_1m": 1.25,
        "output_per_1m": 5.00,
        "capabilities": {"function_calling": True, "json_mode": True, "vision": True},
        "good_at": ["reasoning_hard", "long_context", "vision", "design"],
    },
    "gemini-2.5-flash": {
        "provider": "gemini",
        "context": 1_000_000,
        "input_per_1m": 0.075,
        "output_per_1m": 0.30,
        "capabilities": {"function_calling": True, "json_mode": True, "vision": True},
        "good_at": ["quick_qa", "long_context", "vision", "cheap"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# QUALITY-FIRST LADDERS (Feb 2026)
# Order: BEST QUALITY first → fallback to next best if provider missing.
# Price is the tie-breaker only when quality is comparable.
# ═══════════════════════════════════════════════════════════════════════════
TASK_LADDERS: Dict[str, List[str]] = {
    # 💻 General coding — Kimi K2.6 (#1 SWE-bench, 256K) → Claude Sonnet → GPT-5
    "coding":          ["kimi-k2.6", "claude-sonnet-4-5", "claude-opus-4-5", "gpt-4o", "deepseek-chat"],

    # 🚀 Hard coding (big refactors, complex logic) — Kimi K2.6 + Claude Opus dual
    "coding_strong":   ["kimi-k2.6", "claude-opus-4-5", "claude-sonnet-4-5", "gpt-5", "deepseek-reasoner"],

    # 📚 Very long documents — Kimi K2.6 (256K) → Gemini 2.5 Pro (1M)
    "long_context":    ["kimi-k2.6", "gemini-2.5-pro", "gemini-2.5-flash", "claude-sonnet-4-5"],

    # ✍️ Creative writing — Claude leads, GPT-5/4o as alt voices
    "creative_write":  ["claude-opus-4-5", "claude-sonnet-4-5", "gpt-4o", "deepseek-chat"],

    # 🧠 Hard reasoning / math / planning
    "reasoning_hard":  ["gpt-5", "claude-opus-4-5", "gemini-2.5-pro", "deepseek-reasoner", "claude-sonnet-4-5"],

    # ⚡ Fast Q&A — quality decent, speed matters more
    "quick_qa":        ["claude-sonnet-4-5", "gemini-2.5-flash", "gpt-4o", "llama-3.3-70b-versatile"],

    # 🌐 Translation
    "translation":     ["claude-sonnet-4-5", "gpt-4o", "gemini-2.5-pro", "gemini-2.5-flash"],

    # 🏷️ Classification — speed matters, quality similar
    "classification":  ["claude-sonnet-4-5", "gpt-4o-mini", "gemini-2.5-flash"],

    # 👁️ Vision — Claude Sonnet + GPT-4o are state of the art
    "vision":          ["claude-sonnet-4-5", "gpt-4o", "gemini-2.5-pro", "gemini-2.5-flash"],

    # 🇸🇦 Arabic — Claude Opus dominates, Sonnet very close, GPT-4o solid
    "arabic":          ["claude-opus-4-5", "claude-sonnet-4-5", "gpt-4o", "gemini-2.5-pro"],

    # 🤖 Agentic / tool use — Claude leads
    "agentic":         ["claude-opus-4-5", "claude-sonnet-4-5", "gpt-4o", "kimi-k2.6"],

    # 📦 Strict JSON output
    "json_strict":     ["claude-sonnet-4-5", "gpt-4o", "gpt-4o-mini", "gemini-2.5-flash"],

    # 🎨 Design / UI / UX — best Arabic + visual taste
    "design":          ["claude-opus-4-5", "claude-sonnet-4-5", "gpt-4o", "glm-4.6", "deepseek-chat"],
    "ui_ux":           ["claude-opus-4-5", "claude-sonnet-4-5", "gpt-4o", "glm-4.6"],

    # 🌐 Website build — Kimi K2.6 leads (256K ctx, top SWE-bench coding, cheap),
    # Claude Opus as quality fallback, Sonnet+GPT-4o as wider net.
    "website_build":   ["kimi-k2.6", "claude-opus-4-5", "claude-sonnet-4-5", "gpt-4o"],

    # 📱 Mobile App — Kimi K2.6 great at React Native; Claude for polish
    "mobile_app":      ["kimi-k2.6", "claude-opus-4-5", "claude-sonnet-4-5", "gpt-4o"],

    # 🎮 Game dev — Kimi K2.6 for code, Claude for game design narrative
    "game_dev":        ["kimi-k2.6", "claude-sonnet-4-5", "gpt-4o", "deepseek-chat"],

    # 🎬 Video/script creative
    "video_script":    ["claude-opus-4-5", "claude-sonnet-4-5", "gpt-4o", "deepseek-chat"],

    # 🖼️ Image brief writing (English prompts from Arabic ideas)
    "image_brief":     ["claude-sonnet-4-5", "gpt-4o", "deepseek-chat", "gemini-2.5-flash"],

    # 💬 Support / FAQ — fast + decent
    "support_chat":    ["claude-sonnet-4-5", "gpt-4o", "gemini-2.5-flash"],
}


def _provider_ready(provider: str) -> bool:
    env_map = {
        "openai": "OPENAI_DIRECT_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "moonshot": "MOONSHOT_API_KEY",
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "zhipu": "ZHIPU_API_KEY",
    }
    var = env_map.get(provider)
    if not var:
        return False
    if (os.environ.get(var) or "").strip():
        return True
    # secondary env names
    if provider == "openai" and (os.environ.get("OPENAI_API_KEY") or "").strip():
        return True
    return False


async def hydrate_keys_from_vault(db) -> Dict[str, bool]:
    """
    On startup, decrypt provider keys stored in `credentials_vault` and
    expose them via os.environ so `_provider_ready` / direct SDK clients
    can find them.  Returns a map of {provider: was_loaded}.
    """
    if db is None:
        return {}
    service_to_env = {
        "openai":    "OPENAI_DIRECT_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "moonshot":  "MOONSHOT_API_KEY",
        "groq":      "GROQ_API_KEY",
        "gemini":    "GEMINI_API_KEY",
        "deepseek":  "DEEPSEEK_API_KEY",
        "zhipu":     "ZHIPU_API_KEY",
    }
    loaded: Dict[str, bool] = {}
    try:
        import base64
        import hashlib
        from cryptography.fernet import Fernet
        seed = (os.environ.get("JWT_SECRET", "") + os.environ.get("MONGO_URL", "")).encode()
        if not seed:
            return loaded
        key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
        fernet = Fernet(key)
        cursor = db.credentials_vault.find({}, {"_id": 0, "service": 1, "value_encrypted": 1})
        async for doc in cursor:
            service = (doc.get("service") or "").lower()
            env_var = service_to_env.get(service)
            if not env_var:
                continue
            if (os.environ.get(env_var) or "").strip():
                loaded[service] = True
                continue  # already set; don't override
            enc = doc.get("value_encrypted") or ""
            if not enc:
                continue
            try:
                plaintext = fernet.decrypt(enc.encode()).decode().strip()
                if plaintext:
                    os.environ[env_var] = plaintext
                    loaded[service] = True
            except Exception as e:
                logger.warning(f"hydrate_keys: failed to decrypt {service}: {e}")
    except Exception as e:
        logger.warning(f"hydrate_keys_from_vault failed: {e}")
    return loaded


_DB = None


def bind_db(db) -> None:
    global _DB
    _DB = db


async def _moonshot_key() -> str:
    """Env first, vault fallback (mirrors other helpers)."""
    k = os.environ.get("MOONSHOT_API_KEY", "").strip()
    if k:
        return k
    if _DB is None:
        return ""
    try:
        doc = await _DB.credentials_vault.find_one({"service": "moonshot"}, {"_id": 0})
        if not doc:
            return ""
        enc = doc.get("value_encrypted") or ""
        if not enc:
            return ""
        import base64
        import hashlib
        from cryptography.fernet import Fernet
        seed = (os.environ.get("JWT_SECRET", "") + os.environ.get("MONGO_URL", "")).encode()
        key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
        return Fernet(key).decrypt(enc.encode()).decode()
    except Exception:
        return ""


def _classify_task(prompt: str, hint: Optional[str], requires_vision: bool, context_hint_tokens: int) -> str:
    if hint and hint in TASK_LADDERS:
        return hint
    if requires_vision:
        return "vision"
    if context_hint_tokens > 30_000:
        return "long_context"
    if not prompt:
        return "quick_qa"
    p = prompt.lower()
    # Code/programming indicators (check BEFORE language detection)
    code_signals = ("```", "def ", "function ", "class ", "import ", "console.log",
                    "<div", "select ", "api ", "endpoint", "refactor", "debug",
                    "fix this bug", "implement", "كود", "برمج", "اكتب دالة",
                    "احذف الـ", "أضف endpoint", "صلّح", "API key")
    if any(k in prompt or k in p for k in code_signals):
        return "coding"
    # Creative writing signals (Arabic + English)
    creative_signals = ("اكتب قصة", "اكتب لي قصة", "قصة قصيرة", "شعر ", "قصيدة", "مقال ",
                         "story", "poem", "essay", "draft", "creative")
    if any(k in prompt or k in p for k in creative_signals):
        return "creative_write"
    if any(k in p for k in ("translate", "translation", "to arabic", "to english")) or "ترجم" in prompt:
        return "translation"
    if any(k in p for k in ("classify", "categorize")) or "صنّف" in prompt:
        return "classification"
    # Arabic detection (any Arabic letter)
    is_arabic = any("\u0600" <= ch <= "\u06ff" for ch in prompt[:500])
    if any(k in p for k in ("solve", "prove", "step by step", "analyse", "analyze", "reasoning")) \
            or "احسب" in prompt or "أثبت" in prompt:
        return "reasoning_hard"
    if is_arabic:
        if len(prompt) < 100:
            return "quick_qa"  # short Arabic Q&A → Gemini Flash (super cheap)
        return "arabic"
    if any(k in p for k in ("write a story", "creative", "poem", "essay", "draft")):
        return "creative_write"
    if len(prompt) < 200:
        return "quick_qa"
    return "creative_write"


def pick_model(
    task_type: Optional[str] = None,
    prompt: str = "",
    requires_vision: bool = False,
    context_hint_tokens: int = 0,
    budget: str = "balanced",  # 'cheap' | 'balanced' | 'best'
    force_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Decide which model to use. Returns {model, provider, reason, ladder, classified_task}."""
    if force_model and force_model in MODELS:
        return {"model": force_model, "provider": MODELS[force_model]["provider"],
                "reason": "forced by caller", "ladder": [force_model],
                "classified_task": task_type or "forced"}

    task = task_type or _classify_task(prompt, None, requires_vision, context_hint_tokens)
    ladder = list(TASK_LADDERS.get(task, TASK_LADDERS["creative_write"]))

    # Budget shaping: 'cheap' = pick the cheapest in the ladder even if it's last
    if budget == "cheap":
        ladder.sort(key=lambda m: MODELS[m]["output_per_1m"])
    # 'best' = respect the ladder order (already curated best-first per task)
    # No reordering — task-specific ladders know their winners (e.g. coding → Kimi K2.6)

    # Filter to providers with credentials configured AND capabilities matching
    needs = []
    if requires_vision:
        needs.append("vision")
    available = [m for m in ladder if _provider_ready(MODELS[m]["provider"])
                 and all(MODELS[m]["capabilities"].get(n) for n in needs)]
    if context_hint_tokens > 0:
        available = [m for m in available if MODELS[m]["context"] >= context_hint_tokens]
    if not available:
        # fall back: any configured model
        available = [m for m in MODELS if _provider_ready(MODELS[m]["provider"])]
        if not available:
            return {"model": None, "provider": None,
                    "reason": "no provider has credentials configured!",
                    "ladder": ladder, "classified_task": task}

    chosen = available[0]
    return {
        "model": chosen,
        "provider": MODELS[chosen]["provider"],
        "input_cost": MODELS[chosen]["input_per_1m"],
        "output_cost": MODELS[chosen]["output_per_1m"],
        "context_max": MODELS[chosen]["context"],
        "reason": f"task={task} budget={budget}",
        "ladder": ladder,
        "classified_task": task,
    }


async def smart_complete(
    messages: List[Dict[str, str]],
    task_type: Optional[str] = None,
    requires_vision: bool = False,
    budget: str = "balanced",
    force_model: Optional[str] = None,
    max_tokens: int = 4000,
    temperature: float = 0.7,
    response_format: Optional[Dict[str, str]] = None,
    timeout: int = 90,
) -> Dict[str, Any]:
    """Run a chat completion with automatic model selection + provider fallback.

    Returns:
        {ok, content, model_used, provider, usage, cost_estimate_usd, fallback_chain}
    """
    # Approximate input tokens for context filtering
    user_text = " ".join(m.get("content", "") if isinstance(m.get("content"), str) else "" for m in messages)
    est_in = len(user_text) // 4
    pick = pick_model(task_type=task_type, prompt=user_text[-2000:],
                       requires_vision=requires_vision,
                       context_hint_tokens=est_in,
                       budget=budget, force_model=force_model)
    if not pick.get("model"):
        return {"ok": False, "error": pick["reason"]}

    ladder = pick["ladder"]
    last_err = None
    tried = []

    for model_id in ladder:
        if not _provider_ready(MODELS[model_id]["provider"]):
            continue
        info = MODELS[model_id]
        provider = info["provider"]
        tried.append(model_id)
        t0 = time.time()
        try:
            result = await _call_provider(
                provider=provider, model_id=model_id, info=info,
                messages=messages, max_tokens=max_tokens,
                temperature=temperature, response_format=response_format,
                timeout=timeout,
            )
            if result.get("ok"):
                # Track usage
                if _DB is not None:
                    try:
                        usage = result.get("usage") or {}
                        in_tok = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                        out_tok = usage.get("completion_tokens") or usage.get("output_tokens") or 0
                        cost = (in_tok / 1_000_000) * info["input_per_1m"] + (out_tok / 1_000_000) * info["output_per_1m"]
                        await _DB.model_router_usage.insert_one({
                            "model": model_id, "provider": provider,
                            "task": pick["classified_task"],
                            "input_tokens": in_tok, "output_tokens": out_tok,
                            "cost_usd": round(cost, 6),
                            "duration_ms": int((time.time() - t0) * 1000),
                            "ts": datetime.now(timezone.utc).isoformat(),
                        })
                        result["cost_estimate_usd"] = round(cost, 6)
                    except Exception:
                        pass
                result["fallback_chain"] = tried
                return result
            last_err = result.get("error", "unknown")
            logger.warning(f"[router] {model_id} failed: {last_err[:120]}")
        except Exception as e:
            last_err = str(e)
            logger.warning(f"[router] {model_id} exception: {e}")

    return {"ok": False, "error": last_err or "all providers failed",
            "tried": tried, "ladder": ladder}


async def _call_provider(provider: str, model_id: str, info: Dict[str, Any],
                          messages: List[Dict[str, str]], max_tokens: int,
                          temperature: float, response_format: Optional[Dict],
                          timeout: int) -> Dict[str, Any]:
    """Provider-specific dispatch. Returns {ok, content, usage, error?}."""

    if provider in ("openai", "moonshot", "groq", "zhipu", "deepseek"):
        # OpenAI-compatible SDK
        try:
            from openai import AsyncOpenAI
        except Exception:
            return {"ok": False, "error": "openai SDK missing"}
        if provider == "openai":
            api_key = os.environ.get("OPENAI_DIRECT_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
            base_url = None
        elif provider == "moonshot":
            api_key = await _moonshot_key()
            base_url = info.get("base_url") or "https://api.moonshot.ai/v1"
        elif provider == "zhipu":
            api_key = os.environ.get("ZHIPU_API_KEY", "")
            base_url = "https://api.z.ai/api/paas/v4"
        elif provider == "deepseek":
            api_key = os.environ.get("DEEPSEEK_API_KEY", "")
            base_url = "https://api.deepseek.com/v1"
        else:  # groq
            api_key = os.environ.get("GROQ_API_KEY", "")
            base_url = "https://api.groq.com/openai/v1"
        if not api_key:
            return {"ok": False, "error": f"{provider} key missing"}
        client = AsyncOpenAI(api_key=api_key, base_url=base_url) if base_url else AsyncOpenAI(api_key=api_key)
        try:
            kwargs: Dict[str, Any] = dict(
                model=model_id, messages=messages,
                max_tokens=max_tokens, temperature=temperature, timeout=timeout,
            )
            if response_format:
                kwargs["response_format"] = response_format
            resp = await client.chat.completions.create(**kwargs)
            return {"ok": True,
                    "content": resp.choices[0].message.content or "",
                    "model_used": model_id, "provider": provider,
                    "usage": resp.usage.model_dump() if resp.usage else {}}
        except Exception as e:
            return {"ok": False, "error": f"{provider}: {type(e).__name__}: {str(e)[:200]}"}

    if provider == "anthropic":
        try:
            from anthropic import AsyncAnthropic
        except Exception:
            return {"ok": False, "error": "anthropic SDK missing"}
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY missing"}
        # Split system out of messages list (Anthropic expects it separately)
        system_text = "\n".join(m["content"] for m in messages if m.get("role") == "system" and isinstance(m.get("content"), str))
        non_sys = [m for m in messages if m.get("role") != "system"]
        client = AsyncAnthropic(api_key=api_key)
        try:
            resp = await client.messages.create(
                model="claude-sonnet-4-5-20250929" if model_id == "claude-sonnet-4-5" else model_id,
                system=system_text or "You are a helpful assistant.",
                messages=non_sys,
                max_tokens=max_tokens, temperature=temperature,
            )
            content_text = ""
            for block in resp.content:
                if getattr(block, "type", "") == "text":
                    content_text += block.text
            return {"ok": True, "content": content_text,
                    "model_used": model_id, "provider": "anthropic",
                    "usage": {"input_tokens": resp.usage.input_tokens,
                               "output_tokens": resp.usage.output_tokens}}
        except Exception as e:
            return {"ok": False, "error": f"anthropic: {type(e).__name__}: {str(e)[:200]}"}

    if provider == "gemini":
        try:
            import httpx
        except Exception:
            return {"ok": False, "error": "httpx missing"}
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "GEMINI_API_KEY missing"}
        # Concatenate messages into Gemini parts
        contents = []
        for m in messages:
            role = m.get("role")
            if role == "system":
                continue
            text = m.get("content") if isinstance(m.get("content"), str) else str(m.get("content"))
            contents.append({"role": "user" if role == "user" else "model", "parts": [{"text": text}]})
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                r = await c.post(url, json={"contents": contents,
                                              "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}})
            data = r.json()
            if "error" in data:
                return {"ok": False, "error": f"gemini: {data['error'].get('message','')[:200]}"}
            cands = data.get("candidates") or []
            if not cands:
                return {"ok": False, "error": "gemini: empty response"}
            text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []))
            usage = data.get("usageMetadata") or {}
            return {"ok": True, "content": text, "model_used": model_id, "provider": "gemini",
                    "usage": {"input_tokens": usage.get("promptTokenCount", 0),
                               "output_tokens": usage.get("candidatesTokenCount", 0)}}
        except Exception as e:
            return {"ok": False, "error": f"gemini: {type(e).__name__}: {str(e)[:200]}"}

    return {"ok": False, "error": f"unknown provider: {provider}"}


# ════════════════════════════════════════════════════════════════════════
# Auto-Coder tool wrappers
# ════════════════════════════════════════════════════════════════════════
async def tool_smart_complete(prompt: str, task_type: Optional[str] = None,
                                budget: str = "balanced",
                                max_tokens: int = 2000) -> Dict[str, Any]:
    """Run a one-shot prompt through the smart router (auto-picks cheapest capable model)."""
    r = await smart_complete(
        messages=[{"role": "user", "content": prompt}],
        task_type=task_type, budget=budget, max_tokens=max_tokens,
    )
    return r


async def tool_router_stats(days: int = 7) -> Dict[str, Any]:
    """📊 Cost breakdown for the last N days, grouped by model + task."""
    if _DB is None:
        return {"ok": False, "error": "db not bound"}
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    pipeline = [
        {"$match": {"ts": {"$gte": since}}},
        {"$group": {
            "_id": {"model": "$model", "task": "$task"},
            "calls": {"$sum": 1},
            "in_tokens": {"$sum": "$input_tokens"},
            "out_tokens": {"$sum": "$output_tokens"},
            "cost": {"$sum": "$cost_usd"},
        }},
        {"$sort": {"cost": -1}},
        {"$limit": 30},
    ]
    rows = await _DB.model_router_usage.aggregate(pipeline).to_list(30)
    total_cost = sum(r["cost"] for r in rows)
    return {"ok": True, "days": days, "total_cost_usd": round(total_cost, 4),
            "breakdown": [{"model": r["_id"]["model"], "task": r["_id"]["task"],
                            "calls": r["calls"], "cost_usd": round(r["cost"], 4),
                            "in": r["in_tokens"], "out": r["out_tokens"]} for r in rows]}


async def tool_router_route(task_type: Optional[str] = None,
                              prompt_sample: str = "",
                              budget: str = "balanced") -> Dict[str, Any]:
    """🧭 Show which model the router WOULD pick (without running)."""
    p = pick_model(task_type=task_type, prompt=prompt_sample, budget=budget)
    return {"ok": True, **p}


ROUTER_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "smart_complete",
        "description": ("🤖 شغّل prompt واحد عبر الـrouter — يختار النموذج الأرخص القادر تلقائياً. "
                       "task_type: coding|long_context|creative_write|reasoning_hard|quick_qa|"
                       "translation|vision|arabic|agentic. budget: cheap|balanced|best."),
        "input_schema": {"type": "object", "properties": {
            "prompt": {"type": "string"},
            "task_type": {"type": "string"},
            "budget": {"type": "string", "enum": ["cheap", "balanced", "best"]},
            "max_tokens": {"type": "integer"},
        }, "required": ["prompt"]},
    },
    {
        "name": "router_stats",
        "description": "📊 إحصائيات استخدام الـrouter (تكلفة + tokens لكل نموذج) آخر N يوم.",
        "input_schema": {"type": "object", "properties": {"days": {"type": "integer"}}, "required": []},
    },
    {
        "name": "router_route",
        "description": "🧭 يعرض أي نموذج بيختار الـrouter بدون ما يشغّله.",
        "input_schema": {"type": "object", "properties": {
            "task_type": {"type": "string"}, "prompt_sample": {"type": "string"},
            "budget": {"type": "string", "enum": ["cheap", "balanced", "best"]},
        }, "required": []},
    },
]

ROUTER_TOOL_HANDLERS = {
    "smart_complete": tool_smart_complete,
    "router_stats": tool_router_stats,
    "router_route": tool_router_route,
}

ROUTER_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "smart_complete", "desc": "auto-routed completion", "args": ["prompt", "task_type?", "budget?"]},
    {"name": "router_stats", "desc": "cost analytics", "args": ["days?"]},
    {"name": "router_route", "desc": "preview which model", "args": ["task_type?", "prompt_sample?", "budget?"]},
]


def router_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in ROUTER_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return f"🤖✗ {(result.get('error') or '')[:120]}"
    if name == "smart_complete":
        return f"🤖 {result.get('model_used')} · ${result.get('cost_estimate_usd', 0):.5f}"
    if name == "router_stats":
        return f"📊 {result.get('days')}d · ${result.get('total_cost_usd', 0):.4f} · {len(result.get('breakdown', []))} models"
    if name == "router_route":
        return f"🧭 → {result.get('model')} (task: {result.get('classified_task')})"
    return None


def router_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in ROUTER_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return None
    if name == "router_route":
        return (f"النموذج المختار: {result.get('model')}\n"
                f"المزود: {result.get('provider')}\n"
                f"السبب: {result.get('reason')}\n"
                f"السلسلة: {' → '.join(result.get('ladder', []))}")
    if name == "router_stats":
        out = [f"إجمالي ${result.get('total_cost_usd', 0):.4f} في آخر {result.get('days')} يوم"]
        for b in (result.get("breakdown") or [])[:8]:
            out.append(f"  {b['model']:30s} · {b['task']:14s} · {b['calls']} call · ${b['cost_usd']:.4f}")
        return "\n".join(out)[:1500]
    if name == "smart_complete":
        return f"📥 chain: {' → '.join(result.get('fallback_chain', []))}\n📤 {result.get('content','')[:500]}"
    return None


ROUTER_PROMPT_RULES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Smart Model Router — وفّر التكلفة تلقائياً
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

عندنا 4 مزودين + 9 موديلات. كل مهمة لها سلم أرخص → أغلى:

  • coding         → Kimi K2.6 (0.73$/4$) → Claude → GPT-4o
  • long_context   → Kimi K2.6 (256K) → Gemini Flash → Claude
  • creative_write → Claude → GPT-4o → Kimi
  • reasoning_hard → GPT-5 → Claude → Kimi
  • quick_qa       → Gemini Flash (0.075$/0.3$) → Groq → GPT-4o-mini
  • vision         → Gemini Flash → GPT-4o → Kimi Vision
  • arabic         → Claude → GPT-4o → Gemini

استخدم `smart_complete(prompt, task_type, budget)` بدل ما تستدعي LLM مباشرة.
الـrouter يجرّب الأرخص → fallback تلقائي لو فشل/منتهي رصيده.

لو موقشوت موقوف ⇒ ينتقل لـClaude بدون ما تلاحظ.
لو Claude rate-limit ⇒ ينتقل لـGPT-4o.

استدعِ `router_stats` بشكل دوري عشان تشوف وين الفلوس تروح.
استدعِ `router_route` لو تبي تعرف وش الـrouter بيختار قبل ما يشغّل.
"""
