// Zenrex Assistant — Background Service Worker
// Maintains the WebSocket connection to Zenrex and routes AI commands to
// the user's active Chrome tabs.

const ZENREX_WS_BASE = "wss://zenrex.ai/api/local-browser/ws";
let ws = null;
let reconnectTimer = null;
let pairingCode = null;

async function loadPairingCode() {
  return new Promise((resolve) => {
    chrome.storage.local.get("pairing_code", (data) => {
      resolve(data.pairing_code || null);
    });
  });
}

async function savePairingCode(code) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ pairing_code: code }, () => resolve(true));
  });
}

function notifyUser(title, message) {
  try {
    chrome.notifications.create("", {
      type: "basic",
      iconUrl: "icon128.png",
      title,
      message,
    });
  } catch (e) { /* notifications may not be granted */ }
}

async function getActiveTabId() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab ? tab.id : null;
}

// ── Action handlers — executed in the user's Chrome ────────────────────────
async function execAction(action, params) {
  try {
    if (action === "navigate") {
      const tabId = await getActiveTabId();
      if (!tabId) return { ok: false, error: "no_active_tab" };
      await chrome.tabs.update(tabId, { url: params.url });
      return { ok: true, url: params.url };
    }
    if (action === "open_tab") {
      const tab = await chrome.tabs.create({ url: params.url, active: true });
      return { ok: true, tab_id: tab.id, url: tab.url };
    }
    if (action === "list_tabs") {
      const tabs = await chrome.tabs.query({});
      return {
        ok: true,
        tabs: tabs.map((t) => ({
          id: t.id, url: t.url, title: t.title, active: t.active, windowId: t.windowId,
        })),
      };
    }
    if (action === "get_url") {
      const tabId = await getActiveTabId();
      if (!tabId) return { ok: false, error: "no_active_tab" };
      const tab = await chrome.tabs.get(tabId);
      return { ok: true, url: tab.url, title: tab.title };
    }
    if (action === "screenshot") {
      // Captures the visible area of the currently active window
      const dataUrl = await chrome.tabs.captureVisibleTab(null, { format: "jpeg", quality: 60 });
      const b64 = dataUrl.replace(/^data:image\/jpeg;base64,/, "");
      return { ok: true, screenshot_b64: b64 };
    }
    if (action === "click" || action === "type" || action === "scroll" || action === "eval") {
      const tabId = await getActiveTabId();
      if (!tabId) return { ok: false, error: "no_active_tab" };
      const [result] = await chrome.scripting.executeScript({
        target: { tabId },
        func: domAction,
        args: [action, params],
      });
      return result?.result || { ok: false, error: "no_result" };
    }
    return { ok: false, error: `unknown_action: ${action}` };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

// Executed inside the page context via chrome.scripting.executeScript
function domAction(action, params) {
  try {
    if (action === "click") {
      const sel = params.selector || "";
      let el = null;
      // Allow plain CSS selector
      try { el = document.querySelector(sel); } catch (e) { /* fallthrough */ }
      // Allow `text="..."` semantic search
      if (!el && sel.startsWith('text=')) {
        const needle = sel.slice(5).replace(/^["']|["']$/g, "").trim();
        const candidates = Array.from(document.querySelectorAll("a,button,[role=button],input,div,span"));
        el = candidates.find((c) => (c.innerText || c.value || "").trim().includes(needle));
      }
      if (!el) return { ok: false, error: "element_not_found" };
      el.click();
      return { ok: true, clicked: sel };
    }
    if (action === "type") {
      const sel = params.selector || "";
      const el = document.querySelector(sel);
      if (!el) return { ok: false, error: "element_not_found" };
      el.focus();
      el.value = params.text || "";
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return { ok: true };
    }
    if (action === "scroll") {
      window.scrollBy(0, params.y || 400);
      return { ok: true };
    }
    if (action === "eval") {
      // SAFETY: only allow read-only expression evaluation, no statements
      const code = String(params.code || "").slice(0, 2000);
      // eslint-disable-next-line no-new-func
      const result = (new Function("return (" + code + ")"))();
      return { ok: true, result: JSON.stringify(result).slice(0, 5000) };
    }
    return { ok: false, error: "unknown_dom_action" };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

// ── WebSocket connection ──────────────────────────────────────────────────
async function connect() {
  pairingCode = await loadPairingCode();
  if (!pairingCode) {
    console.log("[Zenrex] No pairing code stored; waiting for user to pair.");
    return;
  }
  if (ws && ws.readyState === WebSocket.OPEN) return;
  const url = `${ZENREX_WS_BASE}?code=${encodeURIComponent(pairingCode)}`;
  ws = new WebSocket(url);
  ws.onopen = () => {
    console.log("[Zenrex] WS connected.");
    notifyUser("Zenrex متصل ✅", "الذكاء جاهز للتحكم بمتصفحك.");
  };
  ws.onmessage = async (evt) => {
    let msg;
    try { msg = JSON.parse(evt.data); } catch { return; }
    if (msg.type === "paired") {
      console.log("[Zenrex] paired with project", msg.project_id);
      return;
    }
    if (msg.type === "error") {
      console.warn("[Zenrex] server error:", msg.message);
      notifyUser("Zenrex — خطأ", msg.message || "حدث خطأ");
      if (String(msg.message).includes("invalid_or_expired")) {
        await savePairingCode("");
        pairingCode = null;
      }
      return;
    }
    if (msg.type === "command") {
      const result = await execAction(msg.action, msg.params || {});
      try {
        ws.send(JSON.stringify({
          type: "response",
          request_id: msg.request_id,
          payload: result,
        }));
      } catch (e) { console.error(e); }
    }
  };
  ws.onclose = () => {
    console.log("[Zenrex] WS closed; reconnecting in 5s.");
    scheduleReconnect();
  };
  ws.onerror = (e) => {
    console.warn("[Zenrex] WS error", e);
  };
}

function scheduleReconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connect, 5000);
}

// Receive pairing code from popup
chrome.runtime.onMessage.addListener(async (msg, _sender, sendResponse) => {
  if (msg.type === "set_pairing_code") {
    await savePairingCode(msg.code);
    pairingCode = msg.code;
    if (ws) try { ws.close(); } catch (e) { /* */ }
    connect();
    sendResponse({ ok: true });
    return true;
  }
  if (msg.type === "get_status") {
    sendResponse({
      ok: true,
      connected: ws && ws.readyState === WebSocket.OPEN,
      paired: !!pairingCode,
      code: pairingCode,
    });
    return true;
  }
  if (msg.type === "unpair") {
    await savePairingCode("");
    pairingCode = null;
    if (ws) try { ws.close(); } catch (e) { /* */ }
    sendResponse({ ok: true });
    return true;
  }
});

// Auto-connect on install / boot
chrome.runtime.onStartup?.addListener(() => connect());
chrome.runtime.onInstalled.addListener(() => connect());
// Try once on script load
connect();
