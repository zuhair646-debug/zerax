import React, { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Send, Loader2, Sparkles, ArrowLeft, Trash2,
  Wrench, CheckCircle2, Clock, Plus, MessageSquare,
} from 'lucide-react';
import { Toaster, toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const API = process.env.REACT_APP_BACKEND_URL;

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
  const scrollRef = useRef(null);
  const token = typeof window !== 'undefined' ? localStorage.getItem('zitex_token') : null;

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
    } catch (e) { toast.error('فشل التحميل'); }
  };

  const newChat = () => {
    setMessages([]);
    setConversationId(null);
    setCurrentStream('');
    setCurrentTools([]);
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

  const send = async () => {
    const msg = input.trim();
    if (!msg || sending) return;
    setInput('');
    setSending(true);
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setCurrentStream('');
    setCurrentTools([]);

    try {
      const r = await fetch(`${API}/api/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: msg,
          model,
        }),
      });
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
            } else if (evt.type === 'saved') {
              setConversationId(evt.conversation_id);
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

  return (
    <div dir="rtl" className="min-h-screen bg-[#050505] text-white flex">
      <Toaster richColors position="top-center" />

      {/* Sidebar: conversations */}
      <aside className="hidden md:flex w-64 flex-col border-e border-white/10 bg-black/40">
        <div className="p-3 flex items-center gap-2 border-b border-white/10">
          <button onClick={() => nav('/')} className="p-1.5 hover:bg-white/5 rounded">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h1 className="font-black text-sm flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-amber-400" /> Zitex AI
          </h1>
        </div>
        <button
          onClick={newChat}
          data-testid="new-chat-btn"
          className="m-3 px-3 py-2 rounded-lg bg-amber-500 text-black font-bold flex items-center gap-2 justify-center hover:bg-amber-400 transition"
        >
          <Plus className="w-4 h-4" /> محادثة جديدة
        </button>
        <div className="flex-1 overflow-y-auto px-2 space-y-1">
          {conversations.length === 0 ? (
            <div className="text-center text-white/40 text-xs p-4">لا توجد محادثات</div>
          ) : conversations.map((c) => (
            <div
              key={c.id}
              data-testid={`conv-${c.id}`}
              onClick={() => loadConversation(c.id)}
              className={`group p-2 rounded-lg cursor-pointer flex items-start gap-2 text-xs transition ${conversationId === c.id ? 'bg-amber-500/15 border border-amber-400/30' : 'hover:bg-white/5'}`}
            >
              <MessageSquare className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 opacity-60" />
              <span className="flex-1 line-clamp-2 leading-snug">{c.preview || 'محادثة'}</span>
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

      {/* Main chat */}
      <main className="flex-1 flex flex-col">
        {/* Header */}
        <header className="px-4 py-3 border-b border-white/10 flex items-center justify-between bg-black/30 backdrop-blur">
          <div className="flex items-center gap-3">
            <h2 className="font-black text-base">مساعدك الذكي</h2>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              data-testid="model-picker"
              className="bg-black/40 border border-white/15 rounded-md px-2 py-1 text-xs"
            >
              <option value="claude-sonnet-4-5">Claude Sonnet 4.5</option>
              <option value="gpt-4o">GPT-4o</option>
            </select>
          </div>
          <div className="text-[10px] text-white/40">
            {messages.length} رسالة
          </div>
        </header>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          {messages.length === 0 && !currentStream && (
            <div className="max-w-2xl mx-auto text-center py-12">
              <Sparkles className="w-12 h-12 text-amber-400 mx-auto mb-4" />
              <h3 className="text-2xl font-black mb-2">كيف أقدر أساعدك اليوم؟</h3>
              <p className="text-white/60 text-sm mb-6">
                اسألني أي شي، أو جرّب واحد من الأمثلة:
              </p>
              <div className="grid md:grid-cols-2 gap-3">
                {[
                  '⚽ جيب لي لاعبين نادي الهلال الحاليين',
                  '🕌 اقترح أفكار لموقع تحفيظ قرآن مبتكر',
                  '🎓 المصادر التعليمية الرسمية في السعودية',
                  '📖 نص سورة الفاتحة كامل من المصحف',
                ].map((ex) => (
                  <button
                    key={ex}
                    onClick={() => setInput(ex.replace(/^\W+\s/, ''))}
                    data-testid="example-chip"
                    className="text-start p-3 rounded-xl border border-white/10 bg-white/[0.03] hover:border-amber-400/30 hover:bg-amber-500/5 text-sm transition"
                  >{ex}</button>
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
        <div className="p-3 border-t border-white/10 bg-black/40">
          <div className="max-w-3xl mx-auto flex gap-2 items-end">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder="اكتب سؤالك هنا… (Shift+Enter لسطر جديد)"
              data-testid="agent-input"
              disabled={sending}
              className="bg-black/60 border-white/15 min-h-[60px] max-h-[200px] resize-none"
            />
            <Button
              onClick={send}
              disabled={sending || !input.trim()}
              data-testid="agent-send-btn"
              className="bg-amber-500 hover:bg-amber-400 text-black font-black h-[60px] px-5"
            >
              {sending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </Button>
          </div>
        </div>
      </main>
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
      </div>
    </div>
  );
}

function ToolPill({ tool }) {
  const isCalling = tool.status === 'calling';
  return (
    <div
      data-testid={`tool-${tool.name}`}
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs border transition ${
        isCalling
          ? 'bg-amber-500/10 border-amber-400/30 text-amber-200'
          : tool.ok === false
          ? 'bg-rose-500/10 border-rose-400/30 text-rose-200'
          : 'bg-emerald-500/10 border-emerald-400/30 text-emerald-200'
      }`}
    >
      {isCalling ? (
        <Clock className="w-3 h-3 animate-pulse" />
      ) : tool.ok === false ? (
        <Wrench className="w-3 h-3" />
      ) : (
        <CheckCircle2 className="w-3 h-3" />
      )}
      <span className="font-mono">{tool.name}</span>
      {!isCalling && tool.summary && (
        <span className="opacity-80">· {tool.summary}</span>
      )}
    </div>
  );
}
