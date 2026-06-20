/**
 * Generic PayPal return page — handles subscription tier purchases
 * (Starter/Pro/Studio/Project Pack). Calls /api/payments/paypal/capture
 * then redirects to the dashboard/landing.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Loader2, AlertCircle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

export default function PaymentsPaypalReturn() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [status, setStatus] = useState('processing');
  const [message, setMessage] = useState('جاري إتمام الدفع...');
  const [credits, setCredits] = useState(0);

  useEffect(() => {
    const orderId = params.get('paymentId') || params.get('order_id');
    const payerId = params.get('PayerID') || params.get('payer_id');
    if (!orderId) {
      setStatus('error'); setMessage('معرف الطلب مفقود.'); return;
    }
    (async () => {
      try {
        const r = await fetch(`${API}/api/payments/paypal/capture`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authH() },
          body: JSON.stringify({ order_id: orderId, payer_id: payerId }),
        });
        const d = await r.json();
        if (!r.ok || !d.ok) throw new Error(d.detail || 'فشل تأكيد الدفع');
        setStatus('done');
        setCredits(d.credits_added || 0);
        setMessage(`تم الدفع بنجاح! أُضيف ${d.credits_added || 0} نقطة لرصيدك.`);
        try { window.dispatchEvent(new Event('zenrex:credits-changed')); } catch (_) { /* noop */ }
        setTimeout(() => navigate('/freebuild/chat', { replace: true }), 2500);
      } catch (e) {
        setStatus('error');
        setMessage(e.message || 'فشل تأكيد الدفع.');
      }
    })();
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4 text-white" dir="rtl">
      <div className="max-w-md w-full rounded-2xl border border-white/10 bg-zinc-900/80 p-8 text-center" data-testid="paypal-return-card">
        <div className="flex justify-center mb-4">
          {status === 'done' ? <CheckCircle2 className="w-16 h-16 text-emerald-400" />
            : status === 'error' ? <AlertCircle className="w-16 h-16 text-red-400" />
            : <Loader2 className="w-16 h-16 text-amber-400 animate-spin" />}
        </div>
        <h1 className="text-2xl font-bold mb-3">
          {status === 'done' ? '🎉 تم الدفع' : status === 'error' ? 'حدث خطأ' : 'لحظة من فضلك...'}
        </h1>
        <p className="text-zinc-400 mb-4">{message}</p>
        {credits > 0 && (
          <p className="text-amber-300 font-black text-3xl mb-6">+{credits.toLocaleString()} نقطة</p>
        )}
        {status === 'error' && (
          <button onClick={() => navigate('/pricing')}
            className="px-5 py-2 rounded-lg bg-amber-400 text-black font-bold hover:bg-amber-300">
            رجوع للأسعار
          </button>
        )}
      </div>
    </div>
  );
}
