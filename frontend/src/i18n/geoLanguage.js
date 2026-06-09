/**
 * Geo + Browser Language Auto-Detect
 * --------------------------------------------------------------
 * Picks the best initial language for a visitor in 3 layers:
 *   1. Manual override   — if the user ever picked a language from the
 *                          LanguagePicker, we ALWAYS honor that choice
 *                          (stored in localStorage as `zerax_lang_manual`).
 *   2. Browser language  — navigator.language (instant, no network).
 *   3. IP geolocation    — ipapi.co (free, CORS-enabled) — runs in the
 *                          background and upgrades the choice when the
 *                          visitor's geographic country implies a
 *                          different language than the browser ships.
 *
 * Exposes:
 *   getInitialLanguage()              — synchronous pick for i18next init
 *   detectGeoLanguageInBackground(cb) — async; calls cb(code) if it has a
 *                                        better guess than the current one
 *   markManualChoice(code)            — call when the user picks from UI
 *   hasManualChoice()                 — whether the user already chose
 */

import { LANG_BY_CODE } from './languages';

// ISO-3166 country → primary language ISO 639-1 we support.
// Curated for the languages in WORLD_LANGUAGES.
const COUNTRY_TO_LANG = {
  // Arabic-speaking
  SA: 'ar', AE: 'ar', EG: 'ar', KW: 'ar', QA: 'ar', BH: 'ar', OM: 'ar',
  JO: 'ar', LB: 'ar', IQ: 'ar', MA: 'ar', DZ: 'ar', TN: 'ar', LY: 'ar',
  SY: 'ar', YE: 'ar', PS: 'ar', SD: 'ar', MR: 'ar', SO: 'so', DJ: 'ar',
  KM: 'ar',
  // English
  US: 'en', GB: 'en', AU: 'en', CA: 'en', NZ: 'en', IE: 'en', ZA: 'en',
  JM: 'en', TT: 'en', BS: 'en', BB: 'en', BZ: 'en', GY: 'en',
  // Spanish
  ES: 'es', MX: 'es', AR: 'es', CL: 'es', CO: 'es', PE: 'es', VE: 'es',
  EC: 'es', BO: 'es', PY: 'es', UY: 'es', GT: 'es', CR: 'es', PA: 'es',
  HN: 'es', SV: 'es', NI: 'es', DO: 'es', CU: 'es', PR: 'es',
  // Portuguese
  BR: 'pt', PT: 'pt', AO: 'pt', MZ: 'pt', CV: 'pt', GW: 'pt', ST: 'pt',
  TL: 'pt',
  // French
  FR: 'fr', BE: 'fr', CH: 'fr', LU: 'fr', MC: 'fr', SN: 'fr', CI: 'fr',
  CM: 'fr', BJ: 'fr', BF: 'fr', NE: 'fr', ML: 'fr', TG: 'fr', GA: 'fr',
  CG: 'fr', CD: 'fr', MG: 'fr', HT: 'ht',
  // German
  DE: 'de', AT: 'de', LI: 'de',
  // Italian
  IT: 'it', SM: 'it', VA: 'it',
  // Dutch
  NL: 'nl',
  // Russian / Slavic
  RU: 'ru', BY: 'ru', KZ: 'ru', KG: 'ky', TJ: 'tg', UZ: 'uz', TM: 'tk',
  AM: 'hy', GE: 'ka', AZ: 'az', MD: 'ro',
  UA: 'uk',
  // East Asia
  CN: 'zh', TW: 'zh', HK: 'zh', MO: 'zh', SG: 'zh',
  JP: 'ja', KR: 'ko', KP: 'ko',
  // South / Southeast Asia
  IN: 'hi', PK: 'ur', BD: 'bn', LK: 'si', NP: 'ne', BT: 'dz',
  ID: 'id', MY: 'ms', BN: 'ms', PH: 'fil', VN: 'vi', TH: 'th', LA: 'lo',
  KH: 'km', MM: 'my', MN: 'mn',
  // Iranian
  IR: 'fa', AF: 'ps',
  // Turkic
  TR: 'tr',
  // Israel
  IL: 'he',
  // Nordic
  SE: 'sv', NO: 'no', DK: 'da', FI: 'fi', IS: 'is', FO: 'da', GL: 'da',
  // Eastern Europe / Balkans
  PL: 'pl', CZ: 'cs', SK: 'sk', HU: 'hu', RO: 'ro', BG: 'bg', GR: 'el',
  HR: 'hr', SI: 'sl', RS: 'sr', BA: 'bs', ME: 'sr', MK: 'mk', AL: 'sq',
  XK: 'sq',
  // Baltics
  LT: 'lt', LV: 'lv', EE: 'et',
  // Africa (non-Arab)
  ET: 'am', ER: 'am', KE: 'sw', TZ: 'sw', UG: 'sw', RW: 'rw', BI: 'rw',
  NG: 'en', GH: 'en', ZW: 'en', ZM: 'en', MW: 'en', BW: 'en', NA: 'en',
  LS: 'en', SZ: 'en',
  // Caucasus / Special
  MT: 'mt',
};

