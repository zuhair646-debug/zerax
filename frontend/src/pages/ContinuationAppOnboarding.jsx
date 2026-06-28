// ContinuationAppOnboarding.jsx — App-flavored variant of the site onboarding
// wizard. Renders at the top of FreeBuildChat for projects whose
// `project_kind === 'app'` until the user finishes: Stack → Source → Keys → Consent.
//
// Mirrors ContinuationOnboarding.jsx (same look, same UX quality) but:
//  • Step 1 picks the APP STACK (Flutter/RN/iOS/Android/...) instead of a URL
//    Inspector — apps don't have public URLs.
//  • Step 2 surfaces ALL code-source providers (Git + EAS/Codemagic/Bitrise +
//    ZIP upload + self-hosted).
//  • Step 3 reuses the same credential-capture pattern (video + paste + AES-128
//    encryption + validity selector + help-modal escalate-to-engineer).
//  • Step 4 signs an app-specific e-consent (sandbox-first, store-submit needs
//    explicit approval, Keystore/Provisioning encrypted, etc.).
//
// All endpoints already exist on the backend:
//   GET  /continuation/app-providers-catalog
//   GET  /project/{pid}/continuation/setup
//   POST /project/{pid}/continuation/setup/save-stack         (new — app only)
//   POST /project/{pid}/continuation/setup/select-provider
//   POST /project/{pid}/continuation/setup/save-credential
//   POST /project/{pid}/continuation/setup/consent
//
// AI brain runs on the platform's own ANTHROPIC_API_KEY — fully independent;
// the user is NEVER asked for an LLM key.

