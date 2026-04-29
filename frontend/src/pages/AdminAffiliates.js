import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * /admin/affiliates — Owner-only management of marketers.
 */
export default function AdminAffiliates() {
  const [list, setList] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const token = useMemo(() => localStorage.getItem('token') || '', []);
  const H = useMemo(() => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }), [token]);

  const load = async () => {
    setLoading(true);
    try {
      const [a, s] = await Promise.all([
        fetch(`${API}/api/affiliate/admin/list`, { headers: H }).then(r => r.json()),
        fetch(`${API}/api/affiliate/admin/stats`, { headers: H }).then(r => r.json()),
      ]);
      setList(a.affiliates || []);
      setStats(s);
    } catch (_) { /* */ }
    setLoading(false);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const approve = async (uid, pct) => {
    await fetch(`${API}/api/affiliate/admin/${uid}/approve`, {
      method: 'POST', headers: H, body: JSON.stringify({ approved: true, commission_pct: pct }),
    });
    toast.success('✅ تم القبول');
    load();
  };
  const reject = async (uid) => {
    if (!window.confirm('رفض هذا الطلب؟')) return;
    await fetch(`${API}/api/affiliate/admin/${uid}/approve`, {
      method: 'POST', headers: H, body: JSON.stringify({ approved: false }),
    });
    load();
  };
  const payout = async (uid, max) => {
    const amt = parseFloat(prompt(`قيمة الصرف (الحد الأقصى ${max} $):`) || '0');
    if (!amt || amt <= 0) return;
    const note = prompt('ملاحظة (اختياري):') || '';
    const r = await fetch(`${API}/api/affiliate/admin/${uid}/payout`, {
      method: 'POST', headers: H, body: JSON.stringify({ amount: amt, method: 'manual', note }),
    });
    if (!r.ok) toast.error('فشل: ' + (await r.json()).detail);
    else { toast.success('✅ سُجِّل الصرف'); load(); }
  };

  if (loading) return <div className="min-h-screen bg-[#0a0b14] text-white flex items-center justify-center">⏳</div>;
  const s = stats?.stats || {};

  return (
    <div className="min-h-screen bg-[#0a0b14] text-white" dir="rtl" data-testid="admin-affiliates">
      <div className="max-w-6xl mx-auto p-4 md:p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl md:text-4xl font-black">🤝 إدارة المسوّقين</h1>
          <a href="/admin" className="text-xs text-white/50 hover:text-white">← لوحة الأدمن</a>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          <Stat label="📋 إجمالي" value={s.total || 0} />
          <Stat label="✅ نشط" value={s.active || 0} accent="emerald" />
          <Stat label="⏳ معلّق" value={s.pending || 0} accent="amber" />
          <Stat label="💰 رصيد متاح" value={`${(s.pending_balance || 0).toFixed(2)} $`} accent="emerald" />
          <Stat label="💸 صُرف" value={`${(s.paid_total || 0).toFixed(2)} $`} accent="blue" />
        </div>

        <div className="space-y-3">
          {list.length === 0 && <div className="text-center text-white/40 py-10 text-sm">لا مسوّقون بعد</div>}
          {list.map((a) => (
            <div key={a.user_id} className="bg-white/[.03] border border-white/10 rounded-xl p-4" data-testid={`aff-row-${a.user_id}`}>
              <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
                <div className="flex-1 min-w-[200px]">
                  <div className="font-black">{a.user?.name || '—'} <span className="text-white/50 text-xs">{a.user?.email}</span></div>
                  <div className="text-[11px] text-white/50">طريقة: {a.method || '—'}</div>
                  {a.notes && <div className="text-[11px] text-white/55 mt-1 max-w-md">{a.notes}</div>}
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {a.status === 'active' && (
                    <>
                      <span className="text-[10px] bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 px-2 py-0.5 rounded-full">نشط</span>
                      <code className="text-[11px] bg-yellow-500/15 text-yellow-300 px-2 py-0.5 rounded">{a.code}</code>
                      <span className="text-[11px] text-white/60">{a.commission_pct}%</span>
                    </>
                  )}
                  {a.status === 'pending' && <span className="text-[10px] bg-amber-500/20 border border-amber-500/40 text-amber-300 px-2 py-0.5 rounded-full">قيد المراجعة</span>}
                  {a.status === 'rejected' && <span className="text-[10px] bg-red-500/20 border border-red-500/40 text-red-300 px-2 py-0.5 rounded-full">مرفوض</span>}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3 text-xs text-white/65 mb-3">
                <span>👥 {a.lifetime_referrals_signups || 0} اشتراكات</span>
                <span>💳 {a.lifetime_referrals_paid || 0} دفعوا</span>
                <span>🎁 ${(a.lifetime_earnings || 0).toFixed(2)} مكتسبة</span>
                <span className="text-emerald-300">💰 ${(a.pending_balance || 0).toFixed(2)} متاح</span>
                <span className="text-blue-300">💸 ${(a.paid_total || 0).toFixed(2)} صُرف</span>
              </div>

              <div className="flex gap-2 flex-wrap">
                {a.status === 'pending' && (
                  <>
                    <button onClick={() => {
                      const pct = parseFloat(prompt('نسبة العمولة %:', '20') || '20');
                      approve(a.user_id, pct);
                    }} className="px-3 py-1.5 bg-emerald-500 text-black rounded-lg text-xs font-black" data-testid={`approve-${a.user_id}`}>✅ موافقة</button>
                    <button onClick={() => reject(a.user_id)} className="px-3 py-1.5 bg-red-500/20 text-red-300 rounded-lg text-xs font-bold">❌ رفض</button>
                  </>
                )}
                {a.status === 'active' && a.pending_balance > 0 && (
                  <button onClick={() => payout(a.user_id, a.pending_balance)} className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-xs font-black" data-testid={`payout-${a.user_id}`}>
                    💸 صرف ({a.pending_balance.toFixed(2)} $)
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }) {
  const colors = {
    emerald: 'from-emerald-500/15 to-emerald-500/5 border-emerald-500/30',
    amber: 'from-amber-500/15 to-amber-500/5 border-amber-500/30',
    blue: 'from-blue-500/15 to-blue-500/5 border-blue-500/30',
    default: 'from-white/10 to-white/5 border-white/15',
  };
  return (
    <div className={`bg-gradient-to-br ${colors[accent || 'default']} border rounded-xl p-3`}>
      <div className="text-[10px] text-white/65">{label}</div>
      <div className="text-xl font-black mt-1">{value}</div>
    </div>
  );
}
