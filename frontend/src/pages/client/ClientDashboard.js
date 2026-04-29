import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { CoursesTab, MembershipsTab, EventsTab, DriverAnalyticsTab } from './Phase2Tabs';

import {
  LogIn, Eye, EyeOff, LogOut, ExternalLink, Users, MessageSquare, BarChart3,
  Edit3, Save, X, RefreshCw, Check, Key, CheckCircle2, Copy, Lock, MapPin,
  Palette, History, RotateCcw, Trash2, Image as ImageIcon,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const authH = (token) => ({ Authorization: `ClientToken ${token}` });

/* ================================================================
   LOGIN — terse & friendly
   ================================================================ */
function LoginCard({ slug, onLoggedIn }) {
  const [pwd, setPwd] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [info, setInfo] = useState(null); // project info fetched by slug

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const r = await fetch(`${API}/api/websites/public/${slug}/info`);
        if (r.ok) {
          const d = await r.json();
          if (mounted) setInfo(d);
        }
      } catch (_) {}
    })();
    return () => { mounted = false; };
  }, [slug]);

  const submit = async (e) => {
    e?.preventDefault();
    if (!pwd) return;
    setBusy(true); setErr('');
    try {
      const r = await fetch(`${API}/api/websites/client/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, password: pwd }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(d.detail || 'فشل تسجيل الدخول'); return; }
      localStorage.setItem(`zx_client_token_${slug}`, d.token);
      onLoggedIn(d.token);
      toast.success(`مرحباً بك في ${d.name}`);
    } catch (_) { setErr('تعذّر الاتصال'); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#050815] via-[#0b0f1f] to-[#050815] flex items-center justify-center p-4" dir="rtl">
      <div className="w-full max-w-md bg-[#0e1128]/90 backdrop-blur border border-yellow-500/20 rounded-3xl p-6 md:p-8 shadow-[0_30px_80px_rgba(234,179,8,0.1)]" data-testid="client-login-card">
        <div className="flex items-center justify-center w-14 h-14 bg-gradient-to-br from-yellow-500 to-orange-500 rounded-2xl mb-4 mx-auto shadow-xl">
          <Lock className="w-7 h-7 text-black" />
        </div>
        <h1 className="text-2xl font-bold text-center mb-1 text-white" data-testid="client-login-title">لوحة تحكم موقعك</h1>
        <p className="text-sm text-center opacity-60 text-white mb-6">
          {info?.name ? `${info.name} — إدارة خاصة بالعميل` : 'سجّل دخولك لإدارة موقعك'}
        </p>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="text-xs opacity-70 block mb-1 text-white">اسم الموقع</label>
            <div className="px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white/70 text-sm font-mono" data-testid="client-login-slug">{slug}</div>
          </div>
          <div>
            <label className="text-xs opacity-70 block mb-1 text-white">كلمة المرور</label>
            <div className="relative">
              <input
                type={showPwd ? 'text' : 'password'}
                value={pwd}
                onChange={(e) => setPwd(e.target.value)}
                className="w-full px-3 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-yellow-500"
                placeholder="••••••••"
                autoFocus
                data-testid="client-login-password"
              />
              <button type="button" onClick={() => setShowPwd((v) => !v)} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/60 hover:text-white" data-testid="client-login-toggle-pwd">
                {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          {err && <div className="text-red-400 text-xs bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2" data-testid="client-login-error">{err}</div>}
          <button
            type="submit"
            disabled={busy || !pwd}
            className="w-full py-3 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-xl font-bold flex items-center justify-center gap-2 disabled:opacity-50 hover:shadow-xl transition"
            data-testid="client-login-submit"
          >
            {busy ? <RefreshCw className="w-4 h-4 animate-spin" /> : <LogIn className="w-4 h-4" />}
            {busy ? 'جاري الدخول...' : 'دخول'}
          </button>
        </form>
        <div className="mt-4 text-center text-xs text-white/40">كلمة المرور حصلت عليها من صانع الموقع. للاستفسار تواصل معه.</div>
      </div>
    </div>
  );
}

/* ================================================================
   STATS BAR
   ================================================================ */
function Stat({ icon: Icon, label, value, accent = 'text-yellow-400' }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-4 flex items-center gap-3" data-testid={`stat-${label}`}>
      <div className={`w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center ${accent}`}><Icon className="w-5 h-5" /></div>
      <div>
        <div className="text-[11px] opacity-60">{label}</div>
        <div className="text-xl font-black">{value}</div>
      </div>
    </div>
  );
}

/* ================================================================
   SECTIONS EDITOR — inline text patches
   ================================================================ */
function SectionsEditor({ project, token, onUpdated }) {
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState({});
  const [busy, setBusy] = useState(false);
  const [variantFor, setVariantFor] = useState(null); // section being styled
  const [catalog, setCatalog] = useState({});

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/websites/section-variants/catalog`);
        const d = await r.json();
        setCatalog(d.catalog || {});
      } catch (_) {}
    })();
  }, []);

  const startEdit = (s) => {
    setEditingId(s.id);
    setDraft({ ...(s.data || {}) });
  };
  const cancel = () => { setEditingId(null); setDraft({}); };

  const save = async (s) => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/sections/${s.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ data: draft }),
      });
      if (!r.ok) throw new Error();
      toast.success('تم الحفظ');
      setEditingId(null);
      onUpdated();
    } catch (_) { toast.error('فشل الحفظ'); }
    finally { setBusy(false); }
  };

  const toggleVisible = async (s) => {
    setBusy(true);
    try {
      await fetch(`${API}/api/websites/client/sections/${s.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ visible: !(s.visible !== false) }),
      });
      onUpdated();
    } catch (_) {}
    finally { setBusy(false); }
  };

  const applyVariant = async (s, variantId) => {
    setBusy(true);
    try {
      await fetch(`${API}/api/websites/client/sections/${s.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ data: { style: variantId } }),
      });
      toast.success('تم تغيير الشكل — شاهد الموقع للمعاينة');
      setVariantFor(null);
      onUpdated();
    } catch (_) { toast.error('فشل التطبيق'); }
    finally { setBusy(false); }
  };

  const EDITABLE_FIELDS = ['title', 'subtitle', 'text', 'cta_text', 'brand', 'description', 'address'];

  return (
    <div className="space-y-2" data-testid="sections-editor">
      {(project?.sections || []).map((s) => {
        const data = s.data || {};
        const isEditing = editingId === s.id;
        const editableKeys = EDITABLE_FIELDS.filter((k) => k in data || ['hero', 'about', 'cta', 'footer', 'contact', 'banner'].includes(s.type));
        return (
          <div key={s.id} className={`rounded-xl border p-3 md:p-4 ${isEditing ? 'bg-yellow-500/5 border-yellow-500/40' : 'bg-white/3 border-white/10'}`} data-testid={`section-row-${s.type}`}>
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 bg-yellow-500/20 text-yellow-300 rounded-full font-bold">{s.type}</span>
                <span className="text-sm font-bold">{data.title || data.brand || '—'}</span>
                {s.visible === false && <span className="text-[10px] px-1.5 py-0.5 bg-red-500/20 text-red-300 rounded">مخفي</span>}
              </div>
              <div className="flex gap-1">
                {catalog[s.type] && (
                  <button onClick={() => setVariantFor(s)} className="p-1.5 hover:bg-white/10 rounded-lg text-purple-300" title="غيّر الشكل" data-testid={`variant-btn-${s.type}`}>
                    <Palette className="w-4 h-4" />
                  </button>
                )}
                <button onClick={() => toggleVisible(s)} disabled={busy} className="p-1.5 hover:bg-white/10 rounded-lg text-xs" title={s.visible === false ? 'إظهار' : 'إخفاء'} data-testid={`toggle-visible-${s.type}`}>
                  {s.visible === false ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                </button>
                {!isEditing ? (
                  <button onClick={() => startEdit(s)} className="p-1.5 hover:bg-white/10 rounded-lg text-yellow-400" data-testid={`edit-btn-${s.type}`}>
                    <Edit3 className="w-4 h-4" />
                  </button>
                ) : (
                  <>
                    <button onClick={cancel} className="p-1.5 hover:bg-white/10 rounded-lg text-red-400" data-testid={`cancel-edit-${s.type}`}>
                      <X className="w-4 h-4" />
                    </button>
                    <button onClick={() => save(s)} disabled={busy} className="p-1.5 bg-green-500/20 hover:bg-green-500/30 rounded-lg text-green-300" data-testid={`save-edit-${s.type}`}>
                      {busy ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    </button>
                  </>
                )}
              </div>
            </div>
            {isEditing && (
              <div className="mt-3 space-y-2" data-testid={`edit-form-${s.type}`}>
                {editableKeys.map((k) => (
                  <div key={k}>
                    <label className="text-[11px] opacity-60 block mb-1">{k}</label>
                    <input
                      value={draft[k] ?? ''}
                      onChange={(e) => setDraft({ ...draft, [k]: e.target.value })}
                      className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-yellow-500"
                      data-testid={`edit-input-${s.type}-${k}`}
                    />
                  </div>
                ))}
                {editableKeys.length === 0 && <div className="text-xs opacity-60">هذا القسم يحتاج تعديل متقدم — تواصل مع صانع الموقع.</div>}
              </div>
            )}
          </div>
        );
      })}

      {/* 🎨 Variant picker modal */}
      {variantFor && (() => {
        const entry = catalog[variantFor.type];
        const currentStyle = (variantFor.data || {}).style || entry?.variants?.[0]?.id;
        return (
          <div className="fixed inset-0 z-[10000] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setVariantFor(null)} data-testid="variant-modal">
            <div onClick={(e) => e.stopPropagation()} className="bg-[#0e1128] border border-purple-500/30 rounded-2xl p-5 md:p-6 max-w-2xl w-full shadow-[0_30px_80px_rgba(168,85,247,0.2)]">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold flex items-center gap-2"><Palette className="w-5 h-5 text-purple-400" />شكل قسم "{entry?.label || variantFor.type}"</h3>
                <button onClick={() => setVariantFor(null)} className="p-1 hover:bg-white/10 rounded-lg"><X className="w-5 h-5" /></button>
              </div>
              <div className="text-xs opacity-70 mb-4">اختر الشكل الذي يعجبك — يُطبَّق فوراً على موقعك (وتنحفظ نسخة قبل التغيير تقدر ترجعلها).</div>
              <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">
                {(entry?.variants || []).map((v) => {
                  const active = v.id === currentStyle;
                  return (
                    <button
                      key={v.id}
                      onClick={() => applyVariant(variantFor, v.id)}
                      disabled={busy}
                      className={`text-right p-4 rounded-xl border-2 transition ${active ? 'bg-purple-500/20 border-purple-500 shadow-[0_0_20px_rgba(168,85,247,0.3)]' : 'bg-white/3 border-white/10 hover:border-purple-400/50 hover:bg-white/6'}`}
                      data-testid={`variant-${variantFor.type}-${v.id}`}
                    >
                      <div className="font-bold mb-1 flex items-center gap-2">{v.label} {active && <Check className="w-3.5 h-3.5 text-purple-400" />}</div>
                      <div className="text-xs opacity-70 leading-relaxed">{v.description}</div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}

/* ================================================================
   MESSAGES INBOX
   ================================================================ */
function MessagesTab({ token }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/client/messages`, { headers: authH(token) });
      const d = await r.json();
      setMessages(d.messages || []);
    } catch (_) {} finally { setLoading(false); }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const markRead = async (id) => {
    try {
      await fetch(`${API}/api/websites/client/messages/${id}/read`, { method: 'POST', headers: authH(token) });
      load();
    } catch (_) {}
  };

  return (
    <div data-testid="messages-tab">
      {loading ? (
        <div className="text-center py-10 opacity-60">جاري التحميل...</div>
      ) : messages.length === 0 ? (
        <div className="text-center py-12 bg-white/3 border border-dashed border-white/15 rounded-2xl">
          <MessageSquare className="w-10 h-10 mx-auto mb-2 opacity-30" />
          <div className="text-sm opacity-60">لا توجد رسائل من عملائك بعد</div>
          <div className="text-xs opacity-40 mt-1">الرسائل المرسلة عبر نموذج "تواصل معنا" ستظهر هنا</div>
        </div>
      ) : (
        <div className="space-y-2">
          {messages.map((m) => (
            <div key={m.id} className={`rounded-xl border p-3 ${m.read ? 'bg-white/3 border-white/10' : 'bg-yellow-500/5 border-yellow-500/30'}`} data-testid={`message-${m.id}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold">{m.name}</span>
                    {m.phone && <span className="text-xs opacity-70">📞 {m.phone}</span>}
                    {m.email && <span className="text-xs opacity-70">✉️ {m.email}</span>}
                    {!m.read && <span className="text-[10px] px-1.5 py-0.5 bg-yellow-500 text-black rounded-full font-black">جديد</span>}
                  </div>
                  <div className="text-sm mt-1 opacity-90 whitespace-pre-wrap">{m.message}</div>
                  <div className="text-[10px] opacity-50 mt-1">{new Date(m.at).toLocaleString('ar-SA')}</div>
                </div>
                {!m.read && (
                  <button onClick={() => markRead(m.id)} className="p-1.5 hover:bg-white/10 rounded-lg" title="تمّت القراءة" data-testid={`mark-read-${m.id}`}>
                    <Check className="w-4 h-4 text-green-400" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ================================================================
   CHANGE PASSWORD
   ================================================================ */
function PasswordTab({ token }) {
  const [oldP, setOldP] = useState('');
  const [newP, setNewP] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ old_password: oldP, new_password: newP }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      toast.success('تم تغيير كلمة المرور');
      setOldP(''); setNewP('');
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  return (
    <form onSubmit={submit} className="max-w-sm space-y-3" data-testid="password-tab">
      <div>
        <label className="text-xs opacity-70 block mb-1">كلمة المرور الحالية</label>
        <input type="password" value={oldP} onChange={(e) => setOldP(e.target.value)} className="w-full px-3 py-2.5 bg-white/5 border border-white/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500" required data-testid="password-old" />
      </div>
      <div>
        <label className="text-xs opacity-70 block mb-1">كلمة مرور جديدة (6 أحرف على الأقل)</label>
        <input type="password" value={newP} onChange={(e) => setNewP(e.target.value)} minLength={6} className="w-full px-3 py-2.5 bg-white/5 border border-white/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500" required data-testid="password-new" />
      </div>
      <button type="submit" disabled={busy} className="w-full py-2.5 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-xl font-bold disabled:opacity-50 flex items-center justify-center gap-2" data-testid="password-submit">
        <Key className="w-4 h-4" />{busy ? 'جاري الحفظ...' : 'تغيير كلمة المرور'}
      </button>
    </form>
  );
}

/* ================================================================
   SUPPORT TICKETS TAB
   ================================================================ */
function SupportTab({ token }) {
  const [tickets, setTickets] = useState([]);
  const [form, setForm] = useState({ subject: '', description: '', category: 'general' });
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/websites/client/support-tickets`, { headers: authH(token) });
      const d = await r.json();
      setTickets(d.tickets || []);
    } catch (_) {}
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.subject.trim() || !form.description.trim()) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/support-tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify(form),
      });
      if (!r.ok) throw new Error();
      toast.success('✅ تم إرسال طلب الدعم — سيتم التواصل معك');
      setForm({ subject: '', description: '', category: 'general' });
      setShowForm(false);
      load();
    } catch (_) { toast.error('فشل الإرسال'); }
    finally { setBusy(false); }
  };

  const CATEGORIES = [
    { id: 'general',  label: '💬 استفسار عام' },
    { id: 'bug',      label: '🐛 خطأ / مشكلة' },
    { id: 'content',  label: '📝 تعديل محتوى' },
    { id: 'design',   label: '🎨 تعديل تصميم' },
    { id: 'other',    label: '❓ أخرى' },
  ];

  return (
    <div data-testid="support-tab">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs opacity-70">{tickets.length} طلب سابق</div>
        {!showForm && (
          <button onClick={() => setShowForm(true)} className="px-3 py-1.5 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-lg text-xs font-black" data-testid="new-ticket-btn">
            + طلب دعم جديد
          </button>
        )}
      </div>
      {showForm && (
        <form onSubmit={submit} className="bg-white/5 border border-yellow-500/30 rounded-xl p-3 mb-3 space-y-2" data-testid="ticket-form">
          <div>
            <label className="text-[11px] opacity-70 block mb-1">نوع الطلب</label>
            <div className="flex flex-wrap gap-1">
              {CATEGORIES.map((c) => (
                <button type="button" key={c.id} onClick={() => setForm({ ...form, category: c.id })}
                  className={`px-2 py-1 rounded-full text-[10px] font-bold border ${form.category === c.id ? 'bg-yellow-500 text-black border-yellow-500' : 'bg-white/5 border-white/15'}`}>
                  {c.label}
                </button>
              ))}
            </div>
          </div>
          <input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="عنوان مختصر" className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" required data-testid="ticket-subject" />
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="اشرح المطلوب بالتفصيل..." rows={4} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" required data-testid="ticket-description" />
          <div className="flex gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="flex-1 py-2 bg-white/10 rounded-lg text-xs font-bold">إلغاء</button>
            <button type="submit" disabled={busy} className="flex-[2] py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-lg text-xs font-black disabled:opacity-50" data-testid="submit-ticket">
              {busy ? 'جاري الإرسال...' : '📤 إرسال الطلب'}
            </button>
          </div>
        </form>
      )}
      {tickets.length === 0 && !showForm ? (
        <div className="text-center py-10 bg-white/3 border border-dashed border-white/15 rounded-2xl">
          <div className="text-sm opacity-60">لا توجد طلبات دعم بعد</div>
          <div className="text-xs opacity-40 mt-1">اضغط "طلب دعم جديد" لتسجيل ملاحظة أو طلب تعديل</div>
        </div>
      ) : (
        <div className="space-y-2">
          {tickets.map((t) => (
            <div key={t.id} className="bg-white/5 border border-white/10 rounded-xl p-3" data-testid={`ticket-${t.id}`}>
              <div className="flex items-center justify-between gap-2">
                <div className="font-bold text-sm flex items-center gap-2">
                  {t.category === 'chatbot_handoff' && <span title="من المساعد الذكي">🤖</span>}
                  {t.subject}
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${t.status === 'open' ? 'bg-yellow-500/20 text-yellow-300' : 'bg-green-500/20 text-green-300'}`}>
                  {t.status === 'open' ? (t.reply ? '💬 تم الرد' : '⏳ قيد المراجعة') : '✓ منتهي'}
                </span>
              </div>
              <div className="text-xs opacity-80 mt-1 whitespace-pre-wrap">{t.description}</div>
              <div className="text-[10px] opacity-50 mt-1">{new Date(t.at).toLocaleString('ar-SA')} · {t.category}</div>
              {t.whatsapp && (t.whatsapp.reply_to_customer_link || t.whatsapp.owner_alert_link) && (
                <div className="mt-2 flex flex-wrap gap-2" data-testid={`ticket-wa-${t.id}`}>
                  {t.whatsapp.reply_to_customer_link && (
                    <a
                      href={t.whatsapp.reply_to_customer_link}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 rounded-lg text-xs font-bold text-emerald-200"
                      data-testid={`wa-reply-${t.id}`}
                    >
                      📲 ردّ على الزبون عبر واتساب
                    </a>
                  )}
                  {t.customer?.contact && !t.whatsapp.reply_to_customer_link && (
                    <span className="text-[10px] opacity-60">رقم الزبون غير صالح للواتساب: {t.customer.contact}</span>
                  )}
                </div>
              )}
              {t.reply && (
                <div className="mt-2 p-2 bg-green-500/10 border border-green-500/30 rounded-lg" data-testid={`ticket-reply-${t.id}`}>
                  <div className="text-[10px] font-bold text-green-300 mb-1">💬 رد المالك:</div>
                  <div className="text-xs whitespace-pre-wrap">{t.reply}</div>
                  {t.replied_at && <div className="text-[9px] opacity-50 mt-1">{new Date(t.replied_at).toLocaleString('ar-SA')}</div>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ================================================================
   ORDERS TAB — owner views & manages orders from their site
   ================================================================ */
function OrdersTab({ token }) {
  const [orders, setOrders] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [oR, dR] = await Promise.all([
        fetch(`${API}/api/websites/client/orders${filter ? `?status=${filter}` : ''}`, { headers: authH(token) }),
        fetch(`${API}/api/websites/client/drivers`, { headers: authH(token) }),
      ]);
      const oD = await oR.json(); const dD = await dR.json();
      setOrders(oD.orders || []); setDrivers(dD.drivers || []);
    } catch (_) {} finally { setLoading(false); }
  }, [token, filter]);
  useEffect(() => { load(); }, [load]);

  const setStatus = async (id, status, driverId = null) => {
    try {
      const r = await fetch(`${API}/api/websites/client/orders/${id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ status, driver_id: driverId }),
      });
      const d = await r.json();
      toast.success('تم التحديث');
      // 🆕 auto-open WhatsApp link if present
      if (d.whatsapp_link) window.open(d.whatsapp_link, '_blank');
      load();
    } catch (_) { toast.error('فشل'); }
  };

  // 🆕 Save tracking number (independent of status changes)
  const saveTracking = async (id, currentStatus, tracking_number) => {
    try {
      const r = await fetch(`${API}/api/websites/client/orders/${id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ status: currentStatus, tracking_number }),
      });
      const d = await r.json();
      toast.success('✅ تم حفظ رقم التتبع');
      // 🆕 Auto-open WhatsApp to notify the customer with the tracking link
      if (d.whatsapp_link && tracking_number) {
        window.open(d.whatsapp_link, '_blank');
      }
      load();
    } catch (_) { toast.error('فشل'); }
  };

  const STATUS_LABELS = { pending: '⏳ قيد المراجعة', accepted: '✓ مقبول', preparing: '👨‍🍳 قيد التحضير', ready: '📦 جاهز', on_the_way: '🛵 في الطريق', delivered: '✅ تم التوصيل', cancelled: '❌ ملغي' };
  const STATUS_COLORS = { pending: 'bg-yellow-500/20 text-yellow-300', accepted: 'bg-blue-500/20 text-blue-300', preparing: 'bg-orange-500/20 text-orange-300', ready: 'bg-purple-500/20 text-purple-300', on_the_way: 'bg-cyan-500/20 text-cyan-300', delivered: 'bg-green-500/20 text-green-300', cancelled: 'bg-red-500/20 text-red-300' };

  return (
    <div data-testid="orders-tab">
      <div className="flex gap-1 flex-wrap mb-3">
        {['', 'pending', 'accepted', 'preparing', 'on_the_way', 'delivered', 'cancelled'].map((s) => (
          <button key={s || 'all'} onClick={() => setFilter(s)} className={`text-[11px] px-2.5 py-1 rounded-full font-bold ${filter === s ? 'bg-yellow-500 text-black' : 'bg-white/5 hover:bg-white/10'}`} data-testid={`filter-${s || 'all'}`}>
            {s ? STATUS_LABELS[s] : 'الكل'}
          </button>
        ))}
      </div>
      {loading ? <div className="text-center py-10 opacity-60">جاري التحميل...</div> : orders.length === 0 ? (
        <div className="text-center py-12 bg-white/3 border border-dashed border-white/15 rounded-2xl">
          <div className="text-4xl mb-2">🛒</div>
          <div className="text-sm opacity-60">لا توجد طلبات بعد</div>
          <div className="text-xs opacity-40 mt-1">طلبات عملاء الموقع ستظهر هنا مباشرة</div>
        </div>
      ) : (
        <div className="space-y-2">
          {orders.map((o) => {
            const drv = drivers.find((d) => d.id === o.driver_id);
            return (
              <div key={o.id} className="bg-white/5 border border-white/10 rounded-xl p-3" data-testid={`order-${o.id}`}>
                <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm">#{o.id.slice(0, 8)}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${STATUS_COLORS[o.status] || 'bg-white/10'}`}>{STATUS_LABELS[o.status] || o.status}</span>
                  </div>
                  <div className="text-xs font-black text-yellow-400">{o.total} ر.س</div>
                </div>
                <div className="text-xs opacity-90 mb-1">{o.customer_name} · 📞 {o.customer_phone}</div>
                <div className="text-[11px] opacity-70 mb-1">📍 {o.address || (o.lat ? `(${o.lat.toFixed(4)}, ${o.lng.toFixed(4)})` : 'لا عنوان')}</div>
                <div className="text-[11px] opacity-70 mb-2">{o.items.map((i) => `${i.name} ×${i.qty}`).join(' · ')}</div>
                {o.note && <div className="text-[11px] bg-yellow-500/10 border border-yellow-500/20 rounded px-2 py-1 mb-2">📝 {o.note}</div>}
                {o.shipping_provider && (
                  <div className="flex items-center gap-2 bg-blue-500/5 border border-blue-500/20 rounded px-2 py-1.5 mb-2" data-testid={`tracking-row-${o.id}`}>
                    <span className="text-[11px] opacity-80">🚚 {o.shipping_provider_name || o.shipping_provider}</span>
                    <input
                      type="text"
                      defaultValue={o.tracking_number || ''}
                      placeholder="رقم التتبع (AWB)"
                      className="flex-1 min-w-0 text-[11px] bg-black/30 border border-white/10 rounded px-2 py-1 font-mono"
                      data-testid={`tracking-input-${o.id}`}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          saveTracking(o.id, o.status, e.target.value.trim());
                        }
                      }}
                      onBlur={(e) => {
                        const newVal = e.target.value.trim();
                        if (newVal !== (o.tracking_number || '').trim()) {
                          saveTracking(o.id, o.status, newVal);
                        }
                      }}
                    />
                  </div>
                )}
                <div className="flex gap-1 flex-wrap">
                  {o.status === 'pending' && <button onClick={() => setStatus(o.id, 'accepted')} className="text-[11px] px-2 py-1 bg-blue-500/20 hover:bg-blue-500/40 rounded font-bold" data-testid={`accept-${o.id}`}>✓ قبول</button>}
                  {o.status === 'accepted' && <button onClick={() => setStatus(o.id, 'preparing')} className="text-[11px] px-2 py-1 bg-orange-500/20 hover:bg-orange-500/40 rounded font-bold">👨‍🍳 تحضير</button>}
                  {o.status === 'preparing' && <button onClick={() => setStatus(o.id, 'ready')} className="text-[11px] px-2 py-1 bg-purple-500/20 hover:bg-purple-500/40 rounded font-bold">📦 جاهز</button>}
                  {['ready', 'accepted'].includes(o.status) && drivers.length > 0 && (
                    <select onChange={(e) => setStatus(o.id, 'on_the_way', e.target.value)} className="text-[11px] px-2 py-1 bg-cyan-500/20 rounded font-bold" data-testid={`assign-driver-${o.id}`}>
                      <option>🛵 عيّن سائق</option>
                      {drivers.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                    </select>
                  )}
                  {o.status === 'on_the_way' && <button onClick={() => setStatus(o.id, 'delivered')} className="text-[11px] px-2 py-1 bg-green-500/20 hover:bg-green-500/40 rounded font-bold">✅ تم التوصيل</button>}
                  {!['delivered', 'cancelled'].includes(o.status) && <button onClick={() => setStatus(o.id, 'cancelled')} className="text-[11px] px-2 py-1 bg-red-500/20 hover:bg-red-500/40 rounded font-bold">❌ إلغاء</button>}
                  {drv && <span className="text-[11px] opacity-70 self-center">🛵 {drv.name}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ================================================================
   DRIVERS TAB — manage delivery drivers
   ================================================================ */
function DriversTab({ token }) {
  const [drivers, setDrivers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', phone: '', password: '', vehicle: '', zone: '' });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/websites/client/drivers`, { headers: authH(token) });
      const d = await r.json();
      setDrivers(d.drivers || []);
    } catch (_) {}
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/drivers`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify(form),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'فشل');
      toast.success('✓ أُضيف السائق');
      setForm({ name: '', phone: '', password: '', vehicle: '', zone: '' });
      setShowForm(false); load();
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const remove = async (id) => {
    if (!window.confirm('حذف السائق؟')) return;
    try {
      await fetch(`${API}/api/websites/client/drivers/${id}`, { method: 'DELETE', headers: authH(token) });
      toast.success('حُذف'); load();
    } catch (_) {}
  };

  return (
    <div data-testid="drivers-tab">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs opacity-70">{drivers.length} سائق مسجّل</div>
        {!showForm && <button onClick={() => setShowForm(true)} className="px-3 py-1.5 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-lg text-xs font-black" data-testid="add-driver-btn">+ إضافة سائق</button>}
      </div>
      {showForm && (
        <form onSubmit={submit} className="bg-white/5 border border-yellow-500/30 rounded-xl p-3 mb-3 space-y-2" data-testid="driver-form">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="اسم السائق" className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" required data-testid="driver-name" />
          <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="رقم الجوال" className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" required data-testid="driver-phone" />
          <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="كلمة مرور له" className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" required data-testid="driver-password" />
          <input value={form.vehicle} onChange={(e) => setForm({ ...form, vehicle: e.target.value })} placeholder="المركبة (دراجة/سيارة)" className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" />
          <input value={form.zone} onChange={(e) => setForm({ ...form, zone: e.target.value })} placeholder="منطقة التوصيل" className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" />
          <div className="flex gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="flex-1 py-2 bg-white/10 rounded-lg text-xs font-bold">إلغاء</button>
            <button type="submit" disabled={busy} className="flex-[2] py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-lg text-xs font-black disabled:opacity-50">✓ إضافة</button>
          </div>
        </form>
      )}
      {drivers.length === 0 && !showForm ? (
        <div className="text-center py-10 bg-white/3 border border-dashed border-white/15 rounded-2xl">
          <div className="text-4xl mb-2">🛵</div>
          <div className="text-sm opacity-60">لا يوجد سائقون مسجّلون</div>
          <div className="text-xs opacity-40 mt-1">أضف سائقاً ليظهر في خيارات تعيين الطلبات</div>
        </div>
      ) : (
        <div className="space-y-2">
          {drivers.map((d) => (
            <div key={d.id} className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-3" data-testid={`driver-${d.id}`}>
              <div className="w-10 h-10 bg-yellow-500/20 rounded-full flex items-center justify-center text-xl">🛵</div>
              <div className="flex-1">
                <div className="font-bold text-sm">{d.name}</div>
                <div className="text-xs opacity-70">📞 {d.phone}{d.vehicle ? ` · ${d.vehicle}` : ''}{d.zone ? ` · ${d.zone}` : ''}</div>
              </div>
              <button onClick={() => remove(d.id)} className="p-1.5 hover:bg-red-500/20 rounded-lg text-red-400"><X className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ================================================================
   CUSTOMERS TAB — site customer directory
   ================================================================ */
function CustomersTab({ token }) {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/websites/client/customers`, { headers: authH(token) });
        const d = await r.json();
        setCustomers(d.customers || []);
      } catch (_) {} finally { setLoading(false); }
    })();
  }, [token]);

  return (
    <div data-testid="customers-tab">
      <div className="text-xs opacity-70 mb-3">{customers.length} عميل مسجّل</div>
      {loading ? <div className="text-center py-10 opacity-60">...</div> : customers.length === 0 ? (
        <div className="text-center py-10 bg-white/3 border border-dashed border-white/15 rounded-2xl">
          <div className="text-4xl mb-2">👥</div>
          <div className="text-sm opacity-60">لا عملاء مسجّلون بعد</div>
          <div className="text-xs opacity-40 mt-1">عندما يُنشئ الزوار حسابات في موقعك ستظهر هنا</div>
        </div>
      ) : (
        <div className="space-y-2">
          {customers.map((c) => (
            <div key={c.id} className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-3" data-testid={`customer-${c.id}`}>
              <div className="w-10 h-10 bg-blue-500/20 rounded-full flex items-center justify-center font-black">{(c.name || '?').charAt(0)}</div>
              <div className="flex-1">
                <div className="font-bold text-sm">{c.name}</div>
                <div className="text-xs opacity-70">📞 {c.phone}{c.email ? ` · ✉️ ${c.email}` : ''}</div>
                <div className="text-[10px] opacity-50">مسجّل منذ {new Date(c.created_at).toLocaleDateString('ar-SA')}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ================================================================
   DELIVERY SETTINGS TAB
   ================================================================ */
function DeliverySettingsTab({ token, slug }) {
  const [s, setS] = useState({ base_lat: '', base_lng: '', base_fee: 10, fee_per_km: 2, free_delivery_above: 200 });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/websites/client/delivery-settings`, { headers: authH(token) });
        const d = await r.json();
        setS({ ...s, ...d });
      } catch (_) {}
    })();
    // eslint-disable-next-line
  }, [token]);

  const useMyLoc = () => {
    if (!navigator.geolocation) return toast.error('متصفحك لا يدعم تحديد الموقع');
    navigator.geolocation.getCurrentPosition((p) => {
      setS((prev) => ({ ...prev, base_lat: p.coords.latitude, base_lng: p.coords.longitude }));
      toast.success('✓ تم تحديد موقع المتجر');
    }, () => toast.error('فشل'));
  };

  const save = async () => {
    setBusy(true);
    try {
      await fetch(`${API}/api/websites/client/delivery-settings`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({
          base_lat: s.base_lat ? parseFloat(s.base_lat) : null,
          base_lng: s.base_lng ? parseFloat(s.base_lng) : null,
          base_fee: parseFloat(s.base_fee) || 0,
          fee_per_km: parseFloat(s.fee_per_km) || 0,
          free_delivery_above: parseFloat(s.free_delivery_above) || 0,
        }),
      });
      toast.success('✓ تم الحفظ');
    } catch (_) { toast.error('فشل'); }
    finally { setBusy(false); }
  };

  const driverUrl = `${window.location.origin}/driver/${slug}`;

  return (
    <div className="space-y-4" data-testid="delivery-settings-tab">
      <div className="bg-gradient-to-br from-cyan-500/10 to-blue-500/5 border border-cyan-500/30 rounded-xl p-4">
        <h3 className="font-black text-cyan-300 mb-3">🛵 إعدادات التوصيل (احتساب تلقائي حسب المسافة)</h3>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[11px] opacity-70 block mb-1">📍 موقع المتجر (lat)</label>
            <input type="number" step="0.0001" value={s.base_lat || ''} onChange={(e) => setS({ ...s, base_lat: e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="base-lat" />
          </div>
          <div>
            <label className="text-[11px] opacity-70 block mb-1">📍 موقع المتجر (lng)</label>
            <input type="number" step="0.0001" value={s.base_lng || ''} onChange={(e) => setS({ ...s, base_lng: e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="base-lng" />
          </div>
        </div>
        <button onClick={useMyLoc} className="w-full mt-2 py-1.5 bg-blue-500/20 hover:bg-blue-500/40 rounded-lg text-xs font-bold" data-testid="use-my-location">📍 استخدم موقعي الحالي</button>
        <div className="grid grid-cols-3 gap-2 mt-3">
          <div><label className="text-[11px] opacity-70 block mb-1">رسوم أساسية</label><input type="number" value={s.base_fee} onChange={(e) => setS({ ...s, base_fee: e.target.value })} className="w-full px-2 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="base-fee" /></div>
          <div><label className="text-[11px] opacity-70 block mb-1">لكل كم</label><input type="number" value={s.fee_per_km} onChange={(e) => setS({ ...s, fee_per_km: e.target.value })} className="w-full px-2 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="fee-per-km" /></div>
          <div><label className="text-[11px] opacity-70 block mb-1">مجاني فوق</label><input type="number" value={s.free_delivery_above} onChange={(e) => setS({ ...s, free_delivery_above: e.target.value })} className="w-full px-2 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="free-above" /></div>
        </div>
        <div className="text-[10px] opacity-60 mt-2">مثال: رسوم أساسية 10 + 2 لكل كم، أو مجاني لو الطلب فوق 200 ر.س</div>
        <button onClick={save} disabled={busy} className="w-full mt-3 py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-lg font-black text-sm" data-testid="save-delivery-settings">{busy ? '...' : '💾 حفظ الإعدادات'}</button>
      </div>

      <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/5 border border-purple-500/30 rounded-xl p-4">
        <h3 className="font-black text-purple-300 mb-2">🔗 رابط لوحة السائقين</h3>
        <div className="flex items-center gap-2 bg-black/30 rounded-lg px-3 py-2 mb-2">
          <code className="flex-1 text-xs text-purple-300 truncate">{driverUrl}</code>
          <button onClick={() => { navigator.clipboard.writeText(driverUrl); toast.success('نُسخ'); }} className="text-xs px-2 py-1 bg-white/10 hover:bg-white/20 rounded">نسخ</button>
        </div>
        <div className="text-[11px] opacity-70">شارك هذا الرابط مع سائقيك — يدخلون بأرقام جوالاتهم وكلمات مرورهم التي أنشأتها في تبويب "السائقون"</div>
      </div>
    </div>
  );
}

/* ================================================================
   COUPONS TAB
   ================================================================ */
function CouponsTab({ token }) {
  const [coupons, setCoupons] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ code: '', discount_percent: 10, discount_amount: 0, min_order: 0, max_uses: 100 });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/websites/client/coupons`, { headers: authH(token) });
      const d = await r.json();
      setCoupons(d.coupons || []);
    } catch (_) {}
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/coupons`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify(form),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'فشل');
      toast.success('✓ أُنشئ الكوبون');
      setForm({ code: '', discount_percent: 10, discount_amount: 0, min_order: 0, max_uses: 100 });
      setShowForm(false); load();
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const remove = async (id) => {
    if (!window.confirm('حذف الكوبون؟')) return;
    await fetch(`${API}/api/websites/client/coupons/${id}`, { method: 'DELETE', headers: authH(token) });
    load();
  };

  return (
    <div data-testid="coupons-tab">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs opacity-70">{coupons.length} كوبون نشط</div>
        {!showForm && <button onClick={() => setShowForm(true)} className="px-3 py-1.5 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-lg text-xs font-black" data-testid="new-coupon-btn">+ كوبون جديد</button>}
      </div>
      {showForm && (
        <form onSubmit={submit} className="bg-white/5 border border-yellow-500/30 rounded-xl p-3 mb-3 space-y-2">
          <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} placeholder="كود الكوبون (مثال: WELCOME10)" className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm uppercase" required data-testid="coupon-code" />
          <div className="grid grid-cols-2 gap-2">
            <div><label className="text-[10px] opacity-60">خصم %</label><input type="number" value={form.discount_percent} onChange={(e) => setForm({ ...form, discount_percent: +e.target.value })} className="w-full px-2 py-1.5 bg-white/5 border border-white/15 rounded text-sm" /></div>
            <div><label className="text-[10px] opacity-60">أو مبلغ ثابت</label><input type="number" value={form.discount_amount} onChange={(e) => setForm({ ...form, discount_amount: +e.target.value })} className="w-full px-2 py-1.5 bg-white/5 border border-white/15 rounded text-sm" /></div>
            <div><label className="text-[10px] opacity-60">الحد الأدنى</label><input type="number" value={form.min_order} onChange={(e) => setForm({ ...form, min_order: +e.target.value })} className="w-full px-2 py-1.5 bg-white/5 border border-white/15 rounded text-sm" /></div>
            <div><label className="text-[10px] opacity-60">الحد الأقصى للاستخدام</label><input type="number" value={form.max_uses} onChange={(e) => setForm({ ...form, max_uses: +e.target.value })} className="w-full px-2 py-1.5 bg-white/5 border border-white/15 rounded text-sm" /></div>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="flex-1 py-2 bg-white/10 rounded text-xs font-bold">إلغاء</button>
            <button type="submit" disabled={busy} className="flex-[2] py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded text-xs font-black">✓ إنشاء</button>
          </div>
        </form>
      )}
      {coupons.length === 0 && !showForm ? (
        <div className="text-center py-10 bg-white/3 border border-dashed border-white/15 rounded-2xl">
          <div className="text-4xl mb-2">🎟️</div>
          <div className="text-sm opacity-60">لا كوبونات بعد</div>
          <div className="text-xs opacity-40 mt-1">أنشئ كوبون لزيادة مبيعاتك</div>
        </div>
      ) : (
        <div className="space-y-2">
          {coupons.map((c) => (
            <div key={c.id} className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-3">
              <div className="px-3 py-1.5 bg-yellow-500/20 text-yellow-300 rounded-lg font-black text-sm font-mono">{c.code}</div>
              <div className="flex-1 text-xs">
                <div className="font-bold">{c.discount_percent ? `خصم ${c.discount_percent}%` : `${c.discount_amount} ر.س خصم`}{c.min_order ? ` · حد أدنى ${c.min_order}` : ''}</div>
                <div className="opacity-60">{c.used}/{c.max_uses} استُخدم</div>
              </div>
              <button onClick={() => remove(c.id)} className="p-1.5 hover:bg-red-500/20 rounded text-red-400"><X className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ================================================================
   LOYALTY SETTINGS TAB
   ================================================================ */
/* ================================================================
   PAYMENT GATEWAYS TAB — each tenant inputs its own provider keys
   ================================================================ */
function PaymentGatewaysTab({ token }) {
  const [gateways, setGateways] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [draft, setDraft] = useState({});
  const [showCompare, setShowCompare] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/client/payment-gateways`, { headers: authH(token) });
      const d = await r.json();
      setGateways(d.gateways || []);
    } catch (_) { toast.error('فشل تحميل بوابات الدفع'); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const setField = (pid, k, v) => setDraft((p) => ({ ...p, [pid]: { ...(p[pid] || {}), [k]: v } }));

  const save = async (pid, extra = {}) => {
    setBusyId(pid);
    try {
      const body = { ...(draft[pid] || {}), ...extra };
      const r = await fetch(`${API}/api/websites/client/payment-gateways/${pid}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error('failed');
      toast.success('✓ تم الحفظ');
      setDraft((p) => { const n = { ...p }; delete n[pid]; return n; });
      await load();
    } catch (_) { toast.error('فشل الحفظ'); }
    finally { setBusyId(null); }
  };

  const testCreds = async (pid) => {
    setBusyId(pid + '-test');
    try {
      const r = await fetch(`${API}/api/websites/client/payment-gateways/${pid}/test`, {
        method: 'POST', headers: authH(token),
      });
      const d = await r.json();
      if (d.ok) toast.success(d.message); else toast.error(d.message);
    } catch (_) { toast.error('فشل الاختبار'); }
    finally { setBusyId(null); }
  };

  if (loading) return <div className="text-center py-10 opacity-60">...</div>;

  return (
    <div className="space-y-4" data-testid="payment-gateways-tab">
      <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/5 border border-blue-500/30 rounded-xl p-4">
        <h3 className="font-black text-blue-300 mb-1">💳 بوابات الدفع الخاصة بك</h3>
        <p className="text-xs opacity-70 mb-3">أدخل مفاتيح بوابات الدفع الخاصة بك هنا — ستُشفَّر قبل الحفظ. جميع المدفوعات تذهب مباشرة إلى حسابك.</p>
        <button onClick={() => setShowCompare(true)}
          className="w-full py-2 bg-gradient-to-r from-blue-500/40 to-cyan-500/40 hover:from-blue-500/60 hover:to-cyan-500/60 border border-blue-400/40 rounded-lg font-black text-xs text-white"
          data-testid="open-gw-compare">
          📊 مقارنة تفصيلية بين كل البوابات (رسوم، تسوية، مميزات، عيوب)
        </button>
      </div>
      {showCompare && <GatewayCompareModal onClose={() => setShowCompare(false)} />}

      {gateways.map((g) => (
        <div key={g.id} className={`rounded-xl border p-4 ${g.enabled ? 'bg-green-500/5 border-green-500/30' : 'bg-white/3 border-white/10'}`} data-testid={`gateway-${g.id}`}>
          <div className="flex items-start justify-between mb-3 gap-2">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h4 className="font-black text-base">{g.name_ar}</h4>
                {g.coming_soon && <span className="text-[10px] bg-yellow-500/20 text-yellow-300 px-2 py-0.5 rounded-full">قريباً</span>}
                {g.configured && g.enabled && <span className="text-[10px] bg-green-500/20 text-green-300 px-2 py-0.5 rounded-full">مفعّل</span>}
              </div>
              <div className="text-[11px] opacity-60 mt-1">{(g.methods || []).join(' · ')}</div>
            </div>
            <label className="flex items-center gap-1.5 cursor-pointer text-xs">
              <input type="checkbox" checked={!!g.enabled} disabled={busyId === g.id}
                onChange={(e) => save(g.id, { enabled: e.target.checked })}
                data-testid={`gateway-${g.id}-toggle`} />
              <span className="opacity-75">{g.enabled ? 'مفعّل' : 'إيقاف'}</span>
            </label>
          </div>

          {/* Provider-specific fields */}
          {g.id === 'moyasar' && (
            <div className="space-y-2">
              <div>
                <label className="text-[11px] opacity-70 block mb-1">Publishable Key (pk_test_...)</label>
                <input type="text"
                  placeholder={g.publishable_key_preview || 'pk_test_...'}
                  value={(draft[g.id] || {}).publishable_key || ''}
                  onChange={(e) => setField(g.id, 'publishable_key', e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm font-mono"
                  data-testid="moyasar-pk" />
              </div>
              <div>
                <label className="text-[11px] opacity-70 block mb-1">Secret Key (sk_test_...)</label>
                <input type="password"
                  placeholder={g.secret_key_preview || 'sk_test_...'}
                  value={(draft[g.id] || {}).secret_key || ''}
                  onChange={(e) => setField(g.id, 'secret_key', e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm font-mono"
                  data-testid="moyasar-sk" />
                <div className="text-[10px] opacity-50 mt-1">
                  <a href="https://dashboard.moyasar.com" target="_blank" rel="noreferrer" className="text-blue-400 underline">احصل على المفاتيح من Moyasar Dashboard</a>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 text-[11px]">
                {['mada', 'creditcard', 'applepay', 'stcpay'].map((m) => (
                  <label key={m} className="flex items-center gap-1 bg-white/5 px-2 py-1 rounded cursor-pointer">
                    <input type="checkbox"
                      checked={((draft[g.id] || {}).methods || g.methods || []).includes(m)}
                      onChange={(e) => {
                        const cur = (draft[g.id] || {}).methods || g.methods || [];
                        const next = e.target.checked ? [...new Set([...cur, m])] : cur.filter((x) => x !== m);
                        setField(g.id, 'methods', next);
                      }} />
                    {m === 'mada' ? 'مدى' : m === 'creditcard' ? 'فيزا/ماستر' : m === 'applepay' ? 'Apple Pay' : 'STC Pay'}
                  </label>
                ))}
              </div>
              <div className="flex gap-2 pt-1">
                <button onClick={() => save(g.id)} disabled={busyId === g.id}
                  className="flex-1 py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-lg font-black text-xs disabled:opacity-50"
                  data-testid="moyasar-save">{busyId === g.id ? '...' : '💾 حفظ المفاتيح'}</button>
                {g.configured && (
                  <button onClick={() => testCreds(g.id)} disabled={busyId}
                    className="px-3 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 rounded-lg font-bold text-xs"
                    data-testid="moyasar-test">{busyId === g.id + '-test' ? '...' : '🧪 اختبار'}</button>
                )}
              </div>
            </div>
          )}

          {g.id === 'tabby' && (
            <div className="space-y-2 opacity-80">
              <div>
                <label className="text-[11px] opacity-70 block mb-1">Public Key (pk_test_...)</label>
                <input type="text" placeholder={g.public_key_preview || 'pk_test_...'}
                  value={(draft[g.id] || {}).public_key || ''}
                  onChange={(e) => setField(g.id, 'public_key', e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm font-mono" />
              </div>
              <div>
                <label className="text-[11px] opacity-70 block mb-1">Secret Key</label>
                <input type="password" placeholder={g.secret_key_preview || 'sk_...'}
                  value={(draft[g.id] || {}).secret_key || ''}
                  onChange={(e) => setField(g.id, 'secret_key', e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm font-mono" />
              </div>
              <button onClick={() => save(g.id)} disabled={busyId === g.id}
                className="w-full py-2 bg-white/10 hover:bg-white/15 rounded-lg font-bold text-xs">
                💾 حفظ (الربط الكامل قيد الإضافة)
              </button>
            </div>
          )}

          {g.id === 'tamara' && (
            <div className="space-y-2 opacity-80">
              <div>
                <label className="text-[11px] opacity-70 block mb-1">API Token</label>
                <input type="password" placeholder={g.api_token_preview || 'tkn_...'}
                  value={(draft[g.id] || {}).api_token || ''}
                  onChange={(e) => setField(g.id, 'api_token', e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm font-mono" />
              </div>
              <div>
                <label className="text-[11px] opacity-70 block mb-1">Notification Token</label>
                <input type="password" placeholder={g.notification_token_preview || '...'}
                  value={(draft[g.id] || {}).notification_token || ''}
                  onChange={(e) => setField(g.id, 'notification_token', e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm font-mono" />
              </div>
              <button onClick={() => save(g.id)} disabled={busyId === g.id}
                className="w-full py-2 bg-white/10 hover:bg-white/15 rounded-lg font-bold text-xs">
                💾 حفظ (الربط الكامل قيد الإضافة)
              </button>
            </div>
          )}

          {g.id === 'cod' && (
            <div className="text-xs opacity-70">
              لا يحتاج مفاتيح. فعّل فقط الزر أعلاه ليُعرض كخيار "الدفع عند الاستلام" للعملاء.
            </div>
          )}
        </div>
      ))}

      <div className="text-[11px] opacity-50 text-center pt-2">
        المفاتيح السرية تُشفَّر قبل الحفظ ولا تُعرض أبداً كاملة.
      </div>
    </div>
  );
}

/* ================================================================
   BOOKINGS TAB — appointments (salon, pets, medical, gym)
   ================================================================ */
function BookingsTab({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const q = filter ? `?status=${filter}` : '';
      const r = await fetch(`${API}/api/websites/client/bookings${q}`, { headers: authH(token) });
      setData(await r.json());
    } catch (_) {} finally { setLoading(false); }
  }, [token, filter]);
  useEffect(() => { load(); const id = setInterval(load, 20000); return () => clearInterval(id); }, [load]);

  const setStatus = async (id, status) => {
    try {
      await fetch(`${API}/api/websites/client/bookings/${id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ status }),
      });
      toast.success('تم التحديث');
      load();
    } catch (_) { toast.error('فشل'); }
  };

  if (loading && !data) return <div className="text-center py-10 opacity-60">...</div>;
  const STATUS_LABEL = {
    pending: '⏳ قيد الانتظار', confirmed: '✅ مؤكد', in_progress: '🚀 قيد التنفيذ',
    completed: '✓ مكتمل', cancelled: '❌ ملغي', no_show: '👻 لم يحضر',
  };
  return (
    <div data-testid="bookings-tab" className="space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-black text-base">📅 المواعيد ({data?.total || 0})</h3>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}
          className="px-3 py-1.5 bg-white/5 border border-white/15 rounded-lg text-xs"
          data-testid="booking-filter">
          <option value="">كل الحالات</option>
          {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      {(data?.bookings || []).length === 0 ? (
        <div className="text-center py-12 opacity-60">لا مواعيد بعد</div>
      ) : (
        <div className="space-y-2">
          {data.bookings.map((b) => (
            <div key={b.id} className="bg-white/3 border border-white/10 rounded-xl p-3 text-sm" data-testid={`booking-${b.id}`}>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex-1">
                  <div className="font-bold">{b.service_name}</div>
                  <div className="text-xs opacity-70">{b.customer_name} · {b.customer_phone}</div>
                  <div className="text-[11px] opacity-60 mt-1">
                    🕐 {new Date(b.slot_iso).toLocaleString('ar-SA')} · {b.duration_min} د · {b.price} ر.س
                  </div>
                  {b.notes && <div className="text-[11px] mt-1 bg-white/5 p-1.5 rounded">📝 {b.notes}</div>}
                </div>
                <div className="text-[11px]">{STATUS_LABEL[b.status] || b.status}</div>
              </div>
              <div className="flex flex-wrap gap-1 text-[10px]">
                {b.status === 'pending' && <button onClick={() => setStatus(b.id, 'confirmed')} className="px-2 py-1 bg-green-500/20 hover:bg-green-500/30 rounded font-bold">✅ تأكيد</button>}
                {['pending', 'confirmed'].includes(b.status) && <button onClick={() => setStatus(b.id, 'in_progress')} className="px-2 py-1 bg-blue-500/20 hover:bg-blue-500/30 rounded font-bold">🚀 بدء</button>}
                {b.status === 'in_progress' && <button onClick={() => setStatus(b.id, 'completed')} className="px-2 py-1 bg-yellow-500/20 hover:bg-yellow-500/30 rounded font-bold">✓ إنهاء</button>}
                {!['completed', 'cancelled'].includes(b.status) && <button onClick={() => setStatus(b.id, 'cancelled')} className="px-2 py-1 bg-red-500/20 hover:bg-red-500/30 rounded font-bold">❌ إلغاء</button>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ================================================================
   SERVICES TAB — manage price list (salon, pets, medical, gym)
   ================================================================ */
function ServicesTab({ token }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: '', price: '', duration_min: 30 });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/client/services`, { headers: authH(token) });
      setItems((await r.json()).services || []);
    } catch (_) {} finally { setLoading(false); }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!form.name || !form.price) { toast.error('الاسم والسعر مطلوبان'); return; }
    try {
      await fetch(`${API}/api/websites/client/services`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ name: form.name, price: parseFloat(form.price), duration_min: parseInt(form.duration_min) || 30 }),
      });
      toast.success('أُضيفت الخدمة');
      setForm({ name: '', price: '', duration_min: 30 });
      load();
    } catch (_) { toast.error('فشل'); }
  };

  const del = async (id) => {
    if (!window.confirm('حذف؟')) return;
    await fetch(`${API}/api/websites/client/services/${id}`, { method: 'DELETE', headers: authH(token) });
    toast.success('تم الحذف');
    load();
  };

  if (loading) return <div className="text-center py-10 opacity-60">...</div>;
  return (
    <div data-testid="services-tab" className="space-y-3">
      <div className="bg-white/3 border border-white/10 rounded-xl p-3 space-y-2">
        <h3 className="font-black text-sm mb-2">➕ إضافة خدمة</h3>
        <input placeholder="اسم الخدمة" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="svc-name" />
        <div className="grid grid-cols-2 gap-2">
          <input type="number" placeholder="السعر (ر.س)" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })}
            className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="svc-price" />
          <input type="number" placeholder="المدة (دقيقة)" value={form.duration_min} onChange={(e) => setForm({ ...form, duration_min: e.target.value })}
            className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="svc-duration" />
        </div>
        <button onClick={add} className="w-full py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded font-black text-sm" data-testid="svc-add">إضافة</button>
      </div>
      <div className="space-y-2">
        {items.length === 0 && <div className="text-center py-8 opacity-60 text-sm">لا خدمات بعد</div>}
        {items.map((s) => (
          <div key={s.id} className="flex items-center gap-2 bg-white/3 border border-white/10 rounded-xl p-3 text-sm" data-testid={`svc-${s.id}`}>
            <div className="flex-1">
              <div className="font-bold">{s.name}</div>
              <div className="text-[11px] opacity-60">{s.price} ر.س · {s.duration_min} دقيقة</div>
            </div>
            <button onClick={() => del(s.id)} className="p-1.5 text-red-400 hover:bg-red-500/20 rounded" data-testid={`svc-del-${s.id}`}>🗑️</button>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ================================================================
   PRODUCTS TAB — e-commerce catalog management
   ================================================================ */
function ProductsTab({ token }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: '', price: '', stock: '', category: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/client/products`, { headers: authH(token) });
      setItems((await r.json()).products || []);
    } catch (_) {} finally { setLoading(false); }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!form.name || !form.price) { toast.error('الاسم والسعر مطلوبان'); return; }
    try {
      await fetch(`${API}/api/websites/client/products`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ name: form.name, price: parseFloat(form.price), stock: parseInt(form.stock) || 0, category: form.category || null }),
      });
      toast.success('أُضيف المنتج');
      setForm({ name: '', price: '', stock: '', category: '' });
      load();
    } catch (_) { toast.error('فشل'); }
  };

  const del = async (id) => {
    if (!window.confirm('حذف؟')) return;
    await fetch(`${API}/api/websites/client/products/${id}`, { method: 'DELETE', headers: authH(token) });
    load();
  };

  if (loading) return <div className="text-center py-10 opacity-60">...</div>;
  return (
    <div data-testid="products-tab" className="space-y-3">
      <div className="bg-white/3 border border-white/10 rounded-xl p-3 space-y-2">
        <h3 className="font-black text-sm mb-2">➕ إضافة منتج</h3>
        <input placeholder="اسم المنتج" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="prod-name" />
        <div className="grid grid-cols-3 gap-2">
          <input type="number" placeholder="السعر" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })}
            className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="prod-price" />
          <input type="number" placeholder="المخزون" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })}
            className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="prod-stock" />
          <input placeholder="الفئة" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="prod-cat" />
        </div>
        <button onClick={add} className="w-full py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-black rounded font-black text-sm" data-testid="prod-add">إضافة</button>
      </div>
      <div className="space-y-2">
        {items.length === 0 && <div className="text-center py-8 opacity-60 text-sm">لا منتجات بعد</div>}
        {items.map((p) => (
          <div key={p.id} className="flex items-center gap-2 bg-white/3 border border-white/10 rounded-xl p-3 text-sm" data-testid={`prod-${p.id}`}>
            <div className="flex-1">
              <div className="font-bold">{p.name}</div>
              <div className="text-[11px] opacity-60">
                {p.price} ر.س · مخزون: {p.stock} {p.stock <= 5 ? '⚠️' : ''}
                {p.category && <span> · {p.category}</span>}
              </div>
            </div>
            <button onClick={() => del(p.id)} className="p-1.5 text-red-400 hover:bg-red-500/20 rounded" data-testid={`prod-del-${p.id}`}>🗑️</button>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ================================================================
   LISTINGS TAB — real estate agent's property list
   ================================================================ */
function ListingsTab({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    title: '', price: '', transaction: 'بيع', type: 'شقة',
    city: '', district: '', area_sqm: '', bedrooms: '', bathrooms: '',
    agent_phone: '', commission_pct: '2.5', description: '', images: '',
  });
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/client/listings`, { headers: authH(token) });
      setData(await r.json());
    } catch (_) {} finally { setLoading(false); }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!form.title || !form.price || !form.agent_phone) {
      toast.error('العنوان والسعر وهاتف الدلّال مطلوبة');
      return;
    }
    try {
      const body = {
        ...form,
        price: parseFloat(form.price),
        area_sqm: form.area_sqm ? parseFloat(form.area_sqm) : null,
        bedrooms: form.bedrooms ? parseInt(form.bedrooms) : null,
        bathrooms: form.bathrooms ? parseInt(form.bathrooms) : null,
        commission_pct: parseFloat(form.commission_pct) || 2.5,
        images: form.images ? form.images.split(',').map((s) => s.trim()).filter(Boolean) : null,
      };
      await fetch(`${API}/api/websites/client/listings`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify(body),
      });
      toast.success('أُضيف العقار ✓');
      setShowForm(false);
      setForm({ ...form, title: '', price: '', city: '', district: '', area_sqm: '', bedrooms: '', bathrooms: '', description: '', images: '' });
      load();
    } catch (_) { toast.error('فشل'); }
  };

  const markSold = async (id) => {
    await fetch(`${API}/api/websites/client/listings/${id}/mark-sold`, { method: 'PATCH', headers: authH(token) });
    toast.success('تم تأشير العقار كمباع ✓');
    load();
  };
  const del = async (id) => {
    if (!window.confirm('حذف العقار؟')) return;
    await fetch(`${API}/api/websites/client/listings/${id}`, { method: 'DELETE', headers: authH(token) });
    load();
  };

  if (loading && !data) return <div className="text-center py-10 opacity-60">...</div>;
  const s = data?.stats || {};
  return (
    <div data-testid="listings-tab" className="space-y-3">
      {/* Commission / Stats Dashboard */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
        <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center">
          <div className="text-[10px] opacity-60">إجمالي العقارات</div>
          <div className="text-lg font-black">{s.total || 0}</div>
        </div>
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-3 text-center">
          <div className="text-[10px] opacity-60">نشطة</div>
          <div className="text-lg font-black text-green-300">{s.active || 0}</div>
        </div>
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-3 text-center">
          <div className="text-[10px] opacity-60">مُباعة</div>
          <div className="text-lg font-black text-blue-300">{s.sold || 0}</div>
        </div>
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-3 text-center">
          <div className="text-[10px] opacity-60">عمولة متوقعة</div>
          <div className="text-lg font-black text-yellow-300">{(s.potential_commission || 0).toLocaleString('ar-SA', { maximumFractionDigits: 0 })} ر.س</div>
        </div>
      </div>
      <div className="text-[11px] opacity-60 text-center mb-2">💰 قيمة المحفظة الإجمالية: <b className="text-yellow-300">{(s.total_value || 0).toLocaleString('ar-SA')} ر.س</b></div>

      <button onClick={() => setShowForm(!showForm)}
        className="w-full py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-black rounded-lg font-black text-sm" data-testid="toggle-add-listing">
        {showForm ? '× إغلاق' : '🏠 إضافة عقار جديد'}
      </button>

      {showForm && (
        <div className="bg-white/3 border border-white/10 rounded-xl p-3 space-y-2">
          <input placeholder="عنوان العقار" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="lst-title" />
          <div className="grid grid-cols-2 gap-2">
            <select value={form.transaction} onChange={(e) => setForm({ ...form, transaction: e.target.value })}
              className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm">
              <option value="بيع">بيع</option><option value="إيجار">إيجار</option>
            </select>
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}
              className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm">
              <option>شقة</option><option>فيلا</option><option>أرض</option><option>تجاري</option><option>مزرعة</option>
            </select>
            <input type="number" placeholder="السعر (ر.س)" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })}
              className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="lst-price" />
            <input type="number" placeholder="المساحة (م²)" value={form.area_sqm} onChange={(e) => setForm({ ...form, area_sqm: e.target.value })}
              className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" />
            <input placeholder="المدينة" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })}
              className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" />
            <input placeholder="الحي" value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })}
              className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" />
            <input type="number" placeholder="غرف النوم" value={form.bedrooms} onChange={(e) => setForm({ ...form, bedrooms: e.target.value })}
              className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" />
            <input type="number" placeholder="دورات المياه" value={form.bathrooms} onChange={(e) => setForm({ ...form, bathrooms: e.target.value })}
              className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" />
            <input placeholder="واتساب الدلّال (+966...)" value={form.agent_phone} onChange={(e) => setForm({ ...form, agent_phone: e.target.value })}
              className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" />
            <input type="number" step="0.1" placeholder="عمولة %" value={form.commission_pct} onChange={(e) => setForm({ ...form, commission_pct: e.target.value })}
              className="px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" />
          </div>
          <textarea rows={2} placeholder="الوصف" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" />
          <input placeholder="روابط صور مفصولة بفاصلة" value={form.images} onChange={(e) => setForm({ ...form, images: e.target.value })}
            className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" />
          <button onClick={save} className="w-full py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded font-black text-sm" data-testid="lst-save">💾 حفظ العقار</button>
        </div>
      )}

      <div className="space-y-2">
        {(data?.listings || []).length === 0 && <div className="text-center py-8 opacity-60 text-sm">لا عقارات بعد</div>}
        {(data?.listings || []).map((l) => {
          const comm = (l.price || 0) * (l.commission_pct || 2.5) / 100;
          return (
            <div key={l.id} className={`border rounded-xl p-3 ${l.sold ? 'bg-blue-500/5 border-blue-500/20 opacity-70' : 'bg-white/3 border-white/10'}`} data-testid={`lst-${l.id}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-black text-sm">{l.title}</span>
                    <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded-full">{l.transaction}</span>
                    {l.sold && <span className="text-[10px] bg-blue-500/30 text-blue-200 px-2 py-0.5 rounded-full">✓ مُباع</span>}
                  </div>
                  <div className="text-yellow-300 font-black mb-1">{Number(l.price).toLocaleString('ar-SA')} ر.س</div>
                  <div className="text-[11px] opacity-70">
                    📍 {l.city} {l.district && `- ${l.district}`} · {l.area_sqm || '—'}م² · {l.bedrooms || '—'}🛏 · {l.bathrooms || '—'}🚿
                  </div>
                  <div className="text-[10px] text-emerald-300 mt-1">
                    💰 عمولة متوقعة: {comm.toLocaleString('ar-SA', { maximumFractionDigits: 0 })} ر.س ({l.commission_pct || 2.5}%)
                  </div>
                </div>
                <div className="flex flex-col gap-1">
                  {!l.sold && <button onClick={() => markSold(l.id)} className="px-2 py-1 bg-blue-500/20 hover:bg-blue-500/30 rounded text-[10px] font-bold">✓ مُباع</button>}
                  <button onClick={() => del(l.id)} className="px-2 py-1 bg-red-500/20 hover:bg-red-500/30 rounded text-[10px] font-bold">🗑</button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ================================================================
   GATEWAY COMPARE MODAL — detailed side-by-side comparison
   ================================================================ */
function GatewayCompareModal({ onClose }) {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    fetch(`${API}/api/websites/payment-gateways/compare`).then((r) => r.json()).then((d) => setRows(d.rows || []));
  }, []);
  return (
    <div className="fixed inset-0 bg-black/85 z-[1100] flex items-center justify-center p-4" onClick={onClose} data-testid="gw-compare-modal">
      <div onClick={(e) => e.stopPropagation()} className="bg-slate-900 text-white rounded-2xl max-w-5xl w-full max-h-[92vh] overflow-auto p-5 border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl md:text-2xl font-black">📊 مقارنة بوابات الدفع المدعومة</h2>
          <button onClick={onClose} className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20" data-testid="gw-compare-close">✕</button>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
          {rows.map((r) => (
            <div key={r.id} className="bg-white/5 border border-white/10 rounded-xl p-3 flex flex-col text-xs" data-testid={`gw-compare-${r.id}`}>
              <div className="font-black text-base mb-1">{r.name_ar}</div>
              <div className="opacity-70 text-[11px] mb-3 min-h-[32px]">{r.description_ar}</div>
              <div className="space-y-2 flex-1">
                <div className="bg-yellow-500/10 rounded p-2"><span className="opacity-60">الرسوم: </span><b>{r.fees}</b></div>
                <div className="bg-green-500/10 rounded p-2"><span className="opacity-60">التسوية: </span><b>{r.settlement}</b></div>
                <div className="bg-blue-500/10 rounded p-2"><span className="opacity-60">مناسبة لـ: </span>{r.best_for}</div>
                <div className="bg-purple-500/10 rounded p-2"><span className="opacity-60">الترخيص: </span>{r.license}</div>
                <div className="bg-cyan-500/10 rounded p-2"><span className="opacity-60">وقت الإعداد: </span>{r.setup_time}</div>
                <div>
                  <div className="font-bold text-green-300 mb-1">✅ مميزات</div>
                  <ul className="pr-3 space-y-0.5 opacity-80">{(r.pros || []).map((p, i) => <li key={i}>• {p}</li>)}</ul>
                </div>
                <div>
                  <div className="font-bold text-red-300 mb-1">⚠️ عيوب</div>
                  <ul className="pr-3 space-y-0.5 opacity-80">{(r.cons || []).map((p, i) => <li key={i}>• {p}</li>)}</ul>
                </div>
              </div>
              {r.signup_url && (
                <a href={r.signup_url} target="_blank" rel="noreferrer"
                  className="mt-3 block text-center py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black font-black rounded text-xs">
                  🔗 سجّل الآن
                </a>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   WIDGET CUSTOMIZER TAB — per-widget variant + position picker
   ================================================================ */
/* ================================================================
   🖱️ DRAG-POSITION CANVAS — mini-screen with draggable widget chip
   Translates a free drag into nearest anchor + precise offset.
   ================================================================ */
function DragPositionCanvas({ widget, position, offsetX, offsetY, onChange }) {
  const ref = React.useRef(null);
  const [drag, setDrag] = React.useState(null); // { x, y } in canvas-local px
  const [dims, setDims] = React.useState({ w: 320, h: 180 });

  // Map anchor to (left%, top%) of the canvas
  const anchorXY = (anchor) => {
    const m = {
      'top-left': [0.08, 0.12], 'top-right': [0.92, 0.12],
      'bottom-left': [0.08, 0.88], 'bottom-right': [0.92, 0.88],
      'middle-left': [0.08, 0.5], 'middle-right': [0.92, 0.5],
    };
    return m[anchor] || [0.92, 0.88];
  };

  // Current widget position inside canvas (in px)
  const [ax, ay] = anchorXY(position);
  const baseX = ax * dims.w;
  const baseY = ay * dims.h;
  // Scale offsets — real widget offsets are in px relative to a full screen (~1000×700)
  // so we scale down by ~3× for the mini canvas. This gives user a sense of direction.
  const scale = 0.25;
  const dispX = drag ? drag.x : baseX + offsetX * scale;
  const dispY = drag ? drag.y : baseY + offsetY * scale;

  const updateDims = React.useCallback(() => {
    if (ref.current) setDims({ w: ref.current.clientWidth, h: ref.current.clientHeight });
  }, []);
  React.useEffect(() => {
    updateDims();
    window.addEventListener('resize', updateDims);
    return () => window.removeEventListener('resize', updateDims);
  }, [updateDims]);

  // Find nearest anchor to a local (x,y) and return anchor + required offset
  const snap = (x, y) => {
    const anchors = ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'middle-left', 'middle-right'];
    let best = null;
    for (const a of anchors) {
      const [ax2, ay2] = anchorXY(a);
      const cx = ax2 * dims.w, cy = ay2 * dims.h;
      const d2 = (cx - x) ** 2 + (cy - y) ** 2;
      if (!best || d2 < best.d) best = { a, d: d2, cx, cy };
    }
    const ox = Math.round((x - best.cx) / scale);
    const oy = Math.round((y - best.cy) / scale);
    return { position: best.a, offset_x: ox, offset_y: oy };
  };

  const onMouseDown = (e) => {
    e.preventDefault();
    const rect = ref.current.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    setDrag({ x: mx, y: my });

    const onMove = (ev) => {
      const rx = ev.clientX - rect.left;
      const ry = ev.clientY - rect.top;
      const x = Math.max(16, Math.min(rect.width - 16, rx));
      const y = Math.max(16, Math.min(rect.height - 16, ry));
      setDrag({ x, y });
    };
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      setDrag((cur) => {
        if (!cur) return cur;
        const snapped = snap(cur.x, cur.y);
        onChange(snapped);
        return null;
      });
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  const onTouchStart = (e) => {
    const t = e.touches[0];
    const rect = ref.current.getBoundingClientRect();
    setDrag({ x: t.clientX - rect.left, y: t.clientY - rect.top });
    const onMove = (ev) => {
      const tt = ev.touches[0];
      const rx = tt.clientX - rect.left;
      const ry = tt.clientY - rect.top;
      setDrag({
        x: Math.max(16, Math.min(rect.width - 16, rx)),
        y: Math.max(16, Math.min(rect.height - 16, ry)),
      });
    };
    const onEnd = () => {
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onEnd);
      setDrag((cur) => {
        if (!cur) return cur;
        const snapped = snap(cur.x, cur.y);
        onChange(snapped);
        return null;
      });
    };
    window.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('touchend', onEnd);
  };

  const icon = widget.icon || '●';
  return (
    <div
      ref={ref}
      className="relative w-full h-44 bg-gradient-to-br from-slate-800/70 to-slate-900/70 border border-white/10 rounded-xl overflow-hidden select-none"
      data-testid={`drag-canvas-${widget.id}`}
    >
      {/* Fake site skeleton */}
      <div className="absolute inset-3 opacity-30">
        <div className="h-6 bg-white/15 rounded mb-2" />
        <div className="h-16 bg-white/8 rounded mb-2" />
        <div className="grid grid-cols-3 gap-1">
          <div className="h-8 bg-white/8 rounded" />
          <div className="h-8 bg-white/8 rounded" />
          <div className="h-8 bg-white/8 rounded" />
        </div>
      </div>
      {/* Draggable chip */}
      <div
        onMouseDown={onMouseDown}
        onTouchStart={onTouchStart}
        style={{
          left: `${dispX}px`,
          top: `${dispY}px`,
          transform: 'translate(-50%, -50%)',
          cursor: drag ? 'grabbing' : 'grab',
        }}
        className={`absolute w-9 h-9 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 text-black font-black flex items-center justify-center shadow-lg ring-2 ring-yellow-300/50 ${drag ? 'scale-110 ring-4' : ''} transition-transform`}
        data-testid={`drag-chip-${widget.id}`}
      >
        <span className="text-base">{icon}</span>
      </div>
      <div className="absolute bottom-1 left-2 text-[10px] opacity-50">اسحب لتحريك · يُثبَّت في أقرب زاوية تلقائياً</div>
    </div>
  );
}

function WidgetCustomizerTab({ token, slug }) {
  const [catalog, setCatalog] = useState(null);
  const [styles, setStyles] = useState({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [cat, mine] = await Promise.all([
        fetch(`${API}/api/websites/widget-styles/catalog`).then((r) => r.json()),
        fetch(`${API}/api/websites/client/widget-styles`, { headers: authH(token) }).then((r) => r.json()),
      ]);
      setCatalog(cat);
      setStyles(mine.widget_styles || {});
    } catch (_) {} finally { setLoading(false); }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const save = async (wid, patch) => {
    const next = { ...(styles[wid] || {}), ...patch };
    setStyles((s) => ({ ...s, [wid]: next }));
    try {
      await fetch(`${API}/api/websites/client/widget-styles/${wid}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify(next),
      });
      toast.success('✓');
    } catch (_) { toast.error('فشل الحفظ'); }
  };

  const reset = async (wid) => {
    await fetch(`${API}/api/websites/client/widget-styles/${wid}`, { method: 'DELETE', headers: authH(token) });
    setStyles((s) => { const n = { ...s }; delete n[wid]; return n; });
    toast.success('استُعيد الافتراضي');
  };

  if (loading) return <div className="text-center py-10 opacity-60">...</div>;
  const posLabels = { 'top-left': '⬉ أعلى يسار', 'top-right': '⬈ أعلى يمين', 'bottom-left': '⬋ أسفل يسار', 'bottom-right': '⬌ أسفل يمين', 'middle-left': '◧ وسط يسار', 'middle-right': '◨ وسط يمين' };

  return (
    <div data-testid="widget-customizer-tab" className="space-y-4">
      <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/5 border border-purple-500/30 rounded-xl p-4">
        <h3 className="font-black text-purple-300 mb-1">🎨 تخصيص الأدوات</h3>
        <p className="text-xs opacity-70">اختر شكل كل أداة، مكان ظهورها على الموقع، أو أخفِها تماماً. التغييرات تظهر مباشرة في موقعك.</p>
        <a href={`/sites/${slug}`} target="_blank" rel="noreferrer"
          className="mt-2 inline-block text-xs text-purple-300 underline" data-testid="preview-link">
          👁️ اعرض موقعك في تبويب جديد للمعاينة
        </a>
      </div>

      {(catalog?.widgets || []).map((w) => {
        const cur = styles[w.id] || {};
        const curVariant = cur.variant || (w.variants[0] && w.variants[0].id);
        const curPos = cur.position || w.default_pos;
        const hidden = !!cur.hidden;
        return (
          <div key={w.id} className={`rounded-xl border p-4 ${hidden ? 'bg-red-500/5 border-red-500/20 opacity-75' : 'bg-white/3 border-white/10'}`} data-testid={`wid-${w.id}`}>
            <div className="flex items-start justify-between gap-2 mb-3">
              <div className="flex-1">
                <h4 className="font-black text-sm">{w.name_ar}</h4>
                <p className="text-[11px] opacity-60">{w.description_ar}</p>
              </div>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                  <input type="checkbox" checked={hidden} onChange={(e) => save(w.id, { hidden: e.target.checked })}
                    data-testid={`wid-${w.id}-hide`} />
                  <span className="opacity-75">إخفاء</span>
                </label>
                <button onClick={() => reset(w.id)} className="text-[10px] text-yellow-300 hover:underline"
                  data-testid={`wid-${w.id}-reset`}>↺ افتراضي</button>
              </div>
            </div>

            {!hidden && (
              <>
                {/* VARIANTS */}
                <div className="mb-3">
                  <label className="text-[11px] opacity-70 block mb-1.5">🎨 الشكل</label>
                  <div className="flex flex-wrap gap-1.5">
                    {w.variants.map((v) => (
                      <button key={v.id}
                        onClick={() => save(w.id, { variant: v.id })}
                        className={`px-3 py-1.5 rounded-lg text-[11px] font-bold ${curVariant === v.id ? 'bg-gradient-to-r from-yellow-400 to-orange-500 text-black' : 'bg-white/5 hover:bg-white/10'}`}
                        data-testid={`wid-${w.id}-variant-${v.id}`}>
                        {v.name_ar}
                      </button>
                    ))}
                  </div>
                </div>

                {/* POSITIONS */}
                {w.supports_position && (
                  <div className="mb-3">
                    <label className="text-[11px] opacity-70 block mb-1.5">📍 الموقع</label>
                    <div className="grid grid-cols-3 gap-1.5">
                      {(catalog?.positions || []).map((p) => (
                        <button key={p}
                          onClick={() => save(w.id, { position: p })}
                          className={`px-2 py-1.5 rounded text-[11px] font-bold ${curPos === p ? 'bg-purple-500 text-white' : 'bg-white/5 hover:bg-white/10'}`}
                          data-testid={`wid-${w.id}-pos-${p}`}>
                          {posLabels[p] || p}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* OFFSETS — fine nudge */}
                {w.supports_position && (
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    <div>
                      <label className="text-[10px] opacity-60 block">تحريك أفقي (px)</label>
                      <input type="number" value={cur.offset_x || 0}
                        onChange={(e) => save(w.id, { offset_x: parseInt(e.target.value) || 0 })}
                        className="w-full px-2 py-1 bg-white/5 border border-white/15 rounded text-sm"
                        data-testid={`wid-${w.id}-ox`} />
                    </div>
                    <div>
                      <label className="text-[10px] opacity-60 block">تحريك عمودي (px)</label>
                      <input type="number" value={cur.offset_y || 0}
                        onChange={(e) => save(w.id, { offset_y: parseInt(e.target.value) || 0 })}
                        className="w-full px-2 py-1 bg-white/5 border border-white/15 rounded text-sm"
                        data-testid={`wid-${w.id}-oy`} />
                    </div>
                  </div>
                )}

                {/* 🖱️ DRAG-TO-POSITION MINI CANVAS */}
                {w.supports_position && (
                  <div className="mt-3">
                    <label className="text-[11px] opacity-70 block mb-1.5">🖱️ اسحب الأيقونة لتثبيت مكانها على الشاشة</label>
                    <DragPositionCanvas
                      widget={w}
                      position={curPos}
                      offsetX={cur.offset_x || 0}
                      offsetY={cur.offset_y || 0}
                      onChange={(patch) => save(w.id, patch)}
                    />
                  </div>
                )}
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}

function LoyaltyTab({ token }) {  const [s, setS] = useState({ enabled: true, welcome_bonus: 50, points_per_sar: 1, redeem_rate: 0.1, referral_bonus: 100 });
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    fetch(`${API}/api/websites/client/loyalty-settings`, { headers: authH(token) }).then((r) => r.json()).then((d) => setS((p) => ({ ...p, ...d })));
  }, [token]);
  const save = async () => {
    setBusy(true);
    try {
      await fetch(`${API}/api/websites/client/loyalty-settings`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...authH(token) }, body: JSON.stringify(s) });
      toast.success('✓ تم الحفظ');
    } catch (_) { toast.error('فشل'); } finally { setBusy(false); }
  };
  return (
    <div className="bg-gradient-to-br from-pink-500/10 to-purple-500/5 border border-pink-500/30 rounded-xl p-4" data-testid="loyalty-tab">
      <h3 className="font-black text-pink-300 mb-3">🎁 نظام نقاط الولاء</h3>
      <label className="flex items-center gap-2 mb-3 cursor-pointer">
        <input type="checkbox" checked={s.enabled} onChange={(e) => setS({ ...s, enabled: e.target.checked })} className="w-4 h-4" />
        <span className="text-sm">تفعيل نظام النقاط</span>
      </label>
      <div className="grid grid-cols-2 gap-2">
        <div><label className="text-[11px] opacity-70 block mb-1">🎁 نقاط ترحيبية</label><input type="number" value={s.welcome_bonus} onChange={(e) => setS({ ...s, welcome_bonus: +e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" data-testid="welcome-bonus" /></div>
        <div><label className="text-[11px] opacity-70 block mb-1">⭐ نقاط لكل 1 ر.س</label><input type="number" step="0.1" value={s.points_per_sar} onChange={(e) => setS({ ...s, points_per_sar: +e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" /></div>
        <div><label className="text-[11px] opacity-70 block mb-1">💱 قيمة النقطة (ر.س)</label><input type="number" step="0.01" value={s.redeem_rate} onChange={(e) => setS({ ...s, redeem_rate: +e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" /></div>
        <div><label className="text-[11px] opacity-70 block mb-1">👥 نقاط الإحالة</label><input type="number" value={s.referral_bonus} onChange={(e) => setS({ ...s, referral_bonus: +e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded text-sm" /></div>
      </div>
      <div className="text-[11px] opacity-60 mt-2">مثال: 10 نقاط = 1 ر.س خصم عند الطلب التالي</div>
      <button onClick={save} disabled={busy} className="w-full mt-3 py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-lg font-black text-sm" data-testid="save-loyalty">{busy ? '...' : '💾 حفظ'}</button>
    </div>
  );
}

/* ================================================================
   STORIES + BANNER TAB — Instagram-style stories + animated banner with AI media gen
   ================================================================ */
function StoriesTab({ token, slug }) {
  const [stories, setStories] = useState([]);
  const [banner, setBanner] = useState(null);
  const [genPrompt, setGenPrompt] = useState('');
  const [genBusy, setGenBusy] = useState(false);
  const [vidPrompt, setVidPrompt] = useState('');
  const [vidDuration, setVidDuration] = useState(4);
  const [vidJob, setVidJob] = useState(null);
  const [tab, setTab] = useState('templates'); // 'templates' | 'stories' | 'banner' | 'autopilot'
  const [templates, setTemplates] = useState([]);
  const [tplPicked, setTplPicked] = useState(null);
  const [tplFields, setTplFields] = useState({});
  const [tplBusy, setTplBusy] = useState(false);
  const [tplCategory, setTplCategory] = useState('all');
  const [apSuggestions, setApSuggestions] = useState([]);
  const [apSettings, setApSettings] = useState(null);
  const [apBusy, setApBusy] = useState(false);
  const fileRef = useRef(null);

  const headers = { 'Content-Type': 'application/json', ...authH(token) };

  const loadAll = useCallback(async () => {
    try {
      const [sR, bR, tR] = await Promise.all([
        fetch(`${API}/api/websites/client/stories`, { headers: authH(token) }),
        fetch(`${API}/api/websites/client/banner`, { headers: authH(token) }),
        fetch(`${API}/api/websites/client/stories/templates`, { headers: authH(token) }),
      ]);
      const sD = await sR.json(); const bD = await bR.json(); const tD = await tR.json();
      setStories(sD.stories || []);
      setBanner({
        enabled: !!bD.enabled, type: bD.type || 'image',
        media_url: bD.media_url || '',
        title: bD.title || '', subtitle: bD.subtitle || '',
        cta_text: bD.cta_text || '', cta_link: bD.cta_link || '',
        animation: bD.animation || 'kenburns',
        overlay_opacity: bD.overlay_opacity ?? 0.45,
      });
      setTemplates(tD.templates || []);
    } catch (_) { toast.error('فشل التحميل'); }
  }, [token]);
  useEffect(() => { loadAll(); }, [loadAll]);

  // Poll video job
  useEffect(() => {
    if (!vidJob || vidJob.status === 'done' || vidJob.status === 'failed') return;
    const t = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/websites/client/media/jobs/${vidJob.job_id}`, { headers: authH(token) });
        if (!r.ok) return;
        const d = await r.json();
        setVidJob({ ...vidJob, ...d });
        if (d.status === 'done') { clearInterval(t); toast.success('🎬 تم توليد الفيديو'); loadAll(); }
        if (d.status === 'failed') { clearInterval(t); toast.error('فشل توليد الفيديو'); }
      } catch (_) {}
    }, 5000);
    return () => clearInterval(t);
  }, [vidJob, token, loadAll]);

  const uploadFile = async (file) => {
    if (!file) return;
    if (file.size > 6 * 1024 * 1024) { toast.error('الملف كبير جداً (الحد 6 ميجا)'); return; }
    setGenBusy(true);
    try {
      const reader = new FileReader();
      reader.onload = async () => {
        const dataUrl = reader.result;
        const isVideo = file.type.startsWith('video/');
        const r = await fetch(`${API}/api/websites/client/stories`, {
          method: 'POST', headers,
          body: JSON.stringify({
            type: isVideo ? 'video' : 'image',
            media_url: dataUrl,
            caption: '', duration_sec: 6, visible: true,
          }),
        });
        if (!r.ok) throw new Error('فشل الرفع');
        toast.success('✅ تمت الإضافة');
        loadAll();
      };
      reader.readAsDataURL(file);
    } catch (e) { toast.error(e.message); }
    finally { setGenBusy(false); }
  };

  const generateImage = async () => {
    if (!genPrompt.trim()) return;
    setGenBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/media/generate-image`, {
        method: 'POST', headers,
        body: JSON.stringify({ prompt: genPrompt, add_as_story: true }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل التوليد');
      toast.success('✨ تم التوليد وإضافته كحالة');
      setGenPrompt('');
      loadAll();
    } catch (e) { toast.error(e.message); }
    finally { setGenBusy(false); }
  };

  const generateVideo = async () => {
    if (!vidPrompt.trim()) return;
    try {
      const r = await fetch(`${API}/api/websites/client/media/generate-video`, {
        method: 'POST', headers,
        body: JSON.stringify({ prompt: vidPrompt, duration: vidDuration, size: '1024x1792', add_as_story: true }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setVidJob({ job_id: d.job_id, status: 'queued', prompt: vidPrompt });
      toast.success(`🎬 بدأ التوليد (≈${Math.round(d.estimated_seconds / 60)} دقيقة)`);
      setVidPrompt('');
    } catch (e) { toast.error(e.message); }
  };

  const patchStory = async (id, body) => {
    await fetch(`${API}/api/websites/client/stories/${id}`, { method: 'PATCH', headers, body: JSON.stringify(body) });
    loadAll();
  };
  const delStory = async (id) => {
    if (!window.confirm('حذف هذه الحالة؟')) return;
    await fetch(`${API}/api/websites/client/stories/${id}`, { method: 'DELETE', headers: authH(token) });
    loadAll();
  };

  const saveBanner = async () => {
    setGenBusy(true);
    try {
      await fetch(`${API}/api/websites/client/banner`, { method: 'PUT', headers, body: JSON.stringify(banner) });
      toast.success('✅ تم حفظ البنر');
    } catch (_) { toast.error('فشل'); }
    finally { setGenBusy(false); }
  };

  const pickTemplate = (t) => {
    setTplPicked(t);
    const init = {};
    (t.fields || []).forEach(f => { init[f.name] = f.default ?? ''; });
    setTplFields(init);
  };

  const loadAutopilot = useCallback(async () => {
    try {
      const [sR, gR] = await Promise.all([
        fetch(`${API}/api/websites/client/autopilot/settings`, { headers: authH(token) }),
        fetch(`${API}/api/websites/client/autopilot/suggestions`, { headers: authH(token) }),
      ]);
      setApSettings(await sR.json());
      const g = await gR.json();
      setApSuggestions(g.suggestions || []);
    } catch (_) { toast.error('فشل تحميل AutoPilot'); }
  }, [token]);

  const applySuggestion = async (sug) => {
    setApBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/stories/from-template`, {
        method: 'POST', headers,
        body: JSON.stringify({ template_id: sug.template_id, fields: sug.fields }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      if (d.type === 'image') {
        toast.success('✨ تم نشر الـ Story الذكي!');
        loadAll(); loadAutopilot();
      } else {
        toast.success(`🎬 بدأ توليد الفيديو الذكي`);
        setVidJob({ job_id: d.job_id, status: 'queued', prompt: sug.name });
      }
    } catch (e) { toast.error(e.message); }
    finally { setApBusy(false); }
  };

  const saveAutopilot = async (patch) => {
    setApBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/autopilot/settings`, {
        method: 'PUT', headers, body: JSON.stringify(patch),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setApSettings(d);
      toast.success('✅ تم الحفظ');
    } catch (e) { toast.error(e.message); }
    finally { setApBusy(false); }
  };

  const runAutopilotNow = async () => {
    setApBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/autopilot/run-now`, { method: 'POST', headers });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      toast.success('✨ تم نشر Story تلقائياً!');
      loadAll(); loadAutopilot();
    } catch (e) { toast.error(e.message); }
    finally { setApBusy(false); }
  };
  const applyTemplate = async () => {
    if (!tplPicked) return;
    const required = (tplPicked.fields || []).filter(f => f.required);
    for (const f of required) {
      const v = String(tplFields[f.name] ?? '').trim();
      if (!v) { toast.error(`الرجاء تعبئة: ${f.label}`); return; }
    }
    setTplBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/stories/from-template`, {
        method: 'POST', headers,
        body: JSON.stringify({ template_id: tplPicked.id, fields: tplFields }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      if (d.type === 'image') {
        toast.success('✨ تم إنشاء الـ Story بنقرة واحدة!');
        setTplPicked(null);
        loadAll();
      } else if (d.type === 'video') {
        toast.success(`🎬 بدأ توليد الفيديو (≈${Math.round(d.estimated_seconds / 60)} دقيقة)`);
        setVidJob({ job_id: d.job_id, status: 'queued', prompt: tplPicked.name });
        setTplPicked(null);
      }
    } catch (e) { toast.error(e.message); }
    finally { setTplBusy(false); }
  };

  if (!banner) return <div className="p-6 text-white/50">جارٍ التحميل...</div>;

  return (
    <div className="space-y-5 p-4 md:p-6" data-testid="stories-tab">
      <div className="bg-gradient-to-br from-orange-500/10 via-pink-500/10 to-purple-500/10 border border-orange-400/30 rounded-2xl p-5">
        <h2 className="text-2xl font-black mb-1 flex items-center gap-2"><span>🎬</span> الحالات والبنر المتحرك</h2>
        <p className="text-sm text-white/70">اعرض إعلانات وفيديوهات على الصفحة الرئيسية لمتجرك بأسلوب فخم وسلس — توليد بـ AI أو رفع مباشر.</p>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-1 p-1 bg-white/5 rounded-xl w-fit">
        {[
          { id: 'templates', label: '⚡ قوالب جاهزة' },
          { id: 'autopilot', label: '🤖 AutoPilot' },
          { id: 'stories', label: '⭕ الحالات' },
          { id: 'banner', label: '🌅 البنر المتحرك' },
        ].map(t => (
          <button key={t.id} onClick={() => { setTab(t.id); if (t.id === 'autopilot' && !apSettings) loadAutopilot(); }}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition ${tab === t.id ? 'bg-yellow-500 text-black' : 'hover:bg-white/5'}`}
            data-testid={`stories-subtab-${t.id}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'autopilot' && (
        <div className="space-y-4" data-testid="autopilot-panel">
          <div className="bg-gradient-to-br from-yellow-500/10 via-orange-500/10 to-pink-500/10 border border-yellow-400/30 rounded-2xl p-5">
            <h3 className="text-xl font-black mb-1 flex items-center gap-2"><span>🤖</span> AutoPilot الذكي</h3>
            <p className="text-sm text-white/70">نظام ذكي يقترح وينشر Stories مناسبة لتوقيت المتجر، مبيعاته، وأنشطته. اضغط نشر أو فعّل التشغيل التلقائي.</p>
          </div>

          {/* Suggestions */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-bold text-sm">💡 اقتراحات ذكية لك الآن</h4>
              <button onClick={loadAutopilot} className="text-[11px] opacity-70 hover:opacity-100" data-testid="ap-refresh">🔄 تحديث</button>
            </div>
            {apSuggestions.length === 0 ? (
              <div className="text-center py-6 text-sm opacity-60">لا توجد اقتراحات حالياً — متجرك نشط بالفعل! 🎉</div>
            ) : (
              <div className="space-y-3">
                {apSuggestions.map((s, i) => (
                  <div key={i} className="bg-gradient-to-r from-white/5 to-transparent border border-white/10 rounded-xl p-3 flex items-start gap-3" data-testid={`ap-sug-${i}`}>
                    <div className="text-3xl">{s.emoji}</div>
                    <div className="flex-1 min-w-0">
                      <div className="font-bold text-sm">{s.name}</div>
                      <div className="text-[11px] opacity-70 mt-0.5 leading-snug">{s.reason}</div>
                      {Object.keys(s.fields || {}).length > 0 && (
                        <div className="text-[10px] opacity-50 mt-1 font-mono">
                          {Object.entries(s.fields).filter(([_, v]) => v !== '' && v != null).map(([k, v]) => `${k}=${v}`).join(' · ')}
                        </div>
                      )}
                    </div>
                    <button onClick={() => applySuggestion(s)} disabled={apBusy}
                      className="px-3 py-2 bg-yellow-500 hover:bg-yellow-400 text-black text-xs font-black rounded-lg disabled:opacity-50 whitespace-nowrap"
                      data-testid={`ap-apply-${i}`}>
                      {apBusy ? '...' : '✨ نشر الآن'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Settings */}
          {apSettings && (
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3">
              <h4 className="font-bold text-sm flex items-center gap-2">⚙️ النشر التلقائي</h4>
              <label className="flex items-center justify-between gap-3 cursor-pointer p-3 bg-white/3 rounded-lg">
                <div>
                  <div className="font-bold text-sm">تفعيل النشر التلقائي</div>
                  <div className="text-[11px] opacity-60 mt-0.5">يقوم AutoPilot بنشر Story جديد حسب التردد المختار — يوفّر عليك وقت ويُبقي متجرك نشطاً</div>
                </div>
                <input type="checkbox" checked={!!apSettings.enabled} onChange={(e) => saveAutopilot({ enabled: e.target.checked })}
                  className="w-5 h-5" data-testid="ap-enabled-toggle" />
              </label>

              <label className="block">
                <span className="text-[11px] opacity-70">التردد</span>
                <select value={apSettings.frequency} onChange={(e) => saveAutopilot({ frequency: e.target.value })}
                  className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" data-testid="ap-frequency">
                  <option value="weekly">📅 أسبوعياً (مُوصى به)</option>
                  <option value="biweekly">📆 كل أسبوعين</option>
                  <option value="monthly">🗓️ شهرياً</option>
                </select>
              </label>

              {apSettings.next_run_at && apSettings.enabled && (
                <div className="text-[11px] opacity-70 p-2 bg-emerald-500/5 border border-emerald-500/20 rounded">
                  ⏰ الموعد التالي: {new Date(apSettings.next_run_at).toLocaleString('ar-SA')}
                </div>
              )}

              <button onClick={runAutopilotNow} disabled={apBusy}
                className="w-full py-2.5 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg font-black text-sm disabled:opacity-50"
                data-testid="ap-run-now">
                {apBusy ? '⏳ جارٍ النشر...' : '🚀 نشر AutoPilot Story الآن (يدوي)'}
              </button>

              {/* History */}
              {apSettings.history?.length > 0 && (
                <div>
                  <div className="text-[11px] opacity-70 mb-1">السجل الأخير ({apSettings.history.length})</div>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {apSettings.history.slice().reverse().map((h, i) => (
                      <div key={i} className="text-[11px] p-2 bg-black/20 rounded flex items-center justify-between gap-2" data-testid={`ap-history-${i}`}>
                        <div className="truncate flex-1">{h.caption}</div>
                        <span className="opacity-50 flex-shrink-0">{new Date(h.at).toLocaleDateString('ar-SA')}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'templates' && (
        <div className="space-y-4" data-testid="templates-panel">
          {/* Category filter */}
          <div className="flex flex-wrap gap-1.5">
            {[
              { id: 'all', label: 'الكل' },
              { id: 'sale', label: '⚡ خصومات' },
              { id: 'new_product', label: '✨ منتج جديد' },
              { id: 'thanks', label: '💖 شكر' },
              { id: 'event', label: '🎉 فعاليات' },
              { id: 'feature', label: '🌟 مميزات' },
              { id: 'announcement', label: '📢 إعلانات' },
              { id: 'reminder', label: '🔔 تذكير' },
            ].map(c => (
              <button key={c.id} onClick={() => setTplCategory(c.id)}
                className={`px-3 py-1 rounded-full text-xs font-bold ${tplCategory === c.id ? 'bg-yellow-500 text-black' : 'bg-white/5 hover:bg-white/10'}`}
                data-testid={`tpl-cat-${c.id}`}>
                {c.label}
              </button>
            ))}
          </div>

          {/* Templates grid */}
          {templates.length === 0 ? (
            <div className="text-center py-10 opacity-60 text-sm">جارٍ تحميل القوالب...</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {templates
                .filter(t => tplCategory === 'all' || t.category === tplCategory)
                .map((t) => (
                  <button key={t.id} onClick={() => pickTemplate(t)}
                    className="bg-gradient-to-br from-white/5 to-white/0 hover:from-yellow-500/10 hover:to-orange-500/5 border border-white/10 hover:border-yellow-500/40 rounded-xl p-4 text-right transition-all group"
                    data-testid={`tpl-${t.id}`}>
                    <div className="text-3xl mb-2">{t.emoji}</div>
                    <div className="font-bold text-sm group-hover:text-yellow-300">{t.name}</div>
                    <div className="text-[11px] opacity-60 mt-1 leading-snug">{t.description}</div>
                    <div className="mt-2 flex items-center gap-1.5 text-[10px]">
                      <span className={`px-1.5 py-0.5 rounded ${t.output === 'video' ? 'bg-purple-500/20 text-purple-300' : 'bg-emerald-500/20 text-emerald-300'}`}>
                        {t.output === 'video' ? '🎥 فيديو' : '🖼️ صورة'}
                      </span>
                      {t.output === 'video' && <span className="opacity-60">{t.duration_sec}ث</span>}
                    </div>
                  </button>
                ))}
            </div>
          )}

          {/* Picked template modal */}
          {tplPicked && (
            <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={(e) => { if (e.target === e.currentTarget) setTplPicked(null); }} data-testid="tpl-modal">
              <div className="bg-[#0e1128] border border-yellow-500/30 rounded-2xl p-5 max-w-md w-full max-h-[85vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-black flex items-center gap-2">
                    <span className="text-2xl">{tplPicked.emoji}</span>
                    {tplPicked.name}
                  </h3>
                  <button onClick={() => setTplPicked(null)} className="opacity-60 hover:opacity-100 text-xl">×</button>
                </div>
                <div className="text-xs opacity-70 mb-4">{tplPicked.description}</div>

                {(tplPicked.fields || []).length === 0 ? (
                  <div className="text-xs opacity-60 mb-3 p-2 bg-white/5 rounded">هذا القالب لا يحتاج إلى مدخلات — جاهز للإنشاء فوراً.</div>
                ) : (
                  <div className="space-y-3 mb-4">
                    {(tplPicked.fields || []).map((f) => (
                      <label key={f.name} className="block">
                        <span className="text-xs opacity-70 mb-1 block">
                          {f.label}{f.required && <span className="text-red-400 mr-1">*</span>}
                        </span>
                        <input
                          type={f.type === 'number' ? 'number' : 'text'}
                          value={tplFields[f.name] ?? ''}
                          onChange={(e) => setTplFields({ ...tplFields, [f.name]: e.target.value })}
                          placeholder={f.default ? String(f.default) : ''}
                          className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm"
                          data-testid={`tpl-field-${f.name}`}
                        />
                      </label>
                    ))}
                  </div>
                )}

                <div className="text-[11px] p-2 bg-amber-500/5 border border-amber-500/20 rounded mb-3">
                  💡 سيتم استخدام اسم متجرك ولونه الأساسي تلقائياً للحفاظ على هويتك البصرية.
                </div>

                <button onClick={applyTemplate} disabled={tplBusy}
                  className="w-full py-3 bg-gradient-to-r from-yellow-500 via-orange-500 to-pink-500 text-black rounded-lg font-black text-sm disabled:opacity-50"
                  data-testid="tpl-apply-btn">
                  {tplBusy ? '⏳ جارٍ الإنشاء...' : (tplPicked.output === 'video' ? '🎬 توليد بنقرة واحدة' : '✨ إنشاء بنقرة واحدة')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'stories' && (
        <div className="space-y-4">
          {/* Add: AI image generation */}
          <div className="bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 border border-emerald-400/30 rounded-xl p-4">
            <h3 className="font-bold text-sm mb-2 flex items-center gap-2">✨ توليد صورة بالذكاء الاصطناعي</h3>
            <div className="flex gap-2">
              <input value={genPrompt} onChange={(e) => setGenPrompt(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') generateImage(); }}
                placeholder="مثال: قهوة لاتيه راقية في كوب ذهبي على طاولة خشبية"
                className="flex-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm"
                data-testid="story-image-prompt" />
              <button onClick={generateImage} disabled={genBusy || !genPrompt.trim()}
                className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-black font-black rounded-lg text-sm disabled:opacity-40"
                data-testid="story-gen-image-btn">
                {genBusy ? '⏳' : '✨ توليد'}
              </button>
            </div>
          </div>

          {/* Add: AI video generation (Sora 2) */}
          <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-400/30 rounded-xl p-4">
            <h3 className="font-bold text-sm mb-2 flex items-center gap-2">🎥 توليد فيديو بالذكاء الاصطناعي (Sora 2)</h3>
            <div className="flex gap-2 mb-2">
              <input value={vidPrompt} onChange={(e) => setVidPrompt(e.target.value)}
                placeholder="مثال: مشهد لباريستا يصنع لاتيه فني، إضاءة سينمائية"
                className="flex-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm"
                data-testid="story-video-prompt" />
              <select value={vidDuration} onChange={(e) => setVidDuration(+e.target.value)}
                className="px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm">
                <option value={4}>4 ثوانٍ</option>
                <option value={8}>8 ثوانٍ</option>
                <option value={12}>12 ثانية</option>
              </select>
              <button onClick={generateVideo} disabled={!vidPrompt.trim() || (vidJob && vidJob.status !== 'done' && vidJob.status !== 'failed')}
                className="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white font-black rounded-lg text-sm disabled:opacity-40"
                data-testid="story-gen-video-btn">
                🎬 ابدأ
              </button>
            </div>
            {vidJob && (
              <div className="text-[11px] mt-2 p-2 bg-black/30 rounded-lg" data-testid="video-job-status">
                {vidJob.status === 'queued' && <span className="text-amber-300">⏳ في طابور الانتظار...</span>}
                {vidJob.status === 'processing' && <span className="text-blue-300 animate-pulse">🎥 جارٍ التوليد (قد تستغرق عدة دقائق)...</span>}
                {vidJob.status === 'done' && <span className="text-emerald-300">✅ تم! تجد الفيديو في القائمة بالأسفل.</span>}
                {vidJob.status === 'failed' && <span className="text-red-300">❌ فشل: {vidJob.error || 'خطأ غير معروف'}</span>}
              </div>
            )}
            <div className="text-[10px] opacity-60 mt-1">⚠️ الفيديوهات تستخدم رصيد Universal Key.</div>
          </div>

          {/* Add: Upload */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <h3 className="font-bold text-sm mb-2 flex items-center gap-2">📤 رفع ملف مباشر</h3>
            <div className="flex items-center gap-2">
              <input ref={fileRef} type="file" accept="image/*,video/*" hidden onChange={(e) => uploadFile(e.target.files[0])} data-testid="story-upload-input" />
              <button onClick={() => fileRef.current?.click()} disabled={genBusy}
                className="px-4 py-2 bg-white/10 hover:bg-white/15 rounded-lg text-sm font-bold border border-white/15"
                data-testid="story-upload-btn">
                📁 اختر ملف (صورة أو فيديو)
              </button>
              <span className="text-[10px] opacity-60">الحد الأقصى: 6 ميجا</span>
            </div>
          </div>

          {/* Stories list */}
          <div className="space-y-2">
            <h3 className="font-bold text-sm">الحالات المنشورة ({stories.length})</h3>
            {stories.length === 0 ? (
              <div className="text-center py-8 bg-white/3 border border-dashed border-white/15 rounded-xl text-sm opacity-60">
                لا توجد حالات بعد. ابدأ بتوليد صورة أو رفع ملف.
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {stories.map((s) => (
                  <div key={s.id} className="bg-white/5 border border-white/10 rounded-xl overflow-hidden" data-testid={`story-card-${s.id}`}>
                    <div className="relative bg-black aspect-[9/16]">
                      {s.type === 'video' ? (
                        <video src={s.media_url} className="w-full h-full object-cover" muted playsInline />
                      ) : (
                        <img src={s.media_url} className="w-full h-full object-cover" alt="" />
                      )}
                      {s.type === 'video' && (
                        <span className="absolute top-2 left-2 bg-purple-500/80 text-white text-[10px] px-1.5 py-0.5 rounded font-bold">▶ فيديو</span>
                      )}
                      {s.ai_generated && (
                        <span className="absolute top-2 right-2 bg-emerald-500/80 text-white text-[10px] px-1.5 py-0.5 rounded font-bold">✨ AI</span>
                      )}
                    </div>
                    <div className="p-2 space-y-1.5">
                      <input value={s.caption || ''} onChange={(e) => patchStory(s.id, { caption: e.target.value })}
                        placeholder="تعليق" className="w-full px-2 py-1 bg-black/30 border border-white/10 rounded text-xs" />
                      <input value={s.link || ''} onChange={(e) => patchStory(s.id, { link: e.target.value })}
                        placeholder="رابط (اختياري)" className="w-full px-2 py-1 bg-black/30 border border-white/10 rounded text-xs" />
                      <div className="flex items-center justify-between gap-1">
                        <label className="flex items-center gap-1 text-[11px] cursor-pointer">
                          <input type="checkbox" checked={s.visible !== false} onChange={(e) => patchStory(s.id, { visible: e.target.checked })} />
                          ظاهرة
                        </label>
                        <button onClick={() => delStory(s.id)} className="text-[11px] text-red-400 hover:text-red-300" data-testid={`del-story-${s.id}`}>🗑️ حذف</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'banner' && banner && (
        <div className="space-y-3 bg-white/5 border border-white/10 rounded-xl p-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={banner.enabled} onChange={(e) => setBanner({ ...banner, enabled: e.target.checked })} data-testid="banner-enabled-toggle" />
            <span className="font-bold">تفعيل البنر المتحرك على الصفحة الرئيسية</span>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block">
              <span className="text-[11px] opacity-70">نوع المحتوى</span>
              <select value={banner.type} onChange={(e) => setBanner({ ...banner, type: e.target.value })}
                className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm">
                <option value="image">صورة</option>
                <option value="video">فيديو</option>
              </select>
            </label>
            <label className="block">
              <span className="text-[11px] opacity-70">نوع الحركة</span>
              <select value={banner.animation} onChange={(e) => setBanner({ ...banner, animation: e.target.value })}
                className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" data-testid="banner-animation">
                <option value="kenburns">Ken Burns (زوم بطيء)</option>
                <option value="parallax">Parallax (تحريك بالتمرير)</option>
                <option value="fade">تلاشي</option>
                <option value="none">بدون</option>
              </select>
            </label>
          </div>
          <label className="block">
            <span className="text-[11px] opacity-70">رابط الوسائط (URL خارجي أو data: URL)</span>
            <input value={banner.media_url} onChange={(e) => setBanner({ ...banner, media_url: e.target.value })}
              placeholder="https://... أو ارفع من تبويب الحالات"
              className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm font-mono" data-testid="banner-media-url" />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block">
              <span className="text-[11px] opacity-70">العنوان الرئيسي</span>
              <input value={banner.title} onChange={(e) => setBanner({ ...banner, title: e.target.value })}
                placeholder="عرض حصري" className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" />
            </label>
            <label className="block">
              <span className="text-[11px] opacity-70">العنوان الفرعي</span>
              <input value={banner.subtitle} onChange={(e) => setBanner({ ...banner, subtitle: e.target.value })}
                placeholder="خصم 20% على أول طلب" className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" />
            </label>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <label className="block">
              <span className="text-[11px] opacity-70">نص زر الـ CTA</span>
              <input value={banner.cta_text} onChange={(e) => setBanner({ ...banner, cta_text: e.target.value })}
                placeholder="تسوق الآن" className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" />
            </label>
            <label className="block">
              <span className="text-[11px] opacity-70">رابط الـ CTA</span>
              <input value={banner.cta_link} onChange={(e) => setBanner({ ...banner, cta_link: e.target.value })}
                placeholder="#products" className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm font-mono" />
            </label>
          </div>
          <button onClick={saveBanner} disabled={genBusy}
            className="w-full py-2.5 bg-gradient-to-r from-orange-500 to-pink-500 text-white rounded-lg font-black text-sm disabled:opacity-50"
            data-testid="save-banner-btn">
            {genBusy ? '...' : '💾 حفظ البنر'}
          </button>
        </div>
      )}
    </div>
  );
}

function ChatbotTab({ token, slug }) {
  const [cfg, setCfg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testReply, setTestReply] = useState('');
  const [analyticsTab, setAnalyticsTab] = useState('settings'); // 'settings' | 'analytics'
  const [analytics, setAnalytics] = useState(null);
  const [testInput, setTestInput] = useState('ما هي أسعاركم؟');

  useEffect(() => {
    fetch(`${API}/api/websites/client/chatbot/config`, { headers: authH(token) })
      .then((r) => r.json())
      .then((d) => setCfg({
        enabled: !!d.enabled,
        welcome_message: d.welcome_message || '',
        business_hours: d.business_hours || '',
        extra_context: d.extra_context || '',
        notify_whatsapp: d.notify_whatsapp || '',
        usage: d.usage || {},
      }))
      .catch(() => setCfg({ enabled: false, welcome_message: '', business_hours: '', extra_context: '', notify_whatsapp: '', usage: {} }));
  }, [token]);

  const save = async () => {
    if (!cfg) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/chatbot/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({
          enabled: cfg.enabled,
          welcome_message: cfg.welcome_message,
          business_hours: cfg.business_hours,
          extra_context: cfg.extra_context,
          notify_whatsapp: cfg.notify_whatsapp,
        }),
      });
      if (!r.ok) throw new Error();
      toast.success('✅ تم حفظ إعدادات المساعد الذكي');
    } catch (_) { toast.error('فشل الحفظ'); }
    finally { setBusy(false); }
  };

  const tryIt = async () => {
    if (!testInput.trim()) return;
    setTesting(true); setTestReply('');
    try {
      const r = await fetch(`${API}/api/websites/public/${slug}/chatbot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: testInput, session_id: 'preview-' + Date.now() }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setTestReply(d.reply || '(لا يوجد رد)');
    } catch (e) {
      setTestReply('⚠️ ' + (e.message || 'تعذّر الاتصال — تأكد من تفعيل المساعد وحفظه أولاً.'));
    } finally { setTesting(false); }
  };

  if (!cfg) return <div className="p-6 text-white/50">جارٍ التحميل...</div>;

  const totalMsgs = Object.values(cfg.usage || {}).reduce((sum, m) => sum + ((m && m.messages) || 0), 0);

  const loadAnalytics = async () => {
    try {
      const r = await fetch(`${API}/api/websites/client/chatbot/analytics?days=30`, { headers: authH(token) });
      const d = await r.json();
      setAnalytics(d);
    } catch (_) { toast.error('فشل تحميل التحليلات'); }
  };

  return (
    <div className="space-y-5 p-4 md:p-6" data-testid="chatbot-tab">
      <div className="bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 border border-emerald-400/30 rounded-2xl p-5">
        <h2 className="text-2xl font-black mb-1 flex items-center gap-2"><span>🤖</span> المساعد الذكي للزبائن</h2>
        <p className="text-sm text-white/60">يجاوب زبائنك تلقائياً على الأسعار، المنتجات، ساعات العمل وأكثر — مدعوم بـ Claude Sonnet.</p>
      </div>

      <div className="flex gap-1 p-1 bg-white/5 rounded-xl w-fit">
        {[
          { id: 'settings', label: '⚙️ الإعدادات' },
          { id: 'analytics', label: '📊 تحليلات المحادثات' },
        ].map(t => (
          <button key={t.id} onClick={() => { setAnalyticsTab(t.id); if (t.id === 'analytics' && !analytics) loadAnalytics(); }}
            className={`px-4 py-2 rounded-lg text-sm font-bold ${analyticsTab === t.id ? 'bg-emerald-500 text-black' : 'hover:bg-white/5'}`}
            data-testid={`chatbot-subtab-${t.id}`}>
            {t.label}
          </button>
        ))}
      </div>

      {analyticsTab === 'settings' && (<>
      {/* Toggle */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex items-center justify-between">
        <div>
          <div className="font-bold text-sm">تفعيل المساعد على المتجر</div>
          <div className="text-[11px] opacity-60 mt-0.5">سيظهر زر دردشة عائم 💬 على صفحة متجرك</div>
        </div>
        <label className="cursor-pointer">
          <input type="checkbox" checked={!!cfg.enabled} onChange={(e) => setCfg({ ...cfg, enabled: e.target.checked })} className="sr-only" data-testid="chatbot-enabled-toggle" />
          <div className={`w-12 h-6 rounded-full p-0.5 transition-colors ${cfg.enabled ? 'bg-emerald-500' : 'bg-white/10'}`}>
            <div className={`w-5 h-5 rounded-full bg-white transition-transform ${cfg.enabled ? 'translate-x-6' : ''}`} />
          </div>
        </label>
      </div>

      {/* Welcome message */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3">
        <label className="block">
          <span className="text-xs text-white/60">رسالة الترحيب (اختياري)</span>
          <input
            type="text"
            value={cfg.welcome_message}
            onChange={(e) => setCfg({ ...cfg, welcome_message: e.target.value })}
            placeholder="مرحباً! كيف أساعدك اليوم؟"
            maxLength={200}
            className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm"
            data-testid="chatbot-welcome-input"
          />
        </label>
        <label className="block">
          <span className="text-xs text-white/60">ساعات العمل (لإخبار الزبون)</span>
          <input
            type="text"
            value={cfg.business_hours}
            onChange={(e) => setCfg({ ...cfg, business_hours: e.target.value })}
            placeholder="السبت - الخميس · 9 صباحاً إلى 11 مساءً"
            maxLength={120}
            className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm"
            data-testid="chatbot-hours-input"
          />
        </label>
        <label className="block">
          <span className="text-xs text-white/60">معلومات إضافية للمساعد (سياسات الإرجاع، رسوم التوصيل، إلخ)</span>
          <textarea
            value={cfg.extra_context}
            onChange={(e) => setCfg({ ...cfg, extra_context: e.target.value })}
            placeholder="مثال: نوصّل لجميع مدن المملكة. الإرجاع متاح خلال 7 أيام. للطلبات بالجملة تواصل واتساب."
            maxLength={1500}
            rows={4}
            className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm font-mono leading-relaxed"
            data-testid="chatbot-context-input"
          />
          <div className="text-[10px] opacity-50 mt-1 text-left">{(cfg.extra_context || '').length}/1500</div>
        </label>
        <label className="block">
          <span className="text-xs text-white/60">📲 رقم واتساب لاستلام إشعارات تواصل الزبائن (اختياري)</span>
          <input
            type="tel"
            value={cfg.notify_whatsapp || ''}
            onChange={(e) => setCfg({ ...cfg, notify_whatsapp: e.target.value })}
            placeholder="966500000000 (شامل رمز الدولة)"
            className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm font-mono"
            data-testid="chatbot-notify-whatsapp"
          />
          <div className="text-[10px] opacity-60 mt-1">
            🔔 لما يطلب زبون التواصل مع موظف، يصلك رابط واتساب جاهز تنقر عليه فيفتح المحادثة بنص الطلب.
          </div>
        </label>
      </div>

      <button
        onClick={save}
        disabled={busy}
        className="w-full py-2.5 bg-gradient-to-r from-emerald-500 to-cyan-500 text-black rounded-lg font-black text-sm disabled:opacity-50"
        data-testid="save-chatbot-btn"
      >
        {busy ? '...' : '💾 حفظ الإعدادات'}
      </button>

      {/* Try-it preview (only after saving + enabled) */}
      {cfg.enabled && (
        <div className="bg-white/5 border border-emerald-400/20 rounded-xl p-4">
          <h3 className="font-bold text-sm mb-2 flex items-center gap-2">🧪 جرّب المساعد الآن</h3>
          <div className="flex gap-2">
            <input
              type="text"
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') tryIt(); }}
              className="flex-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm"
              placeholder="اكتب سؤالاً تجريبياً..."
              data-testid="chatbot-test-input"
            />
            <button onClick={tryIt} disabled={testing} className="px-4 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 rounded-lg text-sm font-bold disabled:opacity-50" data-testid="chatbot-test-btn">
              {testing ? '...' : 'إرسال'}
            </button>
          </div>
          {testReply && (
            <div className="mt-3 p-3 bg-black/30 rounded-lg text-sm whitespace-pre-wrap" data-testid="chatbot-test-reply">
              {testReply}
            </div>
          )}
        </div>
      )}

      {/* Usage stats */}
      <div className="bg-white/3 border border-white/5 rounded-xl p-4">
        <div className="text-xs opacity-70">إحصائيات الاستخدام</div>
        <div className="text-2xl font-black mt-1">{totalMsgs} <span className="text-xs font-normal opacity-60">رسالة</span></div>
        <div className="text-[10px] opacity-50">الإجمالي عبر جميع الأشهر</div>
      </div>
      </>)}

      {analyticsTab === 'analytics' && (
        <div className="space-y-4" data-testid="chatbot-analytics-panel">
          {!analytics ? (
            <div className="text-center py-10 opacity-60 text-sm">جارٍ تحميل التحليلات...</div>
          ) : analytics.totals.messages === 0 ? (
            <div className="text-center py-10 bg-white/3 border border-white/5 rounded-xl">
              <div className="text-4xl mb-2">📊</div>
              <div className="text-sm opacity-60">لا توجد محادثات بعد. التحليلات ستظهر بعد أول رسالة من زبائنك.</div>
            </div>
          ) : (
            <>
              {/* KPI cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border border-emerald-500/30 rounded-xl p-3" data-testid="kpi-messages">
                  <div className="text-[11px] opacity-70">إجمالي الرسائل</div>
                  <div className="text-2xl font-black text-emerald-300">{analytics.totals.messages}</div>
                  <div className="text-[10px] opacity-50">آخر {analytics.window_days} يوم</div>
                </div>
                <div className="bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/30 rounded-xl p-3" data-testid="kpi-sessions">
                  <div className="text-[11px] opacity-70">جلسات فريدة</div>
                  <div className="text-2xl font-black text-blue-300">{analytics.totals.unique_sessions}</div>
                  <div className="text-[10px] opacity-50">زبائن مختلفون</div>
                </div>
                <div className="bg-gradient-to-br from-amber-500/10 to-orange-500/5 border border-amber-500/30 rounded-xl p-3" data-testid="kpi-handoffs">
                  <div className="text-[11px] opacity-70">طلبات تواصل بشري</div>
                  <div className="text-2xl font-black text-amber-300">{analytics.totals.handoffs}</div>
                  <div className="text-[10px] opacity-50">تذاكر دعم</div>
                </div>
                <div className="bg-gradient-to-br from-pink-500/10 to-purple-500/5 border border-pink-500/30 rounded-xl p-3" data-testid="kpi-handoff-rate">
                  <div className="text-[11px] opacity-70">نسبة التحويل البشري</div>
                  <div className="text-2xl font-black text-pink-300">{analytics.totals.handoff_rate_pct}%</div>
                  <div className="text-[10px] opacity-50">{analytics.totals.handoff_rate_pct > 30 ? '⚠️ مرتفعة — حسّن الـ context' : '✅ ضمن المعدّل'}</div>
                </div>
              </div>

              {/* Topics bar chart */}
              <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <h3 className="font-bold text-sm mb-3">🔥 أكثر المواضيع طرحاً</h3>
                <div className="space-y-1.5">
                  {analytics.topics.filter(t => t.count > 0).slice(0, 8).map((t, i) => {
                    const max = Math.max(...analytics.topics.map(x => x.count), 1);
                    const pct = (t.count / max) * 100;
                    return (
                      <div key={i} className="flex items-center gap-3" data-testid={`topic-${i}`}>
                        <div className="text-xs w-32 truncate">{t.label}</div>
                        <div className="flex-1 h-5 bg-white/5 rounded overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded transition-all" style={{ width: `${pct}%` }}></div>
                        </div>
                        <div className="text-xs font-bold w-10 text-right">{t.count}</div>
                      </div>
                    );
                  })}
                  {analytics.topics.every(t => t.count === 0) && <div className="text-xs opacity-50 text-center py-3">لم يُكتشف أي موضوع شائع بعد.</div>}
                </div>
              </div>

              {/* Lost questions */}
              {analytics.lost_questions.length > 0 && (
                <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4">
                  <h3 className="font-bold text-sm mb-2 flex items-center gap-2">🚨 أسئلة تطلب المساعدة البشرية</h3>
                  <p className="text-[11px] opacity-70 mb-2">هذه الأسئلة لم يتمكّن المساعد من الإجابة عليها. أضف معلومات عنها في "معلومات إضافية" لتحسين دقة المساعد.</p>
                  <div className="space-y-1.5 max-h-64 overflow-y-auto">
                    {analytics.lost_questions.slice(0, 10).map((q, i) => (
                      <div key={i} className="text-xs bg-black/30 rounded p-2 border-r-2 border-amber-500/50" data-testid={`lost-q-${i}`}>
                        {q.text}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent messages */}
              <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <h3 className="font-bold text-sm mb-2">💬 آخر الرسائل</h3>
                <div className="space-y-1.5 max-h-72 overflow-y-auto">
                  {analytics.recent.map((m, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs">
                      {m.handoff && <span className="text-amber-400">🚨</span>}
                      <span className="opacity-50 text-[10px] flex-shrink-0">{new Date(m.at).toLocaleString('ar-SA', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })}</span>
                      <span className="flex-1 truncate">{m.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              <button onClick={loadAnalytics} className="w-full py-2 bg-white/5 hover:bg-white/10 rounded-lg text-xs font-bold" data-testid="refresh-analytics">
                🔄 تحديث التحليلات
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}


/* ================================================================
   LIVE MAP TAB — drivers + active orders on OpenStreetMap (WebSocket)
   ================================================================ */
function LiveMapTab({ token, slug }) {
  const [data, setData] = useState(null);
  const [wsOnline, setWsOnline] = useState(false);
  const [pendingOrders, setPendingOrders] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [assigning, setAssigning] = useState(false);
  const wsRef = useRef(null);

  const loadInitial = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/websites/client/live-map`, { headers: authH(token) });
      setData(await r.json());
      // Also load pending orders (ones without driver)
      const or = await fetch(`${API}/api/websites/client/orders`, { headers: authH(token) });
      const od = await or.json();
      setPendingOrders((od.orders || []).filter((o) => !o.driver_id && ['pending', 'accepted', 'preparing', 'ready'].includes(o.status)));
    } catch (_) {}
  }, [token]);

  const applyEvent = useCallback((evt) => {
    if (!evt || !evt.type) return;
    setData((prev) => {
      if (!prev) return prev;
      const next = { ...prev, drivers: [...(prev.drivers || [])], orders: [...(prev.orders || [])] };
      if (evt.type === 'location') {
        const d = evt.data || {};
        const idx = next.drivers.findIndex((x) => x.id === d.driver_id);
        if (idx >= 0) next.drivers[idx] = { ...next.drivers[idx], lat: d.lat, lng: d.lng, last_ping: d.at };
        else next.drivers.push({ id: d.driver_id, name: d.driver_name, lat: d.lat, lng: d.lng, last_ping: d.at });
      } else if (evt.type === 'order_created') {
        const d = evt.data || {};
        if (!next.orders.find((o) => o.id === d.order_id))
          next.orders.unshift({ id: d.order_id, customer: d.customer, total: d.total, lat: d.lat, lng: d.lng, status: d.status });
        loadInitial();
      } else if (evt.type === 'order_status') {
        const d = evt.data || {};
        const idx = next.orders.findIndex((o) => o.id === d.order_id);
        if (idx >= 0) next.orders[idx] = { ...next.orders[idx], status: d.status, driver_id: d.driver_id };
      }
      return next;
    });
  }, [loadInitial]);

  useEffect(() => {
    loadInitial();
    if (!slug || !token) return undefined;
    const wsUrl = `${API.replace(/^http/, 'ws')}/api/websites/ws/client/${slug}?token=${encodeURIComponent(token)}`;
    let closedByUs = false, retryTimer = null, pingTimer = null;
    const connect = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => { setWsOnline(true); pingTimer = setInterval(() => { try { ws.send('ping'); } catch (_) {} }, 25000); };
      ws.onmessage = (e) => { try { applyEvent(JSON.parse(e.data)); } catch (_) {} };
      ws.onclose = () => { setWsOnline(false); if (pingTimer) { clearInterval(pingTimer); pingTimer = null; } if (!closedByUs) retryTimer = setTimeout(connect, 3000); };
      ws.onerror = () => { try { ws.close(); } catch (_) {} };
    };
    connect();
    return () => { closedByUs = true; if (retryTimer) clearTimeout(retryTimer); if (pingTimer) clearInterval(pingTimer); if (wsRef.current) try { wsRef.current.close(); } catch (_) {} };
  }, [slug, token, loadInitial, applyEvent]);

  const assignDriver = async (orderId, driverId) => {
    setAssigning(true);
    try {
      await fetch(`${API}/api/websites/client/orders/${orderId}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ driver_id: driverId, status: 'on_the_way' }),
      });
      toast.success('✅ تم تعيين السائق');
      setSelectedOrder(null);
      loadInitial();
    } catch (_) { toast.error('فشل'); }
    finally { setAssigning(false); }
  };

  if (!data) return <div className="text-center py-10 opacity-60">...</div>;

  const center = data.base?.lat ? `${data.base.lat},${data.base.lng}` : (data.drivers[0] ? `${data.drivers[0].lat},${data.drivers[0].lng}` : '24.7136,46.6753');
  const [lat, lng] = center.split(',').map(parseFloat);
  const bbox = `${lng - 0.08}%2C${lat - 0.06}%2C${lng + 0.08}%2C${lat + 0.06}`;
  const osm = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat},${lng}`;
  const minsSince = (iso) => iso ? Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 60000)) : null;

  return (
    <div data-testid="livemap-tab" className="space-y-3">
      {/* HEADER: WS status + command center title */}
      <div className="flex items-center justify-between text-[11px] flex-wrap gap-2">
        <h3 className="font-black text-base flex items-center gap-2">🚀 مركز قيادة السائقين</h3>
        <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full ${wsOnline ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'}`} data-testid="ws-status">
          <span className={`w-1.5 h-1.5 rounded-full ${wsOnline ? 'bg-green-400 animate-pulse' : 'bg-yellow-400'}`}></span>
          {wsOnline ? 'مباشر (WebSocket)' : 'إعادة الاتصال...'}
        </span>
      </div>

      {/* KPI GRID */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div className="bg-gradient-to-br from-yellow-500/10 to-orange-500/5 border border-yellow-500/30 rounded-xl p-3 text-center">
          <div className="text-[10px] opacity-60">المتجر</div>
          <div className="text-lg font-black text-yellow-400">📍 {data.base?.city || 'الرياض'}</div>
        </div>
        <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/5 border border-green-500/30 rounded-xl p-3 text-center">
          <div className="text-[10px] opacity-60">سائقون نشطون</div>
          <div className="text-lg font-black text-green-400">🟢 {data.drivers.length}</div>
        </div>
        <div className="bg-gradient-to-br from-pink-500/10 to-rose-500/5 border border-pink-500/30 rounded-xl p-3 text-center">
          <div className="text-[10px] opacity-60">طلبات فعّالة</div>
          <div className="text-lg font-black text-pink-400">📦 {data.orders.length}</div>
        </div>
        <div className="bg-gradient-to-br from-orange-500/10 to-red-500/5 border border-orange-500/30 rounded-xl p-3 text-center">
          <div className="text-[10px] opacity-60">بانتظار تعيين</div>
          <div className="text-lg font-black text-orange-400">⏳ {pendingOrders.length}</div>
        </div>
      </div>

      {/* LIVE MAP */}
      <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden relative" style={{ aspectRatio: '16/9' }}>
        <iframe src={osm} className="w-full h-full" title="live-map" style={{ border: 0 }} data-testid="live-map-iframe" />
        {data.drivers.length > 0 && (
          <div className="absolute bottom-2 left-2 right-2 bg-black/75 backdrop-blur-sm rounded-lg p-2 text-[11px]">
            🛵 {data.drivers.map((d) => `${d.name} (${d.lat?.toFixed(3)}, ${d.lng?.toFixed(3)})`).join(' · ')}
          </div>
        )}
      </div>

      {/* PENDING ORDERS — needs driver assignment */}
      {pendingOrders.length > 0 && (
        <div className="bg-orange-500/5 border border-orange-500/20 rounded-xl p-3">
          <div className="font-black text-sm mb-2 text-orange-300">⏳ طلبات بانتظار سائق ({pendingOrders.length})</div>
          <div className="space-y-2">
            {pendingOrders.slice(0, 5).map((o) => (
              <div key={o.id} className="bg-white/3 rounded-lg p-2 text-xs flex items-center justify-between gap-2" data-testid={`pending-${o.id}`}>
                <div className="flex-1 min-w-0">
                  <div className="font-bold">#{o.id.slice(0, 6)} · {o.customer_name || o.customer || 'عميل'}</div>
                  <div className="opacity-60 text-[10px]">{o.total} ر.س · {o.status}</div>
                </div>
                <button onClick={() => setSelectedOrder(o)}
                  className="px-3 py-1 bg-orange-500/30 hover:bg-orange-500/50 rounded font-bold text-[10px]"
                  data-testid={`assign-${o.id}`}>
                  👤 عيّن سائق
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* DRIVERS DETAIL */}
      <div className="bg-white/3 border border-white/10 rounded-xl p-3">
        <div className="font-black text-sm mb-2">🛵 السائقون ({data.drivers.length})</div>
        {data.drivers.length === 0 ? (
          <div className="opacity-60 text-xs py-3 text-center">لا سائق يشارك موقعه حالياً — اطلب من السائقين تفعيل مشاركة الموقع من تطبيق السائق</div>
        ) : (
          <div className="space-y-1.5">
            {data.drivers.map((d) => {
              const m = minsSince(d.last_ping);
              const fresh = m !== null && m < 3;
              return (
                <div key={d.id} className="flex items-center gap-2 bg-white/5 rounded-lg p-2 text-xs" data-testid={`driver-card-${d.id}`}>
                  <span className={`w-2 h-2 rounded-full ${fresh ? 'bg-green-400 animate-pulse' : 'bg-yellow-400'}`}></span>
                  <div className="flex-1">
                    <div className="font-bold">{d.name}</div>
                    <div className="opacity-60 text-[10px]">{d.lat?.toFixed(4)}, {d.lng?.toFixed(4)} · {m !== null ? `آخر تحديث قبل ${m} د` : 'لم يحدّث'}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
      <div className="text-[10px] opacity-50 text-center">🛰️ تحديثات فورية عبر WebSocket — لا حاجة للتحديث اليدوي</div>

      {/* ASSIGN DRIVER MODAL */}
      {selectedOrder && (
        <div className="fixed inset-0 bg-black/80 z-[1100] flex items-center justify-center p-4" onClick={() => setSelectedOrder(null)} data-testid="assign-modal">
          <div onClick={(e) => e.stopPropagation()} className="bg-slate-900 text-white rounded-2xl max-w-md w-full p-5 border border-white/10">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-black">تعيين سائق للطلب #{selectedOrder.id.slice(0, 6)}</h3>
              <button onClick={() => setSelectedOrder(null)} className="w-8 h-8 rounded-full bg-white/10">✕</button>
            </div>
            <div className="text-xs opacity-70 mb-3">اختر السائق الأنسب:</div>
            <div className="space-y-2 max-h-[50vh] overflow-auto">
              {data.drivers.length === 0 ? (
                <div className="text-center py-6 opacity-60 text-xs">لا سائقون متصلون حالياً</div>
              ) : data.drivers.map((d) => (
                <button key={d.id} onClick={() => assignDriver(selectedOrder.id, d.id)}
                  disabled={assigning}
                  className="w-full p-3 bg-white/5 hover:bg-white/10 rounded-lg text-right flex items-center justify-between disabled:opacity-50"
                  data-testid={`pick-driver-${d.id}`}>
                  <div>
                    <div className="font-bold text-sm">{d.name}</div>
                    <div className="text-[10px] opacity-60">{d.lat?.toFixed(3)}, {d.lng?.toFixed(3)}</div>
                  </div>
                  <span className="text-green-400">←</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ================================================================
   📚 SNAPSHOTS TAB — Version History (restore past designs)
   ================================================================ */
function SnapshotsTab({ token, onRestored }) {
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [previewing, setPreviewing] = useState(null); // {id, html, label, created_at}
  const [savingLabel, setSavingLabel] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/client/snapshots`, { headers: authH(token) });
      const d = await r.json();
      setSnapshots(d.snapshots || []);
    } catch (_) {}
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const saveManual = async () => {
    setBusy(true);
    try {
      await fetch(`${API}/api/websites/client/snapshots`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ label: (savingLabel || 'نسخة محفوظة').trim().slice(0, 60) }),
      });
      setSavingLabel('');
      toast.success('تم حفظ النسخة الحالية');
      load();
    } catch (_) { toast.error('فشل الحفظ'); }
    finally { setBusy(false); }
  };

  const openPreview = async (snap) => {
    setPreviewing({ ...snap, html: null });
    try {
      const r = await fetch(`${API}/api/websites/client/snapshots/${snap.id}/preview-html`, { headers: authH(token) });
      const d = await r.json();
      setPreviewing({ ...snap, html: d.html || '' });
    } catch (_) { toast.error('فشل تحميل المعاينة'); setPreviewing(null); }
  };

  const restore = async (snap) => {
    if (!window.confirm(`استعادة "${snap.label}"؟\nسيُحفظ تصميمك الحالي كنسخة قبل الاستعادة تلقائياً — فيمكنك الرجوع له.`)) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/client/snapshots/${snap.id}/restore`, {
        method: 'POST', headers: authH(token),
      });
      if (!r.ok) throw new Error();
      toast.success('✅ تمّت الاستعادة — حدّث موقعك لمشاهدة النسخة');
      setPreviewing(null);
      load();
      onRestored && onRestored();
    } catch (_) { toast.error('فشلت الاستعادة'); }
    finally { setBusy(false); }
  };

  const del = async (snap) => {
    if (!window.confirm(`حذف نسخة "${snap.label}" نهائياً؟`)) return;
    try {
      await fetch(`${API}/api/websites/client/snapshots/${snap.id}`, { method: 'DELETE', headers: authH(token) });
      toast.success('تم الحذف');
      load();
    } catch (_) {}
  };

  const originBadge = (o) => {
    const map = {
      manual: { label: '✋ يدوي', cls: 'bg-yellow-500/20 text-yellow-300' },
      wizard: { label: '🧭 مرشد', cls: 'bg-blue-500/20 text-blue-300' },
      ai_chat: { label: '🤖 ذكاء', cls: 'bg-purple-500/20 text-purple-300' },
      variant: { label: '🎨 نمط', cls: 'bg-pink-500/20 text-pink-300' },
      auto: { label: '⚙️ تلقائي', cls: 'bg-white/10 text-white/70' },
    };
    const m = map[o] || map.auto;
    return <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${m.cls}`}>{m.label}</span>;
  };

  return (
    <div data-testid="snapshots-tab">
      <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/30 rounded-2xl p-4 mb-4">
        <div className="flex items-start gap-3">
          <History className="w-6 h-6 text-purple-300 shrink-0 mt-1" />
          <div className="flex-1">
            <h3 className="font-bold text-lg mb-1">📚 سجل التصاميم (Version History)</h3>
            <div className="text-xs opacity-80 leading-relaxed">كل تعديل كبير يُحفظ تلقائياً هنا. اضغط أي نسخة لمعاينتها، ثم "استعادة" للرجوع لها. لن تفقد شغلك أبداً.</div>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <input
            value={savingLabel}
            onChange={(e) => setSavingLabel(e.target.value)}
            placeholder="اسم النسخة (اختياري، مثل: قبل تغيير الألوان)"
            className="flex-1 px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
            data-testid="snapshot-label-input"
          />
          <button
            onClick={saveManual}
            disabled={busy}
            className="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg text-sm font-bold flex items-center gap-1.5 transition"
            data-testid="save-snapshot-btn"
          >
            <Save className="w-4 h-4" />احفظ النسخة الحالية
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-10 opacity-60">جاري التحميل...</div>
      ) : snapshots.length === 0 ? (
        <div className="text-center py-14 bg-white/3 border border-dashed border-white/15 rounded-2xl">
          <History className="w-10 h-10 mx-auto mb-2 opacity-30" />
          <div className="text-sm opacity-60">لا توجد نسخ محفوظة بعد</div>
          <div className="text-xs opacity-40 mt-1">ستظهر نسخ تلقائية بعد أي تعديل كبير</div>
        </div>
      ) : (
        <div className="space-y-2">
          {snapshots.map((s) => (
            <div key={s.id} className="bg-white/3 border border-white/10 rounded-xl p-3 flex items-center gap-3 flex-wrap" data-testid={`snapshot-${s.id}`}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-bold text-sm">{s.label}</span>
                  {originBadge(s.origin)}
                  <span className="text-[10px] opacity-50">{s.sections_count} قسم</span>
                </div>
                <div className="text-[11px] opacity-60">{new Date(s.created_at).toLocaleString('ar-SA')}</div>
              </div>
              <div className="flex gap-1">
                <button onClick={() => openPreview(s)} className="px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 rounded-lg text-xs font-bold flex items-center gap-1" data-testid={`preview-snapshot-${s.id}`}>
                  <Eye className="w-3.5 h-3.5" />معاينة
                </button>
                <button onClick={() => restore(s)} disabled={busy} className="px-3 py-1.5 bg-green-500/20 hover:bg-green-500/30 text-green-300 rounded-lg text-xs font-bold flex items-center gap-1" data-testid={`restore-snapshot-${s.id}`}>
                  <RotateCcw className="w-3.5 h-3.5" />استعد
                </button>
                <button onClick={() => del(s)} className="p-1.5 hover:bg-red-500/10 text-red-400 rounded-lg" title="حذف" data-testid={`delete-snapshot-${s.id}`}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Preview modal */}
      {previewing && (
        <div className="fixed inset-0 z-[10001] bg-black/80 backdrop-blur-sm flex items-center justify-center p-2 md:p-6" onClick={() => setPreviewing(null)} data-testid="snapshot-preview-modal">
          <div onClick={(e) => e.stopPropagation()} className="bg-[#0e1128] border border-purple-500/30 rounded-2xl w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden">
            <div className="p-3 border-b border-white/10 flex items-center justify-between gap-2 flex-wrap">
              <div className="min-w-0">
                <div className="font-bold truncate">{previewing.label}</div>
                <div className="text-[11px] opacity-60">{new Date(previewing.created_at).toLocaleString('ar-SA')}</div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => restore(previewing)} disabled={busy} className="px-4 py-2 bg-green-500 hover:bg-green-600 text-black rounded-lg text-sm font-bold flex items-center gap-1.5" data-testid="modal-restore-btn">
                  <RotateCcw className="w-4 h-4" />استعد هذا التصميم
                </button>
                <button onClick={() => setPreviewing(null)} className="p-2 hover:bg-white/10 rounded-lg"><X className="w-5 h-5" /></button>
              </div>
            </div>
            <div className="flex-1 bg-white">
              {previewing.html === null ? (
                <div className="h-full flex items-center justify-center opacity-60 text-black">جاري التحميل...</div>
              ) : (
                <iframe srcDoc={previewing.html} title="snapshot-preview" className="w-full h-full border-0" sandbox="allow-scripts allow-same-origin" />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ================================================================
   DASHBOARD — authenticated
   ================================================================ */
function Dashboard({ slug, token, onLogout }) {
  const [project, setProject] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [tab, setTab] = useState('overview'); // overview | edit | messages | support | password
  const [loading, setLoading] = useState(true);
  const [showTour, setShowTour] = useState(() => !localStorage.getItem(`zx_tour_done_${slug}`));

  const loadAll = useCallback(async () => {
    try {
      const [sR, aR] = await Promise.all([
        fetch(`${API}/api/websites/client/session`, { headers: authH(token) }),
        fetch(`${API}/api/websites/client/analytics`, { headers: authH(token) }),
      ]);
      if (sR.status === 401 || aR.status === 401) { onLogout(); return; }
      const s = await sR.json();
      const a = await aR.json();
      setProject(s);
      setAnalytics(a);
    } catch (_) { toast.error('فشل التحميل'); }
    finally { setLoading(false); }
  }, [token, onLogout]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const logout = async () => {
    try { await fetch(`${API}/api/websites/client/logout`, { method: 'POST', headers: authH(token) }); } catch (_) {}
    localStorage.removeItem(`zx_client_token_${slug}`);
    onLogout();
  };

  if (loading) {
    return <div className="min-h-screen bg-[#050815] flex items-center justify-center text-white"><RefreshCw className="w-6 h-6 animate-spin" /></div>;
  }

  const publicUrl = `${window.location.origin}/sites/${slug}`;

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#050815] via-[#0b0f1f] to-[#050815] text-white" dir="rtl" data-testid="client-dashboard">
      <header className="sticky top-0 z-20 bg-[#0e1128]/90 backdrop-blur border-b border-white/10 px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center gap-3 flex-wrap">
          <div className="w-9 h-9 bg-gradient-to-br from-yellow-500 to-orange-500 rounded-xl flex items-center justify-center font-black text-black">Z</div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-bold truncate" data-testid="dashboard-site-name">{project?.name || slug}</div>
            <div className="text-[11px] opacity-60 truncate">لوحة تحكم العميل</div>
          </div>
          <a href={publicUrl} target="_blank" rel="noreferrer" className="text-xs px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg font-bold flex items-center gap-1.5" data-testid="visit-site-btn">
            <ExternalLink className="w-3.5 h-3.5" />زيارة موقعي
          </a>
          <button onClick={logout} className="text-xs px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded-lg font-bold flex items-center gap-1.5" data-testid="logout-btn">
            <LogOut className="w-3.5 h-3.5" />خروج
          </button>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-6">
        {/* Welcome hero */}
        <div className="bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border border-yellow-500/20 rounded-2xl p-4 md:p-5 mb-5" data-testid="welcome-hero">
          <div className="flex items-start gap-3 flex-wrap">
            <CheckCircle2 className="w-9 h-9 text-green-400 shrink-0" />
            <div className="flex-1">
              <h2 className="text-base md:text-lg font-bold mb-1">موقعك يعمل الآن! 🎉</h2>
              <p className="text-xs md:text-sm opacity-80">موقعك على الإنترنت متاح ليراه الجميع. من هنا تستطيع مراقبة الزوار والرسائل وتعديل المحتوى.</p>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3 mb-5">
          <Stat icon={Users} label="زيارات" value={analytics?.visits ?? 0} accent="text-blue-300" />
          <Stat icon={MessageSquare} label="رسائل" value={analytics?.messages_total ?? 0} accent="text-pink-300" />
          <Stat icon={BarChart3} label="أقسام" value={analytics?.sections_count ?? 0} accent="text-green-300" />
          <Stat icon={MessageSquare} label="جديدة" value={analytics?.messages_unread ?? 0} accent="text-yellow-300" />
        </div>

        {/* Tabs — conditional per vertical */}
        <div className="flex gap-1 mb-4 bg-white/3 rounded-xl p-1 overflow-x-auto" data-testid="dashboard-tabs">
          {(() => {
            const v = project?.vertical;
            const hasBookings = ['salon', 'salon_women', 'pets', 'medical', 'gym', 'car_wash', 'sports_club', 'maintenance'].includes(v);
            const hasProducts = ['ecommerce', 'bakery', 'library', 'art_gallery', 'jewelry'].includes(v);
            const hasListings = v === 'realestate';
            const hasOrders = ['restaurant', 'ecommerce', 'bakery', 'library', 'jewelry'].includes(v) || !v;
            const hasCourses = v === 'academy';
            const hasMemberships = ['gym', 'sports_club'].includes(v);
            const hasEvents = ['art_gallery', 'sports_club', 'academy'].includes(v);
            const hasDriverAnalytics = hasOrders;  // any vertical with delivery
            const base = [
              { id: 'overview', label: 'نظرة عامة', icon: BarChart3 },
            ];
            if (hasBookings) {
              base.push({ id: 'bookings', label: '📅 المواعيد', icon: BarChart3 });
              base.push({ id: 'services', label: '✂️ الخدمات', icon: Key });
            }
            if (hasProducts) {
              base.push({ id: 'products', label: '📦 المنتجات', icon: Key });
            }
            if (hasListings) {
              base.push({ id: 'listings', label: '🏠 العقارات', icon: MapPin });
            }
            if (hasOrders) {
              base.push({ id: 'orders', label: 'الطلبات', icon: MessageSquare });
              base.push({ id: 'livemap', label: '🗺️ خريطة حية', icon: MapPin });
              base.push({ id: 'drivers', label: 'السائقون', icon: ExternalLink });
              base.push({ id: 'delivery', label: 'التوصيل', icon: MapPin });
              base.push({ id: 'shipping', label: '📦 الشحن', icon: MapPin });
            }
            if (hasCourses) base.push({ id: 'courses', label: '🎓 الدورات', icon: BarChart3 });
            if (hasMemberships) base.push({ id: 'memberships', label: '💳 العضويات', icon: Key });
            if (hasEvents) base.push({ id: 'events', label: '🎫 الفعاليات', icon: MapPin });
            if (hasDriverAnalytics) base.push({ id: 'driver_analytics', label: '📊 أداء السائقين', icon: BarChart3 });
            base.push(
              { id: 'customers', label: 'العملاء', icon: Users },
              { id: 'payments', label: '💳 الدفع', icon: Key },
              { id: 'widgets', label: '🎨 الأدوات', icon: Key },
              { id: 'coupons', label: '🎟️ كوبونات', icon: Key },
              { id: 'loyalty', label: '🎁 النقاط', icon: CheckCircle2 },
              { id: 'stories', label: '🎬 الحالات والبنر', icon: ImageIcon },
              { id: 'chatbot', label: '🤖 المساعد الذكي', icon: MessageSquare },
              { id: 'edit', label: 'المحتوى', icon: Edit3 },
              { id: 'snapshots', label: '📚 السجل', icon: History },
              { id: 'messages', label: 'الرسائل', icon: MessageSquare },
              { id: 'support', label: 'الدعم', icon: RefreshCw },
              { id: 'password', label: 'الأمان', icon: Key },
            );
            return base;
          })().map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`shrink-0 px-3 py-2 rounded-lg text-xs md:text-sm font-bold flex items-center gap-1.5 transition ${tab === t.id ? 'bg-yellow-500 text-black' : 'hover:bg-white/5'}`}
              data-testid={`tab-${t.id}`}
            >
              <t.icon className="w-3.5 h-3.5" />{t.label}
            </button>
          ))}
        </div>

        {tab === 'overview' && (
          <div className="grid md:grid-cols-2 gap-3" data-testid="overview-tab">
            <div className="bg-white/3 border border-white/10 rounded-2xl p-4">
              <h3 className="font-bold mb-3 flex items-center gap-2"><ExternalLink className="w-4 h-4" />روابط موقعك</h3>
              <div className="space-y-2">
                <div className="flex items-center gap-2 bg-white/5 rounded-lg p-2">
                  <div className="flex-1 text-xs opacity-80 truncate font-mono">{publicUrl}</div>
                  <button onClick={() => { navigator.clipboard.writeText(publicUrl); toast.success('تم النسخ'); }} className="p-1 hover:bg-white/10 rounded" data-testid="copy-public-url"><Copy className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            </div>
            <div className="bg-white/3 border border-white/10 rounded-2xl p-4">
              <h3 className="font-bold mb-3 flex items-center gap-2"><Users className="w-4 h-4" />آخر نشاط</h3>
              <div className="text-xs opacity-70">
                {analytics?.approved_at ? `الموقع معتمد منذ ${new Date(analytics.approved_at).toLocaleDateString('ar-SA')}` : 'الموقع قيد الإعداد'}
              </div>
              <div className="text-xs opacity-70 mt-1">{analytics?.visits || 0} زائر حتى الآن · {analytics?.messages_unread || 0} رسالة جديدة</div>
            </div>
          </div>
        )}

        {tab === 'edit' && (
          <div data-testid="edit-tab">
            <div className="text-xs opacity-60 mb-2">اضغط ✏️ لتعديل أي قسم. التعديلات تُحفظ فوراً.</div>
            <SectionsEditor project={project} token={token} onUpdated={loadAll} />
          </div>
        )}

        {tab === 'orders' && <OrdersTab token={token} />}
        {tab === 'bookings' && <BookingsTab token={token} />}
        {tab === 'services' && <ServicesTab token={token} />}
        {tab === 'products' && <ProductsTab token={token} />}
        {tab === 'listings' && <ListingsTab token={token} />}
        {tab === 'livemap' && <LiveMapTab token={token} slug={slug} />}
        {tab === 'customers' && <CustomersTab token={token} />}
        {tab === 'drivers' && <DriversTab token={token} />}
        {tab === 'delivery' && <DeliverySettingsTab token={token} slug={slug} />}
        {tab === 'shipping' && <ShippingTab token={token} slug={slug} />}
        {tab === 'payments' && <PaymentGatewaysTab token={token} />}
        {tab === 'widgets' && <WidgetCustomizerTab token={token} slug={slug} />}
        {tab === 'coupons' && <CouponsTab token={token} />}
        {tab === 'loyalty' && <LoyaltyTab token={token} />}
        {tab === 'stories' && <StoriesTab token={token} slug={slug} />}
        {tab === 'chatbot' && <ChatbotTab token={token} slug={slug} />}

        {tab === 'messages' && <MessagesTab token={token} />}

        {tab === 'courses' && <CoursesTab token={token} />}
        {tab === 'memberships' && <MembershipsTab token={token} />}
        {tab === 'events' && <EventsTab token={token} />}
        {tab === 'driver_analytics' && <DriverAnalyticsTab token={token} />}

        {tab === 'snapshots' && <SnapshotsTab token={token} onRestored={loadAll} />}

        {tab === 'support' && <SupportTab token={token} />}

        {tab === 'password' && <PasswordTab token={token} />}
      </div>

      {/* 🆕 Welcome Tour — first-time onboarding */}
      {showTour && (
        <WelcomeTour
          siteName={project?.name || slug}
          publicUrl={publicUrl}
          onDone={() => { localStorage.setItem(`zx_tour_done_${slug}`, '1'); setShowTour(false); }}
        />
      )}
    </div>
  );
}

/* ================================================================
   WELCOME TOUR — interactive first-time onboarding
   ================================================================ */
function WelcomeTour({ siteName, publicUrl, onDone }) {
  const [step, setStep] = useState(0);
  const STEPS = [
    { icon: '🎉', title: 'مرحباً بك في لوحة تحكم موقعك', body: `موقعك "${siteName}" جاهز وعلى الإنترنت الآن. من هنا ستدير كل شيء بنفسك.` },
    { icon: '📊', title: 'تابع زوارك ورسائلك', body: 'الإحصائيات في الأعلى تعرض عدد الزوار، الرسائل الواردة، والأقسام.' },
    { icon: '✏️', title: 'عدّل محتوى موقعك بسهولة', body: 'من تبويب "تعديل المحتوى" يمكنك تغيير النصوص، إخفاء/إظهار الأقسام، دون أي برمجة.' },
    { icon: '💬', title: 'استقبل رسائل عملائك', body: 'كل من يراسلك عبر نموذج "تواصل معنا" سيظهر هنا مباشرةً.' },
    { icon: '🛠️', title: 'احصل على الدعم الفني', body: 'من تبويب "الدعم الفني" تقدم طلب تعديل أو إصلاح، وسيتم الرد سريعاً.' },
    { icon: '🔐', title: 'كلمة مرورك بيدك', body: 'غيّر كلمة المرور الآن — لأمان أكبر. موقعك ورابطه الخاص جاهز للمشاركة.' },
  ];
  const cur = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div className="fixed inset-0 bg-black/85 z-[70] flex items-center justify-center p-4" dir="rtl" data-testid="welcome-tour">
      <div className="bg-[#0e1128] rounded-2xl max-w-md w-full border border-yellow-500/40 p-6 shadow-[0_30px_80px_rgba(234,179,8,0.2)]">
        <div className="text-center mb-4">
          <div className="text-5xl mb-2">{cur.icon}</div>
          <div className="text-lg font-black text-white mb-1">{cur.title}</div>
          <div className="text-sm opacity-80">{cur.body}</div>
        </div>
        {/* Dots */}
        <div className="flex justify-center gap-1 mb-4">
          {STEPS.map((_, i) => (
            <div key={i} className={`h-1.5 rounded-full transition-all ${i === step ? 'w-6 bg-yellow-500' : 'w-1.5 bg-white/20'}`} />
          ))}
        </div>
        <div className="flex gap-2">
          <button onClick={onDone} className="flex-1 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-xs font-bold" data-testid="tour-skip">تخطّي</button>
          {isLast ? (
            <button onClick={onDone} className="flex-[2] py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-lg font-black" data-testid="tour-done">✨ ابدأ الاستخدام</button>
          ) : (
            <button onClick={() => setStep(step + 1)} className="flex-[2] py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-lg font-black" data-testid="tour-next">التالي ←</button>
          )}
        </div>
        {isLast && (
          <div className="mt-3 text-center">
            <a href={publicUrl} target="_blank" rel="noreferrer" className="text-[11px] text-yellow-300 underline" data-testid="tour-visit">↗ افتح موقعي الآن</a>
          </div>
        )}
      </div>
    </div>
  );
}

/* ================================================================
   ROOT PAGE
   ================================================================ */
export default function ClientDashboardPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [token, setToken] = useState(() => localStorage.getItem(`zx_client_token_${slug}`) || '');

  useEffect(() => {
    if (!token) return;
    // Validate token on mount
    fetch(`${API}/api/websites/client/session`, { headers: authH(token) })
      .then((r) => { if (r.status === 401) { localStorage.removeItem(`zx_client_token_${slug}`); setToken(''); } })
      .catch(() => {});
  }, [token, slug]);

  if (!slug) { navigate('/'); return null; }

  return token
    ? <Dashboard slug={slug} token={token} onLogout={() => setToken('')} />
    : <LoginCard slug={slug} onLoggedIn={setToken} />;
}

/* ════════════════════════════════════════════════════════════════════
   📦 SHIPPING TAB — تفعيل/تعطيل شركات الشحن السعودية + أسعار مخصصة
   ════════════════════════════════════════════════════════════════════ */
function ShippingTab({ token, slug }) {
  const [providers, setProviders] = useState([]);
  const [config, setConfig] = useState(null);
  const [busy, setBusy] = useState(false);
  const [previewCity, setPreviewCity] = useState('الرياض');
  const [previewCountry, setPreviewCountry] = useState('SA');
  const [previewQuote, setPreviewQuote] = useState(null);

  const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };

  const projectId = slug;  // assumes slug == project id; if not, adjust to fetch project by slug

  useEffect(() => {
    fetch(`${API}/api/websites/shipping/providers`).then(r => r.json()).then(d => setProviders(d.providers || []));
    fetch(`${API}/api/websites/projects/${projectId}/shipping/config`, { headers })
      .then(r => r.json()).then(setConfig).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const toggleProvider = (pid) => {
    if (!config) return;
    const enabled = new Set(config.enabled_providers || []);
    if (enabled.has(pid)) enabled.delete(pid); else enabled.add(pid);
    setConfig({ ...config, enabled_providers: Array.from(enabled) });
  };

  const updateRate = (pid, key, value) => {
    if (!config) return;
    const customRates = { ...(config.custom_rates || {}) };
    customRates[pid] = { ...(customRates[pid] || {}), [key]: parseFloat(value) || 0 };
    setConfig({ ...config, custom_rates: customRates });
  };

  const saveConfig = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/projects/${projectId}/shipping/config`, {
        method: 'PUT', headers, body: JSON.stringify(config),
      });
      if (!r.ok) throw new Error();
      toast.success('✅ تم حفظ إعدادات الشحن');
    } catch (_) { toast.error('فشل الحفظ'); }
    finally { setBusy(false); }
  };

  const previewQuoteFn = async () => {
    try {
      const r = await fetch(`${API}/api/websites/projects/${projectId}/shipping/quote`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ country: previewCountry, city: previewCity, weight_kg: 2, cart_subtotal: 100 }),
      });
      const d = await r.json();
      setPreviewQuote(d);
    } catch (_) { toast.error('فشل المعاينة'); }
  };

  if (!config) return <div className="p-6 text-white/50">جارٍ التحميل...</div>;

  const enabled = new Set(config.enabled_providers || []);

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="shipping-tab">
      <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-400/30 rounded-2xl p-5">
        <h2 className="text-2xl font-black mb-1 flex items-center gap-2"><span>📦</span> نظام الشحن الذكي</h2>
        <p className="text-sm text-white/60">يكتشف موقع العميل تلقائياً ويعرض خيارات الشحن المناسبة (داخلي / محلي / دولي)</p>
      </div>

      {/* Local delivery */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-5">
        <h3 className="font-black text-lg mb-3 flex items-center gap-2"><span>🛵</span> التوصيل الداخلي (نفس مدينتك)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label className="block">
            <span className="text-xs text-white/60">مدينة المتجر</span>
            <input type="text" value={config.store_city || ''} onChange={(e) => setConfig({...config, store_city: e.target.value})}
              className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" placeholder="مثل: جدة" data-testid="store-city-input" />
          </label>
          <label className="block">
            <span className="text-xs text-white/60">سعر التوصيل الداخلي (ر.س)</span>
            <input type="number" value={config.local_delivery_fee || 0} onChange={(e) => setConfig({...config, local_delivery_fee: parseFloat(e.target.value) || 0})}
              className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" data-testid="local-fee-input" />
          </label>
          <label className="block">
            <span className="text-xs text-white/60">شحن مجاني فوق (ر.س) — 0 = معطّل</span>
            <input type="number" value={config.free_shipping_above_sar || 0} onChange={(e) => setConfig({...config, free_shipping_above_sar: parseFloat(e.target.value) || 0})}
              className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" data-testid="free-shipping-input" />
          </label>
          <label className="flex items-center gap-2 mt-5">
            <input type="checkbox" checked={!!config.local_delivery_enabled} onChange={(e) => setConfig({...config, local_delivery_enabled: e.target.checked})} data-testid="local-enabled-toggle" />
            <span className="text-sm">تفعيل التوصيل الداخلي</span>
          </label>
        </div>
      </div>

      {/* Providers */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-5">
        <h3 className="font-black text-lg mb-3 flex items-center gap-2"><span>🚚</span> شركات الشحن (سعودي + دولي)</h3>
        <div className="space-y-3">
          {providers.map((p) => {
            const isEnabled = enabled.has(p.id);
            const customRates = (config.custom_rates || {})[p.id] || {};
            const baseFee = customRates.base_fee ?? p.default_rates.base_fee;
            const extraFee = customRates.extra_kg_fee ?? p.default_rates.extra_kg_fee;
            const isIntl = p.coverage.includes('INTL') || p.coverage.length > 1;
            return (
              <div key={p.id} className={`p-4 rounded-xl border-2 transition-all ${isEnabled ? 'border-emerald-400/50 bg-emerald-500/5' : 'border-white/10 bg-white/[.02]'}`} data-testid={`shipping-row-${p.id}`}>
                <div className="flex items-center gap-3 mb-3">
                  <div className="text-3xl">{p.icon}</div>
                  <div className="flex-1 min-w-0">
                    <div className="font-black">{p.name_ar}</div>
                    <div className="text-[11px] text-white/50">
                      {isIntl ? '🌍 دولي + سعودي' : '🇸🇦 سعودي'} ·
                      {p.supports_cod ? ' 💵 الدفع عند الاستلام' : ''} ·
                      {p.supports_returns ? ' ↩️ المرتجعات' : ''}
                    </div>
                  </div>
                  <label className="cursor-pointer">
                    <input type="checkbox" checked={isEnabled} onChange={() => toggleProvider(p.id)} className="sr-only" data-testid={`toggle-${p.id}`} />
                    <div className={`w-12 h-6 rounded-full p-0.5 transition-colors ${isEnabled ? 'bg-emerald-500' : 'bg-white/10'}`}>
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${isEnabled ? 'translate-x-6' : ''}`} />
                    </div>
                  </label>
                </div>
                {isEnabled && (
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/5">
                    <label className="block">
                      <span className="text-[11px] text-white/50">سعر أساسي (ر.س / 5كغ)</span>
                      <input type="number" value={baseFee} onChange={(e) => updateRate(p.id, 'base_fee', e.target.value)}
                        className="w-full mt-1 px-2 py-1.5 bg-black/40 border border-white/10 rounded-md text-xs" data-testid={`base-fee-${p.id}`} />
                    </label>
                    <label className="block">
                      <span className="text-[11px] text-white/50">سعر كل كغ إضافي (ر.س)</span>
                      <input type="number" value={extraFee} onChange={(e) => updateRate(p.id, 'extra_kg_fee', e.target.value)}
                        className="w-full mt-1 px-2 py-1.5 bg-black/40 border border-white/10 rounded-md text-xs" data-testid={`extra-fee-${p.id}`} />
                    </label>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 🆕 Pickup option — let customer pick up from store (free) */}
      <div className="bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border border-emerald-400/30 rounded-xl p-5" data-testid="pickup-card">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <h3 className="font-black text-lg flex items-center gap-2"><span>🏬</span> الاستلام من المتجر</h3>
            <p className="text-xs text-white/60 mt-1">يعرض للعميل خياراً مجانياً ليأتي ويستلم بنفسه. مفيد للمنتجات الصغيرة، الأطعمة، أو العملاء قرب المتجر.</p>
          </div>
          <label className="cursor-pointer flex-shrink-0">
            <input type="checkbox" checked={!!config.pickup_enabled} onChange={(e) => setConfig({...config, pickup_enabled: e.target.checked})} className="sr-only" data-testid="pickup-toggle" />
            <div className={`w-12 h-6 rounded-full p-0.5 transition-colors ${config.pickup_enabled ? 'bg-emerald-500' : 'bg-white/10'}`}>
              <div className={`w-5 h-5 rounded-full bg-white transition-transform ${config.pickup_enabled ? 'translate-x-6' : ''}`} />
            </div>
          </label>
        </div>
        {config.pickup_enabled && (
          <div className="space-y-3">
            <label className="block">
              <span className="text-xs text-white/60">عنوان الاستلام</span>
              <input type="text" value={config.pickup_address || ''}
                onChange={(e) => setConfig({...config, pickup_address: e.target.value})}
                placeholder="مثل: جدة، حي الروضة، شارع الأمير سلطان، مبنى رقم 12"
                className="w-full mt-1 px-3 py-2 bg-black/30 border border-emerald-400/30 rounded-lg text-sm" data-testid="pickup-address-input" />
            </label>
            <label className="block">
              <span className="text-xs text-white/60">ساعات العمل / مدة التحضير</span>
              <input type="text" value={config.pickup_hours || ''}
                onChange={(e) => setConfig({...config, pickup_hours: e.target.value})}
                placeholder="مثل: السبت-الخميس 9ص-10م | جاهز خلال ساعة"
                className="w-full mt-1 px-3 py-2 bg-black/30 border border-emerald-400/30 rounded-lg text-sm" data-testid="pickup-hours-input" />
            </label>
          </div>
        )}
      </div>

      {/* 🆕 COD Markup — extra revenue knob */}
      <div className="bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-amber-400/30 rounded-xl p-5" data-testid="cod-markup-card">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <h3 className="font-black text-lg flex items-center gap-2"><span>💵</span> هامش الدفع عند الاستلام (COD)</h3>
            <p className="text-xs text-white/60 mt-1">يضيف رسوماً إضافية تلقائياً على كل طلب يدفع عند الاستلام لتعويض رسوم البنك ومخاطر الإرجاع. الرسوم تظهر للعميل قبل التأكيد.</p>
          </div>
          <label className="cursor-pointer flex-shrink-0">
            <input type="checkbox" checked={!!config.cod_markup_enabled} onChange={(e) => setConfig({...config, cod_markup_enabled: e.target.checked})} className="sr-only" data-testid="cod-markup-toggle" />
            <div className={`w-12 h-6 rounded-full p-0.5 transition-colors ${config.cod_markup_enabled ? 'bg-amber-500' : 'bg-white/10'}`}>
              <div className={`w-5 h-5 rounded-full bg-white transition-transform ${config.cod_markup_enabled ? 'translate-x-6' : ''}`} />
            </div>
          </label>
        </div>
        {config.cod_markup_enabled && (
          <label className="block">
            <span className="text-xs text-white/60">قيمة الهامش (ر.س)</span>
            <input type="number" min="0" step="0.5" value={config.cod_markup_sar ?? 5}
              onChange={(e) => setConfig({...config, cod_markup_sar: parseFloat(e.target.value) || 0})}
              className="w-full mt-1 px-3 py-2 bg-black/30 border border-amber-400/30 rounded-lg text-sm" data-testid="cod-markup-input" />
            <p className="text-[11px] text-amber-300/80 mt-2">💡 مثال: لو القيمة 5 ر.س — كل طلب COD سيُضاف له 5 ر.س على رسوم الشحن. ربح إضافي بدون عمل.</p>
          </label>
        )}
      </div>

      {/* 🆕 Shipping Insurance — extra revenue knob */}
      <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-400/30 rounded-xl p-5" data-testid="insurance-card">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <h3 className="font-black text-lg flex items-center gap-2"><span>🛡️</span> تأمين الشحنة (اختياري)</h3>
            <p className="text-xs text-white/60 mt-1">يظهر للعميل كصندوق اختياري عند الـ checkout. يضمن استبدال أو إعادة المبلغ عند تلف/فقدان الشحنة. هامش ربح إضافي على كل طلب يختار التأمين.</p>
          </div>
          <label className="cursor-pointer flex-shrink-0">
            <input type="checkbox" checked={!!config.insurance_enabled} onChange={(e) => setConfig({...config, insurance_enabled: e.target.checked})} className="sr-only" data-testid="insurance-toggle" />
            <div className={`w-12 h-6 rounded-full p-0.5 transition-colors ${config.insurance_enabled ? 'bg-blue-500' : 'bg-white/10'}`}>
              <div className={`w-5 h-5 rounded-full bg-white transition-transform ${config.insurance_enabled ? 'translate-x-6' : ''}`} />
            </div>
          </label>
        </div>
        {config.insurance_enabled && (
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs text-white/60">النسبة (%)</span>
              <input type="number" min="0" step="0.5" value={config.insurance_percent ?? 2}
                onChange={(e) => setConfig({...config, insurance_percent: parseFloat(e.target.value) || 0})}
                className="w-full mt-1 px-3 py-2 bg-black/30 border border-blue-400/30 rounded-lg text-sm" data-testid="insurance-percent-input" />
            </label>
            <label className="block">
              <span className="text-xs text-white/60">الحد الأدنى (ر.س)</span>
              <input type="number" min="0" step="1" value={config.insurance_min_sar ?? 10}
                onChange={(e) => setConfig({...config, insurance_min_sar: parseFloat(e.target.value) || 0})}
                className="w-full mt-1 px-3 py-2 bg-black/30 border border-blue-400/30 rounded-lg text-sm" data-testid="insurance-min-input" />
            </label>
            <p className="col-span-2 text-[11px] text-blue-300/80">💡 مثال: نسبة 2% + حد أدنى 10 ر.س — سلة قيمتها 300 ر.س = تأمين 10 ر.س | سلة قيمتها 1000 ر.س = تأمين 20 ر.س.</p>
          </div>
        )}
      </div>

      {/* Save bar */}
      <div className="sticky bottom-4 flex gap-3">
        <button onClick={saveConfig} disabled={busy}
          className="flex-1 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-600 hover:to-cyan-600 font-black disabled:opacity-50" data-testid="save-shipping-btn">
          {busy ? '⏳ جارٍ الحفظ...' : '✅ حفظ إعدادات الشحن'}
        </button>
      </div>

      {/* Live preview */}
      <div className="bg-gradient-to-br from-violet-500/10 to-pink-500/10 border border-violet-400/30 rounded-xl p-5">
        <h3 className="font-black text-lg mb-3">🔍 معاينة خيارات الشحن (كما سيراها العميل)</h3>
        <div className="grid grid-cols-3 gap-2 mb-3">
          <select value={previewCountry} onChange={(e) => setPreviewCountry(e.target.value)} className="px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" data-testid="preview-country">
            <option value="SA">🇸🇦 السعودية</option>
            <option value="AE">🇦🇪 الإمارات</option>
            <option value="KW">🇰🇼 الكويت</option>
            <option value="US">🇺🇸 أمريكا</option>
          </select>
          <input type="text" value={previewCity} onChange={(e) => setPreviewCity(e.target.value)}
            className="px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" placeholder="المدينة" data-testid="preview-city" />
          <button onClick={previewQuoteFn} className="py-2 rounded-lg bg-violet-500 hover:bg-violet-600 text-sm font-bold" data-testid="preview-quote-btn">معاينة</button>
        </div>
        {previewQuote?.options?.length > 0 && (
          <div className="space-y-2">
            {previewQuote.options.map((o, i) => (
              <div key={i} className={`p-3 rounded-lg border flex items-center gap-3 ${o.is_recommended ? 'border-emerald-400/50 bg-emerald-500/10' : 'border-white/10 bg-black/20'}`}>
                <span className="text-2xl">{o.icon}</span>
                <div className="flex-1">
                  <div className="font-bold text-sm">{o.provider_name} {o.is_recommended && '⭐'}</div>
                  <div className="text-[11px] text-white/50">{o.delivery_eta}</div>
                </div>
                <div className="text-left">
                  {o.is_free ? <span className="font-black text-emerald-400">🆓 مجاني</span>
                    : <span className="font-black">{o.fee_sar} ر.س</span>}
                </div>
              </div>
            ))}
          </div>
        )}
        {previewQuote && previewQuote.options?.length === 0 && (
          <div className="text-center py-4 text-white/50 text-sm">لا توجد خيارات شحن متاحة لهذا الموقع — فعّل شركة على الأقل</div>
        )}
      </div>
    </div>
  );
}