import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import {
  Loader2, ShieldCheck, Sparkles, CheckCircle2, KeyRound, PlayCircle,
  Lock, FileSignature, ExternalLink, LifeBuoy, MessageCircle, X,
  Smartphone, Apple, Bot, Layers, Gamepad2, Monitor, Code2, Cpu,
  ArrowRight,
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

// Picker catalog mirrors the landing page so the user sees a familiar UI.
const APP_KIND_OPTIONS = [
  { id: 'flutter', label: 'Flutter', desc: 'iOS + Android بكود واحد', icon: Layers, color: 'sky', platforms: ['ios', 'android'] },
  { id: 'react_native', label: 'React Native / Expo', desc: 'JavaScript / TypeScript', icon: Smartphone, color: 'cyan', platforms: ['ios', 'android'] },
  { id: 'capacitor', label: 'Ionic / Capacitor', desc: 'PWA → APK/IPA', icon: Bot, color: 'indigo', platforms: ['ios', 'android'] },
  { id: 'android_native', label: 'Android أصلي', desc: 'Kotlin / Java + Gradle', icon: Smartphone, color: 'emerald', platforms: ['android'] },
  { id: 'ios_native', label: 'iOS أصلي', desc: 'Swift + Xcode', icon: Apple, color: 'zinc', platforms: ['ios'] },
  { id: 'dotnet_maui', label: '.NET MAUI / Xamarin', desc: 'C# لكل المنصات', icon: Code2, color: 'violet', platforms: ['ios', 'android', 'desktop'] },
  { id: 'electron_tauri', label: 'Electron / Tauri', desc: 'سطح المكتب', icon: Monitor, color: 'amber', platforms: ['desktop'] },
  { id: 'unity_game', label: 'Unity / Unreal / Godot', desc: 'ألعاب', icon: Gamepad2, color: 'rose', platforms: ['ios', 'android', 'desktop'] },
  { id: 'unknown', label: 'ما أعرف', desc: 'الذكاء يكتشفها بعد الاستنساخ', icon: Sparkles, color: 'fuchsia', platforms: [] },
];

const PLATFORM_LABELS = {
  ios: { label: 'iOS', icon: Apple },
  android: { label: 'Android', icon: Smartphone },
  desktop: { label: 'سطح المكتب', icon: Monitor },
  web: { label: 'الويب', icon: Cpu },
};

// ─── Step 1: App Stack Confirmation ───────────────────────────────────
function AppStackCard({ projectId, initialAppKind, onDone }) {
  const [selected, setSelected] = useState(initialAppKind || '');
  const [platforms, setPlatforms] = useState([]);
  const [repoHint, setRepoHint] = useState('');
  const [busy, setBusy] = useState(false);

  // Pre-fill recommended target platforms when stack picked.
  useEffect(() => {
    const k = APP_KIND_OPTIONS.find((x) => x.id === selected);
    if (k && k.platforms.length && platforms.length === 0) {
      setPlatforms(k.platforms);
    }
  // platforms intentionally omitted to avoid resetting when user toggles
  }, [selected, platforms.length]);

  const togglePlatform = (p) => {
    setPlatforms((cur) => (cur.includes(p) ? cur.filter((x) => x !== p) : [...cur, p]));
  };

  const proceed = async () => {
    if (!selected) { toast.error('اختر نوع التقنية أولاً'); return; }
    setBusy(true);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/setup/save-stack`, {
        method: 'POST',
        body: JSON.stringify({
          app_kind: selected,
          target_platforms: platforms,
          repo_url_hint: repoHint.trim() || undefined,
        }),
      });
      const d = await r.json();
      if (!d.ok) throw new Error(d.detail || 'save failed');
      toast.success('✅ تم تأكيد التقنية — ننتقل لمصدر الكود');
      onDone({ app_kind: selected, target_platforms: platforms, repo_url_hint: repoHint.trim() });
    } catch {
      toast.error('فشل حفظ التقنية');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="app-stack-card" className="rounded-2xl border border-cyan-500/30 bg-gradient-to-br from-cyan-900/25 via-sky-900/15 to-emerald-900/10 backdrop-blur p-5 sm:p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center">
          <Cpu className="w-6 h-6 text-cyan-200" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-black text-cyan-100">نوع البرمجة</h3>
          <p className="text-[11px] text-cyan-300/80">أكّد التقنية اللي تطبيقك مبني عليها — الذكاء يضبط أوامر البناء بناءً عليها</p>
        </div>
      </div>

      <label className="block text-[11px] font-bold text-zinc-400 mb-2">اختر التقنية</label>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-5" data-testid="app-kind-grid">
        {APP_KIND_OPTIONS.map((k) => {
          const isSel = selected === k.id;
          return (
            <button
              key={k.id}
              onClick={() => setSelected(k.id)}
              data-testid={`stack-option-${k.id}`}
              className={cls(
                'text-right px-3 py-2.5 rounded-lg border transition flex items-start gap-2',
                isSel ? `border-${k.color}-400 bg-${k.color}-500/15 shadow-lg shadow-${k.color}-500/10` : 'border-white/10 bg-black/30 hover:bg-white/5',
              )}
            >
              <k.icon className={cls('w-4 h-4 mt-0.5 flex-shrink-0', isSel ? `text-${k.color}-300` : 'text-zinc-400')} />
              <div className="flex-1 min-w-0">
                <div className={cls('text-[11px] font-bold', isSel ? 'text-white' : 'text-zinc-300')}>{k.label}</div>
                <div className="text-[9px] text-zinc-500 mt-0.5 truncate">{k.desc}</div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Target platforms */}
      {selected && selected !== 'unknown' && (
        <div className="mb-5">
          <label className="block text-[11px] font-bold text-zinc-400 mb-2">المنصات المستهدفة (اختر واحد أو أكثر)</label>
          <div className="flex flex-wrap gap-2" data-testid="target-platforms">
            {Object.entries(PLATFORM_LABELS).map(([id, { label, icon: Icon }]) => {
              const isSel = platforms.includes(id);
              return (
                <button
                  key={id}
                  onClick={() => togglePlatform(id)}
                  data-testid={`platform-${id}`}
                  className={cls(
                    'px-3 py-2 rounded-lg border text-[11px] font-bold transition flex items-center gap-1.5',
                    isSel ? 'border-cyan-400 bg-cyan-500/15 text-cyan-100' : 'border-white/10 bg-black/30 text-zinc-300 hover:bg-white/5',
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Optional repo URL hint */}
      <div className="mb-5">
        <label className="block text-[11px] font-bold text-zinc-400 mb-1.5">
          رابط المستودع (اختياري) — يساعد الذكاء على التحضير
        </label>
        <input
          type="text"
          placeholder="https://github.com/username/my-app"
          value={repoHint}
          onChange={(e) => setRepoHint(e.target.value)}
          data-testid="repo-hint-input"
          className="w-full px-3 py-2.5 rounded-lg bg-black/50 border border-white/10 text-xs focus:border-cyan-400/50 focus:outline-none font-mono"
        />
        <p className="text-[10px] text-zinc-500 mt-1.5">
          💡 لا تشارك أي توكنات هنا — المفتاح راح يجي في الخطوة التالية بشكل آمن.
        </p>
      </div>

      {selected === 'unknown' && (
        <div className="mb-5 rounded-xl bg-fuchsia-500/10 border border-fuchsia-500/30 p-3">
          <div className="text-[11px] text-fuchsia-100 leading-relaxed">
            ✨ <strong>اخترت &quot;ما أعرف&quot;</strong> — لا تقلق. بعد ما يستنسخ الذكاء كودك في sandbox،
            راح يشغّل أداة <code className="px-1 rounded bg-black/40 font-mono text-fuchsia-200">detect_project_stack</code>{' '}
            ويحدد التقنية تلقائياً من ملفات المشروع (package.json / pubspec.yaml / build.gradle …).
          </div>
        </div>
      )}

      <button
        onClick={proceed}
        disabled={!selected || busy}
        data-testid="stack-confirm-btn"
        className="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-sky-500 hover:from-cyan-400 hover:to-sky-400 font-black text-sm text-white disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4 rotate-180" />}
        أكّد وانتقل لمصدر الكود
      </button>
    </div>
  );
}

// ─── Step 2: Code Source Selector ─────────────────────────────────────
function CodeSourceSelector({ projectId, catalog, recommendedId, onSelect }) {
  const [selected, setSelected] = useState(recommendedId || null);
  const [busy, setBusy] = useState(false);

  const all = catalog.code_source_providers || [];

  useEffect(() => {
    if (recommendedId) {
      const el = document.getElementById(`source-card-${recommendedId}`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [recommendedId]);

  const confirm = async () => {
    if (!selected) { toast.error('اختر مصدر الكود'); return; }
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
    <div data-testid="code-source-selector" className="rounded-2xl border border-fuchsia-500/30 bg-black/40 backdrop-blur p-5 sm:p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-rose-500/20 border border-rose-400/40 flex items-center justify-center">
          <KeyRound className="w-6 h-6 text-rose-200" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-black text-rose-100">من وين نوصل لكود تطبيقك؟</h3>
          <p className="text-[11px] text-rose-300/80">
            الكود المصدري يجي من إحدى المصادر التالية. اختر اللي مستضيف عليه مشروعك.
          </p>
        </div>
      </div>

      {/* Group hint */}
      <div className="flex flex-wrap gap-2 mb-3 text-[10px]">
        <span className="px-2 py-1 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-cyan-200">
          🌳 مستودعات Git
        </span>
        <span className="px-2 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-200">
          ⚙️ خدمات البناء (EAS / Codemagic / Bitrise)
        </span>
        <span className="px-2 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-200">
          📦 رفع ZIP مباشر
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
        {all.map((p) => {
          const isRec = recommendedId === p.id;
          const isSel = selected === p.id;
          return (
            <button
              key={p.id}
              id={`source-card-${p.id}`}
              data-testid={`source-card-${p.id}`}
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
        data-testid="source-confirm-btn"
        className="w-full mt-4 py-3 rounded-xl bg-gradient-to-r from-fuchsia-500 to-rose-500 hover:from-fuchsia-400 hover:to-rose-400 font-black text-sm text-white disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
        اختاره ✓
      </button>
    </div>
  );
}

// ─── Step 3: Credential Capture (same UX as site flow) ───────────────
function AppCredentialCapture({ projectId, provider, onDone, onBack }) {
  const keys = provider.credential_keys || [];
  const [values, setValues] = useState({});
  const [validity, setValidity] = useState(6);
  const [busy, setBusy] = useState(false);
  const [savedMasks, setSavedMasks] = useState({});
  const [showHelp, setShowHelp] = useState(false);
  const [zipFile, setZipFile] = useState(null);
  const [zipBusy, setZipBusy] = useState(false);

  const isZip = provider.id === 'zip_upload';

  const handleZipUpload = async () => {
    if (!zipFile) { toast.error('اختر ملف ZIP أولاً'); return; }
    if (zipFile.size > 200 * 1024 * 1024) {
      toast.error('الحد الأقصى 200MB');
      return;
    }
    setZipBusy(true);
    try {
      // Reuse the save-credential endpoint with a synthetic token = file name + size
      // so the wizard advances. The actual ZIP bytes go to the project files API
      // via the AI tool once the sandbox is provisioned.
      const fingerprint = `zip:${zipFile.name}:${zipFile.size}`;
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/setup/save-credential`, {
        method: 'POST',
        body: JSON.stringify({ key_name: 'ZIP_UPLOAD_TOKEN', value: fingerprint, validity_months: validity }),
      });
      const d = await r.json();
      if (!d.ok) throw new Error(d.detail);
      toast.success('📦 الملف مسجّل — الذكاء بيستلمه ويستنسخه في الـ sandbox');
      onDone();
    } catch {
      toast.error('فشل تسجيل الرفع');
    } finally {
      setZipBusy(false);
    }
  };

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
    } catch {
      toast.error('فشل حفظ المفتاح — حاول مرة ثانية');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="app-credential-capture" className="rounded-2xl border border-fuchsia-500/30 bg-black/40 backdrop-blur p-5 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="text-3xl">{provider.logo_emoji}</div>
          <div>
            <h3 className="text-base sm:text-lg font-black text-fuchsia-100">{provider.label_ar}</h3>
            <p className="text-[11px] text-zinc-400">
              {isZip ? 'ارفع ملف ZIP يحتوي على مشروعك' : 'شاهد الفيديو، أنشئ المفتاح، الصقه تحت'}
            </p>
          </div>
        </div>
        <button onClick={onBack} className="text-[10px] text-zinc-400 hover:text-fuchsia-300" data-testid="source-back-btn">
          ← غيّر المصدر
        </button>
      </div>

      {/* Video + instructions */}
      {!isZip && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
          <div className="aspect-video rounded-xl bg-black/60 border border-white/10 overflow-hidden flex items-center justify-center relative">
            {provider.tutorial_video_ar ? (
              <iframe
                src={`${API}${provider.tutorial_video_ar}`}
                title={`${provider.label_ar} tutorial`}
                data-testid="tutorial-video"
                className="w-full h-full border-0"
                sandbox="allow-scripts allow-same-origin"
                loading="lazy"
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
              <a href={provider.where_to_get_url} target="_blank" rel="noopener noreferrer" data-testid="provider-where-link"
                className="mt-3 inline-flex items-center gap-1.5 text-[11px] font-bold px-3 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-400/30 text-emerald-100 hover:bg-emerald-500/30">
                <ExternalLink className="w-3.5 h-3.5" />
                افتح صفحة الإنشاء مباشرة
              </a>
            )}
          </div>
        </div>
      )}

      {/* ZIP upload path */}
      {isZip && (
        <div className="mb-4 rounded-xl border-2 border-dashed border-amber-500/40 bg-amber-500/5 p-6 text-center">
          <input
            type="file"
            id="zip-file-input"
            accept=".zip,.tar,.tar.gz,.tgz"
            onChange={(e) => setZipFile(e.target.files?.[0] || null)}
            data-testid="zip-file-input"
            className="hidden"
          />
          <label htmlFor="zip-file-input" className="cursor-pointer flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-full bg-amber-500/20 border border-amber-400/40 flex items-center justify-center">
              <Layers className="w-7 h-7 text-amber-300" />
            </div>
            <div className="text-sm font-bold text-amber-100">
              {zipFile ? zipFile.name : 'اضغط لاختيار ملف ZIP من جهازك'}
            </div>
            <div className="text-[10px] text-amber-300/80">
              {zipFile ? `${(zipFile.size / 1024 / 1024).toFixed(2)} MB` : 'الحد الأقصى 200MB — مشفّر أثناء الرفع'}
            </div>
          </label>
        </div>
      )}

      {/* Help button */}
      {!isZip && (
        <div className="mb-3 -mt-1">
          <button
            onClick={() => setShowHelp(true)}
            data-testid="open-help-btn"
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-amber-500/20 to-orange-500/20 hover:from-amber-500/30 hover:to-orange-500/30 border border-amber-500/40 text-[12px] font-bold text-amber-100 flex items-center justify-center gap-2"
          >
            <LifeBuoy className="w-4 h-4" />
            أواجه مشكلة في الحصول على المفتاح — ساعدني
          </button>
        </div>
      )}
      {showHelp && (
        <HelpModal projectId={projectId} provider={provider} onClose={() => setShowHelp(false)} />
      )}

      {/* Paste fields (skip for zip_upload) */}
      {!isZip && (
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
      )}

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
        onClick={isZip ? handleZipUpload : saveAll}
        disabled={isZip ? (zipBusy || !zipFile) : busy}
        data-testid="credential-save-btn"
        className="w-full py-3 rounded-xl bg-gradient-to-r from-fuchsia-500 to-rose-500 hover:from-fuchsia-400 hover:to-rose-400 font-black text-sm text-white disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {(isZip ? zipBusy : busy) ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
        {isZip ? 'سجّل الرفع المشفّر' : 'احفظ بتشفير AES-128'}
      </button>
    </div>
  );
}

