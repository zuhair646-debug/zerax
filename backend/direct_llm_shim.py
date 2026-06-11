"""
Direct LLM Shim — Drop-in replacement for emergentintegrations.llm.chat
─────────────────────────────────────────────────────────────────────────
Mimics the LlmChat / UserMessage / FileContent / ImageContent API so the
existing 20+ codebase files keep working unchanged, but internally routes
all calls to DIRECT provider SDKs using the user's own API keys.

This lets the platform run 100% independently of Emergent's universal key,
which is critical when deployed to an external VPS (Hetzner) where the
Free-tier universal key returns 403.

Providers routed:
  • "anthropic" → anthropic.AsyncAnthropic            (ANTHROPIC_API_KEY)
  • "gemini"    → google.genai.Client (async)         (GEMINI_API_KEY)
  • "openai"    → openai.AsyncOpenAI                  (OPENAI_DIRECT_KEY or OPENAI_API_KEY)

Module install path (server.py registers it):
    sys.modules['emergentintegrations.llm.chat'] = direct_llm_shim
"""
from __future__ import annotations

import os
import json
import base64
import logging
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("direct_llm_shim")

# ────────────────────────────────────────────────────────────────────────
# Message types
# ────────────────────────────────────────────────────────────────────────
class FileContent:
    def __init__(self, content_type: str, file_content_base64: str):
        self.content_type = content_type
        self.file_content_base64 = file_content_base64


class ImageContent(FileContent):
    """Convenience subclass — image-only file content."""
    def __init__(self, image_base64: str, mime_type: str = "image/png"):
        super().__init__(content_type=mime_type, file_content_base64=image_base64)


class UserMessage:
    def __init__(self, text: Optional[str] = None, file_contents: Optional[List[FileContent]] = None):
        self.text = text or ""
        self.file_contents = file_contents or []


# In-process per-session conversation memory (mirrors LlmChat behavior)
_SESSIONS: Dict[str, List[Dict[str, Any]]] = {}


# ────────────────────────────────────────────────────────────────────────
# Model name normalization (handle older snapshot tags gracefully)
# ────────────────────────────────────────────────────────────────────────
_ANTHROPIC_DEFAULT = os.environ.get("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-5")
_GEMINI_DEFAULT_TEXT = os.environ.get("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash")
_GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
_OPENAI_DEFAULT = os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-4o")


def _normalize_model(provider: str, model: str) -> str:
    """Map legacy/snapshot model names to the latest stable equivalent."""
    if provider == "anthropic":
        # Pass through; SDK supports claude-sonnet-4-5, claude-sonnet-4-6, etc.
        # If model contains a date suffix, strip to canonical alias.
        if model and model.startswith("claude-sonnet-4-5"):
            return "claude-sonnet-4-5"
        if model and model.startswith("claude-sonnet-4-6"):
            return "claude-sonnet-4-6"
        if model and model.startswith("claude-opus"):
            return "claude-opus-4-1" if "4-1" in model else "claude-opus-4-1"
        if model and model.startswith("claude-haiku"):
            return "claude-haiku-4-5"
        return model or _ANTHROPIC_DEFAULT
    if provider == "gemini":
        if model and ("image" in model.lower() or "nano-banana" in model.lower() or "banana" in model.lower()):
            return _GEMINI_IMAGE_MODEL
        return model or _GEMINI_DEFAULT_TEXT
    if provider == "openai":
        return model or _OPENAI_DEFAULT
    return model


# ────────────────────────────────────────────────────────────────────────
# Provider call implementations
# ────────────────────────────────────────────────────────────────────────
async def _call_anthropic(model: str, system: str, messages: List[Dict[str, Any]], extra: Dict[str, Any]) -> str:
    """Direct Anthropic Claude call."""
    from anthropic import AsyncAnthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = AsyncAnthropic(api_key=api_key)

    # Convert our flat history into Anthropic format
    msgs = []
    for m in messages:
        if m["role"] == "system":
            continue  # handled separately
        content = m.get("content")
        if isinstance(content, list):
            msgs.append({"role": m["role"], "content": content})
        else:
            msgs.append({"role": m["role"], "content": str(content)})

    resp = await client.messages.create(
        model=model,
        max_tokens=extra.get("max_tokens", 4096),
        system=system or "You are a helpful assistant.",
        messages=msgs,
    )
    # Combine all text blocks
    out = []
    for block in resp.content:
        if hasattr(block, "text"):
            out.append(block.text)
    return "".join(out)


