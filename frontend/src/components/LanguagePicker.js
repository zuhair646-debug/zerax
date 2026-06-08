import React, { useState, useMemo, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { WORLD_LANGUAGES, LANG_BY_CODE } from '../i18n/languages';
import { Globe, Search, X, Check } from 'lucide-react';

/**
 * Language picker — pill button + searchable modal with 100+ languages.
 * Persists choice to localStorage via i18next side-effect.
 *
 * Usage:
 *   import LanguagePicker from './components/LanguagePicker';
 *   <LanguagePicker />              // default: pill
 *   <LanguagePicker compact />      // small icon-only button
 */
export default function LanguagePicker({ compact = false }) {
  const { i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const current = LANG_BY_CODE[i18n.language] || LANG_BY_CODE['en'];

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return WORLD_LANGUAGES;
    return WORLD_LANGUAGES.filter(
      (l) =>
        l.code.toLowerCase().includes(q) ||
        l.name.toLowerCase().includes(q) ||
        (l.native || '').toLowerCase().includes(q)
    );
  }, [query]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    if (open) window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const pick = (code) => {
    i18n.changeLanguage(code);
    setOpen(false);
    setQuery('');
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        data-testid="lang-picker-trigger"
        className={`inline-flex items-center gap-2 rounded-full border border-white/15 bg-zinc-900/70 hover:bg-zinc-800/90 text-white transition-all ${
          compact ? 'p-2' : 'px-3 py-1.5 text-sm font-bold'
        }`}
        aria-label="Change language"
      >
        <Globe className="w-4 h-4 text-emerald-300" />
        {!compact && (
          <>
            <span className="text-base">{current.flag}</span>
            <span className="hidden md:inline">{current.native}</span>
            <span className="md:hidden uppercase text-xs tracking-wider">{current.code}</span>
          </>
        )}
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[200] bg-black/70 backdrop-blur-md flex items-start justify-center p-4 sm:p-8"
          onClick={() => setOpen(false)}
          data-testid="lang-picker-modal"
        >
          <div
            className="w-full max-w-2xl bg-zinc-950 border border-emerald-400/30 rounded-2xl shadow-2xl flex flex-col max-h-[85vh]"
            onClick={(e) => e.stopPropagation()}
            dir="auto"
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
              <div className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-emerald-400" />
                <h3 className="text-lg font-black text-white">
                  {i18n.t('lang.picker.title')}
                </h3>
                <span className="text-xs text-zinc-500">({WORLD_LANGUAGES.length}+)</span>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-zinc-400 hover:text-white"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="px-5 py-3 border-b border-white/10">
              <div className="relative">
                <Search className="w-4 h-4 absolute top-1/2 -translate-y-1/2 left-3 text-zinc-500" />
                <input
                  type="text"
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={i18n.t('lang.picker.search')}
                  data-testid="lang-picker-search"
                  className="w-full bg-black/40 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-white placeholder-zinc-500 focus:border-emerald-400 outline-none"
                />
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-3">
              {filtered.length === 0 ? (
                <div className="text-center py-12 text-zinc-500">
                  {i18n.t('lang.picker.empty')}
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  {filtered.map((l) => {
                    const active = l.code === i18n.language;
                    return (
                      <button
                        key={l.code}
                        type="button"
                        onClick={() => pick(l.code)}
                        data-testid={`lang-option-${l.code}`}
                        data-no-translate="true"
                        className={`flex items-center gap-3 px-3 py-2 rounded-lg border transition-all text-right ${
                          active
                            ? 'bg-emerald-500/15 border-emerald-400/50 text-emerald-200'
                            : 'bg-zinc-900/40 border-white/5 hover:border-emerald-400/30 text-zinc-200'
                        }`}
                      >
                        <span className="text-xl shrink-0">{l.flag}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-bold truncate" dir={l.dir}>
                            {l.native}
                          </div>
                          <div className="text-[10px] text-zinc-500 truncate">{l.name} · {l.code.toUpperCase()}</div>
                        </div>
                        {active && <Check className="w-4 h-4 text-emerald-400 shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="px-5 py-3 border-t border-white/10 text-[10px] text-zinc-500 text-center">
              💡 الترجمات تُحفظ تلقائياً وتُترجَم على الطلب عند الحاجة
            </div>
          </div>
        </div>
      )}
    </>
  );
}
