import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, Loader2, Send, Paperclip, X, Check, AlertCircle, 
  Eye, Download, Code, Image as ImageIcon, Music, FileText,
  Sparkles, PlayCircle, Zap
} from 'lucide-react';
import { toast } from 'sonner';
import ChatInput from '../components/ChatInput';

const API = process.env.REACT_APP_BACKEND_URL;

export default function WebGameProject({ user }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const messagesEndRef = useRef(null);

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [activeTab, setActiveTab] = useState('chat'); // chat | assets | preview
  const [assets, setAssets] = useState({
    characters: [],
    environments: [],
    ui: [],
    sounds: [],
    code: [],
    docs: []
  });

  // ═══════════════════════════════════════════════════════════
  // Load Project
  // ═══════════════════════════════════════════════════════════
  useEffect(() => {
    fetchProject();
  }, [id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchProject = async () => {
    try {
      const res = await fetch(`${API}/api/games/project/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.ok) {
        setProject(data.project);
        setMessages(data.project.messages || []);
        setAssets(data.project.assets || {
          characters: [], environments: [], ui: [], sounds: [], code: [], docs: []
        });
      } else {
        toast.error(data.error || 'فشل تحميل المشروع');
        navigate('/dashboard/games/web');
      }
    } catch (err) {
      toast.error('خطأ في التحميل');
      navigate('/dashboard/games/web');
    } finally {
      setLoading(false);
    }
  };

  // ═══════════════════════════════════════════════════════════
  // Send Message (with attachments)
  // ═══════════════════════════════════════════════════════════
  const handleSend = async (text, files, audioBlob) => {
    if (!text?.trim() && files.length === 0 && !audioBlob) return;

    const formData = new FormData();
    if (text?.trim()) formData.append('message', text.trim());
    
    if (files && files.length > 0) {
      files.forEach(file => formData.append('files', file));
    }
    
    if (audioBlob) {
      formData.append('audio', audioBlob, 'voice.webm');
    }

    // Optimistic update
    const tempMsg = {
      id: Date.now(),
      role: 'user',
      content: text || '🎤 رسالة صوتية',
      attachments: files?.map(f => ({ name: f.name, type: f.type })) || [],
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempMsg]);
    setInput('');
    setAttachments([]);
    setSending(true);

    try {
      const res = await fetch(`${API}/api/games/web/chat`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      const data = await res.json();

      if (data.ok) {
        setMessages(data.messages);
        setAssets(data.assets || assets);
        setProject(prev => ({ ...prev, current_phase: data.current_phase }));
      } else {
        toast.error(data.error || 'فشل الإرسال');
        setMessages(prev => prev.slice(0, -1));
      }
    } catch (err) {
      toast.error('خطأ في الإرسال');
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setSending(false);
    }
  };

  // ═══════════════════════════════════════════════════════════
  // Approve Phase & Move Next
  // ═══════════════════════════════════════════════════════════
  const handleApprovePhase = async () => {
    try {
      const res = await fetch(`${API}/api/games/project/${id}/phase`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ action: 'approve' })
      });
      const data = await res.json();
      
      if (data.ok) {
        toast.success('تم الانتقال للمرحلة التالية!');
        setProject(data.project);
      } else {
        toast.error(data.error || 'فشل التأكيد');
      }
    } catch (err) {
      toast.error('خطأ في التأكيد');
    }
  };

  // ═══════════════════════════════════════════════════════════
  // UI Helpers
  // ═══════════════════════════════════════════════════════════
  const getPhaseIcon = (phaseId) => {
    const icons = {
      discovery: '🔍', mechanics: '⚙️', characters: '🎭',
      environment: '🏞️', assets: '🎨', programming: '💻',
      testing: '🧪', deployment: '🚀'
    };
    return icons[phaseId] || '📦';
  };

  const getAssetIcon = (type) => {
    const icons = {
      characters: '🎭', environments: '🏞️', ui: '🎨',
      sounds: '🎵', code: '💻', docs: '📄'
    };
    return icons[type] || '📦';
  };

  // ═══════════════════════════════════════════════════════════
  // Main Render
  // ═══════════════════════════════════════════════════════════
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center text-white">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">المشروع غير موجود</h2>
          <button
            onClick={() => navigate('/dashboard/games/web')}
            className="px-4 py-2 bg-cyan-500 rounded-lg hover:bg-cyan-400 transition"
          >
            العودة
          </button>
        </div>
      </div>
    );
  }

  const currentPhase = project.phases?.[project.current_phase];
  const progress = ((project.current_phase || 0) / (project.phases?.length || 1)) * 100;

  return (
    <div dir="rtl" className="h-screen bg-zinc-950 text-white flex flex-col overflow-hidden">
      
      {/* ═════════════════════════════════════════════════════════════ */}
      {/* Header */}
      {/* ═════════════════════════════════════════════════════════════ */}
      <div className="flex-none bg-zinc-900/50 backdrop-blur border-b border-white/10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4 flex-1">
            <button
              onClick={() => navigate('/dashboard/games/web')}
              className="p-2 hover:bg-white/5 rounded-lg transition"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex-1">
              <h1 className="text-xl font-bold line-clamp-1">{project.idea}</h1>
              <div className="flex items-center gap-4 mt-1">
                <span className="text-sm text-zinc-400">
                  {currentPhase ? `${getPhaseIcon(currentPhase.id)} ${currentPhase.title}` : 'جاري التحضير'}
                </span>
                <div className="flex-1 max-w-xs h-2 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-xs text-zinc-500">{Math.round(progress)}%</span>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-2 rounded-lg font-bold transition ${
                activeTab === 'chat'
                  ? 'bg-cyan-500 text-black'
                  : 'bg-white/5 hover:bg-white/10'
              }`}
            >
              💬 الشات
            </button>
            <button
              onClick={() => setActiveTab('assets')}
              className={`px-4 py-2 rounded-lg font-bold transition ${
                activeTab === 'assets'
                  ? 'bg-purple-500 text-black'
                  : 'bg-white/5 hover:bg-white/10'
              }`}
            >
              🎨 الأصول
            </button>
            <button
              onClick={() => setActiveTab('preview')}
              className={`px-4 py-2 rounded-lg font-bold transition ${
                activeTab === 'preview'
                  ? 'bg-green-500 text-black'
                  : 'bg-white/5 hover:bg-white/10'
              }`}
            >
              👁️ المعاينة
            </button>
          </div>
        </div>
      </div>

      {/* ═════════════════════════════════════════════════════════════ */}
      {/* Main Content */}
      {/* ═════════════════════════════════════════════════════════════ */}
      <div className="flex-1 overflow-hidden flex">
        
        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="flex-1 flex flex-col">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {messages.map((msg, idx) => (
                <div
                  key={msg.id || idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-2xl rounded-2xl px-6 py-4 ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-r from-cyan-500 to-blue-500 text-black'
                        : 'bg-zinc-900/80 backdrop-blur border border-white/10'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                    {msg.attachments?.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-3">
                        {msg.attachments.map((att, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2 px-3 py-1 bg-black/20 rounded-lg text-xs"
                          >
                            <Paperclip className="w-3 h-3" />
                            {att.name || att.url?.split('/').pop()}
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="text-xs opacity-60 mt-2">
                      {new Date(msg.timestamp).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="bg-zinc-900/80 backdrop-blur border border-white/10 rounded-2xl px-6 py-4">
                    <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Phase Actions */}
            {currentPhase && (
              <div className="flex-none px-6 py-3 bg-zinc-900/30 backdrop-blur border-t border-white/10">
                <div className="max-w-4xl mx-auto flex items-center justify-between">
                  <div className="flex-1">
                    <div className="text-sm font-bold mb-1">{currentPhase.title}</div>
                    <div className="text-xs text-zinc-400">{currentPhase.description}</div>
                  </div>
                  <button
                    onClick={handleApprovePhase}
                    disabled={project.current_phase >= project.phases.length - 1}
                    className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl font-bold hover:opacity-90 transition disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    <Check className="w-5 h-5" />
                    اعتمد المرحلة
                  </button>
                </div>
              </div>
            )}

            {/* Chat Input */}
            <div className="flex-none p-4 border-t border-white/10">
              <ChatInput
                onSend={handleSend}
                disabled={sending}
                placeholder="اكتب رسالتك... (يمكنك رفع صور أو مستندات مرجعية)"
                enableVoice={true}
                enableAttachments={true}
              />
            </div>
          </div>
        )}

        {/* Assets Tab */}
        {activeTab === 'assets' && (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto space-y-8">
              {Object.entries(assets).map(([category, items]) => (
                <div key={category}>
                  <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    {getAssetIcon(category)}
                    {category === 'characters' && 'الشخصيات'}
                    {category === 'environments' && 'البيئات'}
                    {category === 'ui' && 'واجهة المستخدم'}
                    {category === 'sounds' && 'الأصوات والموسيقى'}
                    {category === 'code' && 'الكود والبرمجة'}
                    {category === 'docs' && 'المستندات'}
                    <span className="text-sm text-zinc-500">({items.length})</span>
                  </h3>
                  
                  {items.length === 0 ? (
                    <div className="text-center py-8 text-zinc-500">
                      لا توجد أصول بعد في هذا القسم
                    </div>
                  ) : (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {items.map((asset, idx) => (
                        <div
                          key={idx}
                          className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-xl p-4 hover:border-cyan-400/50 transition group"
                        >
                          {asset.preview_url && (
                            <img
                              src={asset.preview_url}
                              alt={asset.name}
                              className="w-full h-32 object-cover rounded-lg mb-3"
                            />
                          )}
                          <div className="font-bold mb-1">{asset.name}</div>
                          <div className="text-xs text-zinc-400 mb-3 line-clamp-2">
                            {asset.description}
                          </div>
                          {asset.metadata && (
                            <div className="text-xs text-zinc-500 space-y-1">
                              {asset.metadata.role && <div>الدور: {asset.metadata.role}</div>}
                              {asset.metadata.abilities && (
                                <div>القدرات: {asset.metadata.abilities.join(', ')}</div>
                              )}
                            </div>
                          )}
                          <div className="flex gap-2 mt-3">
                            {asset.url && (
                              <a
                                href={asset.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-1 px-3 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1"
                              >
                                <Eye className="w-3 h-3" />
                                عرض
                              </a>
                            )}
                            {asset.download_url && (
                              <a
                                href={asset.download_url}
                                download
                                className="flex-1 px-3 py-2 bg-green-500/20 hover:bg-green-500/30 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1"
                              >
                                <Download className="w-3 h-3" />
                                تحميل
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Preview Tab */}
        {activeTab === 'preview' && (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-5xl mx-auto">
              {project.live_url ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-2xl font-bold">👁️ معاينة حية</h3>
                    <a
                      href={project.live_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 rounded-lg font-bold transition"
                    >
                      فتح في نافذة جديدة ↗
                    </a>
                  </div>
                  <iframe
                    src={project.live_url}
                    className="w-full h-[600px] bg-black rounded-xl border border-white/20"
                    title="Game Preview"
                  />
                </div>
              ) : (
                <div className="text-center py-20">
                  <PlayCircle className="w-20 h-20 text-zinc-600 mx-auto mb-4" />
                  <h3 className="text-xl font-bold text-zinc-400 mb-2">
                    المعاينة الحية ستتوفر بعد مرحلة البرمجة
                  </h3>
                  <p className="text-zinc-500">
                    حالياً في المرحلة: {currentPhase?.title}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
