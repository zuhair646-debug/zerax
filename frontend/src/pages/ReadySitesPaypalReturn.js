/**
 * PayPal Return Page — handles the redirect from PayPal after user approval.
 * Captures the payment, gets the project_id, then bounces to /freebuild/chat.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Loader2, AlertCircle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

export default function ReadySitesPaypalReturn() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [status, setStatus] = useState('processing'); // processing | done | error
  const [message, setMessage] = useState('جاري إتمام الدفع...');

  useEffect(() => {
    const orderId = params.get('paymentId') || params.get('order_id');
    const payerId = params.get('PayerID') || params.get('payer_id');
    if (!orderId) {
      setStatus('error');
      setMessage('معرف الطلب مفقود من رابط PayPal.');
      return;
    }
    (async () => {
      try {
        const r = await fetch(`${API}/api/ready-sites/paypal/capture`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authH() },
          body: JSON.stringify({ order_id: orderId, payer_id: payerId }),
        });
        const d = await r.json();
        if (!r.ok || !d.ok) throw new Error(d.detail || 'فشل تأكيد الدفع');
        setStatus('done');
        setMessage('تم الدفع بنجاح! جاري فتح موقعك...');
        const pid = d.project_id;
        setTimeout(() => navigate(`/freebuild/chat/${pid}?source=ready-sites`, { replace: true }), 1500);
      } catch (e) {
        setStatus('error');
        setMessage(e.message || 'فشل تأكيد الدفع. تواصل مع الدعم.');
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
        <p className="text-zinc-400 mb-6">{message}</p>
        {status === 'error' && (
          <button onClick={() => navigate('/ready-sites')}
            className="px-5 py-2 rounded-lg bg-amber-400 text-black font-bold hover:bg-amber-300">
            رجوع
          </button>
        )}
      </div>
    </div>
  );
}
