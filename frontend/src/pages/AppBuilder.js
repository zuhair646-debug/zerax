import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import {
  ArrowLeft, Sparkles, Send, Code2, Smartphone, Layers, Upload,
  Github, Database, Key, Rocket, FolderTree, Paperclip, Mic,
  Image as ImageIcon, Loader2, ChevronRight, Check, X, Apple,
  Bot, User as UserIcon, Zap, Brain, Plus,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// ─────────────────────────────────────────────────────────────────────
// 4 modes for app creation
// ─────────────────────────────────────────────────────────────────────
const MODES = [
  {
    id: 'scratch_rn',
    title: 'React Native',
    subtitle: 'الأكثر مرونة',
    desc: 'تطبيق Cross-Platform يشتغل على iOS و Android بنفس الكود. مع Expo.',
    icon: Smartphone,
    accent: '#06b6d4',
    bg: 'from-cyan-500/15 to-blue-500/5',
    pros: ['أسرع تطوير', 'كود واحد لمنصتين', 'مجتمع ضخم', 'مناسب 90% من الحالات'],
    tech: 'React Native + Expo',
  },
  {
    id: 'scratch_flutter',
    title: 'Flutter',
    subtitle: 'الأقوى أداءً',
    desc: 'إطار Google لبناء تطبيقات native بأداء عالي ومظهر موحد على كل المنصات.',
    icon: Layers,
    accent: '#3b82f6',
    bg: 'from-blue-500/15 to-indigo-500/5',
    pros: ['أداء native كامل', 'UI متطابق على كل الأجهزة', 'Hot reload سريع', 'يدعم الويب والديسكتوب'],
    tech: 'Flutter + Dart',
  },
  {
    id: 'scratch_native',
    title: 'Native أصلي',
    subtitle: 'الأفضل أداءً',
    desc: 'Swift لـ iOS و Kotlin لـ Android — أعلى أداء وأقرب لتجربة النظام.',
    icon: Apple,
    accent: '#8b5cf6',
    bg: 'from-violet-500/15 to-purple-500/5',
    pros: ['أداء استثنائي', 'وصول كامل لمزايا النظام', 'مكتبات أصلية', 'مناسب للألعاب والـ AR'],
    tech: 'Swift (iOS) + Kotlin (Android)',
  },
  {
    id: 'continue',
    title: 'تطبيق قابل للإكمال',
    subtitle: 'ارفع كودك ونكمل',
    desc: 'ارفع مشروعك الموجود (ZIP أو GitHub) وخل الذكاء يكمّل ويعدّل عليه.',
    icon: Upload,
    accent: '#f59e0b',
    bg: 'from-amber-500/15 to-orange-500/5',
    pros: ['دعم لأي تقنية', 'صيانة وتحديثات', 'إضافة ميزات جديدة', 'تحويل التقنيات'],
    tech: 'GitHub / ZIP / Repository URL',
  },
];

// Tools available in sidebar
const TOOLS = [
  { id: 'upload', label: 'رفع ملفات', icon: Upload, color: 'text-cyan-400', desc: 'ارفع ZIP أو ملفات منفردة' },
  { id: 'github', label: 'ربط GitHub', icon: Github, color: 'text-zinc-300', desc: 'استورد مستودع موجود' },
  { id: 'keys', label: 'مفاتيح API', icon: Key, color: 'text-amber-400', desc: 'Stripe / Google / Firebase' },
  { id: 'database', label: 'قاعدة بيانات', icon: Database, color: 'text-emerald-400', desc: 'MongoDB / Postgres / Supabase' },
  { id: 'files', label: 'متصفح الملفات', icon: FolderTree, color: 'text-indigo-400', desc: 'استعرض وعدّل المشروع' },
  { id: 'deploy', label: 'النشر', icon: Rocket, color: 'text-rose-400', desc: 'نشر على Vercel/Railway/App Store' },
];

export default function AppBuilder({ user }) {
  const nav = useNavigate();
  const [search] = useSearchParams();
  const initialMode = search.get('mode') === 'continue' ? 'continue' : null;
  const [mode, setMode] = useState(initialMode);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTool, setActiveTool] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Mode selection screen ───────────────────────────────────────────
  if (!mode) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-black to-zinc-950 text-zinc-100">
        <Toaster richColors position="top-center" />

        <div className="border-b border-zinc-800/60 sticky top-0 z-30 bg-zinc-950/85 backdrop-blur-xl">
          <div className="max-w-6xl mx-auto px-5 py-4 flex items-center gap-4">
            <button onClick={() => nav('/')} className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <Code2 className="w-5 h-5 text-cyan-400" />
                <h1 className="text-xl font-bold">منشئ التطبيقات</h1>
              </div>
              <p className="text-xs text-zinc-500 mt-0.5">اختر الطريقة المناسبة لمشروعك</p>
            </div>
          </div>
        </div>

        <div className="max-w-6xl mx-auto px-5 py-8">
          <div className="text-center mb-10">
            <h2 className="text-3xl sm:text-4xl font-black mb-3">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-blue-400">
                كيف تبني تطبيقك؟
              </span>
            </h2>
            <p className="text-zinc-400 text-sm max-w-xl mx-auto">
              4 طرق احترافية — اختر اللي يناسب مهارتك وهدف مشروعك. الذكاء يرشدك خطوة بخطوة في كل واحد.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {MODES.map((m) => {
              const Icon = m.icon;
              return (
                <button
                  key={m.id}
                  onClick={() => setMode(m.id)}
                  data-testid={`mode-${m.id}`}
                  className={`group relative text-right rounded-2xl border border-zinc-800 hover:border-zinc-600 bg-gradient-to-br ${m.bg} p-6 transition-all hover:scale-[1.02] hover:shadow-2xl`}
                  style={{ boxShadow: `0 0 0 0 ${m.accent}00` }}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className="p-3 rounded-xl border"
                      style={{ borderColor: `${m.accent}40`, background: `${m.accent}15` }}
                    >
                      <Icon className="w-6 h-6" style={{ color: m.accent }} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-lg font-bold">{m.title}</h3>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                          {m.subtitle}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400 mb-3 leading-relaxed">{m.desc}</p>
                      <div className="flex flex-wrap gap-1 mb-3">
                        {m.pros.map((p, i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 bg-zinc-800/60 rounded text-zinc-400">
                            {p}
                          </span>
                        ))}
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-zinc-500">{m.tech}</span>
                        <span
                          className="text-[11px] font-bold flex items-center gap-1"
                          style={{ color: m.accent }}
                        >
                          ابدأ <ChevronRight className="w-3 h-3" />
                        </span>
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // ── Chat screen ─────────────────────────────────────────────────────
  const currentMode = MODES.find((m) => m.id === mode);
  const ModeIcon = currentMode.icon;

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setInput('');
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API}/api/autocoder/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          mode: mode,
          context: { app_mode: mode, technology: currentMode.tech },
        }),
      });
      const data = await res.json();
      const reply = data.reply || data.response || data.message || '✨ سأبني هذا لك. أعطني تفاصيل أكثر لو سمحت.';
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: '⚠️ حصل خطأ في الاتصال. حاول مرة ثانية.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 to-black text-zinc-100 flex flex-col">
      <Toaster richColors position="top-center" />

      {/* Header */}
      <div className="border-b border-zinc-800/60 sticky top-0 z-30 bg-zinc-950/85 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-5 py-3 flex items-center gap-3">
          <button onClick={() => setMode(null)} className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400" data-testid="back-to-modes">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div
            className="p-2 rounded-lg"
            style={{ background: `${currentMode.accent}15`, border: `1px solid ${currentMode.accent}40` }}
          >
            <ModeIcon className="w-4 h-4" style={{ color: currentMode.accent }} />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-sm">{currentMode.title}</h1>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                {currentMode.subtitle}
              </span>
            </div>
            <p className="text-[11px] text-zinc-500">{currentMode.tech}</p>
          </div>
          <div className="hidden md:flex items-center gap-1 text-[10px] text-zinc-500">
            <Brain className="w-3 h-3 text-amber-400" />
            <span>Claude Sonnet 4.5</span>
          </div>
        </div>
      </div>

      <div className="flex-1 max-w-7xl w-full mx-auto flex gap-0 overflow-hidden">

        {/* SIDEBAR — Tools */}
        <aside className="hidden md:flex flex-col w-60 border-e border-zinc-800/60 bg-zinc-950/40 py-4 px-3 gap-1 overflow-y-auto">
          <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider px-2 mb-2">
            الأدوات المتاحة
          </div>
          {TOOLS.map((t) => {
            const TIcon = t.icon;
            const active = activeTool === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTool(active ? null : t.id)}
                data-testid={`tool-${t.id}`}
                className={`group flex items-start gap-2 px-2.5 py-2 rounded-lg text-right transition ${
                  active ? 'bg-zinc-800 ring-1 ring-zinc-700' : 'hover:bg-zinc-900'
                }`}
              >
                <TIcon className={`w-4 h-4 mt-0.5 ${t.color}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold">{t.label}</div>
                  <div className="text-[10px] text-zinc-500 leading-tight">{t.desc}</div>
                </div>
              </button>
            );
          })}

          <div className="border-t border-zinc-800/60 mt-4 pt-3">
            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider px-2 mb-2">
              معلومات سريعة
            </div>
            <div className="px-2 py-2 bg-zinc-900/40 rounded-lg space-y-1">
              <p className="text-[11px] text-zinc-400">
                <span className="font-semibold">التقنية:</span> {currentMode.tech}
              </p>
              <p className="text-[11px] text-zinc-400">
                <span className="font-semibold">الذكاء:</span> Claude + Auto Router
              </p>
            </div>
          </div>
        </aside>

        {/* CHAT — Main area */}
        <main className="flex-1 flex flex-col overflow-hidden">

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-6">
            {messages.length === 0 ? (
              <div className="max-w-2xl mx-auto text-center py-12">
                <div
                  className="inline-flex p-4 rounded-2xl mb-4"
                  style={{ background: `${currentMode.accent}15`, border: `1px solid ${currentMode.accent}40` }}
                >
                  <Sparkles className="w-8 h-8" style={{ color: currentMode.accent }} />
                </div>
                <h2 className="text-2xl font-bold mb-2">جاهز لبناء تطبيقك بـ {currentMode.title}</h2>
                <p className="text-sm text-zinc-400 mb-6">
                  اكتب فكرة تطبيقك أو ابدأ بسؤال. الذكاء يرشدك خطوة بخطوة.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-xl mx-auto">
                  {mode === 'continue' ? [
                    'لدي مشروع React Native، أبي أضيف feature login',
                    'حلّل كودي وأخبرني إذا فيه أخطاء',
                    'حوّل تطبيقي من Flutter إلى React Native',
                    'أبي أربط Stripe بتطبيقي',
                  ] : [
                    `تطبيق متجر إلكتروني بـ ${currentMode.title}`,
                    `تطبيق لياقة بدنية بتتبع نشاط`,
                    `تطبيق دردشة مع AI بصوت سعودي`,
                    `تطبيق توصيل طلبات للمطاعم`,
                  ].map((s, i) => (
                    <button
                      key={i}
                      onClick={() => setInput(s)}
                      className="text-right text-xs px-3 py-2.5 bg-zinc-900/60 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-100 transition border border-zinc-800 hover:border-zinc-700"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto space-y-4">
                {messages.map((m, i) => (
                  <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div
                      className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                        m.role === 'user'
                          ? 'bg-zinc-800 text-zinc-300'
                          : 'bg-gradient-to-br from-amber-400 to-orange-500 text-black'
                      }`}
                    >
                      {m.role === 'user' ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>
                    <div className={`flex-1 ${m.role === 'user' ? 'text-right' : ''}`}>
                      <div
                        className={`inline-block px-4 py-2.5 rounded-2xl text-sm max-w-[90%] ${
                          m.role === 'user'
                            ? 'bg-zinc-100 text-zinc-900'
                            : 'bg-zinc-900 border border-zinc-800 text-zinc-200'
                        }`}
                      >
                        <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>
                      </div>
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-black" />
                    </div>
                    <div className="inline-block px-4 py-2.5 rounded-2xl bg-zinc-900 border border-zinc-800">
                      <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Input bar */}
          <div className="border-t border-zinc-800/60 bg-zinc-950/60 backdrop-blur p-3">
            <div className="max-w-3xl mx-auto">
              {/* Active tool indicator */}
              {activeTool && (
                <div className="mb-2 px-3 py-1.5 bg-zinc-900 border border-zinc-800 rounded-lg flex items-center gap-2 text-xs">
                  <span className="text-zinc-400">الأداة النشطة:</span>
                  <span className="font-semibold">{TOOLS.find((t) => t.id === activeTool)?.label}</span>
                  <button onClick={() => setActiveTool(null)} className="ms-auto text-zinc-500 hover:text-zinc-300">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              )}

              <div className="flex items-end gap-2 bg-zinc-900 border border-zinc-800 rounded-2xl p-2">
                <div className="flex items-center gap-1 md:hidden">
                  <button className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400">
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
                  }}
                  placeholder={
                    mode === 'continue'
                      ? 'اكتب طلبك (مثلاً: حلل كودي، أضف ميزة...)'
                      : `صف تطبيقك بـ ${currentMode.title}...`
                  }
                  rows={1}
                  data-testid="app-builder-input"
                  className="flex-1 bg-transparent outline-none resize-none text-sm py-1.5 px-2 min-h-[24px] max-h-32"
                />
                <div className="flex items-center gap-1">
                  <button className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400" title="ملف">
                    <Paperclip className="w-4 h-4" />
                  </button>
                  <button className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400" title="صوت">
                    <Mic className="w-4 h-4" />
                  </button>
                  <button
                    onClick={sendMessage}
                    disabled={!input.trim() || loading}
                    data-testid="app-builder-send"
                    className="p-2.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed text-black rounded-lg transition"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <p className="text-[10px] text-zinc-600 text-center mt-1.5">
                مدعوم بـ Claude Sonnet 4.5 · يمكن استخدام الأدوات الجانبية في أي وقت
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
