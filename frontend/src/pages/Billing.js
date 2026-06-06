import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Wallet, FileText, Download, RotateCw, Sparkles, History } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function Billing({ user }) {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    refresh();
  }, [user]);

  const refresh = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const [s, inv] = await Promise.all([
        axios.get(`${API}/api/pricing/me`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/api/pricing/invoices`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      setSummary(s.data);
      setInvoices(inv.data.invoices);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const resend = async (id) => {
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(
        `${API}/api/pricing/invoices/${id}/resend`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      alert(r.data.ok ? '✅ أُرسلت الفاتورة من جديد' : '⚠️ تعذّر الإرسال');
    } catch {
      alert('فشل الإرسال');
    }
  };

  const testCharge = async (serviceKey) => {
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(
        `${API}/api/pricing/test-charge?service_key=${serviceKey}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      alert(`✅ تم خصم ${r.data.credits_charged} شعلة (${r.data.label_ar})\nرصيدك الجديد: ${Math.floor(r.data.new_balance).toLocaleString()}`);
      refresh();
    } catch (e) {
      alert(`❌ ${e.response?.data?.detail || 'فشل الخصم'}`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center" dir="rtl">
        جاري التحميل...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-6" dir="rtl">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Wallet className="w-8 h-8 text-amber-400" /> اشتراكي وفواتيري
          </h1>
          <button
            onClick={refresh}
            data-testid="refresh-billing"
            className="p-2 rounded-lg bg-zinc-900 hover:bg-zinc-800"
          >
            <RotateCw className="w-5 h-5" />
          </button>
        </div>

        {/* Balance card */}
        <div className="bg-gradient-to-br from-amber-500/10 to-rose-500/10 border border-amber-500/30 rounded-2xl p-8 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-zinc-400 mb-2">رصيدك الحالي من الشعلات</p>
              <div className="text-5xl font-bold text-amber-400" data-testid="balance-display">
                {Math.floor(summary?.balance || 0).toLocaleString()}
              </div>
              <p className="text-zinc-500 text-sm mt-2">
                ≈ ${summary?.balance_usd_equivalent?.toFixed(2)} قيمة استخدام
              </p>
            </div>
            <Sparkles className="w-20 h-20 text-amber-400/30" />
          </div>
          <button
            onClick={() => navigate('/pricing')}
            data-testid="topup-btn"
            className="mt-6 px-6 py-3 bg-amber-500 text-zinc-900 rounded-lg font-bold hover:bg-amber-400"
          >
            شحن المزيد
          </button>
        </div>

        {/* Test charge widget — verify deduction works */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-8">
          <h2 className="text-lg font-bold mb-3">🧪 تجربة خصم الشعلات</h2>
          <p className="text-zinc-500 text-sm mb-4">
            اضغط زر لمحاكاة استخدام خدمة وتأكد إن الشعلات تُخصم من رصيدك (بدون استدعاء AI فعلياً).
          </p>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => testCharge('chat_message')} data-testid="test-charge-chat" className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm">
              رسالة شات (10 شعلات)
            </button>
            <button onClick={() => testCharge('image_nano_banana')} data-testid="test-charge-image" className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm">
              صورة Nano Banana (80 شعلة)
            </button>
            <button onClick={() => testCharge('video_fal_5s')} data-testid="test-charge-video" className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm">
              فيديو Fal 5ث (250 شعلة)
            </button>
            <button onClick={() => testCharge('voice_eleven_min')} data-testid="test-charge-voice" className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm">
              صوت ElevenLabs/د (1000 شعلة)
            </button>
          </div>
        </div>

        {/* Active subscription */}
        {summary?.subscription && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-8">
            <h2 className="text-lg font-bold mb-3">باقتك الحالية</h2>
            <div className="flex justify-between items-center">
              <div>
                <div className="text-2xl font-bold text-amber-400">{summary.subscription.plan_id}</div>
                <div className="text-sm text-zinc-500">
                  {summary.subscription.billing_cycle === 'yearly' ? 'سنوي' : 'شهري'} — تنتهي في{' '}
                  {new Date(summary.subscription.expires_at).toLocaleDateString('ar-SA')}
                </div>
              </div>
              <button
                onClick={() => navigate('/pricing')}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm"
              >
                ترقية
              </button>
            </div>
          </div>
        )}

        {/* Invoices */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-8">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5" /> الفواتير
          </h2>
          {invoices.length === 0 ? (
            <p className="text-zinc-500 text-center py-8">لا توجد فواتير بعد</p>
          ) : (
            <div className="space-y-2">
              {invoices.map((inv) => (
                <div
                  key={inv.id}
                  data-testid={`invoice-${inv.invoice_number}`}
                  className="flex items-center justify-between p-4 bg-black/30 rounded-lg"
                >
                  <div>
                    <div className="font-mono text-sm">{inv.invoice_number}</div>
                    <div className="text-xs text-zinc-500">{inv.issued_at_display}</div>
                  </div>
                  <div className="text-amber-400 font-bold">${inv.total_usd?.toFixed(2)}</div>
                  <div className="flex gap-2">
                    <a
                      href={`${API}/api/pricing/invoices/${inv.id}/pdf`}
                      target="_blank"
                      rel="noreferrer"
                      data-testid={`dl-${inv.invoice_number}`}
                      className="p-2 bg-zinc-800 hover:bg-zinc-700 rounded"
                      title="تحميل"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                    <button
                      onClick={() => resend(inv.id)}
                      data-testid={`resend-${inv.invoice_number}`}
                      className="p-2 bg-zinc-800 hover:bg-zinc-700 rounded"
                      title="إعادة إرسال"
                    >
                      <RotateCw className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent transactions */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <History className="w-5 h-5" /> آخر العمليات على الرصيد
          </h2>
          {(summary?.transactions || []).length === 0 ? (
            <p className="text-zinc-500 text-center py-8">لا توجد عمليات بعد</p>
          ) : (
            <div className="space-y-2">
              {summary.transactions.map((t, i) => (
                <div key={i} className="flex justify-between items-center p-3 bg-black/30 rounded-lg text-sm">
                  <div>
                    <span className={t.type === 'credit' ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                      {t.type === 'credit' ? '+' : '-'}{Math.floor(t.amount).toLocaleString()}
                    </span>
                    <span className="text-zinc-500 ms-3">{t.reason}</span>
                  </div>
                  <div className="text-zinc-600 text-xs">{new Date(t.ts).toLocaleString('ar-SA')}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
