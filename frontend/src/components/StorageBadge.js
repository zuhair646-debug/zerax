import { useState, useEffect } from 'react';
import { Sparkles, Check, X, Zap, Crown, Star, Layers } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const TIER_ICONS = {
  free: <Sparkles className="w-4 h-4" />,
  starter: <Zap className="w-4 h-4" />,
  studio: <Star className="w-4 h-4" />,
  aaa: <Crown className="w-4 h-4" />,
};

const TIER_COLORS = {
  free: 'bg-zinc-500/20 border-zinc-500/40 text-zinc-200',
  starter: 'bg-cyan-500/20 border-cyan-500/40 text-cyan-200',
  studio: 'bg-violet-500/20 border-violet-500/40 text-violet-200',
  aaa: 'bg-amber-500/20 border-amber-500/40 text-amber-200',
};

export default function StorageBadge({ projectId }) {
  const [info, setInfo] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem('token');

  const refresh = () => {
    if (!projectId || !token) return;
    fetch(`${API}/api/games/project/${projectId}/billing`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(setInfo)
      .catch(() => {});
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30000); // refresh every 30s
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const upgrade = async (tier) => {
    setLoading(true);
    try {
      const form = new FormData();
      form.append('tier', tier);
      const res = await fetch(`${API}/api/games/project/${projectId}/upgrade`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'فشل الترقية');
      toast.success(`✓ تمت الترقية إلى ${info?.all_tiers?.[tier]?.label || tier}`);
      setShowModal(false);
      refresh();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (!info) return null;

  const tierColor = TIER_COLORS[info.tier] || TIER_COLORS.free;
  const pctColor = info.percent_used > 90 ? 'bg-red-400' : info.percent_used > 70 ? 'bg-amber-400' : 'bg-emerald-400';
  const expiringSoon = info.expires_at && info.retention_days > 0 && (() => {
    try {
      const exp = new Date(info.expires_at);
      const days = Math.ceil((exp - new Date()) / 86400000);
      return days <= 3 ? days : null;
    } catch { return null; }
  })();

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className={`group flex items-center gap-2 px-3 py-1.5 border rounded-lg text-xs font-bold transition-all hover:scale-105 ${tierColor}`}
        data-testid="storage-badge"
        title="إدارة الباقة"
      >
        {TIER_ICONS[info.tier]}
        <div className="flex flex-col items-start leading-tight">
          <span>{info.tier_label}</span>
          <div className="flex items-center gap-1">
            <div className="w-12 h-1 rounded-full bg-white/10 overflow-hidden">
              <div className={`h-full ${pctColor}`} style={{ width: `${Math.min(info.percent_used, 100)}%` }} />
            </div>
            <span className="text-[9px] opacity-70">{info.size_mb}/{info.limit_mb >= 1024 ? `${(info.limit_mb/1024).toFixed(0)}GB` : `${info.limit_mb}MB`}</span>
          </div>
        </div>
        {expiringSoon !== null && expiringSoon !== undefined && (
          <span className="ms-1 text-[9px] px-1.5 py-0.5 bg-red-500/30 border border-red-400/40 rounded-full text-red-200 animate-pulse">
            ينتهي خلال {expiringSoon} يوم
          </span>
        )}
      </button>

      {showModal && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
             onClick={() => setShowModal(false)} data-testid="pricing-modal">
          <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl border border-amber-500/30 bg-gradient-to-br from-[#13131c] to-[#0a0a12] p-6 sm:p-7"
               onClick={(e) => e.stopPropagation()} dir="rtl">
            <button onClick={() => setShowModal(false)}
                    className="absolute top-3 left-3 w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center"
                    data-testid="pricing-close">
              <X className="w-4 h-4 text-white/80" />
            </button>
            <h2 className="text-2xl font-black text-white mb-1 pl-10">💎 باقات حفظ المشروع</h2>
            <p className="text-sm text-zinc-400 mb-6">باقتك الحالية: <span className="font-bold text-amber-300">{info.tier_label}</span> · {info.size_mb} MB من {info.limit_mb} MB ({info.percent_used}%)</p>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {Object.entries(info.all_tiers || {}).map(([key, t]) => {
                const isCurrent = key === info.tier;
                const isPremium = key !== 'free';
                return (
                  <div key={key}
                       className={`relative rounded-xl border p-4 flex flex-col gap-2 ${isCurrent ? 'border-amber-400 bg-amber-500/10' : 'border-white/10 bg-black/30'}`}
                       data-testid={`tier-${key}`}>
                    {isCurrent && (
                      <span className="absolute -top-2 right-2 text-[10px] px-2 py-0.5 bg-amber-400 text-black rounded-full font-black">الحالية</span>
                    )}
                    <div className="flex items-center gap-2">
                      {TIER_ICONS[key]}
                      <h3 className="text-base font-black text-white">{t.label}</h3>
                    </div>
                    <div className="text-2xl font-black text-amber-300">{t.price_label}</div>
                    <ul className="space-y-1 text-xs text-white/80 flex-1">
                      <li className="flex items-start gap-1.5">
                        <Layers className="w-3 h-3 text-emerald-400 mt-0.5" />
                        <span>{t.storage_mb >= 1024 ? `${(t.storage_mb/1024).toFixed(0)} GB` : `${t.storage_mb} MB`} تخزين</span>
                      </li>
                      <li className="flex items-start gap-1.5">
                        <Check className="w-3 h-3 text-emerald-400 mt-0.5" />
                        <span>{t.retention_days < 0 ? 'حفظ دائم' : `${t.retention_days} يوم`}</span>
                      </li>
                      {key === 'starter' && <li className="flex items-start gap-1.5 text-cyan-300"><Check className="w-3 h-3 mt-0.5" />دعم بريد إلكتروني</li>}
                      {key === 'studio' && <li className="flex items-start gap-1.5 text-violet-300"><Check className="w-3 h-3 mt-0.5" />Backup يومي</li>}
                      {key === 'aaa' && <li className="flex items-start gap-1.5 text-amber-300"><Check className="w-3 h-3 mt-0.5" />CDN عالمي + API</li>}
                    </ul>
                    <button
                      onClick={() => upgrade(key)}
                      disabled={isCurrent || loading}
                      className={`w-full py-2 rounded-lg text-xs font-bold mt-2 transition-all ${
                        isCurrent
                          ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
                          : isPremium
                          ? 'bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-black'
                          : 'bg-zinc-700 hover:bg-zinc-600 text-white'
                      }`}
                      data-testid={`upgrade-${key}`}
                    >
                      {isCurrent ? '✓ الحالية' : isPremium ? '⚡ ترقية' : 'تخفيض'}
                    </button>
                  </div>
                );
              })}
            </div>
            <p className="text-[10px] text-zinc-500 mt-4 text-center">
              💡 ملاحظة: المشاريع المجانية يتم حذفها تلقائياً بعد 14 يوم. الترقية تحفظها لمدة أطول وتعطيك مساحة أكبر.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
