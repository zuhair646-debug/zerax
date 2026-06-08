import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { toast } from 'sonner';
import { CheckCircle2, XCircle, Loader2, Wallet, Mail, ExternalLink, ShieldCheck } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
function api(p, opts = {}) {
  const t = localStorage.getItem('token');
  return fetch(`${API}${p}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(t ? { Authorization: `Bearer ${t}` } : {}), ...(opts.headers || {}) },
  });
}

export default function PayoutsAdmin({ user }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('pending');
  const [acting, setActing] = useState(null);
  const [txnRef, setTxnRef] = useState({});
  const [rejectReason, setRejectReason] = useState({});

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'owner' || user?.is_owner;

  const load = async () => {
    setLoading(true);
    try {
      const r = await api(`/api/admin/payouts${status ? `?status=${status}` : ''}`);
      if (r.ok) setItems((await r.json()).items || []);
    } finally { setLoading(false); }
  };
  useEffect(() => { if (isAdmin) load(); /* eslint-disable-next-line */ }, [status]);

  const markPaid = async (id) => {
    setActing(id);
    const r = await api(`/api/admin/payouts/${id}/mark-paid`, {
      method: 'POST', body: JSON.stringify({ paid_txn_ref: txnRef[id] || '' }),
    });
    if (r.ok) { toast.success('تم تأكيد التحويل + إشعار المسوّق'); load(); }
    else { const e = await r.json().catch(() => ({})); toast.error(e.detail || 'فشل'); }
    setActing(null);
  };

  const reject = async (id) => {
    const reason = rejectReason[id];
    if (!reason || reason.length < 3) { toast.error('اكتب سبب الرفض'); return; }
    setActing(id);
    const r = await api(`/api/admin/payouts/${id}/reject`, {
      method: 'POST', body: JSON.stringify({ reason }),
    });
    if (r.ok) { toast.success('تم الرفض + إعادة الرصيد'); load(); }
    setActing(null);
  };

  if (!isAdmin) return (
    <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
      <ShieldCheck className="w-12 h-12 text-red-400" />
      <div className="ms-3 font-bold">للأدمن فقط</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <Navbar user={user} />
      <div className="pt-24 pb-12 px-4 max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-amber-500 flex items-center justify-center">
            <Wallet className="w-5 h-5 text-zinc-950" />
          </div>
          <div>
            <h1 className="text-2xl font-black">طلبات السحب</h1>
            <p className="text-zinc-500 text-sm">أكّد التحويلات بعد إرسال الأموال يدوياً عبر PayPal</p>
          </div>
        </div>

        <div className="flex gap-2 mb-4">
          {[
            ['pending', 'معلّقة', 'amber'],
            ['paid', 'مدفوعة', 'emerald'],
            ['rejected', 'مرفوضة', 'red'],
            ['', 'الكل', 'zinc'],
          ].map(([k, l]) => (
            <button
              key={k}
              onClick={() => setStatus(k)}
              className={`px-3 py-1.5 rounded-lg text-xs ${status === k ? `bg-${l}-500/20 border border-${l}-400/40 text-${l}-200` : 'border border-zinc-800 text-zinc-400'}`}
            >
              {l}
            </button>
          ))}
        </div>

        {loading ? <Loader2 className="w-6 h-6 animate-spin mx-auto" /> :
         items.length === 0 ? <div className="text-zinc-500 text-center py-12">لا يوجد طلبات</div> :
         <div className="space-y-3" data-testid="payouts-list">
           {items.map((p) => (
             <div key={p.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
               <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                 <div>
                   <div className="font-bold">{p.user?.name || p.user?.email}</div>
                   <div className="text-[11px] text-zinc-500" data-no-translate="true">
                     {p.user?.email} · {p.user?.country || '—'} · كود: {p.code}
                   </div>
                   <div className="text-[11px] text-zinc-500 mt-1" data-no-translate="true">
                     طُلب: {(p.requested_at || '').slice(0, 16)}
                   </div>
                 </div>
                 <div className="text-end">
                   <div className="text-2xl font-black text-amber-300" data-no-translate="true">${p.amount_requested_usd}</div>
                   <div className="text-[10px] text-zinc-500">
                     رسوم <span data-no-translate="true">${p.fee_usd}</span> · يستلم <span className="text-emerald-300" data-no-translate="true">${p.amount_net_usd}</span>
                   </div>
                 </div>
               </div>

               <div className="bg-black/40 rounded-lg p-3 mb-3 flex items-center gap-2">
                 <Mail className="w-4 h-4 text-emerald-400" />
                 <span className="text-sm font-mono text-emerald-300 flex-1" data-no-translate="true">{p.paypal_email}</span>
                 <button
                   onClick={() => { navigator.clipboard?.writeText(p.paypal_email); toast.success('نُسخ'); }}
                   className="text-zinc-400 hover:text-white text-xs"
                 >
                   نسخ
                 </button>
                 <a
                   href={`https://www.paypal.com/myaccount/transfer/homepage/pay?recipient=${encodeURIComponent(p.paypal_email)}&amount=${p.amount_net_usd}`}
                   target="_blank" rel="noreferrer"
                   className="text-xs text-amber-400 hover:underline flex items-center gap-1"
                 >
                   <ExternalLink className="w-3 h-3" /> فتح PayPal
                 </a>
               </div>

               {p.status === 'pending' ? (
                 <>
                   <div className="grid md:grid-cols-2 gap-2 mb-2">
                     <input
                       value={txnRef[p.id] || ''}
                       onChange={(e) => setTxnRef({ ...txnRef, [p.id]: e.target.value })}
                       placeholder="مرجع التحويل (اختياري)"
                       className="bg-black/40 border border-zinc-800 rounded-lg px-3 py-2 text-xs"
                     />
                     <input
                       value={rejectReason[p.id] || ''}
                       onChange={(e) => setRejectReason({ ...rejectReason, [p.id]: e.target.value })}
                       placeholder="سبب الرفض (للرفض فقط)"
                       className="bg-black/40 border border-zinc-800 rounded-lg px-3 py-2 text-xs"
                     />
                   </div>
                   <div className="flex gap-2">
                     <button
                       onClick={() => markPaid(p.id)}
                       disabled={acting === p.id}
                       data-testid={`mark-paid-${p.id}`}
                       className="flex-1 bg-emerald-500 text-zinc-950 rounded-lg py-2 text-sm font-bold flex items-center justify-center gap-1 disabled:opacity-50"
                     >
                       {acting === p.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                       تأكيد التحويل
                     </button>
                     <button
                       onClick={() => reject(p.id)}
                       disabled={acting === p.id}
                       data-testid={`reject-${p.id}`}
                       className="flex-1 bg-red-500/20 border border-red-400/40 text-red-300 rounded-lg py-2 text-sm font-bold flex items-center justify-center gap-1 disabled:opacity-50"
                     >
                       <XCircle className="w-4 h-4" />
                       رفض وإعادة الرصيد
                     </button>
                   </div>
                 </>
               ) : (
                 <div className={`text-xs ${p.status === 'paid' ? 'text-emerald-300' : 'text-red-300'}`}>
                   {p.status === 'paid' ? '✓ تم التحويل' : '⛔ مرفوض'}
                   {p.paid_txn_ref && <span className="ms-2 text-zinc-500" data-no-translate="true">· {p.paid_txn_ref}</span>}
                   {p.rejection_reason && <span className="ms-2 text-zinc-500">· {p.rejection_reason}</span>}
                 </div>
               )}
             </div>
           ))}
         </div>
        }
      </div>
    </div>
  );
}
