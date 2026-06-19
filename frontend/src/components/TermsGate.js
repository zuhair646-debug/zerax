/**
 * TermsGate — wraps any section/page so first-time visitors must accept
 * the legal terms before they can use the section.
 *
 * Usage:
 *   <TermsGate section="websites">
 *     <FreeBuildChat ... />
 *   </TermsGate>
 *
 * The gate auto-detects the user's preferred locale (from <html lang> or
 * localStorage 'i18n-lang' or browser navigator.language).
 *
 * Acceptance is persisted in the user's record and never asked again for
 * that section/version. If we bump the version on the backend, users are
 * asked to re-accept.
 */
import React, { useState, useEffect } from 'react';
import { CheckCircle2, Loader2, ShieldCheck, X } from 'lucide-react';
import ZenrexBrand from './ZenrexBrand';

const API = process.env.REACT_APP_BACKEND_URL;

function detectLocale() {
  try {
    const stored = localStorage.getItem('i18n-lang');
    if (stored) return stored;
    const htmlLang = document.documentElement.lang;
    if (htmlLang) return htmlLang.split('-')[0];
    const nav = (navigator.language || 'ar').split('-')[0];
    return nav;
  } catch (_) { return 'ar'; }
}

export default function TermsGate({ section, children }) {
  const [state, setState] = useState({ status: 'checking', content: null });
  const [checked, setChecked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const locale = detectLocale();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = localStorage.getItem('token');
      if (!token) { setState({ status: 'accepted', content: null }); return; }
      try {
        const r = await fetch(`${API}/api/terms/check?section=${encodeURIComponent(section)}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (cancelled) return;
        if (r.ok) {
          const data = await r.json();
          if (data.accepted) { setState({ status: 'accepted', content: null }); return; }
        }
        // Load content
        const cr = await fetch(`${API}/api/terms/content?section=${encodeURIComponent(section)}&locale=${encodeURIComponent(locale)}`);
        if (cr.ok) {
          const body = await cr.json();
          if (!cancelled) setState({ status: 'needs_accept', content: body });
        } else {
          if (!cancelled) setState({ status: 'accepted', content: null });
        }
      } catch (_) {
        if (!cancelled) setState({ status: 'accepted', content: null });
      }
    })();
    return () => { cancelled = true; };
  }, [section, locale]);

  const accept = async () => {
    if (!checked) return;
    setSubmitting(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/terms/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ section, locale }),
      });
      if (r.ok) setState({ status: 'accepted', content: null });
    } finally {
      setSubmitting(false);
    }
  };

  if (state.status === 'accepted') return children;
  if (state.status === 'checking') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-zinc-300" data-testid={`terms-gate-loading-${section}`}>
        <Loader2 className="w-6 h-6 animate-spin text-amber-400" />
      </div>
    );
  }

  const c = state.content;
  const isRtl = locale === 'ar';

  return (
    <div
      className="fixed inset-0 z-[100] bg-zinc-950/95 backdrop-blur-md flex items-start sm:items-center justify-center p-3 sm:p-4 overflow-y-auto"
      data-testid={`terms-gate-${section}`}
      dir={isRtl ? 'rtl' : 'ltr'}
    >
      <div className="bg-zinc-900 border border-amber-500/40 rounded-2xl max-w-2xl w-full my-4 sm:my-8 shadow-2xl shadow-amber-500/15 max-h-[calc(100vh-2rem)] overflow-y-auto">
        <div className="p-5 border-b border-white/10 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <ZenrexBrand size={26} showLabel={false} />
            <div>
              <div className="flex items-center gap-2 text-amber-400 text-[10px] font-bold">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>{isRtl ? 'موافقة قانونية' : 'Legal Agreement'}</span>
              </div>
              <h2 className="text-lg font-black text-amber-200 mt-0.5" data-testid="terms-title">{c.title}</h2>
            </div>
          </div>
        </div>

        <div className="p-5 space-y-4 max-h-[60vh] overflow-y-auto">
          <p className="text-sm text-zinc-300 leading-relaxed">{c.intro}</p>
          <ul className="space-y-3">
            {c.bullets.map((b, i) => (
              <li key={i} data-testid={`terms-bullet-${i}`} className="flex gap-3 text-sm text-zinc-200 leading-relaxed">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-500/15 border border-emerald-400/40 text-emerald-300 text-xs font-black flex items-center justify-center">
                  {i + 1}
                </span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="p-5 border-t border-white/10 bg-black/30 rounded-b-2xl">
          <label className="flex items-start gap-3 cursor-pointer mb-4">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              data-testid={`terms-checkbox-${section}`}
              className="mt-1 w-4 h-4 accent-amber-400"
            />
            <span className="text-sm text-zinc-200 font-medium">{c.agreement}</span>
          </label>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => { window.location.href = '/'; }}
              data-testid={`terms-decline-${section}`}
              className="flex-1 px-4 py-3 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm font-bold flex items-center justify-center gap-1.5"
            >
              <X className="w-4 h-4" />
              {isRtl ? 'رفض والخروج' : 'Decline & Exit'}
            </button>
            <button
              type="button"
              onClick={accept}
              disabled={!checked || submitting}
              data-testid={`terms-accept-${section}`}
              className={`flex-[2] px-4 py-3 rounded-xl text-sm font-black flex items-center justify-center gap-1.5 ${checked ? 'bg-gradient-to-r from-amber-400 to-yellow-500 text-black hover:from-amber-300 hover:to-yellow-400' : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'}`}
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              {isRtl ? 'موافق — استمر' : 'I Accept — Continue'}
            </button>
          </div>
          <p className="text-[10px] text-zinc-500 text-center mt-3">
            {isRtl
              ? 'سيتم حفظ موافقتك مع تاريخ ووقت ورقم IP لأغراض قانونية.'
              : 'Your acceptance is logged with date/time/IP for legal purposes.'}
          </p>
        </div>
      </div>
    </div>
  );
}
