/**
 * Freebuild Checkout — decision screen showing payment options for the project.
 * Three packages: Source-only ($100), Pro ($249), Monthly hosting ($25).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Check, Sparkles, Code, Cloud, Shield, Loader2, ArrowLeft } from 'lucide-react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const PACKAGES = [
  {
    id: 'code_only',
    price: '$100',
    label: 'الكود الكامل',
    tagline: 'دفعة واحدة — ملكية كاملة',
    color: 'from-emerald-500 to-cyan-500',
    icon: Code,
    perks: [
      'ZIP فيه index.html + كل الصور + README + LICENSE',
      'استضفه على أي مكان (Netlify / Vercel / Hostinger)',
      'مُلكيتك بالكامل — احذف Zenrex، عدّل ما تبيه',
      'لا اشتراك شهري — دفعة واحدة فقط',
    ],
    recommended: false,
  },
  {
    id: 'code_pro',
    price: '$249',
    label: 'الباقة الاحترافية',
    tagline: 'كود + Multi-Page + استشارة',
    color: 'from-purple-500 to-pink-500',
    icon: Sparkles,
    perks: [
      'كل ما في الباقة الأولى',
      'تحويل الموقع لـMulti-Page (about, contact, products)',
      'SEO advanced + Schema.org',
      'استشارة 30 دقيقة مع مهندس Zenrex',
      'دعم بريدي 90 يوم',
    ],
    recommended: true,
  },
  {
    id: 'hosting_month',
    price: '$25',
    label: 'استضافة شهرية',
    tagline: 'اشتراك متجدد — تعديلات مستمرة',
    color: 'from-amber-500 to-orange-500',
    icon: Cloud,
    perks: [
      'استضافة على zenrex.ai/s/[اسمك]',
      'SSL + CDN + نسخ احتياطية يومية',
      '200 رسالة AI شهرياً للتعديلات',
      'تحليلات زوار + Status page',
      'ألغِ في أي وقت',
    ],
    recommended: false,
  },
];

export default function FreebuildCheckout() {
  const { pid } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState(null);

  const token = localStorage.getItem('token') || sessionStorage.getItem('token');

  const pollStatus = useCallback(async (sessionId, attempts = 0) => {
    if (attempts > 30) {
      setPolling(false);
      toast.error('انتهت مدة فحص الدفع. تحقّق من بريدك.');
      return;
    }
    try {
      const r = await fetch(`${API}/api/freebuild-chat/payments/status/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error('status fetch failed');
      const d = await r.json();
      setPaymentStatus(d);
      if (d.payment_status === 'paid') {
        setPolling(false);
        toast.success('🎉 الدفع تم بنجاح! الكود مفتوح');
        setTimeout(() => navigate(`/freebuild/chat/${pid}`), 2000);
        return;
      }
      if (d.status === 'expired') {
        setPolling(false);
        toast.error('انتهت صلاحية الجلسة. حاول مرة ثانية');
        return;
      }
      setTimeout(() => pollStatus(sessionId, attempts + 1), 2500);
    } catch (e) {
      setTimeout(() => pollStatus(sessionId, attempts + 1), 3000);
    }
  }, [token, navigate, pid]);

  // Check if we returned from Stripe via success URL
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const sid = params.get('session_id');
    if (sid) {
      setPolling(true);
      pollStatus(sid);
    }
  }, [location.search, pollStatus]);

  const handleBuy = async (packageId) => {
    if (!token) {
      toast.error('سجّل دخولك أولاً');
      return;
    }
    setLoading(packageId);
    try {
      const fd = new FormData();
      fd.append('package_id', packageId);
      fd.append('origin', window.location.origin);
      const r = await fetch(`${API}/api/freebuild-chat/project/${pid}/checkout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (!r.ok) {
        const t = await r.text();
        throw new Error(t.slice(0, 200));
      }
      const d = await r.json();
      window.location.href = d.url;
    } catch (e) {
      toast.error(`فشل بدء الدفع: ${e.message}`);
      setLoading(null);
    }
  };

  if (polling) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center" dir="rtl">
        <Card className="bg-zinc-900 border-zinc-800 p-8 max-w-md text-center">
          <Loader2 className="w-12 h-12 text-emerald-400 animate-spin mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">جاري تأكيد الدفع...</h2>
          <p className="text-zinc-400 text-sm">
            {paymentStatus?.payment_status === 'paid'
              ? '✅ تم! نوجّهك للموقع الآن...'
              : 'لا تغلق هذي الصفحة — راح ناخذ ثوان معدودة'}
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" dir="rtl" data-testid="freebuild-checkout">
      <div className="max-w-6xl mx-auto px-4 py-10">
        <Button
          variant="ghost"
          onClick={() => navigate(`/freebuild/chat/${pid}`)}
          className="mb-6 text-zinc-400"
          data-testid="back-to-chat-btn"
        >
          <ArrowLeft className="w-4 h-4 ml-1" /> رجوع للمحادثة
        </Button>

        <div className="text-center mb-10">
          <Shield className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <h1 className="text-3xl md:text-4xl font-bold mb-3">اختر باقتك واحصد موقعك</h1>
          <p className="text-zinc-400 max-w-2xl mx-auto">
            موقعك جاهز. اختر كيف تبيّ تستلمه — كود ملكية كاملة، أو استضافة شهرية مع تعديلات مستمرة.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {PACKAGES.map((pkg) => {
            const Icon = pkg.icon;
            return (
              <Card
                key={pkg.id}
                className={`relative bg-zinc-900 border-2 ${
                  pkg.recommended ? 'border-purple-500/50 shadow-lg shadow-purple-500/10' : 'border-zinc-800'
                } p-6 flex flex-col hover:scale-[1.02] transition-transform`}
                data-testid={`package-${pkg.id}`}
              >
                {pkg.recommended && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                    ⭐ موصى به
                  </div>
                )}
                <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${pkg.color} flex items-center justify-center mb-4`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-bold mb-1">{pkg.label}</h3>
                <p className="text-zinc-400 text-sm mb-4">{pkg.tagline}</p>
                <div className="text-4xl font-extrabold mb-1">{pkg.price}</div>
                <div className="text-xs text-zinc-500 mb-5">
                  {pkg.id === 'hosting_month' ? '/شهر' : 'دفعة واحدة'}
                </div>
                <ul className="space-y-2 mb-6 flex-1">
                  {pkg.perks.map((perk, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                      <Check className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                      <span>{perk}</span>
                    </li>
                  ))}
                </ul>
                <Button
                  className={`w-full bg-gradient-to-r ${pkg.color} hover:opacity-90 text-white font-bold`}
                  onClick={() => handleBuy(pkg.id)}
                  disabled={loading === pkg.id || !!loading}
                  data-testid={`buy-${pkg.id}-btn`}
                >
                  {loading === pkg.id ? (
                    <><Loader2 className="w-4 h-4 ml-2 animate-spin" /> جاري التحويل لـStripe...</>
                  ) : (
                    `اشترِ بـ${pkg.price}`
                  )}
                </Button>
              </Card>
            );
          })}
        </div>

        <p className="text-center text-xs text-zinc-500 mt-8">
          🔒 الدفع آمن عبر Stripe. لا نحفظ بيانات بطاقتك. تطبق
          <a href="#" className="text-emerald-400 mx-1">الشروط والأحكام</a>
          و
          <a href="#" className="text-emerald-400 mx-1">سياسة الاسترداد</a>.
        </p>
      </div>
    </div>
  );
}
