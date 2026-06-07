import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { BackButton } from '@/components/BackButton';
import { Send, CheckCircle, Sparkles, Image as ImageIcon, Globe } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// ─── Step 1: Type Picker + Project Init ───
const TypePicker = ({ onCreate, user, setUser }) => {
  const navigate = useNavigate();
  const [types, setTypes] = useState([]);
  const [selected, setSelected] = useState(null);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/freebuild-chat/types`).then(r => r.json()).then(d => setTypes(d.types || []));
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
        <div className="mb-6"><BackButton to="/dashboard" label="لوحة التحكم" /></div>
        <h1 className="text-3xl font-black text-white mb-2 flex items-center gap-3">
          <Globe className="w-8 h-8 text-cyan-400" /> إنشاء موقع من الصفر
        </h1>
        <p className="text-gray-400 text-sm mb-8">شات ذكي مع توليد أصول · ذاكرة كاملة · موقع نهائي قابل للنشر</p>

        <h2 className="text-lg font-bold text-white mb-3">١. اختر نوع الموقع</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
          {types.map(t => (
            <button key={t.id} type="button" onClick={() => setSelected(t.id)}
              className={`quick-action-card p-4 rounded-xl text-right border-2 ${selected === t.id ? 'border-amber-400 bg-amber-500/10' : 'border-slate-700 bg-slate-800/40'}`}
              data-testid={`type-${t.id}`}>
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
            <input value={name} onChange={e => setName(e.target.value)} placeholder="اسم المشروع"
              className="w-full bg-slate-900/70 border border-slate-700 rounded-lg px-4 py-2.5 text-white mb-3" />
            <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="وصف مختصر (نشاطك، جمهورك، ميزات أساسية)"
              rows={4} className="w-full bg-slate-900/70 border border-slate-700 rounded-lg px-4 py-2.5 text-white" />
            <button type="button" onClick={create} disabled={creating}
              className="navbar-btn-primary mt-4 w-full py-3 rounded-lg font-black text-black"
              data-testid="create-project-btn">
              {creating ? 'جاري الإنشاء...' : 'ابدأ المحادثة الذكية ←'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Step 2: Chat Workspace ───
const ChatWorkspace = ({ projectId, user, setUser }) => {
  const navigate = useNavigate();
  const [proj, setProj] = useState(null);
  const [msg, setMsg] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  const fetchProj = async () => {
    const token = localStorage.getItem('token');
    const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
    if (r.ok) setProj(await r.json());
  };

  useEffect(() => {
    fetchProj();
    const t = setInterval(fetchProj, 5000); // poll for asset generation status
    return () => clearInterval(t);
  }, [projectId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [proj?.messages?.length]);

  const send = async () => {
    if (!msg.trim() || sending) return;
    setSending(true);
    const token = localStorage.getItem('token');
    const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ message: msg }),
    });
    if (r.ok) { setMsg(''); await fetchProj(); }
    else toast.error('فشل الإرسال');
    setSending(false);
  };

  const approve = async (aid) => {
    const token = localStorage.getItem('token');
    await fetch(`${API}/api/freebuild-chat/project/${projectId}/asset/${aid}/approve`, {
      method: 'POST', headers: { Authorization: `Bearer ${token}` },
    });
    toast.success('تم الاعتماد ✓');
    await fetchProj();
  };

  if (!proj) return <div className="min-h-screen bg-[#0a0a12] flex items-center justify-center text-gray-400">جاري التحميل...</div>;

  return (
    <div className="min-h-screen bg-[#0a0a12]">
      <Navbar user={user} setUser={setUser} transparent />
      <div className="container mx-auto px-4 max-w-7xl pt-24 pb-12">
        <div className="mb-4 flex items-center justify-between">
          <BackButton to="/freebuild/chat" label="مشاريعي" />
          <div className="text-right">
            <h1 className="text-xl font-black text-white">{proj.name}</h1>
            <p className="text-gray-400 text-xs">{proj.description?.slice(0, 80)}</p>
          </div>
        </div>

        <div className="grid lg:grid-cols-[1fr_320px] gap-4">
          {/* Chat (center) */}
          <div className="rounded-2xl bg-slate-900/60 border border-slate-700 flex flex-col" style={{ height: '70vh' }}>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {(proj.messages || []).length === 0 && (
                <div className="text-center text-gray-500 py-12">
                  <Sparkles className="w-12 h-12 mx-auto mb-3 text-amber-400/50" />
                  <p className="text-sm">ابدأ بطرح فكرتك للذكاء الاصطناعي</p>
                  <p className="text-xs mt-1">مثلاً: "أبي تصميم للصفحة الرئيسية بألوان دافئة"</p>
                </div>
              )}
              {(proj.messages || []).map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${m.role === 'user' ? 'bg-amber-500/20 text-amber-100' : 'bg-slate-800 text-gray-200'}`}>
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</p>
                    {m.pending_assets?.length > 0 && (
                      <div className="mt-3 grid grid-cols-2 gap-2">
                        {m.pending_assets.map(a => (
                          <div key={a.id} className="rounded-lg bg-black/40 p-2 border border-white/10">
                            {a.image_url ? (
                              <img src={a.image_url} alt="" className="w-full aspect-video object-cover rounded mb-2" />
                            ) : (
                              <div className="w-full aspect-video bg-slate-900 rounded mb-2 flex items-center justify-center text-xs text-gray-500 animate-pulse">
                                {a.status === 'failed' ? '❌ فشل' : '⏳ جاري التوليد...'}
                              </div>
                            )}
                            <p className="text-[10px] text-gray-400 mb-1 line-clamp-1">{a.type} · {a.prompt.slice(0, 30)}</p>
                            {a.image_url && !a.approved && (
                              <button type="button" onClick={() => approve(a.id)}
                                className="w-full py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-[10px] font-bold">
                                ✓ اعتمد
                              </button>
                            )}
                            {a.approved && <p className="text-emerald-400 text-[10px] font-bold text-center">✓ معتمد</p>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            <div className="border-t border-slate-700 p-3 flex gap-2">
              <input value={msg} onChange={e => setMsg(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()}
                placeholder="اكتب طلبك (مثل: ابغى hero مع جبال)..." disabled={sending}
                className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm" />
              <button type="button" onClick={send} disabled={sending || !msg.trim()}
                className="navbar-btn-primary px-4 rounded-lg text-black disabled:opacity-40">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Approved assets sidebar (right) */}
          <div className="rounded-2xl bg-slate-900/60 border border-slate-700 p-4" style={{ height: '70vh', overflowY: 'auto' }}>
            <h3 className="text-white font-black text-sm mb-3 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-400" /> الأصول المعتمدة
            </h3>
            {(proj.approved_assets || []).length === 0 ? (
              <p className="text-gray-500 text-xs text-center py-8">سيظهر هنا كل تصميم بعد اعتماده</p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {proj.approved_assets.map(a => (
                  <div key={a.id} className="rounded-lg overflow-hidden border border-emerald-500/30">
                    {a.image_url && <img src={a.image_url} alt="" className="w-full aspect-square object-cover" />}
                    <p className="text-[9px] text-gray-400 p-1 truncate">{a.type}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ─── Main Page (router) ───
const FreeBuildChat = ({ user, setUser }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  if (id) return <ChatWorkspace projectId={id} user={user} setUser={setUser} />;
  return <TypePicker onCreate={(pid) => navigate(`/freebuild/chat/${pid}`)} user={user} setUser={setUser} />;
};

export default FreeBuildChat;
