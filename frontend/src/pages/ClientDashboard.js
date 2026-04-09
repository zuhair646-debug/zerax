import React from 'react';
import { Navbar } from '@/components/Navbar';
import { Card, CardContent } from '@/components/ui/card';
import { useNavigate } from 'react-router-dom';
import { Coins, Crown, Gift, Image, Video, Globe, MessageSquare } from 'lucide-react';

const ClientDashboard = ({ user }) => {
  const navigate = useNavigate();

  const quickActions = [
    { title: 'الشات الذكي', desc: 'تحدث مع الذكاء الاصطناعي', icon: <MessageSquare className="w-6 h-6" />, path: '/chat', color: 'from-purple-500 to-pink-500' },
    { title: 'توليد الصور', desc: 'أنشئ صوراً إبداعية', icon: <Image className="w-6 h-6" />, path: '/chat', color: 'from-blue-500 to-cyan-500' },
    { title: 'إنشاء الفيديو', desc: 'فيديوهات بتقنية AI', icon: <Video className="w-6 h-6" />, path: '/chat', color: 'from-orange-500 to-red-500' },
    { title: 'بناء المواقع', desc: 'مواقع احترافية', icon: <Globe className="w-6 h-6" />, path: '/chat', color: 'from-green-500 to-emerald-500' },
  ];

  return (
    <div className="min-h-screen bg-slate-900">
      <Navbar user={user} transparent />
      <div className="container mx-auto px-4 md:px-8 max-w-7xl pt-24 pb-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            مرحباً، {user?.name || 'مستخدم'}
            {user?.is_owner && <Crown className="w-6 h-6 inline ms-2 text-yellow-400" />}
          </h1>
          <p className="text-gray-400">إليك نظرة سريعة على حسابك</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6 text-center">
              <Coins className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
              <span className="text-3xl font-bold text-white block">{user?.credits || 0}</span>
              <p className="text-sm text-gray-400">رصيد النقاط</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6 text-center">
              <Image className="w-8 h-8 text-purple-400 mx-auto mb-2" />
              <span className="text-3xl font-bold text-white block">{user?.free_images || 0}</span>
              <p className="text-sm text-gray-400">صور مجانية</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6 text-center">
              <Video className="w-8 h-8 text-orange-400 mx-auto mb-2" />
              <span className="text-3xl font-bold text-white block">{user?.free_videos || 0}</span>
              <p className="text-sm text-gray-400">فيديوهات مجانية</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6 text-center">
              <Gift className="w-8 h-8 text-green-400 mx-auto mb-2" />
              <span className="text-3xl font-bold text-white block">{user?.bonus_points || 0}</span>
              <p className="text-sm text-gray-400">نقاط المكافآت</p>
            </CardContent>
          </Card>
        </div>

        <h2 className="text-xl font-semibold text-white mb-4">إجراءات سريعة</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((action, index) => (
            <Card key={index} className="bg-slate-800 border-slate-700 hover:border-purple-500 transition-all cursor-pointer"
              onClick={() => navigate(action.path)}>
              <CardContent className="p-6 text-center">
                <div className={`p-4 rounded-full bg-gradient-to-r ${action.color} text-white w-fit mx-auto mb-4`}>
                  {action.icon}
                </div>
                <h3 className="font-semibold text-white mb-1">{action.title}</h3>
                <p className="text-sm text-gray-400">{action.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ClientDashboard;
