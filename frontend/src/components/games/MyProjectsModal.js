import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Loader2, Gamepad2, Smartphone, Globe, Clock, HardDrive, FileText, ArrowLeft, Trash2, RotateCcw, Trash } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * 📂 Reusable modal that shows the user's game projects + 30-day trash bin
 * with soft-delete & restore actions.
 */
export default function MyProjectsModal({ open, onClose, filterGameType = null, accentColor = 'amber' }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState([]);
  const [trash, setTrash] = useState({ projects: [], assets: [] });
  const [view, setView] = useState('active'); // active | trash
  const [query, setQuery] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null); // project obj to confirm
  const token = localStorage.getItem('token');

  const loadActive = useCallback(async () => {
    setLoading(true);
    try {
      const url = filterGameType
        ? `${API}/api/games/projects?game_type=${filterGameType}`
        : `${API}/api/games/projects`;
      const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      const d = await r.json();
      setProjects(d.projects || []);
    } catch (_) {
      toast.error('فشل تحميل المشاريع');
    } finally {
      setLoading(false);
    }
  }, [filterGameType, token]);

  const loadTrash = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/games/trash`, { headers: { Authorization: `Bearer ${token}` } });
      const d = await r.json();
      setTrash({ projects: d.projects || [], assets: d.assets || [] });
    } catch (_) {
      toast.error('فشل تحميل سلة المهملات');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!open) return;
    if (view === 'active') loadActive();
    else loadTrash();
  }, [open, view, loadActive, loadTrash]);

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
    navigate(path);
  };

  const handleDeleteProject = async (p) => {
    setConfirmDelete(null);
    try {
      const r = await fetch(`${API}/api/games/project/${p.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error('failed');
      toast.success('🗑️ تم النقل لسلة المهملات (قابل للاسترداد 30 يوم)');
      loadActive();
    } catch (_) {
      toast.error('فشل الحذف');
    }
  };

  const handleRestoreProject = async (p) => {
    try {
      const r = await fetch(`${API}/api/games/project/${p.id}/restore`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error('failed');
      toast.success('✅ تم الاسترداد بنجاح');
      loadTrash();
    } catch (_) {
      toast.error('فشل الاسترداد');
    }
  };

  const handleRestoreAsset = async (a) => {
    try {
      const r = await fetch(`${API}/api/games/project/${a.project_id}/asset/${a.id}/restore`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error('failed');
      toast.success('✅ تم استرداد الأصل');
      loadTrash();
    } catch (_) {
      toast.error('فشل الاسترداد');
    }
  };

  const accent = {
    amber: { ring: 'ring-amber-500/40', text: 'text-amber-300', dot: 'bg-amber-400', tabActive: 'border-amber-400 text-amber-300', tabBg: 'bg-amber-500/10' },
    blue: { ring: 'ring-blue-500/40', text: 'text-blue-300', dot: 'bg-blue-400', tabActive: 'border-blue-400 text-blue-300', tabBg: 'bg-blue-500/10' },
  }[accentColor] || { ring: 'ring-amber-500/40', text: 'text-amber-300', dot: 'bg-amber-400', tabActive: 'border-amber-400 text-amber-300', tabBg: 'bg-amber-500/10' };

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
              <h2 className="font-bold text-lg text-white">{view === 'active' ? 'المشاريع والمحادثات السابقة' : 'سلة المهملات (30 يوم)'}</h2>
              <p className="text-xs text-zinc-400">
                {view === 'active'
                  ? 'كل جلساتك محفوظة — اضغط لاستئناف أي مشروع.'
                  : 'العناصر تنحذف نهائياً بعد 30 يوم من تاريخ الحذف.'}
              </p>
            </div>
          </div>
          <button type="button" onClick={onClose} data-testid="close-my-projects"
            className="w-9 h-9 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-zinc-300 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/5 px-2">
          <button type="button" onClick={() => setView('active')} data-testid="tab-active-projects"
            className={`px-4 py-2 text-sm font-bold border-b-2 ${view === 'active' ? accent.tabActive : 'border-transparent text-zinc-400 hover:text-white'}`}>
            📂 النشطة {projects.length > 0 && <span className="ms-1 text-[10px] opacity-70">({projects.length})</span>}
          </button>
          <button type="button" onClick={() => setView('trash')} data-testid="tab-trash"
            className={`px-4 py-2 text-sm font-bold border-b-2 flex items-center gap-1.5 ${view === 'trash' ? 'border-rose-400 text-rose-300' : 'border-transparent text-zinc-400 hover:text-white'}`}>
            <Trash className="w-3.5 h-3.5" />
            <span>سلة المهملات</span>
            {(trash.projects.length + trash.assets.length) > 0 && (
              <span className="text-[10px] bg-rose-500/20 px-1.5 py-0.5 rounded-full">{trash.projects.length + trash.assets.length}</span>
            )}
          </button>
        </div>

        {/* Search (only for active view) */}
        {view === 'active' && (
          <div className="px-6 py-3 border-b border-white/5">
            <input type="text" value={query} onChange={e => setQuery(e.target.value)}
              placeholder="🔎 ابحث في مشاريعك..." data-testid="my-projects-search"
              className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm outline-none focus:border-white/30 text-white" />
          </div>
        )}

        {/* List */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="flex items-center justify-center py-16 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin me-2" />
              <span>جاري التحميل...</span>
            </div>
          )}

          {/* ─── ACTIVE PROJECTS ─── */}
          {!loading && view === 'active' && filtered.length === 0 && (
            <div className="text-center py-16 text-zinc-500">
              <Gamepad2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="font-bold mb-1">ما عندك مشاريع محفوظة بعد</p>
              <p className="text-xs">ابدأ مشروع جديد من زر "ابدأ المشروع".</p>
            </div>
          )}
          {!loading && view === 'active' && filtered.length > 0 && (
            <div className="space-y-2">
              {filtered.map(p => {
                const isApp = p.game_type === 'app';
                const Icon = isApp ? Smartphone : Globe;
                const updated = p.updated_at ? new Date(p.updated_at) : null;
                return (
                  <div key={p.id} className="group p-4 rounded-xl bg-zinc-900/60 hover:bg-zinc-900 border border-white/10 hover:border-white/20 transition-all flex items-start gap-3"
                    data-testid={`my-projects-item-${p.id}`}>
                    <button type="button" onClick={() => openProject(p)} className="flex-1 text-right flex items-start gap-3 min-w-0">
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
                        {p.description && <p className="text-xs text-zinc-400 line-clamp-1 mb-2">{p.description}</p>}
                        <div className="flex flex-wrap items-center gap-3 text-[11px] text-zinc-500">
                          <span className="flex items-center gap-1">
                            <span className={`w-1.5 h-1.5 rounded-full ${accent.dot}`}></span>
                            <span>{p.current_phase || 'discovery'}</span>
                          </span>
                          <span className="flex items-center gap-1"><HardDrive className="w-3 h-3" /><span>{p.size_mb ?? 0}/{p.limit_mb ?? 0} MB</span></span>
                          <span className="flex items-center gap-1"><FileText className="w-3 h-3" /><span>{p.asset_count || 0} أصل</span></span>
                          {p.has_notes && <span className="text-emerald-400">🧠 ذاكرة محفوظة</span>}
                          {updated && (
                            <span className="flex items-center gap-1"><Clock className="w-3 h-3" />
                              <span>{updated.toLocaleDateString('ar-SA')}</span>
                            </span>
                          )}
                        </div>
                      </div>
                      <ArrowLeft className="w-4 h-4 text-zinc-600 group-hover:text-white shrink-0 mt-1.5" />
                    </button>
                    <button type="button" onClick={() => setConfirmDelete(p)}
                      data-testid={`delete-project-${p.id}`}
                      title="نقل لسلة المهملات"
                      className="w-9 h-9 rounded-lg bg-rose-500/10 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 hover:text-rose-200 flex items-center justify-center shrink-0">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {/* ─── TRASH VIEW ─── */}
          {!loading && view === 'trash' && (trash.projects.length === 0 && trash.assets.length === 0) && (
            <div className="text-center py-16 text-zinc-500">
              <Trash className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="font-bold mb-1">سلة المهملات فاضية</p>
              <p className="text-xs">المحذوفات تظهر هنا لمدة 30 يوم.</p>
            </div>
          )}
          {!loading && view === 'trash' && (trash.projects.length > 0 || trash.assets.length > 0) && (
            <div className="space-y-4">
              {trash.projects.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-zinc-400 mb-2 px-1">📂 مشاريع محذوفة ({trash.projects.length})</h3>
                  <div className="space-y-2">
                    {trash.projects.map(p => (
                      <div key={p.id} className="flex items-center gap-3 p-3 rounded-lg bg-zinc-900/40 border border-rose-500/20" data-testid={`trash-project-${p.id}`}>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="text-base">{p.game_type === 'app' ? '📱' : '🌐'}</span>
                            <h4 className="font-bold text-sm text-white truncate">{p.title || 'مشروع بدون عنوان'}</h4>
                          </div>
                          <p className="text-[10px] text-zinc-500">حُذف: {new Date(p.deleted_at).toLocaleString('ar-SA')}</p>
                        </div>
                        <button type="button" onClick={() => handleRestoreProject(p)}
                          data-testid={`restore-project-${p.id}`}
                          className="px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-400/30 text-emerald-200 text-xs font-bold flex items-center gap-1.5">
                          <RotateCcw className="w-3 h-3" /><span>استرداد</span>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {trash.assets.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-zinc-400 mb-2 px-1">🎨 أصول محذوفة ({trash.assets.length})</h3>
                  <div className="space-y-2">
                    {trash.assets.map(a => (
                      <div key={`${a.project_id}-${a.id}`} className="flex items-center gap-3 p-3 rounded-lg bg-zinc-900/40 border border-rose-500/20" data-testid={`trash-asset-${a.id}`}>
                        {a.image_url && (
                          <img src={`${API}${a.image_url}`} alt={a.name}
                            className="w-12 h-12 rounded object-cover bg-black/40" loading="lazy"
                            onError={(e) => { e.currentTarget.src = (a.cdn_url || ''); }} />
                        )}
                        <div className="flex-1 min-w-0">
                          <h4 className="text-xs font-bold text-white truncate">{a.name || 'أصل'}</h4>
                          <p className="text-[10px] text-zinc-500 truncate">من: {a.project_title || a.project_id}</p>
                          <p className="text-[10px] text-zinc-600">حُذف: {new Date(a.deleted_at).toLocaleString('ar-SA')}</p>
                        </div>
                        <button type="button" onClick={() => handleRestoreAsset(a)}
                          data-testid={`restore-asset-${a.id}`}
                          className="px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-400/30 text-emerald-200 text-xs font-bold flex items-center gap-1.5">
                          <RotateCcw className="w-3 h-3" /><span>استرداد</span>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Confirm delete dialog */}
      {confirmDelete && (
        <div className="fixed inset-0 z-[60] bg-black/80 flex items-center justify-center p-4">
          <div dir="rtl" className="bg-zinc-950 border border-rose-500/30 rounded-2xl p-6 max-w-md w-full" data-testid="confirm-delete-dialog">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-rose-500/20 flex items-center justify-center text-rose-300">
                <Trash2 className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-white">نقل لسلة المهملات؟</h3>
            </div>
            <p className="text-sm text-zinc-300 mb-2">
              المشروع <span className="font-bold text-amber-300">"{confirmDelete.title || 'بدون عنوان'}"</span> راح ينحذف لكن يبقى قابل للاسترداد لمدة 30 يوم.
            </p>
            <p className="text-xs text-zinc-500 mb-5">بعد 30 يوم راح ينحذف نهائياً ولن يمكن استرداده.</p>
            <div className="flex items-center justify-end gap-2">
              <button type="button" onClick={() => setConfirmDelete(null)} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-300 text-sm font-bold" data-testid="cancel-delete">
                إلغاء
              </button>
              <button type="button" onClick={() => handleDeleteProject(confirmDelete)} className="px-4 py-2 rounded-lg bg-rose-500/30 hover:bg-rose-500/40 border border-rose-500/50 text-rose-100 text-sm font-bold flex items-center gap-1.5" data-testid="confirm-delete-btn">
                <Trash2 className="w-3.5 h-3.5" /><span>نعم، احذف</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
