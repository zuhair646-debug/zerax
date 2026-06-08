/**
 * Live DOM Translator — translates EVERY visible Arabic/English text node
 * on the page into the chosen target language via the batch Claude endpoint.
 *
 * Strategy:
 *  - Walk the DOM, collect text nodes inside visible elements
 *  - Skip code blocks, scripts, styles, contenteditable inputs, and
 *    elements explicitly marked with data-no-translate="true"
 *  - Cache each (source, target) translation in localStorage forever
 *  - Use MutationObserver to translate new content as it appears
 *  - Store the ORIGINAL text in a data-orig attribute so we can restore
 *    when the user switches back to Arabic
 */
const API = process.env.REACT_APP_BACKEND_URL || '';
const CACHE_PREFIX = 'zitex_pt_';
const SKIP_TAGS = new Set([
  'SCRIPT', 'STYLE', 'CODE', 'PRE', 'TEXTAREA', 'INPUT',
  'NOSCRIPT', 'IFRAME', 'CANVAS', 'SVG', 'PATH',
]);
const MIN_LEN = 2;
const MAX_LEN = 240;

let observer = null;
let currentTarget = 'ar';
let translatingNow = false;

function cacheKey(src, target) {
  // Hash via base64 to keep localStorage key compact
  try {
    return CACHE_PREFIX + target + '_' + btoa(unescape(encodeURIComponent(src))).slice(0, 80);
  } catch (_) {
    return CACHE_PREFIX + target + '_' + encodeURIComponent(src).slice(0, 80);
  }
}

function shouldTranslateNode(node) {
  if (!node || node.nodeType !== 3) return false; // only text nodes
  const txt = (node.nodeValue || '').trim();
  if (txt.length < MIN_LEN || txt.length > MAX_LEN) return false;
  if (/^[\d\s.,:;\-+%$€£¥#@!*()<>[\]\\/|`~^&=_'"]+$/.test(txt)) return false; // pure punct/numbers
  let p = node.parentElement;
  while (p) {
    if (SKIP_TAGS.has(p.tagName)) return false;
    if (p.getAttribute && p.getAttribute('data-no-translate') === 'true') return false;
    if (p.isContentEditable) return false;
    p = p.parentElement;
  }
  return true;
}

function collectTextNodes(root) {
  const out = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (shouldTranslateNode(n) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT),
  });
  let cur;
  while ((cur = walker.nextNode())) out.push(cur);
  return out;
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

/** Translate the page (or a subtree) into `target`. */
async function translateRoot(root, target) {
  if (target === 'ar') {
    // Restore originals
    const nodes = collectTextNodes(root);
    nodes.forEach((n) => {
      const orig = n.parentElement && n.parentElement.getAttribute('data-orig-' + (n.dataset?.__idx || '0'));
      // Fallback simpler restore: every translated node stores its original in a sibling-like map
    });
    // Simpler: just reload to restore originals
    if (currentTarget !== 'ar') window.location.reload();
    return;
  }

  const nodes = collectTextNodes(root);
  if (!nodes.length) return;

  // Group by unique original text — many duplicates across the DOM (buttons, labels)
  const uniq = new Map(); // origText -> [node, node, ...]
  for (const n of nodes) {
    const origText = (n.__zitexOrig || n.nodeValue || '').trim();
    if (!n.__zitexOrig) n.__zitexOrig = origText;
    if (!uniq.has(origText)) uniq.set(origText, []);
    uniq.get(origText).push(n);
  }

  // Resolve from cache first, queue the rest
  const toFetch = [];
  for (const [src] of uniq) {
    const cached = localStorage.getItem(cacheKey(src, target));
    if (cached) {
      uniq.get(src).forEach((n) => { n.nodeValue = cached; });
    } else {
      toFetch.push(src);
    }
  }

  if (toFetch.length === 0) return;

  // Fetch in chunks of 40
  const chunkSize = 40;
  for (let i = 0; i < toFetch.length; i += chunkSize) {
    const chunk = toFetch.slice(i, i + chunkSize);
    const translations = await fetchBatch(chunk, target);
    if (!translations) continue;
    chunk.forEach((src, j) => {
      const out = translations[j];
      if (out && out !== src) {
        localStorage.setItem(cacheKey(src, target), out);
        (uniq.get(src) || []).forEach((n) => { n.nodeValue = out; });
      }
    });
  }
}

/** Public entry: kick off live translation of the whole page. */
export async function applyPageLanguage(targetCode) {
  if (translatingNow) return;
  // Avoid no-op work on first boot when target equals the page's native language
  if (targetCode === currentTarget) return;
  const previousTarget = currentTarget;
  translatingNow = true;
  currentTarget = targetCode;
  try {
    if (observer) { observer.disconnect(); observer = null; }
    // Going BACK to Arabic from another language → reload so all originals
    // are restored cleanly (avoids tracking inverse mappings node-by-node).
    // Only reload when we actually had a non-Arabic target before.
    if (targetCode === 'ar' && previousTarget !== 'ar') {
      window.location.reload();
      return;
    }
    // First boot or target is Arabic and we never left Arabic — nothing to do
    if (targetCode === 'ar') return;
    await translateRoot(document.body, targetCode);
    // Watch for new content (route changes, modals, async-loaded sections)
    observer = new MutationObserver((muts) => {
      const added = [];
      for (const m of muts) {
        m.addedNodes && m.addedNodes.forEach((n) => {
          if (n.nodeType === 1) added.push(n);
        });
      }
      if (added.length === 0) return;
      clearTimeout(observer.__pendingTimer);
      observer.__pendingTimer = setTimeout(() => {
        added.forEach((node) => translateRoot(node, currentTarget));
      }, 220);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  } finally {
    translatingNow = false;
  }
}
