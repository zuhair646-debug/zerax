import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import {
  ArrowLeft, Loader2, ShieldCheck, ExternalLink, Copy, AlertTriangle,
  CheckCircle2, XCircle, Zap, Sparkles, CreditCard, BarChart3, Mic,
  Brain, Code2, RefreshCw,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORY_ICON = {
  ai: Brain,
  payments: CreditCard,
  data: BarChart3,
  fallback: Sparkles,
};

const CATEGORY_LABEL = {
  ai: 'الذكاء الاصطناعي والصوت',
  payments: 'المدفوعات',
  data: 'بيانات خارجية',
  fallback: 'احتياطي (Emergent)',
};

export default function AdminIndependence() {
  const nav = useNavigate();
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

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
                {score}% مستقل
              </h2>
              <p className="text-sm text-white/70">
                {data.independent_count} من {data.total_count} خدمات تستخدم مفاتيحك الخاصة مباشرة
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
        {Object.keys(grouped).map((cat) => {
          const Icon = CATEGORY_ICON[cat] || Brain;
          return (
            <div key={cat} className="mb-8">
              <h3 className="text-lg font-black mb-3 flex items-center gap-2">
                <Icon className="w-5 h-5 text-amber-400" />
                {CATEGORY_LABEL[cat] || cat}
              </h3>
              <div className="grid md:grid-cols-2 gap-3">
                {grouped[cat].map((it) => <IntegrationCard key={it.id} it={it} />)}
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
    </div>
  );
}

function IntegrationCard({ it }) {
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
          <h4 className="font-black text-sm mb-0.5">{it.name_ar}</h4>
          <p className="text-[11px] text-white/50">{it.name}</p>
        </div>
        <span className={`text-[10px] px-2 py-1 rounded-full border ${badgeMap[it.status_color]} whitespace-nowrap`}>
          {it.status_label}
        </span>
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
