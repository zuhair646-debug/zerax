import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import {
  ArrowLeft, Loader2, ExternalLink, RefreshCw, Sparkles,
  Cpu, Image as ImageIcon, Video, Mic, Database, Mail, AlertTriangle,
  MessageSquare, TrendingUp, Layers, KeyRound, CheckCircle2, XCircle,
  CircleDollarSign, ShieldAlert, Zap, Copy,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const ICONS = {
  Cpu, Sparkles, Image: ImageIcon, Video, Mic, Database, Mail,
  AlertTriangle, MessageSquare, TrendingUp, Layers, KeyRound,
};

const LIGHT_STYLES = {
  red:    { dot: 'bg-rose-500',   ring: 'ring-rose-500/40',   pulse: 'animate-pulse', label: 'مفتاح ناقص',   text: 'text-rose-300',   border: 'border-rose-500/40' },
  orange: { dot: 'bg-orange-500', ring: 'ring-orange-500/40', pulse: '',              label: 'ناقص جزئياً',  text: 'text-orange-300', border: 'border-orange-500/40' },
  yellow: { dot: 'bg-amber-500',  ring: 'ring-amber-500/40',  pulse: 'animate-pulse', label: 'رصيد منخفض',   text: 'text-amber-300',  border: 'border-amber-500/40' },
  green:  { dot: 'bg-emerald-500',ring: 'ring-emerald-500/40',pulse: '',              label: 'يعمل',         text: 'text-emerald-300',border: 'border-emerald-500/40' },
  gray:   { dot: 'bg-zinc-600',   ring: 'ring-zinc-700',      pulse: '',              label: 'اختياري',      text: 'text-zinc-400',   border: 'border-zinc-700' },
};

const CATEGORY_LABELS = {
  llm: 'الذكاء النصي',
  media: 'الصور والفيديو',
  voice: 'الصوت',
  infra: 'البنية التحتية',
};

const CATEGORY_ICON = {
  llm: Cpu,
  media: ImageIcon,
  voice: Mic,
  infra: Database,
};

export default function AdminApiKeys() {
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshingId, setRefreshingId] = useState(null);
  const [filter, setFilter] = useState('all');

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API}/api/owner/keys/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(await res.text());
      const d = await res.json();
      setData(d);
    } catch (e) {
      toast.error('فشل تحميل الحالة. تأكد من صلاحيات المالك.');
    } finally {
      setLoading(false);
    }
  };

  const refreshBalance = async (sid) => {
    setRefreshingId(sid);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API}/api/owner/keys/refresh-balance/${sid}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const out = await res.json();
      if (out.balance) {
        toast.success('تم تحديث الرصيد');
      } else {
        toast.info(out.message || 'هذا المزود لا يدعم فحص رصيد مباشر');
      }
      await load();
    } catch {
      toast.error('فشل التحديث');
    } finally {
      setRefreshingId(null);
    }
  };

  useEffect(() => { load(); }, []);

  // Filter services
  const services = (data?.services || []).filter((s) => {
    if (filter === 'all') return true;
    if (filter === 'attention') return ['red', 'orange', 'yellow'].includes(s.status_light);
    return s.category === filter;
  });

  const summary = data?.summary || {};
  const total = summary.total || 0;
  const configured = summary.configured || 0;
  const readiness = total > 0 ? Math.round((configured / total) * 100) : 0;

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 to-black text-zinc-100">
      <Toaster richColors position="top-center" />

      {/* Header */}
      <div className="border-b border-zinc-800/60 sticky top-0 z-30 bg-zinc-950/85 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-5 py-4 flex items-center gap-4">
          <button onClick={() => nav('/admin')} className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <KeyRound className="w-5 h-5 text-amber-400" />
              <h1 className="text-xl font-bold">مفاتيح الذكاء الصناعي</h1>
              <span className="text-xs px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-full">
                {configured}/{total} مفعّل · {readiness}% جاهزية
              </span>
            </div>
            <p className="text-xs text-zinc-500 mt-0.5">
              اضغط على أي خدمة بلون أحمر أو أصفر لتنتقل لصفحة الدفع مباشرة.
            </p>
          </div>
          <button
            onClick={load}
            disabled={loading}
            data-testid="reload-keys-btn"
            className="px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            تحديث
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-5 py-6">

        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <SummaryCard label="جاهز" value={summary.configured || 0} icon={CheckCircle2} color="emerald" />
          <SummaryCard label="ناقص حرج" value={summary.critical_missing || 0} icon={ShieldAlert} color="rose" pulse={summary.critical_missing > 0} />
          <SummaryCard label="ناقص مهم" value={summary.high_missing || 0} icon={AlertTriangle} color="orange" />
          <SummaryCard label="رصيد منخفض" value={summary.low_balance || 0} icon={CircleDollarSign} color="amber" pulse={summary.low_balance > 0} />
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2 mb-5 overflow-x-auto pb-2">
          {[
            { id: 'all', label: 'الكل' },
            { id: 'attention', label: '⚠️ يحتاج انتباه', highlight: true },
            ...Object.keys(CATEGORY_LABELS).map((k) => ({ id: k, label: CATEGORY_LABELS[k] })),
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id)}
              data-testid={`filter-${tab.id}`}
              className={`px-3 py-1.5 rounded-lg text-xs whitespace-nowrap border ${
                filter === tab.id
                  ? 'bg-zinc-100 text-zinc-900 border-zinc-100'
                  : `bg-zinc-900/60 border-zinc-800 text-zinc-300 hover:border-zinc-700 ${
                      tab.highlight ? 'border-amber-500/40 text-amber-300' : ''
                    }`
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Service cards */}
        {loading && !data ? (
          <div className="py-20 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-zinc-500" /></div>
        ) : services.length === 0 ? (
          <div className="text-center py-12 text-zinc-500">لا توجد خدمات بهذا الفلتر</div>
        ) : (
          <div className="space-y-2.5">
            {services.map((s) => (
              <ServiceCard
                key={s.id}
                service={s}
                onRefresh={() => refreshBalance(s.id)}
                refreshing={refreshingId === s.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryCard({ label, value, icon: Icon, color, pulse }) {
  const palette = {
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    rose:    'bg-rose-500/10 text-rose-400 border-rose-500/30',
    orange:  'bg-orange-500/10 text-orange-400 border-orange-500/30',
    amber:   'bg-amber-500/10 text-amber-400 border-amber-500/30',
  }[color];
  return (
    <div className={`rounded-xl border p-3 ${palette} ${pulse ? 'animate-pulse' : ''}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs opacity-80">{label}</p>
          <p className="text-2xl font-bold mt-0.5">{value}</p>
        </div>
        <Icon className="w-5 h-5" />
      </div>
    </div>
  );
}