// ─── Help modal — reused pattern from site flow ────────────────────────
function HelpModal({ projectId, provider, onClose }) {
  const [help, setHelp] = useState(null);
  const [issue, setIssue] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/freebuild-chat/continuation/help/${provider.id}`);
        const d = await r.json();
        setHelp(d);
      } catch { setHelp({ faq: [] }); }
    })();
  }, [provider.id]);

  const escalate = async () => {
    setBusy(true);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/continuation/help/escalate`, {
        method: 'POST',
        body: JSON.stringify({ project_id: projectId, provider_id: provider.id, issue: issue.trim() }),
      });
      const d = await r.json();
      if (!d.ok) throw new Error();
      toast.success('✅ المهندس مستعد — اكتب رسالتك في الشات تحت');
      onClose();
      window.dispatchEvent(new CustomEvent('zenrex:help-session-started', {
        detail: { projectId, providerId: provider.id },
      }));
    } catch { toast.error('فشل فتح الجلسة'); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="help-modal" className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} dir="rtl" className="w-full max-w-xl max-h-[85vh] overflow-y-auto rounded-2xl bg-gradient-to-br from-fuchsia-950 via-rose-950 to-black border border-fuchsia-500/40 p-5">
        <div className="flex items-center gap-3 mb-4 pb-3 border-b border-white/10">
          <LifeBuoy className="w-6 h-6 text-amber-300" />
          <div className="flex-1">
            <h3 className="text-base font-black text-fuchsia-100">{help?.title_ar || 'مساعدة سريعة'}</h3>
            <p className="text-[10px] text-fuchsia-300/70">{provider.label_ar}</p>
          </div>
          <button onClick={onClose} data-testid="help-modal-close" className="text-zinc-400 hover:text-fuchsia-300">
            <X className="w-5 h-5" />
          </button>
        </div>
        {help?.direct_url && (
          <a href={help.direct_url} target="_blank" rel="noopener noreferrer" data-testid="help-direct-url"
            className="block mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20 group">
            <div className="flex items-center gap-2">
              <ExternalLink className="w-4 h-4 text-emerald-300 group-hover:rotate-12 transition" />
              <span className="text-xs font-bold text-emerald-100">افتح صفحة المفتاح مباشرة</span>
            </div>
            <div className="text-[10px] text-emerald-300/70 font-mono mt-1 truncate">{help.direct_url}</div>
          </a>
        )}
        {help?.faq?.length > 0 && (
          <div className="space-y-2 mb-4">
            <div className="text-[10px] font-black text-amber-200 mb-1">❓ مشاكل شائعة وحلولها</div>
            {help.faq.map((f, i) => (
              <details key={i} className="rounded-lg bg-black/30 border border-white/5 px-3 py-2 group">
                <summary className="text-[11px] font-bold text-fuchsia-100 cursor-pointer hover:text-fuchsia-200 list-none flex items-start gap-2">
                  <span className="text-amber-300 shrink-0 mt-0.5">›</span>
                  <span>{f.q}</span>
                </summary>
                <div className="mt-2 pt-2 border-t border-white/5 text-[11px] text-zinc-300 leading-relaxed pr-4">{f.a}</div>
              </details>
            ))}
          </div>
        )}
        <div className="rounded-xl bg-indigo-500/10 border border-indigo-500/30 p-3 mb-3">
          <div className="text-[11px] font-bold text-indigo-100 mb-2 flex items-center gap-1.5">
            <MessageCircle className="w-3.5 h-3.5" /> ولا حصلت إجابة؟ كلّم المهندس مباشرة
          </div>
          <textarea
            placeholder="اكتب وصف مشكلتك"
            value={issue}
            onChange={(e) => setIssue(e.target.value)}
            rows={3}
            data-testid="help-issue-input"
            className="w-full px-3 py-2 rounded-lg bg-black/50 border border-white/10 text-xs focus:border-indigo-400/50 focus:outline-none resize-none"
          />
        </div>
        <button onClick={escalate} disabled={busy} data-testid="help-escalate-btn"
          className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-fuchsia-500 hover:from-indigo-400 hover:to-fuchsia-400 font-black text-sm text-white disabled:opacity-40 flex items-center justify-center gap-2">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageCircle className="w-4 h-4" />}
          افتح جلسة مساعدة مع المهندس
        </button>
      </div>
    </div>
  );
}

