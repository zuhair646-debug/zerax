/**
 * BillingStorage — Storage subscription plans page.
 *
 * Lists linear storage tiers (10MB free, +$5 per +50MB up to 1GB) plus
 * recovery options for archived users. Routes to PayPal for paid plans.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { HardDrive, Check, Loader2, ArrowLeft, Archive, Clock, ShieldCheck, AlertTriangle, XCircle, Info } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const fmtGB = (mb) => {
  if (!mb) return '0 MB';
  if (mb < 1024) return `${mb} MB`;
  return `${(mb / 1024).toFixed(0)} GB`;
};

export default function BillingStorage() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState([]);
  const [recovery, setRecovery] = useState([]);
  const [graceDays, setGraceDays] = useState(10);
  const [sub, setSub] = useState(null);
  const [usage, setUsage] = useState(null);
  const [busyPlanId, setBusyPlanId] = useState(null);
  const [busyRecovery, setBusyRecovery] = useState(false);

  const reload = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    try {
      const [plansR, subR, usageR] = await Promise.all([
        fetch(`${API}/api/storage/plans`),
        fetch(`${API}/api/storage/subscription`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/api/freebuild-chat/storage/usage`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (plansR.ok) {
        const d = await plansR.json();
        setPlans(d.plans || []);
        setRecovery(d.recovery || []);
        setGraceDays(d.grace_days || 10);
      }
      if (subR.ok) setSub(await subR.json());
      if (usageR.ok) setUsage(await usageR.json());
    } catch (e) {
      toast.error('تعذر تحميل البيانات: ' + (e?.message || ''));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    reload();
    // PayPal return: capture the pending transaction so the subscription
    // actually flips to active (PayPal does not call our server directly).
    const status = params.get('status');
    const txn = params.get('txn');
    const orderId = params.get('paymentId') || params.get('orderID') || params.get('token');
    const payerId = params.get('PayerID');
    if (status === 'success' && txn) {
      (async () => {
        try {
          const token = localStorage.getItem('token');
          await fetch(`${API}/api/storage/capture`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({ txn_ref: txn, order_id: orderId, payer_id: payerId }),
          });
          toast.success('تم تفعيل اشتراك التخزين بنجاح');
          await reload();
        } catch (e) {
          toast.error('فشل تأكيد الدفع — تواصل مع الدعم إذا تم الخصم');
        }
      })();
    } else if (status === 'recovered' && txn) {
      (async () => {
        try {
          const token = localStorage.getItem('token');
          await fetch(`${API}/api/storage/capture`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({ txn_ref: txn, order_id: orderId, payer_id: payerId }),
          });
          toast.success('تم استرداد ملفاتك. جدّد اشتراكك للحفاظ عليها.');
          await reload();
        } catch (e) {
          toast.error('فشل تأكيد الاسترداد — تواصل مع الدعم');
        }
      })();
    }
  }, [params]); // eslint-disable-line react-hooks/exhaustive-deps

  const startCheckout = async (planId) => {
    const token = localStorage.getItem('token');
    if (!token) { nav('/login'); return; }
    setBusyPlanId(planId);
    try {
      // NEW: PayPal Subscriptions API — true recurring billing (auto-charge monthly).
      const r = await fetch(`${API}/api/storage/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ plan_id: planId }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      if (d.approval_url) window.location.href = d.approval_url;
    } catch (e) {
      toast.error(e?.message || 'تعذر إنشاء الاشتراك');
    } finally {
      setBusyPlanId(null);
    }
  };

  const cancelSubscription = async () => {
    const ok = window.confirm(
      'هل تريد فعلاً إلغاء الاشتراك؟\n\n' +
      '• ستحتفظ بكامل الصلاحيات حتى نهاية الشهر المدفوع.\n' +
      '• لن نسحب أي مبلغ منك بعدها.\n' +
      '• إذا أردت العودة لاحقاً، يجب الاشتراك من جديد + دفع رسم الاسترداد (ضعف سعر باقتك) لفك قفل ملفاتك القديمة.'
    );
    if (!ok) return;
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/storage/cancel-subscription`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل الإلغاء');
      toast.success('تم إلغاء الاشتراك. أنت مغطى حتى نهاية الشهر المدفوع.');
      await reload();
    } catch (e) {
      toast.error(e?.message || 'تعذر الإلغاء');
    }
  };

  const startRecovery = async () => {
    const token = localStorage.getItem('token');
    if (!token) { nav('/login'); return; }
    setBusyRecovery(true);
    try {
      const r = await fetch(`${API}/api/storage/recovery/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ confirm: true }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      if (d.checkout_url) window.location.href = d.checkout_url;
    } catch (e) {
      toast.error(e?.message || 'تعذر إنشاء استرداد');
    } finally {
      setBusyRecovery(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-amber-400" />
      </div>
    );
  }

  const isArchived = sub?.status === 'archived';
  const isPastDue = sub?.status === 'past_due';
  const usedPct = usage ? Math.min(usage.used_pct || 0, 100) : 0;

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 to-black text-white" dir="rtl">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => nav(-1)}
            data-testid="storage-back-btn"
            className="p-2 rounded-full bg-white/5 hover:bg-white/10 transition"
            aria-label="رجوع"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl sm:text-3xl font-black bg-gradient-to-r from-amber-200 to-yellow-400 bg-clip-text text-transparent">
              التخزين والاشتراك
            </h1>
            <p className="text-zinc-400 text-sm mt-1">باقات تخزين موحدة لكل أعمالك — مواقع، تطبيقات، صور، فيديوات.</p>
          </div>
        </div>

        {/* Current status card */}
        {sub && usage && (
          <div className="mb-8 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
            <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <HardDrive className="w-5 h-5 text-amber-300" />
                  <h2 className="text-lg font-black">باقتك الحالية: <span className="text-amber-300">{sub.plan_label_ar}</span></h2>
                </div>
                <p className="text-zinc-400 text-sm">
                  استخدمت <span className="text-white font-bold">{usage.used_mb < 1 ? `${Math.round(usage.used_mb * 1024)} KB` : `${usage.used_mb.toFixed(2)} MB`}</span> من {fmtGB(usage.quota_mb)} ({usedPct.toFixed(1)}%)
                </p>
              </div>
              <div className="text-right">
                {isArchived && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-red-500/20 text-red-300 text-xs font-bold border border-red-500/40">
                    <Archive className="w-3.5 h-3.5" /> مؤرشف
                  </span>
                )}
                {isPastDue && !isArchived && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 text-xs font-bold border border-amber-500/40">
                    <Clock className="w-3.5 h-3.5" />
                    {sub.grace_days_left != null ? `متبقي ${sub.grace_days_left} أيام` : 'فشل تجديد الاشتراك'}
                  </span>
                )}
                {!isPastDue && !isArchived && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-bold border border-emerald-500/40">
                    <ShieldCheck className="w-3.5 h-3.5" /> نشط
                  </span>
                )}
              </div>
            </div>
            {/* Usage bar */}
            <div className="h-2 rounded-full bg-zinc-800 overflow-hidden">
              <div className={`h-full transition-all ${
                usedPct >= 95 ? 'bg-red-500' : usedPct >= 70 ? 'bg-amber-400' : 'bg-emerald-400'
              }`} style={{ width: `${usedPct}%` }} />
            </div>

            {/* Recovery banner for archived users */}
            {isArchived && (
              <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 p-4 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-bold text-red-100 mb-1">ملفاتك محفوظة لكنها مؤرشفة</p>
                  <p className="text-xs text-red-100/80 mb-3">
                    انتهت فترة السماح ({graceDays} أيام). ملفاتك آمنة لدينا لمدة 6 أشهر. ادفع رسم الاسترداد المناسب ثم جدّد اشتراكك.
                  </p>
                  <button
                    onClick={startRecovery}
                    disabled={busyRecovery}
                    data-testid="recovery-checkout-btn"
                    className="px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white text-xs font-black flex items-center gap-2"
                  >
                    {busyRecovery && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    استرداد الآن
                  </button>
                </div>
              </div>
            )}

            {/* Cancel subscription — visible only when user has an active paid sub */}
            {!isArchived && sub.plan_id && sub.plan_id !== 'trial' && sub.plan_id !== 'free' && sub.plan_price_usd > 0 && (
              <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/40 p-4 flex items-start gap-3" data-testid="cancel-subscription-block">
                <Info className="w-5 h-5 text-zinc-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-bold text-zinc-200 mb-1">إدارة الاشتراك</p>
                  <p className="text-xs text-zinc-400 mb-3 leading-relaxed">
                    اشتراكك يُجدّد تلقائياً عبر PayPal كل شهر. عند الإلغاء:
                    <span className="block mt-1.5">• تحتفظ بصلاحياتك حتى نهاية الشهر المدفوع.</span>
                    <span className="block">• لا نسحب أي مبلغ بعدها.</span>
                    <span className="block">• ملفاتك تبقى محفوظة، وتحتاج لدفع <b className="text-rose-300">ضعف سعر باقتك</b> لاستردادها مستقبلاً.</span>
                  </p>
                  <button
                    onClick={cancelSubscription}
                    data-testid="cancel-subscription-btn"
                    className="px-4 py-2 rounded-lg border border-rose-500/40 hover:bg-rose-500/10 text-rose-300 text-xs font-black inline-flex items-center gap-2"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    إلغاء الاشتراك
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Plans grid */}
        <h2 className="text-xl font-black mb-4 text-amber-200">اختر باقتك</h2>
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 mb-6 text-[12px] leading-relaxed">
          <p className="text-amber-200 font-bold mb-2">💡 كيف تعمل الباقات</p>
          <ul className="space-y-1 text-zinc-300">
            <li>• <b className="text-amber-300">تجربة مجانية:</b> 2 ميجا فقط (حتى تتأكد من النظام) — بعدها يجب الاشتراك.</li>
            <li>• <b className="text-amber-300">تسعير خطي:</b> 10 ميجا بـ $3، ثم +$5 لكل +50 ميجا.</li>
            <li>• <b className="text-amber-300">تجديد شهري تلقائي</b> عبر PayPal — يسحب من غير تدخل منك.</li>
            <li>• <b className="text-emerald-300">إلغاء فوري:</b> اضغط زر «إلغاء الاشتراك» → نوقف السحب فوراً وتحتفظ بالصلاحيات للشهر المدفوع.</li>
            <li>• <b className="text-rose-300">عند التأخر في السداد:</b> 10 أيام سماح، ثم يُقفل الوصول لكن الملفات تبقى 6 أشهر.</li>
            <li>• <b className="text-rose-300">رسم الاسترداد:</b> ضعف سعر الباقة (مثال: باقة $5 → استرداد بـ $10).</li>
          </ul>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 mb-12">
          {plans.map((plan) => {
            const isCurrent = sub?.plan_id === plan.id;
            return (
              <div
                key={plan.id}
                data-testid={`storage-plan-${plan.id}`}
                className={`relative rounded-2xl border p-5 transition ${
                  plan.highlight
                    ? 'border-amber-400 bg-gradient-to-b from-amber-500/10 to-zinc-900 shadow-lg shadow-amber-500/10'
                    : 'border-zinc-800 bg-zinc-900/60 hover:border-zinc-700'
                }`}
              >
                {plan.highlight && (
                  <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 text-[10px] font-black px-2.5 py-0.5 rounded-full bg-amber-400 text-black">
                    الأكثر شعبية
                  </span>
                )}
                {isCurrent && (
                  <span className="absolute -top-2.5 right-3 text-[10px] font-black px-2.5 py-0.5 rounded-full bg-emerald-400 text-black">
                    باقتك
                  </span>
                )}
                <div className="text-center">
                  <h3 className="text-base font-black text-amber-200 mb-1">{plan.label_ar}</h3>
                  <p className="text-[11px] text-zinc-400 mb-3 min-h-[28px]">{plan.description_ar}</p>
                  <div className="mb-1">
                    <span className="text-3xl font-black">${plan.price_usd}</span>
                    <span className="text-sm text-zinc-400">/شهر</span>
                  </div>
                  <p className="text-[10px] text-emerald-300 font-bold mb-3">يتجدد شهرياً تلقائياً</p>
                  <div className="text-amber-300 font-black text-lg mb-3">
                    {fmtGB(plan.quota_mb)}
                  </div>
                  <ul className="space-y-1.5 text-[11px] text-zinc-300 mb-3 text-right">
                    <li className="flex items-center gap-1.5">
                      <Check className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                      <span>تخزين موحد لكل المحتوى</span>
                    </li>
                    <li className="flex items-center gap-1.5">
                      <Check className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                      <span>مشاريع غير محدودة</span>
                    </li>
                    <li className="flex items-center gap-1.5">
                      <Check className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                      <span>إلغاء في أي وقت</span>
                    </li>
                  </ul>
                  {plan.recovery_price_usd != null && (
                    <p className="text-[10px] text-rose-300/80 mb-3" data-testid={`recovery-fee-${plan.id}`}>
                      💡 رسم الاسترداد عند التأخر: <b>${plan.recovery_price_usd}</b>
                    </p>
                  )}
                  {(isCurrent || !plan.available) ? (
                    <button
                      onClick={() => startCheckout(plan.id)}
                      disabled
                      data-testid={`storage-plan-cta-${plan.id}`}
                      className="w-full px-4 py-3 rounded-xl text-sm font-black inline-flex items-center justify-center gap-2 transition-all bg-zinc-800 text-zinc-500 cursor-not-allowed"
                    >
                      {isCurrent ? 'باقتك الحالية' : 'قريباً'}
                    </button>
                  ) : (
                    <button
                      onClick={() => startCheckout(plan.id)}
                      disabled={busyPlanId === plan.id}
                      data-testid={`storage-plan-cta-${plan.id}`}
                      className="relative group w-full overflow-hidden rounded-xl shadow-lg shadow-blue-900/30 transition-all hover:scale-[1.02] active:scale-[0.99] disabled:opacity-60 disabled:scale-100 disabled:cursor-wait"
                      style={{ background: 'linear-gradient(180deg, #003087 0%, #0070ba 50%, #ffc439 100%)' }}
                    >
                      <div className="absolute inset-0 opacity-30 pointer-events-none bg-gradient-to-br from-white/20 via-transparent to-transparent" />
                      <div className="relative flex items-center justify-center gap-1.5 py-3 px-4">
                        {busyPlanId === plan.id ? (
                          <Loader2 className="w-4 h-4 animate-spin text-white" />
                        ) : (
                          <>
                            <span className="text-base font-black italic" style={{ color: '#003087', textShadow: '0 1px 0 rgba(255,255,255,0.5)' }}>Pay</span>
                            <span className="text-base font-black italic" style={{ color: '#ffffff', textShadow: '0 1px 0 rgba(0,0,0,0.2)' }}>Pal</span>
                            <span className="mx-1.5 h-3.5 w-px bg-white/40" />
                            <span className="text-sm font-bold text-white drop-shadow">${plan.price_usd}</span>
                          </>
                        )}
                      </div>
                      <span className="pointer-events-none absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 bg-gradient-to-r from-transparent via-white/15 to-transparent" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* How it works */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
            <div className="w-9 h-9 rounded-full bg-amber-500/20 flex items-center justify-center mb-3">
              <ShieldCheck className="w-5 h-5 text-amber-300" />
            </div>
            <h3 className="font-black mb-1">دفع شهري آمن</h3>
            <p className="text-xs text-zinc-400">يتجدد اشتراكك تلقائياً كل شهر عبر PayPal. تقدر تلغي في أي وقت.</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
            <div className="w-9 h-9 rounded-full bg-amber-500/20 flex items-center justify-center mb-3">
              <Clock className="w-5 h-5 text-amber-300" />
            </div>
            <h3 className="font-black mb-1">{graceDays} أيام فترة سماح</h3>
            <p className="text-xs text-zinc-400">إذا فشل التجديد، نحاول مرة أخرى ثم نقفل الوصول للملفات بعد {graceDays} أيام.</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
            <div className="w-9 h-9 rounded-full bg-rose-500/20 flex items-center justify-center mb-3">
              <Archive className="w-5 h-5 text-rose-300" />
            </div>
            <h3 className="font-black mb-1">رسم استرداد = ضعف الباقة</h3>
            <p className="text-xs text-zinc-400">ملفاتك تبقى محفوظة بعد التأخر، لكن لاستعادة الوصول ادفع <b className="text-rose-300">ضعف سعر باقتك</b>.</p>
          </div>
        </div>

        {/* Terms summary */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 mb-12" data-testid="storage-terms">
          <h3 className="text-base font-black text-amber-200 mb-3 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" /> الشروط والأحكام للتخزين
          </h3>
          <ol className="space-y-2 text-xs text-zinc-300 leading-relaxed list-decimal pr-5">
            <li>الاشتراك <b className="text-amber-300">شهري ويتجدد تلقائياً</b> عبر PayPal حتى تقوم بإلغائه.</li>
            <li>إذا فشل التجديد أو لم تدفع، يبدأ <b>عداد {graceDays} أيام</b> سماح. خلالها نحاول السحب من حسابك تلقائياً.</li>
            <li>بعد انتهاء فترة السماح <b className="text-rose-300">يُقفل الوصول</b> لكل ملفاتك (المواقع، الصور، التطبيقات...) — لكنها <b>تبقى محفوظة عندنا</b> لمدة 6 أشهر.</li>
            <li>لاستعادة الوصول لملفاتك ادفع <b className="text-rose-300">رسم استرداد يساوي ضعف سعر باقتك الشهرية</b> + التجديد الشهري.</li>
            <li>عند إلغاء الاشتراك تنطبق نفس قواعد الاسترداد إذا أردت استعادة الوصول لاحقاً.</li>
            <li>الدفع بالكامل عبر PayPal — لا نحفظ بيانات بطاقتك على خوادمنا.</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
