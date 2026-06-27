/**
 * 🎴 ConciergeWizard — renders Setup Wizard cards from backend schema.
 *
 * Consumes SSE events:
 *   - concierge_setup_required → opens wizard panel
 *   - concierge_wizard_card → adds a card
 *   - concierge_setup_done → marks "awaiting user"
 *
 * Each card type has a dedicated renderer (Intro, KeyInput, Checklist, Cost,
 * Success, SkipAlternative). All bilingual (ar+en).
 */
import React, { useState, useCallback } from 'react';

const TXT = {
  ar: {
    paste: 'الصق المفتاح هنا',
    validate: 'تحقّق واحفظ',
    open_provider: 'افتح صفحة الإصدار',
    skip: 'تخطّى الآن',
    continue: 'أكمل البناء',
    saved: 'تم الحفظ والتحقق ✅',
    setup_title: '🔑 إعداد المتطلبات',
    setup_subtitle: 'لاحظت أن مشروعك يحتاج بعض المفاتيح. خطوات سريعة قبل البناء:',
    cost_label: '💸 ملخّص التكلفة',
    free_tier_label: 'مجاني',
    invalid: 'مفتاح غير صالح',
  },
  en: {
    paste: 'Paste your key here',
    validate: 'Validate & Save',
    open_provider: 'Open provider page',
    skip: 'Skip for now',
    continue: 'Continue building',
    saved: 'Saved & verified ✅',
    setup_title: '🔑 Setup Required',
    setup_subtitle: 'Your project needs a few keys. Quick steps before we build:',
    cost_label: '💸 Cost summary',
    free_tier_label: 'Free',
    invalid: 'Invalid key',
  },
};

const SetupIntroCard = ({ card, lang, onAction }) => {
  const t = TXT[lang] || TXT.ar;
  return (
    <div data-testid={`card-intro-${card.integration_id}`}
         className="border border-amber-500/30 bg-zinc-900/80 rounded-2xl p-5 mb-4">
      <h3 className="text-lg font-bold text-amber-400 mb-1">{card.title}</h3>
      <p className="text-sm text-zinc-300 mb-3">{card.subtitle_ar || card.subtitle_en || t.setup_subtitle}</p>
      <div className="text-xs text-zinc-500 mb-3">⏱️ ~{card.estimated_minutes || 3} {lang === 'ar' ? 'دقائق' : 'min'}</div>
      <div className="flex gap-2 flex-wrap">
        {(card.actions || []).map(a => (
          <button key={a.id}
                  data-testid={`btn-${card.integration_id}-${a.id}`}
                  onClick={() => onAction(card, a)}
                  className={`px-4 py-2 rounded-lg text-sm ${a.primary ? 'bg-amber-500 text-black hover:bg-amber-400' : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'}`}>
            {a.label}
          </button>
        ))}
      </div>
    </div>
  );
};

