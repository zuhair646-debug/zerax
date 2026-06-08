import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { Users, FileText, CreditCard, Globe, Image, Video, Settings, Clock, CheckCircle, Activity, Coins, Brain, Code2, ShieldCheck, Sparkles, ShieldAlert, DollarSign } from 'lucide-react';

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
    { title: 'مركز ذكاء العملاء 🧠', desc: 'تقرير 360° لكل عميل + اقتراح حملات إعلانية مستهدفة بالذكاء الاصطناعي', path: '/admin/intelligence', icon: <Sparkles className="w-6 h-6" />, color: 'from-amber-500 to-orange-600', testId: 'admin-tile-intelligence' },
    { title: 'مركز المسوّقين 📈', desc: 'تتبع نقرات وإحصائيات كل مسوّق + مدى تأثيره الحقيقي وأفضل منشوراته', path: '/admin/affiliates', icon: <Sparkles className="w-6 h-6" />, color: 'from-pink-500 to-purple-600', testId: 'admin-tile-affiliates' },
    { title: 'النقاط والعروض', desc: 'إدارة النقاط والأسعار والعروض', path: '/admin/credits', icon: <Coins className="w-6 h-6" />, color: 'from-amber-500 to-yellow-500' },
    { title: 'تدريب الذكاء', desc: 'تعليم الذكاء الاصطناعي أمثلة احترافية', path: '/admin/training', icon: <Brain className="w-6 h-6" />, color: 'from-purple-500 to-pink-500' },
    { title: 'غرفة التحكم الأمنية 🛡️', desc: 'حماية 10 طبقات · فحص AI مستمر · IPs محظورة · نسخ احتياطي · سجل أحداث', path: '/admin/security', icon: <ShieldAlert className="w-6 h-6" />, color: 'from-red-500 to-rose-600', testId: 'admin-tile-security' },
    { title: 'برمجة زيتاكس 🔐', desc: 'ذكاء يعدّل كود المنصة بنفسه (للمالك فقط)', path: '/admin/autocoder', icon: <Code2 className="w-6 h-6" />, color: 'from-amber-500 to-orange-600', testId: 'admin-tile-autocoder' },
    { title: 'مركز التسويق الذكي 📣', desc: 'ذكاء يولّد، يجدول، وينشر تلقائياً عبر 6 منصات (Telegram/Twitter/IG/...)', path: '/admin/marketing', icon: <Sparkles className="w-6 h-6" />, color: 'from-pink-500 to-amber-500', testId: 'admin-tile-marketing' },
    { title: 'الاستقلالية والمفاتيح 🔓', desc: 'كل API keys مع روابط مباشرة للحصول عليها', path: '/admin/independence', icon: <ShieldCheck className="w-6 h-6" />, color: 'from-emerald-500 to-teal-600', testId: 'admin-tile-independence' },
    { title: 'نمو الذكاء 🧠', desc: 'الدروس اللي يتعلمها الذكاء يومياً من تفاعلاتك', path: '/admin/learning', icon: <Sparkles className="w-6 h-6" />, color: 'from-pink-500 to-rose-600', testId: 'admin-tile-learning' },
    { title: 'جاهزية الذكاء 🚀', desc: 'حالة نماذج AI والتكاملات الناقصة وروابط الارتقاء', path: '/admin/ai-readiness', icon: <Brain className="w-6 h-6" />, color: 'from-violet-500 to-amber-500', testId: 'admin-tile-ai-readiness' },
    { title: 'إدارة المواقع', desc: 'إضافة وتحديث المواقع', path: '/admin/websites', icon: <Globe className="w-6 h-6" />, color: 'from-orange-500 to-red-500' },
    { title: 'سجل النشاط', desc: 'تتبع جميع الأنشطة على المنصة', path: '/admin/activity', icon: <Activity className="w-6 h-6" />, color: 'from-cyan-500 to-blue-500' },
    { title: 'الإعدادات', desc: 'إعدادات الموقع ومعلومات الدفع', path: '/admin/settings', icon: <Settings className="w-6 h-6" />, color: 'from-gray-500 to-slate-600' },
  ];

  const aiCommandCards = [
    {
      title: 'برمجة زيتاكس',
      desc: 'اطلب مني أبني/أصلح/أختبر وأنشر، مع خطوات واضحة وخلاصة مربعة في النهاية.',
      path: '/admin/autocoder',
      icon: <Code2 className="w-5 h-5" />,
      badge: 'تنفيذ مباشر',
      testId: 'admin-ai-command-autocoder',
    },
    {
      title: 'جاهزية الذكاء',
      desc: 'شوف نماذج AI، التكاملات الناقصة، روابط المفاتيح، وأولويات ترقية Zitex.',
      path: '/admin/ai-readiness',
      icon: <Brain className="w-5 h-5" />,
      badge: 'تقرير شامل',
      testId: 'admin-ai-command-readiness',
    },
    {
      title: 'الاستقلالية والمفاتيح',
      desc: 'روابط الخدمات المطلوبة مثل Sentry وR2 وOpenRouter وFal وStripe.',
      path: '/admin/independence',
      icon: <ShieldCheck className="w-5 h-5" />,
      badge: 'مفاتيح ناقصة',
      testId: 'admin-ai-command-keys',
    },
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

        <div data-testid="admin-ai-command-center" className="mb-8 overflow-hidden rounded-3xl border border-amber-400/20 bg-gradient-to-br from-amber-500/15 via-slate-800 to-slate-950 p-6 shadow-2xl shadow-amber-500/10">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-2xl">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-200">
                <CheckCircle className="h-4 w-4" /> مركز الذكاء مفعّل
              </div>
              <h2 className="text-2xl font-black text-white md:text-3xl">إذا ما شفت التغيير: ابدأ من هنا</h2>
              <p className="mt-3 text-sm leading-7 text-slate-300">
                رتّبت لك مدخل واضح لكل ما يخص ذكاء Zitex: اطلب تنفيذ مهام من برمجة زيتاكس، راقب جاهزية الذكاء، وشوف المفاتيح والخدمات الناقصة بروابط مباشرة.
              </p>
            </div>
            <div className="grid min-w-[280px] grid-cols-2 gap-3 text-center">
              <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                <div className="text-2xl font-black text-amber-300">4</div>
                <div className="text-xs text-slate-400">نماذج AI أساسية</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                <div className="text-2xl font-black text-emerald-300">LIVE</div>
                <div className="text-xs text-slate-400">Railway + Vercel</div>
              </div>
            </div>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {aiCommandCards.map((card) => (
              <button key={card.path} data-testid={card.testId} onClick={() => navigate(card.path)} className="group rounded-2xl border border-white/10 bg-black/25 p-4 text-right transition hover:-translate-y-0.5 hover:border-amber-300/40 hover:bg-black/35">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <span className="rounded-xl bg-amber-500/15 p-2 text-amber-300">{card.icon}</span>
                  <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-bold text-white/70">{card.badge}</span>
                </div>
                <h3 className="mb-1 font-black text-white group-hover:text-amber-200">{card.title}</h3>
                <p className="text-xs leading-6 text-slate-400">{card.desc}</p>
              </button>
            ))}
          </div>
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
                      data-testid={action.testId}
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
