import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import {
  ArrowLeft, Loader2, ShieldCheck, ExternalLink, Copy, AlertTriangle,
  CheckCircle2, XCircle, Zap, Sparkles, CreditCard, BarChart3, Mic,
  Brain, Code2, RefreshCw, Image as ImageIcon, Database, Mail, Rocket,
  TrendingUp, Lock, HelpCircle, X, Play,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORY_ICON = {
  ai: Brain,
  media: ImageIcon,
  payments: CreditCard,
  storage: Database,
  messaging: Mail,
  devops: Rocket,
  analytics: TrendingUp,
  auth: Lock,
  data: BarChart3,
  fallback: Sparkles,
};

const CATEGORY_LABEL = {
  ai: '🤖 الذكاء الاصطناعي',
  media: '🎨 توليد الصور والفيديو والصوت',
  payments: '💳 المدفوعات',
  storage: '🗄️ التخزين وقواعد البيانات',
  messaging: '📨 الإيميل والـSMS',
  devops: '🚀 النشر والمراقبة',
  analytics: '📊 التحليلات',
  auth: '🔐 المصادقة',
  data: '📈 بيانات خارجية',
  fallback: '⚡ احتياطي (Emergent)',
};

const CATEGORY_ORDER = ['ai', 'media', 'payments', 'storage', 'messaging', 'devops', 'analytics', 'auth', 'data', 'fallback'];

export default function AdminIndependence() {
  const nav = useNavigate();
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [helpFor, setHelpFor] = useState(null);  // currently open tutorial integration_id
  const [helpData, setHelpData] = useState(null); // loaded tutorial payload
  const [helpLoading, setHelpLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/admin/independence-status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.status === 403) {
        toast.error('للمالك فقط');
        nav('/dashboard'); return;
      }
      if (!r.ok) throw new Error('failed');
      setData(await r.json());
    } catch (e) {
      toast.error('فشل التحميل');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token) { nav('/login'); return; }
    load();
    // eslint-disable-next-line
  }, []);

  const openHelp = async (integrationId) => {
    setHelpFor(integrationId);
    setHelpLoading(true);
    setHelpData(null);
    try {
      const r = await fetch(`${API}/api/admin/integration-tutorial/${integrationId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error('failed');
      setHelpData(await r.json());
    } catch (e) {
      toast.error('فشل تحميل الشرح');
      setHelpFor(null);
    } finally {
      setHelpLoading(false);
    }
  };

  const closeHelp = () => { setHelpFor(null); setHelpData(null); };

  if (loading || !data) {
    return (
      <div className="min-h-screen bg-[#050505] text-white flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-amber-400" />
      </div>
    );
  }

  // Group by category
  const grouped = data.integrations.reduce((acc, it) => {
    const cat = it.category || 'other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(it);
    return acc;
  }, {});

  const score = data.total_count > 0
    ? Math.round((data.independent_count / data.total_count) * 100)
    : 0;

  return (
    <div dir="rtl" className="min-h-screen bg-[#050505] text-white">
      <Toaster richColors position="top-center" />

      <header className="h-14 px-4 border-b border-white/10 flex items-center justify-between bg-black/40 backdrop-blur sticky top-0 z-20">
        <div className="flex items-center gap-2">
          <button onClick={() => nav('/admin')} className="p-1.5 hover:bg-white/5 rounded">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h1 className="font-black text-sm flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-amber-400" /> الاستقلالية والمفاتيح
          </h1>
        </div>
        <button
          onClick={load}
          data-testid="refresh-status"
          className="px-3 py-1.5 rounded-md bg-white/5 hover:bg-white/10 text-xs flex items-center gap-1"
        >
          <RefreshCw className="w-3.5 h-3.5" /> تحديث
        </button>
      </header>

      <div className="container mx-auto max-w-5xl px-4 md:px-8 py-8 md:py-12">

        {/* Score banner */}
        <div className={`rounded-2xl p-6 md:p-8 mb-8 border ${
          score >= 100
            ? 'bg-emerald-500/10 border-emerald-400/30'
            : score >= 50
              ? 'bg-amber-500/10 border-amber-400/30'
              : 'bg-rose-500/10 border-rose-400/30'
        }`}>
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h2 className="text-2xl md:text-3xl font-black mb-1">
                {score}% مستقل (أساسي)
              </h2>
              <p className="text-sm text-white/70">
                {data.independent_count} من {data.total_count} مفتاح أساسي ✦ {data.optional_set || 0} مفتاح اختياري إضافي مفعّل
              </p>
            </div>
            <div className="flex items-center gap-2">
              {score >= 100 ? (
                <span className="px-3 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 text-xs font-bold flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> استقلال كامل
                </span>
              ) : (
                <span className="px-3 py-1.5 rounded-lg bg-amber-500/20 border border-amber-400/40 text-amber-300 text-xs font-bold flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4" /> {data.total_count - data.independent_count} خدمة لسه على Emergent
                </span>
              )}
            </div>
          </div>
          <div className="mt-4 h-2 bg-black/40 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-700 ${
                score >= 100 ? 'bg-emerald-400' : score >= 50 ? 'bg-amber-400' : 'bg-rose-400'
              }`}
              style={{ width: `${score}%` }}
            />
          </div>
        </div>

        {/* Quick guide */}
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5 mb-8 text-sm text-white/70 leading-relaxed">
          <div className="font-bold text-white mb-2 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-amber-400" /> كيف تستخدم هذه الصفحة؟
          </div>
          <ol className="space-y-1.5 list-decimal pr-5 text-xs">
            <li>كل بطاقة تحت تمثّل خدمة. لو الـbadge أخضر → شغّالة على مفتاحك ✅</li>
            <li>لو أصفر/أحمر → اضغط "احصل على المفتاح" → يفتح صفحة الخدمة الرسمية مباشرة</li>
            <li>انسخ المفتاح، روح Railway → Variables → ضع اسم المتغير (مكتوب في البطاقة) + قيمة المفتاح</li>
            <li>Railway يعيد deploy تلقائياً، رجع هنا واضغط "تحديث" عشان تتأكد</li>
          </ol>
        </div>

        {/* Integration groups */}
        {CATEGORY_ORDER.filter((cat) => grouped[cat]?.length).map((cat) => {
          const Icon = CATEGORY_ICON[cat] || Brain;
          return (
            <div key={cat} className="mb-8">
              <h3 className="text-lg font-black mb-3 flex items-center gap-2">
                <Icon className="w-5 h-5 text-amber-400" />
                {CATEGORY_LABEL[cat] || cat}
                <span className="text-xs font-normal text-white/40">({grouped[cat].length})</span>
              </h3>
              <div className="grid md:grid-cols-2 gap-3">
                {grouped[cat].map((it) => <IntegrationCard key={it.id} it={it} onHelp={openHelp} />)}
              </div>
            </div>
          );
        })}

        {/* Owner key copy section */}
        <div className="rounded-xl border border-amber-400/20 bg-amber-500/5 p-5 mt-8">
          <h3 className="font-black mb-2 flex items-center gap-1.5">
            <Code2 className="w-4 h-4 text-amber-400" /> ملخص متغيرات Railway
          </h3>
          <p className="text-xs text-white/60 mb-3">
            انسخ السطور الناقصة وحطها في Railway → Variables (سطر-سطر):
          </p>
          <RailwayCopyBlock items={data.integrations.filter(i => !i.is_independent && i.category !== 'fallback')} />
        </div>
      </div>

      {/* Help / tutorial modal */}
      {helpFor && (
        <HelpModal
          loading={helpLoading}
          data={helpData}
          onClose={closeHelp}
        />
      )}
    </div>
  );
}

