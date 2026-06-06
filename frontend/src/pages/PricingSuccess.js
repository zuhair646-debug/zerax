import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { CheckCircle2, XCircle, Loader2, Download, Mail } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function PricingSuccess({ user }) {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const orderId = params.get('order') || localStorage.getItem('pending_order_id');
  const [state, setState] = useState('capturing'); // capturing | success | error
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (!orderId || !user) {
      setState('error');
      setErrorMsg('لا يوجد طلب نشط — أعد المحاولة من صفحة التسعير');
      return;
    }
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const r = await axios.post(
          `${API}/api/pricing/capture`,
          { order_id: orderId },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setResult(r.data);
        setState('success');
        localStorage.removeItem('pending_order_id');
      } catch (e) {
        setErrorMsg(e.response?.data?.detail || 'فشل تحصيل الدفعة');
        setState('error');
      }
    })();
  }, [orderId, user]);

  if (state === 'capturing') {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center" dir="rtl">
        <div className="text-center">
          <Loader2 className="w-16 h-16 text-amber-400 animate-spin mx-auto mb-4" />
          <p className="text-xl">جاري تأكيد دفعتك...</p>
          <p className="text-zinc-500 text-sm mt-2">لحظات فقط</p>
        </div>
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center p-8" dir="rtl">
        <div className="bg-zinc-900 border border-red-500/30 rounded-2xl p-10 max-w-md text-center">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">حصل خلل</h1>
          <p className="text-zinc-400 mb-6">{errorMsg}</p>
          <button
            onClick={() => navigate('/pricing')}
            data-testid="back-to-pricing"
            className="px-6 py-3 bg-amber-500 text-zinc-900 rounded-lg font-bold hover:bg-amber-400"
          >
            رجوع للأسعار
          </button>
        </div>
      </div>
    );
  }

  const inv = result?.invoice;
  return (
    <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center p-8" dir="rtl">
      <div className="bg-zinc-900 border border-emerald-500/30 rounded-2xl p-10 max-w-lg w-full">
        <CheckCircle2 className="w-20 h-20 text-emerald-400 mx-auto mb-6" />
        <h1 className="text-3xl font-bold text-center mb-2" data-testid="billing-success-title">تم الدفع بنجاح! 🎉</h1>
        <p className="text-center text-zinc-400 mb-8">شكراً لاشتراكك في Zitex</p>

        <div className="bg-black/30 rounded-xl p-6 space-y-3 mb-6">
          <div className="flex justify-between">
            <span className="text-zinc-500">رقم الفاتورة:</span>
            <span className="font-mono text-sm">{inv?.invoice_number}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-500">المبلغ المدفوع:</span>
            <span className="font-bold text-amber-400">${inv?.total_usd?.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-500">الشعلات المُضافة:</span>
            <span className="font-bold text-emerald-400" data-testid="credits-added">
              {result?.credits_added?.toLocaleString()} ✨
            </span>
          </div>
          {result?.bonus_credits > 0 && (
            <div className="flex justify-between text-sm">
              <span className="text-zinc-500">بونص أول شحن:</span>
              <span className="text-emerald-400">+{result.bonus_credits.toLocaleString()}</span>
            </div>
          )}
          <div className="flex justify-between border-t border-zinc-800 pt-3">
            <span className="text-zinc-500">رصيدك الجديد:</span>
            <span className="font-bold">{result?.new_balance?.toLocaleString()} شعلة</span>
          </div>
        </div>

        <div className="flex gap-3">
          <a
            href={`${API}/api/pricing/invoices/${inv?.id}/pdf`}
            target="_blank"
            rel="noreferrer"
            data-testid="download-invoice-pdf"
            className="flex-1 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-lg font-bold text-center flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4" /> تحميل PDF
          </a>
          <button
            onClick={() => navigate('/billing')}
            data-testid="go-to-billing"
            className="flex-1 py-3 bg-amber-500 hover:bg-amber-400 text-zinc-900 rounded-lg font-bold"
          >
            لوحة الفواتير
          </button>
        </div>

        <p className="text-center text-xs text-zinc-500 mt-6 flex items-center justify-center gap-1">
          <Mail className="w-3 h-3" /> نسخة من الفاتورة أُرسلت إلى {inv?.customer_email}
        </p>
      </div>
    </div>
  );
}
