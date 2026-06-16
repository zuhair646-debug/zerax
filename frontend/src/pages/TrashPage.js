/**
 * Trash — recover deleted projects.
 *
 * UX:
 *   - List of soft-deleted projects (newest first)
 *   - Each row shows: name · mode · message count · time since deletion ·
 *     restore eligibility (free / $5 fee / expired) · Restore + Purge buttons
 *   - Top banner explains the 24h-free / 30-day-paid / hard-purge policy
 */
/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect, useCallback } from 'react';
import { Trash2, RotateCcw, AlertTriangle, Clock, Crown, ArrowRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const MODE_LABELS = {
  website: 'موقع', image_studio: 'صور', video_studio: 'فيديو',
  anime_studio: 'أنمي', longform_video: 'فيديو طويل',
  app: 'تطبيق', game: 'لعبة',
};

const formatAge = (iso) => {
  if (!iso) return '—';
  const d = typeof iso === 'number' ? new Date(iso * 1000) : new Date(iso);
  const sec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (sec < 60) return `${sec} ثانية`;
  if (sec < 3600) return `${Math.floor(sec / 60)} دقيقة`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} ساعة`;
  return `${Math.floor(sec / 86400)} يوم`;
};

const formatRemaining = (sec) => {
  if (!sec || sec <= 0) return 'انتهى';
  if (sec < 3600) return `${Math.floor(sec / 60)} دقيقة`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} ساعة`;
  return `${Math.floor(sec / 86400)} يوم`;
};

export default function TrashPage() {
  const [items, setItems] = useState([]);
  const [policy, setPolicy] = useState({ retention_days: 30, grace_hours: 24, paid_fee_usd: 5 });
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await fetch(`${API}/api/freebuild-chat/trash`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setItems(d.items || []);
      setPolicy({
        retention_days: d.retention_days,
        grace_hours: d.grace_hours,
        paid_fee_usd: d.paid_fee_usd,
      });
    } catch (e) {
      toast.error(`فشل التحميل: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const restore = async (project) => {
    if (project.restore.fee_usd > 0) {
      if (!window.confirm(`استرجاع المشروع "${project.name}" برسم $${project.restore.fee_usd}. متابعة؟`)) return;
    }
    setBusyId(project.id);
    try {
      const token = localStorage.getItem('token');
      const r = await fetch(`${API}/api/freebuild-chat/project/${project.id}/restore`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل الاسترجاع');
      toast.success(d.message);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusyId(null);
    }
  };

  const purge = async (project) => {
    if (!window.confirm(`حذف نهائي للمشروع "${project.name}" — لا يمكن استرجاعه أبداً. هل أنت متأكد؟`)) return;
    setBusyId(project.id);
    try {
      const token = localStorage.getItem('token');
      const r = await fetch(`${API}/api/freebuild-chat/project/${project.id}/purge`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      toast.success(d.message);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black text-white">
        <Loader2 className="w-8 h-8 animate-spin text-rose-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white p-6" dir="rtl" data-testid="trash-page">
      <div className="max-w-4xl mx-auto space-y-5">
        <div className="flex items-center gap-3">
          <Trash2 className="w-7 h-7 text-rose-400" />
          <h1 className="text-2xl font-black">سلة المحذوفات</h1>
          <span className="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-200 text-xs font-bold">
            {items.length}
          </span>
        </div>

        {/* Policy banner */}
        <div className="bg-gradient-to-br from-rose-500/10 to-amber-500/10 border border-rose-500/30 rounded-2xl p-4">
          <p className="text-sm font-bold text-rose-200 mb-2 flex items-center gap-2">
            <Crown className="w-4 h-4" /> سياسة الاسترداد
          </p>
          <ul className="text-xs text-zinc-200 space-y-1 leading-relaxed pr-4 list-disc marker:text-rose-400">
            <li>المشاريع المحذوفة تبقى محفوظة لـ <span className="font-bold text-emerald-300">{policy.retention_days} يوم</span> قبل الحذف النهائي.</li>
            <li>الاسترجاع <span className="font-bold text-emerald-300">مجاني خلال أول {policy.grace_hours} ساعة</span> من الحذف.</li>
            <li>بعد فترة السماح، الاسترجاع برسم رمزي <span className="font-bold text-amber-300">${policy.paid_fee_usd}</span> فقط — يغطي تكلفة استعادة البيانات من النسخ الاحتياطية.</li>
            <li>الفيديوهات والصور والسيناريوهات والشخصيات كلها تُسترجع بالكامل — لا يضيع شي.</li>
          </ul>
        </div>

        {items.length === 0 ? (
          <div className="text-center py-12 text-zinc-500" data-testid="trash-empty">
            <Trash2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">السلة فاضية — ما عندك مشاريع محذوفة.</p>
            <a href="/freebuild" className="inline-flex items-center gap-1 text-emerald-400 text-xs mt-2 hover:underline">
              <ArrowRight className="w-3 h-3" /> ارجع للمشاريع
            </a>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((p) => {
              const isFree = p.restore.fee_usd === 0;
              const isExpired = !p.restore.eligible;
              return (
                <div
                  key={p.id}
                  data-testid={`trash-item-${p.id}`}
                  className={`rounded-xl border p-3 ${
                    isExpired ? 'border-zinc-700 bg-zinc-900/30 opacity-60' :
                    isFree ? 'border-emerald-500/30 bg-emerald-500/5' :
                             'border-amber-500/30 bg-amber-500/5'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-sm font-black truncate">{p.name || '(بدون اسم)'}</h3>
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-black/40 text-zinc-300">
                          {MODE_LABELS[p.mode] || p.mode}
                        </span>
                        <span className="text-[10px] text-zinc-500">{p.message_count} رسالة</span>
                      </div>
                      <p className="text-[11px] text-zinc-400 mt-1 flex items-center gap-2 flex-wrap">
                        <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> حُذف منذ {formatAge(p.deleted_at)}</span>
                        {p.restore.expires_in_sec && (
                          <span className={isFree ? 'text-emerald-300' : 'text-amber-300'}>
                            • {isFree ? 'مجاني لمدة' : 'متبقي للاسترجاع'} {formatRemaining(p.restore.expires_in_sec)}
                          </span>
                        )}
                      </p>
                      <p className={`text-[11px] mt-1 ${
                        isExpired ? 'text-zinc-500' : isFree ? 'text-emerald-300' : 'text-amber-300'
                      }`}>
                        {p.restore.reason}
                      </p>
                    </div>
                    <div className="flex gap-2 flex-shrink-0">
                      {!isExpired && (
                        <button
                          onClick={() => restore(p)}
                          disabled={busyId === p.id}
                          data-testid={`restore-${p.id}`}
                          className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition disabled:opacity-50 ${
                            isFree
                              ? 'bg-emerald-500 hover:bg-emerald-400 text-black'
                              : 'bg-amber-500 hover:bg-amber-400 text-black'
                          }`}
                        >
                          {busyId === p.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                          {isFree ? 'استرجع مجاناً' : `استرجع $${p.restore.fee_usd}`}
                        </button>
                      )}
                      <button
                        onClick={() => purge(p)}
                        disabled={busyId === p.id}
                        data-testid={`purge-${p.id}`}
                        className="px-2 py-1.5 rounded-lg text-xs font-bold bg-zinc-800 hover:bg-red-600 text-zinc-400 hover:text-white transition disabled:opacity-50"
                        title="حذف نهائي"
                      >
                        <AlertTriangle className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