function IntegrationCard({ it, onHelp }) {
  const copyVar = () => {
    navigator.clipboard.writeText(`${it.env_var}=`);
    toast.success(`نسخت اسم المتغير: ${it.env_var}`);
  };
  const colorMap = {
    green: 'border-emerald-400/30 bg-emerald-500/[0.04]',
    amber: 'border-amber-400/30 bg-amber-500/[0.04]',
    red: 'border-rose-400/30 bg-rose-500/[0.04]',
  };
  const badgeMap = {
    green: 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30',
    amber: 'bg-amber-500/20 text-amber-300 border-amber-400/30',
    red: 'bg-rose-500/20 text-rose-300 border-rose-400/30',
  };
  return (
    <div
      data-testid={`integration-${it.id}`}
      className={`rounded-xl border p-4 ${colorMap[it.status_color]} transition`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0 flex-1">
          <h4 className="font-black text-sm mb-0.5 flex items-center gap-1.5 flex-wrap">
            {it.name_ar}
            {it.priority === 'high' && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-md bg-rose-500/20 border border-rose-400/40 text-rose-300 font-bold uppercase">أساسي</span>
            )}
            {it.priority === 'medium' && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-md bg-amber-500/20 border border-amber-400/40 text-amber-300 font-bold uppercase">مفيد</span>
            )}
            {it.priority === 'low' && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-md bg-white/10 border border-white/20 text-white/60 font-bold uppercase">اختياري</span>
            )}
          </h4>
          <p className="text-[11px] text-white/50">{it.name}</p>
        </div>
        <span className={`text-[10px] px-2 py-1 rounded-full border ${badgeMap[it.status_color]} whitespace-nowrap`}>
          {it.status_label}
        </span>
        {it.category !== 'fallback' && onHelp && (
          <button
            onClick={() => onHelp(it.id)}
            data-testid={`help-btn-${it.id}`}
            title="كيف أحصل على هذا المفتاح؟"
            className="shrink-0 w-7 h-7 rounded-full bg-blue-500/15 hover:bg-blue-500/30 border border-blue-400/30 text-blue-300 flex items-center justify-center transition"
          >
            <HelpCircle className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
      <p className="text-xs text-white/70 leading-relaxed mb-3">
        <span className="text-white/50">يشغّل:</span> {it.powers_ar}
      </p>

      {/* Status detail */}
      {it.is_independent ? (
        <div className="text-[11px] text-emerald-300 mb-3 flex items-center gap-1.5">
          <CheckCircle2 className="w-3 h-3" />
          <span className="font-mono">{it.preview}</span>
        </div>
      ) : it.using_fallback ? (
        <div className="text-[11px] text-amber-300 mb-3 flex items-center gap-1.5">
          <Zap className="w-3 h-3" /> {it.fallback_label_ar}
        </div>
      ) : (
        <div className="text-[11px] text-rose-300 mb-3 flex items-center gap-1.5">
          <XCircle className="w-3 h-3" /> {it.fallback_label_ar}
        </div>
      )}

      {/* Pricing note */}
      <div className="text-[11px] text-white/50 mb-3 leading-relaxed bg-black/30 rounded-md px-2 py-1.5">
        💰 {it.pricing_note_ar}
      </div>

      {/* Action buttons */}
      {it.category !== 'fallback' && (
        <div className="flex flex-wrap gap-1.5">
          <a
            href={it.console_url}
            target="_blank"
            rel="noopener noreferrer"
            data-testid={`get-key-${it.id}`}
            className="flex-1 min-w-[120px] text-center px-3 py-1.5 rounded-md bg-amber-500 hover:bg-amber-400 text-black text-[11px] font-bold flex items-center justify-center gap-1"
          >
            <ExternalLink className="w-3 h-3" /> احصل على المفتاح
          </a>
          <button
            onClick={copyVar}
            data-testid={`copy-var-${it.id}`}
            title={`نسخ ${it.env_var}=`}
            className="px-3 py-1.5 rounded-md bg-white/5 hover:bg-white/10 text-[11px] flex items-center gap-1"
          >
            <Copy className="w-3 h-3" /> {it.env_var}
          </button>
        </div>
      )}
    </div>
  );
}

