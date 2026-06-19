/**
 * MyProjects — dedicated page that lists every "in-progress" project the user
 * has started, split into:
 *   - Websites (mode === 'website' or no mode)
 *   - Apps     (mode === 'app')
 *   - Studio   (image / video / anime / longform)
 *
 * Each card shows: name, last update, phase, completion %, mode badge,
 * and CTAs: ▶ Continue · 🗑 Delete · ❓ Support.
 *
 * Goal: split the "start new" flow from the "continue existing" flow so the
 * landing pages stay clean and focused.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Globe, Smartphone, Sparkles, Trash2, ArrowLeft, Plus, LifeBuoy, Clock, RefreshCw, Bell, BellOff } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import ZenrexBrand from '../components/ZenrexBrand';
import StorageIndicator from '../components/StorageIndicator';

const API = process.env.REACT_APP_BACKEND_URL;

function fmtDate(s) {
  if (!s) return '';
  try {
    const d = new Date(s);
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return 'الآن';
    if (diff < 3600) return `قبل ${Math.floor(diff / 60)} دقيقة`;
    if (diff < 86400) return `قبل ${Math.floor(diff / 3600)} ساعة`;
    if (diff < 604800) return `قبل ${Math.floor(diff / 86400)} يوم`;
    return d.toLocaleDateString('ar-SA');
  } catch (_) { return ''; }
}

function modeBadge(mode) {
  const map = {
    website:       { label: 'موقع',         color: 'emerald', icon: Globe },
    app:           { label: 'تطبيق جوال',   color: 'purple',  icon: Smartphone },
    image_studio:  { label: 'صور',          color: 'rose',    icon: Sparkles },
    video_studio:  { label: 'فيديو',        color: 'cyan',    icon: Sparkles },
    anime_studio:  { label: 'أنمي',         color: 'pink',    icon: Sparkles },
    longform_video:{ label: 'فيديو طويل',   color: 'blue',    icon: Sparkles },
  };
  return map[mode] || map.website;
}

function ProjectCard({ project, onContinue, onDelete }) {
  const m = modeBadge(project.mode);
  const Icon = m.icon;
  // Static class maps — Tailwind JIT requires literal class names
  const STYLE = {
    emerald: { card: 'border-emerald-500/30 hover:border-emerald-400/60', icon: 'text-emerald-300', pill: 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300', btn: 'bg-gradient-to-r from-emerald-500 to-emerald-600' },
    purple:  { card: 'border-purple-500/30 hover:border-purple-400/60',  icon: 'text-purple-300',  pill: 'bg-purple-500/20 border-purple-500/30 text-purple-300',    btn: 'bg-gradient-to-r from-purple-500 to-purple-600' },
    rose:    { card: 'border-rose-500/30 hover:border-rose-400/60',      icon: 'text-rose-300',    pill: 'bg-rose-500/20 border-rose-500/30 text-rose-300',          btn: 'bg-gradient-to-r from-rose-500 to-rose-600' },
    cyan:    { card: 'border-cyan-500/30 hover:border-cyan-400/60',      icon: 'text-cyan-300',    pill: 'bg-cyan-500/20 border-cyan-500/30 text-cyan-300',          btn: 'bg-gradient-to-r from-cyan-500 to-cyan-600' },
    pink:    { card: 'border-pink-500/30 hover:border-pink-400/60',      icon: 'text-pink-300',    pill: 'bg-pink-500/20 border-pink-500/30 text-pink-300',          btn: 'bg-gradient-to-r from-pink-500 to-pink-600' },
    blue:    { card: 'border-blue-500/30 hover:border-blue-400/60',      icon: 'text-blue-300',    pill: 'bg-blue-500/20 border-blue-500/30 text-blue-300',          btn: 'bg-gradient-to-r from-blue-500 to-blue-600' },
  };
  const s = STYLE[m.color] || STYLE.emerald;

  return (
    <div
      data-testid={`project-card-${project.id}`}
      className={`group rounded-2xl border bg-zinc-900/60 ${s.card} p-5 transition-all hover:scale-[1.01]`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <div className={`w-10 h-10 rounded-xl bg-black/40 flex items-center justify-center shrink-0 ${s.icon}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="font-black text-base text-white truncate">{project.name || 'بدون اسم'}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${s.pill}`}>
                {m.label}
              </span>
              {project.platform && (
                <span className="text-[10px] text-zinc-400">
                  {project.platform === 'ios' ? '🍎 iPhone' : project.platform === 'android' ? '🤖 Android' : '📱 الاثنين'}
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onDelete(project); }}
          data-testid={`project-delete-${project.id}`}
          className="text-zinc-500 hover:text-red-400 p-1.5 rounded-lg hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition"
          aria-label="حذف"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {project.description && (
        <p className="text-xs text-zinc-400 line-clamp-2 mb-3">{project.description}</p>
      )}

      <div className="flex items-center justify-between text-[11px] text-zinc-500 mb-4">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {fmtDate(project.updated_at || project.created_at)}
        </span>
        <span>
          {project.current_html ? '✅ يحتوي على بناء' : '⏳ في البداية'}
        </span>
      </div>

      <div className="flex gap-2">
        <Button
          onClick={() => onContinue(project)}
          data-testid={`project-continue-${project.id}`}
          className={`flex-1 ${s.btn} hover:opacity-90 text-white text-xs font-black`}
        >
          أكمل العمل
          <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />
        </Button>
      </div>
    </div>
  );
}

export default function MyProjects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all | website | app | studio
  const [reminderOptOut, setReminderOptOut] = useState(false);

  const loadReminderPref = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
      const r = await fetch(`${API}/api/resume-reminders/me`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) setReminderOptOut(!!(await r.json()).opt_out);
    } catch (_) { /* silent */ }
  }, []);

  const toggleReminders = async () => {
    const token = localStorage.getItem('token');
    const next = !reminderOptOut;
    try {
      const r = await fetch(`${API}/api/resume-reminders/me/opt-out`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ opt_out: next }),
      });
      if (r.ok) {
        setReminderOptOut(next);
        toast.success(next ? 'تم إيقاف التذكيرات' : 'تم تفعيل التذكيرات — راح نذكرك بمشاريعك');
      }
    } catch (_) {
      toast.error('فشل التحديث');
    }
  };

  const load = useCallback(async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
      return;
    }
    try {
      const r = await fetch(`${API}/api/freebuild-chat/projects`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) {
        const d = await r.json();
        setProjects(d.projects || []);
      } else if (r.status === 401) {
        navigate('/login');
      }
    } catch (e) {
      toast.error('فشل التحميل');
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => { load(); loadReminderPref(); }, [load, loadReminderPref]);

  const handleContinue = (p) => {
    navigate(`/freebuild/chat/${p.id}`);
  };

  const handleDelete = async (p) => {
    if (!window.confirm(`حذف "${p.name}"؟ هذي العملية لا رجعة فيها.`)) return;
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/freebuild-chat/project/${p.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) {
        toast.success('تم الحذف');
        setProjects((arr) => arr.filter((x) => x.id !== p.id));
      } else {
        toast.error('فشل الحذف');
      }
    } catch (e) {
      toast.error('فشل الحذف');
    }
  };

  // Group by mode
  const websites = projects.filter((p) => !p.mode || p.mode === 'website');
  const apps     = projects.filter((p) => p.mode === 'app');
  const studio   = projects.filter((p) => ['image_studio', 'video_studio', 'anime_studio', 'longform_video'].includes(p.mode));

  const groups = [
    { id: 'website', title: 'المواقع', icon: Globe,      items: websites, newPath: '/freebuild/chat',  color: 'emerald' },
    { id: 'app',     title: 'تطبيقات الجوال', icon: Smartphone, items: apps,     newPath: '/native/new',      color: 'purple'  },
    { id: 'studio',  title: 'الاستوديو (صور/فيديو)', icon: Sparkles,   items: studio,   newPath: '/dashboard',       color: 'rose'    },
  ];
  const visibleGroups = filter === 'all' ? groups : groups.filter((g) => g.id === filter);

  // Static class maps for group "new" buttons — Tailwind JIT needs literals
  const GROUP_BTN = {
    emerald: 'bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/30 text-emerald-300',
    purple:  'bg-purple-500/10 hover:bg-purple-500/20 border-purple-500/30 text-purple-300',
    rose:    'bg-rose-500/10 hover:bg-rose-500/20 border-rose-500/30 text-rose-300',
  };
  const GROUP_ICON = {
    emerald: 'text-emerald-400',
    purple:  'text-purple-400',
    rose:    'text-rose-400',
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" dir="rtl" data-testid="my-projects-page">
      {/* Top bar */}
      <header className="sticky top-0 z-30 border-b border-white/10 bg-zinc-950/85 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <a href="/" className="flex items-center gap-2 hover:opacity-80">
              <ZenrexBrand size={26} />
            </a>
            <span className="text-zinc-600">•</span>
            <h1 className="text-sm font-bold text-zinc-300">مشاريعي قيد الإنشاء</h1>
          </div>
          <div className="flex items-center gap-2">
            <StorageIndicator />
            <button
              type="button"
              onClick={toggleReminders}
              data-testid="toggle-reminders"
              title={reminderOptOut ? 'فعّل تذكيرات أكمل المشروع' : 'أوقف تذكيرات أكمل المشروع'}
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border text-xs font-bold ${reminderOptOut ? 'bg-zinc-900 border-zinc-700 text-zinc-400' : 'bg-amber-500/10 border-amber-500/40 text-amber-300'}`}
            >
              {reminderOptOut ? <BellOff className="w-4 h-4" /> : <Bell className="w-4 h-4" />}
              <span className="hidden sm:inline">{reminderOptOut ? 'التذكيرات موقوفة' : 'تذكيرات مفعّلة'}</span>
            </button>
            <button
              type="button"
              onClick={load}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-300"
              aria-label="تحديث"
              data-testid="refresh-btn"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <a
              href="https://wa.me/966500000000"
              target="_blank"
              rel="noreferrer"
              data-testid="support-btn"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-bold"
            >
              <LifeBuoy className="w-4 h-4" />
              <span className="hidden sm:inline">دعم فني</span>
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Filter pills */}
        <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-1">
          {[
            { id: 'all',     label: 'الكل' },
            { id: 'website', label: '🌐 مواقع' },
            { id: 'app',     label: '📱 تطبيقات' },
            { id: 'studio',  label: '🎨 استوديو' },
          ].map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              data-testid={`filter-${f.id}`}
              className={`px-4 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition ${
                filter === f.id
                  ? 'bg-amber-400 text-black'
                  : 'bg-zinc-900 text-zinc-400 border border-zinc-800 hover:border-zinc-700'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Reminder info banner */}
        {!reminderOptOut && (
          <div data-testid="reminder-banner" className="mb-6 rounded-xl border border-amber-500/20 bg-gradient-to-l from-amber-500/5 to-transparent p-3 flex items-start gap-3">
            <Bell className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-100/80 leading-relaxed flex-1">
              <strong className="text-amber-200">تذكيرات ذكية مفعّلة:</strong> راح نرسل لك إيميل لطيف
              بعد <b>يوم</b>، ثم <b>٣ أيام</b>، ثم <b>أسبوع</b> لأي مشروع تتركه بدون إكمال — موقع، تطبيق، لعبة، أو فيديو.
              <button
                type="button"
                onClick={toggleReminders}
                className="underline mr-1 hover:text-amber-200"
                data-testid="reminder-banner-disable"
              >
                إيقاف
              </button>
            </p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-20 text-zinc-500">جاري التحميل...</div>
        ) : projects.length === 0 ? (
          <div className="text-center py-20" data-testid="no-projects">
            <div className="text-6xl mb-3">📂</div>
            <p className="text-zinc-300 font-bold text-lg mb-1">لا توجد مشاريع بعد</p>
            <p className="text-zinc-500 text-sm mb-6">ابدأ مشروعك الأول الآن</p>
            <div className="flex justify-center gap-3 flex-wrap">
              <a href="/freebuild/chat" className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black font-black text-sm">
                <Globe className="w-4 h-4 inline ml-1" />
                موقع جديد
              </a>
              <a href="/native/new" className="px-5 py-2.5 rounded-xl bg-purple-500 hover:bg-purple-400 text-white font-black text-sm">
                <Smartphone className="w-4 h-4 inline ml-1" />
                تطبيق جديد
              </a>
            </div>
          </div>
        ) : (
          <div className="space-y-10">
            {visibleGroups.map((g) => {
              const Icon = g.icon;
              return (
                <section key={g.id} data-testid={`group-${g.id}`}>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-black flex items-center gap-2">
                      <Icon className={`w-5 h-5 ${GROUP_ICON[g.color]}`} />
                      <span>{g.title}</span>
                      <span className="text-xs text-zinc-500 font-normal">({g.items.length})</span>
                    </h2>
                    <a
                      href={g.newPath}
                      data-testid={`new-${g.id}-btn`}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-bold ${GROUP_BTN[g.color]}`}
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>جديد</span>
                    </a>
                  </div>
                  {g.items.length === 0 ? (
                    <p className="text-sm text-zinc-600 py-6 text-center border border-dashed border-white/10 rounded-xl">
                      ما عندك {g.title} لسه — اضغط (جديد) لتبدأ.
                    </p>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {g.items.map((p) => (
                        <ProjectCard key={p.id} project={p} onContinue={handleContinue} onDelete={handleDelete} />
                      ))}
                    </div>
                  )}
                </section>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
