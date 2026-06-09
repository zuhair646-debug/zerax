import React, { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Send, Loader2, Sparkles, ArrowLeft, Trash2,
  Wrench, CheckCircle2, Clock, Plus, MessageSquare,
  Eye, Code2, Download, ExternalLink, RefreshCw,
} from 'lucide-react';
import { Toaster, toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import ChatInput from '@/components/ChatInput';

const API = process.env.REACT_APP_BACKEND_URL;

function normalizeAttachment(att) {
  if (!att) return null;
  if (typeof att === 'string') {
    const raw = att;
    const url = raw.startsWith('blob:') || raw.startsWith('data:') || raw.startsWith('http')
      ? raw
      : `${API}${raw.startsWith('/') ? raw : `/${raw}`}`;
    const cleanName = raw.split('/').pop() || 'مرفق';
    return { url, name: cleanName, type: raw.match(/\.(png|jpe?g|gif|webp|bmp|svg)$/i) ? 'image/*' : '' };
  }
  const rawUrl = att.previewUrl || att.url || '';
  const url = rawUrl
    ? (rawUrl.startsWith('blob:') || rawUrl.startsWith('data:') || rawUrl.startsWith('http')
      ? rawUrl
      : `${API}${rawUrl.startsWith('/') ? rawUrl : `/${rawUrl}`}`)
    : '';
  const name = att.name || (rawUrl ? rawUrl.split('/').pop() : 'مرفق');
  const type = att.type || (rawUrl.match(/\.(png|jpe?g|gif|webp|bmp|svg)$/i) ? 'image/*' : '');
  return { ...att, url, name, type };
}

function isImageAttachment(att) {
  return Boolean(att?.type?.startsWith?.('image/') || att?.url?.match?.(/\.(png|jpe?g|gif|webp|bmp|svg)(\?|$)/i));
}

export default function AIAgent() {
  const nav = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [model, setModel] = useState('claude-sonnet-4-5');
  const [conversations, setConversations] = useState([]);
  const [currentStream, setCurrentStream] = useState('');
  const [currentTools, setCurrentTools] = useState([]);
  const [hasHtml, setHasHtml] = useState(false);
  const [previewKey, setPreviewKey] = useState(0);
  const [previewMode, setPreviewMode] = useState('preview'); // preview | mobile
  const [showSidebar, setShowSidebar] = useState(false);
  const scrollRef = useRef(null);
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

  useEffect(() => {
    if (!token) { nav('/login'); return; }
    loadConversations();
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, currentStream, currentTools]);

  const loadConversations = async () => {
    try {
      const r = await fetch(`${API}/api/agent/conversations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      setConversations(d.conversations || []);
    } catch (e) {/* silent */}
  };

  const loadConversation = async (cid) => {
    try {
      const r = await fetch(`${API}/api/agent/conversation/${cid}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      setMessages(d.messages || []);
      setConversationId(cid);
      setHasHtml(!!d.current_html);
      setPreviewKey((k) => k + 1);
      setShowSidebar(false);
    } catch (e) { toast.error('فشل التحميل'); }
  };

  const newChat = () => {
    setMessages([]);
    setConversationId(null);
    setCurrentStream('');
    setCurrentTools([]);
    setHasHtml(false);
    setShowSidebar(false);
  };

  const deleteConversation = async (cid) => {
    if (!window.confirm('احذف هذه المحادثة؟')) return;
    try {
      await fetch(`${API}/api/agent/conversation/${cid}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (cid === conversationId) newChat();
      loadConversations();
    } catch (e) { toast.error(e.message); }
  };

  const downloadHtml = async () => {
    if (!conversationId) return;
    try {
      const r = await fetch(`${API}/api/agent/conversation/${conversationId}/preview`);
      const html = await r.text();
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `zerax-site-${conversationId.slice(0, 8)}.html`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('تم تحميل الملف');
    } catch (e) { toast.error('فشل التحميل'); }
  };

  const send = async ({ text, files = [] }) => {
    const msg = text.trim();
    const hasFiles = Array.isArray(files) && files.length > 0;
    if ((!msg && !hasFiles) || sending) return;

    const outgoingText = msg || 'حلّل المرفقات المرسلة.';
    const localAttachments = files.map((file) => ({
      name: file.name,
      type: file.type,
      size: file.size,
      previewUrl: file.type?.startsWith('image/') ? URL.createObjectURL(file) : '',
    }));
    setSending(true);
    setMessages((prev) => [
      ...prev,
      {
        role: 'user',
        content: outgoingText,
        attachments: localAttachments,
      },
    ]);
    setCurrentStream('');
    setCurrentTools([]);

    try {
      const formData = new FormData();
      formData.append('message', outgoingText);
      formData.append('model', model);
      if (conversationId) formData.append('conversation_id', conversationId);
      files.forEach((file) => formData.append('files', file));

      const r = await fetch(`${API}/api/agent/chat`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      if (!r.body) throw new Error('no stream');
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let assistantText = '';
      let toolEvents = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';
        for (const part of parts) {
          if (!part.startsWith('data: ')) continue;
          try {
            const evt = JSON.parse(part.slice(6));
            if (evt.type === 'text') {
              assistantText += evt.content;
              setCurrentStream(assistantText);
            } else if (evt.type === 'tool') {
              toolEvents.push(evt);
              setCurrentTools([...toolEvents]);
            } else if (evt.type === 'html') {
              setHasHtml(true);
              setPreviewKey((k) => k + 1);
              toast.success(`✨ الموقع جاهز (${(evt.length/1024).toFixed(0)} KB)`);
            } else if (evt.type === 'saved') {
              setConversationId(evt.conversation_id);
              setHasHtml(!!evt.has_html);
              if (Array.isArray(evt.attachments) && evt.attachments.length > 0) {
                setMessages((prev) => {
                  const next = [...prev];
                  for (let i = next.length - 1; i >= 0; i -= 1) {
                    if (next[i]?.role === 'user') {
                      const previousAttachments = Array.isArray(next[i].attachments) ? next[i].attachments : [];
                      next[i] = {
                        ...next[i],
                        attachments: evt.attachments.map((url, idx) => ({
                          ...(previousAttachments[idx] || {}),
                          url,
                        })),
                      };
                      break;
                    }
                  }
                  return next;
                });
              }
              loadConversations();
            } else if (evt.type === 'error') {
              toast.error(evt.message);
            }
          } catch (e) { /* malformed event */ }
        }
      }

      // Commit
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: assistantText, tool_events: toolEvents },
      ]);
      setCurrentStream('');
      setCurrentTools([]);
    } catch (e) {
      toast.error('خطأ في الشبكة: ' + e.message);
    } finally {
      setSending(false);
    }
  };

  const previewSrc = conversationId
    ? `${API}/api/agent/conversation/${conversationId}/preview?v=${previewKey}`
    : null;

  return (
    <div dir="rtl" className="h-screen bg-[#050505] text-white flex flex-col overflow-hidden">
      <Toaster richColors position="top-center" />

      {/* Top bar (mobile + desktop) */}
      <header className="h-14 px-3 md:px-4 border-b border-white/10 flex items-center justify-between bg-black/40 backdrop-blur z-20 flex-shrink-0">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSidebar((s) => !s)}
            data-testid="toggle-sidebar"
            className="md:hidden p-2 hover:bg-white/5 rounded"
          >
            <MessageSquare className="w-4 h-4" />
          </button>
          <button onClick={() => nav('/')} className="p-1.5 hover:bg-white/5 rounded">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h1 className="font-black text-sm flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-amber-400" /> Zerax AI
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            data-testid="model-picker"
            className="bg-black/40 border border-white/15 rounded-md px-2 py-1 text-[11px]"
          >
            <option value="claude-sonnet-4-5">Claude Sonnet 4.5 (موصى)</option>
            <option value="gpt-4o">GPT-4o</option>
          </select>
          <button
            onClick={newChat}
            data-testid="new-chat-btn"
            className="px-3 py-1.5 rounded-md bg-amber-500 text-black text-xs font-bold flex items-center gap-1 hover:bg-amber-400"
          >
            <Plus className="w-3.5 h-3.5" /> جديدة
          </button>
        </div>
      </header>

      {/* Main 3-column layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar — conversations */}
        <aside
          className={`${showSidebar ? 'flex' : 'hidden md:flex'} flex-col w-64 border-e border-white/10 bg-black/30 flex-shrink-0`}
        >
          <div className="p-2 border-b border-white/10 text-[10px] uppercase tracking-widest text-white/40">
            المحادثات
          </div>
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
            {conversations.length === 0 ? (
              <div className="text-center text-white/40 text-xs p-4">لا توجد بعد</div>
            ) : conversations.map((c) => (
              <div
                key={c.id}
                data-testid={`conv-${c.id}`}
                onClick={() => loadConversation(c.id)}
                className={`group p-2 rounded-lg cursor-pointer flex items-start gap-2 text-xs transition ${conversationId === c.id ? 'bg-amber-500/15 border border-amber-400/30' : 'hover:bg-white/5'}`}
              >
                <MessageSquare className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 opacity-60" />
                <span className="flex-1 line-clamp-2 leading-snug">
                  {c.preview || 'محادثة'}
                  {c.has_html && <span className="ms-1 text-amber-400">●</span>}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteConversation(c.id); }}
                  className="opacity-0 group-hover:opacity-100 text-rose-400 hover:text-rose-300"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </aside>

        {/* Chat panel */}
        <main className={`flex flex-col ${hasHtml ? 'lg:w-[42%] xl:w-[40%]' : 'flex-1'} border-e border-white/10 min-w-0`}>
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
            {messages.length === 0 && !currentStream && (
              <div className="max-w-2xl mx-auto text-center py-12">
                <Sparkles className="w-12 h-12 text-amber-400 mx-auto mb-4" />
                <h3 className="text-2xl font-black mb-2">شنو نبني اليوم؟</h3>
                <p className="text-white/60 text-sm mb-6">
                  اطلب أي موقع، أي فكرة. أنا أفكّر معك وأبنيها مباشرة.
                </p>
                <div className="grid md:grid-cols-2 gap-3 text-start">
                  {[
                    { i: '🕌', t: 'موقع تحفيظ قرآن سعودي بـ5 قراء وأجر يومي' },
                    { i: '⚽', t: 'موقع نادي الهلال مع لاعبيه الحاليين' },
                    { i: '🍽️', t: 'مطعم سعودي تراثي اسمه "بيت الجد"' },
                    { i: '🎨', t: 'بورتفوليو لمصمم جرافيك بألوان نيون' },
                  ].map((ex) => (
                    <button
                      key={ex.t}
                      onClick={() => setInput(ex.t)}
                      data-testid="example-chip"
                      className="p-3 rounded-xl border border-white/10 bg-white/[0.03] hover:border-amber-400/30 hover:bg-amber-500/5 text-sm transition flex items-start gap-2"
                    >
                      <span className="text-xl">{ex.i}</span>
                      <span className="leading-snug">{ex.t}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <MessageBubble key={i} message={m} />
            ))}

            {(currentTools.length > 0 || currentStream) && (
              <div className="max-w-3xl">
                {currentTools.length > 0 && (
                  <div className="space-y-1.5 mb-2">
                    {currentTools.map((t, i) => (
                      <ToolPill key={i} tool={t} />
                    ))}
                  </div>
                )}
                {currentStream && (
                  <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-4">
                    <div className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap leading-relaxed">
                      {currentStream}
                      <span className="inline-block w-1.5 h-4 bg-amber-400 animate-pulse ms-1" />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Composer */}
          <div className="p-3 border-t border-white/10 bg-black/40 flex-shrink-0">
            <ChatInput
              value={input}
              onChange={setInput}
              onSend={send}
              placeholder="اكتب طلبك… (Shift+Enter سطر جديد)"
              disabled={sending}
              supportFiles={true}
              supportVoice={true}
              supportEmojis={true}
            />
          </div>
        </main>

        {/* Live preview pane */}
        {hasHtml && previewSrc && (
          <section className="hidden lg:flex flex-col flex-1 bg-[#0a0a0f] min-w-0">
            <div className="h-12 px-3 border-b border-white/10 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-2 text-xs">
                <Eye className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-white/70">المعاينة المباشرة</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPreviewKey((k) => k + 1)}
                  data-testid="refresh-preview"
                  className="p-1.5 rounded hover:bg-white/5 text-white/60"
                  title="تحديث"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setPreviewMode((m) => m === 'mobile' ? 'preview' : 'mobile')}
                  data-testid="toggle-mobile"
                  className={`px-2 py-1 rounded text-[10px] font-bold ${previewMode === 'mobile' ? 'bg-amber-500 text-black' : 'bg-white/5 text-white/60 hover:bg-white/10'}`}
                >
                  جوال
                </button>
                <button
                  onClick={downloadHtml}
                  data-testid="download-html"
                  className="p-1.5 rounded hover:bg-white/5 text-white/60"
                  title="تحميل HTML"
                >
                  <Download className="w-3.5 h-3.5" />
                </button>
                <a
                  href={previewSrc}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="open-preview"
                  className="p-1.5 rounded hover:bg-white/5 text-white/60"
                  title="فتح في نافذة"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
            <div className="flex-1 overflow-auto bg-black flex items-start justify-center p-3">
              <iframe
                key={previewKey}
                src={previewSrc}
                title="معاينة الموقع"
                data-testid="site-preview"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                className={`bg-white shadow-2xl shadow-amber-900/20 border border-white/10 rounded-lg ${
                  previewMode === 'mobile' ? 'w-[375px] h-[680px]' : 'w-full h-full'
                }`}
              />
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`max-w-3xl ${isUser ? 'ms-auto' : ''}`}>
      {!isUser && message.tool_events && message.tool_events.length > 0 && (
        <div className="space-y-1.5 mb-2">
          {message.tool_events
            .filter((t) => t.status === 'done')
            .map((t, i) => (
              <ToolPill key={i} tool={t} />
            ))}
        </div>
      )}
      <div
        className={`rounded-2xl p-4 ${
          isUser
            ? 'bg-gradient-to-br from-amber-500/20 to-amber-600/15 border border-amber-400/30'
            : 'bg-white/[0.04] border border-white/10'
        }`}
      >
        <div className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap leading-relaxed">
          {message.content}
        </div>
        {Array.isArray(message.attachments) && message.attachments.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {message.attachments.map((rawAtt, i) => {
              const att = normalizeAttachment(rawAtt);
              if (!att) return null;
              const image = isImageAttachment(att);
              return (
                <a
                  key={`${att.name || 'file'}-${i}`}
                  href={att.url || undefined}
                  target={att.url ? '_blank' : undefined}
                  rel="noreferrer"
                  className={`group overflow-hidden rounded-xl bg-black/30 border border-white/10 text-white/70 ${image ? 'w-36' : 'px-2 py-1 text-[11px]'}`}
                  title={att.name}
                >
                  {image && att.url ? (
                    <>
                      <img
                        src={att.url}
                        alt={att.name || 'مرفق صورة'}
                        className="h-28 w-full object-cover bg-zinc-900 transition group-hover:scale-[1.02]"
                        loading="lazy"
                      />
                      <div className="px-2 py-1 text-[10px] truncate">📎 {att.name || 'صورة'}</div>
                    </>
                  ) : (
                    <>📎 {att.name || att.url || 'مرفق'}</>
                  )}
                </a>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// Per-color class map (Tailwind needs literal classnames at compile time)
const COLOR_CLASSES = {
  amber: 'bg-amber-500/10 border-amber-400/30 text-amber-200',
  sky: 'bg-sky-500/10 border-sky-400/30 text-sky-200',
  fuchsia: 'bg-fuchsia-500/10 border-fuchsia-400/30 text-fuchsia-200',
  emerald: 'bg-emerald-500/10 border-emerald-400/30 text-emerald-200',
};

function ToolPill({ tool }) {
  const isCalling = tool.status === 'calling';
  const isAudio = tool.name === 'generate_audio' && tool.url;
  const meta = AGENT_META[tool.name] || { icon: '🔧', label: tool.name, color: 'amber' };
  const colorClass = tool.ok === false
    ? 'bg-rose-500/10 border-rose-400/30 text-rose-200'
    : (COLOR_CLASSES[meta.color] || COLOR_CLASSES.amber);
  return (
    <div
      data-testid={`tool-${tool.name}`}
      className={`flex flex-wrap items-center gap-2 px-3 py-1.5 rounded-full text-xs border transition ${colorClass} ${isCalling ? 'animate-pulse' : ''}`}
    >
      <span className="text-sm leading-none">{meta.icon}</span>
      <span className="font-bold text-[11px]">{meta.label}</span>
      {isCalling ? (
        <Clock className="w-3 h-3 opacity-70" />
      ) : tool.ok === false ? (
        <Wrench className="w-3 h-3 opacity-70" />
      ) : (
        <CheckCircle2 className="w-3 h-3 opacity-70" />
      )}
      {!isCalling && tool.summary && (
        <span className="opacity-80">· {tool.summary}</span>
      )}
      {tool.url && tool.name === 'publish_site' && tool.ok && (
        <a
          href={tool.url}
          target="_blank"
          rel="noreferrer"
          className="underline hover:text-white"
        >
          {tool.url}
        </a>
      )}
      {isAudio && (
        <audio controls src={tool.url} className="h-7 max-w-full" />
      )}
    </div>
  );
}

// Agent role mapping → icon + label + color
const AGENT_META = {
  // Workflow phases
  analyze_intent: { icon: '🧠', label: 'Planner', color: 'sky' },
  pick_design: { icon: '🎨', label: 'Designer', color: 'fuchsia' },
  qa_html: { icon: '🧪', label: 'QA', color: 'emerald' },
  publish_site: { icon: '🚀', label: 'Deployer', color: 'amber' },
  // Builders
  build_website: { icon: '🛠️', label: 'Builder', color: 'amber' },
  build_quran_mushaf_reader: { icon: '🕌', label: 'Quran Builder', color: 'emerald' },
  fetch_quran_blocks: { icon: '📖', label: 'Quran Blocks', color: 'emerald' },
  build_creative_quran_site: { icon: '🎮', label: 'Creative Quran', color: 'emerald' },
  build_quran_website: { icon: '🎮', label: 'Quran Site', color: 'emerald' },
  inject_quran_blocks: { icon: '🩹', label: 'Quran Inject', color: 'emerald' },
  update_website: { icon: '🔧', label: 'Updater', color: 'amber' },
  edit_section: { icon: '✏️', label: 'Editor', color: 'amber' },
  add_page: { icon: '📄', label: 'Page Add', color: 'amber' },
  set_theme: { icon: '🎨', label: 'Theme', color: 'fuchsia' },
  // Research / data
  web_search: { icon: '🔎', label: 'Researcher', color: 'sky' },
  web_fetch: { icon: '🌐', label: 'Fetcher', color: 'sky' },
  quran_reciter_lookup: { icon: '🎙️', label: 'Reciters', color: 'emerald' },
  quran_verse_fetch: { icon: '📖', label: 'Verse', color: 'emerald' },
  saudi_official_sources: { icon: '🇸🇦', label: 'KSA Sources', color: 'emerald' },
  sports_team_lookup: { icon: '⚽', label: 'Sports', color: 'sky' },
  geo_lookup: { icon: '🌍', label: 'Geo', color: 'sky' },
  // Media
  generate_image_url: { icon: '🖼️', label: 'Image AI', color: 'fuchsia' },
  generate_audio: { icon: '🎵', label: 'Audio AI', color: 'fuchsia' },
};
