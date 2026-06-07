import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { BackButton } from '@/components/BackButton';
import { Send, CheckCircle, Sparkles, Globe, Eye, Monitor, Smartphone, Trash2, Plus } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// ─── Project List (when no id) ───
const ProjectList = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/freebuild-chat/projects`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) {
        const d = await r.json();
        setProjects(d.projects || []);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const remove = async (pid) => {
    if (!window.confirm('حذف المشروع؟')) return;
    const token = localStorage.getItem('token');
    await fetch(`${API}/api/freebuild-chat/project/${pid}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
    toast.success('تم الحذف');
    load();
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a14] to-[#0a0a12]">
      <Navbar user={user} setUser={setUser} transparent />
      <div className="container mx-auto px-4 max-w-6xl pt-24 pb-12">
        <div className="mb-6"><BackButton to="/dashboard" label="لوحة التحكم" /></div>

        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-black text-white mb-1 flex items-center gap-3">
              <Globe className="w-8 h-8 text-cyan-400" /> مشاريع المواقع
            </h1>
            <p className="text-gray-400 text-sm">شات ذكي · توليد أصول · معاينة لحظية</p>
          </div>
          <button
            type="button"
            data-testid="new-project-btn"
            onClick={() => navigate('/freebuild/chat/new')}
            className="navbar-btn-primary px-5 py-2.5 rounded-xl font-black text-black flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> مشروع جديد
          </button>
        </div>

        {loading ? (
          <p className="text-gray-500 text-sm">جاري التحميل...</p>
        ) : projects.length === 0 ? (
          <div className="rounded-2xl bg-slate-800/40 border border-slate-700 p-12 text-center">
            <Sparkles className="w-14 h-14 mx-auto mb-4 text-amber-400/60" />
            <h3 className="text-white text-xl font-black mb-2">ما عندك مشاريع بعد</h3>
            <p className="text-gray-400 text-sm mb-6">ابدأ مشروع جديد وخلي الذكاء يصمم معك خطوة بخطوة</p>
            <button type="button" onClick={() => navigate('/freebuild/chat/new')}
              className="navbar-btn-primary px-6 py-3 rounded-xl font-black text-black">
              ابدأ أول مشروع ←
            </button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((p) => (
              <div key={p.id} data-testid={`project-card-${p.id}`}
                className="rounded-2xl bg-slate-800/50 border border-slate-700 hover:border-cyan-500/50 p-5 transition cursor-pointer group"
                onClick={() => navigate(`/freebuild/chat/${p.id}`)}>
                <div className="flex items-start justify-between mb-3">
                  <h3 className="text-white font-black truncate">{p.name}</h3>
                  <button type="button" onClick={(e) => { e.stopPropagation(); remove(p.id); }}
                    className="text-gray-500 hover:text-red-400 p-1">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <p className="text-gray-400 text-xs mb-3 line-clamp-2 h-8">{p.description}</p>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-cyan-400">{p.website_type}</span>
                  <span className="text-gray-500">{(p.messages || []).length} رسالة</span>
                </div>
                {p.approved_assets?.length > 0 && (
                  <div className="mt-3 flex gap-1">
                    {p.approved_assets.slice(0, 4).map((a) => a.image_url && (
                      <img key={a.id} src={a.image_url} alt="" className="w-10 h-10 object-cover rounded" />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Type Picker (new project) ───
const TypePicker = ({ onCreate, user, setUser }) => {
  const [types, setTypes] = useState([]);
  const [selected, setSelected] = useState(null);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/freebuild-chat/types`).then((r) => r.json()).then((d) => setTypes(d.types || []));
  }, []);

  const create = async () => {
    if (!selected || !name.trim() || !desc.trim()) return toast.error('املأ كل الحقول');
    setCreating(true);
    const token = localStorage.getItem('token');
    const r = await fetch(`${API}/api/freebuild-chat/project`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ website_type: selected, name, description: desc }),
    });
    if (r.ok) {
      const data = await r.json();
      onCreate(data.id);
    } else toast.error('فشل إنشاء المشروع');
    setCreating(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a14] to-[#0a0a12]">
      <Navbar user={user} setUser={setUser} transparent />
      <div className="container mx-auto px-4 max-w-5xl pt-24 pb-12">
        <div className="mb-6"><BackButton to="/freebuild/chat" label="مشاريعي" /></div>
        <h1 className="text-3xl font-black text-white mb-2 flex items-center gap-3">
          <Globe className="w-8 h-8 text-cyan-400" /> مشروع جديد
        </h1>
        <p className="text-gray-400 text-sm mb-8">شات ذكي مع توليد أصول · معاينة لحظية · موقع نهائي قابل للنشر</p>

        <h2 className="text-lg font-bold text-white mb-3">١. اختر نوع الموقع</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
          {types.map((t) => (
            <button key={t.id} type="button" onClick={() => setSelected(t.id)}
              data-testid={`type-${t.id}`}
              className={`quick-action-card p-4 rounded-xl text-right border-2 ${selected === t.id ? 'border-amber-400 bg-amber-500/10' : 'border-slate-700 bg-slate-800/40'}`}>
              <div className="text-2xl mb-2">{t.title.split(' ')[0]}</div>
              <h3 className="text-white text-sm font-bold mb-1">{t.title.replace(/^[^\s]+\s/, '')}</h3>
              <p className="text-gray-400 text-xs mb-2">{t.desc}</p>
              <span className="text-amber-300 text-xs font-black">{t.credits} نقطة</span>
            </button>
          ))}
        </div>

        {selected && (
          <div className="rounded-2xl bg-slate-800/50 border border-slate-700 p-5 mb-6">
            <h2 className="text-lg font-bold text-white mb-3">٢. عرّفنا بمشروعك</h2>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="اسم المشروع"
              data-testid="project-name-input"
              className="w-full bg-slate-900/70 border border-slate-700 rounded-lg px-4 py-2.5 text-white mb-3" />
            <textarea value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="وصف مختصر (نشاطك، جمهورك، ميزات أساسية)"
              data-testid="project-desc-input"
              rows={4} className="w-full bg-slate-900/70 border border-slate-700 rounded-lg px-4 py-2.5 text-white" />
            <button type="button" onClick={create} disabled={creating}
              data-testid="create-project-btn"
              className="navbar-btn-primary mt-4 w-full py-3 rounded-lg font-black text-black">
              {creating ? 'جاري الإنشاء...' : 'ابدأ المحادثة الذكية ←'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Chat Workspace (3-pane layout) ───
const ChatWorkspace = ({ projectId, user, setUser }) => {
  const [proj, setProj] = useState(null);
  const [msg, setMsg] = useState('');
  const [sending, setSending] = useState(false);
  const [previewMode, setPreviewMode] = useState('desktop'); // desktop | mobile
  const [showPreview, setShowPreview] = useState(true);
  const messagesEndRef = useRef(null);

  const fetchProj = useCallback(async () => {
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) setProj(await r.json());
    } catch (e) {
      // silent
    }
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    const token = localStorage.getItem('token');
    const tick = async () => {
      try {
        const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
        if (r.ok && !cancelled) {
          const d = await r.json();
          setProj(d);
        }
      } catch (e) { /* silent */ }
    };
    tick();
    const iv = setInterval(tick, 4000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [projectId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [proj?.messages?.length]);

  const send = async () => {
    if (!msg.trim() || sending) return;
    setSending(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: msg }),
      });
      if (r.ok) {
        setMsg('');
        await fetchProj();
      } else {
        const err = await r.json().catch(() => ({}));
        toast.error(err.detail || 'فشل الإرسال');
      }
    } finally {
      setSending(false);
    }
  };

  const approve = async (aid) => {
    const token = localStorage.getItem('token');
    const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/asset/${aid}/approve`, {
      method: 'POST', headers: { Authorization: `Bearer ${token}` },
    });
    if (r.ok) {
      toast.success('تم اعتماد الأصل ✓');
      fetchProj();
    } else toast.error('فشل');
  };

  if (!proj) {
    return (
      <div className="min-h-screen bg-[#0a0a12] flex items-center justify-center">
        <div className="text-gray-400 text-sm flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
          جاري التحميل...
        </div>
      </div>
    );
  }

  // Collect all pending (not approved) assets across messages
  const pending = [];
  (proj.messages || []).forEach((m) => {
    (m.pending_assets || []).forEach((a) => {
      if (!a.approved) pending.push(a);
    });
  });

  return (
    <div className="min-h-screen bg-[#0a0a12]">
      <Navbar user={user} setUser={setUser} transparent />
      <div className="px-4 max-w-[1700px] mx-auto pt-20 pb-6">
        <div className="mb-3 flex items-center justify-between gap-3">
          <BackButton to="/freebuild/chat" label="مشاريعي" />
          <div className="text-right flex-1 min-w-0">
            <h1 className="text-lg font-black text-white truncate" data-testid="project-title">{proj.name}</h1>
            <p className="text-gray-500 text-xs truncate">{proj.description?.slice(0, 100)}</p>
          </div>
          <button type="button" onClick={() => setShowPreview((v) => !v)}
            data-testid="toggle-preview-btn"
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-gray-300 text-xs font-bold flex items-center gap-1.5">
            <Eye className="w-3.5 h-3.5" /> {showPreview ? 'إخفاء المعاينة' : 'إظهار المعاينة'}
          </button>
        </div>

        <div className={`grid gap-3 ${showPreview ? 'lg:grid-cols-[280px_1fr_minmax(0,600px)]' : 'lg:grid-cols-[280px_1fr]'}`}
          style={{ height: 'calc(100vh - 120px)' }}>

          {/* LEFT: Assets pending + approved */}
          <div className="rounded-2xl bg-slate-900/60 border border-slate-700 flex flex-col overflow-hidden">
            <div className="px-3 py-2.5 border-b border-slate-700 bg-slate-800/40">
              <h3 className="text-white font-black text-xs flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" /> الأصول
              </h3>
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-3" data-testid="assets-panel">
              {/* Pending */}
              {pending.length > 0 && (
                <div>
                  <p className="text-amber-400 text-[10px] font-black mb-2">⏳ بانتظار الاعتماد ({pending.length})</p>
                  <div className="space-y-2">
                    {pending.map((a) => (
                      <div key={a.id} className="rounded-lg bg-slate-800/60 border border-amber-500/20 p-2"
                        data-testid={`pending-asset-${a.id}`}>
                        {a.image_url ? (
                          <img src={a.image_url} alt="" className="w-full aspect-video object-cover rounded mb-2" />
                        ) : (
                          <div className="w-full aspect-video bg-slate-900 rounded mb-2 flex items-center justify-center text-[10px] text-gray-500 animate-pulse">
                            {a.status === 'failed' ? '❌ فشل التوليد' : '⏳ جاري التوليد...'}
                          </div>
                        )}
                        <p className="text-[10px] text-gray-300 mb-1 font-bold">{a.type}</p>
                        <p className="text-[9px] text-gray-500 mb-2 line-clamp-2">{a.prompt}</p>
                        {a.image_url && (
                          <button type="button" onClick={() => approve(a.id)}
                            data-testid={`approve-asset-${a.id}`}
                            className="w-full py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-[10px] font-black">
                            ✓ اعتمد
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Approved */}
              {(proj.approved_assets || []).length > 0 && (
                <div>
                  <p className="text-emerald-400 text-[10px] font-black mb-2 flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" /> معتمدة ({proj.approved_assets.length})
                  </p>
                  <div className="grid grid-cols-2 gap-1.5">
                    {proj.approved_assets.map((a) => (
                      <div key={a.id} className="rounded overflow-hidden border border-emerald-500/30">
                        {a.image_url && <img src={a.image_url} alt="" className="w-full aspect-square object-cover" />}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {pending.length === 0 && (proj.approved_assets || []).length === 0 && (
                <div className="text-center py-8">
                  <Sparkles className="w-8 h-8 mx-auto mb-2 text-gray-700" />
                  <p className="text-gray-600 text-[11px]">الذكاء سيقترح أصولاً تلقائياً</p>
                </div>
              )}
            </div>
          </div>

          {/* MIDDLE: Chat */}
          <div className="rounded-2xl bg-slate-900/60 border border-slate-700 flex flex-col overflow-hidden">
            <div className="px-4 py-2.5 border-b border-slate-700 bg-slate-800/40">
              <h3 className="text-white font-black text-xs">💬 محادثة التصميم</h3>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="chat-messages">
              {(proj.messages || []).length === 0 && (
                <div className="text-center text-gray-500 py-12">
                  <Sparkles className="w-10 h-10 mx-auto mb-3 text-amber-400/50" />
                  <p className="text-sm">ابدأ بطرح فكرتك للذكاء الاصطناعي</p>
                  <p className="text-xs mt-2 text-gray-600">مثل: «أبي صفحة هبوط بألوان داكنة وhero فيها جبال»</p>
                </div>
              )}
              {(proj.messages || []).map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${m.role === 'user' ? 'bg-amber-500/20 text-amber-100 border border-amber-500/20' : 'bg-slate-800 text-gray-200 border border-slate-700'}`}>
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</p>
                    {m.had_html && (
                      <p className="text-cyan-400 text-[10px] mt-2 flex items-center gap-1">
                        <Eye className="w-3 h-3" /> تم تحديث المعاينة
                      </p>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            <div className="border-t border-slate-700 p-3 flex gap-2">
              <input value={msg} onChange={(e) => setMsg(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
                placeholder="اكتب طلبك (مثل: ابغى hero مع جبال)..."
                disabled={sending}
                data-testid="chat-input"
                className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" />
              <button type="button" onClick={send} disabled={sending || !msg.trim()}
                data-testid="chat-send-btn"
                className="navbar-btn-primary px-4 rounded-lg text-black disabled:opacity-40 font-black flex items-center gap-1.5">
                {sending ? <div className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* RIGHT: Live Preview */}
          {showPreview && (
            <div className="rounded-2xl bg-slate-900/60 border border-slate-700 flex flex-col overflow-hidden">
              <div className="px-3 py-2 border-b border-slate-700 bg-slate-800/40 flex items-center justify-between">
                <h3 className="text-white font-black text-xs flex items-center gap-2">
                  <Eye className="w-3.5 h-3.5 text-cyan-400" /> المعاينة الحية
                </h3>
                <div className="flex items-center gap-1">
                  <button type="button" onClick={() => setPreviewMode('desktop')}
                    data-testid="preview-desktop-btn"
                    className={`p-1.5 rounded ${previewMode === 'desktop' ? 'bg-cyan-500/30 text-cyan-300' : 'text-gray-500 hover:text-gray-300'}`}>
                    <Monitor className="w-3.5 h-3.5" />
                  </button>
                  <button type="button" onClick={() => setPreviewMode('mobile')}
                    data-testid="preview-mobile-btn"
                    className={`p-1.5 rounded ${previewMode === 'mobile' ? 'bg-cyan-500/30 text-cyan-300' : 'text-gray-500 hover:text-gray-300'}`}>
                    <Smartphone className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-auto bg-slate-950 p-3 flex items-start justify-center">
                {proj.current_html ? (
                  <iframe
                    title="Live Preview"
                    data-testid="preview-iframe"
                    srcDoc={proj.current_html}
                    sandbox="allow-scripts allow-same-origin"
                    className={`bg-white rounded-lg shadow-2xl border border-slate-700 transition-all ${previewMode === 'mobile' ? 'w-[375px]' : 'w-full'}`}
                    style={{ height: '100%', minHeight: '500px' }}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-center">
                    <div>
                      <Globe className="w-12 h-12 mx-auto mb-3 text-gray-700" />
                      <p className="text-gray-500 text-sm">لا يوجد HTML بعد</p>
                      <p className="text-gray-600 text-xs mt-1">اطلب من الذكاء بناء صفحة كاملة</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── Main Page ───
const FreeBuildChat = ({ user, setUser }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  if (id === 'new') {
    return <TypePicker onCreate={(pid) => navigate(`/freebuild/chat/${pid}`)} user={user} setUser={setUser} />;
  }
  if (id) return <ChatWorkspace projectId={id} user={user} setUser={setUser} />;
  return <ProjectList user={user} setUser={setUser} />;
};

export default FreeBuildChat;