function RailwayCopyBlock({ items }) {
  if (items.length === 0) {
    return (
      <div className="text-xs text-emerald-300 flex items-center gap-1.5">
        <CheckCircle2 className="w-4 h-4" /> ممتاز — كل المتغيرات مضبوطة!
      </div>
    );
  }
  const text = items.map(i => `${i.env_var}=`).join('\n');
  const copy = () => {
    navigator.clipboard.writeText(text);
    toast.success(`نسخت ${items.length} متغير`);
  };
  return (
    <>
      <pre
        data-testid="railway-vars-block"
        className="bg-black/60 border border-white/10 rounded-lg p-3 text-[11px] font-mono text-amber-200 overflow-x-auto"
      >
        {text}
      </pre>
      <button
        onClick={copy}
        data-testid="copy-all-vars"
        className="mt-2 px-3 py-1.5 rounded-md bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold flex items-center gap-1"
      >
        <Copy className="w-3.5 h-3.5" /> نسخ كل المتغيرات
      </button>
    </>
  );
}


function HelpModal({ loading, data, onClose }) {
  if (!loading && !data) return null;

  const handleBackdrop = (e) => {
    if (e.target === e.currentTarget) onClose();
  };

  const t = data?.tutorial;
  const rt = data?.railway_tutorial;
  const ig = data?.integration;
  const copyVar = () => {
    if (!ig?.env_var) return;
    navigator.clipboard.writeText(ig.env_var);
    toast.success(`نسخت: ${ig.env_var}`);
  };

  return (
    <div
      onClick={handleBackdrop}
      data-testid="help-modal-backdrop"
      className="fixed inset-0 z-[80] bg-black/85 backdrop-blur-sm flex items-start md:items-center justify-center p-4 overflow-y-auto"
    >
      <div
        data-testid="help-modal"
        className="bg-[#0a0a0a] border border-white/10 rounded-2xl max-w-2xl w-full my-8 overflow-hidden shadow-2xl"
        dir="rtl"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-white/10 bg-gradient-to-l from-blue-500/10 to-transparent">
          <h3 className="font-black text-base flex items-center gap-2 text-white">
            <HelpCircle className="w-5 h-5 text-blue-400" />
            {loading ? 'تحميل...' : (t?.title_ar || 'شرح الإعداد')}
          </h3>
          <button
            onClick={onClose}
            data-testid="help-modal-close"
            className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center"
          >
            <X className="w-4 h-4 text-white/70" />
          </button>
        </div>

        <div className="p-5 max-h-[75vh] overflow-y-auto space-y-5">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
            </div>
          ) : (
            <>
              {/* Intro */}
              {t?.intro_ar && (
                <p className="text-sm text-white/75 leading-relaxed bg-blue-500/5 border border-blue-400/20 rounded-lg p-3">
                  {t.intro_ar}
                </p>
              )}

              {/* Pricing */}
              {ig?.pricing_note_ar && (
                <div className="text-xs text-white/60 bg-black/40 rounded-md px-3 py-2 flex items-center gap-2">
                  💰 <span>{ig.pricing_note_ar}</span>
                </div>
              )}

              {/* YouTube tutorial button */}
              {t?.youtube_search && (
                <a
                  href={t.youtube_search}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="help-watch-video"
                  className="flex items-center gap-3 p-4 rounded-xl bg-gradient-to-l from-red-600/20 to-rose-600/10 border border-red-500/30 hover:border-red-500/60 transition group"
                >
                  <div className="w-12 h-12 rounded-full bg-red-600 group-hover:bg-red-500 flex items-center justify-center shrink-0">
                    <Play className="w-5 h-5 text-white fill-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-sm text-white">شاهد فيديوهات شرح على YouTube</div>
                    <div className="text-xs text-white/60">يفتح لك نتائج بحث على آخر الفيديوهات</div>
                  </div>
                  <ExternalLink className="w-4 h-4 text-white/60" />
                </a>
              )}

              {/* Step-by-step */}
              {t?.steps_ar && t.steps_ar.length > 0 && (
                <div>
                  <h4 className="font-black text-sm text-white mb-2 flex items-center gap-1.5">
                    <span className="w-6 h-6 rounded-full bg-amber-500 text-black flex items-center justify-center text-xs font-bold">1</span>
                    خطوات الحصول على المفتاح
                  </h4>
                  <ol className="space-y-2 pr-2">
                    {t.steps_ar.map((step, i) => (
                      <li key={i} className="flex gap-2.5 text-sm text-white/80 leading-relaxed">
                        <span className="shrink-0 w-5 h-5 rounded-full bg-white/10 text-white/70 flex items-center justify-center text-[10px] font-bold mt-0.5">
                          {i + 1}
                        </span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Get key button */}
              {ig?.console_url && (
                <a
                  href={ig.console_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="help-open-console"
                  className="block text-center px-4 py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-bold text-sm transition"
                >
                  <ExternalLink className="w-4 h-4 inline ml-1.5 -mt-0.5" />
                  افتح صفحة الخدمة الرسمية
                </a>
              )}

              {/* Variable name reminder */}
              {ig?.env_var && (
                <div className="bg-emerald-500/5 border border-emerald-400/30 rounded-lg p-3">
                  <div className="text-xs text-emerald-300 mb-2 font-bold flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    اسم المتغير في Railway
                  </div>
                  <button
                    onClick={copyVar}
                    className="font-mono text-sm bg-black/40 px-3 py-2 rounded-md w-full text-right text-amber-300 hover:bg-black/60 flex items-center justify-between gap-2"
                  >
                    <Copy className="w-3.5 h-3.5 text-white/50" />
                    {ig.env_var}
                  </button>
                </div>
              )}

              {/* Railway tutorial */}
              {rt?.steps_ar && rt.steps_ar.length > 0 && (
                <details className="border border-white/10 rounded-xl overflow-hidden bg-white/[0.02]">
                  <summary className="px-4 py-3 cursor-pointer text-sm font-bold flex items-center gap-2 hover:bg-white/5">
                    <span className="w-6 h-6 rounded-full bg-purple-500 text-white flex items-center justify-center text-xs font-bold">2</span>
                    {rt.title_ar}
                    <span className="text-[10px] text-white/40 mr-auto">اضغط لفتح</span>
                  </summary>
                  <div className="p-4 pt-2 border-t border-white/10">
                    <ol className="space-y-1.5 text-xs text-white/75">
                      {rt.steps_ar.map((step, i) => (
                        <li key={i} className="flex gap-2">
                          <span className="text-white/40">{i + 1}.</span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                    {rt.youtube_search && (
                      <a
                        href={rt.youtube_search}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-3 inline-flex items-center gap-1.5 text-xs text-red-300 hover:text-red-200"
                      >
                        <Play className="w-3 h-3" /> فيديو شرح Railway
                      </a>
                    )}
                  </div>
                </details>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
