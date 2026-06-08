import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { LANG_BY_CODE } from '../i18n/languages';
import { markManualChoice } from '../i18n/geoLanguage';
import { X, Globe } from 'lucide-react';

/**
 * Floating toast that confirms an auto-detected language for the visitor.
 * Listens for the custom `zitex:lang-auto-detected` event (dispatched by
 * geoLanguage.js) and offers a one-click "Keep Arabic" escape hatch.
 *
 * - Auto-dismisses after 8 seconds
 * - Persists "dismissed once" in sessionStorage so it doesn't nag
 * - Always presented in BOTH the new language AND Arabic so the visitor
 *   can read either side
 */
export default function DetectedLanguageBanner() {
  const { i18n } = useTranslation();
  const [detected, setDetected] = useState(null); // language code
  const [show, setShow] = useState(false);

  useEffect(() => {
    const handler = (e) => {
      const code = e?.detail?.code;
      if (!code || !LANG_BY_CODE[code]) return;
      // Don't show if the visitor has dismissed this session
      try { if (sessionStorage.getItem('zitex_geo_banner_seen') === '1') return; }
      catch (_) { /* */ }
      setDetected(code);
      setShow(true);
      const t = setTimeout(() => setShow(false), 8000);
      return () => clearTimeout(t);
    };
    window.addEventListener('zitex:lang-auto-detected', handler);
    return () => window.removeEventListener('zitex:lang-auto-detected', handler);
  }, []);

  if (!show || !detected) return null;
  const lang = LANG_BY_CODE[detected];

  const keepArabic = () => {
    markManualChoice('ar');
    i18n.changeLanguage('ar');
      try { sessionStorage.setItem('zitex_geo_banner_seen', '1'); } catch (_) { /* */ }
    setShow(false);
  };

  const dismiss = () => {
    try { sessionStorage.setItem('zitex_geo_banner_seen', '1'); } catch (_) { /* */ }
    setShow(false);
  };

  return (
    <div
      data-testid="geo-lang-banner"
      data-no-translate="true"
      dir={lang.dir}
      className="fixed bottom-5 left-1/2 -translate-x-1/2 z-[150] max-w-md w-[92%] sm:w-auto bg-zinc-950/95 backdrop-blur-xl border border-emerald-400/30 rounded-2xl shadow-2xl px-4 py-3 flex items-center gap-3 animate-[fadeInUp_.4s_ease]"
      style={{ animationFillMode: 'both' }}
    >
      <span className="text-2xl shrink-0">{lang.flag}</span>
      <div className="flex-1 min-w-0">
        <div className="text-white font-bold text-sm leading-tight" dir={lang.dir}>
          <Globe className="inline w-3.5 h-3.5 me-1 text-emerald-300" />
          {lang.native}
        </div>
        <div className="text-zinc-400 text-[11px] mt-0.5 leading-tight">
          تم اكتشاف لغتك تلقائياً
        </div>
      </div>
      <button
        type="button"
        onClick={keepArabic}
        data-testid="geo-banner-keep-arabic"
        className="px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-200 text-xs font-bold border border-amber-400/30 shrink-0"
      >
        العربية
      </button>
      <button
        type="button"
        onClick={dismiss}
        data-testid="geo-banner-close"
        aria-label="Close"
        className="text-zinc-500 hover:text-white p-1 shrink-0"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
