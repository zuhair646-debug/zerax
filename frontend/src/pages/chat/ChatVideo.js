/**
 * Conversational Video Wizard — for the main /chat/video flow.
 *
 * Premium chat-driven experience that adapts questions based on chosen
 * video category (commercial, cinematic, anime, horror, documentary, etc).
 *
 * Flow:
 *   1. Pick category (animated grid)
 *   2. Answer 3-5 contextual questions
 *   3. Pick duration tier (15s / 30s / 45s / 60s / open)
 *   4. Pick voice
 *   5. Review summary + cost → click Generate
 *   6. Watch video render
 */
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Coins, Loader2, Send, Video as VideoIcon, Sparkles, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ChatVideo({ user }) {
  const navigate = useNavigate();
  const [credits, setCredits] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [history, setHistory] = useState([]);            // {role, content, kind?, options?}
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [textAnswer, setTextAnswer] = useState('');
  const [busy, setBusy] = useState(false);
  const [readyState, setReadyState] = useState(null);    // {summary} when wizard complete
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const scrollRef = useRef(null);

  const tokenH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

  useEffect(() => {
    if (!localStorage.getItem('token')) { navigate('/login'); return; }
    refreshCredits();
    startWizard();
  }, [navigate]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [history, currentQuestion, readyState]);

  const refreshCredits = async () => {
    try {
      const r = await fetch(`${API}/api/studio/credits`, { headers: tokenH() });
      if (r.ok) {
        const d = await r.json();
        setCredits(d.credits);
      }
    } catch (_) { /* ignore */ }
  };

  const startWizard = async () => {
    try {
      const r = await fetch(`${API}/api/wizard/video/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenH() },
        body: JSON.stringify({}),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل البدء');
      setSessionId(d.session_id);
      setHistory([{ role: 'assistant', content: d.next_question.label, kind: d.next_question.kind }]);
      setCurrentQuestion(d.next_question);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const submitAnswer = async (answer, displayLabel) => {
    if (busy) return;
    setBusy(true);
    setHistory(h => [...h, { role: 'user', content: displayLabel ?? String(answer) }]);
    setTextAnswer('');
    try {
      const r = await fetch(`${API}/api/wizard/video/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenH() },
        body: JSON.stringify({ session_id: sessionId, answer }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');

      if (d.ready) {
        setReadyState(d.summary);
        setCurrentQuestion(null);
        setHistory(h => [...h, { role: 'assistant', content: '✨ كل شيء جاهز! راجع التفاصيل أدناه ثم اضغط إنشاء الفيديو.', kind: 'final' }]);
      } else {
        const q = d.next_question;
        const stepLabel = q.step_label ? `(${q.step_label}) ` : '';
        setHistory(h => [...h, { role: 'assistant', content: stepLabel + q.label, kind: q.kind }]);
        setCurrentQuestion(q);
      }
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleTextSubmit = () => {
    if (!textAnswer.trim() && !currentQuestion?.optional) {
      toast.error('الرجاء كتابة إجابة');
      return;
    }
    submitAnswer(textAnswer.trim() || '(تخطّى)', textAnswer.trim() || '(تخطّى)');
  };

  const handleGenerate = async () => {
    if (!readyState?.can_afford) {
      toast.error('رصيد النقاط غير كافٍ');
      return;
    }
    setGenerating(true);
    try {
      const r = await fetch(`${API}/api/wizard/video/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenH() },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل التوليد');
      setResult(d.asset);
      setCredits(d.credits_remaining);
      toast.success(`🎬 تم! خُصم ${d.credits_spent} نقاط`);
    } catch (e) {
      toast.error(e.message);
      refreshCredits();
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a12] flex flex-col" data-testid="chat-video-page">
      <Navbar user={user} transparent />
      <div className="pt-20 max-w-4xl mx-auto w-full px-4 pb-6 flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-black text-white">🎬 استوديو الفيديو الذكي</h1>
            <p className="text-orange-300/70 text-xs">شات تفاعلي يبني فيديو احترافي خطوة بخطوة</p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-400/30 text-amber-300 text-sm font-bold" data-testid="chat-video-credits">
            <Coins className="w-4 h-4" />
            <span>{credits ?? '...'}</span>
          </div>
        </div>

        {/* Chat history */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto rounded-2xl border border-white/10 bg-black/30 p-4 space-y-3 min-h-[400px]" data-testid="chat-video-history">
          {history.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`} data-testid={`msg-${i}`}>
              <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm ${
                msg.role === 'user'
                  ? 'bg-orange-500/20 border border-orange-400/30 text-white'
                  : 'bg-white/5 border border-white/10 text-white/90'
              }`}>{msg.content}</div>
            </div>
          ))}

          {/* Render current question's input UI */}
          {currentQuestion?.kind === 'category_picker' && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2" data-testid="category-picker">
              {currentQuestion.options.map(opt => (
                <button key={opt.id} onClick={() => submitAnswer(opt.id, opt.label)}
                  className="p-3 rounded-xl bg-white/5 hover:bg-orange-500/15 border border-white/10 hover:border-orange-400/40 text-right transition" data-testid={`cat-${opt.id}`}>
                  <div className="font-black text-white text-sm">{opt.label}</div>
                  <div className="text-[10px] text-white/60 mt-0.5">{opt.desc}</div>
                </button>
              ))}
            </div>
          )}

          {currentQuestion?.kind === 'duration_picker' && (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-2" data-testid="duration-picker">
              {currentQuestion.options.map(opt => (
                <button key={opt.id} onClick={() => submitAnswer(opt.id, opt.label)}
                  className="p-3 rounded-xl bg-white/5 hover:bg-orange-500/15 border border-white/10 hover:border-orange-400/40 text-center transition" data-testid={`dur-${opt.id}`}>
                  <div className="font-black text-white text-sm">{opt.label}</div>
                  <div className="text-[9px] text-amber-300 font-bold mt-0.5">{opt.cost_per_sec * opt.seconds} نقطة</div>
                  <div className="text-[8px] text-white/50 uppercase">{opt.tier}</div>
                </button>
              ))}
            </div>
          )}

          {currentQuestion?.kind === 'voice_picker' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2" data-testid="voice-picker">
              {currentQuestion.options.map(opt => (
                <button key={opt.id} onClick={() => submitAnswer(opt.id, opt.label)}
                  className="p-3 rounded-xl bg-white/5 hover:bg-purple-500/15 border border-white/10 hover:border-purple-400/40 text-right transition" data-testid={`voice-${opt.id}`}>
                  <div className="font-bold text-white text-sm">{opt.label}</div>
                </button>
              ))}
            </div>
          )}

          {currentQuestion?.kind === 'category_question' && currentQuestion.type === 'select' && (
            <div className="flex flex-wrap gap-2 pt-2" data-testid="select-picker">
              {currentQuestion.options.map(opt => (
                <button key={opt} onClick={() => submitAnswer(opt, opt)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-orange-500/20 border border-white/10 hover:border-orange-400/40 text-sm transition" data-testid={`opt-${opt}`}>
                  {opt}
                </button>
              ))}
            </div>
          )}

          {/* Final summary + generate */}
          {readyState && !result && (
            <div className="mt-3 p-4 rounded-2xl bg-gradient-to-br from-amber-500/15 to-orange-500/10 border border-amber-400/30 space-y-3" data-testid="ready-summary">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-amber-200/60">التكلفة</div>
                  <div className="text-3xl font-black text-amber-300">{readyState.estimated_cost} نقطة</div>
                </div>
                <div className={`px-3 py-1.5 rounded-lg text-xs font-bold ${readyState.can_afford ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`}>
                  {readyState.can_afford ? '✓ رصيدك كافٍ' : `يلزم ${readyState.estimated_cost - readyState.credits_balance} نقاط إضافية`}
                </div>
              </div>
              <div className="text-xs text-white/70">
                <strong className="text-amber-200">{readyState.category_label}</strong> — مدة {readyState.answers?.duration_seconds}s — صوت {readyState.answers?.voice}
              </div>
              <Button onClick={handleGenerate} disabled={generating || !readyState.can_afford}
                className="w-full h-11 bg-gradient-to-r from-orange-500 to-red-600 text-white font-black disabled:opacity-50" data-testid="chat-video-generate">
                {generating ? <Loader2 className="w-4 h-4 me-2 animate-spin" /> : <VideoIcon className="w-4 h-4 me-2" />}
                {generating ? 'جارٍ الإنشاء... (~3-5 دقائق)' : '🎬 أنشئ الفيديو الآن'}
              </Button>
            </div>
          )}

          {result && (
            <div className="mt-3 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-400/30" data-testid="chat-video-result">
              <div className="text-sm font-bold text-emerald-300 mb-2">✓ الفيديو جاهز</div>
              <video src={result.media_url} controls className="w-full rounded-xl mb-3" />
              <div className="flex gap-2">
                <a href={result.media_url} download={`zitex-${result.id}.mp4`} className="flex-1">
                  <Button variant="outline" className="w-full border-emerald-400/30 text-emerald-300">تحميل</Button>
                </a>
                <Button onClick={() => { setResult(null); setReadyState(null); setHistory([]); setCurrentQuestion(null); startWizard(); }}
                  className="bg-orange-500/20 border border-orange-400/30 text-orange-300 hover:bg-orange-500/30" data-testid="chat-video-restart">
                  ابدأ فيديو جديد
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Text input for free-text questions */}
        {currentQuestion?.type === 'text' && (
          <div className="mt-3 flex items-end gap-2" data-testid="text-input-bar">
            <textarea
              value={textAnswer}
              onChange={(e) => setTextAnswer(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleTextSubmit(); } }}
              placeholder={currentQuestion.optional ? 'اكتب إجابتك أو اتركه فارغاً للتخطي' : 'اكتب إجابتك هنا...'}
              className="flex-1 min-h-[50px] max-h-[120px] p-3 bg-black/40 border border-white/10 focus:border-orange-400 rounded-xl text-sm text-white outline-none resize-y"
              data-testid="chat-video-text-input"
              dir="rtl"
            />
            <Button onClick={handleTextSubmit} disabled={busy} className="h-12 px-5 bg-orange-500 hover:bg-orange-600 text-white font-black" data-testid="chat-video-send">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
        )}

        {currentQuestion?.type === 'number' && (
          <div className="mt-3 flex items-end gap-2">
            <input
              type="number"
              min={currentQuestion.min || 1}
              max={currentQuestion.max || 10}
              value={textAnswer}
              onChange={(e) => setTextAnswer(e.target.value)}
              className="flex-1 h-12 p-3 bg-black/40 border border-white/10 focus:border-orange-400 rounded-xl text-center text-2xl font-black outline-none"
              data-testid="chat-video-number-input"
            />
            <Button onClick={() => submitAnswer(parseInt(textAnswer || '1', 10), textAnswer)} disabled={busy || !textAnswer}
              className="h-12 px-5 bg-orange-500 text-white font-black">
              <Send className="w-4 h-4" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
