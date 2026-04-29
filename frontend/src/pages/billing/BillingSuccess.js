import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Loader2, AlertCircle, Sparkles } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

const MAX_ATTEMPTS = 8;
const POLL_INTERVAL_MS = 2500;

export default function BillingSuccess() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const sessionId = params.get('session_id');

  const [status, setStatus] = useState('polling'); // polling | paid | expired | error
  const [message, setMessage] = useState('جاري التحقق من حالة الدفع...');
  const attemptsRef = useRef(0);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!sessionId) {
      setStatus('error');
      setMessage('معرف الجلسة مفقود.');
      return;
    }

    const poll = async () => {
      attemptsRef.current += 1;
      try {
        const res = await fetch(`${API}/api/billing/status/${sessionId}`, { headers: authH() });
        if (!res.ok) throw new Error('status check failed');
        const data = await res.json();

        if (data.payment_status === 'paid') {
          setStatus('paid');
          setMessage('تم تفعيل اشتراكك بنجاح — مرحباً بك في الاستوديو.');
          return;
        }
        if (data.status === 'expired') {
          setStatus('expired');
          setMessage('انتهت صلاحية جلسة الدفع. يرجى المحاولة مرة أخرى.');
          return;
        }
        if (attemptsRef.current >= MAX_ATTEMPTS) {
          setStatus('error');
          setMessage('استغرق التحقق وقتاً طويلاً. يرجى مراجعة بريدك أو تحديث الصفحة.');
          return;
        }
        setMessage(`جاري المعالجة... (${attemptsRef.current}/${MAX_ATTEMPTS})`);
        timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
      } catch (_e) {
        if (attemptsRef.current >= MAX_ATTEMPTS) {
          setStatus('error');
          setMessage('حدث خطأ أثناء التحقق. حاول تحديث الصفحة.');
        } else {
          timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        }
      }
    };
    poll();
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [sessionId]);

  const icon = status === 'paid' ? <CheckCircle2 className="w-16 h-16 text-green-400" />
    : status === 'error' || status === 'expired' ? <AlertCircle className="w-16 h-16 text-red-400" />
    : <Loader2 className="w-16 h-16 text-yellow-400 animate-spin" />;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 to-slate-900 flex items-center justify-center p-4 text-white" dir="rtl">
      <div className="max-w-md w-full rounded-3xl border border-white/10 bg-slate-900/80 backdrop-blur-xl p-8 text-center" data-testid="billing-success-card">
        <div className="flex justify-center mb-4">{icon}</div>
        <h1 className="text-2xl md:text-3xl font-bold mb-3">
          {status === 'paid' ? '🎉 تم الدفع بنجاح' : status === 'expired' ? 'انتهت الجلسة' : status === 'error' ? 'حدث خطأ' : 'لحظة من فضلك...'}
        </h1>
        <p className="text-white/70 mb-6" data-testid="billing-status-message">{message}</p>

        {status === 'paid' && (
          <button
            onClick={() => navigate('/websites')}
            className="w-full rounded-xl bg-gradient-to-r from-yellow-400 to-orange-500 text-slate-900 font-bold py-3 px-4 hover:scale-[1.02] transition-transform flex items-center justify-center gap-2"
            data-testid="go-to-studio-btn"
          >
            <Sparkles className="w-5 h-5" />
            ابدأ البناء الآن
          </button>
        )}
        {(status === 'expired' || status === 'error') && (
          <button
            onClick={() => navigate('/websites')}
            className="w-full rounded-xl bg-white/10 hover:bg-white/20 text-white font-semibold py-3 px-4 transition"
            data-testid="retry-btn"
          >
            العودة وإعادة المحاولة
          </button>
        )}
      </div>
    </div>
  );
}
