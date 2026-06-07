import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useNavigate } from 'react-router-dom';
import {
  PlusCircle, FileText, Globe, Image, Video, Coins, Crown, Gift,
  Sparkles, Bot, Share2, Clapperboard, Smartphone, Gamepad2,
} from 'lucide-react';
import SiteBannerStories from '@/components/SiteBannerStories';
import { BackButton } from '@/components/BackButton';

const QUICK_ACTIONS = [
  { title: 'استوديو الصور', desc: 'صور احترافية بسيناريو عميق + شات تفاعلي', icon: Image, path: '/studio/image', accent: '#a78bfa', gradient: 'from-purple-500/30 to-violet-500/10', bgImage: 'https://images.unsplash.com/photo-1542038784456-1ea8e935640e?auto=format&fit=crop&w=800&q=70', badge: 'نقاط' },
  { title: 'استوديو الفيديو', desc: 'Sora 2 + سيناريو + ستوري بورد + رفع صوتك', icon: Clapperboard, path: '/studio/video', accent: '#fb923c', gradient: 'from-orange-500/30 to-red-500/10', bgImage: 'https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=800&q=70', badge: 'نقاط' },
  { title: 'إنشاء التطبيقات', desc: 'ألعاب وأدوات بمحادثة AI + معاينة iPhone حية', icon: Smartphone, path: '/dashboard/apps', accent: '#22d3ee', gradient: 'from-cyan-500/30 to-blue-500/10', bgImage: 'https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&w=800&q=70', badge: '⚡ AI' },
  { title: 'استوديو الألعاب', desc: 'ألعاب HTML5 + تطبيقات 3D للموبايل والـPC', icon: Gamepad2, path: '/dashboard/games', accent: '#a855f7', gradient: 'from-violet-500/30 to-purple-500/10', bgImage: 'https://images.unsplash.com/photo-1593305841991-05c297ba4575?auto=format&fit=crop&w=800&q=70', badge: '🔥 جديد' },
  { title: 'استوديو السينما', desc: 'أفلام + إعلانات + موسيقى + حلقات طويلة', icon: Clapperboard, path: '/dashboard/cinema', accent: '#f472b6', gradient: 'from-rose-500/30 to-amber-500/10', bgImage: 'https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=800&q=70', badge: '⭐ جديد' },
  { title: 'طلب موقع جديد', desc: 'أنشئ موقعك بالذكاء الاصطناعي', icon: PlusCircle, path: '/dashboard/new-request', accent: '#3b82f6', gradient: 'from-blue-500/30 to-cyan-500/10', bgImage: 'https://images.unsplash.com/photo-1467232004584-a241de8bcf5d?auto=format&fit=crop&w=800&q=70' },
  { title: 'رفيقتي على الجوال', desc: 'Zara/Layla كمساعدة شخصية يومية', icon: Bot, path: '/companion', accent: '#e879f9', gradient: 'from-fuchsia-500/30 to-pink-500/10', bgImage: 'https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=800&q=70', badge: 'جديد' },
  { title: 'مساعدتي الذكية', desc: 'فعّل مساعدة AI لمتجرك', icon: Bot, path: '/dashboard/avatar', accent: '#10b981', gradient: 'from-emerald-500/30 to-green-500/10', bgImage: 'https://images.unsplash.com/photo-1556761175-5973dc0f32e7?auto=format&fit=crop&w=800&q=70', badge: '14 يوم مجاناً' },
  { title: 'Channel Bridge', desc: 'انشر أصولك في متاجرك المتعددة', icon: Share2, path: '/dashboard/bridge', accent: '#0ea5e9', gradient: 'from-sky-500/30 to-cyan-500/10', bgImage: 'https://images.unsplash.com/photo-1557804506-669a67965ba0?auto=format&fit=crop&w=800&q=70' },
  { title: 'طلباتي', desc: 'عرض وإدارة طلباتك', icon: FileText, path: '/dashboard/requests', accent: '#22c55e', gradient: 'from-green-500/30 to-emerald-500/10', bgImage: 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=800&q=70' },
  { title: 'مواقعي', desc: 'عرض المواقع المنجزة', icon: Globe, path: '/dashboard/websites', accent: '#6366f1', gradient: 'from-indigo-500/30 to-purple-500/10', bgImage: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=800&q=70' },
];

const ClientDashboard = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({ requests: 0, websites: 0 });
  const fetchedRef = useRef(false);

  // Fetch stats EXACTLY ONCE on mount — never re-runs even if parent re-renders.
  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    const token = localStorage.getItem('token');
    if (!token) return;

    const controller = new AbortController();
    const headers = { Authorization: `Bearer ${token}` };
    const API = process.env.REACT_APP_BACKEND_URL;

    // Each fetch has its own 6s timeout; failures are silent.
    const safeFetch = (url) =>
      Promise.race([
        fetch(url, { headers, signal: controller.signal })
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null),
        new Promise((resolve) => setTimeout(() => resolve(null), 6000)),
      ]);

    Promise.all([
      safeFetch(`${API}/api/requests`),
      safeFetch(`${API}/api/websites`),
      safeFetch(`${API}/api/auth/me`),
    ]).then(([requests, websites, me]) => {
      setStats({
        requests: Array.isArray(requests) ? requests.length : 0,
        websites: Array.isArray(websites) ? websites.length : 0,
      });
      if (me && me.id && setUser) setUser(me);
    });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // ← EMPTY deps. Runs once. Never re-fires.

  const go = (path) => () => navigate(path);

  return (
    <div className="min-h-screen bg-slate-900" data-testid="client-dashboard">
      <Navbar user={user} setUser={setUser} transparent />

      {/* Banner stories above the content */}
      <div className="pt-16">
        <SiteBannerStories placement="inside" />
      </div>

      <div className="container mx-auto px-4 md:px-8 max-w-7xl pt-6 pb-12">
        <div className="mb-5">
          <BackButton to="/" label="الصفحة الرئيسية" />
        </div>

        {/* Header */}
        <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-1" data-testid="dashboard-title">
              مرحباً، {user?.name || 'مستخدم'}
              {user?.is_owner && <Crown className="w-6 h-6 inline ms-2 text-yellow-400" />}
            </h1>
            <p className="text-gray-400 text-sm">إليك نظرة سريعة على حسابك</p>
          </div>
          <Button
            onClick={go('/pricing')}
            variant="outline"
            className="border-amber-500/40 text-amber-400 hover:bg-amber-500/10 hover:text-amber-300 cursor-pointer"
            data-testid="buy-credits-btn"
          >
            <Coins className="w-4 h-4 me-2" />
            شراء نقاط
          </Button>
        </div>

        {/* Free Trials Banner — only if user has trials remaining */}
        {(user?.free_images > 0 || user?.free_videos > 0 || user?.free_website_trial) && (
          <Card className="bg-gradient-to-r from-green-500/15 to-emerald-500/15 border-green-500/30 mb-6">
            <CardContent className="p-6">
              <div className="flex items-center gap-4 mb-4">
                <Gift className="w-9 h-9 text-green-400" />
                <div>
                  <h3 className="text-lg font-semibold text-white">تجاربك المجانية</h3>
                  <p className="text-green-400/80 text-sm">جرّب خدماتنا مجاناً قبل الاشتراك</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-white/5 rounded-lg text-center">
                  <Image className="w-6 h-6 text-purple-400 mx-auto mb-1" />
                  <p className="text-xl font-bold text-white">{user?.free_images || 0}</p>
                  <p className="text-xs text-gray-400">صور</p>
                </div>
                <div className="p-3 bg-white/5 rounded-lg text-center">
                  <Video className="w-6 h-6 text-orange-400 mx-auto mb-1" />
                  <p className="text-xl font-bold text-white">{user?.free_videos || 0}</p>
                  <p className="text-xs text-gray-400">فيديوهات</p>
                </div>
                <div className="p-3 bg-white/5 rounded-lg text-center">
                  <Sparkles className="w-6 h-6 text-blue-400 mx-auto mb-1" />
                  <p className="text-xl font-bold text-white">{user?.free_website_trial ? '1' : '0'}</p>
                  <p className="text-xs text-gray-400">موقع</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-slate-800/80 border-slate-700">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-2">
                <Coins className="w-7 h-7 text-yellow-400" />
                <span className="text-2xl font-bold text-white">{user?.credits || 0}</span>
              </div>
              <p className="text-xs text-gray-400">رصيد النقاط</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-800/80 border-slate-700">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-2">
                <FileText className="w-7 h-7 text-blue-400" />
                <span className="text-2xl font-bold text-white">{stats.requests}</span>
              </div>
              <p className="text-xs text-gray-400">إجمالي الطلبات</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-800/80 border-slate-700">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-2">
                <Globe className="w-7 h-7 text-green-400" />
                <span className="text-2xl font-bold text-white">{stats.websites}</span>
              </div>
              <p className="text-xs text-gray-400">المواقع الجاهزة</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-800/80 border-slate-700">
            <CardContent className="p-5">
              <p className="text-xs text-gray-400 mb-1">الاشتراك الحالي</p>
              <p className="text-base font-semibold text-white truncate">
                {user?.is_owner ? 'مالك (مجاني)' :
                  user?.subscription_type === 'images' ? 'باقة الصور' :
                  user?.subscription_type === 'videos' ? 'باقة الفيديو' : 'لا يوجد'}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions Grid — vibrant cards with background images, matching landing page style */}
        <Card className="bg-slate-800/60 border-slate-700">
          <CardHeader className="pb-4">
            <CardTitle className="text-white text-lg">الإجراءات السريعة</CardTitle>
            <CardDescription className="text-gray-400 text-sm">اختر ما تريد فعله</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
              {QUICK_ACTIONS.map((action, idx) => {
                const Icon = action.icon;
                return (
                  <div
                    key={action.path}
                    role="button"
                    tabIndex={0}
                    onClick={go(action.path)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(action.path); } }}
                    className="quick-action-card relative rounded-xl overflow-hidden aspect-[4/3] sm:aspect-[5/4] border border-white/10 cursor-pointer text-right"
                    data-testid={`action-${idx}`}
                  >
                    {/* Background photo */}
                    <div
                      className="absolute inset-0 bg-cover bg-center"
                      style={{ backgroundImage: `url('${action.bgImage}')`, transform: 'scale(1.08)' }}
                    />
                    {/* Color tint */}
                    <div className={`absolute inset-0 bg-gradient-to-tr ${action.gradient}`} />
                    {/* Dark gradient bottom for text readability */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black via-black/70 to-black/10" />

                    {/* Accent dot top-left */}
                    <div
                      className="absolute top-2 right-2 w-2 h-2 rounded-full"
                      style={{ background: action.accent, boxShadow: `0 0 10px ${action.accent}` }}
                    />

                    {/* Badge */}
                    {action.badge && (
                      <div className="absolute top-2 left-2 z-10 px-2 py-0.5 rounded-md bg-gradient-to-r from-amber-400 to-yellow-500 text-black text-[10px] font-black tracking-wider">
                        {action.badge}
                      </div>
                    )}

                    {/* Icon mid-top */}
                    <div className="absolute top-3 right-1/2 translate-x-1/2 sm:top-4 sm:right-auto sm:left-3 sm:translate-x-0 z-10">
                      <div
                        className="w-10 h-10 rounded-lg bg-black/40 backdrop-blur-md border border-white/15 flex items-center justify-center"
                        style={{ boxShadow: `0 0 14px ${action.accent}40` }}
                      >
                        <Icon className="w-5 h-5" style={{ color: action.accent }} />
                      </div>
                    </div>

                    {/* Text bottom */}
                    <div className="relative h-full flex flex-col justify-end p-3 sm:p-4">
                      <h3 className="text-white font-black text-sm sm:text-base mb-0.5" style={{ textShadow: '0 2px 8px rgba(0,0,0,.5)' }}>
                        {action.title}
                      </h3>
                      <p className="text-[10px] sm:text-xs text-white/80 font-medium leading-relaxed">{action.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ClientDashboard;
