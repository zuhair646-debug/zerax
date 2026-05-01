import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import { Sparkles, Wand2, Check, X, Loader2, ExternalLink, Pencil, Trash2, RotateCcw, ArrowRight } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const fetchJson = async (url, options = {}) => {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${url}`, { ...options, headers });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text }; }
  if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
  return data;
};

const PreviewFrame = ({ projectId, version }) => {
  const src = useMemo(() => `${API}/api/freebuild/preview/${projectId}?v=${version || 1}`, [projectId, version]);
  return (
    <iframe
      src={src}
      title="Free-build website preview"
      data-testid="freebuild-preview-iframe"
      className="w-full h-full border-0 rounded-lg"
      sandbox="allow-scripts allow-same-origin"
    />
  );
};

const YesNoButton = ({ children, onClick, variant, testId }) => (
  <button
    onClick={onClick}
    data-testid={testId}
    className={`flex-1 px-6 py-5 rounded-2xl font-black text-lg transition-all border-2 ${
      variant === 'yes'
        ? 'bg-gradient-to-br from-emerald-500/20 to-emerald-700/30 border-emerald-400/50 text-emerald-100 hover:from-emerald-400/30 hover:to-emerald-600/40 hover:scale-[1.02]'
        : 'bg-gradient-to-br from-rose-500/15 to-rose-700/20 border-rose-400/40 text-rose-100 hover:from-rose-400/25 hover:to-rose-600/30 hover:scale-[1.02]'
    } active:scale-95`}
  >
    {children}
  </button>
);

const FreeBuild = () => {
  const navigate = useNavigate();
  const [stage, setStage] = useState('intro'); // intro | yn | free_text | ready | generating | done | gallery
  const [session, setSession] = useState(null);
  const [yn, setYn] = useState({ step: 1, total: 17, question: null });
  const [ft, setFt] = useState({ index: 1, total: 3, field: null, value: '' });
  const [summary, setSummary] = useState(null);
  const [project, setProject] = useState(null);
  const [refining, setRefining] = useState(false);
  const [refineText, setRefineText] = useState('');
  const [list, setList] = useState([]);
  const [showGallery, setShowGallery] = useState(false);

  // Auth gate
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      toast.error('سجّل دخولك أولاً');
      navigate('/login');
    }
  }, [navigate]);

  const loadGallery = async () => {
    try {
      const d = await fetchJson('/api/freebuild/projects');
      setList(d.projects || []);
    } catch (e) {
      toast.error('فشل تحميل المشاريع: ' + e.message);
    }
  };

  useEffect(() => { if (showGallery) loadGallery(); }, [showGallery]);

  const begin = async () => {
    try {
      const d = await fetchJson('/api/freebuild/start', { method: 'POST', body: JSON.stringify({}) });
      setSession(d.session_id);
      setYn({ step: d.step, total: d.total_yn, question: d.question });
      setStage('yn');
    } catch (e) { toast.error('فشل البدء: ' + e.message); }
  };

  const answerYn = async (yes) => {
    try {
      const d = await fetchJson('/api/freebuild/answer', {
        method: 'POST',
        body: JSON.stringify({ session_id: session, question_id: yn.question.id, answer: yes }),
      });
      if (d.phase === 'yn') {
        setYn({ step: d.step, total: d.total_yn, question: d.question });
      } else if (d.phase === 'free_text') {
        setFt({ index: d.free_text_index, total: d.free_text_total, field: d.field, value: '' });
        setStage('free_text');
      }
    } catch (e) { toast.error(e.message); }
  };

  const submitFreeText = async () => {
    if (!ft.value.trim()) { toast.error('اكتب الجواب أولاً'); return; }
    try {
      const d = await fetchJson('/api/freebuild/free-text', {
        method: 'POST',
        body: JSON.stringify({ session_id: session, field_id: ft.field.id, value: ft.value.trim() }),
      });
      if (d.phase === 'free_text') {
        setFt({ index: d.free_text_index, total: d.free_text_total, field: d.field, value: '' });
      } else if (d.phase === 'ready') {
        setSummary(d);
        setStage('ready');
      }
    } catch (e) { toast.error(e.message); }
  };

  const generate = async () => {
    setStage('generating');
    try {
      const d = await fetchJson('/api/freebuild/generate', {
        method: 'POST',
        body: JSON.stringify({ session_id: session }),
      });
      setProject(d.project);
      setStage('done');
      toast.success('تم بناء موقعك بنجاح ✨');
    } catch (e) {
      toast.error('فشل التوليد: ' + e.message);
      setStage('ready');
    }
  };

  const refine = async () => {
    if (!refineText.trim() || refineText.trim().length < 4) { toast.error('اكتب التعديل المطلوب'); return; }
    setRefining(true);
    try {
      const d = await fetchJson('/api/freebuild/refine', {
        method: 'POST',
        body: JSON.stringify({ project_id: project.id, instruction: refineText.trim() }),
      });
      setProject({ ...project, version: d.version });
      setRefineText('');
      toast.success('تم تطبيق التعديل');
    } catch (e) { toast.error(e.message); }
    setRefining(false);
  };

  const deleteProject = async (id) => {
    if (!window.confirm('متأكد تبي تحذف هذا المشروع؟')) return;
    try {
      await fetchJson(`/api/freebuild/project/${id}`, { method: 'DELETE' });
      toast.success('تم الحذف');
      loadGallery();
    } catch (e) { toast.error(e.message); }
  };

  const restart = () => {
    setSession(null);
    setYn({ step: 1, total: 17, question: null });
    setFt({ index: 1, total: 3, field: null, value: '' });
    setSummary(null);
    setProject(null);
    setStage('intro');
  };

  // ====================================================================
  return (
    <div dir="rtl" className="min-h-screen bg-[#070710] text-white" data-testid="freebuild-page">
      {/* Header */}
      <div className="sticky top-0 z-30 backdrop-blur-xl bg-black/60 border-b border-amber-400/15">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <button onClick={() => navigate('/')} className="flex items-center gap-2 text-white/70 hover:text-amber-300 transition-colors text-sm" data-testid="back-home-btn">
            <ArrowRight className="w-4 h-4" /> الرئيسية
          </button>
          <div className="flex items-center gap-2 text-amber-200/90 font-black">
            <Wand2 className="w-4 h-4 text-amber-400" /> ذكاء البناء من الصفر
          </div>
          <button
            onClick={() => setShowGallery(true)}
            className="text-xs px-3 py-1.5 rounded-lg bg-amber-400/10 border border-amber-400/30 text-amber-200 hover:bg-amber-400/20"
            data-testid="open-gallery-btn"
          >
            مواقعي
          </button>
        </div>
      </div>

      {/* Stages */}
      <div className="max-w-3xl mx-auto px-4 py-10">
        {stage === 'intro' && (
          <div className="text-center" data-testid="freebuild-intro">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gradient-to-r from-amber-400/15 to-orange-400/15 border border-amber-400/30 text-amber-300 text-xs font-black mb-6">
              <Sparkles className="w-3 h-3" /> ذكاء معماري — يبني فريداً 100%
            </div>
            <h1 className="text-4xl sm:text-6xl font-black tracking-tight mb-4">
              لا قوالب جاهزة.<br/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-300 via-yellow-400 to-amber-500">موقعك يطلع من خيالك</span>
            </h1>
            <p className="text-white/60 text-base sm:text-lg leading-relaxed max-w-2xl mx-auto mb-8">
              نسألك ١٧ سؤال نعم/لا + ٣ أسئلة قصيرة عن رؤيتك. الذكاء المعماري يحلّل إجاباتك ويبني لك موقعاً
              مخصّصاً بصرياً ومضموناً — يختلف عن أي موقع آخر، يعكس شخصيتك ولا يشبه أي قالب.
            </p>
            <div className="grid grid-cols-3 gap-3 max-w-2xl mx-auto mb-10">
              {[
                { n: 1, t: 'إجب نعم/لا', s: '17 سؤال يحدد الذوق' },
                { n: 2, t: 'وصف قصير', s: 'اسم + رؤية + لون' },
                { n: 3, t: 'موقع فريد', s: 'HTML + CSS + JS' },
              ].map((x) => (
                <div key={x.n} className="p-4 rounded-xl bg-white/[0.03] border border-amber-400/10">
                  <div className="text-amber-300 text-2xl font-black mb-1">{x.n}</div>
                  <div className="font-bold text-sm">{x.t}</div>
                  <div className="text-xs text-white/50 mt-1">{x.s}</div>
                </div>
              ))}
            </div>
            <Button
              onClick={begin}
              size="lg"
              className="bg-gradient-to-r from-amber-500 to-yellow-500 text-black font-black text-base px-8 py-6 hover:scale-105 transition-transform shadow-[0_20px_60px_-12px_rgba(245,158,11,0.5)]"
              data-testid="start-interview-btn"
            >
              <Sparkles className="w-5 h-5 ms-2" /> ابدأ المحادثة الآن
            </Button>
            <div className="text-xs text-white/40 mt-3">25 نقطة لكل موقع · 10 نقاط لكل تعديل</div>
          </div>
        )}

        {stage === 'yn' && yn.question && (
          <div data-testid="freebuild-yn-stage">
            <div className="mb-6">
              <div className="flex items-center justify-between text-xs text-white/50 mb-2">
                <span>سؤال {yn.step} من {yn.total}</span>
                <span>{Math.round((yn.step / yn.total) * 100)}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-amber-400 to-yellow-400 transition-all duration-500" style={{ width: `${(yn.step / yn.total) * 100}%` }} />
              </div>
            </div>
            <Card className="bg-gradient-to-br from-white/[0.04] to-white/[0.02] border-amber-400/15 p-8 sm:p-12 mb-6">
              <div className="text-center" data-testid="freebuild-question-text">
                <div className="text-amber-300/70 text-xs font-black tracking-widest uppercase mb-3">
                  Question {yn.step}
                </div>
                <h2 className="text-2xl sm:text-3xl font-black leading-tight">{yn.question.text}</h2>
              </div>
            </Card>
            <div className="flex gap-3">
              <YesNoButton onClick={() => answerYn(false)} variant="no" testId="answer-no-btn">
                <X className="w-5 h-5 inline-block ms-2" /> لا
              </YesNoButton>
              <YesNoButton onClick={() => answerYn(true)} variant="yes" testId="answer-yes-btn">
                <Check className="w-5 h-5 inline-block ms-2" /> نعم
              </YesNoButton>
            </div>
          </div>
        )}

        {stage === 'free_text' && ft.field && (
          <div data-testid="freebuild-freetext-stage">
            <div className="mb-6">
              <div className="flex items-center justify-between text-xs text-white/50 mb-2">
                <span>تفاصيل {ft.index} من {ft.total}</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-amber-400 to-yellow-400" style={{ width: `${(ft.index / ft.total) * 100}%` }} />
              </div>
            </div>
            <Card className="bg-gradient-to-br from-white/[0.04] to-white/[0.02] border-amber-400/15 p-6 sm:p-10">
              <div className="text-amber-300/70 text-xs font-black tracking-widest uppercase mb-2">Detail {ft.index}</div>
              <h2 className="text-xl sm:text-2xl font-black mb-5 leading-tight">{ft.field.label}</h2>
              {ft.field.id === 'vision' ? (
                <Textarea
                  rows={5}
                  value={ft.value}
                  onChange={(e) => setFt({ ...ft, value: e.target.value })}
                  placeholder="مثال: موقع شخصي لمصممة جرافيك سعودية، يبرز هويتها العربية، عصري وأنثوي بلمسة فخامة، الجمهور هم مالكي البراندات..."
                  className="bg-black/50 border-amber-400/20 text-white text-base"
                  data-testid="freetext-textarea"
                />
              ) : (
                <Input
                  value={ft.value}
                  onChange={(e) => setFt({ ...ft, value: e.target.value })}
                  placeholder={ft.field.id === 'site_name' ? 'مثال: نور للتصميم' : 'اختاره أنت'}
                  className="bg-black/50 border-amber-400/20 text-white text-base h-12"
                  data-testid="freetext-input"
                />
              )}
              <Button
                onClick={submitFreeText}
                className="w-full mt-5 bg-gradient-to-r from-amber-500 to-yellow-500 text-black font-black h-12"
                data-testid="freetext-submit-btn"
              >
                التالي ←
              </Button>
            </Card>
          </div>
        )}

        {stage === 'ready' && summary && (
          <div data-testid="freebuild-ready-stage">
            <Card className="bg-gradient-to-br from-emerald-400/10 to-amber-400/10 border-amber-400/40 p-8 mb-6">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-amber-400 to-yellow-500 mb-4 shadow-[0_8px_30px_-8px_rgba(245,158,11,0.7)]">
                  <Wand2 className="w-8 h-8 text-black" />
                </div>
                <h2 className="text-3xl font-black mb-2">جاهز للبناء</h2>
                <p className="text-white/60 mb-5">
                  المهندس الذكي راح يحلل {summary.summary?.yn_answers ? Object.keys(summary.summary.yn_answers).length : 0} إجابة
                  + رؤيتك ويبني الموقع كامل (HTML + CSS + JS).
                </p>
                <div className="inline-block px-4 py-2 rounded-lg bg-black/40 border border-amber-400/30 text-amber-200 text-sm mb-5">
                  التكلفة: {summary.estimated_cost} نقطة · رصيدك: {summary.credits_balance}
                </div>
                <Button
                  onClick={generate}
                  disabled={!summary.can_afford}
                  size="lg"
                  className="w-full bg-gradient-to-r from-amber-500 to-yellow-500 text-black font-black text-base h-14 disabled:opacity-50"
                  data-testid="generate-btn"
                >
                  <Sparkles className="w-5 h-5 ms-2" />
                  {summary.can_afford ? 'ابني موقعي الآن' : 'رصيدك ما يكفي'}
                </Button>
              </div>
            </Card>
          </div>
        )}

        {stage === 'generating' && (
          <div className="text-center py-20" data-testid="freebuild-generating">
            <div className="inline-flex flex-col items-center gap-4">
              <Loader2 className="w-16 h-16 animate-spin text-amber-400" />
              <h2 className="text-2xl font-black">جارٍ البناء...</h2>
              <p className="text-white/60 max-w-md">
                المهندس الذكي يكتب ويصمّم موقعك حالياً. ممكن يأخذ من 30 ثانية إلى دقيقتين.
              </p>
            </div>
          </div>
        )}

        {stage === 'done' && project && (
          <div data-testid="freebuild-done-stage">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-xs text-emerald-400 font-black mb-1">✓ تم البناء بنجاح</div>
                <h2 className="text-2xl font-black">{project.name}</h2>
                <div className="text-xs text-white/40 mt-1">إصدار {project.version}</div>
              </div>
              <div className="flex gap-2">
                <a
                  href={`${API}/api/freebuild/preview/${project.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-2 rounded-lg bg-amber-400/15 border border-amber-400/40 text-amber-200 text-sm hover:bg-amber-400/25 flex items-center gap-1"
                  data-testid="open-preview-btn"
                >
                  <ExternalLink className="w-3.5 h-3.5" /> فتح كصفحة
                </a>
                <button
                  onClick={restart}
                  className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white/70 text-sm hover:bg-white/10 flex items-center gap-1"
                  data-testid="build-another-btn"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> ابني آخر
                </button>
              </div>
            </div>
            <div className="rounded-2xl overflow-hidden border border-amber-400/15 bg-black/40 mb-4" style={{ aspectRatio: '16/10' }}>
              <PreviewFrame projectId={project.id} version={project.version} />
            </div>
            {/* Refinement */}
            <Card className="bg-white/[0.03] border-amber-400/15 p-5">
              <div className="text-amber-300 font-black text-sm mb-2 flex items-center gap-2">
                <Pencil className="w-4 h-4" /> تبي تعدّل؟ اكتب التغيير وخل الذكاء يحدّث (10 نقاط/تعديل)
              </div>
              <Textarea
                rows={2}
                value={refineText}
                onChange={(e) => setRefineText(e.target.value)}
                placeholder="مثال: غيّر الخلفية لذهبي داكن، وضيف قسم آراء العملاء بعد الخدمات"
                className="bg-black/50 border-amber-400/20 text-white"
                data-testid="refine-input"
              />
              <Button
                onClick={refine}
                disabled={refining}
                className="mt-3 bg-amber-500 hover:bg-amber-400 text-black font-black"
                data-testid="refine-submit-btn"
              >
                {refining ? <Loader2 className="w-4 h-4 animate-spin ms-2" /> : <Wand2 className="w-4 h-4 ms-2" />}
                طبّق التعديل
              </Button>
            </Card>
          </div>
        )}
      </div>

      {/* Gallery modal */}
      {showGallery && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-start justify-center p-4 overflow-auto" onClick={() => setShowGallery(false)} data-testid="gallery-modal">
          <div className="bg-[#0c0c18] border border-amber-400/20 rounded-2xl max-w-3xl w-full p-6 my-10" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-xl font-black">مواقعي ({list.length})</h3>
              <button onClick={() => setShowGallery(false)} className="text-white/50 hover:text-white" data-testid="close-gallery-btn">
                <X className="w-5 h-5" />
              </button>
            </div>
            {list.length === 0 ? (
              <div className="text-center py-10 text-white/50">ما عندك مواقع بعد</div>
            ) : (
              <div className="grid gap-3">
                {list.map((p) => (
                  <div key={p.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.04] border border-white/10 hover:border-amber-400/30 transition-colors">
                    <div className="flex-1">
                      <div className="font-bold">{p.name}</div>
                      <div className="text-xs text-white/40">إصدار {p.version} · {new Date(p.created_at).toLocaleDateString('ar')}</div>
                    </div>
                    <a href={`${API}/api/freebuild/preview/${p.id}`} target="_blank" rel="noopener noreferrer"
                       className="text-amber-300 hover:text-amber-200 text-sm flex items-center gap-1" data-testid={`gallery-open-${p.id}`}>
                      <ExternalLink className="w-3.5 h-3.5" /> فتح
                    </a>
                    <button onClick={() => deleteProject(p.id)} className="text-rose-400 hover:text-rose-300" data-testid={`gallery-delete-${p.id}`}>
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default FreeBuild;
