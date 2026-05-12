import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import {
  ArrowLeft, Loader2, Brain, Pin, PinOff, Archive, Search, Plus, X,
  TrendingUp, Calendar, User, Crown, Bot, Sparkles, Tag,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const SOURCE_META = {
  owner: { label: 'من المالك', icon: Crown, color: 'amber' },
  user: { label: 'من العملاء', icon: User, color: 'blue' },
  system: { label: 'تلقائي', icon: Bot, color: 'purple' },
};

export default function AdminLearning() {
  const nav = useNavigate();
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const [stats, setStats] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [filterSource, setFilterSource] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    if (!token) { nav('/login'); return; }
    load();
    // eslint-disable-next-line
  }, []);

  // Reload on filter change
  useEffect(() => {
    if (token) load();
    // eslint-disable-next-line
  }, [q, filterSource]);

  const load = async () => {
    setLoading(true);
    try {
      const [s, l] = await Promise.all([
        fetch(`${API}/api/autocoder/learning/stats`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
        fetch(`${API}/api/autocoder/learning/lessons?q=${encodeURIComponent(q)}&source=${filterSource}&limit=100`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      ]);
      if (s?.ok) setStats(s);
      if (l?.ok) setLessons(l.lessons || []);
    } catch (e) {
      toast.error('فشل التحميل');
    } finally {
      setLoading(false);
    }
  };

  const togglePin = async (lesson_id, currentlyPinned) => {
    try {
      await fetch(`${API}/api/autocoder/learning/lessons/${lesson_id}/pin`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ pinned: !currentlyPinned }),
      });
      toast.success(currentlyPinned ? 'فُك التثبيت' : '📌 ثُبّت');
      load();
    } catch (e) {
      toast.error('فشلت العملية');
    }
  };

  const archiveLesson = async (lesson_id) => {
    if (!window.confirm('هل تريد أرشفة هذا الدرس؟')) return;
    try {
      await fetch(`${API}/api/autocoder/learning/lessons/${lesson_id}/archive`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ archived: true }),
      });
      toast.success('أُرشف');
      load();
    } catch (e) {
      toast.error('فشل');
    }
  };

  if (loading && !stats) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <Loader2 className="w-7 h-7 animate-spin text-amber-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white" dir="rtl">
      <Toaster richColors position="top-center" />

      {/* Header */}
      <div className="border-b border-white/10 bg-gradient-to-l from-amber-500/10 to-transparent">
        <div className="max-w-6xl mx-auto px-4 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => nav('/admin')} className="p-2 rounded-lg hover:bg-white/10" data-testid="back-btn">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl md:text-2xl font-black flex items-center gap-2">
                <Brain className="w-6 h-6 text-amber-400" />
                نمو الذكاء — Learning Journal
              </h1>
              <p className="text-xs text-white/60 mt-0.5">كل ما يتعلّمه الذكاء يوماً بيوم من تفاعلاتك ومن العملاء</p>
            </div>
          </div>
          <button
            onClick={() => setShowAdd(true)}
            data-testid="add-lesson-btn"
            className="px-3 py-2 rounded-xl bg-amber-500 text-black font-bold text-sm hover:bg-amber-400 flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" /> أضف درساً يدوياً
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6">
        {/* Stats cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <StatCard icon={Brain} label="إجمالي الدروس" value={stats.total || 0} color="amber" />
            <StatCard icon={Pin} label="مثبّت" value={stats.pinned || 0} color="rose" />
            <StatCard icon={Calendar} label="اليوم" value={stats.today || 0} color="blue" />
            <StatCard icon={TrendingUp} label="من المالك" value={stats.by_source?.owner || 0} color="emerald" />
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-2 mb-5">
          <div className="relative flex-1">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="ابحث في الدروس..."
              data-testid="search-input"
              className="w-full bg-white/5 border border-white/10 rounded-xl pr-9 pl-3 py-2.5 text-sm focus:border-amber-400/50 focus:outline-none"
            />
          </div>
          <div className="flex gap-2">
            <FilterButton active={filterSource === ''} onClick={() => setFilterSource('')}>الكل</FilterButton>
            <FilterButton active={filterSource === 'owner'} onClick={() => setFilterSource('owner')}>👑 المالك</FilterButton>
            <FilterButton active={filterSource === 'user'} onClick={() => setFilterSource('user')}>👤 العملاء</FilterButton>
            <FilterButton active={filterSource === 'system'} onClick={() => setFilterSource('system')}>🤖 تلقائي</FilterButton>
          </div>
        </div>

        {/* Lessons list */}
        <div className="space-y-2.5">
          {lessons.length === 0 ? (
            <div className="text-center py-16 text-white/40">
              <Sparkles className="w-12 h-12 mx-auto mb-3 text-white/20" />
              <p className="text-sm">ما فيه دروس بعد. كل ما تكلّمت الذكاء وأنجز شي، راح يحفظ الدرس هنا تلقائياً.</p>
            </div>
          ) : (
            lessons.map(ls => (
              <LessonCard key={ls.id} lesson={ls} onPin={togglePin} onArchive={archiveLesson} />
            ))
          )}
        </div>
      </div>

      {/* Add lesson modal */}
      {showAdd && <AddLessonModal token={token} onClose={() => setShowAdd(false)} onAdded={load} />}
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }) {
  const colorMap = {
    amber: 'from-amber-500/20 to-orange-500/10 border-amber-400/30 text-amber-300',
    rose: 'from-rose-500/20 to-pink-500/10 border-rose-400/30 text-rose-300',
    blue: 'from-blue-500/20 to-cyan-500/10 border-blue-400/30 text-blue-300',
    emerald: 'from-emerald-500/20 to-green-500/10 border-emerald-400/30 text-emerald-300',
  };
  return (
    <div className={`bg-gradient-to-br ${colorMap[color]} border rounded-2xl p-4`}>
      <Icon className="w-5 h-5 mb-2" />
      <div className="text-2xl font-black mb-0.5">{value.toLocaleString('ar')}</div>
      <div className="text-xs text-white/60">{label}</div>
    </div>
  );
}

function FilterButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-2 rounded-xl text-xs font-bold transition ${
        active ? 'bg-amber-500 text-black' : 'bg-white/5 hover:bg-white/10 text-white/70'
      }`}
    >
      {children}
    </button>
  );
}

function LessonCard({ lesson, onPin, onArchive }) {
  const meta = SOURCE_META[lesson.source] || SOURCE_META.owner;
  const Icon = meta.icon;
  const colorMap = {
    amber: 'border-amber-400/30 bg-amber-500/[0.04]',
    blue: 'border-blue-400/30 bg-blue-500/[0.04]',
    purple: 'border-purple-400/30 bg-purple-500/[0.04]',
  };
  const created = lesson.created_at ? new Date(lesson.created_at).toLocaleString('ar-SA', {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  }) : '';

  return (
    <div
      data-testid={`lesson-${lesson.id}`}
      className={`border ${colorMap[meta.color]} rounded-2xl p-4 hover:border-white/20 transition relative ${
        lesson.pinned ? 'ring-1 ring-amber-400/30' : ''
      }`}
    >
      <div className="flex items-start gap-3">
        <div className={`w-9 h-9 rounded-xl bg-${meta.color}-500/15 border border-${meta.color}-400/30 flex items-center justify-center shrink-0`}>
          <Icon className={`w-4 h-4 text-${meta.color}-300`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-[10px] font-bold uppercase text-${meta.color}-300`}>
              {meta.label}
            </span>
            {lesson.pinned && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold flex items-center gap-1">
                <Pin className="w-2.5 h-2.5" /> مثبّت
              </span>
            )}
            {lesson.relevance_score > 1 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300">
                ⭐ {lesson.relevance_score}
              </span>
            )}
          </div>
          <h4 className="font-bold text-sm mb-1">{lesson.task_summary}</h4>
          <p className="text-sm text-white/75 leading-relaxed">{lesson.lesson}</p>
          {lesson.code_pattern && (
            <pre className="mt-2 bg-black/40 border border-white/5 rounded-lg p-2 text-[11px] text-amber-200 overflow-x-auto">
              {lesson.code_pattern}
            </pre>
          )}
          <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
            <div className="flex items-center gap-1.5 flex-wrap">
              {(lesson.tags || []).map(t => (
                <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/60 flex items-center gap-1">
                  <Tag className="w-2.5 h-2.5" />{t}
                </span>
              ))}
            </div>
            <span className="text-[10px] text-white/40">{created}</span>
          </div>
        </div>
      </div>
      <div className="absolute top-3 left-3 flex gap-1">
        <button
          onClick={() => onPin(lesson.id, lesson.pinned)}
          data-testid={`pin-${lesson.id}`}
          className="p-1.5 rounded-lg hover:bg-white/10 text-white/50 hover:text-amber-300 transition"
          title={lesson.pinned ? 'فك التثبيت' : 'تثبيت'}
        >
          {lesson.pinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
        </button>
        <button
          onClick={() => onArchive(lesson.id)}
          data-testid={`archive-${lesson.id}`}
          className="p-1.5 rounded-lg hover:bg-white/10 text-white/50 hover:text-rose-300 transition"
          title="أرشفة"
        >
          <Archive className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

function AddLessonModal({ token, onClose, onAdded }) {
  const [task_summary, setSummary] = useState('');
  const [lesson, setLesson] = useState('');
  const [tags, setTags] = useState('');
  const [code, setCode] = useState('');
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!task_summary.trim() || !lesson.trim()) {
      toast.error('املأ الحقلين المطلوبين');
      return;
    }
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/autocoder/learning/lessons`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_summary, lesson,
          tags: tags.split(',').map(t => t.trim()).filter(Boolean),
          code_pattern: code || null,
        }),
      });
      const j = await r.json();
      if (j.ok) {
        toast.success('📚 درس مسجّل');
        onAdded();
        onClose();
      } else {
        toast.error(j.error || 'فشل');
      }
    } catch (e) {
      toast.error('خطأ شبكة');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      onClick={e => e.target === e.currentTarget && onClose()}
      data-testid="add-lesson-modal"
      className="fixed inset-0 z-[80] bg-black/85 backdrop-blur-sm flex items-start md:items-center justify-center p-4 overflow-y-auto"
    >
      <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl max-w-xl w-full my-8 overflow-hidden" dir="rtl">
        <div className="flex items-center justify-between p-4 border-b border-white/10 bg-amber-500/[0.05]">
          <h3 className="font-black text-base flex items-center gap-2">
            <Plus className="w-5 h-5 text-amber-400" /> أضف درساً للذكاء
          </h3>
          <button onClick={onClose} className="p-1.5 rounded-full hover:bg-white/10" data-testid="close-add-modal">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5 space-y-3">
          <div>
            <label className="text-xs font-bold mb-1 block text-white/70">ملخّص المهمة *</label>
            <input
              value={task_summary}
              onChange={e => setSummary(e.target.value)}
              data-testid="summary-input"
              placeholder="مثال: إصلاح رفع الصور في الشات"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-400/50 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs font-bold mb-1 block text-white/70">الدرس المستفاد *</label>
            <textarea
              value={lesson}
              onChange={e => setLesson(e.target.value)}
              data-testid="lesson-input"
              placeholder="مثال: لما ترفع ملف للـbackend استخدم FormData (لا تستخدم JSON)..."
              rows={4}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-400/50 focus:outline-none resize-none"
            />
          </div>
          <div>
            <label className="text-xs font-bold mb-1 block text-white/70">Tags (اختياري، مفصولة بفاصلة)</label>
            <input
              value={tags}
              onChange={e => setTags(e.target.value)}
              data-testid="tags-input"
              placeholder="frontend, bug-fix, upload"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-400/50 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs font-bold mb-1 block text-white/70">مثال كود (اختياري)</label>
            <textarea
              value={code}
              onChange={e => setCode(e.target.value)}
              data-testid="code-input"
              placeholder="const formData = new FormData(); ..."
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono focus:border-amber-400/50 focus:outline-none resize-none"
            />
          </div>
          <button
            onClick={save}
            disabled={saving}
            data-testid="save-lesson-btn"
            className="w-full bg-amber-500 hover:bg-amber-400 text-black font-bold py-2.5 rounded-xl disabled:opacity-50 transition flex items-center justify-center gap-2"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            احفظ الدرس
          </button>
        </div>
      </div>
    </div>
  );
}
