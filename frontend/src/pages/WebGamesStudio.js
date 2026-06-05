import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Send, Check, AlertCircle, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function WebGamesStudio({ user }) {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNewProject, setShowNewProject] = useState(false);
  const [idea, setIdea] = useState('');
  const [creating, setCreating] = useState(false);

  // ═══════════════════════════════════════════════════════════
  // Load Projects
  // ═══════════════════════════════════════════════════════════
  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API}/api/games/projects`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.ok) {
        setProjects(data.projects.filter(p => p.type === 'web_game'));
      }
    } catch (err) {
      toast.error('خطأ في تحميل المشاريع');
    } finally {
      setLoading(false);
    }
  };

  // ═══════════════════════════════════════════════════════════
  // Create New Project
  // ═══════════════════════════════════════════════════════════
  const handleCreate = async () => {
    if (!idea.trim()) return toast.error('اكتب فكرة اللعبة أولاً');
    
    setCreating(true);
    try {
      const res = await fetch(`${API}/api/games/web/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ idea, game_type: 'web' })
      });
      const data = await res.json();
      
      if (data.ok) {
        toast.success('تم إنشاء المشروع!');
        navigate(`/dashboard/games/web/${data.project_id}`);
      } else {
        toast.error(data.error || 'فشل الإنشاء');
      }
    } catch (err) {
      toast.error('خطأ في الإنشاء');
    } finally {
      setCreating(false);
    }
  };

  // ═══════════════════════════════════════════════════════════
  // UI
  // ═══════════════════════════════════════════════════════════
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
      </div>
    );
  }

  return (
    <div dir="rtl" className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard/games')}
              className="p-2 hover:bg-white/5 rounded-lg transition"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-3xl font-bold">🎮 ألعاب الويب</h1>
              <p className="text-zinc-400 mt-1">HTML5 Games — تعمل على أي متصفح</p>
            </div>
          </div>
          <button
            onClick={() => setShowNewProject(true)}
            className="px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl font-bold hover:opacity-90 transition flex items-center gap-2"
          >
            <Sparkles className="w-5 h-5" />
            مشروع جديد
          </button>
        </div>

        {/* New Project Modal */}
        {showNewProject && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-zinc-900 rounded-2xl border border-white/10 max-w-2xl w-full p-8">
              <h2 className="text-2xl font-bold mb-4">💡 فكرة اللعبة</h2>
              <p className="text-zinc-400 mb-6">
                اكتب وصف مختصر للعبة اللي تبيها — الذكاء الاصطناعي راح يساعدك تبنيها خطوة بخطوة
              </p>
              
              <textarea
                value={idea}
                onChange={e => setIdea(e.target.value)}
                placeholder="مثال: لعبة platformer ثنائية الأبعاد، البطل يجمع عملات ذهبية ويتجنب الأعداء، مستوحاة من ماريو..."
                className="w-full h-32 bg-black/40 border border-white/15 rounded-xl px-4 py-3 outline-none focus:border-cyan-400 transition resize-none"
                dir="rtl"
              />

              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleCreate}
                  disabled={creating || !idea.trim()}
                  className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl font-bold disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition flex items-center justify-center gap-2"
                >
                  {creating ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      جاري الإنشاء...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      ابدأ المشروع
                    </>
                  )}
                </button>
                <button
                  onClick={() => setShowNewProject(false)}
                  className="px-6 py-3 bg-white/5 hover:bg-white/10 rounded-xl font-bold transition"
                >
                  إلغاء
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Projects List */}
        {projects.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-10 h-10 text-zinc-600" />
            </div>
            <h3 className="text-xl font-bold text-zinc-400 mb-2">ما عندك مشاريع بعد</h3>
            <p className="text-zinc-500 mb-6">ابدأ مشروعك الأول الحين!</p>
            <button
              onClick={() => setShowNewProject(true)}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl font-bold hover:opacity-90 transition"
            >
              إنشاء مشروع
            </button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map(project => {
              const phases = project.phases || [];
              const current = project.current_phase || 0;
              const progress = (current / phases.length) * 100;
              
              return (
                <div
                  key={project.id}
                  onClick={() => navigate(`/dashboard/games/web/${project.id}`)}
                  className="group bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl p-6 hover:border-cyan-400/50 transition cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <h3 className="font-bold text-lg mb-1 line-clamp-1">{project.idea}</h3>
                      <p className="text-sm text-zinc-400">
                        {new Date(project.created_at).toLocaleDateString('ar-SA')}
                      </p>
                    </div>
                    {project.status === 'completed' && (
                      <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
                        <Check className="w-4 h-4 text-green-400" />
                      </div>
                    )}
                  </div>

                  {/* Progress */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between text-xs text-zinc-500 mb-2">
                      <span>المرحلة {current + 1} من {phases.length}</span>
                      <span>{Math.round(progress)}%</span>
                    </div>
                    <div className="h-2 bg-black/40 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>

                  {/* Current Phase */}
                  {phases[current] && (
                    <div className="text-sm text-zinc-400">
                      <span className="text-cyan-400 font-semibold">المرحلة الحالية:</span> {phases[current].title}
                    </div>
                  )}

                  {/* Credits Spent */}
                  <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between text-sm">
                    <span className="text-zinc-500">مصروف</span>
                    <span className="text-amber-400 font-bold">{project.total_credits_spent || 0} نقطة</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
}
