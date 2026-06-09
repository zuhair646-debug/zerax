import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { BackButton } from '@/components/BackButton';
import {
  Smartphone, Globe, Calendar, CheckCircle2, Sparkles, Zap, Download,
  Lock, ExternalLink, Crown
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const authHeaders = () => {
  const t = localStorage.getItem('token');
  return t ? { Authorization: `Bearer ${t}` } : {};
};

const CarePortal = ({ user }) => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const [showPlans, setShowPlans] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    (async () => {
      try {
        const r = await fetch(`${API}/api/care/project/${projectId}`, { headers: authHeaders() });
        if (!r.ok) throw new Error('failed');
        const data = await r.json();
        setProject(data);
      } catch (e) {
        toast.error('فشل تحميل بيانات المشروع');
        navigate('/dashboard/sites');
      } finally {
        setLoading(false);
      }
    })();
  }, [projectId, navigate]);

  const upgrade = async (plan) => {
    setUpgrading(true);
    try {
      const r = await fetch(`${API}/api/care/upgrade/mobile-app`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, plan, pay_with: 'credits' }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'فشل الترقية');
      toast.success(data.message);
      setProject((p) => ({
        ...p,
        entitlements: { ...p.entitlements, mobile_app: { ...p.entitlements.mobile_app, active: true, plan, expires_at: data.expires_at } },
      }));
      setShowPlans(false);
    } catch (e) {
      toast.error(e.message || 'فشل الترقية');
    } finally {
      setUpgrading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a14] flex items-center justify-center" data-testid="care-loading">
        <div className="text-amber-400">جاري التحميل...</div>
      </div>
    );
  }
  if (!project) return null;

  const mobileApp = project.entitlements?.mobile_app || {};
  const pricing = mobileApp.pricing || {};

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a14] via-[#0a0a18] to-[#0a0a12]" data-testid="care-portal">
      <Navbar user={user} />
      <div className="max-w-4xl mx-auto p-4 md:p-8 pb-24">
        <BackButton to="/dashboard/sites" />

        {/* Header */}
        <div className="rounded-2xl bg-slate-800/40 border border-slate-700 p-6 mb-6">
          <div className="flex items-start gap-4 flex-wrap">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-400 to-pink-500 flex items-center justify-center text-3xl shrink-0">
              🏪
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-amber-300 mb-1 tracking-wider">CARE PORTAL · لوحة الصيانة</p>
              <h1 className="text-2xl md:text-3xl font-black text-white mb-2 truncate">{project.name}</h1>
              <div className="flex gap-3 flex-wrap text-xs">
                <span className="px-2 py-1 rounded bg-slate-900/60 text-gray-300">القالب: <b className="text-amber-300">{project.template_mode || 'app_mode'}</b></span>
                <span className="px-2 py-1 rounded bg-slate-900/60 text-gray-300">السوق: <b className="text-amber-300">{project.market_id || 'sa'}</b></span>
                <span className="px-2 py-1 rounded bg-slate-900/60 text-gray-300">الإصدار: v{project.version || 1}</span>
              </div>
            </div>
            <a
              href={project.preview_url}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="open-live-site-btn"
              className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-sm font-black flex items-center gap-2"
            >
              <ExternalLink className="w-4 h-4" /> عرض الموقع
            </a>
          </div>
        </div>

        {/* ✨ Mobile App Conversion Card (the feature the user asked for) */}
        <div
          className={`rounded-2xl p-6 mb-6 border-2 ${
            mobileApp.active
              ? 'bg-gradient-to-br from-emerald-500/10 to-emerald-700/5 border-emerald-500/40'
              : 'bg-gradient-to-br from-purple-500/10 via-pink-500/10 to-amber-500/10 border-purple-500/30'
          }`}
          data-testid="mobile-app-card"
        >
          <div className="flex items-start gap-4 mb-4 flex-wrap">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center shrink-0">
              <Smartphone className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-lg md:text-xl font-black text-white mb-1 flex items-center gap-2">
                تحويل موقعك إلى تطبيق جوال
                {mobileApp.active && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
                {!mobileApp.active && <Crown className="w-4 h-4 text-amber-400" />}
              </h2>
              <p className="text-sm text-gray-300 leading-relaxed">
                {mobileApp.active
                  ? '✓ زوّار موقعك يشوفون زر "تثبيت التطبيق" تلقائياً — يضغطون فيصير لهم أيقونة على شاشتهم بدون متجر تطبيقات.'
                  : 'فعّل الميزة وزوّار موقعك راح يقدرون يثبتوا موقعك كتطبيق فوري على آيفون وأندرويد — بدون موافقات المتاجر، نشر فوري.'}
              </p>
            </div>
          </div>

          {mobileApp.active ? (
            <div className="mt-4 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-emerald-200/70 text-xs mb-1">الخطة الحالية</p>
                  <p className="text-white font-bold">{mobileApp.plan === 'yearly' ? 'سنوي' : 'شهري'}</p>
                </div>
                <div>
                  <p className="text-emerald-200/70 text-xs mb-1">ينتهي في</p>
                  <p className="text-white font-bold">
                    {mobileApp.expires_at
                      ? new Date(mobileApp.expires_at).toLocaleDateString('ar-SA')
                      : '—'}
                  </p>
                </div>
              </div>
            </div>
          ) : !showPlans ? (
            <>
              {/* Benefits */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
                {[
                  { ico: Zap, t: 'بدون موافقات', s: 'لا حسابات Apple/Google، نشر فوري' },
                  { ico: Smartphone, t: 'iOS + Android', s: 'يشتغل على كل الجوالات بنفس الكود' },
                  { ico: Sparkles, t: 'يتحدّث تلقائياً', s: 'أي تعديل بموقعك يظهر للعميل فوراً' },
                ].map((b, i) => (
                  <div key={i} className="p-3 rounded-lg bg-slate-900/40 border border-slate-700">
                    <b.ico className="w-5 h-5 text-purple-400 mb-2" />
                    <p className="text-white text-sm font-bold mb-1">{b.t}</p>
                    <p className="text-gray-400 text-xs leading-relaxed">{b.s}</p>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setShowPlans(true)}
                data-testid="show-plans-btn"
                className="w-full px-6 py-4 rounded-xl bg-gradient-to-r from-purple-600 via-pink-600 to-amber-500 hover:opacity-90 text-white font-black flex items-center justify-center gap-2 transition-all"
              >
                <Smartphone className="w-5 h-5" /> فعّل التطبيق الآن
              </button>
              <p className="text-center text-gray-500 text-xs mt-3">
                يبدأ من <b className="text-amber-300">{pricing.monthly_sar} ر.س/شهر</b> أو <b className="text-amber-300">{pricing.monthly_credits} نقطة</b>
              </p>
            </>
          ) : (
            <>
              {/* Plans */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <PlanCard
                  testId="plan-monthly"
                  title="شهري"
                  priceSar={pricing.monthly_sar}
                  priceCredits={pricing.monthly_credits}
                  features={['تحويل فوري', 'دعم iOS + Android', 'تحديث تلقائي']}
                  onChoose={() => upgrade('monthly')}
                  disabled={upgrading}
                />
                <PlanCard
                  testId="plan-yearly"
                  title="سنوي"
                  priceSar={pricing.yearly_sar}
                  priceCredits={pricing.monthly_credits * 10}
                  badge="وفّر 20%"
                  features={['كل مميزات الشهري', 'خصم 20%', 'دفعة وحدة، راحة بال']}
                  onChoose={() => upgrade('yearly')}
                  disabled={upgrading}
                  highlight
                />
              </div>
              <button
                type="button"
                onClick={() => setShowPlans(false)}
                className="w-full mt-4 px-4 py-2 rounded-lg border border-slate-700 text-gray-400 text-sm hover:text-white"
              >
                ← رجوع
              </button>
            </>
          )}
        </div>

        {/* Future placeholder cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FeatureCard icon={Globe} title="إعدادات السوق" desc="غيّر العملة، اللغة، طرق الدفع المحلية" locked />
          <FeatureCard icon={Calendar} title="جدول المحتوى" desc="انشر منتجات/وجبات جديدة بصور AI" locked />
        </div>
      </div>
    </div>
  );
};

const PlanCard = ({ title, priceSar, priceCredits, features, onChoose, disabled, badge, highlight, testId }) => (
  <div
    className={`p-5 rounded-xl border-2 ${
      highlight ? 'bg-gradient-to-br from-amber-500/15 to-pink-500/10 border-amber-500/40' : 'bg-slate-900/40 border-slate-700'
    } relative`}
    data-testid={testId}
  >
    {badge && (
      <div className="absolute -top-3 right-4 px-2 py-1 rounded-full bg-amber-500 text-black text-[10px] font-black">
        {badge}
      </div>
    )}
    <h3 className="text-white font-black text-lg mb-1">{title}</h3>
    <div className="my-3">
      <p className="text-3xl font-black text-amber-300">
        {priceSar} <span className="text-sm font-normal text-gray-400">ر.س</span>
      </p>
      <p className="text-gray-500 text-xs mt-1">أو {priceCredits} نقطة</p>
    </div>
    <ul className="text-sm text-gray-300 space-y-1 mb-4">
      {features.map((f, i) => (
        <li key={i} className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" /> {f}
        </li>
      ))}
    </ul>
    <button
      type="button"
      disabled={disabled}
      onClick={onChoose}
      data-testid={`${testId}-btn`}
      className={`w-full py-3 rounded-lg font-black text-sm transition-all ${
        highlight
          ? 'bg-amber-500 hover:bg-amber-400 text-black'
          : 'bg-slate-700 hover:bg-slate-600 text-white'
      } disabled:opacity-50`}
    >
      {disabled ? 'جاري الترقية...' : `اختر ${title}`}
    </button>
  </div>
);

const FeatureCard = ({ icon: Icon, title, desc, locked }) => (
  <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700 opacity-60">
    <div className="flex items-start gap-3">
      <Icon className="w-5 h-5 text-amber-400 mt-1" />
      <div className="flex-1">
        <h3 className="text-white font-bold text-sm mb-1 flex items-center gap-2">
          {title} {locked && <Lock className="w-3 h-3 text-gray-500" />}
        </h3>
        <p className="text-gray-400 text-xs">{desc}</p>
      </div>
    </div>
    <p className="text-gray-500 text-[10px] mt-2 text-center">قريباً</p>
  </div>
);

export default CarePortal;
