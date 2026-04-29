import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Lock, Sparkles, Check, Loader2, Crown, ArrowLeft } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

/**
 * SubscriptionGate — wraps the Website Studio route.
 * - Checks /api/billing/subscription on mount
 * - If active or owner bypass → renders children
 * - Else renders a paywall that initiates Stripe Checkout
 */
export default function SubscriptionGate({ children }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [sub, setSub] = useState(null);
  const [creating, setCreating] = useState(false);

  const checkSubscription = async () => {
    try {
      const res = await fetch(`${API}/api/billing/subscription`, { headers: authH() });
      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          navigate('/login');
          return;
        }
        throw new Error('failed');
      }
      const data = await res.json();
      setSub(data);
    } catch (_e) {
      setSub({ active: false, bypass: false });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { checkSubscription(); }, []);

  const startCheckout = async () => {
    setCreating(true);
    try {
      const res = await fetch(`${API}/api/billing/checkout`, {
        method: 'POST',
        headers: { ...authH(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          package_id: 'studio_monthly',
          origin_url: window.location.origin,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Checkout failed');
      }
      const data = await res.json();
      if (!data.url) throw new Error('لم يتم استلام رابط الدفع');
      window.location.href = data.url;
    } catch (e) {
      toast.error(e.message || 'فشل بدء عملية الدفع');
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-white" data-testid="gate-loading">
        <div className="flex items-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-yellow-400" />
          <span>جاري التحقق من اشتراكك...</span>
        </div>
      </div>
    );
  }

  if (sub?.active) {
    return children;
  }

  // PAYWALL
  return (
    <div
      className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white flex items-center justify-center p-4"
      data-testid="subscription-gate"
    >
      <div className="absolute inset-0 opacity-30 pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(circle at 20% 20%, rgba(250,204,21,0.15), transparent 50%), radial-gradient(circle at 80% 80%, rgba(168,85,247,0.15), transparent 50%)'
        }}
      />

      <button
        onClick={() => navigate('/dashboard')}
        className="absolute top-6 right-6 text-white/60 hover:text-white flex items-center gap-2 text-sm z-10"
        data-testid="gate-back-btn"
      >
        <ArrowLeft className="w-4 h-4 rotate-180" />
        العودة للوحة التحكم
      </button>

      <div className="relative z-10 max-w-2xl w-full">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-yellow-400 to-orange-500 mb-4 shadow-2xl shadow-yellow-500/30">
            <Lock className="w-8 h-8 text-slate-900" />
          </div>
          <h1 className="text-3xl md:text-4xl font-bold mb-3">
            استوديو المواقع احترافي
          </h1>
          <p className="text-white/70 text-base md:text-lg max-w-lg mx-auto">
            ابنِ موقعاً متكاملاً مع متجر إلكتروني، سلة، دفع، وسائقين — بمحادثة واحدة مع الذكاء الاصطناعي.
          </p>
        </div>

        <div
          className="relative rounded-3xl border-2 border-yellow-500/40 bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-xl p-6 md:p-8 shadow-2xl shadow-yellow-500/10"
          data-testid="subscription-card"
        >
          <div className="absolute -top-3 right-6 bg-gradient-to-r from-yellow-400 to-orange-500 text-slate-900 px-4 py-1 rounded-full text-xs font-black flex items-center gap-1.5">
            <Crown className="w-3.5 h-3.5" />
            باقة واحدة — كل شيء
          </div>

          <div className="flex items-end gap-2 mb-6 mt-2">
            <span className="text-5xl md:text-6xl font-black bg-gradient-to-r from-yellow-400 to-orange-500 bg-clip-text text-transparent">
              $50
            </span>
            <span className="text-white/60 text-lg mb-2">/ شهرياً</span>
          </div>

          <ul className="space-y-3 mb-8">
            {[
              'مواقع غير محدودة بمحادثة AI',
              'متجر إلكتروني كامل مع سلة ودفع',
              'لوحة تحكم لعملائك + تتبع الطلبات',
              'نظام سائقين مع GPS وخرائط حية',
              'نقاط ولاء، كوبونات، تطبيق PWA',
              'دعم فني مباشر + ترقيات مستمرة',
            ].map((feat) => (
              <li key={feat} className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-500/20 text-green-400 flex items-center justify-center mt-0.5">
                  <Check className="w-3.5 h-3.5" />
                </span>
                <span className="text-white/90 text-sm md:text-base">{feat}</span>
              </li>
            ))}
          </ul>

          <button
            onClick={startCheckout}
            disabled={creating}
            className="w-full group relative overflow-hidden rounded-xl bg-gradient-to-r from-yellow-400 to-orange-500 text-slate-900 font-black text-lg py-4 px-6 transition-all hover:scale-[1.02] hover:shadow-2xl hover:shadow-yellow-500/40 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
            data-testid="start-checkout-btn"
          >
            <span className="relative z-10 flex items-center justify-center gap-2">
              {creating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  جاري التحويل إلى Stripe...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  اشترك الآن وابدأ البناء
                </>
              )}
            </span>
          </button>

          <p className="text-center text-xs text-white/50 mt-4">
            دفع آمن عبر Stripe • يمكنك الإلغاء في أي وقت • ضمان استرداد 7 أيام
          </p>
        </div>

        <p className="text-center text-white/40 text-xs mt-6" data-testid="test-mode-notice">
          وضع التجربة مُفعّل — استخدم بطاقة 4242 4242 4242 4242 أي تاريخ مستقبلي و أي CVC
        </p>
      </div>
    </div>
  );
}