const FALLBACK = 'en';   // when we have no clue
const KEY_MANUAL = 'zerax_lang_manual';   // user-chosen
const KEY_PERSIST = 'zerax_lang';          // i18next's persisted key

function isSupported(code) {
  return Boolean(code && LANG_BY_CODE[code]);
}

/** Quick synchronous pick — used at i18next init time so the very first
 *  render is already in the user's likely language. */
export function getInitialLanguage() {
  try {
    // 1) Manual override always wins
    const manual = localStorage.getItem(KEY_MANUAL);
    if (isSupported(manual)) return manual;
    // 2) Legacy / previously persisted choice
    const persisted = localStorage.getItem(KEY_PERSIST);
    if (isSupported(persisted)) return persisted;
    // 3) Browser language (e.g. "fr-FR" → "fr")
    const navs = (navigator.languages && navigator.languages.length
      ? navigator.languages
      : [navigator.language || '']);
    for (const raw of navs) {
      if (!raw) continue;
      const code = raw.toLowerCase().split('-')[0];
      if (isSupported(code)) return code;
    }
  } catch (_) { /* SSR / privacy mode */ }
  return 'ar'; // Zerax default — Arabic
}

export function hasManualChoice() {
  try { return Boolean(localStorage.getItem(KEY_MANUAL)); }
  catch (_) { return false; }
}

export function markManualChoice(code) {
  try { if (isSupported(code)) localStorage.setItem(KEY_MANUAL, code); }
  catch (_) { /* ignore */ }
}

/**
 * Hit a free geo-IP endpoint and infer a language from the country.
 * Falls back silently on any error. We only invoke `apply(code)` if:
 *   - the visitor has NOT made a manual choice, and
 *   - the inferred language differs from the one currently active.
 */
export async function detectGeoLanguageInBackground(currentCode, apply) {
  if (hasManualChoice()) return; // user already chose — don't touch
  // Try a couple of free providers; first success wins
  const providers = [
    { url: 'https://ipapi.co/json/',       parse: (d) => (d && d.country_code) || (d && d.country) },
    { url: 'https://ipwho.is/',            parse: (d) => d && d.country_code },
    { url: 'https://get.geojs.io/v1/ip/country.json', parse: (d) => d && d.country },
  ];
  for (const p of providers) {
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 4500);
      const r = await fetch(p.url, { signal: ctrl.signal });
      clearTimeout(t);
      if (!r.ok) continue;
      const d = await r.json();
      const cc = (p.parse(d) || '').toString().toUpperCase();
      if (!cc) continue;
      const inferred = COUNTRY_TO_LANG[cc];
      if (!inferred || !isSupported(inferred)) return;
      if (inferred === currentCode) return; // already perfect
      // Guardrail: don't override if the browser language was an exact
      // match for navigator.language (user clearly prefers that one).
      try {
        const nav = (navigator.language || '').toLowerCase().split('-')[0];
        if (nav && nav === currentCode && nav !== inferred) {
          // Only override if the geo signal is strong AND current is the
          // pure fallback. We respect navigator.language otherwise.
          if (currentCode !== FALLBACK && currentCode !== 'ar') return;
        }
      } catch (_) { /* */ }
      apply(inferred);
      return;
    } catch (_) {
      // try next provider
    }
  }
}
