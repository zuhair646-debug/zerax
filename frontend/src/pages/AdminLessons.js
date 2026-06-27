/**
 * AdminLessons — operator-only UI for managing the AI's learning store.
 *
 * Lets the owner:
 *   • View all lessons sorted by priority + effectiveness
 *   • Add a critical-priority lesson (always-on, top of every prompt)
 *   • Edit / delete lessons
 *   • View the Auto-E1 review audit log
 *   • Track effectiveness — weak lessons (eff < 0.5) get a red badge so the
 *     owner can rewrite or delete them.
 */
import { useState, useEffect, useCallback } from 'react';
import { Brain, Plus, Trash2, Edit3, AlertCircle, Loader2, RefreshCw, Save, X } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const PRIORITY = {
  critical: { color: 'bg-red-500/15 border-red-500/40 text-red-200', label: '🔴 حرج (دائم)' },
  high: { color: 'bg-orange-500/15 border-orange-500/40 text-orange-200', label: '🟠 عالٍ' },
  medium: { color: 'bg-amber-500/15 border-amber-500/40 text-amber-200', label: '🟡 متوسط' },
  low: { color: 'bg-zinc-500/15 border-zinc-500/40 text-zinc-300', label: '⚪ منخفض' },
};

const SOURCE_LABEL = {
  supervisor: 'مراقب تلقائي',
  honesty: 'فحص الصدق',
  auto_e1: '🤝 مراجعة E1',
  manual_operator: '✍️ يدوي',
};

