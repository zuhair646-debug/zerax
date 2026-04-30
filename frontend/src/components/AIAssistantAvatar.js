/**
 * AIAssistantAvatar — premium floating AI assistant widget.
 *
 * Renders a 3D-animated character bubble in the bottom-right of the page.
 * Click to open chat panel. Each user message gets:
 *   - Text reply (Claude Sonnet 4.5)
 *   - Voice reply (ElevenLabs multilingual)
 *   - Subtle "speaking" animation on the character
 *
 * Used in TWO places:
 *   - Landing page (talks about Zitex platform): pass mode="zitex"
 *   - Merchant sites (talks about the shop's products): pass mode="merchant" slug={slug}
 */
import React, { useEffect, useRef, useState } from 'react';
import { MessageCircle, X, Send, Volume2, VolumeX, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AIAssistantAvatar({ mode = 'zitex', slug = null, characterStyle = 'friendly_arab_woman' }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [muted, setMuted] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [enabled, setEnabled] = useState(mode === 'zitex'); // zitex always on; merchant must subscribe
  const audioRef = useRef(null);
  const sessionRef = useRef(null);
  const scrollRef = useRef(null);

  // For merchant mode, check if subscription is active
  useEffect(() => {
    if (mode === 'merchant' && slug) {
      fetch(`${API}/api/merchant/avatar/${slug}`)
        .then(r => r.json())
        .then(d => setEnabled(d.enabled))
        .catch(() => setEnabled(false));
    }
  }, [mode, slug]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, busy]);

  // Greeting message on first open
  useEffect(() => {
    if (open && messages.length === 0) {
      const greeting = mode === 'zitex'
        ? 'أهلاً بك في Zitex! 👋 أنا مساعدك الذكي. اسألني عن أي خدمة — مواقع، صور، فيديوهات، أو طريقة الاشتراك.'
        : 'مرحباً! 👋 أنا مساعدك الذكي في هذا المتجر. اسألني عن أي منتج أو خدمة وسأشرحها لك.';
      setMessages([{ role: 'assistant', content: greeting }]);
    }
  }, [open, mode, messages.length]);

  if (!enabled) return null;

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput('');
    setMessages(m => [...m, { role: 'user', content: text }]);
    setBusy(true);

    const url = mode === 'zitex'
      ? `${API}/api/avatar/chat`
      : `${API}/api/merchant/avatar/${slug}/chat`;
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionRef.current, want_voice: !muted }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'failed');
      sessionRef.current = d.session_id;
      setMessages(m => [...m, { role: 'assistant', content: d.reply, audio: d.audio_url }]);
      if (d.audio_url && !muted) {
        if (audioRef.current) {
          audioRef.current.src = d.audio_url;
          setSpeaking(true);
          audioRef.current.play().catch(() => { /* autoplay blocked */ });
          audioRef.current.onended = () => setSpeaking(false);
        }
      }
    } catch (e) {
      toast.error('عذراً — المساعد غير متاح الآن');
      setMessages(m => [...m, { role: 'assistant', content: 'عذراً، حدث خطأ. حاول مرة أخرى.' }]);
    } finally {
      setBusy(false);
    }
  };

  // Character emoji as fallback (will be replaced with 3D animated SVG)
  const characterEmoji = {
    friendly_arab_woman: '🧕',
    professional_man:    '🧑‍💼',
    cartoon_pet:         '🦊',
  }[characterStyle] || '🤖';

  return (
    <>
      <audio ref={audioRef} />

      {/* Floating bubble button (when closed) */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 group"
          data-testid="avatar-open-btn"
          aria-label="افتح المساعد الذكي"
        >
          <div className="relative">
            {/* Pulsing rings */}
            <span className="absolute inset-0 rounded-full bg-gradient-to-br from-amber-400/40 to-orange-500/40 animate-ping" />
            <span className="absolute inset-0 rounded-full bg-gradient-to-br from-amber-400/20 to-orange-500/20" style={{ animation: 'ping 2.5s cubic-bezier(0,0,.2,1) infinite', animationDelay: '0.5s' }} />
            {/* Main bubble */}
            <div className="relative w-16 h-16 rounded-full bg-gradient-to-br from-amber-400 via-yellow-500 to-orange-500 flex items-center justify-center shadow-[0_8px_30px_-4px_rgba(245,158,11,0.6)] group-hover:scale-110 transition-transform">
              <span className="text-3xl">{characterEmoji}</span>
            </div>
            {/* Notification dot */}
            <span className="absolute -top-1 -left-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
          </div>
          <div className="absolute bottom-full mb-2 right-0 px-2.5 py-1 rounded-lg bg-black/80 text-amber-300 text-[10px] font-bold whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
            تحدّث معي 💬
          </div>
        </button>
      )}

      {/* Chat panel (when open) */}
      {open && (
        <div className="fixed bottom-6 right-6 z-50 w-[92vw] max-w-sm h-[560px] max-h-[85vh] rounded-2xl bg-[#0a0a12] border border-amber-400/30 shadow-2xl shadow-amber-500/20 flex flex-col overflow-hidden" data-testid="avatar-chat-panel">
          {/* Header — character + close */}
          <div className="px-3 py-3 bg-gradient-to-r from-amber-500/20 to-orange-500/15 border-b border-amber-400/20 flex items-center gap-3">
            <div className={`relative w-12 h-12 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg ${speaking ? 'animate-pulse' : ''}`}>
              <span className="text-2xl">{characterEmoji}</span>
              {speaking && (
                <span className="absolute -bottom-1 -left-1 flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-emerald-500 text-white text-[8px] font-bold">
                  <span className="w-1 h-1 bg-white rounded-full animate-pulse" />
                  يتحدّث
                </span>
              )}
            </div>
            <div className="flex-1 text-right">
              <div className="text-sm font-black text-white">
                {mode === 'zitex' ? 'مساعد Zitex' : 'مساعد المتجر'}
              </div>
              <div className="text-[10px] text-emerald-400 flex items-center gap-1 justify-end">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                متصل الآن
              </div>
            </div>
            <button onClick={() => setMuted(!muted)} className="p-2 rounded-lg hover:bg-white/5 text-white/70 hover:text-white" data-testid="avatar-mute-btn" title={muted ? 'تشغيل الصوت' : 'كتم'}>
              {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
            <button onClick={() => setOpen(false)} className="p-2 rounded-lg hover:bg-white/5 text-white/70 hover:text-white" data-testid="avatar-close-btn" aria-label="إغلاق">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3" data-testid="avatar-messages">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] px-3 py-2 rounded-2xl text-sm ${
                  m.role === 'user'
                    ? 'bg-amber-500/20 border border-amber-400/30 text-white'
                    : 'bg-white/5 border border-white/10 text-white/90'
                }`}>
                  {m.content}
                  {m.audio && !muted && (
                    <button onClick={() => { if (audioRef.current) { audioRef.current.src = m.audio; setSpeaking(true); audioRef.current.play(); audioRef.current.onended = () => setSpeaking(false); } }}
                      className="mt-1 inline-flex items-center gap-1 text-[10px] text-amber-300 hover:text-amber-200" data-testid={`avatar-replay-${i}`}>
                      <Volume2 className="w-3 h-3" />
                      شغّل الصوت
                    </button>
                  )}
                </div>
              </div>
            ))}
            {busy && (
              <div className="flex justify-start">
                <div className="px-3 py-2 rounded-2xl bg-white/5 border border-white/10">
                  <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-3 border-t border-white/5 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
              placeholder="اكتب رسالتك..."
              className="flex-1 px-3 py-2 bg-black/40 border border-white/10 focus:border-amber-400 rounded-xl text-sm outline-none"
              data-testid="avatar-input"
              dir="rtl"
            />
            <button onClick={send} disabled={busy || !input.trim()} className="px-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 text-black font-black disabled:opacity-50" data-testid="avatar-send-btn">
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
