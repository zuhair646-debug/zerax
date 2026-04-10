import React, { useState, useEffect, useRef, useCallback, memo } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import { 
  Send, Plus, MessageSquare, Image, Video, Globe, 
  Loader2, Download, Trash2, Mic, ChevronLeft, ChevronRight, Sparkles,
  Volume2, VolumeX, Copy, Check, Play, X, ArrowUp,
  Code, Eye, EyeOff, Gamepad2, RefreshCw, Maximize2, Minimize2,
  Coins, Gift, Paperclip, Zap, Save, GitFork, Settings2, Bot
} from 'lucide-react';

// ============== Zitex Logo Animation ==============
const ZITEX_LOGO_URL = "https://static.prod-images.emergentagent.com/jobs/d28c1cbc-c039-46df-a176-2e32ebb0f715/images/f7f88c5a96c3a3978fb84a31dd4d6b922be1568a9083c93bf3cef363e8c17387.png";

const ZitexLogo = memo(({ isAnimating, size = 'md' }) => {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24'
  };
  
  return (
    <div className={`${sizeClasses[size]} relative flex-shrink-0`}>
      <img 
        src={ZITEX_LOGO_URL} 
        alt="Zitex" 
        className={`w-full h-full object-contain rounded-full ${isAnimating ? 'animate-spin-slow' : ''}`}
      />
      {isAnimating && (
        <div className="absolute inset-0 rounded-full bg-amber-500/20 animate-ping" />
      )}
    </div>
  );
});

// ============== Code Block with Copy ==============
const CodeBlock = memo(({ code, language = 'html', filename }) => {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    toast.success('تم نسخ الكود!');
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <div className="my-3 rounded-xl overflow-hidden bg-[#0d1117] border border-slate-700/50">
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <Code className="w-4 h-4 text-purple-400" />
          <span className="text-xs text-gray-400 font-mono">{filename || language}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all hover:bg-slate-700/50"
          style={{ color: copied ? '#10b981' : '#94a3b8' }}
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'تم!' : 'نسخ'}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm max-h-96">
        <code className="text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">{code}</code>
      </pre>
    </div>
  );
});

// ============== Message Content Parser ==============
const parseMessageContent = (content) => {
  if (!content) return [];
  const parts = [];
  const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;
  
  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: content.slice(lastIndex, match.index) });
    }
    parts.push({ type: 'code', language: match[1] || 'code', content: match[2].trim() });
    lastIndex = match.index + match[0].length;
  }
  
  if (lastIndex < content.length) {
    parts.push({ type: 'text', content: content.slice(lastIndex) });
  }
  
  return parts.length > 0 ? parts : [{ type: 'text', content }];
};

// ============== Session Skeleton ==============
const SessionSkeleton = () => (
  <div className="space-y-2 p-2">
    {[1, 2, 3].map(i => (
      <div key={i} className="flex items-center gap-2 p-3 rounded-lg bg-slate-800/30 animate-pulse">
        <div className="w-8 h-8 rounded-lg bg-slate-700/50" />
        <div className="flex-1">
          <div className="h-3 w-3/4 mb-2 bg-slate-700/50 rounded" />
          <div className="h-2 w-1/2 bg-slate-700/50 rounded" />
        </div>
      </div>
    ))}
  </div>
);

