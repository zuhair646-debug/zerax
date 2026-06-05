import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Send, Check, AlertCircle, Sparkles, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function GameProject({ user }) {
  const { type, id } = useParams(); // type: 'web' or 'app'
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const messagesEndRef = useRef(null);

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [confirming, setConfirming] = useState(false);

  // ═══════════════════════════════════════════════════════════
  // Load Project
  // ═══════════════════════════════════════════════════════════
  useEffect(() => {
    fetchProject();
  }, [id]);

  useEffect(() => {
    scrollToBottom();
  }, [project?.conversation]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchProject = async () => {
    try {
      const res = await fetch(`${API}/api/games/project/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.ok) {
        setProject(data.project);
      } else {
        toast.error('المشروع غير موجود');
        navigate(`/dashboard/games/${type}`);
      }
    } catch (err) {
      toast.error('خطأ في التحميل');
    } finally {
      setLoading(false);
    }
  };

  // ═══════════════════════════════════════════════════════════
  // Send Message
  // ═══════════════════════════════════════════════════════════
  const handleSend = async () => {
    if (!message.trim() || sending) return;

    const msg = message;
    setMessage('');
    setSending(true);

    try {
      const res = await fetch(`${API}/api/games/${type}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: id,
          message: msg
        })
      });
      const data = await res.json();

      if (data.ok) {
        // Reload project
        await fetchProject();
      } else {
        toast.error(data.error || 'فشل الإرسال');
      }
    } catch (err) {
      toast.error('خطأ في الإرسال');
    } finally {
      setSending(false);
    }
  };

  // ═══════════════════════════════════════════════════════════
  // Confirm Phase
  // ═══════════════════════════════════════════════════════════
  const handleConfirmPhase = async () => {
    setConfirming(true);
    try {
      const res = await fetch(`${API}/api/games/project/${id}/phase`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ approved: true })
      });
      const data = await res.json();

      if (data.ok) {
        toast.success(data.completed ? '🎉 المشروع اكتمل!' : '✅ انتقلت للمرحلة التالية');
        await fetchProject();
      } else {
        toast.error(data.error || 'فشل التأكيد');
      }
    } catch (err) {
      toast.error('خطأ في التأكيد');
    } finally {
      setConfirming(false);
    }
  };

  // ═══════════════════════════════════════════════════════════
  // UI
  // ═══════════════════════════════════════════════════════════
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center text-white">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold">المشروع غير موجود</h2>
        </div>
      </div>
    );
  }

  const phases = project.phases || [];
  const currentPhaseIdx = project.current_phase || 0;
  const currentPhase = phases[currentPhaseIdx];
  const progress = (currentPhaseIdx / phases.length) * 100;
  const isCompleted = project.status === 'completed';

  const lastMessage = project.conversation?.[project.conversation.length - 1];
  const canProceed = lastMessage?.content?.toLowerCase().includes('جاهز للانتقال');

  return (
    <div dir="rtl" className="min-h-screen bg-zinc-950 text-white flex flex-col">
      
      {/* Header */}
      <div className="border-b border-white/10 bg-zinc-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate(`/dashboard/games/${type}`)}
                className="p-2 hover:bg-white/5 rounded-lg transition"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-xl font-bold line-clamp-1">{project.idea}</h1>
                <p className="text-sm text-zinc-400">
                  {type === 'web' ? '🎮 Web Game' : '📱 App Game'}
                </p>
              </div>
            </div>
            
            {/* Balance */}
            <div className="text-left">
              <div className="text-sm text-zinc-400">رصيدك</div>
              <div className="text-lg font-bold text-amber-400">{user.balance || 0} نقطة</div>
            </div>
          </div>

          {/* Progress Bar */}
          {!isCompleted && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-zinc-400 mb-2">
                <span>المرحلة {currentPhaseIdx + 1} من {phases.length}</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div className="h-2 bg-black/40 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    type === 'web'
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-500'
                      : 'bg-gradient-to-r from-purple-500 to-pink-500'
                  }`}
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Sidebar + Chat */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Sidebar — Phases */}
        <div className="w-80 border-l border-white/10 bg-zinc-900/30 p-4 overflow-y-auto">
          <h2 className="text-lg font-bold mb-4">📋 المراحل</h2>
          <div className="space-y-3">
            {phases.map((phase, idx) => {
              const isDone = idx < currentPhaseIdx;
              const isCurrent = idx === currentPhaseIdx;
              const isLocked = idx > currentPhaseIdx;

              return (
                <div
                  key={idx}
                  className={`p-4 rounded-xl border transition ${
                    isDone
                      ? 'bg-green-500/10 border-green-500/30'
                      : isCurrent
                      ? type === 'web'
                        ? 'bg-cyan-500/10 border-cyan-500/50'
                        : 'bg-pink-500/10 border-pink-500/50'
                      : 'bg-black/20 border-white/5'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        isDone
                          ? 'bg-green-500'
                          : isCurrent
                          ? type === 'web'
                            ? 'bg-cyan-500'
                            : 'bg-pink-500'
                          : 'bg-zinc-700'
                      }`}
                    >
                      {isDone ? (
                        <Check className="w-4 h-4 text-white" />
                      ) : (
                        <span className="text-sm font-bold text-white">{idx + 1}</span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-sm mb-1">{phase.title}</h3>
                      <p className="text-xs text-zinc-400 mb-2">{phase.description}</p>
                      <div className="text-xs text-amber-400 font-semibold">{phase.credits} نقطة</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {project.conversation?.map((msg, idx) => {
              const isUser = msg.role === 'user';
              const isSystem = msg.role === 'system';

              if (isSystem) {
                return (
                  <div key={idx} className="flex justify-center">
                    <div className="px-4 py-2 rounded-full bg-green-500/10 border border-green-500/30 text-sm text-green-400">
                      {msg.content}
                    </div>
                  </div>
                );
              }

              return (
                <div key={idx} className={`flex ${isUser ? 'justify-start' : 'justify-end'}`}>
                  <div
                    className={`max-w-2xl rounded-2xl px-6 py-4 ${
                      isUser
                        ? 'bg-white/5 border border-white/10'
                        : type === 'web'
                        ? 'bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border border-cyan-500/30'
                        : 'bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-pink-500/30'
                    }`}
                  >
                    <div className="text-xs text-zinc-500 mb-2">
                      {isUser ? 'أنت' : '🤖 الذكاء الاصطناعي'}
                    </div>
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Input + Confirm Button */}
          <div className="border-t border-white/10 bg-zinc-900/50 backdrop-blur p-4">
            
            {/* Confirm Phase Button */}
            {canProceed && !isCompleted && (
              <div className="mb-4">
                <button
                  onClick={handleConfirmPhase}
                  disabled={confirming}
                  className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-3 transition ${
                    type === 'web'
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-500 hover:opacity-90'
                      : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:opacity-90'
                  } disabled:opacity-50`}
                >
                  {confirming ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      جاري التأكيد...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-5 h-5" />
                      أكّد المرحلة وانتقل للتالي ({currentPhase?.credits} نقطة)
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Message Input */}
            {!isCompleted && (
              <div className="flex gap-3">
                <input
                  type="text"
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  onKeyPress={e => e.key === 'Enter' && handleSend()}
                  placeholder="اكتب رسالتك..."
                  disabled={sending}
                  className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-3 outline-none focus:border-cyan-400 transition"
                  dir="rtl"
                />
                <button
                  onClick={handleSend}
                  disabled={sending || !message.trim()}
                  className={`px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition ${
                    type === 'web'
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-500'
                      : 'bg-gradient-to-r from-purple-500 to-pink-500'
                  } disabled:opacity-50 hover:opacity-90`}
                >
                  {sending ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </div>
            )}

            {isCompleted && (
              <div className="text-center py-8">
                <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
                  <Sparkles className="w-10 h-10 text-green-400" />
                </div>
                <h3 className="text-2xl font-bold mb-2">🎉 المشروع اكتمل!</h3>
                <p className="text-zinc-400">كل المراحل خلصت — مشروعك جاهز للتسليم</p>
              </div>
            )}

          </div>

        </div>

      </div>
    </div>
  );
}