const KeyInputCard = ({ card, lang, onValidate, isSecret = true }) => {
  const t = TXT[lang] || TXT.ar;
  const [value, setValue] = useState('');
  const [status, setStatus] = useState(null); // null | "validating" | "ok" | "error"
  const [message, setMessage] = useState('');
  const [showValue, setShowValue] = useState(false);

  const submit = async () => {
    if (!value.trim()) return;
    setStatus('validating');
    setMessage('');
    try {
      const r = await fetch('/api/concierge/credentials/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_name: card.credential_key, value: value.trim() }),
      });
      const data = await r.json();
      if (data.saved) {
        setStatus('ok');
        setMessage(data.validation?.message || t.saved);
        onValidate(card, data);
      } else {
        setStatus('error');
        setMessage(data.validation?.message || t.invalid);
      }
    } catch (e) {
      setStatus('error');
      setMessage(e.message);
    }
  };

  return (
    <div data-testid={`card-key-${card.credential_key}`}
         className="border border-zinc-700 bg-zinc-900/60 rounded-2xl p-5 mb-4">
      <h4 className="text-base font-semibold text-zinc-100 mb-2">{card.title}</h4>
      {card.instructions_markdown && (
        <pre className="text-xs text-zinc-400 bg-zinc-950 rounded p-3 mb-3 whitespace-pre-wrap font-mono">
{card.instructions_markdown}
        </pre>
      )}
      <div className="flex gap-2 items-stretch mb-2">
        <input
          data-testid={`input-${card.credential_key}`}
          type={isSecret && !showValue ? 'password' : 'text'}
          value={value}
          onChange={e => setValue(e.target.value)}
          placeholder={card.placeholder || t.paste}
          className="flex-1 bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 font-mono focus:border-amber-500 outline-none"
        />
        {isSecret && (
          <button onClick={() => setShowValue(s => !s)}
                  data-testid={`toggle-show-${card.credential_key}`}
                  className="px-3 py-2 text-xs text-zinc-400 hover:text-zinc-200">
            {showValue ? '🙈' : '👁️'}
          </button>
        )}
      </div>
      <div className="flex gap-2">
        <button onClick={submit}
                disabled={status === 'validating' || !value.trim()}
                data-testid={`validate-${card.credential_key}`}
                className="flex-1 px-4 py-2 rounded-lg text-sm bg-amber-500 text-black font-medium disabled:opacity-50 hover:bg-amber-400">
          {status === 'validating' ? '⏳ ...' : t.validate}
        </button>
        {(card.actions || []).filter(a => a.id === 'open_provider').map(a => (
          <a key={a.id} href={a.url || '#'} target="_blank" rel="noreferrer"
             data-testid={`open-provider-${card.credential_key}`}
             className="px-3 py-2 rounded-lg text-sm bg-zinc-800 text-zinc-300 hover:bg-zinc-700">
            🔗 {a.label}
          </a>
        ))}
      </div>
      {message && (
        <div className={`text-xs mt-2 ${status === 'ok' ? 'text-emerald-400' : 'text-rose-400'}`}>
          {message}
        </div>
      )}
    </div>
  );
};

