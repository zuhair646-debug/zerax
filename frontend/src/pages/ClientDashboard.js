import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useNavigate } from 'react-router-dom';
import { PlusCircle, FileText, Globe, Image, Video, Coins, Crown, Gift, Sparkles } from 'lucide-react';
import SiteBannerStories from '@/components/SiteBannerStories';

const ClientDashboard = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({ requests: 0, pending: 0, completed: 0, websites: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setLoading(false);
        return;
      }
      
      try {
        const [requestsRes, websitesRes, userRes] = await Promise.all([
          fetch(`${process.env.REACT_APP_BACKEND_URL}/api/requests`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch(`${process.env.REACT_APP_BACKEND_URL}/api/websites`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ]);

        const requests = requestsRes.ok ? await requestsRes.json() : [];
        const websites = websitesRes.ok ? await websitesRes.json() : [];
        const userData = userRes.ok ? await userRes.json() : null;
        
        if (userData && userData.id) {
          setUser(userData);
        }

        setStats({
          requests: Array.isArray(requests) ? requests.length : 0,
          pending: Array.isArray(requests) ? requests.filter(r => r.status === 'pending').length : 0,
          completed: Array.isArray(requests) ? requests.filter(r => r.status === 'completed').length : 0,
          websites: Array.isArray(websites) ? websites.length : 0
        });
      } catch (error) {
        console.error('Error fetching stats:', error);
      }
      setLoading(false);
    };

    fetchStats();
  }, [setUser]);

  const quickActions = [
    { title: 'طلب موقع جديد', desc: 'أنشئ موقعك بالذكاء الاصطناعي', icon: <PlusCircle className="w-6 h-6" />, path: '/dashboard/new-request', color: 'from-blue-500 to-cyan-500' },
    { title: 'توليد الصور', desc: user?.free_images > 0 ? `${user.free_images} صور مجانية` : 'أنشئ صوراً إبداعية', icon: <Image className="w-6 h-6" />, path: '/dashboard/images', color: 'from-purple-500 to-pink-500', badge: user?.free_images > 0 ? 'مجاني' : null },
    { title: 'إنشاء الفيديو', desc: user?.free_videos > 0 ? `${user.free_videos} فيديوهات مجانية` : 'فيديوهات بتقنية AI', icon: <Video className="w-6 h-6" />, path: '/dashboard/videos', color: 'from-orange-500 to-red-500', badge: user?.free_videos > 0 ? 'مجاني' : null },
    { title: 'طلباتي', desc: 'عرض وإدارة طلباتك', icon: <FileText className="w-6 h-6" />, path: '/dashboard/requests', color: 'from-green-500 to-emerald-500' },
    { title: 'مواقعي', desc: 'عرض المواقع المنجزة', icon: <Globe className="w-6 h-6" />, path: '/dashboard/websites', color: 'from-indigo-500 to-purple-500' },
  ];

  return (
    <div className="min-h-screen bg-slate-900" data-testid="client-dashboard">
      <Navbar user={user} transparent />

      {/* Rotating banner + stories above the dashboard sections */}
      <div className="pt-16">
        <SiteBannerStories placement="inside" />
      </div>

      <div className="container mx-auto px-4 md:px-8 max-w-7xl pt-8 pb-12">
        <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2" data-testid="dashboard-title">
              مرحباً، {user?.name}
              {user?.is_owner && <Crown className="w-6 h-6 inline ms-2 text-yellow-400" />}
            </h1>
            <p className="text-gray-400">إليك نظرة سريعة على حسابك</p>
          </div>
          <Button onClick={() => navigate('/pricing')} variant="outline" className="border-slate-600 text-white">
            <Coins className="w-4 h-4 me-2" />
            شراء نقاط
          </Button>
        </div>

        {loading ? (
          <div className="text-center py-12 text-white">جاري التحميل...</div>
        ) : (
          <>
            {/* Free Trials Banner */}
            {(user?.free_images > 0 || user?.free_videos > 0 || user?.free_website_trial) && (
              <Card className="bg-gradient-to-r from-green-500/20 to-emerald-500/20 border-green-500/30 mb-8">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4 mb-4">
                    <Gift className="w-10 h-10 text-green-400" />
                    <div>
                      <h3 className="text-xl font-semibold text-white">تجاربك المجانية</h3>
                      <p className="text-green-400/70">جرّب خدماتنا مجاناً قبل الاشتراك!</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 bg-white/5 rounded-lg text-center">
                      <Image className="w-8 h-8 text-purple-400 mx-auto mb-2" />
                      <p className="text-2xl font-bold text-white">{user?.free_images || 0}</p>
                      <p className="text-sm text-gray-400">صور مجانية</p>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg text-center">
                      <Video className="w-8 h-8 text-orange-400 mx-auto mb-2" />
                      <p className="text-2xl font-bold text-white">{user?.free_videos || 0}</p>
                      <p className="text-sm text-gray-400">فيديوهات مجانية</p>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg text-center">
                      <Sparkles className="w-8 h-8 text-blue-400 mx-auto mb-2" />
                      <p className="text-2xl font-bold text-white">{user?.free_website_trial ? '1' : '0'}</p>
                      <p className="text-sm text-gray-400">تجربة موقع</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <Coins className="w-8 h-8 text-yellow-400" />
                    <span className="text-3xl font-bold text-white">{user?.credits || 0}</span>
                  </div>
                  <p className="text-sm text-gray-400">رصيد النقاط</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <FileText className="w-8 h-8 text-blue-400" />
                    <span className="text-3xl font-bold text-white">{stats.requests}</span>
                  </div>
                  <p className="text-sm text-gray-400">إجمالي الطلبات</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <Globe className="w-8 h-8 text-green-400" />
                    <span className="text-3xl font-bold text-white">{stats.websites}</span>
                  </div>
                  <p className="text-sm text-gray-400">المواقع الجاهزة</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-6">
                  <p className="text-sm text-gray-400 mb-1">الاشتراك الحالي</p>
                  <p className="text-lg font-semibold text-white">
                    {user?.is_owner ? 'مالك (مجاني)' : 
                     user?.subscription_type === 'images' ? 'باقة الصور' :
                     user?.subscription_type === 'videos' ? 'باقة الفيديو' : 'لا يوجد'}
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Quick Actions */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">الإجراءات السريعة</CardTitle>
                <CardDescription className="text-gray-400">اختر ما تريد فعله</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {quickActions.map((action, idx) => (
                    <button
                      key={idx}
                      onClick={() => navigate(action.path)}
                      className="p-6 rounded-xl bg-slate-700/50 hover:bg-slate-700 transition-all text-right group border border-slate-600 hover:border-slate-500 relative"
                      data-testid={`action-${idx}`}
                    >
                      {action.badge && (
                        <span className="absolute top-3 left-3 text-xs bg-green-500 text-white px-2 py-1 rounded-full">
                          {action.badge}
                        </span>
                      )}
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${action.color} flex items-center justify-center text-white mb-4 group-hover:scale-110 transition-transform`}>
                        {action.icon}
                      </div>
                      <h3 className="text-lg font-semibold text-white mb-2">{action.title}</h3>
                      <p className="text-sm text-gray-400">{action.desc}</p>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
};

export default ClientDashboard;