export default function AdminLessons() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newGuidance, setNewGuidance] = useState('');
  const [newPriority, setNewPriority] = useState('critical');
  const [creating, setCreating] = useState(false);
  const [editId, setEditId] = useState(null);
  const [editText, setEditText] = useState('');

  const token = (() => {
    try {
      return localStorage.getItem('token') || localStorage.getItem('access_token');
    } catch {
      return null;
    }
  })();

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/admin/lessons?limit=200`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setItems(d.items || []);
    } catch (e) {
      toast.error(`فشل التحميل: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (newGuidance.trim().length < 8) {
      toast.error('الدرس قصير جداً (8 أحرف على الأقل)');
      return;
    }
    setCreating(true);
    try {
      const r = await fetch(`${API}/api/admin/lessons`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          guidance_ar: newGuidance.trim(),
          priority: newPriority,
          pattern: 'manual_owner_rule',
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      toast.success('✅ تم حفظ الدرس — يطبّق فوراً على كل المشاريع');
      setNewGuidance('');
      setShowCreate(false);
      load();
    } catch (e) {
      toast.error(`فشل الحفظ: ${e.message}`);
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm('احذف هذا الدرس نهائياً؟')) return;
    try {
      const r = await fetch(`${API}/api/admin/lessons/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      toast.success('🗑️ تم الحذف');
      load();
    } catch (e) {
      toast.error(`فشل الحذف: ${e.message}`);
    }
  };

  const startEdit = (item) => {
    setEditId(item.id);
    setEditText(item.guidance_ar || '');
  };

  const saveEdit = async () => {
    if (editText.trim().length < 8) {
      toast.error('الدرس قصير جداً');
      return;
    }
    try {
      const fd = new FormData();
      fd.append('guidance_ar', editText.trim());
      const r = await fetch(`${API}/api/admin/lessons/${editId}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      toast.success('✅ تم التعديل');
      setEditId(null);
      load();
    } catch (e) {
      toast.error(`فشل التعديل: ${e.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white p-6" dir="rtl" data-testid="admin-lessons">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Brain className="w-7 h-7 text-cyan-400" />
            <h1 className="text-2xl font-black">دروس الذكاء الصناعي</h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-300">
              {items.length} درس
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCreate((v) => !v)}
              data-testid="create-lesson-btn"
              className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-sky-600 hover:from-cyan-400 hover:to-sky-500 text-black font-bold text-sm flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              درس جديد
            </button>
            <button
              onClick={load}
              data-testid="refresh-lessons"
              className="p-1.5 rounded-lg border border-white/10 hover:border-white/30"
              title="تحديث"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Create form */}
        {showCreate && (
          <div className="rounded-xl border border-cyan-400/40 bg-cyan-500/5 p-4 mb-5" data-testid="create-lesson-form">
            <h3 className="text-sm font-bold mb-3 text-cyan-200">إضافة درس جديد</h3>
            <textarea
              value={newGuidance}
              onChange={(e) => setNewGuidance(e.target.value)}
              rows={4}
              placeholder="مثال: قبل النشر، تحقّق من توكن العميل عبر طلب الـ credential. لا تكرر الطلب أكثر من مرة واحدة."
              data-testid="lesson-text-input"
              className="w-full bg-black/40 border border-cyan-500/30 rounded-lg px-3 py-2.5 text-sm text-cyan-50 placeholder:text-zinc-500 outline-none focus:border-cyan-300 mb-3"
            />
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <select
                value={newPriority}
                onChange={(e) => setNewPriority(e.target.value)}
                data-testid="lesson-priority-select"
                className="bg-black/40 border border-cyan-500/30 rounded-lg px-2.5 py-1.5 text-sm text-cyan-100 outline-none"
              >
                {Object.entries(PRIORITY).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setShowCreate(false); setNewGuidance(''); }}
                  className="px-3 py-1.5 rounded-lg border border-zinc-700 hover:bg-zinc-800/60 text-zinc-300 text-sm"
                >
                  إلغاء
                </button>
                <button
                  onClick={create}
                  disabled={creating || newGuidance.trim().length < 8}
                  data-testid="lesson-save-btn"
                  className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-sky-600 hover:from-cyan-400 hover:to-sky-500 disabled:opacity-50 text-black font-bold text-sm flex items-center gap-1.5"
                >
                  {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  احفظ
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Lessons list */}
        {loading && items.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-zinc-500">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-12 text-zinc-500">
            <Brain className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">ما في دروس بعد.</p>
            <p className="text-xs mt-1 text-zinc-600">الدروس تتراكم تلقائياً مع استخدام الذكاء، أو أضف درساً يدوياً بزر «درس جديد».</p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {items.map((it) => {
              const pri = PRIORITY[it.priority] || PRIORITY.medium;
              const eff = it.effectiveness ?? 1;
              const weak = eff < 0.5 && (it.injection_count || 0) >= 3;
              const isEditing = editId === it.id;
              return (
                <div
                  key={it.id}
                  data-testid={`lesson-${it.id}`}
                  className={`relative rounded-xl border p-3 ${pri.color}`}
                >
                  <div className="flex items-start gap-3">
                    <Brain className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-wide">{pri.label}</span>
                        <span className="text-[10px] bg-black/30 px-1.5 py-0.5 rounded">
                          {SOURCE_LABEL[it.source] || it.source || 'auto'}
                        </span>
                        {(it.injection_count || 0) > 0 && (
                          <span className="text-[10px] bg-black/30 px-1.5 py-0.5 rounded" title="عدد مرات الحقن">
                            استُخدم {it.injection_count}×
                          </span>
                        )}
                        {(it.injection_count || 0) >= 3 && (
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                              weak ? 'bg-red-500/30 text-red-200' : 'bg-emerald-500/20 text-emerald-200'
                            }`}
                            title="فعالية = 1 - تكرار الخطأ / (مرات الحقن + 1)"
                          >
                            فعالية {Math.round(eff * 100)}%
                          </span>
                        )}
                        {weak && (
                          <span className="text-[10px] bg-red-500/30 text-red-200 px-1.5 py-0.5 rounded font-bold flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" /> يحتاج إعادة صياغة
                          </span>
                        )}
                      </div>
                      {isEditing ? (
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          rows={3}
                          data-testid={`edit-textarea-${it.id}`}
                          className="w-full bg-black/40 border border-cyan-500/30 rounded-lg px-2 py-1.5 text-sm text-cyan-50 outline-none focus:border-cyan-300 mt-1"
                        />
                      ) : (
                        <p className="text-sm leading-relaxed whitespace-pre-wrap" data-testid={`lesson-text-${it.id}`}>
                          {it.guidance_ar}
                        </p>
                      )}
                      {it.pattern && !isEditing && (
                        <p className="text-[10px] text-zinc-400 mt-1.5">
                          نمط: <code>{it.pattern}</code>
                          {it.ts && <> · {new Date(it.ts).toLocaleString('ar-SA')}</>}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col gap-1">
                      {isEditing ? (
                        <>
                          <button
                            onClick={saveEdit}
                            data-testid={`save-edit-${it.id}`}
                            className="px-2 py-1 rounded text-[10px] font-bold bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-200 flex items-center gap-1"
                          >
                            <Save className="w-3 h-3" /> احفظ
                          </button>
                          <button
                            onClick={() => setEditId(null)}
                            className="px-2 py-1 rounded text-[10px] font-bold bg-zinc-700/40 hover:bg-zinc-700/60 text-zinc-300 flex items-center gap-1"
                          >
                            <X className="w-3 h-3" /> إلغاء
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => startEdit(it)}
                            data-testid={`edit-${it.id}`}
                            className="px-2 py-1 rounded text-[10px] font-bold bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-200 flex items-center gap-1"
                          >
                            <Edit3 className="w-3 h-3" /> عدّل
                          </button>
                          <button
                            onClick={() => remove(it.id)}
                            data-testid={`delete-${it.id}`}
                            className="px-2 py-1 rounded text-[10px] font-bold bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 text-red-200 flex items-center gap-1"
                          >
                            <Trash2 className="w-3 h-3" /> احذف
                          </button>
                        </>
                      )}
                    </div>
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
