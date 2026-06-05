import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowLeft, Send, Loader2, Sparkles, Upload, Download,
  Play, CheckCircle, XCircle, AlertCircle, Image as ImageIcon
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function WebGamesStudio({ user }) {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  const [projectMeta, setProjectMeta] = useState(null);
  const [attachments, setAttachments] = useState([]);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (!user) navigate('/login');
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, user, navigate]);

  const phases = [
    { key: 'concept', label: 'التصميم', color: 'blue' },
    { key: 'assets', label: 'الأصول', color: 'purple' },
    { key: 'programming', label: 'البرمجة', color: 'green' },
    { key: 'testing', label: 'الاختبار', color: 'amber' },
    { key: 'deployment', label: 'النشر', color: 'pink' },
  ];

  const handleSend = async () => {
    if (!input.trim() && attachments.length === 0) return;

    const formData = new FormData();
    formData.append('message', input);
    if (sessionId) formData.append('session_id', sessionId);
    attachments.forEach(file => formData.append('files', file));

    const userMsg = {
      role: 'user',
      content: input,
      attachments: attachments.map(f => f.name),
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setAttachments([]);
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/game-studio/web/chat`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        phase: data.phase,
        meta: data.meta,
        timestamp: new Date().toISOString()
      }]);

      if (data.session_id) setSessionId(data.session_id);
      if (data.phase) setCurrentPhase(data.phase);
      if (data.meta) setProjectMeta(data.meta);

    } catch (err) {
      toast.error(err.message);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ خطأ: ${err.message}`,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    setAttachments(prev => [...prev, ...files]);
    toast.success(`تم إضافة ${files.length} ملف`);
  };

  const removeAttachment = (idx) => {
    setAttachments(prev => prev.filter((_, i) => i !== idx));
  };

  const startNewProject = () => {
    setMessages([]);
    setSessionId(null);
    setCurrentPhase(null);
    setProjectMeta(null);
    toast.success('مشروع جديد جاهز');
  };

  return (
    <div dir="rtl" className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <div className="sticky top-0 z-50 bg-zinc-900/80 backdrop-blur border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/dashboard/games')}
                className="p-2 hover:bg-white/10 rounded-xl transition-colors"
                data-testid="back-button"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold flex items-center gap-2">
                  <Sparkles className="w-6 h-6 text-amber-400" />
                  استوديو ألعاب الويب
                </h1>
                <p className="text-sm text-zinc-400 mt-1">
                  Phaser.js • Three.js • Babylon.js — ألعاب HTML5 احترافية
                </p>
              </div>
            </div>
            <button
              onClick={startNewProject}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-500 rounded-xl font-bold transition-colors"
              data-testid="new-project-button"
            >
              مشروع جديد
            </button>
          </div>

          {/* Phase Progress */}
          {currentPhase && (
            <div className="mt-4 flex gap-2 overflow-x-auto pb-2">
              {phases.map(phase => {
                const isActive = phase.key === currentPhase;
                const isDone = phases.findIndex(p => p.key === currentPhase) > phases.findIndex(p => p.key === phase.key);
                return (
                  <div
                    key={phase.key}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-all ${
                      isActive
                        ? `bg-${phase.color}-500/20 border-${phase.color}-500 text-${phase.color}-400`
                        : isDone
                        ? 'bg-green-500/10 border-green-500/30 text-green-400'
                        : 'bg-zinc-800/50 border-white/10 text-zinc-500'
                    }`}
                  >
                    {isDone && <CheckCircle className="w-4 h-4" />}
                    <span className="text-sm font-medium">{phase.label}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Chat Area */}
          <div className="lg:col-span-3">
            <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl overflow-hidden flex flex-col h-[calc(100vh-220px)]">
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.length === 0 && (
                  <div className="text-center py-12 text-zinc-500">
                    <Sparkles className="w-16 h-16 mx-auto mb-4 text-amber-500" />
                    <h3 className="text-xl font-bold mb-2">ابدأ مشروع لعبة ويب احترافي</h3>
                    <p className="text-sm">
                      وصف فكرة لعبتك (مثال: لعبة Flappy Bird، Candy Crush، لعبة سباقات...)
                    </p>
                    <p className="text-xs text-amber-400 mt-2">
                      💡 الذكاء يقسّم المشروع لـ5 مراحل، كل مرحلة تحتاج موافقتك
                    </p>
                  </div>
                )}

                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl p-4 ${
                        msg.role === 'user'
                          ? 'bg-amber-600 text-white'
                          : 'bg-zinc-800 border border-white/10'
                      }`}
                    >
                      {msg.phase && (
                        <div className="text-xs text-amber-400 mb-2 flex items-center gap-1">
                          <AlertCircle className="w-3 h-3" />
                          {phases.find(p => p.key === msg.phase)?.label || msg.phase}
                        </div>
                      )}
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      {msg.attachments && msg.attachments.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {msg.attachments.map((name, i) => (
                            <div key={i} className="text-xs bg-white/10 px-2 py-1 rounded">
                              📎 {name}
                            </div>
                          ))}
                        </div>
                      )}
                      {msg.meta && msg.meta.preview_url && (
                        <div className="mt-3">
                          <a
                            href={msg.meta.preview_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 text-xs bg-green-600 hover:bg-green-500 px-3 py-2 rounded-lg transition-colors"
                          >
                            <Play className="w-4 h-4" />
                            شغّل اللعبة
                          </a>
                        </div>
                      )}
                      {msg.meta && msg.meta.download_url && (
                        <a
                          href={msg.meta.download_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-2 inline-flex items-center gap-2 text-xs bg-blue-600 hover:bg-blue-500 px-3 py-1 rounded-lg transition-colors"
                        >
                          <Download className="w-3 h-3" />
                          تحميل الكود
                        </a>
                      )}
                      <div className="text-xs text-white/50 mt-2">
                        {new Date(msg.timestamp).toLocaleTimeString('ar-SA', {
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </div>
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-zinc-800 border border-white/10 rounded-2xl p-4">
                      <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="border-t border-white/10 p-4">
                {attachments.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-2">
                    {attachments.map((file, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 bg-zinc-800 border border-white/10 rounded-lg px-3 py-2 text-sm"
                      >
                        <ImageIcon className="w-4 h-4 text-amber-400" />
                        <span className="text-xs">{file.name}</span>
                        <button
                          onClick={() => removeAttachment(idx)}
                          className="text-red-400 hover:text-red-300"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex gap-2">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                    multiple
                    accept="image/*,.pdf,.txt"
                    className="hidden"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="p-3 bg-zinc-800 hover:bg-zinc-700 border border-white/10 rounded-xl transition-colors"
                    data-testid="attach-button"
                  >
                    <Upload className="w-5 h-5" />
                  </button>
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                    placeholder="اكتب رسالتك... (مثال: ابي لعبة مثل Flappy Bird)"
                    className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-3 focus:border-amber-400 outline-none"
                    disabled={loading}
                    data-testid="message-input"
                  />
                  <button
                    onClick={handleSend}
                    disabled={loading || (!input.trim() && attachments.length === 0)}
                    className="px-6 py-3 bg-amber-600 hover:bg-amber-500 disabled:bg-zinc-800 disabled:text-zinc-600 rounded-xl font-bold transition-colors flex items-center gap-2"
                    data-testid="send-button"
                  >
                    {loading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <>
                        <Send className="w-5 h-5" />
                        <span>إرسال</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Project Info */}
            {projectMeta && (
              <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl p-4">
                <h3 className="font-bold mb-3 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-amber-400" />
                  معلومات المشروع
                </h3>
                <div className="space-y-2 text-sm">
                  {projectMeta.name && (
                    <div>
                      <span className="text-zinc-400">الاسم:</span>
                      <span className="font-bold mr-2">{projectMeta.name}</span>
                    </div>
                  )}
                  {projectMeta.genre && (
                    <div>
                      <span className="text-zinc-400">النوع:</span>
                      <span className="font-bold mr-2">{projectMeta.genre}</span>
                    </div>
                  )}
                  {projectMeta.credits_used && (
                    <div className="mt-3 pt-3 border-t border-white/10">
                      <span className="text-zinc-400">النقاط المستخدمة:</span>
                      <span className="font-bold text-amber-400 mr-2">
                        {projectMeta.credits_used}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Quick Guide */}
            <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl p-4">
              <h3 className="font-bold mb-3 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-amber-400" />
                دليل سريع
              </h3>
              <div className="space-y-2 text-xs text-zinc-400">
                <p>✅ كل مرحلة تحتاج موافقتك</p>
                <p>✅ ارفع صور مرجعية للـcharacters/backgrounds</p>
                <p>✅ النقاط تُخصم بعد كل مرحلة ناجحة</p>
                <p>✅ تقدر تعيد توليد أي عنصر</p>
                <p className="text-amber-400 mt-3">
                  💡 كل iteration إضافية = نقاط إضافية
                </p>
              </div>
            </div>

            {/* Pricing */}
            <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl p-4">
              <h3 className="font-bold mb-3 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" />
                التسعير
              </h3>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Concept Design</span>
                  <span className="font-bold">30</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Assets Generation</span>
                  <span className="font-bold">50</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Programming</span>
                  <span className="font-bold">100</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Testing</span>
                  <span className="font-bold">30</span>
                </div>
                <div className="flex justify-between border-t border-white/10 pt-2 mt-2">
                  <span className="text-zinc-400">Deployment</span>
                  <span className="font-bold">50</span>
                </div>
                <div className="flex justify-between border-t border-white/10 pt-2 mt-2 text-amber-400">
                  <span>الإجمالي (تقريبي)</span>
                  <span className="font-bold">260+</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
