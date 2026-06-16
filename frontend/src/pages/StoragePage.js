/* eslint-disable react-hooks/set-state-in-effect */
/**
 * StoragePage — honest, byte-accurate storage usage dashboard.
 *
 * Shows the user exactly where their bytes go (messages, html snapshots,
 * media files, engineering docs), what tier they're on, and provides a
 * direct "request recovery" button if anything got lost.
 */
import { useState, useEffect, useCallback } from 'react';
import { HardDrive, AlertTriangle, FileText, Image as ImageIcon,
         CheckCircle, Loader2, LifeBuoy, Crown } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const formatBytes = (b) => {
  if (!b || b < 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0; let n = b;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
};

const BREAKDOWN_LABELS = {
  messages_text: { label: 'نصوص الرسائل', color: 'bg-cyan-500', icon: FileText },
  html_snapshots: { label: 'نسخ HTML', color: 'bg-violet-500', icon: FileText },
  current_html: { label: 'الموقع الحالي', color: 'bg-emerald-500', icon: FileText },
  engineering_docs: { label: 'مستندات المشروع', color: 'bg-amber-500', icon: FileText },
  media_files_on_disk: { label: 'الصور والفيديوهات', color: 'bg-pink-500', icon: ImageIcon },
};

export default function StoragePage() {
  const [usage, setUsage] = useState(null);
  const [tiers, setTiers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showRecovery, setShowRecovery] = useState(false);
  const [recoveryText, setRecoveryText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [myRequests, setMyRequests] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const [u, t, m] = await Promise.all([
        fetch(`${API}/api/me/storage/usage`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/api/me/storage/tiers`),
        fetch(`${API}/api/me/storage/recovery-requests/mine`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (u.ok) setUsage(await u.json());
      if (t.ok) setTiers((await t.json()).tiers);
      if (m.ok) setMyRequests((await m.json()).items);
    } catch (e) {
      toast.error(`فشل تحميل البيانات: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  const submitRecovery = useCallback(async () => {
    if (recoveryText.trim().length < 10) {
      toast.error('اكتب على الأقل 10 أحرف توضّح ما الذي فُقد');
      return;
    }
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const r = await fetch(`${API}/api/me/storage/recovery-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ description: recoveryText.trim(), contact_method: 'in_app' }),
      });
      const d = await r.json();
      if (r.ok) {
        toast.success(d.message || 'تم استلام طلبك');
        setRecoveryText(''); setShowRecovery(false); load();
      } else {
        toast.error(d.detail || 'فشل الإرسال');
      }
    } finally {
      setSubmitting(false);
    }
  }, [recoveryText, load]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black text-white">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
      </div>
    );
  }
  if (!usage) return null;

  const pct = Math.min(usage.used_pct, 100);
  const isWarn = pct >= 80;
  const isOver = usage.over_quota;
  const tier = usage.tier;

  return (
    <div className="min-h-screen bg-black text-white p-6" dir="rtl" data-testid="storage-page">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <HardDrive className="w-7 h-7 text-cyan-400" />
          <h1 className="text-2xl font-black">مساحة التخزين</h1>
        </div>

        {/* Big usage bar */}
        <div className={`rounded-2xl border p-5 ${
          isOver ? 'bg-red-500/15 border-red-500/40' :
          isWarn ? 'bg-amber-500/15 border-amber-500/40' :
                   'bg-zinc-900/60 border-white/10'
        }`} data-testid="usage-card">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div>
              <p className="text-xs text-zinc-400">باقتك الحالية</p>
              <h2 className="text-xl font-black flex items-center gap-2">
                {tier.id !== 'free' && <Crown className="w-4 h-4 text-amber-400" />}
                {tier.name_ar}
              </h2>
            </div>
            <div className="text-right">
              <p className="text-2xl font-black tabular-nums" data-testid="storage-used-display">
                {formatBytes(usage.used_bytes)}
                <span className="text-zinc-500 text-sm font-normal"> / {formatBytes(usage.quota_bytes)}</span>
              </p>
              <p className={`text-xs font-bold ${isOver ? 'text-red-400' : isWarn ? 'text-amber-400' : 'text-zinc-400'}`}>
                {pct.toFixed(1)}% مستخدم
              </p>
            </div>
          </div>
          <div className="h-3 bg-black/40 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                isOver ? 'bg-red-500' : isWarn ? 'bg-amber-500' : 'bg-gradient-to-r from-cyan-500 to-emerald-500'
              }`}
              style={{ width: `${pct}%` }}
              data-testid="storage-bar"
            />
          </div>
          {isOver && (
            <div className="mt-3 flex items-start gap-2 text-red-200">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <p className="text-sm">
                تجاوزت حد باقتك. لن تستطيع إضافة مشاريع/أصول جديدة حتى تحذف بعض البيانات أو ترفع الباقة.
              </p>
            </div>
          )}
        </div>

        {/* Breakdown */}
        <div className="bg-zinc-900/60 border border-white/10 rounded-2xl p-5" data-testid="breakdown-card">
          <h3 className="text-sm font-black text-zinc-300 mb-3">تفاصيل دقيقة لكل بايت:</h3>
          <div className="space-y-2.5">
            {Object.entries(usage.breakdown).map(([key, bytes]) => {
              const meta = BREAKDOWN_LABELS[key];
              if (!meta) return null;
              const Icon = meta.icon;
              const segPct = usage.used_bytes > 0 ? (bytes / usage.used_bytes) * 100 : 0;
              return (
                <div key={key} data-testid={`breakdown-${key}`}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="flex items-center gap-1.5 text-zinc-300">
                      <Icon className="w-3.5 h-3.5" />
                      {meta.label}
                    </span>
                    <span className="tabular-nums text-zinc-400">
                      {formatBytes(bytes)} <span className="text-zinc-600">({segPct.toFixed(1)}%)</span>
                    </span>
                  </div>
                  <div className="h-1.5 bg-black/40 rounded-full overflow-hidden">
                    <div className={`h-full ${meta.color}`} style={{ width: `${segPct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 pt-4 border-t border-white/10 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div><p className="text-xl font-black tabular-nums">{usage.counts.projects}</p><p className="text-[10px] text-zinc-500 uppercase tracking-wide">مشاريع</p></div>
            <div><p className="text-xl font-black tabular-nums">{usage.counts.messages}</p><p className="text-[10px] text-zinc-500 uppercase tracking-wide">رسائل</p></div>
            <div><p className="text-xl font-black tabular-nums">{usage.counts.docs}</p><p className="text-[10px] text-zinc-500 uppercase tracking-wide">مستندات</p></div>
            <div><p className="text-xl font-black tabular-nums">{usage.counts.files}</p><p className="text-[10px] text-zinc-500 uppercase tracking-wide">ملفات</p></div>
          </div>
        </div>

        {/* Tier ladder */}
        <div className="bg-zinc-900/60 border border-white/10 rounded-2xl p-5" data-testid="tiers-card">
          <h3 className="text-sm font-black text-zinc-300 mb-3">الباقات المتاحة:</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {tiers.map((t) => {
              const isCurrent = t.id === tier.id;
              return (
                <div
                  key={t.id}
                  data-testid={`tier-${t.id}`}
                  className={`rounded-xl border p-3 ${
                    isCurrent ? 'border-emerald-400/60 bg-emerald-500/10' : 'border-white/10 bg-black/30'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="text-sm font-black">{t.name_ar}</h4>
                    {isCurrent && <CheckCircle className="w-4 h-4 text-emerald-400" />}
                  </div>
                  <p className="text-lg font-black">{formatBytes(t.quota_bytes)}</p>
                  <p className="text-xs text-zinc-400">
                    {t.price_usd === 0 ? 'مجاناً' : `$${t.price_usd}/شهر`}
                  </p>
                  <p className="text-[11px] text-zinc-500 mt-1.5 leading-snug">{t.description_ar}</p>
                </div>
              );
            })}
          </div>
          <p className="text-[11px] text-zinc-500 mt-3">
            * التسعير تجريبي ويعرض الآن للعلم فقط — الفوترة الفعلية ستفعّل قريباً.
          </p>
        </div>

        {/* Recovery */}
        <div className="bg-zinc-900/60 border border-white/10 rounded-2xl p-5" data-testid="recovery-card">
          <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
            <div>
              <h3 className="text-sm font-black flex items-center gap-2 text-rose-300">
                <LifeBuoy className="w-4 h-4" /> فقدت بيانات؟ اطلب استرداد
              </h3>
              <p className="text-xs text-zinc-400 mt-1 leading-snug">
                لدينا نسخ احتياطية يومية لآخر 14 يوم. أرسل لنا وصفاً لما فُقد ومتى وسنرجعه لك خلال 24 ساعة.
              </p>
            </div>
            <button
              onClick={() => setShowRecovery((v) => !v)}
              data-testid="open-recovery-form"
              className="px-4 py-2 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-200 text-xs font-bold transition"
            >
              {showRecovery ? 'إخفاء' : 'فتح نموذج الاسترداد'}
            </button>
          </div>
          <div className="mt-2 mb-2">
            <a
              href="/trash"
              data-testid="open-trash-link"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800/60 hover:bg-zinc-700/70 border border-rose-400/30 text-rose-200 text-[11px] font-bold transition"
            >
              🗑️ سلة المحذوفات — استرجع مشاريعك المحذوفة (24 ساعة مجاني، بعدها $5)
            </a>
          </div>
          {showRecovery && (
            <div className="space-y-2 pt-2 border-t border-white/10">
              <textarea
                value={recoveryText}
                onChange={(e) => setRecoveryText(e.target.value)}
                placeholder="مثال: المشروع 'فيلم رعب كوري' كان فيه سيناريو + شخصيات معتمدة، اختفت كل المحادثات بعد ظهور خطأ تقني يوم الأحد..."
                rows={4}
                data-testid="recovery-description"
                className="w-full bg-black/40 border border-white/10 focus:border-rose-400 rounded-lg p-3 text-sm outline-none"
              />
              <button
                onClick={submitRecovery}
                disabled={submitting || recoveryText.trim().length < 10}
                data-testid="submit-recovery"
                className="px-4 py-2 rounded-lg bg-rose-500 hover:bg-rose-400 disabled:opacity-50 text-white font-bold text-xs transition"
              >
                {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin inline ml-1" /> : null}
                إرسال طلب الاسترداد
              </button>
            </div>
          )}
          {myRequests.length > 0 && (
            <div className="mt-4 pt-4 border-t border-white/10">
              <p className="text-[11px] text-zinc-500 mb-2">طلباتك السابقة:</p>
              <div className="space-y-1.5">
                {myRequests.map((r) => (
                  <div key={r.id} className="flex items-center justify-between text-xs bg-black/30 rounded px-2 py-1.5">
                    <span className="truncate flex-1 ml-2">{r.description?.slice(0, 60)}...</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      r.status === 'resolved' ? 'bg-emerald-500/20 text-emerald-200' :
                      r.status === 'rejected' ? 'bg-zinc-500/20 text-zinc-300' :
                      r.status === 'in_progress' ? 'bg-cyan-500/20 text-cyan-200' :
                      'bg-amber-500/20 text-amber-200'
                    }`}>
                      {r.status === 'pending' ? 'قيد المراجعة' :
                       r.status === 'in_progress' ? 'قيد العمل' :
                       r.status === 'resolved' ? 'تم الاسترداد' :
                       'مرفوض'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
