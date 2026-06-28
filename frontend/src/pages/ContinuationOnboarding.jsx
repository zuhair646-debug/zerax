// ContinuationOnboarding.jsx — Inspector → Provider → Keys → Consent wizard
// that appears at the TOP of the chat for projects in `continuation` mode
// before the AI engineer-manager is allowed to talk.
//
// Designed by user spec:
//  1) "الفاحص" card asks for the site URL and runs an external scan.
//  2) Visual provider cards (logos) + tutorial video appear underneath.
//  3) User pastes the key directly below the video and picks a 6-month validity.
//  4) Second card asks for the AI brain (Anthropic key or Emergent Universal).
//  5) Electronic-signature consent before the engineer wakes up.
//
// All credentials are encrypted server-side (Fernet) before being persisted.

import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import {
  Globe, Loader2, ShieldCheck, Sparkles, CheckCircle2,
  AlertTriangle, KeyRound, PlayCircle, ArrowRight, Lock,
  Brain, Scan, FileSignature, ExternalLink,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const cls = (...x) => x.filter(Boolean).join(' ');

async function authedFetch(url, opts = {}) {
  const token = localStorage.getItem('token');
  return fetch(url, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(opts.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });
}

// ─── Inspector card (الفاحص) ──────────────────────────────────────────
function InspectorCard({ projectId, onDone }) {
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [dupe, setDupe] = useState(null);

  const inspect = async () => {
    if (!url.trim()) { toast.error('الصق رابط موقعك أولاً'); return; }
    setBusy(true);
    setResult(null);
    setDupe(null);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/continuation/inspect-url`, {
        method: 'POST',
        body: JSON.stringify({ url: url.trim() }),
      });
      if (!r.ok) throw new Error('inspect failed');
      const d = await r.json();
      setResult(d);
    } catch (e) {
      toast.error('تعذّر فحص الرابط — تأكد من صحته وحاول مرة ثانية');
    } finally {
      setBusy(false);
    }
  };

  const proceed = async () => {
    setBusy(true);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/setup/save-url`, {
        method: 'POST',
        body: JSON.stringify({ url: result.url, inspection: result }),
      });
      const d = await r.json();
      if (d.duplicate) {
        setDupe(d);
        return;
      }
      if (!d.ok) throw new Error(d.detail || 'save failed');
      toast.success('✅ تم حفظ الرابط — ننتقل لاختيار مزود الكود');
      onDone(result);
    } catch {
      toast.error('فشل الحفظ');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="inspector-card" className="rounded-2xl border border-fuchsia-500/30 bg-gradient-to-br from-fuchsia-900/30 via-rose-900/20 to-amber-900/10 backdrop-blur p-5 sm:p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-fuchsia-500/20 border border-fuchsia-400/40 flex items-center justify-center">
          <Scan className="w-6 h-6 text-fuchsia-200" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-black text-fuchsia-100">الفاحص</h3>
          <p className="text-[11px] text-fuchsia-300/80">يقرأ موقعك خارجياً ويحدد لك أسرع طريقة وصول آمنة</p>
        </div>
      </div>

      <label className="block text-[11px] font-bold text-zinc-400 mb-1.5">رابط موقعك</label>
      <div className="flex gap-2 mb-3">
        <div className="flex-1 flex items-center gap-2 px-3 rounded-lg bg-black/40 border border-white/10 focus-within:border-fuchsia-400/50">
          <Globe className="w-4 h-4 text-zinc-500 shrink-0" />
          <input
            type="url"
            placeholder="https://yoursite.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={busy || !!result}
            data-testid="inspector-url-input"
            className="flex-1 py-3 bg-transparent text-sm focus:outline-none"
          />
        </div>
        {!result && (
          <button
            onClick={inspect}
            disabled={busy}
            data-testid="inspector-scan-btn"
            className="px-4 sm:px-5 rounded-lg bg-gradient-to-r from-fuchsia-500 to-rose-500 hover:from-fuchsia-400 hover:to-rose-400 transition font-black text-sm text-white disabled:opacity-40 flex items-center gap-1.5 whitespace-nowrap"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Scan className="w-4 h-4" />}
            افحص
          </button>
        )}
      </div>

      {/* Inspection result */}
      {result && (
        <div data-testid="inspection-result" className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 space-y-2.5">
          <div className="flex items-center gap-3">
            <img src={result.favicon} alt="" className="w-8 h-8 rounded" onError={(e) => { e.target.style.display = 'none'; }} />
            <div className="flex-1">
              <div className="text-xs font-bold text-emerald-100">{result.title || result.domain}</div>
              <div className="text-[10px] text-emerald-300/70">{result.domain}</div>
            </div>
            {result.ssl && <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-400/30 text-emerald-200">🔒 HTTPS</span>}
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="px-3 py-2 rounded-lg bg-black/30 border border-white/5">
              <div className="text-zinc-500">المنصة</div>
              <div className="text-zinc-100 font-bold">{result.platform}</div>
            </div>
            <div className="px-3 py-2 rounded-lg bg-black/30 border border-white/5">
              <div className="text-zinc-500">التقنية</div>
              <div className="text-zinc-100 font-bold">{result.framework}</div>
            </div>
          </div>
          {result.hints && result.hints.length > 0 && (
            <div className="space-y-1">
              {result.hints.map((h, i) => (
                <div key={i} className="text-[11px] text-amber-100/80 flex items-start gap-1.5">
                  <span className="mt-0.5">💡</span><span>{h}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Duplicate warning */}
      {dupe && (
        <div data-testid="duplicate-warning" className="mt-3 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4">
          <div className="flex items-start gap-2 mb-2">
            <AlertTriangle className="w-5 h-5 text-amber-300 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-bold text-amber-100 mb-0.5">عندك مشروع تكملة سابق لنفس الرابط</div>
              <div className="text-[11px] text-amber-200/80">{dupe.existing_project_name}</div>
            </div>
          </div>
          <div className="flex gap-2">
            <a href={`/freebuild/chat/${dupe.existing_project_id}`} className="flex-1 text-center px-3 py-2 rounded-lg bg-amber-500/20 border border-amber-400/40 text-xs font-bold text-amber-100 hover:bg-amber-500/30">
              فتح المشروع السابق
            </a>
            <button onClick={() => setDupe(null)} className="flex-1 px-3 py-2 rounded-lg bg-zinc-500/20 border border-zinc-400/30 text-xs font-bold text-zinc-200 hover:bg-zinc-500/30">
              ابدأ من جديد
            </button>
          </div>
        </div>
      )}

      {result && !dupe && (
        <button
          onClick={proceed}
          disabled={busy}
          data-testid="inspector-proceed-btn"
          className="w-full mt-3 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 font-black text-sm text-white flex items-center justify-center gap-2 disabled:opacity-50"
        >
          متابعة لاختيار مزود الكود
          <ArrowRight className="w-4 h-4 rotate-180" />
        </button>
      )}
    </div>
  );
}

// ─── Provider selection (visual logo cards) ───────────────────────────
function ProviderSelector({ projectId, catalog, recommendedId, onSelect }) {
  const all = [
    ...(catalog.git_providers || []).map((p) => ({ ...p, group: 'git' })),
    ...(catalog.hosting_providers || []).map((p) => ({ ...p, group: 'hosting' })),
  ];
  const [selected, setSelected] = useState(recommendedId || null);
  const [busy, setBusy] = useState(false);

  // Auto-scroll recommended into view
  useEffect(() => {
    if (recommendedId) {
      const el = document.getElementById(`provider-card-${recommendedId}`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [recommendedId]);

  const confirm = async () => {
    if (!selected) { toast.error('اختر مزوّداً أولاً'); return; }
    setBusy(true);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/setup/select-provider`, {
        method: 'POST',
        body: JSON.stringify({ provider_id: selected }),
      });
      const d = await r.json();
      if (!d.ok) throw new Error();
      onSelect(all.find((p) => p.id === selected));
    } catch {
      toast.error('فشل الحفظ');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="provider-selector" className="rounded-2xl border border-fuchsia-500/30 bg-black/40 backdrop-blur p-5 sm:p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-rose-500/20 border border-rose-400/40 flex items-center justify-center">
          <KeyRound className="w-6 h-6 text-rose-200" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-black text-rose-100">من وين نوصل لكودك؟</h3>
          <p className="text-[11px] text-rose-300/80">اختر المنصة اللي مستضيف عليها مشروعك. اقتراحنا مُعلّم بنجمة ⭐</p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
        {all.map((p) => {
          const isRec = recommendedId === p.id;
          const isSel = selected === p.id;
          return (
            <button
              key={p.id}
              id={`provider-card-${p.id}`}
              data-testid={`provider-card-${p.id}`}
              onClick={() => setSelected(p.id)}
              className={cls(
                'relative aspect-square rounded-xl p-3 flex flex-col items-center justify-center gap-1.5 transition border',
                isSel
                  ? 'border-fuchsia-400 bg-fuchsia-500/20 shadow-lg shadow-fuchsia-500/20 scale-[1.02]'
                  : 'border-white/10 bg-black/30 hover:bg-white/5 hover:border-white/20',
              )}
            >
              {isRec && (
                <span className="absolute -top-1.5 -right-1.5 text-[9px] font-black px-1.5 py-0.5 rounded-full bg-amber-400 text-black">⭐</span>
              )}
              <div className="text-3xl sm:text-4xl">{p.logo_emoji}</div>
              <div className="text-[10px] sm:text-[11px] font-bold text-zinc-200 text-center leading-tight">{p.label_ar}</div>
            </button>
          );
        })}
      </div>

      <button
        onClick={confirm}
        disabled={!selected || busy}
        data-testid="provider-confirm-btn"
        className="w-full mt-4 py-3 rounded-xl bg-gradient-to-r from-fuchsia-500 to-rose-500 hover:from-fuchsia-400 hover:to-rose-400 font-black text-sm text-white disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
        اختاره ✓
      </button>
    </div>
  );
}

// ─── Credential capture (video + paste + validity) ────────────────────
function CredentialCapture({ projectId, provider, onDone, onBack }) {
  const keys = provider.credential_keys || [];
  const [values, setValues] = useState({});
  const [validity, setValidity] = useState(6);
  const [busy, setBusy] = useState(false);
  const [savedMasks, setSavedMasks] = useState({});

  const saveAll = async () => {
    for (const k of keys) {
      if (!values[k] || values[k].trim().length < 4) {
        toast.error(`اكتب قيمة ${k}`);
        return;
      }
    }
    setBusy(true);
    try {
      for (const k of keys) {
        const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/setup/save-credential`, {
          method: 'POST',
          body: JSON.stringify({ key_name: k, value: values[k], validity_months: validity }),
        });
        const d = await r.json();
        if (!d.ok) throw new Error(d.detail || `failed for ${k}`);
        setSavedMasks((m) => ({ ...m, [k]: d.mask }));
      }
      toast.success('🔐 المفاتيح محفوظة بتشفير AES-128');
      onDone();
    } catch (e) {
      toast.error('فشل حفظ المفتاح — حاول مرة ثانية');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="credential-capture" className="rounded-2xl border border-fuchsia-500/30 bg-black/40 backdrop-blur p-5 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="text-3xl">{provider.logo_emoji}</div>
          <div>
            <h3 className="text-base sm:text-lg font-black text-fuchsia-100">{provider.label_ar}</h3>
            <p className="text-[11px] text-zinc-400">شاهد الفيديو، أنشئ المفتاح، الصقه تحت</p>
          </div>
        </div>
        <button onClick={onBack} className="text-[10px] text-zinc-400 hover:text-fuchsia-300" data-testid="provider-back-btn">
          ← غيّر المزوّد
        </button>
      </div>

      {/* Video + instructions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        <div className="aspect-video rounded-xl bg-black/60 border border-white/10 overflow-hidden flex items-center justify-center relative">
          {provider.tutorial_video_ar ? (
            <video
              src={provider.tutorial_video_ar}
              controls
              loop
              playsInline
              data-testid="tutorial-video"
              className="w-full h-full object-cover"
              onError={(e) => { e.target.parentElement.classList.add('video-fail'); }}
            />
          ) : (
            <div className="flex flex-col items-center gap-2 text-zinc-500 text-xs">
              <PlayCircle className="w-10 h-10" />
              <span>فيديو الشرح قيد التحضير</span>
            </div>
          )}
        </div>
        <div className="rounded-xl bg-emerald-500/5 border border-emerald-500/20 p-4">
          <div className="text-[10px] font-black text-emerald-300 mb-2">خطوات الحصول على المفتاح</div>
          <pre className="text-[11px] text-zinc-200 leading-relaxed whitespace-pre-wrap font-sans" data-testid="provider-instructions">
            {provider.instructions_ar || 'تعليمات قيد التحضير'}
          </pre>
          {provider.where_to_get_url && (
            <a
              href={provider.where_to_get_url}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="provider-where-link"
              className="mt-3 inline-flex items-center gap-1.5 text-[11px] font-bold px-3 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-400/30 text-emerald-100 hover:bg-emerald-500/30"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              افتح صفحة الإنشاء مباشرة
            </a>
          )}
        </div>
      </div>

      {/* Paste fields */}
      <div className="space-y-2.5 mb-4">
        {keys.map((k) => (
          <div key={k}>
            <label className="block text-[11px] font-bold text-zinc-400 mb-1">{k}</label>
            {savedMasks[k] ? (
              <div className="px-3 py-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs font-mono text-emerald-200 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" /> {savedMasks[k]} <span className="text-[10px] text-emerald-300/70 ml-auto">محفوظ مشفّر</span>
              </div>
            ) : (
              <input
                type="password"
                placeholder={`الصق ${k} هنا...`}
                value={values[k] || ''}
                onChange={(e) => setValues((v) => ({ ...v, [k]: e.target.value }))}
                data-testid={`credential-input-${k}`}
                className="w-full px-3 py-2.5 rounded-lg bg-black/50 border border-white/10 text-sm font-mono focus:border-fuchsia-400/50 focus:outline-none"
              />
            )}
          </div>
        ))}
      </div>

      {/* Validity selector */}
      <div className="mb-4 rounded-xl bg-amber-500/5 border border-amber-500/20 p-3">
        <div className="text-[11px] font-bold text-amber-100 mb-2">⏳ مدة صلاحية المفتاح (ضروري ≥ 3 شهور)</div>
        <div className="flex gap-2">
          {[3, 6, 12].map((m) => (
            <button
              key={m}
              onClick={() => setValidity(m)}
              data-testid={`validity-${m}m`}
              className={cls(
                'flex-1 py-2 rounded-lg text-xs font-bold transition border',
                validity === m
                  ? 'bg-amber-500/30 border-amber-400 text-amber-100'
                  : 'bg-black/30 border-white/10 text-zinc-300 hover:bg-white/5',
              )}
            >
              {m} شهور {m === 6 && <span className="text-[9px] text-amber-300 mr-1">(الأنسب)</span>}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={saveAll}
        disabled={busy}
        data-testid="credential-save-btn"
        className="w-full py-3 rounded-xl bg-gradient-to-r from-fuchsia-500 to-rose-500 hover:from-fuchsia-400 hover:to-rose-400 font-black text-sm text-white disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
        احفظ بتشفير AES-128
      </button>
    </div>
  );
}

// ─── LLM key step (Anthropic vs Emergent Universal) ────────────────────
function LlmKeyStep({ projectId, onDone }) {
  const [provider, setProvider] = useState('emergent');
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (provider === 'anthropic' && !value.startsWith('sk-ant-')) {
      toast.error('مفتاح Anthropic يبدأ بـ sk-ant-');
      return;
    }
    setBusy(true);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/setup/save-llm-key`, {
        method: 'POST',
        body: JSON.stringify({ provider, value: provider === 'anthropic' ? value : '' }),
      });
      const d = await r.json();
      if (!d.ok) throw new Error();
      toast.success('🧠 تم اختيار عقل الذكاء الاصطناعي');
      onDone();
    } catch {
      toast.error('فشل الحفظ');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="llm-key-step" className="rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-900/30 via-violet-900/20 to-fuchsia-900/10 backdrop-blur p-5 sm:p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-indigo-500/20 border border-indigo-400/40 flex items-center justify-center">
          <Brain className="w-6 h-6 text-indigo-200" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-black text-indigo-100">عقل المهندس</h3>
          <p className="text-[11px] text-indigo-300/80">اختر من يفكّر للذكاء الاصطناعي: حسابك الخاص أو عقل Zenrex الجاهز</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        <button
          onClick={() => setProvider('emergent')}
          data-testid="llm-option-emergent"
          className={cls(
            'rounded-xl p-4 text-right transition border',
            provider === 'emergent'
              ? 'border-emerald-400 bg-emerald-500/15 shadow-lg shadow-emerald-500/10'
              : 'border-white/10 bg-black/30 hover:bg-white/5',
          )}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">⚡</span>
            <span className="text-sm font-black text-emerald-100">Zenrex Universal</span>
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/30 text-emerald-100 mr-auto">الأسرع</span>
          </div>
          <div className="text-[11px] text-emerald-200/80 leading-relaxed">
            عقل جاهز (Claude Sonnet 4.5). يُحتسب من نقاطك حسب الاستخدام. مايحتاج مفتاح.
          </div>
        </button>
        <button
          onClick={() => setProvider('anthropic')}
          data-testid="llm-option-anthropic"
          className={cls(
            'rounded-xl p-4 text-right transition border',
            provider === 'anthropic'
              ? 'border-indigo-400 bg-indigo-500/15 shadow-lg shadow-indigo-500/10'
              : 'border-white/10 bg-black/30 hover:bg-white/5',
          )}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">🤖</span>
            <span className="text-sm font-black text-indigo-100">Anthropic الخاص بك</span>
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-indigo-500/30 text-indigo-100 mr-auto">للمحترفين</span>
          </div>
          <div className="text-[11px] text-indigo-200/80 leading-relaxed">
            استخدم مفتاحك من console.anthropic.com. تتحكم في الميزانية مباشرة.
          </div>
        </button>
      </div>

      {provider === 'anthropic' && (
        <div className="mb-4">
          <label className="block text-[11px] font-bold text-zinc-400 mb-1">ANTHROPIC_API_KEY</label>
          <input
            type="password"
            placeholder="sk-ant-api03-..."
            value={value}
            onChange={(e) => setValue(e.target.value)}
            data-testid="anthropic-key-input"
            className="w-full px-3 py-2.5 rounded-lg bg-black/50 border border-white/10 text-sm font-mono focus:border-indigo-400/50 focus:outline-none"
          />
          <a
            href="https://console.anthropic.com/settings/keys"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-flex items-center gap-1.5 text-[11px] text-indigo-300 hover:text-indigo-100"
          >
            <ExternalLink className="w-3 h-3" /> افتح صفحة إنشاء المفتاح
          </a>
        </div>
      )}

      <button
        onClick={save}
        disabled={busy}
        data-testid="llm-key-save-btn"
        className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-fuchsia-500 hover:from-indigo-400 hover:to-fuchsia-400 font-black text-sm text-white disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
        تأكيد العقل واستكمل
      </button>
    </div>
  );
}

// ─── Electronic-signature consent ──────────────────────────────────────
function ConsentStep({ projectId, onDone }) {
  const CLAUSES = [
    'أقرّ بأنني المالك الشرعي لهذا المشروع وأملك صلاحية تعديله',
    'أوافق على أن Zenrex يعمل في نسخة معزولة أولاً (Sandbox) ولا يلمس الإنتاج بدون موافقتي الصريحة',
    'أتحمل مسؤولية أي تعديل أوافق عليه بضغطة "اعتماد" في الشات',
    'أفهم أن المفاتيح مشفّرة وتُستخدم داخلياً فقط، ولن تظهر في أي محادثة',
  ];
  const [checked, setChecked] = useState(Array(CLAUSES.length).fill(false));
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);

  const allChecked = checked.every(Boolean);

  const sign = async () => {
    if (!allChecked) { toast.error('وافق على كل البنود'); return; }
    if (name.trim().length < 3) { toast.error('اكتب اسمك الكامل كتوقيع'); return; }
    setBusy(true);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/setup/consent`, {
        method: 'POST',
        body: JSON.stringify({
          clauses_accepted: CLAUSES.filter((_, i) => checked[i]),
          signature_name: name.trim(),
        }),
      });
      const d = await r.json();
      if (!d.ok) throw new Error();
      toast.success('✅ تم التوقيع — المهندس بدأ العمل');
      onDone();
    } catch {
      toast.error('فشل التوقيع');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="consent-step" className="rounded-2xl border border-amber-500/30 bg-amber-500/5 backdrop-blur p-5 sm:p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-amber-500/20 border border-amber-400/40 flex items-center justify-center">
          <FileSignature className="w-6 h-6 text-amber-200" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-black text-amber-100">التوقيع الإلكتروني</h3>
          <p className="text-[11px] text-amber-300/80">آخر خطوة قبل ما يبدأ المهندس الهندسي العمل</p>
        </div>
      </div>

      <div className="space-y-2 mb-4">
        {CLAUSES.map((c, i) => (
          <label key={i} className="flex items-start gap-2.5 p-3 rounded-lg bg-black/30 border border-amber-500/10 cursor-pointer hover:bg-black/40">
            <input
              type="checkbox"
              checked={checked[i]}
              onChange={(e) => setChecked((prev) => prev.map((v, idx) => idx === i ? e.target.checked : v))}
              data-testid={`consent-clause-${i}`}
              className="w-4 h-4 mt-0.5 accent-amber-500 shrink-0"
            />
            <span className="text-[11px] text-amber-100/90 leading-relaxed">{c}</span>
          </label>
        ))}
      </div>

      <div className="mb-4">
        <label className="block text-[11px] font-bold text-amber-200 mb-1">التوقيع (اكتب اسمك الكامل)</label>
        <input
          type="text"
          placeholder="مثلاً: محمد العمراني"
          value={name}
          onChange={(e) => setName(e.target.value)}
          data-testid="signature-name-input"
          className="w-full px-3 py-2.5 rounded-lg bg-black/50 border border-amber-500/30 text-sm focus:border-amber-400/60 focus:outline-none font-serif italic"
          style={{ fontFamily: '"Lateef", "Amiri", serif' }}
        />
      </div>

      <button
        onClick={sign}
        disabled={!allChecked || busy}
        data-testid="consent-sign-btn"
        className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 font-black text-sm text-white disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
        وقّع وابدأ
      </button>
    </div>
  );
}

// ─── Main wizard ────────────────────────────────────────────────────────
export default function ContinuationOnboarding({ projectId, onCompleted }) {
  const [state, setState] = useState('loading');
  const [catalog, setCatalog] = useState(null);
  const [inspection, setInspection] = useState(null);
  const [selectedProvider, setSelectedProvider] = useState(null);

  // Load setup state + provider catalog in parallel on mount
  useEffect(() => {
    (async () => {
      try {
        const [setupRes, catalogRes] = await Promise.all([
          authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/setup`),
          fetch(`${API}/api/freebuild-chat/continuation/providers-catalog`),
        ]);
        const setupData = await setupRes.json();
        const catData = await catalogRes.json();
        setCatalog(catData);
        if (setupData.inspection) setInspection(setupData.inspection);
        if (setupData.provider_id) {
          const all = [...(catData.git_providers || []), ...(catData.hosting_providers || [])];
          setSelectedProvider(all.find((p) => p.id === setupData.provider_id));
        }
        if (setupData.completed) {
          setState('ready');
          onCompleted && onCompleted();
        } else {
          setState(setupData.state || 'url');
        }
      } catch (e) {
        setState('url');
      }
    })();
  }, [projectId, onCompleted]);

  // Track progress
  const STEPS = ['url', 'provider', 'provider_key', 'llm', 'consent'];
  const stepIdx = STEPS.indexOf(state);

  if (state === 'ready' || state === 'loading') return null;

  return (
    <div dir="rtl" data-testid="continuation-onboarding" className="space-y-4 mb-4">
      {/* Progress bar */}
      <div className="flex items-center gap-1.5 px-2">
        {STEPS.map((s, i) => (
          <div
            key={s}
            data-testid={`progress-step-${i}`}
            className={cls(
              'flex-1 h-1.5 rounded-full transition',
              i <= stepIdx ? 'bg-gradient-to-r from-fuchsia-500 to-rose-500' : 'bg-white/10',
            )}
          />
        ))}
      </div>
      <div className="text-[10px] text-zinc-500 px-2 flex justify-between">
        <span>إعداد آمن — الخطوة {stepIdx + 1} من {STEPS.length}</span>
        <span>🔐 مشفّر AES-128</span>
      </div>

      {state === 'url' && (
        <InspectorCard
          projectId={projectId}
          onDone={(insp) => { setInspection(insp); setState('provider'); }}
        />
      )}

      {state === 'provider' && catalog && (
        <ProviderSelector
          projectId={projectId}
          catalog={catalog}
          recommendedId={inspection?.recommended_provider}
          onSelect={(p) => { setSelectedProvider(p); setState('provider_key'); }}
        />
      )}

      {state === 'provider_key' && selectedProvider && (
        <CredentialCapture
          projectId={projectId}
          provider={selectedProvider}
          onDone={() => setState('llm')}
          onBack={() => setState('provider')}
        />
      )}

      {state === 'llm' && (
        <LlmKeyStep
          projectId={projectId}
          onDone={() => setState('consent')}
        />
      )}

      {state === 'consent' && (
        <ConsentStep
          projectId={projectId}
          onDone={() => {
            setState('ready');
            onCompleted && onCompleted();
          }}
        />
      )}
    </div>
  );
}
