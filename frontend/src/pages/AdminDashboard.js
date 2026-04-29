import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { Users, FileText, CreditCard, Globe, Image, Video, Settings, Clock, CheckCircle, Activity, Coins, Brain } from 'lucide-react';

const AdminDashboard = ({ user }) => {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/stats`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        setStats(data);
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  const statCards = stats ? [
    { title: 'إجمالي العملاء', value: stats.total_users, icon: <Users className="w-8 h-8" />, color: 'from-blue-500 to-cyan-500' },
    { title: 'إجمالي الطلبات', value: stats.total_requests, icon: <FileText className="w-8 h-8" />, color: 'from-green-500 to-emerald-500' },
    { title: 'طلبات قيد الانتظار', value: stats.pending_requests, icon: <Clock className="w-8 h-8" />, color: 'from-yellow-500 to-orange-500' },
    { title: 'مدفوعات معلقة', value: stats.pending_payments, icon: <CreditCard className="w-8 h-8" />, color: 'from-red-500 to-pink-500' },
    { title: 'صور تم توليدها', value: stats.total_images_generated, icon: <Image className="w-8 h-8" />, color: 'from-purple-500 to-pink-500' },
    { title: 'فيديوهات تم توليدها', value: stats.total_videos_generated, icon: <Video className="w-8 h-8" />, color: 'from-orange-500 to-red-500' },
    { title: 'إجمالي الأنشطة', value: stats.total_activities, icon: <Activity className="w-8 h-8" />, color: 'from-cyan-500 to-blue-500' },
  ] : [];

  const quickActions = [
    { title: 'إدارة الطلبات', desc: 'عرض ومراجعة جميع الطلبات', path: '/admin/requests', icon: <FileText className="w-6 h-6" />, color: 'from-blue-500 to-cyan-500' },
    { title: 'إدارة المدفوعات', desc: 'مراجعة والموافقة على المدفوعات', path: '/admin/payments', icon: <CreditCard className="w-6 h-6" />, color: 'from-green-500 to-emerald-500' },
    { title: 'إدارة العملاء', desc: 'عرض وإدارة قائمة العملاء', path: '/admin/clients', icon: <Users className="w-6 h-6" />, color: 'from-purple-500 to-pink-500' },
    { title: 'النقاط والعروض', desc: 'إدارة النقاط والأسعار والعروض', path: '/admin/credits', icon: <Coins className="w-6 h-6" />, color: 'from-amber-500 to-yellow-500' },
    { title: 'تدريب الذكاء', desc: 'تعليم الذكاء الاصطناعي أمثلة احترافية', path: '/admin/training', icon: <Brain className="w-6 h-6" />, color: 'from-purple-500 to-pink-500' },
    { title: 'إدارة المواقع', desc: 'إضافة وتحديث المواقع', path: '/admin/websites', icon: <Globe className="w-6 h-6" />, color: 'from-orange-500 to-red-500' },
    { title: 'سجل النشاط', desc: 'تتبع جميع الأنشطة على المنصة', path: '/admin/activity', icon: <Activity className="w-6 h-6" />, color: 'from-cyan-500 to-blue-500' },
    { title: 'الإعدادات', desc: 'إعدادات الموقع ومعلومات الدفع', path: '/admin/settings', icon: <Settings className="w-6 h-6" />, color: 'from-gray-500 to-slate-600' },
  ];

  return (
    <div className="min-h-screen bg-slate-900" data-testid="admin-dashboard">
      <Navbar user={user} transparent />
      
      <div className="container mx-auto px-4 md:px-8 max-w-7xl pt-24 pb-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2" data-testid="dashboard-title">
            لوحة تحكم الأدمن
          </h1>
          <p className="text-gray-400">نظرة شاملة على المنصة</p>
        </div>

        {loading ? (
          <div className="text-center py-12 text-white">جاري التحميل...</div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
              {statCards.map((stat, idx) => (
                <Card key={idx} className="bg-slate-800 border-slate-700" data-testid={`stat-card-${idx}`}>
                  <CardContent className="p-4 text-center">
                    <div className={`w-12 h-12 mx-auto mb-3 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center text-white`}>
                      {stat.icon}
                    </div>
                    <span className="text-2xl font-bold text-white block">{stat.value}</span>
                    <p className="text-xs text-gray-400 mt-1">{stat.title}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="p-6">
                <h2 className="text-xl font-semibold text-white mb-4">الإجراءات السريعة</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {quickActions.map((action, idx) => (
                    <button
                      key={idx}
                      onClick={() => navigate(action.path)}
                      className="p-6 rounded-xl bg-slate-700/50 hover:bg-slate-700 transition-all text-right group border border-slate-600 hover:border-slate-500"
                    >
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

export default AdminDashboard;