// ============== Session Item ==============
const SessionItem = memo(({ session, isActive, onSelect, onDelete, getIcon }) => (
  <div
    className={`group flex items-center gap-2 p-2.5 rounded-xl cursor-pointer transition-all duration-200 ${
      isActive 
        ? 'bg-gradient-to-r from-amber-500/20 to-yellow-500/20 border border-amber-500/30' 
        : 'hover:bg-slate-800/50 border border-transparent'
    }`}
    onClick={() => onSelect(session.id)}
    data-testid={`session-${session.id}`}
  >
    <div className={`p-1.5 rounded-lg ${
      session.session_type === 'image' ? 'bg-purple-500/20 text-purple-400' :
      session.session_type === 'video' ? 'bg-orange-500/20 text-orange-400' :
      session.session_type === 'website' ? 'bg-green-500/20 text-green-400' :
      session.session_type === 'game' ? 'bg-cyan-500/20 text-cyan-400' :
      'bg-slate-700/50 text-gray-400'
    }`}>
      {getIcon(session.session_type)}
    </div>
    <div className="flex-1 min-w-0">
      <p className="text-white text-sm truncate">{session.title}</p>
      <p className="text-[10px] text-gray-500">{session.message_count || 0} رسالة</p>
    </div>
    <Button
      size="icon"
      variant="ghost"
      onClick={(e) => { e.stopPropagation(); onDelete(session.id); }}
      className="opacity-0 group-hover:opacity-100 h-6 w-6 text-gray-500 hover:text-red-400"
    >
      <Trash2 className="w-3 h-3" />
    </Button>
  </div>
));

