import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useNavigate } from 'react-router-dom';
import { PlusCircle, FileText, Globe, Image, Video, Coins, Crown, Gift, Sparkles } from 'lucide-react';

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
        const backendUrl = process.env.REACT_APP_BACKEND_URL;
        
        const [requestsRes, websitesRes, userRes] = await Promise.all([
          fetch(`${backendUrl}/api/requests`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch(`${backendUrl}/api/websites`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch(`${backendUrl}/api/auth/me`, {
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
      } finally {
        setLoading(false);
      }
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
      
      <div className="container mx-auto px-4 md:px-8 max-w-7xl pt-24 pb-12">
        <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2" data-testid="dashboard-title">
              مرحباً، {user?.name || 'مستخدم'}
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
          <div className="text-center py-12 text-white">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
            جاري التحميل...
          </div>
        ) : (
          <>
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
                  <p className="text-sm text-gray-400">المواقع المنجزة</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <PlusCircle className="w-8 h-8 text-purple-400" />
                    <span className="text-3xl font-bold text-white">{stats.pending}</span>
                  </div>
                  <p className="text-sm text-gray-400">قيد التنفيذ</p>
                </CardContent>
              </Card>
            </div>

            <h2 className="text-xl font-semibold text-white mb-4">إجراءات سريعة</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {quickActions.map((action, index) => (
                <Card
                  key={index}
                  className="bg-slate-800 border-slate-700 hover:border-slate-500 transition-all cursor-pointer group"
                  onClick={() => navigate(action.path)}
                >
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4">
                      <div className={`p-3 rounded-lg bg-gradient-to-r ${action.color} text-white`}>
                        {action.icon}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-white group-hover:text-cyan-400 transition-colors">
                            {action.title}
                          </h3>
                          {action.badge && (
                            <span className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded-full">
                              {action.badge}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-400 mt-1">{action.desc}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ClientDashboard;
