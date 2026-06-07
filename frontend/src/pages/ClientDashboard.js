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
  { title: '🎨 استوديو الصور', desc: 'صور احترافية بسيناريو عميق + شات تفاعلي', icon: Image, path: '/studio/image', color: 'from-purple-500 to-violet-600', badge: 'نقاط' },
  { title: '🎬 استوديو الفيديو', desc: 'Sora 2 + سيناريو + ستوري بورد + رفع صوتك', icon: Clapperboard, path: '/studio/video', color: 'from-orange-500 to-red-500', badge: 'نقاط' },
  { title: '📱 إنشاء التطبيقات', desc: 'ألعاب وأدوات بمحادثة AI + معاينة iPhone حية', icon: Smartphone, path: '/dashboard/apps', color: 'from-cyan-500 to-blue-600', badge: '⚡ AI' },
  { title: '🎮 استوديو الألعاب', desc: 'ألعاب HTML5 + تطبيقات 3D للموبايل والـPC', icon: Gamepad2, path: '/dashboard/games', color: 'from-violet-500 to-purple-600', badge: '🔥 جديد' },
  { title: '🎬 استوديو السينما', desc: 'أفلام + إعلانات + موسيقى + حلقات طويلة', icon: Clapperboard, path: '/dashboard/cinema', color: 'from-rose-500 to-amber-600', badge: '⭐ جديد' },
  { title: '🌐 طلب موقع جديد', desc: 'أنشئ موقعك بالذكاء الاصطناعي', icon: PlusCircle, path: '/dashboard/new-request', color: 'from-blue-500 to-cyan-500' },
  { title: '📱 رفيقتي على الجوال', desc: 'Zara/Layla كمساعدة شخصية يومية', icon: Bot, path: '/companion', color: 'from-fuchsia-500 to-pink-600', badge: 'جديد' },
  { title: '🤖 مساعدتي الذكية', desc: 'فعّل مساعدة AI لمتجرك', icon: Bot, path: '/dashboard/avatar', color: 'from-emerald-500 to-green-600', badge: '14 يوم مجاناً' },
  { title: '🌉 Channel Bridge', desc: 'انشر أصولك في متاجرك', icon: Share2, path: '/dashboard/bridge', color: 'from-sky-500 to-cyan-500' },
  { title: '📄 طلباتي', desc: 'عرض وإدارة طلباتك', icon: FileText, path: '/dashboard/requests', color: 'from-green-500 to-emerald-500' },
  { title: '🌍 مواقعي', desc: 'عرض المواقع المنجزة', icon: Globe, path: '/dashboard/websites', color: 'from-indigo-500 to-purple-500' },
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

        {/* Quick Actions Grid — clean, performant, mobile-first */}
        <Card className="bg-slate-800/80 border-slate-700">
          <CardHeader className="pb-4">
            <CardTitle className="text-white text-lg">الإجراءات السريعة</CardTitle>
            <CardDescription className="text-gray-400 text-sm">اختر ما تريد فعله</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {QUICK_ACTIONS.map((action, idx) => {
                const Icon = action.icon;
                return (
                  <div
                    key={action.path}
                    role="button"
                    tabIndex={0}
                    onClick={go(action.path)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(action.path); } }}
                    className="quick-action-card p-5 rounded-xl bg-slate-700/40 border border-slate-600/60 cursor-pointer text-right"
                    data-testid={`action-${idx}`}
                  >
                    {action.badge && (
                      <span className="absolute top-3 left-3 text-[10px] bg-green-500 text-white px-2 py-0.5 rounded-full font-medium">
                        {action.badge}
                      </span>
                    )}
                    <div className={`w-11 h-11 rounded-lg bg-gradient-to-br ${action.color} flex items-center justify-center text-white mb-3`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <h3 className="text-base font-semibold text-white mb-1">{action.title}</h3>
                    <p className="text-xs text-gray-400 leading-relaxed">{action.desc}</p>
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
