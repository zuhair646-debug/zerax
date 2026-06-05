import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, Loader2, Send, Paperclip, X, Check, AlertCircle, 
  Eye, Download, Code, Smartphone, Zap, PlayCircle
} from 'lucide-react';
import { toast } from 'sonner';
import ChatInput from '../components/ChatInput';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AppGameProject({ user }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const messagesEndRef = useRef(null);

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [assets, setAssets] = useState({
    characters: [],
    ui: [],
    code: [],
    builds: [],
    docs: []
  });

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
          characters: [], ui: [], code: [], builds: [], docs: []
        });
      } else {
        toast.error(data.error || 'فشل تحميل المشروع');
        navigate('/dashboard/games/app');
      }
    } catch (err) {
      toast.error('خطأ في التحميل');
      navigate('/dashboard/games/app');
    } finally {
      setLoading(false);
    }
  };

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

    const tempMsg = {
      id: Date.now(),
      role: 'user',
      content: text || '🎤 رسالة صوتية',
      attachments: files?.map(f => ({ name: f.name, type: f.type })) || [],
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempMsg]);
    setSending(true);

    try {
      const res = await fetch(`${API}/api/games/app/chat`, {
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

  const getPhaseIcon = (phaseId) => {
    const icons = {
      discovery: '🔍', architecture: '🏗️', ui_ux: '🎨',
      characters: '🎭', backend: '🔧', programming: '💻',
      testing: '🧪', store_deployment: '🚀', live_ops: '📊'
    };
    return icons[phaseId] || '📦';
  };

  const getAssetIcon = (type) => {
    const icons = {
      characters: '🎭', ui: '🎨', code: '💻', builds: '📱', docs: '📄'
    };
    return icons[type] || '📦';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-pink-400 animate-spin" />
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
            onClick={() => navigate('/dashboard/games/app')}
            className="px-4 py-2 bg-pink-500 rounded-lg hover:bg-pink-400 transition"
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
      
      {/* Header */}
      <div className="flex-none bg-zinc-900/50 backdrop-blur border-b border-white/10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4 flex-1">
            <button
              onClick={() => navigate('/dashboard/games/app')}
              className="p-2 hover:bg-white/5 rounded-lg transition"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <Smartphone className="w-5 h-5 text-pink-400" />
                <h1 className="text-xl font-bold line-clamp-1">{project.idea}</h1>
              </div>
              <div className="flex items-center gap-4 mt-1">
                <span className="text-sm text-zinc-400">
                  {currentPhase ? `${getPhaseIcon(currentPhase.id)} ${currentPhase.title}` : 'جاري التحضير'}
                </span>
                <div className="flex-1 max-w-xs h-2 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-xs text-zinc-500">{Math.round(progress)}%</span>
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-2 rounded-lg font-bold transition ${
                activeTab === 'chat'
                  ? 'bg-pink-500 text-black'
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
              onClick={() => setActiveTab('builds')}
              className={`px-4 py-2 rounded-lg font-bold transition ${
                activeTab === 'builds'
                  ? 'bg-green-500 text-black'
                  : 'bg-white/5 hover:bg-white/10'
              }`}
            >
              📱 الإصدارات
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden flex">
        
        {activeTab === 'chat' && (
          <div className="flex-1 flex flex-col">
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {messages.map((msg, idx) => (
                <div
                  key={msg.id || idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-2xl rounded-2xl px-6 py-4 ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-black'
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
                    <Loader2 className="w-5 h-5 animate-spin text-pink-400" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

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

            <div className="flex-none p-4 border-t border-white/10">
              <ChatInput
                onSend={handleSend}
                disabled={sending}
                placeholder="اكتب رسالتك... (متعدد الخطوات: GDD → UI → برمجة → نشر)"
                enableVoice={true}
                enableAttachments={true}
              />
            </div>
          </div>
        )}

        {activeTab === 'assets' && (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto space-y-8">
              {Object.entries(assets).filter(([k]) => k !== 'builds').map(([category, items]) => (
                <div key={category}>
                  <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    {getAssetIcon(category)}
                    {category === 'characters' && 'الشخصيات والنماذج 3D'}
                    {category === 'ui' && 'تصاميم الواجهة'}
                    {category === 'code' && 'الكود المصدري'}
                    {category === 'docs' && 'المستندات'}
                    <span className="text-sm text-zinc-500">({items.length})</span>
                  </h3>
                  
                  {items.length === 0 ? (
                    <div className="text-center py-8 text-zinc-500">
                      لا توجد أصول بعد
                    </div>
                  ) : (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {items.map((asset, idx) => (
                        <div
                          key={idx}
                          className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-xl p-4 hover:border-pink-400/50 transition"
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
                          <div className="flex gap-2">
                            {asset.url && (
                              <a
                                href={asset.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-1 px-3 py-2 bg-pink-500/20 hover:bg-pink-500/30 rounded-lg text-xs font-bold transition text-center"
                              >
                                عرض
                              </a>
                            )}
                            {asset.download_url && (
                              <a
                                href={asset.download_url}
                                download
                                className="flex-1 px-3 py-2 bg-green-500/20 hover:bg-green-500/30 rounded-lg text-xs font-bold transition text-center"
                              >
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

        {activeTab === 'builds' && (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl font-bold mb-6">📱 الإصدارات (Builds)</h2>
              {assets.builds?.length === 0 ? (
                <div className="text-center py-20">
                  <Smartphone className="w-20 h-20 text-zinc-600 mx-auto mb-4" />
                  <h3 className="text-xl font-bold text-zinc-400 mb-2">
                    الإصدارات ستظهر بعد مرحلة البرمجة
                  </h3>
                  <p className="text-zinc-500">
                    حالياً في المرحلة: {currentPhase?.title}
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {assets.builds.map((build, idx) => (
                    <div
                      key={idx}
                      className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-xl p-6"
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="font-bold text-lg mb-1">{build.version}</h3>
                          <p className="text-sm text-zinc-400">{build.platform}</p>
                        </div>
                        <div className={`px-3 py-1 rounded-lg text-xs font-bold ${
                          build.status === 'ready'
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-yellow-500/20 text-yellow-400'
                        }`}>
                          {build.status === 'ready' ? 'جاهز' : 'قيد التطوير'}
                        </div>
                      </div>
                      {build.changelog && (
                        <div className="text-sm text-zinc-300 mb-4">
                          {build.changelog}
                        </div>
                      )}
                      <div className="flex gap-3">
                        {build.apk_url && (
                          <a
                            href={build.apk_url}
                            download
                            className="px-4 py-2 bg-green-500 hover:bg-green-400 rounded-lg font-bold transition"
                          >
                            تحميل APK
                          </a>
                        )}
                        {build.testflight_url && (
                          <a
                            href={build.testflight_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-4 py-2 bg-blue-500 hover:bg-blue-400 rounded-lg font-bold transition"
                          >
                            TestFlight
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
