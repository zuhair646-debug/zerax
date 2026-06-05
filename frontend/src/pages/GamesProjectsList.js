import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowRight, Gamepad2, Smartphone, FileText, Layers, Calendar, Loader2, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function GamesProjectsList() {
  const navigate = useNavigate();
  const location = useLocation();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  // Detect game type from URL: /dashboard/games/web/projects → web, /dashboard/games/app/projects → app
  const isApp = location.pathname.includes('/games/app');
  const gameType = isApp ? 'app' : 'web';
  const backUrl = isApp ? '/dashboard/games/app' : '/dashboard/games/web';
  const accentColor = isApp ? 'blue' : 'amber';

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { setLoading(false); return; }
    fetch(`${API}/api/games/projects?game_type=${gameType}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : Promise.reject(r))
      .then(d => setProjects(d.projects || []))
      .catch(() => toast.error('فشل تحميل المشاريع'))
      .finally(() => setLoading(false));
  }, [gameType]);

  const openProject = (pid) => navigate(`${backUrl}?project=${pid}`);

  return (
    <div dir="rtl" className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-amber-950/20 text-white p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6 gap-3 flex-wrap">
          <button onClick={() => navigate(backUrl)}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10"
            data-testid="back-to-studio">
            <ArrowRight className="w-4 h-4" />
            <span className="text-sm font-medium">رجوع للاستوديو</span>
          </button>
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${isApp ? 'from-blue-500 to-purple-600' : 'from-amber-500 to-orange-600'} flex items-center justify-center`}>
              {isApp ? <Smartphone className="w-7 h-7 text-white" /> : <Gamepad2 className="w-7 h-7 text-black" />}
            </div>
            <div>
              <h1 className="text-2xl font-bold">📂 مشاريعي · {isApp ? 'تطبيقات الألعاب' : 'مواقع الألعاب'}</h1>
              <p className="text-sm text-zinc-400">كل اللي اشتغلت عليه — رجع للأي منها وكمّل من حيث وقفت</p>
            </div>
          </div>
        </div>

        {loading && (
          <div className="text-center text-zinc-500 mt-12">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" />
            <p>جاري تحميل المشاريع...</p>
          </div>
        )}

        {!loading && projects.length === 0 && (
          <div className="text-center text-zinc-500 mt-20">
            <div className="text-6xl mb-3">📭</div>
            <p className="font-bold mb-2">ما عندك أي مشاريع بعد</p>
            <p className="text-xs mb-4">ابدأ مشروعك الأول واشتغل عليه بثقة — كل شي محفوظ تلقائياً.</p>
            <button onClick={() => navigate(backUrl)}
              className={`px-6 py-3 rounded-xl font-bold ${isApp ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white' : 'bg-gradient-to-r from-amber-500 to-orange-600 text-black'}`}>
              ابدأ مشروع جديد ✨
            </button>
          </div>
        )}

        {!loading && projects.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="projects-grid">
            {projects.map(p => {
              const expiringSoon = p.expires_at && (() => {
                try { return Math.ceil((new Date(p.expires_at) - new Date()) / 86400000); } catch { return null; }
              })();
              return (
                <div key={p.id} onClick={() => openProject(p.id)}
                  className={`group rounded-xl border border-white/10 hover:border-${accentColor}-400/50 bg-zinc-900/50 hover:bg-zinc-900/80 p-4 cursor-pointer transition-all hover:scale-[1.01]`}
                  data-testid={`project-card-${p.id}`}>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex-1 min-w-0">
                      <h3 className={`font-bold text-white truncate flex items-center gap-2`}>
                        {p.title}
                        <ExternalLink className={`w-3.5 h-3.5 text-zinc-500 group-hover:text-${accentColor}-300`} />
                      </h3>
                      <p className="text-xs text-zinc-400 truncate">{p.description || 'بدون وصف'}</p>
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full bg-${accentColor}-500/15 border border-${accentColor}-400/30 text-${accentColor}-200 font-bold shrink-0`}>
                      {p.tier_label || 'مجاني'}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-[11px] text-zinc-500 mt-2">
                    <span className="flex items-center gap-1"><Layers className="w-3 h-3" />{p.programming_type}</span>
                    <span className="flex items-center gap-1"><FileText className="w-3 h-3" />{p.asset_count} أصل</span>
                    <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{(p.updated_at || p.created_at || '').slice(0, 10)}</span>
                    <span>{p.size_mb} MB</span>
                    {p.has_notes && <span className="text-emerald-300">📝 ملاحظات</span>}
                    {expiringSoon !== null && expiringSoon !== undefined && expiringSoon <= 3 && (
                      <span className="text-red-300 font-bold animate-pulse">⚠️ ينتهي خلال {expiringSoon} يوم</span>
                    )}
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