async def _call_gemini_text(model: str, system: str, messages: List[Dict[str, Any]], extra: Dict[str, Any]) -> str:
    """Direct Google Gemini text call."""
    from google import genai
    from google.genai import types
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    client = genai.Client(api_key=api_key)

    # Build conversation contents
    contents = []
    for m in messages:
        if m["role"] == "system":
            continue
        role = "user" if m["role"] == "user" else "model"
        c = m.get("content")
        if isinstance(c, list):
            # Multimodal parts
            parts = []
            for part in c:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        parts.append(types.Part.from_text(text=part["text"]))
                    elif part.get("type") in ("image", "image_url"):
                        # part may carry inline base64 data
                        b64 = part.get("data") or part.get("image_base64") or ""
                        mime = part.get("mime_type") or "image/png"
                        if b64:
                            parts.append(types.Part.from_bytes(data=base64.b64decode(b64), mime_type=mime))
                else:
                    parts.append(types.Part.from_text(text=str(part)))
            contents.append(types.Content(role=role, parts=parts))
        else:
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=str(c))]))

    cfg = types.GenerateContentConfig(
        system_instruction=system or None,
        max_output_tokens=extra.get("max_tokens", 4096),
    )
    resp = await client.aio.models.generate_content(model=model, contents=contents, config=cfg)
    return resp.text or ""


async def _call_gemini_multimodal(model: str, system: str, messages: List[Dict[str, Any]], extra: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    """Gemini call that returns BOTH text and generated images (Nano Banana)."""
    from google import genai
    from google.genai import types
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    client = genai.Client(api_key=api_key)

    # Build contents from the latest user message (image gen is typically one-shot)
    contents = []
    for m in messages:
        if m["role"] == "system":
            continue
        role = "user" if m["role"] == "user" else "model"
        c = m.get("content")
        if isinstance(c, list):
            parts = []
            for part in c:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        parts.append(types.Part.from_text(text=part["text"]))
                    elif part.get("type") in ("image", "image_url"):
                        b64 = part.get("data") or part.get("image_base64") or ""
                        mime = part.get("mime_type") or "image/png"
                        if b64:
                            parts.append(types.Part.from_bytes(data=base64.b64decode(b64), mime_type=mime))
                else:
                    parts.append(types.Part.from_text(text=str(part)))
            contents.append(types.Content(role=role, parts=parts))
        else:
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=str(c))]))

    cfg = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        max_output_tokens=extra.get("max_tokens", 4096),
    )
    if system:
        cfg.system_instruction = system

    resp = await client.aio.models.generate_content(model=model, contents=contents, config=cfg)

    text_out = ""
    images: List[Dict[str, str]] = []
    for cand in resp.candidates or []:
        if not cand.content or not cand.content.parts:
            continue
        for part in cand.content.parts:
            if getattr(part, "text", None):
                text_out += part.text
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                raw = inline.data
                if isinstance(raw, bytes):
                    b64 = base64.b64encode(raw).decode("ascii")
                else:
                    b64 = str(raw)
                images.append({
                    "mime_type": getattr(inline, "mime_type", "image/png"),
                    "data": b64,
                })
    return text_out, images


async def _call_openai(model: str, system: str, messages: List[Dict[str, Any]], extra: Dict[str, Any]) -> str:
    """Direct OpenAI Chat Completions call."""
    from openai import AsyncOpenAI
    api_key = os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_DIRECT_KEY/OPENAI_API_KEY not set")
    client = AsyncOpenAI(api_key=api_key)

    chat_msgs = []
    if system:
        chat_msgs.append({"role": "system", "content": system})
    for m in messages:
        if m["role"] == "system":
            continue
        c = m.get("content")
        if isinstance(c, list):
            # OpenAI multimodal format
            parts = []
            for part in c:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        parts.append({"type": "text", "text": part["text"]})
                    elif part.get("type") in ("image", "image_url"):
                        b64 = part.get("data") or part.get("image_base64") or ""
                        mime = part.get("mime_type") or "image/png"
                        if b64:
                            parts.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{b64}"},
                            })
            chat_msgs.append({"role": m["role"], "content": parts})
        else:
            chat_msgs.append({"role": m["role"], "content": str(c)})

    resp = await client.chat.completions.create(
        model=model,
        messages=chat_msgs,
        max_tokens=extra.get("max_tokens", 4096),
    )
    return resp.choices[0].message.content or ""