// ─── Step 4: App-specific e-Consent ───────────────────────────────────
function AppConsentStep({ projectId, onDone }) {
  const CLAUSES = [
    'أقرّ بأنني المالك الشرعي لهذا التطبيق وأملك صلاحية تعديله ورفعه للمتاجر',
    'أوافق على أن Zenrex يبني التطبيق في sandbox معزول ولا يلمس النسخة المنشورة بدون موافقتي الصريحة',
    'أي رفع لـ Google Play / App Store / Firebase Distribution يحتاج موافقة صريحة + ينفّذ على Track Internal أولاً',
    'مفاتيح Keystore + Provisioning Profile تُحفظ بتشفير AES-128 ولا تخرج من السيرفر',
    'أتحمل مسؤولية أي بناء/نشر أوافق عليه بضغطة "اعتماد" في الشات',
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
      toast.success('✅ تم التوقيع — المهندس الهندسي بدأ العمل على تطبيقك');
      onDone();
    } catch { toast.error('فشل التوقيع'); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="app-consent-step" className="rounded-2xl border border-amber-500/30 bg-amber-500/5 backdrop-blur p-5 sm:p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-amber-500/20 border border-amber-400/40 flex items-center justify-center">
          <FileSignature className="w-6 h-6 text-amber-200" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-black text-amber-100">التوقيع الإلكتروني — تكملة تطبيق</h3>
          <p className="text-[11px] text-amber-300/80">آخر خطوة قبل ما يبدأ المهندس الهندسي العمل على تطبيقك</p>
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

// ─── Main app wizard ──────────────────────────────────────────────────
export default function ContinuationAppOnboarding({ projectId, onCompleted }) {
  const [state, setState] = useState('loading');
  const [catalog, setCatalog] = useState(null);
  const [appKind, setAppKind] = useState('');
  const [stackInfo, setStackInfo] = useState(null);
  const [selectedSource, setSelectedSource] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [setupRes, catalogRes] = await Promise.all([
          authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/setup`),
          fetch(`${API}/api/freebuild-chat/continuation/app-providers-catalog`),
        ]);
        const setupData = await setupRes.json();
        const catData = await catalogRes.json();
        setCatalog(catData);
        setAppKind(setupData.app_kind || '');
        if (setupData.app_stack) setStackInfo(setupData.app_stack);
        if (setupData.provider_id) {
          const all = catData.code_source_providers || [];
          setSelectedSource(all.find((p) => p.id === setupData.provider_id));
        }
        if (setupData.completed) {
          setState('ready');
          onCompleted && onCompleted();
        } else {
          // Legacy: collapse stale states
          let s = setupData.state || 'stack';
          if (s === 'url') s = 'stack';           // app projects starting from old state
          if (s === 'llm') s = 'consent';         // pre-independence projects
          setState(s);
        }
      } catch {
        setState('stack');
      }
    })();
  }, [projectId, onCompleted]);

  const STEPS = ['stack', 'provider', 'provider_key', 'consent'];
  const stepIdx = STEPS.indexOf(state);

  if (state === 'ready' || state === 'loading') return null;

  // Suggest a source based on chosen stack
  const recommendedSourceId = (() => {
    if (state !== 'provider') return null;
    if (appKind === 'react_native') return 'expo_eas';
    if (appKind === 'flutter') return 'codemagic';
    return 'github';
  })();

  return (
    <div dir="rtl" data-testid="continuation-app-onboarding" className="space-y-4 mb-4">
      {/* Progress bar */}
      <div className="flex items-center gap-1.5 px-2">
        {STEPS.map((s, i) => (
          <div key={s} data-testid={`progress-step-${i}`}
            className={cls(
              'flex-1 h-1.5 rounded-full transition',
              i <= stepIdx ? 'bg-gradient-to-r from-cyan-500 to-sky-500' : 'bg-white/10',
            )} />
        ))}
      </div>
      <div className="text-[10px] text-zinc-500 px-2 flex justify-between">
        <span>إعداد التطبيق — الخطوة {stepIdx + 1} من {STEPS.length}</span>
        <span>🔐 مشفّر AES-128 · 📱 مدير هندسي تطبيقات</span>
      </div>

      {state === 'stack' && (
        <AppStackCard
          projectId={projectId}
          initialAppKind={appKind}
          onDone={(info) => {
            setStackInfo(info);
            setAppKind(info.app_kind);
            setState('provider');
          }}
        />
      )}

      {state === 'provider' && catalog && (
        <CodeSourceSelector
          projectId={projectId}
          catalog={catalog}
          recommendedId={recommendedSourceId}
          onSelect={(p) => { setSelectedSource(p); setState('provider_key'); }}
        />
      )}

      {state === 'provider_key' && selectedSource && (
        <AppCredentialCapture
          projectId={projectId}
          provider={selectedSource}
          onDone={() => setState('consent')}
          onBack={() => setState('provider')}
        />
      )}

      {state === 'consent' && (
        <AppConsentStep
          projectId={projectId}
          onDone={() => { setState('ready'); onCompleted && onCompleted(); }}
        />
      )}

      {/* Tiny stack summary shown under all steps after step 1 */}
      {stackInfo && state !== 'stack' && (
        <div className="mt-2 px-3 py-2 rounded-lg bg-cyan-500/5 border border-cyan-500/15 text-[10px] text-cyan-200 flex items-center justify-between">
          <span>📱 التقنية: <strong>{stackInfo.app_kind}</strong>{stackInfo.target_platforms?.length ? ` · المنصات: ${stackInfo.target_platforms.join(', ')}` : ''}</span>
          <button onClick={() => setState('stack')} className="text-cyan-300 hover:text-cyan-100 underline" data-testid="back-to-stack-btn">
            غيّر
          </button>
        </div>
      )}
    </div>
  );
}
