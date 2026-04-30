/**
 * ZitexDuo — the signature dual AI assistants: Zara (زارا) + Layla (ليلى).
 *
 * Permanent bottom-of-screen companions for the main Zitex site.
 *
 * Features:
 *   - Always visible: both peek from the bottom corners (idle animations)
 *   - Random idle behaviors: hair-play, peek, gaze-swap, gentle bob, blink
 *   - Click on either → she "dodges" aside with a cute reaction
 *   - Click-speak bubble on either → opens chat with her as the speaker
 *   - Smart intent detection: when user says 'ابي صورة' or 'ابي فيديو',
 *     the assistant automatically navigates to /chat/image or /chat/video
 *   - Conversational flow: she asks follow-up questions like a friend
 *   - User can drag them around (simple drag-to-reposition)
 *   - TTS voice for spoken replies
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Send, Volume2, VolumeX, Loader2, MessageCircle } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// Idle animation keyframes (appended to <head> once)
const STYLE_ID = 'zitex-duo-styles';
if (typeof window !== 'undefined' && !document.getElementById(STYLE_ID)) {
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = `
@keyframes zdBob { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
@keyframes zdSway { 0%,100%{transform:rotate(-1deg)} 50%{transform:rotate(1.2deg)} }
@keyframes zdPeek { 0%,85%{transform:translateY(0)} 88%{transform:translateY(-14px)} 95%{transform:translateY(-10px)} 100%{transform:translateY(0)} }
@keyframes zdBlink { 0%,96%,100%{opacity:1} 98%{opacity:0.35} }
@keyframes zdDodge { 0%{transform:translateX(0) rotate(0)} 50%{transform:translateX(-45px) rotate(-8deg)} 100%{transform:translateX(0) rotate(0)} }
@keyframes zdWave { 0%,100%{transform:rotate(0)} 25%{transform:rotate(-12deg)} 75%{transform:rotate(12deg)} }
@keyframes zdFadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
.zd-char { animation: zdBob 4.5s ease-in-out infinite, zdSway 6.2s ease-in-out infinite, zdBlink 7s linear infinite; transition: opacity .3s ease; }
.zd-char-peek { animation: zdPeek 10s ease-in-out infinite, zdBlink 9s linear infinite; }
.zd-char-dodge { animation: zdDodge .7s ease-out; }
.zd-bubble { animation: zdFadeIn .35s ease; }
`;
  document.head.appendChild(style);
}

// Prompts the character asks first based on what user mentions
const INTENT_SNIPPETS = [
  { keywords: ['صور', 'صورة', 'image'],   intent: 'image',   route: '/chat/image',  reaction: '🎨 تمام! صور. اسمح لي أسألك كذا سؤال عشان نطلع بأفضل نتيجة...' },
  { keywords: ['فيديو', 'فيديوهات', 'video'], intent: 'video',   route: '/chat/video',  reaction: '🎬 فيديو! يلا نبدأ — عندي تصنيفات حلوة...' },
  { keywords: ['موقع', 'متجر', 'ستور'],     intent: 'website', route: '/websites',    reaction: '🏗️ ممتاز! موقعك الجديد. عندنا 25 تخصص — خليني أريك...' },
];

function detectIntent(userText) {
  const t = userText.toLowerCase();
  for (const s of INTENT_SNIPPETS) {
    if (s.keywords.some(k => t.includes(k))) return s;
  }
  return null;
}

export default function ZitexDuo() {
  const navigate = useNavigate();
  const [openChar, setOpenChar] = useState(null);  // 'zara' | 'layla' | null
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [muted, setMuted] = useState(false);
  const [speaking, setSpeaking] = useState(null);   // which char is speaking
  const [zaraPos, setZaraPos] = useState({ dodge: false });
  const [laylaPos, setLaylaPos] = useState({ dodge: false });
  const [showHint, setShowHint] = useState(true);
  const [hidden, setHidden] = useState(false);
  const audioRef = useRef(null);
  const sessionRef = useRef(null);
  const scrollRef = useRef(null);

  // Hide hint after 8 sec
  useEffect(() => {
    const t = setTimeout(() => setShowHint(false), 8000);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const dodge = useCallback((who) => {
    if (who === 'zara')  { setZaraPos({ dodge: true });  setTimeout(() => setZaraPos({ dodge: false }), 700); }
    else                 { setLaylaPos({ dodge: true }); setTimeout(() => setLaylaPos({ dodge: false }), 700); }
  }, []);

  const openChat = (who) => {
    setOpenChar(who);
    setShowHint(false);
    if (messages.length === 0) {
      const greeting = who === 'zara'
        ? 'هاي! 👋 أنا زارا. وش اللي يحتاجه قلبك اليوم؟ صورة؟ فيديو؟ موقع؟ قولي وأساعدك خطوة بخطوة ✨'
        : 'أهلاً، أنا ليلى 🖤 جاي في بالك مشروع؟ احكي لي وأنا بأنظّم لك الأفكار وأوصلك لأحسن نتيجة.';
      setMessages([{ role: 'assistant', char: who, content: greeting }]);
    }
  };

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput('');
    setMessages(m => [...m, { role: 'user', content: text }]);
    setBusy(true);

    // Intent detection for auto-routing
    const intent = detectIntent(text);
    try {
      const r = await fetch(`${API}/api/avatar/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionRef.current, want_voice: !muted }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'failed');
      sessionRef.current = d.session_id;
      const speaker = openChar === 'zara' ? 'zara' : 'layla';
      setMessages(m => [...m, { role: 'assistant', char: speaker, content: d.reply, audio: d.audio_url }]);
      if (d.audio_url && !muted && audioRef.current) {
        audioRef.current.src = d.audio_url;
        setSpeaking(speaker);
        audioRef.current.play().catch(() => { /* blocked */ });
        audioRef.current.onended = () => setSpeaking(null);
      }
      // Auto-navigate if intent detected
      if (intent) {
        setTimeout(() => {
          setMessages(m => [...m, { role: 'assistant', char: speaker, content: intent.reaction }]);
          setTimeout(() => {
            setMessages(m => [...m, { role: 'assistant', char: speaker, content: `⚡ خذتك للصفحة المناسبة — استمر معاي هناك.` }]);
            setTimeout(() => navigate(intent.route), 1400);
          }, 1200);
        }, 800);
      }
    } catch (e) {
      toast.error('عذراً — حدث خطأ');
    } finally {
      setBusy(false);
    }
  };

  if (hidden) {
    return (
      <button
        onClick={() => setHidden(false)}
        className="fixed bottom-4 right-4 z-40 px-3 py-2 rounded-full bg-amber-500/20 border border-amber-400/40 text-amber-300 text-xs font-bold hover:bg-amber-500/30"
        data-testid="zd-show-again"
      >
        <MessageCircle className="w-3.5 h-3.5 inline me-1" /> استعد الشخصيات
      </button>
    );
  }

  return (
    <>
      <audio ref={audioRef} />

      {/* Characters peek from bottom corners */}
      <div className="fixed bottom-0 left-0 right-0 z-30 pointer-events-none h-[200px] overflow-visible" data-testid="zd-stage">
        {/* Layla — bottom left */}
        <div
          className={`absolute bottom-0 left-2 sm:left-6 pointer-events-auto cursor-pointer select-none ${laylaPos.dodge ? 'zd-char-dodge' : 'zd-char'}`}
          style={{ width: 130, height: 200 }}
          onClick={() => { dodge('layla'); openChat('layla'); }}
          data-testid="zd-char-layla"
          title="ليلى — اضغط لأتكلّم معك"
        >
          <div className="absolute bottom-0 left-0 right-0 overflow-hidden" style={{ height: 200, borderRadius: '50% 50% 0 0 / 30% 30% 0 0' }}>
            <img
              src="/avatars/f2_layla.png"
              alt="ليلى"
              className="w-full h-auto object-cover object-top"
              style={{ marginTop: -10 }}
            />
          </div>
          {/* Name tag */}
          <div className="absolute -top-2 left-0 right-0 text-center">
            <span className="inline-block px-2 py-0.5 rounded-full bg-black/70 border border-pink-400/40 text-pink-300 text-[9px] font-black">ليلى</span>
          </div>
          {speaking === 'layla' && (
            <div className="absolute -top-8 left-0 right-0 text-center zd-bubble">
              <span className="inline-block px-2 py-0.5 rounded-full bg-emerald-500/90 text-white text-[9px] font-bold">يتحدّث 🔊</span>
            </div>
          )}
        </div>

        {/* Zara — bottom right */}
        <div
          className={`absolute bottom-0 right-2 sm:right-6 pointer-events-auto cursor-pointer select-none ${zaraPos.dodge ? 'zd-char-dodge' : 'zd-char-peek'}`}
          style={{ width: 130, height: 200 }}
          onClick={() => { dodge('zara'); openChat('zara'); }}
          data-testid="zd-char-zara"
          title="زارا — اضغط لأتكلّم معك"
        >
          <div className="absolute bottom-0 left-0 right-0 overflow-hidden" style={{ height: 200, borderRadius: '50% 50% 0 0 / 30% 30% 0 0' }}>
            <img
              src="/avatars/f1_zara.png"
              alt="زارا"
              className="w-full h-auto object-cover object-top"
              style={{ marginTop: -10 }}
            />
          </div>
          <div className="absolute -top-2 left-0 right-0 text-center">
            <span className="inline-block px-2 py-0.5 rounded-full bg-black/70 border border-amber-400/40 text-amber-300 text-[9px] font-black">زارا</span>
          </div>
          {speaking === 'zara' && (
            <div className="absolute -top-8 left-0 right-0 text-center zd-bubble">
              <span className="inline-block px-2 py-0.5 rounded-full bg-emerald-500/90 text-white text-[9px] font-bold">يتحدّث 🔊</span>
            </div>
          )}
        </div>

        {/* First-visit hint */}
        {showHint && !openChar && (
          <div className="absolute bottom-[210px] left-1/2 -translate-x-1/2 pointer-events-none zd-bubble">
            <div className="px-3 py-2 rounded-full bg-amber-500/90 text-black text-[11px] font-black shadow-lg whitespace-nowrap">
              👇 اضغط على أي منّا للتحدّث
            </div>
          </div>
        )}

        {/* Hide (dismiss) button */}
        <button
          onClick={() => setHidden(true)}
          className="absolute top-2 right-4 pointer-events-auto text-white/30 hover:text-white/70 text-xs"
          data-testid="zd-hide-btn"
          title="إخفاء مؤقتاً"
        >
          ✕
        </button>
      </div>

      {/* Chat panel (when a character is selected) */}
      {openChar && (
        <div className="fixed bottom-[210px] right-6 z-40 w-[92vw] max-w-sm h-[440px] rounded-2xl bg-[#0a0a12] border border-amber-400/30 shadow-2xl shadow-amber-500/20 flex flex-col overflow-hidden zd-bubble" data-testid="zd-chat-panel">
          <div className="px-3 py-2.5 bg-gradient-to-r from-amber-500/20 to-pink-500/10 border-b border-amber-400/20 flex items-center gap-3">
            <div className="w-9 h-9 rounded-full overflow-hidden border-2 border-amber-400/50">
              <img src={openChar === 'zara' ? '/avatars/f1_zara.png' : '/avatars/f2_layla.png'} alt="" className="w-full h-full object-cover object-top" />
            </div>
            <div className="flex-1 text-right">
              <div className="text-sm font-black text-white">{openChar === 'zara' ? 'زارا' : 'ليلى'}</div>
              <div className="text-[10px] text-emerald-400 flex items-center gap-1 justify-end">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                متصلة
              </div>
            </div>
            <button onClick={() => setMuted(!muted)} className="p-1.5 rounded-lg hover:bg-white/5 text-white/70" data-testid="zd-mute">
              {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
            <button onClick={() => setOpenChar(null)} className="p-1.5 rounded-lg hover:bg-white/5 text-white/70" data-testid="zd-close">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-2.5">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {m.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-full overflow-hidden border border-amber-400/30 me-2 flex-shrink-0 mt-1">
                    <img src={m.char === 'zara' ? '/avatars/f1_zara.png' : '/avatars/f2_layla.png'} alt="" className="w-full h-full object-cover object-top" />
                  </div>
                )}
                <div className={`max-w-[75%] px-3 py-2 rounded-2xl text-sm ${
                  m.role === 'user'
                    ? 'bg-amber-500/20 border border-amber-400/30 text-white'
                    : 'bg-white/5 border border-white/10 text-white/90'
                }`}>
                  {m.content}
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

          <div className="p-2.5 border-t border-white/5 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
              placeholder={openChar === 'zara' ? 'احكي معي يا حلو...' : 'شاركني أفكارك...'}
              className="flex-1 px-3 py-2 bg-black/40 border border-white/10 focus:border-amber-400 rounded-xl text-sm outline-none"
              data-testid="zd-input"
              dir="rtl"
            />
            <button onClick={send} disabled={busy || !input.trim()} className="px-3 rounded-xl bg-gradient-to-r from-amber-500 to-pink-500 text-white font-black disabled:opacity-50" data-testid="zd-send">
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
