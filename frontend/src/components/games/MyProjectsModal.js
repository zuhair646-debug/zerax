import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Loader2, Gamepad2, Smartphone, Globe, Clock, HardDrive, FileText, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * 📂 Reusable modal that shows all the user's game projects across BOTH
 * Web Games Studio and App Games Studio, with a click-to-resume action.
 * Opened from a "My Projects" button anywhere.
 */
export default function MyProjectsModal({ open, onClose, filterGameType = null, accentColor = 'amber' }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState([]);
  const [query, setQuery] = useState('');
  const token = localStorage.getItem('token');

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    const url = filterGameType
      ? `${API}/api/games/projects?game_type=${filterGameType}`
      : `${API}/api/games/projects`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : Promise.reject(r))
      .then(d => setProjects(d.projects || []))
      .catch(() => toast.error('فشل تحميل المشاريع'))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, filterGameType]);

  if (!open) return null;

  const filtered = projects.filter(p =>
    !query.trim() ||
    (p.title || '').toLowerCase().includes(query.toLowerCase()) ||
    (p.description || '').toLowerCase().includes(query.toLowerCase())
  );

  const openProject = (p) => {
    const path = p.game_type === 'web'
      ? `/dashboard/games/web?project=${p.id}`
      : `/dashboard/games/app?project=${p.id}`;
    onClose?.();
    // Navigate then force-refresh so the studio mounts and reads the project param fresh
    navigate(path);
    // Small delay then reload (only needed if we're already on the same route)
    setTimeout(() => {
      if (window.location.search.includes(`project=${p.id}`)) {
        // Already loaded — nothing to do.
      } else {
        window.location.href = path; // safe fallback
      }
    }, 50);
  };

  const accent = {
    amber: { ring: 'ring-amber-500/40', text: 'text-amber-300', dot: 'bg-amber-400' },
    blue: { ring: 'ring-blue-500/40', text: 'text-blue-300', dot: 'bg-blue-400' },
  }[accentColor] || { ring: 'ring-amber-500/40', text: 'text-amber-300', dot: 'bg-amber-400' };

  return (
    <div dir="rtl" className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" data-testid="my-projects-modal">
      <div className={`bg-zinc-950 border border-white/10 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl ring-1 ${accent.ring}`}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center ${accent.text}`}>
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-lg text-white">المشاريع والمحادثات السابقة</h2>
              <p className="text-xs text-zinc-400">كل جلساتك محفوظة — اضغط لاستئناف أي مشروع بدون فقدان أي معلومة</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="close-my-projects"
            className="w-9 h-9 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-zinc-300 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className="px-6 py-3 border-b border-white/5">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="🔎 ابحث في مشاريعك..."
            className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm outline-none focus:border-white/30 text-white"
            data-testid="my-projects-search"
          />
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="flex items-center justify-center py-16 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin me-2" />
              <span>جاري تحميل مشاريعك...</span>
            </div>
          )}

          {!loading && filtered.length === 0 && (
            <div className="text-center py-16 text-zinc-500">
              <Gamepad2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="font-bold mb-1">ما عندك مشاريع محفوظة بعد</p>
              <p className="text-xs">ابدأ مشروع جديد من زر "ابدأ المشروع" وراح تلقاه هنا.</p>
            </div>
          )}

          {!loading && filtered.length > 0 && (
            <div className="space-y-2">
              {filtered.map(p => {
                const isApp = p.game_type === 'app';
                const Icon = isApp ? Smartphone : Globe;
                const updated = p.updated_at ? new Date(p.updated_at) : null;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => openProject(p)}
                    data-testid={`my-projects-item-${p.id}`}
                    className="w-full text-right p-4 rounded-xl bg-zinc-900/60 hover:bg-zinc-900 border border-white/10 hover:border-white/20 transition-all group"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${isApp ? 'bg-blue-500/15 text-blue-300' : 'bg-amber-500/15 text-amber-300'}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <h3 className="font-bold text-white truncate">{p.title || 'مشروع بدون عنوان'}</h3>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full border ${isApp ? 'border-blue-500/30 text-blue-300 bg-blue-500/10' : 'border-amber-500/30 text-amber-300 bg-amber-500/10'}`}>
                            {isApp ? 'لعبة تطبيق' : 'لعبة ويب'}
                          </span>
                        </div>
                        {p.description && (
                          <p className="text-xs text-zinc-400 line-clamp-1 mb-2">{p.description}</p>
                        )}
                        <div className="flex flex-wrap items-center gap-3 text-[11px] text-zinc-500">
                          <span className="flex items-center gap-1">
                            <span className={`w-1.5 h-1.5 rounded-full ${accent.dot}`}></span>
                            <span>{p.current_phase || 'discovery'}</span>
                          </span>
                          <span className="flex items-center gap-1">
                            <HardDrive className="w-3 h-3" />
                            <span>{p.size_mb ?? 0}/{p.limit_mb ?? 0} MB</span>
                          </span>
                          <span className="flex items-center gap-1">
                            <FileText className="w-3 h-3" />
                            <span>{p.asset_count || 0} أصل</span>
                          </span>
                          {p.has_notes && (
                            <span className="text-emerald-400">🧠 ذاكرة محفوظة</span>
                          )}
                          {updated && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              <span>{updated.toLocaleDateString('ar-SA')} {updated.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}</span>
                            </span>
                          )}
                        </div>
                      </div>
                      <ArrowLeft className="w-4 h-4 text-zinc-600 group-hover:text-white shrink-0 mt-1.5" />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