function ServiceCard({ service: s, onRefresh, refreshing }) {
  const light = LIGHT_STYLES[s.status_light] || LIGHT_STYLES.gray;
  const CategoryIcon = CATEGORY_ICON[s.category] || Cpu;
  const ServiceIcon = ICONS[s.icon] || Sparkles;

  const isAttention = ['red', 'orange', 'yellow'].includes(s.status_light);
  const billingUrl = s.billing_url;
  const keysUrl = s.keys_url;
  const signupUrl = s.signup_url;

  const handleClickPay = () => {
    if (billingUrl) window.open(billingUrl, '_blank');
  };

  return (
    <div
      className={`rounded-xl border p-4 transition group ${
        isAttention
          ? `bg-zinc-900/70 ${light.border} cursor-pointer hover:bg-zinc-900`
          : 'bg-zinc-900/40 border-zinc-800'
      }`}
      data-testid={`service-${s.id}`}
      onClick={isAttention ? handleClickPay : undefined}
    >
      <div className="flex items-start gap-3">
        {/* Status dot */}
        <div className={`relative mt-1.5`}>
          <div className={`w-3 h-3 rounded-full ${light.dot} ${light.pulse}`} />
          {light.pulse && (
            <div className={`absolute inset-0 w-3 h-3 rounded-full ${light.dot} animate-ping opacity-75`} />
          )}
        </div>

        {/* Icon */}
        <div className={`p-2 rounded-lg ${light.border} ${
          s.status_light === 'green' ? 'bg-emerald-500/10' :
          s.status_light === 'yellow' ? 'bg-amber-500/10' :
          s.status_light === 'red' ? 'bg-rose-500/10' :
          s.status_light === 'orange' ? 'bg-orange-500/10' : 'bg-zinc-800/40'
        }`}>
          <ServiceIcon className={`w-4 h-4 ${light.text}`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold">{s.name}</h3>
            <span className={`text-[10px] px-1.5 py-0.5 rounded border ${light.border} ${light.text}`}>
              {light.label}
            </span>
            {s.priority === 'critical' && (
              <span className="text-[10px] px-1.5 py-0.5 bg-rose-500/10 text-rose-400 border border-rose-500/30 rounded">
                ضروري
              </span>
            )}
            <span className="text-[10px] px-1.5 py-0.5 bg-zinc-800 text-zinc-500 rounded">
              <CategoryIcon className="w-2.5 h-2.5 inline -mt-px" /> {CATEGORY_LABELS[s.category]}
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-1">{s.purpose_ar}</p>
          {s.free_tier_note && !s.is_available && (
            <p className="text-[11px] text-emerald-400 mt-1">🎁 {s.free_tier_note}</p>
          )}

          {/* Balance line */}
          {s.balance && (
            <div className="mt-2 flex items-center gap-2 text-xs">
              <CircleDollarSign className="w-3.5 h-3.5 text-amber-400" />
              {s.balance.balance !== undefined && (
                <span className={s.low_balance ? 'text-amber-400 font-semibold' : 'text-emerald-400'}>
                  ${s.balance.balance.toFixed(2)} {s.balance.currency || 'USD'} متبقي
                </span>
              )}
              {s.balance.credits_remaining !== undefined && (
                <span className={s.low_balance ? 'text-amber-400 font-semibold' : 'text-emerald-400'}>
                  {s.balance.credits_remaining.toLocaleString()} حرف متبقي
                  {s.balance.tier && <span className="text-zinc-500"> · {s.balance.tier}</span>}
                </span>
              )}
              {s.balance.used !== undefined && s.balance.balance === undefined && (
                <span className="text-zinc-400">استخدمت ${s.balance.used.toFixed(2)}</span>
              )}
            </div>
          )}

          {/* Env vars status */}
          {s.missing_envs.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {s.missing_envs.map((e) => (
                <span key={e} className="text-[10px] px-1.5 py-0.5 bg-rose-500/10 text-rose-400 border border-rose-500/30 rounded">
                  {e}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-1.5" onClick={(e) => e.stopPropagation()}>
          {!s.is_available ? (
            <>
              <a
                href={signupUrl}
                target="_blank"
                rel="noreferrer"
                data-testid={`signup-${s.id}`}
                className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-black text-xs font-semibold rounded-lg flex items-center gap-1 whitespace-nowrap"
              >
                <ExternalLink className="w-3 h-3" /> سجّل
              </a>
              <a
                href={keysUrl}
                target="_blank"
                rel="noreferrer"
                data-testid={`keys-${s.id}`}
                className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-xs rounded-lg flex items-center gap-1 whitespace-nowrap"
              >
                <KeyRound className="w-3 h-3" /> المفتاح
              </a>
            </>
          ) : (
            <>
              <a
                href={billingUrl}
                target="_blank"
                rel="noreferrer"
                data-testid={`pay-${s.id}`}
                className={`px-3 py-1.5 ${
                  s.low_balance ? 'bg-amber-500 hover:bg-amber-400 text-black' : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-100'
                } text-xs font-semibold rounded-lg flex items-center gap-1 whitespace-nowrap`}
              >
                <CircleDollarSign className="w-3 h-3" /> {s.low_balance ? 'اشحن الآن' : 'الفواتير'}
              </a>
              {s.balance_check && (
                <button
                  onClick={onRefresh}
                  disabled={refreshing}
                  data-testid={`refresh-${s.id}`}
                  className="px-3 py-1.5 bg-zinc-800/60 hover:bg-zinc-700 text-zinc-400 text-xs rounded-lg flex items-center gap-1 disabled:opacity-50"
                >
                  {refreshing ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                  فحص الرصيد
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
