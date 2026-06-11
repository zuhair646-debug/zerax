import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import {
  ArrowLeft, RefreshCw, Loader2, Brain, CheckCircle2, AlertTriangle,
  XCircle, ExternalLink, Rocket, Database, ShieldCheck, Zap, Radio,
  Image as ImageIcon, Layers3, Code2, Copy, Sparkles, ServerCog,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const LINKS = {
  sentry: 'https://sentry.io/settings/projects/',
  cloudflare_r2: 'https://dash.cloudflare.com/',
  openrouter: 'https://openrouter.ai/settings/keys',
  redis_queue: 'https://railway.app/new/plugin/redis',
  livekit: 'https://cloud.livekit.io/projects/p_/settings/keys',
  resend: 'https://resend.com/api-keys',
  fal_runway_luma_heygen: 'https://fal.ai/dashboard/keys',
  vector_db: 'https://www.pinecone.io/start/',
  posthog: 'https://app.posthog.com/project/settings',
  twilio_whatsapp: 'https://console.twilio.com/',
};

const ICONS = {
  sentry: ShieldCheck,
  cloudflare_r2: Database,
  openrouter: Layers3,
  redis_queue: ServerCog,
  livekit: Radio,
  resend: Sparkles,
  fal_runway_luma_heygen: ImageIcon,
  vector_db: Brain,
  posthog: Zap,
  twilio_whatsapp: Rocket,
};

const STATUS = {
  configured: { label: 'مكتمل', icon: CheckCircle2, cls: 'text-emerald-300 bg-emerald-500/10 border-emerald-400/20' },
  partial: { label: 'جزئي', icon: AlertTriangle, cls: 'text-amber-300 bg-amber-500/10 border-amber-400/20' },
  missing: { label: 'ناقص', icon: XCircle, cls: 'text-rose-300 bg-rose-500/10 border-rose-400/20' },
};

const priorityLabel = {
  critical: 'حرج',
  high: 'مهم',
  medium: 'متوسط',
  optional: 'اختياري',
};

function StatusPill({ status }) {
  const s = STATUS[status] || STATUS.missing;
  const Icon = s.icon;
  return <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-bold ${s.cls}`}><Icon className="h-3.5 w-3.5" />{s.label}</span>;
}

export default function AdminAIReadiness() {
  const navigate = useNavigate();
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const [capabilities, setCapabilities] = useState(null);
  const [roadmap, setRoadmap] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [capRes, roadRes] = await Promise.all([
        fetch(`${API}/api/autocoder-meta/capabilities`, { headers }),
        fetch(`${API}/api/autocoder-meta/roadmap`, { headers }),
      ]);
      if (capRes.status === 403 || roadRes.status === 403) {
        toast.error('هذه اللوحة للمالك فقط');
        navigate('/dashboard');
        return;
      }
      if (!capRes.ok || !roadRes.ok) throw new Error('فشل تحميل تقرير جاهزية الذكاء');
      setCapabilities(await capRes.json());
      setRoadmap(await roadRes.json());
    } catch (error) {
      toast.error(error.message || 'فشل تحميل البيانات');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token) { navigate('/login'); return; }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stats = useMemo(() => {
    const integrations = capabilities?.recommended_integrations || [];
    const configured = integrations.filter((i) => i.status === 'configured').length;
    const partial = integrations.filter((i) => i.status === 'partial').length;
    const missing = integrations.filter((i) => i.status === 'missing').length;
    const score = integrations.length ? Math.round(((configured + partial * 0.5) / integrations.length) * 100) : 0;
    return { total: integrations.length, configured, partial, missing, score };
  }, [capabilities]);

  const copyEnv = async (names = []) => {
    const text = names.map((name) => `${name}=`).join('\n');
    await navigator.clipboard.writeText(text);
    toast.success('تم نسخ أسماء المتغيرات');
  };

  if (loading || !capabilities || !roadmap) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
        <Loader2 className="h-7 w-7 animate-spin text-amber-400" />
      </div>
    );
  }

  return (
    <div dir="rtl" className="min-h-screen bg-zinc-950 text-white">
      <Toaster richColors position="top-center" />
      <header className="sticky top-0 z-20 border-b border-white/10 bg-black/50 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <button data-testid="ai-readiness-back" onClick={() => navigate('/admin')} className="rounded-xl bg-white/5 p-2 hover:bg-white/10">
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <h1 className="flex items-center gap-2 text-lg font-black md:text-xl">
                <Brain className="h-5 w-5 text-amber-400" /> جاهزية الذكاء في Zenrex
              </h1>
              <p className="text-xs text-zinc-400">قدرات برمجة زيتاكس، النواقص، وروابط الارتقاء</p>
            </div>
          </div>
          <button data-testid="refresh-ai-readiness" onClick={load} className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10">
            <RefreshCw className="h-4 w-4" /> تحديث
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <section className="mb-8 grid gap-4 lg:grid-cols-[1.3fr_.7fr]">
          <div className="rounded-3xl border border-amber-400/20 bg-gradient-to-br from-amber-500/15 via-zinc-900 to-zinc-950 p-6 md:p-8">
            <div className="mb-4 inline-flex rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-xs font-bold text-amber-200">تقرير حي من الإنتاج</div>
            <h2 className="mb-3 text-3xl font-black md:text-4xl">جاهزية الذكاء: {stats.score}%</h2>
            <p className="max-w-3xl leading-8 text-zinc-300">{capabilities.summary_ar}</p>
            <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
              <div className="rounded-2xl bg-black/30 p-4"><div className="text-2xl font-black text-emerald-300">{stats.configured}</div><div className="text-xs text-zinc-400">مكتمل</div></div>
              <div className="rounded-2xl bg-black/30 p-4"><div className="text-2xl font-black text-amber-300">{stats.partial}</div><div className="text-xs text-zinc-400">جزئي</div></div>
              <div className="rounded-2xl bg-black/30 p-4"><div className="text-2xl font-black text-rose-300">{stats.missing}</div><div className="text-xs text-zinc-400">ناقص</div></div>
              <div className="rounded-2xl bg-black/30 p-4"><div className="text-2xl font-black text-white">{capabilities.llm_providers.filter((p) => p.configured).length}</div><div className="text-xs text-zinc-400">مزودي AI</div></div>
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-zinc-900/60 p-6">
            <h3 className="mb-4 flex items-center gap-2 text-xl font-black"><Code2 className="h-5 w-5 text-amber-400" /> شكل التنفيذ الجديد</h3>
            <ol className="space-y-3 text-sm text-zinc-300">
              <li>1) أفهم طلبك وأشرح وش ببني.</li>
              <li>2) أحدد المميزات والخدمات والواجهات.</li>
              <li>3) أنفذ الكود والاختبارات والنشر.</li>
              <li>4) أختم بمربع خلاصة: روابط + نصائح + التالي.</li>
            </ol>
          </div>
        </section>

        <section className="mb-8 rounded-3xl border border-white/10 bg-zinc-900/50 p-6">
          <h3 className="mb-5 text-xl font-black">مزودو الذكاء الحاليون</h3>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {capabilities.llm_providers.map((provider) => (
              <div key={provider.id} className="rounded-2xl border border-white/10 bg-black/25 p-4">
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div>
                    <h4 className="font-black">{provider.name}</h4>
                    <p className="text-xs text-zinc-500">{provider.priority}</p>
                  </div>
                  <StatusPill status={provider.configured ? 'configured' : 'missing'} />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {provider.best_for.map((tag) => <span key={tag} className="rounded-full bg-white/5 px-2 py-1 text-[11px] text-zinc-300">{tag}</span>)}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-8">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="text-xl font-black">النواقص المطلوبة للمرحلة الأعلى</h3>
            <p className="text-xs text-zinc-500">الأسرار لا تظهر هنا؛ فقط الأسماء والحالة</p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {capabilities.recommended_integrations.map((item) => {
              const Icon = ICONS[item.id] || Sparkles;
              const link = LINKS[item.id];
              return (
                <div key={item.id} data-testid={`integration-${item.id}`} className="rounded-3xl border border-white/10 bg-zinc-900/50 p-5">
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <div className="flex gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-amber-400/10 text-amber-300"><Icon className="h-5 w-5" /></div>
                      <div>
                        <h4 className="font-black">{item.name}</h4>
                        <p className="text-xs text-zinc-500">أولوية: {priorityLabel[item.priority] || item.priority}</p>
                      </div>
                    </div>
                    <StatusPill status={item.status} />
                  </div>
                  <p className="mb-4 text-sm leading-7 text-zinc-300">{item.why_ar}</p>
                  <div className="mb-4 flex flex-wrap gap-1.5">
                    {item.env_vars.map((env) => <code key={env} className="rounded-lg bg-black/40 px-2 py-1 text-xs text-amber-100">{env}</code>)}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {link && <a href={link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-3 py-2 text-sm font-bold text-black hover:bg-amber-400"><ExternalLink className="h-4 w-4" /> افتح الرابط</a>}
                    <button onClick={() => copyEnv(item.env_vars)} className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10"><Copy className="h-4 w-4" /> انسخ المتغيرات</button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="mb-8 rounded-3xl border border-white/10 bg-zinc-900/50 p-6">
          <h3 className="mb-5 flex items-center gap-2 text-xl font-black"><Rocket className="h-5 w-5 text-amber-400" /> خارطة الطريق</h3>
          <div className="grid gap-3">
            {roadmap.phases.map((phase) => (
              <div key={phase.phase} className="rounded-2xl border border-white/10 bg-black/25 p-4 md:flex md:items-center md:justify-between md:gap-4">
                <div>
                  <div className="mb-1 text-xs font-bold text-amber-300">المرحلة {phase.phase}</div>
                  <h4 className="font-black">{phase.title}</h4>
                  <p className="mt-1 text-sm text-zinc-400">{phase.outcome}</p>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5 md:mt-0 md:justify-end">
                  {phase.keys.map((key) => <code key={key} className="rounded-lg bg-white/5 px-2 py-1 text-xs text-zinc-300">{key}</code>)}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-3xl border border-amber-400/20 bg-amber-500/10 p-6" data-testid="ai-readiness-summary-box">
          <h3 className="mb-4 text-xl font-black text-amber-100">الخلاصة المربعة</h3>
          <div className="grid gap-3 text-sm leading-7 text-zinc-200 md:grid-cols-2">
            <div>✅ أقوى الموجود: Anthropic + OpenAI + Gemini + Groq + GitHub/Vercel/Railway.</div>
            <div>⚠️ أهم نقص: Sentry DSN + Cloudflare R2 + OpenRouter + Redis queue.</div>
            <div>🔗 روابط المفاتيح موجودة داخل كل كرت فوق بزر “افتح الرابط”.</div>
            <div>🎯 الخطوة التالية: أرسل القيم بالترتيب، وأنا أربطها وأنشر وأختبر.</div>
          </div>
        </section>
      </main>
    </div>
  );
}
