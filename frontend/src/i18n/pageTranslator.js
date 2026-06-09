/**
 * Live DOM Translator for Zerax
 * ------------------------------------------------------------------
 * Translates EVERY visible Arabic/English text node on the page into
 * the user's chosen language via the batch Claude endpoint.
 *
 * Key behaviours:
 *  - Walks the DOM, collects text nodes inside visible elements only
 *  - Skips code, scripts, styles, inputs, contenteditable, and any
 *    element/subtree marked with data-no-translate="true"
 *  - Caches each (source -> target) translation in localStorage forever
 *  - Uses a MutationObserver to translate new content as it appears
 *    AND to re-apply translations when React replaces nodeValue back to
 *    the original Arabic during re-renders (super common cause of
 *    "translation disappears after typing")
 *  - Stores the ORIGINAL text in a WeakMap so we can restore instantly
 *    when the user switches back to Arabic (no full page reload)
 *  - Self-mutation guard prevents infinite observer loops
 */

const API = process.env.REACT_APP_BACKEND_URL || '';
const CACHE_PREFIX = 'zerax_pt_';
const SKIP_TAGS = new Set([
  'SCRIPT', 'STYLE', 'CODE', 'PRE', 'TEXTAREA', 'INPUT',
  'NOSCRIPT', 'IFRAME', 'CANVAS', 'SVG', 'PATH', 'KBD', 'SAMP',
]);
const MIN_LEN = 2;
const MAX_LEN = 280;
const BATCH_SIZE = 35;
const DEBOUNCE_MS = 250;

// State
let observer = null;
let currentTarget = 'ar';  // page native language
let scheduleTimer = null;
let pendingNodes = new Set();
let isApplying = false;     // true while we mutate the DOM ourselves
// Track original text per node so we can:
//  (a) re-apply translation if React resets it to the original
//  (b) restore originals instantly when switching back to 'ar'
const originalOf = new WeakMap();
// Track current applied translation per node (so we know when React reset it)
const currentOf = new WeakMap();
// In-memory mirror of localStorage for synchronous lookups
const memCache = new Map(); // `${target}::${src}` -> translated

// -------- cache helpers --------
function memKey(src, target) {
  return target + '::' + src;
}

function cacheKey(src, target) {
  try {
    return CACHE_PREFIX + target + '_' + btoa(unescape(encodeURIComponent(src))).slice(0, 96);
  } catch (_) {
    return CACHE_PREFIX + target + '_' + encodeURIComponent(src).slice(0, 96);
  }
}

function cacheGet(src, target) {
  const k = memKey(src, target);
  if (memCache.has(k)) return memCache.get(k);
  try {
    const v = localStorage.getItem(cacheKey(src, target));
    if (v) memCache.set(k, v);
    return v;
  } catch (_) {
    return null;
  }
}

function cacheSet(src, target, value) {
  memCache.set(memKey(src, target), value);
  try { localStorage.setItem(cacheKey(src, target), value); } catch (_) { /* quota */ }
}

// -------- DOM helpers --------
function shouldTranslateNode(node) {
  if (!node || node.nodeType !== 3) return false; // text nodes only
  const raw = node.nodeValue || '';
  const txt = raw.trim();
  if (txt.length < MIN_LEN || txt.length > MAX_LEN) return false;
  // Skip pure numbers / punctuation / single emoji
  if (/^[\d\s.,:;\-+%$€£¥#@!*()<>[\]\\/|`~^&=_'"©®™•·…]+$/.test(txt)) return false;
  // Skip strings that are ONLY emoji
  if (/^(\p{Extended_Pictographic}|\s)+$/u.test(txt)) return false;
  let p = node.parentElement;
  while (p) {
    if (SKIP_TAGS.has(p.tagName)) return false;
    if (p.hasAttribute && p.hasAttribute('data-no-translate')) return false;
    if (p.isContentEditable) return false;
    p = p.parentElement;
  }
  return true;
}

function collectTextNodes(root) {
  if (!root) return [];
  // If root is a text node, just check it directly
  if (root.nodeType === 3) return shouldTranslateNode(root) ? [root] : [];
  const out = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (shouldTranslateNode(n) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT),
  });
  let cur;
  while ((cur = walker.nextNode())) out.push(cur);
  return out;
}

function setNodeValue(node, value) {
  isApplying = true;
  try { node.nodeValue = value; } finally {
    // Release on next microtask so the observer callback for this very
    // mutation fires while the flag is still true, then resets cleanly.
    queueMicrotask(() => { isApplying = false; });
  }
}

// -------- API --------
// Track in-flight fetches so we never request the same string twice
// concurrently (multiple overlapping sweeps were saturating the proxy
// connection pool and starving all but the last call).
const inflight = new Map(); // `${target}::${src}` -> Promise<string|null>
let sweepRunning = false;