# ────────────────────────────────────────────────────────────────────────
# LlmChat — drop-in interface for emergentintegrations.llm.chat.LlmChat
# ────────────────────────────────────────────────────────────────────────
class LlmChat:
    def __init__(
        self,
        api_key: str,
        session_id: str,
        system_message: str,
        initial_messages: Optional[List[Dict[str, Any]]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ):
        # api_key is IGNORED — we use direct provider keys from env.
        self._session_id = session_id
        self._system = system_message or ""
        self._provider = "gemini"
        self._model = _GEMINI_DEFAULT_TEXT
        self._params: Dict[str, Any] = {}
        # Restore prior history if exists
        _SESSIONS.setdefault(session_id, [])
        if initial_messages:
            _SESSIONS[session_id].extend(initial_messages)

    def with_model(self, provider: str, model: str) -> "LlmChat":
        self._provider = (provider or "gemini").lower()
        self._model = _normalize_model(self._provider, model)
        return self

    def with_params(self, **kwargs: Any) -> "LlmChat":
        self._params.update(kwargs)
        return self

    async def get_messages(self) -> List[Dict[str, Any]]:
        return list(_SESSIONS.get(self._session_id, []))

    def _build_user_content(self, user_message: UserMessage) -> Any:
        """Build content (str or list) from UserMessage."""
        if not user_message.file_contents:
            return user_message.text or ""
        parts: List[Dict[str, Any]] = []
        if user_message.text:
            parts.append({"type": "text", "text": user_message.text})
        for fc in user_message.file_contents:
            parts.append({
                "type": "image",
                "mime_type": fc.content_type,
                "data": fc.file_content_base64,
            })
        return parts

    async def _dispatch(self, messages: List[Dict[str, Any]]) -> str:
        prov = self._provider
        model = self._model
        if prov == "anthropic":
            return await _call_anthropic(model, self._system, messages, self._params)
        if prov == "openai":
            return await _call_openai(model, self._system, messages, self._params)
        # default: gemini
        return await _call_gemini_text(model, self._system, messages, self._params)

    async def send_message(self, user_message: UserMessage) -> str:
        history = _SESSIONS.setdefault(self._session_id, [])
        history.append({"role": "user", "content": self._build_user_content(user_message)})
        try:
            text = await self._dispatch(history)
        except Exception as e:
            # Fallback chain: claude → gemini → openai
            log.warning(f"[shim] primary provider {self._provider}/{self._model} failed: {e} — trying fallback")
            text = await self._fallback_dispatch(history, failed_provider=self._provider)
        history.append({"role": "assistant", "content": text})
        return text

    async def _fallback_dispatch(self, history: List[Dict[str, Any]], failed_provider: str) -> str:
        chain = [p for p in ("anthropic", "gemini", "openai") if p != failed_provider]
        last_err: Optional[Exception] = None
        for prov in chain:
            try:
                if prov == "anthropic":
                    return await _call_anthropic(_ANTHROPIC_DEFAULT, self._system, history, self._params)
                if prov == "gemini":
                    return await _call_gemini_text(_GEMINI_DEFAULT_TEXT, self._system, history, self._params)
                if prov == "openai":
                    return await _call_openai(_OPENAI_DEFAULT, self._system, history, self._params)
            except Exception as e:
                last_err = e
                log.warning(f"[shim] fallback {prov} also failed: {e}")
        raise last_err or RuntimeError("All LLM providers failed")

    async def send_message_multimodal_response(self, user_message: UserMessage) -> Tuple[str, List[Dict[str, str]]]:
        """Send message expecting BOTH text and image responses (Nano Banana)."""
        history = _SESSIONS.setdefault(self._session_id, [])
        history.append({"role": "user", "content": self._build_user_content(user_message)})
        # For image generation, always route through Gemini multimodal
        model = self._model if "image" in (self._model or "").lower() else _GEMINI_IMAGE_MODEL
        try:
            text, images = await _call_gemini_multimodal(model, self._system, history, self._params)
        except Exception as e:
            log.error(f"[shim] multimodal generation failed: {e}")
            raise
        if text:
            history.append({"role": "assistant", "content": text})
        return text, images


# ────────────────────────────────────────────────────────────────────────
# Public re-exports (mirror emergentintegrations.llm.chat)
# ────────────────────────────────────────────────────────────────────────
__all__ = ["LlmChat", "UserMessage", "FileContent", "ImageContent"]
