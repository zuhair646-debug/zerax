import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Gamepad2, Globe, Smartphone, Sparkles, ArrowRight, Zap } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function GameStudioDashboard({ user }) {
  const navigate = useNavigate();
  const [credits, setCredits] = useState(null);
  const [projects, setProjects] = useState([]);
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API}/api/games/projects`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (e) {
      console.error(e);
    }
  };

  const studios = [
    {
      id: 'web',
      title: 'مواقع الألعاب',
      subtitle: 'Web Games Studio',
      description: 'ألعاب HTML5 تعمل في المتصفح — سريعة الإنشاء، قابلة للنشر فوراً على Vercel',
      icon: Globe,
      color: 'from-blue-500 to-cyan-500',
      path: '/dashboard/games/web',
      examples: ['Candy Crush', 'Flappy Bird', 'Platformer', 'Puzzle Games'],
      credits: '500-2,000 نقطة',
      timeline: '2-5 أيام',
    },
    {
      id: 'app',
      title: 'تطبيقات الألعاب',
      subtitle: 'Game Apps Studio',
      description: 'ألعاب 3D احترافية للموبايل والـPC — Unity/Godot — جودة عالمية',
      icon: Smartphone,
      color: 'from-purple-500 to-pink-500',
      path: '/dashboard/games/app',
      examples: ['Fortnite-like', 'Travian', 'Racing', 'RPG'],
      credits: '2,000-50,000 نقطة',
      timeline: '1-4 أسابيع',
    },
  ];

  return (
    <div dir="rtl" className="min-h-screen bg-zinc-950 text-white">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-br from-zinc-900 via-purple-900/20 to-zinc-900 border-b border-white/10">
        {/* Grid background pattern with CSS */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute inset-0" style={{
            backgroundImage: 'linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px)',
            backgroundSize: '50px 50px'
          }} />
        </div>
        
        <div className="relative max-w-7xl mx-auto px-6 py-16">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-500">
              <Gamepad2 className="w-8 h-8 text-black" />
            </div>
            <div>
              <h1 className="text-4xl font-bold">استوديو الألعاب</h1>
              <p className="text-zinc-400">أنشئ ألعاباً احترافية بالذكاء الصناعي من الصفر</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
            <div className="bg-white/5 backdrop-blur border border-white/10 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-amber-400" />
                <div>
                  <div className="text-sm text-zinc-400">رصيدك الحالي</div>
                  <div className="text-2xl font-bold">{user?.balance?.toLocaleString() || 0} نقطة</div>
                </div>
              </div>
            </div>
            
            <div className="bg-white/5 backdrop-blur border border-white/10 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <Gamepad2 className="w-5 h-5 text-blue-400" />
                <div>
                  <div className="text-sm text-zinc-400">مشاريع نشطة</div>
                  <div className="text-2xl font-bold">{projects.length}</div>
                </div>
              </div>
            </div>
            
            <div className="bg-white/5 backdrop-blur border border-white/10 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <Zap className="w-5 h-5 text-purple-400" />
                <div>
                  <div className="text-sm text-zinc-400">سرعة الإنجاز</div>
                  <div className="text-2xl font-bold">2-5 أيام</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Studios Selection */}
      <div className="max-w-7xl mx-auto px-6 py-12">
        <h2 className="text-2xl font-bold mb-8">اختر نوع اللعبة</h2>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {studios.map(studio => (
            <div
              key={studio.id}
              className="group relative bg-zinc-900/50 backdrop-blur border border-white/10 rounded-3xl p-8 hover:border-white/20 transition-all cursor-pointer overflow-hidden"
              onClick={() => navigate(studio.path)}
            >
              {/* Background gradient */}
              <div className={`absolute inset-0 bg-gradient-to-br ${studio.color} opacity-0 group-hover:opacity-10 transition-opacity`} />
              
              <div className="relative">
                {/* Icon */}
                <div className={`inline-flex p-4 rounded-2xl bg-gradient-to-br ${studio.color} mb-6`}>
                  <studio.icon className="w-8 h-8 text-white" />
                </div>

                {/* Title */}
                <h3 className="text-3xl font-bold mb-2">{studio.title}</h3>
                <p className="text-zinc-400 text-sm mb-4">{studio.subtitle}</p>
                
                {/* Description */}
                <p className="text-zinc-300 leading-relaxed mb-6">
                  {studio.description}
                </p>

                {/* Examples */}
                <div className="flex flex-wrap gap-2 mb-6">
                  {studio.examples.map(ex => (
                    <span
                      key={ex}
                      className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-zinc-300"
                    >
                      {ex}
                    </span>
                  ))}
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div>
                    <div className="text-xs text-zinc-500 mb-1">التكلفة التقديرية</div>
                    <div className="text-sm font-semibold text-amber-400">{studio.credits}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 mb-1">وقت الإنجاز</div>
                    <div className="text-sm font-semibold text-green-400">{studio.timeline}</div>
                  </div>
                </div>

                {/* CTA */}
                <button
                  className={`w-full flex items-center justify-center gap-2 bg-gradient-to-r ${studio.color} text-white font-bold py-3 rounded-xl group-hover:scale-105 transition-transform`}
                >
                  <span>ابدأ الآن</span>
                  <ArrowRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Recent Projects */}
        {projects.length > 0 && (
          <div className="mt-16">
            <h2 className="text-2xl font-bold mb-6">مشاريعك الأخيرة</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {projects.slice(0, 6).map(project => (
                <div
                  key={project.id}
                  onClick={() => navigate(project.type === 'web_game' ? `/dashboard/games/web?project=${project.id}` : `/dashboard/games/app?project=${project.id}`)}
                  className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl p-6 hover:border-white/20 transition-all cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="font-bold text-lg mb-1">{project.gdd?.title || 'مشروع جديد'}</h3>
                      <p className="text-xs text-zinc-400">{project.type === 'web_game' ? 'لعبة ويب' : 'لعبة تطبيق'}</p>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      project.phase === 'deployed' ? 'bg-green-500/20 text-green-400' :
                      project.phase.includes('review') ? 'bg-amber-500/20 text-amber-400' :
                      'bg-blue-500/20 text-blue-400'
                    }`}>
                      {project.phase}
                    </span>
                  </div>
                  
                  <div className="text-sm text-zinc-400 mb-4">
                    <span className="text-amber-400 font-semibold">{project.credits_spent}</span> نقطة مستخدمة
                  </div>
                  
                  <div className="text-xs text-zinc-500">
                    {new Date(project.created_at).toLocaleDateString('ar-SA')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