async function fetchOneCached(src, target) {
  // 1) memCache / localStorage
  const c = cacheGet(src, target);
  if (c) return c;
  // 2) in-flight de-dup
  const k = memKey(src, target);
  if (inflight.has(k)) return inflight.get(k);
  // 3) launch a single-string fetch is too expensive — we batch in callers
  return null;
}

async function fetchBatch(texts, target) {
  try {
    const r = await fetch(`${API}/api/i18n/translate-batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts, target }),
    });
    if (!r.ok) return null;
    const d = await r.json();
    return Array.isArray(d.translations) ? d.translations : null;
  } catch (_) {
    return null;
  }
}

// -------- core: translate a list of nodes into `target` --------
async function translateNodes(nodes, target) {
  if (!nodes.length || target === currentTarget && currentTarget !== 'ar') {
    // currentTarget already reflects desired language and we're not just
    // resetting; nothing to do for these specific nodes that are already
    // shown in the target language.
  }
  // Group identical source strings together (a UI repeats labels a lot)
  // Source = the ORIGINAL text we first saw for this node.
  const groups = new Map(); // src -> Node[]
  for (const n of nodes) {
    if (!shouldTranslateNode(n)) continue;
    const orig = originalOf.get(n) || (n.nodeValue || '').trim();
    if (!orig) continue;
    if (!originalOf.has(n)) originalOf.set(n, orig);
    if (!groups.has(orig)) groups.set(orig, []);
    groups.get(orig).push(n);
  }

  if (target === 'ar') {
    // Restore originals instantly — no API call needed
    for (const [src, list] of groups) {
      for (const n of list) {
        if (n.nodeValue !== src) setNodeValue(n, src);
        currentOf.set(n, src);
      }
    }
    return;
  }

  // Apply cached translations first; collect uncached unique sources
  const toFetch = [];
  for (const [src, list] of groups) {
    const cached = cacheGet(src, target);
    if (cached) {
      for (const n of list) {
        if (n.nodeValue !== cached) setNodeValue(n, cached);
        currentOf.set(n, cached);
      }
    } else {
      toFetch.push(src);
    }
  }

  if (!toFetch.length) return;

  // Filter out strings already being fetched by a concurrent call.
  // For those, just await the existing promise instead of issuing a
  // duplicate request (this is what saturated the proxy).
  const reallyNeed = [];
  const awaitingExisting = [];
  for (const src of toFetch) {
    const k = memKey(src, target);
    if (inflight.has(k)) {
      awaitingExisting.push({ src, p: inflight.get(k) });
    } else {
      reallyNeed.push(src);
    }
  }

  // Issue one merged batch for everything that isn't already in flight.
  const chunks = [];
  for (let i = 0; i < reallyNeed.length; i += BATCH_SIZE) {
    chunks.push(reallyNeed.slice(i, i + BATCH_SIZE));
  }

  await Promise.all(chunks.map(async (chunk) => {
    // Register this chunk as in-flight so a sibling sweep skips it
    const chunkPromise = fetchBatch(chunk, target);
    chunk.forEach((src) => inflight.set(memKey(src, target), chunkPromise.then((arr) => {
      if (!arr) return null;
      const idx = chunk.indexOf(src);
      return idx >= 0 ? (arr[idx] || null) : null;
    })));
    try {
      const translations = await chunkPromise;
      if (translations) {
        chunk.forEach((src, j) => {
          const out = (translations[j] || '').trim();
          if (!out || out === src) return;
          cacheSet(src, target, out);
          const list = groups.get(src) || [];
          for (const n of list) {
            if (n.nodeValue !== out) setNodeValue(n, out);
            currentOf.set(n, out);
          }
        });
      }
    } finally {
      // Always clear in-flight entries (success or fail) so future
      // sweeps can retry if needed.
      chunk.forEach((src) => inflight.delete(memKey(src, target)));
    }
  }));

  // For strings that were already in flight when we started, await
  // their result and apply it to our local groups too.
  await Promise.all(awaitingExisting.map(async ({ src, p }) => {
    const out = await p;
    if (!out || out === src) return;
    cacheSet(src, target, out);
    const list = groups.get(src) || [];
    for (const n of list) {
      if (n.nodeValue !== out) setNodeValue(n, out);
      currentOf.set(n, out);
    }
  }));
}

// -------- queue + debounce --------
function schedule(nodes) {
  for (const n of nodes) pendingNodes.add(n);
  if (scheduleTimer) clearTimeout(scheduleTimer);
  scheduleTimer = setTimeout(flush, DEBOUNCE_MS);
}

async function flush() {
  scheduleTimer = null;
  const batch = Array.from(pendingNodes);
  pendingNodes.clear();
  if (!batch.length) return;
  await translateNodes(batch, currentTarget);
}

// -------- observer --------
function startObserver() {
  if (observer) return;
  observer = new MutationObserver((mutations) => {
    if (isApplying) return; // our own writes — ignore
    const fresh = [];
    for (const m of mutations) {
      if (m.type === 'childList') {
        m.addedNodes && m.addedNodes.forEach((node) => {
          if (node.nodeType === 3) {
            fresh.push(node);
          } else if (node.nodeType === 1) {
            fresh.push(...collectTextNodes(node));
          }
        });
      } else if (m.type === 'characterData') {
        const node = m.target;
        if (node && node.nodeType === 3) {
          // React often resets nodeValue back to the original source string
          // during re-renders. If we already know a translation for this
          // original, re-apply it from cache instantly (no API call).
          const orig = originalOf.get(node);
          const applied = currentOf.get(node);
          if (orig && applied && node.nodeValue === orig && currentTarget !== 'ar') {
            const cached = cacheGet(orig, currentTarget);
            if (cached) {
              setNodeValue(node, cached);
              continue;
            }
          }
          // Otherwise treat as a new node to translate
          if (shouldTranslateNode(node)) fresh.push(node);
        }
      }
    }
    if (fresh.length) schedule(fresh);
  });
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
  });
}

function stopObserver() {
  if (observer) { observer.disconnect(); observer = null; }
  if (scheduleTimer) { clearTimeout(scheduleTimer); scheduleTimer = null; }
  pendingNodes.clear();
}

// -------- public entry --------
let initialBoot = true;
let scrollHandler = null;
let scrollDebounce = null;

function attachScrollSweep() {
  if (scrollHandler) return;
  scrollHandler = () => {
    if (scrollDebounce) clearTimeout(scrollDebounce);
    scrollDebounce = setTimeout(() => sweepAndTranslate(), 180);
  };
  window.addEventListener('scroll', scrollHandler, { passive: true });
  // Also catch resize / orientation as they can reveal lazy content
  window.addEventListener('resize', scrollHandler, { passive: true });
}

export async function applyPageLanguage(targetCode) {
  if (!targetCode) return;
  // On very first call we just record the current language; nothing to
  // translate yet because the page is already in its native (Arabic).
  if (initialBoot) {
    initialBoot = false;
    currentTarget = targetCode;
    // Even on first boot, if user previously chose a non-Arabic language
    // (persisted in localStorage), translate the page now.
    if (targetCode !== 'ar') {
      stopObserver();
      const all = collectTextNodes(document.body);
      await translateNodes(all, targetCode);
      startObserver();
      // A few staggered sweeps catch Hero/Carousel/cards that React
      // renders asynchronously (route lazy-load, intersection reveals).
      setTimeout(() => sweepAndTranslate(), 600);
      setTimeout(() => sweepAndTranslate(), 1800);
      setTimeout(() => sweepAndTranslate(), 4000);
      setTimeout(() => sweepAndTranslate(), 8000);
      setTimeout(() => sweepAndTranslate(), 13000);
    } else {
      startObserver();
    }
    attachScrollSweep();
    return;
  }

  // Allow re-running with the same language to catch newly-rendered
  // content (the early `return` here was the cause of "language change
  // doesn't update everything until I refresh").
  currentTarget = targetCode;
  stopObserver();
  const all = collectTextNodes(document.body);
  await translateNodes(all, targetCode);
  startObserver();
  // Re-sweep several times after a change to catch lazy / off-screen
  // / re-rendered content + safety nets for slow Claude responses.
  setTimeout(() => sweepAndTranslate(), 400);
  setTimeout(() => sweepAndTranslate(), 1200);
  setTimeout(() => sweepAndTranslate(), 2800);
  setTimeout(() => sweepAndTranslate(), 5500);
  setTimeout(() => sweepAndTranslate(), 9000);
  setTimeout(() => sweepAndTranslate(), 14000);
  attachScrollSweep();
}

/** Re-scan the entire document.body and translate anything still in
 *  the source language. Cheap because cached strings are O(1) and we
 *  only hit the API for genuinely new text. Single-flight: if a sweep
 *  is already running, this call is queued (one slot only). */
let sweepQueued = false;
async function sweepAndTranslate() {
  if (!currentTarget) return;
  if (sweepRunning) { sweepQueued = true; return; }
  sweepRunning = true;
  try {
    do {
      sweepQueued = false;
      const all = collectTextNodes(document.body);
      if (all.length) await translateNodes(all, currentTarget);
    } while (sweepQueued);
  } finally {
    sweepRunning = false;
  }
}

// Exported for debugging in the browser console
if (typeof window !== 'undefined') {
  window.__zeraxI18n = {
    apply: applyPageLanguage,
    clearCache: () => {
      memCache.clear();
      try {
        Object.keys(localStorage).forEach((k) => {
          if (k.startsWith(CACHE_PREFIX)) localStorage.removeItem(k);
        });
      } catch (_) { /* */ }
    },
  };
}
