import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from '@/components/Navbar';
import { useNavigate } from 'react-router-dom';
import {
  Coins, Crown, Image as ImageIcon, Video, FileText, Globe,
  Share2, User, CreditCard, Smartphone, Sparkles, Gift, Heart,
  Download, Send, TrendingUp, Receipt, Settings, Award,
} from 'lucide-react';
import { BackButton } from '@/components/BackButton';

// ─── Sections curated for a CUSTOMER DASHBOARD ───────────────────────
// Philosophy: this page is the user's PRIVATE WORKSPACE.
// All "create from scratch" tiles live on the LANDING page.
// Here we show: storage vaults · sharing · account · billing · history.

const VAULTS = [
  { title: 'صوري المحفوظة', desc: 'كل الصور اللي ولدتها', icon: ImageIcon, path: '/dashboard/my-images', accent: '#a78bfa', gradient: 'from-purple-600/40 to-violet-700/20', bgImage: 'https://images.unsplash.com/photo-1542038784456-1ea8e935640e?auto=format&fit=crop&w=800&q=70', countKey: 'images' },
  { title: 'فيديوهاتي', desc: 'مكتبتك الكاملة من الفيديوهات', icon: Video, path: '/dashboard/my-videos', accent: '#fb923c', gradient: 'from-orange-600/40 to-red-700/20', bgImage: 'https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=800&q=70', countKey: 'videos' },
  { title: 'إنشاء موقع بالشات الذكي', desc: 'شات حر + توليد أصول + معاينة لحظية', icon: Globe, path: '/freebuild/chat', accent: '#22d3ee', gradient: 'from-cyan-600/40 to-blue-700/20', bgImage: 'https://images.unsplash.com/photo-1467232004584-a241de8bcf5d?auto=format&fit=crop&w=800&q=70' },
  { title: 'المواقع الجاهزة', desc: 'معالج 6 خطوات · 6 أنماط · 24 ميزة (مطاعم)', icon: Globe, path: '/ready-sites', accent: '#f59e0b', gradient: 'from-amber-600/40 to-pink-700/20', bgImage: 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&q=70' },
  { title: 'مواقعي', desc: 'كل المواقع المنجزة + روابطها', icon: Globe, path: '/dashboard/websites', accent: '#22d3ee', gradient: 'from-cyan-600/40 to-blue-700/20', bgImage: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=800&q=70', countKey: 'websites' },
  { title: 'تطبيقاتي وألعابي', desc: 'كل اللي طورتها بالـ AI', icon: Smartphone, path: '/dashboard/my-apps', accent: '#a855f7', gradient: 'from-violet-600/40 to-purple-700/20', bgImage: 'https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&w=800&q=70', countKey: 'apps' },
];

const SHARING = [
  { title: 'النشر السريع', desc: 'انشر على وسائل التواصل بنقرة', icon: Send, path: '/dashboard/share', accent: '#10b981', gradient: 'from-emerald-600/40 to-green-700/20', bgImage: 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=800&q=70' },
  { title: 'سجل المشاركات', desc: 'كل اللي نشرته وأين', icon: Share2, path: '/dashboard/share-history', accent: '#0ea5e9', gradient: 'from-sky-600/40 to-cyan-700/20', bgImage: 'https://images.unsplash.com/photo-1611926653458-09294b3142bf?auto=format&fit=crop&w=800&q=70' },
  { title: 'الحسابات المرتبطة', desc: 'انستقرام · تويتر · فيسبوك · تيك توك', icon: Heart, path: '/dashboard/social-accounts', accent: '#ec4899', gradient: 'from-pink-600/40 to-rose-700/20', bgImage: 'https://images.unsplash.com/photo-1611162616305-c69b3fa7fbe0?auto=format&fit=crop&w=800&q=70' },
  { title: 'التنزيلات', desc: 'صيغ متعددة + جودات مختلفة', icon: Download, path: '/dashboard/downloads', accent: '#06b6d4', gradient: 'from-cyan-600/40 to-teal-700/20', bgImage: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=70' },
];

const ACCOUNT = [
  { title: 'الفواتير والاشتراك', desc: 'إدارة باقتك + تاريخ الدفع', icon: Receipt, path: '/billing', accent: '#fbbf24', gradient: 'from-amber-600/40 to-yellow-700/20', bgImage: 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=800&q=70' },
  { title: 'شراء نقاط', desc: 'باقات + خصومات + Pay in 4', icon: Coins, path: '/pricing', accent: '#f59e0b', gradient: 'from-yellow-600/40 to-amber-700/20', bgImage: 'https://images.unsplash.com/photo-1605792657660-596af9009e82?auto=format&fit=crop&w=800&q=70' },
  { title: 'برنامج الإحالة', desc: 'عمولة على كل عميل تحضره', icon: Award, path: '/affiliate', accent: '#eab308', gradient: 'from-yellow-600/40 to-orange-700/20', bgImage: 'https://images.unsplash.com/photo-1579621970795-87facc2f976d?auto=format&fit=crop&w=800&q=70' },
  { title: 'ملفي الشخصي', desc: 'الاسم · الإيميل · كلمة المرور · الأجهزة', icon: User, path: '/dashboard/profile', accent: '#94a3b8', gradient: 'from-slate-600/40 to-slate-700/20', bgImage: 'https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=800&q=70' },
];

const ClientDashboard = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [counts, setCounts] = useState({ images: 0, videos: 0, websites: 0, apps: 0, orders: 0 });
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    const token = localStorage.getItem('token');
    if (!token) return;

    const controller = new AbortController();
    const headers = { Authorization: `Bearer ${token}` };
    const API = process.env.REACT_APP_BACKEND_URL;
    const safeFetch = (url) =>
      Promise.race([
        fetch(url, { headers, signal: controller.signal })
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null),
        new Promise((res) => setTimeout(() => res(null), 6000)),
      ]);

    Promise.all([
      safeFetch(`${API}/api/generate/images/history`),
      safeFetch(`${API}/api/generate/videos/history`),
      safeFetch(`${API}/api/websites`),
      safeFetch(`${API}/api/requests`),
      safeFetch(`${API}/api/auth/me`),
    ]).then(([images, videos, websites, requests, me]) => {
      setCounts({
        images: Array.isArray(images) ? images.length : 0,
        videos: Array.isArray(videos) ? videos.length : 0,
        websites: Array.isArray(websites) ? websites.length : 0,
        apps: 0, // placeholder until /api/apps exists
        orders: Array.isArray(requests) ? requests.length : 0,
      });
      if (me && me.id && setUser) setUser(me);
    });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const go = (path) => () => navigate(path);

  const Section = ({ title, subtitle, items, testid }) => (
    <section className="mb-10" data-testid={testid}>
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">{title}</h2>
          <p className="text-sm text-gray-400 mt-0.5">{subtitle}</p>
        </div>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {items.map((item) => {
          const Icon = item.icon;
          const count = item.countKey ? counts[item.countKey] : null;
          return (
            <div
              key={item.path}
              role="button"
              tabIndex={0}
              onClick={go(item.path)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(item.path); } }}
              className="quick-action-card relative rounded-2xl overflow-hidden aspect-[5/4] border border-white/10 cursor-pointer"
              data-testid={`vault-${item.path.split('/').pop()}`}
            >
              {/* Background photo */}
              <div
                className="absolute inset-0 bg-cover bg-center"
                style={{ backgroundImage: `url('${item.bgImage}')`, transform: 'scale(1.06)' }}
              />
              {/* Color tint */}
              <div className={`absolute inset-0 bg-gradient-to-tr ${item.gradient}`} />
              {/* Bottom darkening */}
              <div className="absolute inset-0 bg-gradient-to-t from-black via-black/75 to-black/10" />

              {/* Top-left: counter pill (only for vaults) */}
              {count !== null && (
                <div
                  className="absolute top-3 left-3 z-10 px-2.5 py-1 rounded-full bg-black/55 backdrop-blur-md border text-[11px] font-black"
                  style={{ borderColor: `${item.accent}50`, color: item.accent }}
                >
                  {count}
                </div>
              )}

              {/* Top-right: accent dot */}
              <div
                className="absolute top-3 right-3 w-2 h-2 rounded-full"
                style={{ background: item.accent, boxShadow: `0 0 12px ${item.accent}` }}
              />

              {/* Icon (centered top) */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[140%] z-10">
                <div
                  className="w-14 h-14 rounded-2xl bg-black/45 backdrop-blur-md border border-white/20 flex items-center justify-center"
                  style={{ boxShadow: `0 8px 24px ${item.accent}50` }}
                >
                  <Icon className="w-7 h-7" style={{ color: item.accent }} />
                </div>
              </div>

              {/* Text bottom */}
              <div className="relative h-full flex flex-col justify-end p-3 sm:p-4 text-right">
                <h3 className="text-white font-black text-sm sm:text-base mb-0.5" style={{ textShadow: '0 2px 8px rgba(0,0,0,.6)' }}>
                  {item.title}
                </h3>
                <p className="text-[10px] sm:text-xs text-white/80 font-medium leading-relaxed">{item.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a14] via-[#0a0a18] to-[#0a0a12]" data-testid="client-dashboard">
      <Navbar user={user} setUser={setUser} transparent />

      <div className="container mx-auto px-4 md:px-8 max-w-7xl pt-24 pb-12">
        <div className="mb-6">
          <BackButton to="/" label="الصفحة الرئيسية" />
        </div>

        {/* Header */}
        <div className="mb-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-black text-white mb-1" data-testid="dashboard-title">
              مرحباً، {user?.name || 'عميل Zerax'}
              {user?.is_owner && <Crown className="w-7 h-7 inline ms-2 text-amber-400" />}
            </h1>
            <p className="text-gray-400 text-sm">مكتبتك الخاصة · وصول من أي جهاز · شارك بسهولة</p>
          </div>
          <button
            type="button"
            onClick={go('/pricing')}
            className="navbar-btn-primary inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-black text-black"
            data-testid="buy-credits-btn"
          >
            <Coins className="w-4 h-4" />
            شراء نقاط
          </button>
        </div>

        {/* Top Stats Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
          <div className="rounded-xl bg-gradient-to-br from-amber-500/15 to-yellow-700/5 border border-amber-500/25 p-4">
            <div className="flex items-center justify-between mb-1">
              <Coins className="w-6 h-6 text-amber-400" />
              <span className="text-2xl font-black text-white">{user?.credits || 0}</span>
            </div>
            <p className="text-xs text-amber-200/70 font-medium">رصيد النقاط</p>
          </div>
          <div className="rounded-xl bg-gradient-to-br from-emerald-500/15 to-green-700/5 border border-emerald-500/25 p-4">
            <div className="flex items-center justify-between mb-1">
              <TrendingUp className="w-6 h-6 text-emerald-400" />
              <span className="text-2xl font-black text-white">{counts.images + counts.videos}</span>
            </div>
            <p className="text-xs text-emerald-200/70 font-medium">ملف منشأ</p>
          </div>
          <div className="rounded-xl bg-gradient-to-br from-blue-500/15 to-cyan-700/5 border border-blue-500/25 p-4">
            <div className="flex items-center justify-between mb-1">
              <FileText className="w-6 h-6 text-blue-400" />
              <span className="text-2xl font-black text-white">{counts.orders}</span>
            </div>
            <p className="text-xs text-blue-200/70 font-medium">طلب نشط</p>
          </div>
          <div className="rounded-xl bg-gradient-to-br from-purple-500/15 to-violet-700/5 border border-purple-500/25 p-4">
            <p className="text-xs text-purple-200/70 font-medium mb-1">الاشتراك</p>
            <p className="text-base font-black text-white truncate">
              {user?.is_owner ? 'مالك' :
                user?.subscription_type === 'images' ? 'باقة الصور' :
                user?.subscription_type === 'videos' ? 'باقة الفيديو' : 'بدون اشتراك'}
            </p>
          </div>
        </div>

        {/* Free Trials Banner — only if user has trials remaining */}
        {(user?.free_images > 0 || user?.free_videos > 0 || user?.free_website_trial) && (
          <div className="rounded-2xl bg-gradient-to-r from-green-500/15 to-emerald-500/10 border border-green-500/25 p-5 mb-10">
            <div className="flex items-center gap-3 mb-3">
              <Gift className="w-7 h-7 text-green-400" />
              <div>
                <h3 className="text-base font-black text-white">تجاربك المجانية</h3>
                <p className="text-green-400/70 text-xs">جرّب قبل الاشتراك</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="p-2.5 bg-black/30 rounded-lg text-center">
                <p className="text-lg font-black text-white">{user?.free_images || 0}</p>
                <p className="text-[10px] text-gray-400">صور</p>
              </div>
              <div className="p-2.5 bg-black/30 rounded-lg text-center">
                <p className="text-lg font-black text-white">{user?.free_videos || 0}</p>
                <p className="text-[10px] text-gray-400">فيديو</p>
              </div>
              <div className="p-2.5 bg-black/30 rounded-lg text-center">
                <p className="text-lg font-black text-white">{user?.free_website_trial ? '1' : '0'}</p>
                <p className="text-[10px] text-gray-400">موقع</p>
              </div>
            </div>
          </div>
        )}

        {/* Section 1: My Vaults — user's content storage */}
        <Section
          title="مكتبتي"
          subtitle="كل ما أنشأته في مكان واحد · وصول من أي جهاز"
          items={VAULTS}
          testid="section-vaults"
        />

        {/* Section 2: Sharing & Distribution */}
        <Section
          title="النشر والمشاركة"
          subtitle="انشر إنتاجك مباشرة على منصاتك المفضلة"
          items={SHARING}
          testid="section-sharing"
        />

        {/* Section 3: Account & Billing */}
        <Section
          title="حسابي"
          subtitle="إدارة اشتراكك · فواتيرك · حسابك الشخصي"
          items={ACCOUNT}
          testid="section-account"
        />

        {/* Footer hint */}
        <div className="mt-6 p-4 rounded-xl bg-slate-800/40 border border-slate-700/50 text-center">
          <p className="text-sm text-gray-400">
            تبي تنشئ شي جديد؟{' '}
            <button
              type="button"
              onClick={go('/')}
              className="text-amber-400 underline-offset-4 hover:underline font-semibold"
              data-testid="back-to-create"
            >
              ارجع للصفحة الرئيسية واختر أداة الإنشاء
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default ClientDashboard;
