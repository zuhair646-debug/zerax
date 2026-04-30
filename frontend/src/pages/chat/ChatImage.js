/**
 * Conversational Image Wizard — for the main /chat/image flow.
 *
 * Deep chat-driven experience that adapts questions based on chosen
 * image category (social_ad, product_shot, banner, portrait, scene, food).
 *
 * Flow:
 *   1. Pick category (animated grid)
 *   2. Answer 3-4 contextual questions (text/select)
 *   3. Pick aspect ratio
 *   4. Pick quality tier (standard 5pts / premium 10pts)
 *   5. Review summary + cost → click Generate
 *   6. Image renders via Gemini Nano Banana
 */
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Coins, Loader2, Send, Image as ImageIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ChatImage({ user }) {
  const navigate = useNavigate();
  const [credits, setCredits] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [history, setHistory] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [textAnswer, setTextAnswer] = useState('');
  const [busy, setBusy] = useState(false);
  const [readyState, setReadyState] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const scrollRef = useRef(null);

  const tokenH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

  useEffect(() => {
    if (!localStorage.getItem('token')) { navigate('/login'); return; }
    refreshCredits();
    startWizard();

    // Pull voice intent if user came from Voice Stage
    try {
      const raw = sessionStorage.getItem('zitex_voice_intent');
      if (raw) {
        const data = JSON.parse(raw);
        if (data.intent === 'image' && data.subject && (Date.now() - (data.ts || 0)) < 60000) {
          // Pre-fill the first text input with the voice subject — wait for wizard to load
          setTimeout(() => {
            setTextAnswer(data.subject);
            toast.success(`✓ سمعتك: "${data.subject}". اضغطي تأكيد أو عدّلي`);
          }, 800);
        }
        sessionStorage.removeItem('zitex_voice_intent');
      }
    } catch (_) {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      const r = await fetch(`${API}/api/wizard/image/start`, {
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
      const r = await fetch(`${API}/api/wizard/image/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenH() },
        body: JSON.stringify({ session_id: sessionId, answer }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');

      if (d.ready) {
        setReadyState(d.summary);
        setCurrentQuestion(null);
        setHistory(h => [...h, { role: 'assistant', content: '✨ تمام! كل شي جاهز. راجع التفاصيل واضغط "أنشئ الصورة".', kind: 'final' }]);
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
      toast.error('اكتب إجابتك');
      return;
    }
    submitAnswer(textAnswer.trim() || '(تخطّى)', textAnswer.trim() || '(تخطّى)');
  };

  const handleGenerate = async () => {
    if (!readyState?.can_afford) {
      toast.error('رصيدك مو كافي');
      return;
    }
    setGenerating(true);
    try {
      const r = await fetch(`${API}/api/wizard/image/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenH() },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل التوليد');
      setResult(d.asset);
      setCredits(d.credits_remaining);
      toast.success(`🎨 تم! خُصم ${d.credits_spent} نقطة`);
    } catch (e) {
      toast.error(e.message);
      refreshCredits();
    } finally {
      setGenerating(false);
    }
  };

  const restart = () => {
    setResult(null); setReadyState(null); setHistory([]); setCurrentQuestion(null);
    startWizard();
  };

  return (
    <div className="min-h-screen bg-[#0a0a12] flex flex-col" data-testid="chat-image-page">
      <Navbar user={user} transparent />
      <div className="pt-20 max-w-4xl mx-auto w-full px-4 pb-6 flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-black text-white">🎨 استوديو الصور الذكي</h1>
            <p className="text-purple-300/70 text-xs">شات تفاعلي يبني صورة احترافية خطوة خطوة</p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-400/30 text-amber-300 text-sm font-bold" data-testid="chat-image-credits">
            <Coins className="w-4 h-4" />
            <span>{credits ?? '...'}</span>
          </div>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto rounded-2xl border border-white/10 bg-black/30 p-4 space-y-3 min-h-[400px]" data-testid="chat-image-history">
          {history.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`} data-testid={`img-msg-${i}`}>
              <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm ${
                msg.role === 'user'
                  ? 'bg-purple-500/20 border border-purple-400/30 text-white'
                  : 'bg-white/5 border border-white/10 text-white/90'
              }`}>{msg.content}</div>
            </div>
          ))}

          {currentQuestion?.kind === 'category_picker' && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2" data-testid="img-category-picker">
              {currentQuestion.options.map(opt => (
                <button key={opt.id} onClick={() => submitAnswer(opt.id, opt.label)}
                  className="p-3 rounded-xl bg-white/5 hover:bg-purple-500/15 border border-white/10 hover:border-purple-400/40 text-right transition" data-testid={`img-cat-${opt.id}`}>
                  <div className="font-black text-white text-sm">{opt.label}</div>
                  <div className="text-[10px] text-white/60 mt-0.5">{opt.desc}</div>
                </button>
              ))}
            </div>
          )}

          {currentQuestion?.kind === 'aspect_picker' && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2" data-testid="img-aspect-picker">
              {currentQuestion.options.map(opt => (
                <button key={opt.id} onClick={() => submitAnswer(opt.id, opt.label)}
                  className="p-3 rounded-xl bg-white/5 hover:bg-purple-500/15 border border-white/10 hover:border-purple-400/40 text-center transition" data-testid={`img-aspect-${opt.id}`}>
                  <div className="font-black text-white text-sm">{opt.label}</div>
                  <div className="text-[10px] text-white/60 mt-0.5">{opt.desc}</div>
                </button>
              ))}
            </div>
          )}

          {currentQuestion?.kind === 'quality_picker' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2" data-testid="img-quality-picker">
              {currentQuestion.options.map(opt => (
                <button key={opt.id} onClick={() => submitAnswer(opt.id, opt.label)}
                  className="p-3 rounded-xl bg-white/5 hover:bg-amber-500/15 border border-white/10 hover:border-amber-400/40 text-right transition" data-testid={`img-q-${opt.id}`}>
                  <div className="font-black text-white text-sm">{opt.label}</div>
                  <div className="text-[10px] text-white/60 mt-0.5">{opt.desc}</div>
                  <div className="text-[10px] text-amber-300 font-bold mt-1">{opt.cost} نقطة</div>
                </button>
              ))}
            </div>
          )}

          {currentQuestion?.kind === 'category_question' && currentQuestion.type === 'select' && (
            <div className="flex flex-wrap gap-2 pt-2" data-testid="img-select-picker">
              {currentQuestion.options.map(opt => (
                <button key={opt} onClick={() => submitAnswer(opt, opt)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-purple-500/20 border border-white/10 hover:border-purple-400/40 text-sm transition" data-testid={`img-opt-${opt}`}>
                  {opt}
                </button>
              ))}
            </div>
          )}

          {readyState && !result && (
            <div className="mt-3 p-4 rounded-2xl bg-gradient-to-br from-purple-500/15 to-pink-500/10 border border-purple-400/30 space-y-3" data-testid="img-ready-summary">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-purple-200/60">التكلفة</div>
                  <div className="text-3xl font-black text-purple-300">{readyState.estimated_cost} نقطة</div>
                </div>
                <div className={`px-3 py-1.5 rounded-lg text-xs font-bold ${readyState.can_afford ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`}>
                  {readyState.can_afford ? '✓ رصيدك كافي' : `محتاج ${readyState.estimated_cost - readyState.credits_balance} نقاط زود`}
                </div>
              </div>
              <div className="text-xs text-white/70">
                <strong className="text-purple-200">{readyState.category_label}</strong> — مقاس {readyState.answers?.aspect_ratio} — جودة {readyState.answers?.quality}
              </div>
              <Button onClick={handleGenerate} disabled={generating || !readyState.can_afford}
                className="w-full h-11 bg-gradient-to-r from-purple-500 to-violet-600 text-white font-black disabled:opacity-50" data-testid="chat-image-generate">
                {generating ? <Loader2 className="w-4 h-4 me-2 animate-spin" /> : <ImageIcon className="w-4 h-4 me-2" />}
                {generating ? 'جارٍ الإنشاء... (~20 ثانية)' : '🎨 أنشئ الصورة الآن'}
              </Button>
            </div>
          )}

          {result && (
            <div className="mt-3 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-400/30" data-testid="chat-image-result">
              <div className="text-sm font-bold text-emerald-300 mb-2">✓ الصورة جاهزة</div>
              <img src={result.media_url} alt="generated" className="w-full rounded-xl mb-3" />
              <div className="flex gap-2">
                <a href={result.media_url} download={`zitex-${result.id}.png`} className="flex-1">
                  <Button variant="outline" className="w-full border-emerald-400/30 text-emerald-300">تحميل</Button>
                </a>
                <Button onClick={restart}
                  className="bg-purple-500/20 border border-purple-400/30 text-purple-300 hover:bg-purple-500/30" data-testid="chat-image-restart">
                  صورة جديدة
                </Button>
              </div>
            </div>
          )}
        </div>

        {currentQuestion?.type === 'text' && (
          <div className="mt-3 flex items-end gap-2" data-testid="img-text-input-bar">
            <textarea
              value={textAnswer}
              onChange={(e) => setTextAnswer(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleTextSubmit(); } }}
              placeholder={currentQuestion.optional ? 'اكتب إجابتك أو اتركها فارغة للتخطي' : 'اكتب إجابتك هنا...'}
              className="flex-1 min-h-[50px] max-h-[120px] p-3 bg-black/40 border border-white/10 focus:border-purple-400 rounded-xl text-sm text-white outline-none resize-y"
              data-testid="chat-image-text-input"
              dir="rtl"
            />
            <Button onClick={handleTextSubmit} disabled={busy} className="h-12 px-5 bg-purple-500 hover:bg-purple-600 text-white font-black" data-testid="chat-image-send">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