const CostSummaryCard = ({ card, lang }) => {
  const t = TXT[lang] || TXT.ar;
  return (
    <div data-testid="card-cost-summary"
         className="border border-emerald-500/30 bg-emerald-950/20 rounded-2xl p-5 mb-4">
      <h3 className="text-base font-bold text-emerald-400 mb-3">{card.title}</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-zinc-500 border-b border-zinc-800">
            <th className="text-right pb-2">{lang === 'ar' ? 'الخدمة' : 'Service'}</th>
            <th className="text-right pb-2">{t.free_tier_label}</th>
            <th className="text-right pb-2">{lang === 'ar' ? 'مدفوع' : 'Paid'}</th>
          </tr>
        </thead>
        <tbody>
          {(card.items || []).map((item, i) => (
            <tr key={i} className="border-b border-zinc-900 text-zinc-300">
              <td className="py-2">{item.label}</td>
              <td className="py-2 text-emerald-400">{item.free_tier}</td>
              <td className="py-2 text-zinc-500">{item.paid || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {(card.note_ar || card.note_en) && (
        <p className="text-xs text-zinc-500 mt-3">{lang === 'ar' ? card.note_ar : card.note_en}</p>
      )}
    </div>
  );
};

const ChecklistCard = ({ card, lang }) => (
  <div data-testid="card-checklist"
       className="border border-zinc-700 bg-zinc-900/60 rounded-2xl p-5 mb-4">
    <h4 className="text-base font-semibold text-zinc-100 mb-3">{card.title}</h4>
    <ul className="space-y-2">
      {(card.steps || []).map((s, i) => (
        <li key={i} className={`text-sm flex items-center gap-2 ${s.done ? 'text-emerald-400' : 'text-zinc-500'}`}>
          <span>{s.done ? '✅' : '⭕'}</span>
          <span>{s.label}</span>
        </li>
      ))}
    </ul>
  </div>
);

const SuccessCard = ({ card, lang, onContinue }) => {
  const t = TXT[lang] || TXT.ar;
  return (
    <div data-testid={`card-success-${card.integration_id}`}
         className="border border-emerald-500/40 bg-emerald-950/30 rounded-2xl p-5 mb-4">
      <h3 className="text-lg font-bold text-emerald-400 mb-2">{card.title}</h3>
      {card.account_info && Object.keys(card.account_info).length > 0 && (
        <pre className="text-xs text-zinc-400 bg-zinc-950 rounded p-2 mb-3 font-mono">
{JSON.stringify(card.account_info, null, 2)}
        </pre>
      )}
      <button onClick={() => onContinue(card)}
              data-testid={`continue-${card.integration_id}`}
              className="px-4 py-2 rounded-lg bg-emerald-500 text-black font-medium hover:bg-emerald-400">
        {t.continue} →
      </button>
    </div>
  );
};

const SkipAlternativeCard = ({ card, lang, onAction }) => (
  <div data-testid={`card-skip-${card.integration_id}`}
       className="border border-amber-500/30 bg-amber-950/10 rounded-2xl p-4 mb-4">
    <h4 className="text-sm font-semibold text-amber-400 mb-2">
      {lang === 'ar' ? card.title_ar : card.title_en}
    </h4>
    <p className="text-xs text-zinc-300 mb-3">
      {lang === 'ar' ? card.alternative_ar : card.alternative_en}
    </p>
    <div className="flex gap-2">
      {(card.actions || []).map(a => (
        <button key={a.id} onClick={() => onAction(card, a)}
                data-testid={`btn-skip-${a.id}`}
                className={`px-3 py-1.5 text-xs rounded ${a.primary ? 'bg-amber-500 text-black' : 'bg-zinc-800 text-zinc-300'}`}>
          {a.label}
        </button>
      ))}
    </div>
  </div>
);


export const ConciergeCard = ({ card, lang = 'ar', onAction, onValidate, onContinue }) => {
  if (!card || !card.card_type) return null;
  const props = { card, lang, onAction, onValidate, onContinue };
  switch (card.card_type) {
    case 'setup_intro':       return <SetupIntroCard {...props} />;
    case 'key_input_validate':return <KeyInputCard {...props} isSecret={card.is_secret !== false} />;
    case 'cost_summary':      return <CostSummaryCard {...props} />;
    case 'setup_checklist':   return <ChecklistCard {...props} />;
    case 'setup_success':     return <SuccessCard {...props} />;
    case 'skip_alternative':  return <SkipAlternativeCard {...props} />;
    default:
      return (
        <div className="border border-zinc-700 rounded p-3 text-xs text-zinc-400">
          Unknown card type: {card.card_type}
        </div>
      );
  }
};


/**
 * Panel that collects multiple wizard cards as they stream in.
 * Usage:
 *   <ConciergeWizardPanel
 *      cards={cardsFromSSE}
 *      language="ar"
 *      onAllDone={() => resumeBuild()}
 *   />
 */
export const ConciergeWizardPanel = ({ cards = [], language = 'ar', projectId, onAllDone, onSkipAll }) => {
  const t = TXT[language] || TXT.ar;
  const [savedKeys, setSavedKeys] = useState(new Set());
  const [skipped, setSkipped] = useState(new Set());

  const handleValidate = useCallback((card, data) => {
    setSavedKeys(prev => new Set([...prev, card.credential_key]));
  }, []);

  const handleAction = useCallback((card, action) => {
    if (action.id === 'skip_for_now') {
      setSkipped(prev => new Set([...prev, card.integration_id]));
    }
  }, []);

  // Check if all key-input cards are saved → trigger onAllDone
  React.useEffect(() => {
    const keyCards = cards.filter(c => c.card_type === 'key_input_validate');
    if (keyCards.length === 0) return;
    const allDone = keyCards.every(c => savedKeys.has(c.credential_key) || skipped.has(c.integration_id));
    if (allDone && onAllDone) onAllDone();
  }, [savedKeys, skipped, cards, onAllDone]);

  if (!cards.length) return null;

  return (
    <div data-testid="concierge-wizard-panel"
         className="bg-zinc-950 border-l-2 border-amber-500 p-5 my-3 rounded-xl"
         dir={language === 'ar' ? 'rtl' : 'ltr'}>
      <div className="mb-4 pb-3 border-b border-zinc-800">
        <h2 className="text-xl font-bold text-amber-400">{t.setup_title}</h2>
        <p className="text-sm text-zinc-400 mt-1">{t.setup_subtitle}</p>
      </div>
      {cards.map((card, i) => (
        <ConciergeCard
          key={card.card_id || i}
          card={card}
          lang={language}
          onAction={handleAction}
          onValidate={handleValidate}
          onContinue={() => onAllDone && onAllDone()}
        />
      ))}
      {onSkipAll && (
        <button onClick={onSkipAll}
                data-testid="skip-all-setup"
                className="text-xs text-zinc-500 hover:text-zinc-300 mt-2 underline">
          {language === 'ar' ? 'تخطّى كل الإعداد لاحقاً' : 'Skip all setup for later'}
        </button>
      )}
    </div>
  );
};

export default ConciergeWizardPanel;