// ============== Chat Message ==============
const ChatMessage = memo(({ msg, idx, renderAttachment, onPlayAudio, onGenerateTTS, playingAudio, onPreview, isTyping }) => {
  const parsedContent = parseMessageContent(msg.content);
  const hasCode = parsedContent.some(p => p.type === 'code');
  const isUser = msg.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-start' : 'justify-end'} animate-fadeIn`} data-testid={`message-${idx}`}>
      {isUser ? (
        <div className="flex items-start gap-3 max-w-[85%]">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
            U
          </div>
          <div className="bg-slate-800/80 backdrop-blur border border-slate-700/50 rounded-2xl rounded-tl-md p-4 shadow-lg">
            {parsedContent.map((part, i) => (
              part.type === 'code' ? (
                <CodeBlock key={i} code={part.content} language={part.language} />
              ) : (
                <p key={i} className="text-white whitespace-pre-wrap leading-relaxed text-sm">{part.content}</p>
              )
            ))}
            <p className="text-[10px] text-gray-500 mt-2">
              {new Date(msg.created_at).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
        </div>
      ) : (
        <div className="flex items-start gap-3 max-w-[85%]">
          <div className="order-2">
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl rounded-tr-md p-4 shadow-xl">
              {parsedContent.map((part, i) => (
                part.type === 'code' ? (
                  <CodeBlock key={i} code={part.content} language={part.language} />
                ) : (
                  <p key={i} className="text-gray-200 whitespace-pre-wrap leading-relaxed text-sm">{part.content}</p>
                )
              ))}
              {msg.attachments?.map((attachment, aIdx) => (
                <div key={aIdx}>{renderAttachment(attachment, onPreview)}</div>
              ))}
              <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-700/30">
                <p className="text-[10px] text-gray-500">
                  {new Date(msg.created_at).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}
                </p>
                <div className="flex items-center gap-1">
                  {hasCode && (
                    <button
                      onClick={() => {
                        const codeContent = parsedContent.find(p => p.type === 'code')?.content;
                        if (codeContent) onPreview(codeContent);
                      }}
                      className="p-1.5 rounded-lg text-green-400 hover:bg-green-500/20 transition-all"
                      title="معاينة"
                    >
                      <Eye className="w-3.5 h-3.5" />
                    </button>
                  )}
                  <button
                    onClick={() => msg.audio_url ? onPlayAudio(msg.audio_url, msg.id) : onGenerateTTS(msg.content, msg.id)}
                    className={`p-1.5 rounded-lg transition-all ${
                      playingAudio === msg.id ? 'bg-purple-500 text-white' : 'text-gray-400 hover:bg-slate-700'
                    }`}
                  >
                    {playingAudio === msg.id ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            </div>
          </div>
          <ZitexLogo size="sm" isAnimating={isTyping} />
        </div>
      )}
    </div>
  );
});

// ============== Live Preview Panel ==============
const LivePreviewPanel = memo(({ code, isOpen, onClose, onRefresh, isFullscreen, onToggleFullscreen }) => {
  const iframeRef = useRef(null);
  
  useEffect(() => {
    if (code && iframeRef.current) {
      const iframe = iframeRef.current;
      const doc = iframe.contentDocument || iframe.contentWindow.document;
      doc.open();
      doc.write(code);
      doc.close();
    }
  }, [code]);
  
  if (!isOpen) return null;
  
  return (
    <div className={`${isFullscreen ? 'fixed inset-0 z-50' : 'h-full'} bg-slate-900 flex flex-col`}>
      <div className="flex items-center justify-between p-3 bg-slate-800/80 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-500"></span>
            <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
            <span className="w-3 h-3 rounded-full bg-green-500"></span>
          </div>
          <span className="text-sm text-gray-400 font-medium">App Preview</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={onRefresh} className="p-1.5 rounded-lg hover:bg-slate-700 text-gray-400 hover:text-white transition-all">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button onClick={onToggleFullscreen} className="p-1.5 rounded-lg hover:bg-slate-700 text-gray-400 hover:text-white transition-all">
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-700 text-gray-400 hover:text-red-400 transition-all">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="flex-1 bg-white overflow-hidden">
        {code ? (
          <iframe ref={iframeRef} className="w-full h-full border-0" title="Live Preview" sandbox="allow-scripts allow-same-origin" />
        ) : (
          <div className="h-full flex items-center justify-center bg-slate-900 text-gray-500">
            <div className="text-center">
              <Eye className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p>لا يوجد محتوى للمعاينة</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

// ============== Credits Banner ==============
const CreditsBanner = memo(({ credits, isOwner, onBuyCredits }) => {
  if (isOwner) return null;
  const percentage = Math.min(100, Math.max(0, ((credits || 0) / 1000) * 100));
  const isLow = percentage < 30;
  if (!isLow) return null;
  
  return (
    <div className="flex items-center justify-between px-4 py-2 bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 rounded-xl mb-3">
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-amber-400" />
        <span className="text-sm text-amber-200">نقاطك تنفذ؟ اشتري المزيد بخصم 44%...</span>
      </div>
      <button 
        onClick={onBuyCredits}
        className="flex items-center gap-1.5 px-3 py-1 bg-gradient-to-r from-green-500 to-emerald-500 rounded-full text-white text-xs font-medium hover:from-green-600 hover:to-emerald-600 transition-all"
      >
        <Coins className="w-3 h-3" />
        Credits {Math.round(percentage)}% more
      </button>
      <button className="text-gray-500 hover:text-white transition-colors">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
});

// ============== Main Component ==============
const AIChat = ({ user }) => {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isTyping, setIsTyping] = useState(false);
  const [playingAudio, setPlayingAudio] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [userCredits, setUserCredits] = useState(user?.credits || 0);
  const [ultraMode, setUltraMode] = useState(false);
  const [previewCode, setPreviewCode] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFullscreen, setPreviewFullscreen] = useState(false);
  const [ttsSettings, setTtsSettings] = useState({ enabled: false, provider: 'openai', voice: 'alloy', speed: 1.0 });
  
  const messagesEndRef = useRef(null);
  const audioRef = useRef(null);
  const recordingTimerRef = useRef(null);
  const audioChunksRef = useRef([]);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [inputMessage]);

  useEffect(() => { fetchSessions(); fetchUserCredits(); }, []);
  useEffect(() => { if (messages.length > 0) messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => { return () => { if (recordingTimerRef.current) clearInterval(recordingTimerRef.current); if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop(); }; }, [mediaRecorder]);

  const fetchUserCredits = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/me`, { headers: { 'Authorization': `Bearer ${token}` } });
      if (res.ok) { const data = await res.json(); setUserCredits(data.credits || 0); }
    } catch (error) { console.error('Error fetching credits:', error); }
  };

  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions`, { headers: { 'Authorization': `Bearer ${token}` } });
      if (res.ok) { const data = await res.json(); setSessions(data); }
    } catch (error) { console.error('Error fetching sessions:', error); }
    finally { setSessionsLoading(false); }
  }, []);

  const createSession = useCallback(async (type = 'general') => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ session_type: type }) });
      const session = await res.json();
      setSessions(prev => [session, ...prev]); setCurrentSession(session); setMessages([]); setPreviewCode('');
      toast.success('تم إنشاء محادثة جديدة');
      if (window.innerWidth < 768) setSidebarOpen(false);
    } catch (error) { toast.error('فشل إنشاء المحادثة'); }
  }, []);

  const loadSession = useCallback(async (sessionId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions/${sessionId}`, { headers: { 'Authorization': `Bearer ${token}` } });
      const session = await res.json();
      setCurrentSession(session); setMessages(session.messages || []); setPreviewCode('');
      if (window.innerWidth < 768) setSidebarOpen(false);
    } catch (error) { toast.error('فشل تحميل المحادثة'); }
  }, []);

  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim() || !currentSession || loading) return;
    const userMessage = inputMessage;
    setInputMessage(''); setLoading(true); setIsTyping(true);
    const tempUserMsg = { id: Date.now().toString(), role: 'user', content: userMessage, attachments: [], created_at: new Date().toISOString() };
    setMessages(prev => [...prev, tempUserMsg]);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions/${currentSession.id}/messages`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ message: userMessage, settings: { tts: ttsSettings, ultra: ultraMode } }) });
      const data = await res.json();
      if (res.ok) {
        setMessages(prev => { const filtered = prev.filter(m => m.id !== tempUserMsg.id); return [...filtered, data.user_message, data.assistant_message]; });
        if (data.credits_used) setUserCredits(prev => Math.max(0, prev - data.credits_used));
        if (ttsSettings.enabled && data.assistant_message?.audio_url) playAudio(data.assistant_message.audio_url, data.assistant_message.id);
        const assistantContent = data.assistant_message?.content || '';
        const codeMatch = assistantContent.match(/```(?:html|javascript|js)?\n?([\s\S]*?)```/);
        if (codeMatch) { setPreviewCode(codeMatch[1]); setPreviewOpen(true); }
        if (sessions.find(s => s.id === currentSession.id)?.message_count === 0) { setSessions(prev => prev.map(s => s.id === currentSession.id ? { ...s, title: userMessage.slice(0, 50), message_count: 2 } : s)); }
      } else { toast.error(data.detail || 'فشل إرسال الرسالة'); setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id)); }
    } catch (error) { toast.error('حدث خطأ في الاتصال'); setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id)); }
    finally { setLoading(false); setIsTyping(false); }
  }, [inputMessage, currentSession, loading, ttsSettings, ultraMode, sessions]);

  const deleteSession = useCallback(async (sessionId) => {
    if (!window.confirm('هل تريد حذف هذه المحادثة؟')) return;
    try {
      const token = localStorage.getItem('token');
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions/${sessionId}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSession?.id === sessionId) { setCurrentSession(null); setMessages([]); setPreviewCode(''); }
      toast.success('تم حذف المحادثة');
    } catch (error) { toast.error('فشل حذف المحادثة'); }
  }, [currentSession]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      recorder.onstop = async () => { const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' }); stream.getTracks().forEach(track => track.stop()); await transcribeAudio(audioBlob); };
      recorder.start(100); setMediaRecorder(recorder); setIsRecording(true); setRecordingTime(0);
      recordingTimerRef.current = setInterval(() => setRecordingTime(prev => prev + 1), 1000);
    } catch (error) { toast.error('فشل الوصول للمايكروفون'); }
  };

  const stopRecording = () => { if (mediaRecorder && mediaRecorder.state !== 'inactive') { mediaRecorder.stop(); setIsRecording(false); if (recordingTimerRef.current) { clearInterval(recordingTimerRef.current); recordingTimerRef.current = null; } } };

  const transcribeAudio = async (audioBlob) => {
    if (!currentSession) { toast.error('اختر محادثة أولاً'); return; }
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData(); formData.append('audio', audioBlob, 'recording.webm'); formData.append('language', 'ar');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/stt/transcribe`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` }, body: formData });
      if (res.ok) { const data = await res.json(); if (data.text?.trim()) { setInputMessage(data.text); toast.success('تم تحويل الصوت!'); } else { toast.error('لم يتم التعرف على أي كلام'); } }
    } catch (error) { toast.error('خطأ في تحويل الصوت'); }
    finally { setLoading(false); }
  };

  const toggleRecording = () => { isRecording ? stopRecording() : startRecording(); };

  const playAudio = (audioUrl, messageId) => {
    if (playingAudio === messageId) { audioRef.current?.pause(); setPlayingAudio(null); }
    else { if (audioRef.current) { audioRef.current.src = audioUrl; audioRef.current.play(); setPlayingAudio(messageId); audioRef.current.onended = () => setPlayingAudio(null); } }
  };

  const generateTTS = async (text, messageId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/tts/generate`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ text: text.replace(/```[\s\S]*?```/g, '').replace(/[*#_]/g, '').trim(), provider: ttsSettings.provider, voice: ttsSettings.voice, speed: ttsSettings.speed }) });
      if (res.ok) { const data = await res.json(); playAudio(data.audio_url, messageId); setMessages(prev => prev.map(m => m.id === messageId ? { ...m, audio_url: data.audio_url } : m)); }
    } catch (error) { toast.error('فشل توليد الصوت'); }
  };

  const downloadAsset = useCallback((url, filename) => { const link = document.createElement('a'); link.href = url; link.download = filename; document.body.appendChild(link); link.click(); document.body.removeChild(link); }, []);
  const handleKeyPress = useCallback((e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }, [sendMessage]);
  const getSessionIcon = useCallback((type) => { switch (type) { case 'image': return <Image className="w-4 h-4" />; case 'video': return <Video className="w-4 h-4" />; case 'website': return <Globe className="w-4 h-4" />; case 'game': return <Gamepad2 className="w-4 h-4" />; default: return <MessageSquare className="w-4 h-4" />; } }, []);
  const handlePreview = useCallback((code) => { setPreviewCode(code); setPreviewOpen(true); }, []);

  const renderAttachment = useCallback((attachment, onPreview) => {
    switch (attachment.type) {
      case 'image': return (<div className="mt-3 relative group rounded-xl overflow-hidden"><img src={attachment.url} alt="Generated" className="max-w-full rounded-xl" loading="lazy" /><div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"><Button size="sm" onClick={() => downloadAsset(attachment.url, 'zitex-image.png')} className="bg-white/20 backdrop-blur"><Download className="w-4 h-4 me-1" /> تحميل</Button></div></div>);
      case 'video': return (<div className="mt-3"><video src={attachment.url} controls className="max-w-full rounded-xl" preload="metadata" /><Button size="sm" onClick={() => downloadAsset(attachment.url, 'zitex-video.mp4')} className="mt-2 bg-orange-500 hover:bg-orange-600"><Download className="w-4 h-4 me-1" /> تحميل</Button></div>);
      case 'website': case 'game': return (<div className="mt-3 p-3 bg-slate-800/50 rounded-xl border border-slate-700/50"><div className="flex items-center gap-2 mb-2">{attachment.type === 'game' ? <Gamepad2 className="w-5 h-5 text-cyan-400" /> : <Globe className="w-5 h-5 text-green-400" />}<span className="text-white font-medium text-sm">{attachment.type === 'game' ? 'لعبة جاهزة!' : 'موقع جاهز!'}</span></div><div className="flex gap-2"><Button size="sm" onClick={() => onPreview(attachment.code || Object.values(attachment.files || {})[0])} className="bg-green-500 hover:bg-green-600"><Eye className="w-4 h-4 me-1" /> معاينة</Button><Button size="sm" variant="outline" onClick={() => downloadAsset(URL.createObjectURL(new Blob([attachment.code], { type: 'text/html' })), `zitex-${attachment.type}.html`)}><Download className="w-4 h-4 me-1" /> تحميل</Button></div></div>);
      case 'video_pending': return (<div className="mt-3 p-3 bg-orange-500/10 border border-orange-500/20 rounded-xl flex items-center gap-3"><Loader2 className="w-5 h-5 text-orange-400 animate-spin" /><span className="text-orange-300 text-sm">جاري توليد الفيديو...</span></div>);
      default: return null;
    }
  }, [downloadAsset]);

  return (
    <div className="h-screen bg-[#0a0a12] flex flex-col overflow-hidden" data-testid="ai-chat-page">
      <Navbar user={user} transparent />
      <audio ref={audioRef} className="hidden" />
      
      <div className="flex-1 flex mt-16 overflow-hidden">
        {!sidebarOpen && (<button onClick={() => setSidebarOpen(true)} className="md:hidden fixed top-20 right-4 z-30 p-2 bg-slate-800 rounded-lg shadow-lg border border-slate-700"><MessageSquare className="w-5 h-5 text-white" /></button>)}
        {sidebarOpen && <div className="md:hidden fixed inset-0 bg-black/60 z-10 backdrop-blur-sm" onClick={() => setSidebarOpen(false)} />}
        
        <div className={`${sidebarOpen ? 'w-64' : 'w-0'} ${sidebarOpen ? 'fixed md:relative inset-y-0 right-0 z-20 mt-16 md:mt-0' : ''} flex-shrink-0 transition-all duration-300 overflow-hidden bg-[#0d0d18] border-l border-slate-800/50 flex flex-col`}>
          <div className="p-3 border-b border-slate-800/50">
            <div className="flex items-center justify-between p-2 bg-slate-800/30 rounded-xl">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center"><span className="text-white text-xs font-bold">{user?.email?.[0]?.toUpperCase() || 'U'}</span></div>
                <div><p className="text-white text-xs font-medium truncate max-w-[100px]">{user?.role === 'owner' ? 'مالك' : 'مستخدم'}</p><p className="text-[10px] text-amber-400 flex items-center gap-1"><Coins className="w-3 h-3" />{user?.role === 'owner' ? '∞' : userCredits}</p></div>
              </div>
              <button className="p-1.5 rounded-lg hover:bg-slate-700/50 text-gray-400" title="المكافآت (قريباً)"><Gift className="w-4 h-4" /></button>
            </div>
          </div>
          
          <div className="p-3 border-b border-slate-800/50">
            <Button onClick={() => createSession('general')} className="w-full bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-700 hover:to-yellow-700 shadow-lg shadow-amber-500/20" data-testid="new-chat-btn"><Plus className="w-4 h-4 me-2" /> محادثة جديدة</Button>
            <div className="grid grid-cols-4 gap-1.5 mt-2">
              {[{ type: 'image', icon: Image, color: 'purple' }, { type: 'video', icon: Video, color: 'orange' }, { type: 'website', icon: Globe, color: 'green' }, { type: 'game', icon: Gamepad2, color: 'cyan' }].map(({ type, icon: Icon, color }) => (<button key={type} onClick={() => createSession(type)} className={`p-2 rounded-lg border border-${color}-500/30 bg-${color}-500/10 hover:bg-${color}-500/20 transition-all`}><Icon className={`w-4 h-4 text-${color}-400 mx-auto`} /></button>))}
            </div>
          </div>
          
          <ScrollArea className="flex-1 p-2">
            {sessionsLoading ? <SessionSkeleton /> : sessions.length === 0 ? (<div className="text-center py-8 text-gray-500"><Sparkles className="w-10 h-10 mx-auto mb-2 opacity-20" /><p className="text-xs">لا توجد محادثات</p></div>) : (<div className="space-y-1">{sessions.map(session => (<SessionItem key={session.id} session={session} isActive={currentSession?.id === session.id} onSelect={loadSession} onDelete={deleteSession} getIcon={getSessionIcon} />))}</div>)}
          </ScrollArea>
        </div>

        <Button size="icon" variant="ghost" onClick={() => setSidebarOpen(!sidebarOpen)} className="hidden md:flex absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-slate-800 hover:bg-slate-700 rounded-r-none">{sidebarOpen ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}</Button>

        <div className={`flex-1 flex ${previewOpen ? 'flex-row' : 'flex-col'} overflow-hidden`}>
          <div className={`${previewOpen ? 'w-1/2 border-l border-slate-800/50' : 'w-full'} flex flex-col overflow-hidden`}>
            {!currentSession ? (
              <div className="flex-1 flex items-center justify-center p-4">
                <div className="text-center max-w-lg">
                  <ZitexLogo size="xl" isAnimating={false} />
                  <h1 className="text-3xl font-bold text-white mt-6 mb-2">مرحباً في <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">Zitex</span></h1>
                  <p className="text-amber-200/80 mb-8">منصة الإبداع بالذكاء الاصطناعي</p>
                  <div className="grid grid-cols-2 gap-3 mb-6">
                    {[{ type: 'image', icon: Image, color: 'purple', title: 'صور', desc: 'GPT Image 1' }, { type: 'video', icon: Video, color: 'orange', title: 'فيديو', desc: 'Sora 2' }, { type: 'website', icon: Globe, color: 'green', title: 'مواقع', desc: 'GPT-5.2' }, { type: 'game', icon: Gamepad2, color: 'cyan', title: 'ألعاب', desc: 'Babylon.js' }].map(({ type, icon: Icon, color, title, desc }) => (<Card key={type} className={`bg-slate-800/30 border-slate-700/50 cursor-pointer hover:bg-slate-800/50 hover:border-${color}-500/30 transition-all`} onClick={() => createSession(type)}><CardContent className="p-4 text-center"><Icon className={`w-8 h-8 text-${color}-400 mx-auto mb-2`} /><h3 className="text-white font-medium text-sm">{title}</h3><p className="text-[10px] text-gray-500">{desc}</p></CardContent></Card>))}
                  </div>
                  <Button size="lg" onClick={() => createSession('general')} className="bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-700 hover:to-yellow-700 shadow-lg shadow-amber-500/20"><Zap className="w-5 h-5 me-2" /> ابدأ الآن</Button>
                </div>
              </div>
            ) : (
              <>
                <ScrollArea className="flex-1 p-4">
                  <div className="max-w-3xl mx-auto space-y-4">
                    {messages.length === 0 && (<div className="text-center py-16 text-gray-500"><Bot className="w-16 h-16 mx-auto mb-4 opacity-20" /><p>ابدأ المحادثة!</p></div>)}
                    {messages.map((msg, idx) => (<ChatMessage key={msg.id || idx} msg={msg} idx={idx} renderAttachment={renderAttachment} onPlayAudio={playAudio} onGenerateTTS={generateTTS} playingAudio={playingAudio} onPreview={handlePreview} isTyping={isTyping && idx === messages.length - 1 && msg.role === 'assistant'} />))}
                    {isTyping && (<div className="flex justify-end"><div className="flex items-start gap-3"><div className="bg-slate-800 rounded-2xl rounded-tr-md p-4 border border-slate-700/50"><div className="flex items-center gap-2">{[0, 1, 2].map(i => <span key={i} className="w-2 h-2 bg-amber-500 rounded-full animate-bounce" style={{ animationDelay: `${i * 150}ms` }} />)}<span className="text-gray-400 text-sm mr-2">جاري التفكير...</span></div></div><ZitexLogo size="sm" isAnimating={true} /></div></div>)}
                    <div ref={messagesEndRef} />
                  </div>
                </ScrollArea>

                <div className="border-t border-slate-800/50 p-3 bg-[#0d0d18]/90 backdrop-blur">
                  <div className="max-w-3xl mx-auto">
                    <CreditsBanner credits={userCredits} isOwner={user?.role === 'owner'} onBuyCredits={() => toast.info('سيتم إضافة هذه الميزة قريباً')} />
                    <div className="bg-slate-800/50 rounded-2xl border border-slate-700/50 overflow-hidden focus-within:border-purple-500/50 transition-colors">
                      {isRecording && (<div className="px-4 py-2 bg-red-500/10 border-b border-red-500/20 flex items-center gap-3"><span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span><span className="text-red-400 text-sm font-mono">{Math.floor(recordingTime / 60).toString().padStart(2, '0')}:{(recordingTime % 60).toString().padStart(2, '0')}</span><span className="text-red-300/70 text-xs">جاري التسجيل...</span></div>)}
                      <textarea ref={textareaRef} value={inputMessage} onChange={(e) => setInputMessage(e.target.value)} onKeyPress={handleKeyPress} placeholder="Message Agent" className="w-full bg-transparent text-white placeholder:text-gray-500 text-sm resize-none focus:outline-none min-h-[50px] max-h-[150px] p-4" disabled={loading} rows={1} data-testid="chat-input" />
                      <div className="flex items-center justify-between px-3 py-2 border-t border-slate-700/30">
                        <div className="flex items-center gap-1">
                          <button className="p-2 rounded-lg text-gray-500 hover:text-gray-400 hover:bg-slate-700/50 transition-all opacity-50 cursor-not-allowed" title="رفع ملفات (قريباً)" disabled><Paperclip className="w-4 h-4" /></button>
                          <button className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-gray-500 hover:text-gray-400 hover:bg-slate-700/50 transition-all text-xs opacity-50 cursor-not-allowed" title="حفظ (قريباً)" disabled><Save className="w-3.5 h-3.5" /><span className="hidden sm:inline">Save</span></button>
                          <button className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-gray-500 hover:text-gray-400 hover:bg-slate-700/50 transition-all text-xs opacity-50 cursor-not-allowed" title="نسخ (قريباً)" disabled><GitFork className="w-3.5 h-3.5" /><span className="hidden sm:inline">Fork</span></button>
                          <button onClick={() => setUltraMode(!ultraMode)} className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs transition-all ${ultraMode ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'text-gray-500 hover:text-gray-400 hover:bg-slate-700/50'}`} title="وضع Ultra"><Zap className="w-3.5 h-3.5" /><span className="hidden sm:inline">Ultra</span><div className={`w-6 h-3.5 rounded-full transition-colors ${ultraMode ? 'bg-amber-500' : 'bg-slate-600'}`}><div className={`w-2.5 h-2.5 rounded-full bg-white transition-transform mt-0.5 ${ultraMode ? 'translate-x-3' : 'translate-x-0.5'}`} /></div></button>
                        </div>
                        <div className="flex items-center gap-1">
                          <button onClick={toggleRecording} disabled={loading} className={`p-2 rounded-lg transition-all ${isRecording ? 'bg-red-500 text-white animate-pulse' : 'text-gray-400 hover:text-white hover:bg-slate-700/50'}`}><Mic className="w-5 h-5" /></button>
                          <button onClick={sendMessage} disabled={loading || !inputMessage.trim() || isRecording} className="p-2 rounded-lg bg-gradient-to-r from-amber-600 to-yellow-600 text-white disabled:opacity-50 hover:from-amber-700 hover:to-yellow-700 transition-all shadow-lg shadow-amber-500/20" data-testid="send-btn">{loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowUp className="w-5 h-5" />}</button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
          
          {previewOpen && (<div className={`${previewFullscreen ? 'fixed inset-0 z-50' : 'w-1/2'}`}><LivePreviewPanel code={previewCode} isOpen={previewOpen} onClose={() => setPreviewOpen(false)} onRefresh={() => {}} isFullscreen={previewFullscreen} onToggleFullscreen={() => setPreviewFullscreen(!previewFullscreen)} /></div>)}
        </div>
      </div>
      
      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fadeIn { animation: fadeIn 0.3s ease-out; }
        @keyframes spin-slow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .animate-spin-slow { animation: spin-slow 2s linear infinite; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
      `}</style>
    </div>
  );
};

export default AIChat;
