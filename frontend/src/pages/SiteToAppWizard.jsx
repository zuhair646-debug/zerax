/**
 * SiteToAppWizard — multi-step converter that takes a website (existing
 * Zenrex project OR external URL) and turns it into a mobile app project.
 *
 * Steps:
 *   1. Source — pick from "my projects" or paste an external URL.
 *   2. Scan — show what the AI found + features detected.
 *   3. Tech — pick platform (iOS/Android/Both) + stack (PWA/RN/Flutter/Native).
 *   4. Plan — confirm category + see phased plan + info we'll need from user.
 *   5. Start — provisions a new app project and redirects to chat.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, Globe, Link2, ArrowRight, ArrowLeft, Smartphone, Apple, Bot, CheckCircle2, AlertTriangle, KeyRound, Sparkles, Folder } from 'lucide-react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import ZenrexBrand from '../components/ZenrexBrand';
import StorageIndicator from '../components/StorageIndicator';
import TermsGate from '../components/TermsGate';

const API = process.env.REACT_APP_BACKEND_URL;

const TECH_STACKS = [
  { id: 'pwa',            label: 'PWA (موصى به)',         desc: 'يشتغل فوراً على iPhone + Android بدون متجر', emoji: '⚡', recommended: true },
  { id: 'react_native',   label: 'React Native',           desc: 'تطبيق Native بـ JavaScript', emoji: '⚛️' },
  { id: 'flutter',        label: 'Flutter',                desc: 'تطبيق Native بـ Dart من Google', emoji: '🐦' },
  { id: 'native_ios',     label: 'Native iOS (Swift)',     desc: 'تطبيق iOS أصلي', emoji: '🍎' },
  { id: 'native_android', label: 'Native Android (Kotlin)',desc: 'تطبيق Android أصلي', emoji: '🤖' },
];

const CATEGORIES = [
  { id: 'ecommerce',    emoji: '🛒', label: 'متجر إلكتروني' },
  { id: 'services',     emoji: '🛠️', label: 'خدمات / حجوزات' },
  { id: 'content',      emoji: '📰', label: 'محتوى / أخبار / مدوّنة' },
  { id: 'community',    emoji: '💬', label: 'مجتمع / تواصل' },
  { id: 'productivity', emoji: '✅', label: 'إنتاجية / أدوات' },
  { id: 'other',        emoji: '✨', label: 'غير ذلك' },
];

function StepBadge({ step, current, label }) {
  const done = current > step;
  const active = current === step;
  return (
    <div className="flex flex-col items-center gap-1" data-testid={`wizard-step-${step}`}>
      <div className={`w-9 h-9 rounded-full flex items-center justify-center font-black text-sm border-2 ${
        done ? 'bg-emerald-500 border-emerald-400 text-black' :
        active ? 'bg-amber-400 border-amber-300 text-black' :
        'bg-zinc-900 border-zinc-700 text-zinc-500'
      }`}>
        {done ? '✓' : step}
      </div>
      <span className={`text-[10px] font-bold ${active ? 'text-amber-300' : done ? 'text-emerald-400' : 'text-zinc-600'}`}>{label}</span>
    </div>
  );
}

function WizardCore() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  // Step 1 state
  const [sourceMode, setSourceMode] = useState('url'); // 'url' | 'project'
  const [urlInput, setUrlInput] = useState('');
  const [myProjects, setMyProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  // Step 2 state — scan result
  const [scan, setScan] = useState(null);
  // Step 3 state
  const [platform, setPlatform] = useState('both');
  const [techStack, setTechStack] = useState('pwa');
  // Step 4 state
  const [category, setCategory] = useState('');
  const [appName, setAppName] = useState('');
  const [plan, setPlan] = useState(null);

  // Load user's existing projects for picker
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/login'); return; }
    fetch(`${API}/api/freebuild-chat/projects`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.ok ? r.json() : { projects: [] })
      .then((d) => {
        // Only show non-app projects with current_html (sites that can be converted)
        const candidates = (d.projects || []).filter((p) => (!p.mode || p.mode === 'website') && p.current_html);
        setMyProjects(candidates);
      })
      .catch(() => {});
  }, [navigate]);

  const doScan = async () => {
    setBusy(true);
    const token = localStorage.getItem('token');
    try {
      const body = sourceMode === 'url'
        ? { source: 'url', url: urlInput.trim() }
        : { source: 'project', project_id: selectedProjectId };
      const r = await fetch(`${API}/api/site-to-app/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'فشل الفحص'); return; }
      setScan(d);
      if (!appName) setAppName(`تطبيق ${(d.analysis.title || '').slice(0, 30)}`);
      setStep(2);
    } catch (e) {
      toast.error('فشل الاتصال');
    } finally {
      setBusy(false);
    }
  };

  const loadPlan = async () => {
    setBusy(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/site-to-app/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ scan_id: scan.scan_id, platform, tech_stack: techStack }),
      });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'فشل توليد الخطّة'); return; }
      setPlan(d.plan);
      setStep(4);
    } finally {
      setBusy(false);
    }
  };

  const startConversion = async () => {
    setBusy(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/site-to-app/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          scan_id: scan.scan_id,
          platform,
          tech_stack: techStack,
          category,
          app_name: appName,
        }),
      });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'فشل البدء'); return; }
      toast.success('تم إنشاء المشروع 🎉');
      navigate(`/freebuild/chat/${d.project_id}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" dir="rtl" data-testid="site-to-app-wizard">
      <header className="sticky top-0 z-30 border-b border-white/10 bg-zinc-950/85 backdrop-blur">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <a href="/" className="hover:opacity-90"><ZenrexBrand size={26} /></a>
          <div className="flex items-center gap-2">
            <StorageIndicator compact />
            <a
              href="/freebuild/projects"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 text-xs font-bold"
            >
              <Folder className="w-4 h-4" />
              <span className="hidden sm:inline">مشاريعي</span>
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl sm:text-3xl font-black bg-gradient-to-l from-purple-400 to-pink-400 bg-clip-text text-transparent">
            🔁 محوّل المواقع إلى تطبيقات
          </h1>
          <p className="text-zinc-400 text-sm mt-2">حوّل أي موقع جاهز إلى تطبيق جوال بدون كتابة سطر كود</p>
        </div>

        {/* Stepper */}
        <div className="flex items-center justify-center gap-3 sm:gap-6 mb-10">
          <StepBadge step={1} current={step} label="المصدر" />
          <div className="w-8 h-px bg-zinc-700" />
          <StepBadge step={2} current={step} label="الفحص" />
          <div className="w-8 h-px bg-zinc-700" />
          <StepBadge step={3} current={step} label="التقنية" />
          <div className="w-8 h-px bg-zinc-700" />
          <StepBadge step={4} current={step} label="الخطّة" />
        </div>

        {/* STEP 1 — Source */}
        {step === 1 && (
          <Card className="bg-zinc-900 border-white/10 p-6" data-testid="step-1-source">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
              <button
                type="button"
                onClick={() => setSourceMode('project')}
                data-testid="src-project"
                className={`p-4 rounded-xl border text-right transition ${sourceMode === 'project' ? 'border-amber-400 bg-amber-500/10' : 'border-zinc-800 bg-zinc-950 hover:border-zinc-700'}`}
              >
                <Globe className="w-6 h-6 text-amber-400 mb-2" />
                <h3 className="font-black text-sm mb-1">من مشاريعي السابقة</h3>
                <p className="text-[11px] text-zinc-400">موقع بنيته سابقاً مع زنركس</p>
                <span className="text-[10px] text-amber-300 font-bold">{myProjects.length} موقع متاح</span>
              </button>
              <button
                type="button"
                onClick={() => setSourceMode('url')}
                data-testid="src-url"
                className={`p-4 rounded-xl border text-right transition ${sourceMode === 'url' ? 'border-amber-400 bg-amber-500/10' : 'border-zinc-800 bg-zinc-950 hover:border-zinc-700'}`}
              >
                <Link2 className="w-6 h-6 text-purple-400 mb-2" />
                <h3 className="font-black text-sm mb-1">من رابط موقع خارجي</h3>
                <p className="text-[11px] text-zinc-400">الصق رابط أي موقع تملكه</p>
              </button>
            </div>

            {sourceMode === 'url' ? (
              <div>
                <label className="text-xs text-zinc-400 mb-2 block">رابط الموقع</label>
                <Input
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="example.com أو https://mysite.com"
                  data-testid="url-input"
                  className="bg-zinc-950 border-zinc-700 text-white"
                />
                <p className="text-[10px] text-zinc-500 mt-2">⚠️ تأكد أنك مالك الموقع — تحويل موقع لا تملكه مخالف قانونياً.</p>
              </div>
            ) : (
              <div className="max-h-80 overflow-y-auto space-y-2" data-testid="project-picker">
                {myProjects.length === 0 ? (
                  <p className="text-center text-sm text-zinc-500 py-8">ما عندك مواقع جاهزة. ابني واحد أولاً أو استخدم رابط خارجي.</p>
                ) : myProjects.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setSelectedProjectId(p.id)}
                    data-testid={`pick-project-${p.id}`}
                    className={`w-full p-3 rounded-lg border text-right flex items-center justify-between ${selectedProjectId === p.id ? 'border-amber-400 bg-amber-500/10' : 'border-zinc-800 bg-zinc-950 hover:border-zinc-700'}`}
                  >
                    <div className="flex items-center gap-3">
                      <Globe className="w-4 h-4 text-emerald-400" />
                      <div>
                        <div className="font-bold text-sm">{p.name}</div>
                        <div className="text-[10px] text-zinc-500">{(p.description || '').slice(0, 60)}</div>
                      </div>
                    </div>
                    {selectedProjectId === p.id && <CheckCircle2 className="w-5 h-5 text-amber-400" />}
                  </button>
                ))}
              </div>
            )}

            <div className="mt-6 flex justify-end">
              <Button
                onClick={doScan}
                data-testid="scan-btn"
                disabled={busy || (sourceMode === 'url' ? !urlInput.trim() : !selectedProjectId)}
                className="bg-gradient-to-l from-purple-500 to-pink-500 hover:from-purple-400 hover:to-pink-400 text-white font-black"
              >
                {busy ? <Loader2 className="w-4 h-4 animate-spin ml-2" /> : <ArrowRight className="w-4 h-4 ml-2" />}
                ابدأ الفحص
              </Button>
            </div>
          </Card>
        )}

        {/* STEP 2 — Scan results */}
        {step === 2 && scan && (
          <Card className="bg-zinc-900 border-white/10 p-6" data-testid="step-2-scan">
            <h2 className="text-lg font-black mb-1">📊 نتيجة الفحص</h2>
            <p className="text-xs text-zinc-400 mb-5">{scan.source_label}</p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3">
                <div className="text-[10px] text-emerald-400 font-bold mb-1">العنوان</div>
                <div className="text-xs text-white truncate" title={scan.analysis.title}>{scan.analysis.title}</div>
              </div>
              <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-3">
                <div className="text-[10px] text-cyan-400 font-bold mb-1">اللغة</div>
                <div className="text-xs text-white">{scan.analysis.lang}</div>
              </div>
              <div className="rounded-xl border border-purple-500/30 bg-purple-500/5 p-3">
                <div className="text-[10px] text-purple-400 font-bold mb-1">الصور</div>
                <div className="text-xs text-white">{scan.analysis.images_count}</div>
              </div>
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-3">
                <div className="text-[10px] text-rose-400 font-bold mb-1">روابط القائمة</div>
                <div className="text-xs text-white">{scan.analysis.nav_links.length}</div>
              </div>
            </div>

            <div className="mb-5">
              <h3 className="text-sm font-bold text-amber-300 mb-2">الميزات المكتشفة:</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(scan.analysis.features).map(([k, v]) => (
                  <span
                    key={k}
                    data-testid={`feature-${k}`}
                    className={`text-[11px] px-2.5 py-1 rounded-full border ${v ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300' : 'bg-zinc-900 border-zinc-700 text-zinc-500'}`}
                  >
                    {v ? '✓' : '✗'} {{
                      ecommerce: 'متجر إلكتروني',
                      booking: 'حجوزات',
                      blog: 'مدوّنة',
                      contact_form: 'نموذج تواصل',
                      video: 'فيديوهات',
                      auth: 'تسجيل دخول',
                    }[k] || k}
                  </span>
                ))}
              </div>
            </div>

            <div className="flex justify-between">
              <Button onClick={() => setStep(1)} variant="ghost" className="text-zinc-400">
                <ArrowLeft className="w-4 h-4 ml-1" /> رجوع
              </Button>
              <Button
                onClick={() => setStep(3)}
                data-testid="goto-step-3"
                className="bg-gradient-to-l from-purple-500 to-pink-500 text-white font-black"
              >
                التالي: اختر التقنية <ArrowRight className="w-4 h-4 mr-1" />
              </Button>
            </div>
          </Card>
        )}

        {/* STEP 3 — Tech */}
        {step === 3 && (
          <Card className="bg-zinc-900 border-white/10 p-6" data-testid="step-3-tech">
            <h2 className="text-lg font-black mb-1">⚙️ اختر التقنية</h2>
            <p className="text-xs text-zinc-400 mb-5">قرّر كيف تبي يتبني تطبيقك. PWA هو الأسرع والأرخص.</p>

            <div className="mb-6">
              <h3 className="text-xs font-bold text-zinc-400 mb-2">الأجهزة المستهدفة</h3>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'ios',     label: 'iPhone',     icon: <Apple className="w-4 h-4" /> },
                  { id: 'android', label: 'Android',    icon: <Bot className="w-4 h-4" /> },
                  { id: 'both',    label: 'الاثنين',    icon: <Smartphone className="w-4 h-4" /> },
                ].map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setPlatform(p.id)}
                    data-testid={`platform-${p.id}`}
                    className={`px-3 py-2 rounded-lg border text-xs font-bold flex items-center justify-center gap-1.5 ${platform === p.id ? 'border-amber-400 bg-amber-500/10 text-amber-300' : 'border-zinc-700 bg-zinc-950 text-zinc-400'}`}
                  >
                    {p.icon} {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-6">
              <h3 className="text-xs font-bold text-zinc-400 mb-2">نوع البرمجة</h3>
              <div className="space-y-2">
                {TECH_STACKS.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setTechStack(t.id)}
                    data-testid={`tech-${t.id}`}
                    className={`w-full p-3 rounded-lg border text-right flex items-center justify-between transition ${techStack === t.id ? 'border-amber-400 bg-amber-500/10' : 'border-zinc-800 bg-zinc-950 hover:border-zinc-700'}`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{t.emoji}</span>
                      <div>
                        <div className="font-bold text-sm flex items-center gap-2">
                          {t.label}
                          {t.recommended && <span className="text-[9px] bg-emerald-500 text-black px-1.5 py-0.5 rounded-full font-black">موصى به</span>}
                        </div>
                        <div className="text-[10px] text-zinc-500">{t.desc}</div>
                      </div>
                    </div>
                    {techStack === t.id && <CheckCircle2 className="w-5 h-5 text-amber-400" />}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-between">
              <Button onClick={() => setStep(2)} variant="ghost" className="text-zinc-400">
                <ArrowLeft className="w-4 h-4 ml-1" /> رجوع
              </Button>
              <Button
                onClick={loadPlan}
                data-testid="goto-step-4"
                disabled={busy}
                className="bg-gradient-to-l from-purple-500 to-pink-500 text-white font-black"
              >
                {busy ? <Loader2 className="w-4 h-4 animate-spin ml-2" /> : <ArrowRight className="w-4 h-4 ml-2" />}
                التالي: اعرض الخطّة
              </Button>
            </div>
          </Card>
        )}

        {/* STEP 4 — Plan */}
        {step === 4 && plan && (
          <Card className="bg-zinc-900 border-white/10 p-6" data-testid="step-4-plan">
            <h2 className="text-lg font-black mb-1">📋 الخطّة النهائية</h2>
            <p className="text-xs text-zinc-400 mb-5">
              راح يستغرق التحويل تقريباً <span className="text-amber-400 font-bold">{plan.estimated_total_minutes} دقيقة</span> من العمل التفاعلي معك.
            </p>

            <div className="mb-5">
              <label className="text-xs font-bold text-zinc-400 mb-2 block">اسم التطبيق</label>
              <Input
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                placeholder="مثال: متجر العزم"
                data-testid="app-name-input"
                className="bg-zinc-950 border-zinc-700"
              />
            </div>

            <div className="mb-5">
              <label className="text-xs font-bold text-zinc-400 mb-2 block">تصنيف التطبيق</label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {CATEGORIES.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setCategory(c.id)}
                    data-testid={`cat-${c.id}`}
                    className={`p-2.5 rounded-lg border text-right ${category === c.id ? 'border-amber-400 bg-amber-500/10' : 'border-zinc-800 bg-zinc-950 hover:border-zinc-700'}`}
                  >
                    <div className="text-xl mb-0.5">{c.emoji}</div>
                    <div className="text-xs font-bold">{c.label}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-5">
              <h3 className="text-sm font-bold text-emerald-300 mb-2 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4" /> المراحل ({plan.phases.length})
              </h3>
              <ol className="space-y-2">
                {plan.phases.map((p) => (
                  <li key={p.id} data-testid={`plan-phase-${p.id}`} className="flex gap-3 text-xs text-zinc-300 leading-relaxed">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-emerald-500/15 border border-emerald-400/40 text-emerald-300 text-[10px] font-black flex items-center justify-center">
                      {p.id}
                    </span>
                    <span className="flex-1">
                      <b>{p.title}</b> — {p.summary}{' '}
                      <span className="text-zinc-500">(~{p.estimated_minutes}د)</span>
                    </span>
                  </li>
                ))}
              </ol>
            </div>

            {plan.must_collect.length > 0 && (
              <div className="mb-5 rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-4">
                <h3 className="text-sm font-bold text-cyan-300 mb-2 flex items-center gap-1.5">
                  <KeyRound className="w-4 h-4" /> المعلومات اللي راح أطلبها منك
                </h3>
                <ul className="space-y-1.5">
                  {plan.must_collect.map((it, i) => (
                    <li key={i} className="text-xs text-cyan-100/80 flex gap-2">
                      <span className="text-cyan-400">•</span>
                      <span><b>{it.label}</b> — <span className="text-zinc-400">{it.why}</span></span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {plan.cant_auto_convert.length > 0 && (
              <div className="mb-5 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
                <h3 className="text-sm font-bold text-amber-300 mb-2 flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4" /> أمور لا يمكن تحويلها تلقائياً
                </h3>
                <ul className="space-y-1">
                  {plan.cant_auto_convert.map((c, i) => (
                    <li key={i} className="text-xs text-amber-100/80">• {c}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex justify-between gap-2">
              <Button onClick={() => setStep(3)} variant="ghost" className="text-zinc-400">
                <ArrowLeft className="w-4 h-4 ml-1" /> رجوع
              </Button>
              <Button
                onClick={startConversion}
                data-testid="start-conversion-btn"
                disabled={busy || !category || !appName.trim()}
                className="bg-gradient-to-l from-emerald-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-black font-black"
              >
                {busy ? <Loader2 className="w-4 h-4 animate-spin ml-2" /> : <CheckCircle2 className="w-4 h-4 ml-2" />}
                ابدأ التحويل 🚀
              </Button>
            </div>
          </Card>
        )}
      </main>
    </div>
  );
}

export default function SiteToAppWizard() {
  return (
    <TermsGate section="site_to_app">
      <WizardCore />
    </TermsGate>
  );
}
