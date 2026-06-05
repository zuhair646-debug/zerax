import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Gamepad2, Smartphone, ArrowLeft } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function GameStudio({ user }) {
  const navigate = useNavigate();

  const studios = [
    {
      id: 'web',
      title: '🎮 ألعاب الويب',
      description: 'العاب HTML5 قوية تعمل على أي متصفح',
      features: [
        'لا تحتاج تثبيت',
        'توافق مع كل الأجهزة',
        'سريعة التحميل',
        'سهلة المشاركة'
      ],
      path: '/dashboard/games/web',
      color: 'from-blue-500 to-cyan-500',
      icon: Gamepad2
    },
    {
      id: 'app',
      title: '📱 ألعاب التطبيقات',
      description: 'تطبيقات احترافية للـiOS و Android',
      features: [
        'أداء عالي',
        'نشر على المتاجر',
        'Multiplayer جاهز',
        'Monetization مدمج'
      ],
      path: '/dashboard/games/app',
      color: 'from-purple-500 to-pink-500',
      icon: Smartphone
    }
  ];

  return (
    <div dir="rtl" className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => navigate('/dashboard')}
            className="p-2 hover:bg-white/5 rounded-lg transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-3xl font-bold">🎮 استوديو الألعاب</h1>
            <p className="text-zinc-400 mt-1">اختر نوع اللعبة اللي تبي تبنيها</p>
          </div>
        </div>

        {/* Studios Grid */}
        <div className="grid md:grid-cols-2 gap-6">
          {studios.map(studio => {
            const Icon = studio.icon;
            return (
              <div
                key={studio.id}
                onClick={() => navigate(studio.path)}
                className="group relative overflow-hidden rounded-2xl border border-white/10 bg-zinc-900/50 backdrop-blur p-8 cursor-pointer hover:border-white/20 transition-all hover:scale-[1.02]"
              >
                {/* Gradient Background */}
                <div className={`absolute inset-0 bg-gradient-to-br ${studio.color} opacity-0 group-hover:opacity-10 transition-opacity`} />
                
                {/* Content */}
                <div className="relative z-10">
                  <div className="flex items-center gap-4 mb-4">
                    <div className={`p-4 rounded-xl bg-gradient-to-br ${studio.color}`}>
                      <Icon className="w-8 h-8 text-white" />
                    </div>
                    <h2 className="text-2xl font-bold">{studio.title}</h2>
                  </div>
                  
                  <p className="text-zinc-300 mb-6">{studio.description}</p>
                  
                  {/* Features */}
                  <div className="space-y-2">
                    {studio.features.map((feature, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm text-zinc-400">
                        <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                        <span>{feature}</span>
                      </div>
                    ))}
                  </div>

                  {/* Arrow */}
                  <div className="mt-6 flex justify-end">
                    <div className="w-10 h-10 rounded-full bg-white/5 group-hover:bg-white/10 flex items-center justify-center transition">
                      <ArrowLeft className="w-5 h-5 rotate-180" />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Info Card */}
        <div className="mt-8 rounded-xl border border-amber-500/20 bg-amber-500/5 p-6">
          <h3 className="text-lg font-bold text-amber-400 mb-2">💡 كيف يشتغل؟</h3>
          <p className="text-zinc-300 mb-4">
            كل مشروع لعبة يمر بمراحل احترافية — من التصميم لين النشر. كل مرحلة:
          </p>
          <ul className="space-y-2 text-sm text-zinc-400">
            <li>✓ نفهم متطلباتك بالتفصيل</li>
            <li>✓ نوفّر لك خيارات واقتراحات</li>
            <li>✓ نولّد الأصول (صور، أصوات، كود) حقيقية</li>
            <li>✓ تدفع بعد كل مرحلة (شفافية كاملة)</li>
          </ul>
        </div>

      </div>
    </div>
  );
}
