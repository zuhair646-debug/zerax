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
      <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/30 animate-pulse">
        <div className="w-8 h-8 bg-slate-700 rounded-lg" />
        <div className="flex-1 space-y-2">
          <div className="h-3 bg-slate-700 rounded w-3/4" />
          <div className="h-2 bg-slate-700/50 rounded w-1/2" />
        </div>
      </div>
    ))}
  </div>
);

// ============== Markdown Renderer ==============
const MarkdownRenderer = memo(({ content }) => {
  // Parse markdown content
  const renderMarkdown = (text) => {
    if (!text) return null;
    
    const lines = text.split('\n');
    const elements = [];
    let inTable = false;
    let tableRows = [];
    
    lines.forEach((line, idx) => {
      // Headers
      if (line.startsWith('## ')) {
        elements.push(<h2 key={idx} className="text-xl font-bold text-amber-400 mt-4 mb-2 flex items-center gap-2">{line.slice(3)}</h2>);
      } else if (line.startsWith('### ')) {
        elements.push(<h3 key={idx} className="text-lg font-semibold text-white mt-3 mb-1">{line.slice(4)}</h3>);
      }
      // Horizontal rule
      else if (line.trim() === '---') {
        elements.push(<hr key={idx} className="border-slate-700/50 my-3" />);
      }
      // Blockquote
      else if (line.startsWith('> ')) {
        elements.push(
          <div key={idx} className="border-r-4 border-amber-500/50 pr-4 my-2 text-amber-200/80 bg-amber-500/5 py-2 rounded-l">
            {line.slice(2)}
          </div>
        );
      }
      // Table detection
      else if (line.includes('|') && line.trim().startsWith('|')) {
        if (!inTable) {
          inTable = true;
          tableRows = [];
        }
        if (!line.includes('---')) {
          tableRows.push(line.split('|').filter(cell => cell.trim()).map(cell => cell.trim()));
        }
      }
      // End of table
      else if (inTable && !line.includes('|')) {
        inTable = false;
        if (tableRows.length > 0) {
          elements.push(
            <div key={`table-${idx}`} className="my-3 overflow-x-auto">
              <table className="w-full text-sm border border-slate-700/50 rounded-lg overflow-hidden">
                <thead>
                  <tr className="bg-slate-800/50">
                    {tableRows[0]?.map((cell, i) => (
                      <th key={i} className="px-4 py-2 text-right text-amber-400 font-medium border-b border-slate-700/50">{cell}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {tableRows.slice(1).map((row, rowIdx) => (
                    <tr key={rowIdx} className="border-b border-slate-700/30 hover:bg-slate-800/30">
                      {row.map((cell, cellIdx) => (
                        <td key={cellIdx} className="px-4 py-2 text-gray-300">{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
          tableRows = [];
        }
        // Process the current non-table line
        if (line.trim()) {
          elements.push(<p key={idx} className="text-gray-300 leading-relaxed">{line}</p>);
        }
      }
      // Bullet points
      else if (line.trim().startsWith('- ') || line.trim().startsWith('• ')) {
        elements.push(
          <div key={idx} className="flex items-start gap-2 my-1 mr-4">
            <span className="text-amber-400 mt-1">•</span>
            <span className="text-gray-300">{line.trim().slice(2)}</span>
          </div>
        );
      }
      // Bold text handling
      else if (line.trim() && !inTable) {
        let processedLine = line
          .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
          .replace(/`(.*?)`/g, '<code class="bg-slate-700/50 px-1.5 py-0.5 rounded text-amber-300 text-sm">$1</code>');
        elements.push(<p key={idx} className="text-gray-300 leading-relaxed my-1" dangerouslySetInnerHTML={{ __html: processedLine }} />);
      }
    });
    
    // Handle remaining table if any
    if (inTable && tableRows.length > 0) {
      elements.push(
        <div key="table-final" className="my-3 overflow-x-auto">
          <table className="w-full text-sm border border-slate-700/50 rounded-lg overflow-hidden">
            <thead>
              <tr className="bg-slate-800/50">
                {tableRows[0]?.map((cell, i) => (
                  <th key={i} className="px-4 py-2 text-right text-amber-400 font-medium border-b border-slate-700/50">{cell}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableRows.slice(1).map((row, rowIdx) => (
                <tr key={rowIdx} className="border-b border-slate-700/30 hover:bg-slate-800/30">
                  {row.map((cell, cellIdx) => (
                    <td key={cellIdx} className="px-4 py-2 text-gray-300">{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    
    return elements;
  };
  
  return <div className="markdown-content">{renderMarkdown(content)}</div>;
});

// ============== Session Item ==============
const SessionItem = memo(({ session, isActive, onSelect, onDelete, getIcon }) => (
  <div
    onClick={() => onSelect(session.id)}
    className={`group flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${isActive ? 'bg-gradient-to-l from-amber-600/20 to-transparent border border-amber-500/30' : 'hover:bg-slate-800/50'}`}
  >
    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isActive ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800 text-gray-400'}`}>
      {getIcon(session.session_type)}
    </div>
    <div className="flex-1 min-w-0">
      <p className={`text-sm truncate ${isActive ? 'text-amber-200' : 'text-white'}`}>{session.title || 'محادثة جديدة'}</p>
      <p className="text-[10px] text-gray-500">{session.message_count || 0} رسالة</p>
    </div>
    <button onClick={(e) => { e.stopPropagation(); onDelete(session.id); }} className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/20 text-red-400 transition-all">
      <Trash2 className="w-3.5 h-3.5" />
    </button>
  </div>
));

// ============== Live Preview Panel ==============
const LivePreviewPanel = memo(({ code, isOpen, onClose, onRefresh, isFullscreen, onToggleFullscreen }) => {
  const iframeRef = useRef(null);
  
  useEffect(() => {
    if (iframeRef.current && code) {
      const doc = iframeRef.current.contentDocument;
      doc.open();
      doc.write(code);
      doc.close();
    }
  }, [code]);
  
  if (!isOpen) return null;
  
  return (
    <div className={`${isFullscreen ? 'fixed inset-0 z-50' : 'h-full'} bg-[#0d0d18] flex flex-col`}>
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900/80 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-green-400" />
          <span className="text-sm text-white font-medium">المعاينة المباشرة</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={onRefresh} className="p-1.5 rounded hover:bg-slate-700/50 text-gray-400">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button onClick={onToggleFullscreen} className="p-1.5 rounded hover:bg-slate-700/50 text-gray-400">
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-slate-700/50 text-gray-400">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="flex-1 bg-white">
        <iframe ref={iframeRef} title="preview" className="w-full h-full border-0" sandbox="allow-scripts allow-same-origin" />
      </div>
    </div>
  );
});

// ============== Chat Message ==============
const ChatMessage = memo(({ msg, idx, renderAttachment, onPlayAudio, onGenerateTTS, playingAudio, onPreview, isTyping }) => {
  const isUser = msg.role === 'user';
  const parts = parseMessageContent(msg.content);
  
  return (
    <div className={`flex ${isUser ? 'justify-start' : 'justify-end'} animate-fadeIn`}>
      <div className={`flex items-start gap-3 max-w-[85%] ${isUser ? 'flex-row' : 'flex-row-reverse'}`}>
        {isUser ? (
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center flex-shrink-0">
            <span className="text-white text-xs font-bold">أنت</span>
          </div>
        ) : (
          <ZitexLogo size="sm" isAnimating={isTyping} />
        )}
        <div className={`rounded-2xl ${isUser ? 'rounded-tl-md bg-gradient-to-br from-blue-600 to-blue-700' : 'rounded-tr-md bg-slate-800 border border-slate-700/50'} p-4`}>
          {parts.map((part, i) => (
            part.type === 'code' ? (
              <CodeBlock key={i} code={part.content} language={part.language} />
            ) : (
              <MarkdownRenderer key={i} content={part.content} />
            )
          ))}
          {msg.attachments?.map((att, i) => <div key={i}>{renderAttachment(att)}</div>)}
          {!isUser && (
            <div className="flex items-center gap-2 mt-3 pt-2 border-t border-slate-700/30">
              <button onClick={() => parts.some(p => p.type === 'code') && onPreview(parts.find(p => p.type === 'code').content)} className="p-1.5 rounded hover:bg-slate-700/50 text-gray-400 hover:text-white" title="معاينة">
                <Eye className="w-4 h-4" />
              </button>
              <button onClick={() => navigator.clipboard.writeText(msg.content).then(() => toast.success('تم النسخ!'))} className="p-1.5 rounded hover:bg-slate-700/50 text-gray-400 hover:text-white" title="نسخ">
                <Copy className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

// ============== Credits Banner ==============
const CreditsBanner = memo(({ credits, isOwner, onBuyCredits }) => {
  if (isOwner) return null;
  const percentage = Math.min(100, (credits / 100) * 100);
  if (percentage > 30) return null;
  
  return (
    <div className="flex items-center justify-between p-3 mb-3 bg-gradient-to-r from-amber-900/30 to-orange-900/30 rounded-xl border border-amber-500/20">
      <div className="flex items-center gap-2">
        <Coins className="w-5 h-5 text-amber-400" />
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
  // State
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false); // مخفي بشكل افتراضي
  const [isTyping, setIsTyping] = useState(false);
  const [playingAudio, setPlayingAudio] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [userCredits, setUserCredits] = useState(user?.credits || 0);
  const [ultraMode, setUltraMode] = useState(false);
  
  // Preview State
  const [previewCode, setPreviewCode] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFullscreen, setPreviewFullscreen] = useState(false);
  
  // TTS Settings
  const [ttsSettings, setTtsSettings] = useState({
    enabled: false,
    provider: 'openai',
    voice: 'alloy',
    speed: 1.0
  });
  
  // Refs
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const audioRef = useRef(null);
  const recordingTimerRef = useRef(null);
  const audioChunksRef = useRef([]);
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [inputMessage]);

  useEffect(() => {
    fetchSessions();
    fetchUserCredits();
  }, []);

  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
    };
  }, [mediaRecorder]);

  const fetchUserCredits = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUserCredits(data.credits || 0);
      }
    } catch (error) {
      console.error('Error fetching credits:', error);
    }
  };

  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const createSession = useCallback(async (type = 'general') => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_type: type })
      });
      const session = await res.json();
      setSessions(prev => [session, ...prev]);
      setCurrentSession(session);
      setMessages(session.messages || []);
      setPreviewCode('');
      toast.success('تم إنشاء محادثة جديدة');
      setSidebarOpen(false);
    } catch (error) {
      toast.error('فشل إنشاء المحادثة');
    }
  }, []);

  const loadSession = useCallback(async (sessionId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions/${sessionId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const session = await res.json();
      setCurrentSession(session);
      setMessages(session.messages || []);
      setPreviewCode('');
      setSidebarOpen(false);
    } catch (error) {
      toast.error('فشل تحميل المحادثة');
    }
  }, []);

  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim() || !currentSession || loading) return;

    const userMessage = inputMessage;
    setInputMessage('');
    setLoading(true);
    setIsTyping(true);

    const tempUserMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: userMessage,
      attachments: [],
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions/${currentSession.id}/messages`,
        {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMessage, settings: { tts: ttsSettings, ultra: ultraMode } })
        }
      );

      const data = await res.json();

      if (res.ok) {
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== tempUserMsg.id);
          return [...filtered, data.user_message, data.assistant_message];
        });
        
        if (data.credits_used) setUserCredits(prev => Math.max(0, prev - data.credits_used));
        if (ttsSettings.enabled && data.assistant_message?.audio_url) {
          playAudio(data.assistant_message.audio_url, data.assistant_message.id);
        }

        const assistantContent = data.assistant_message?.content || '';
        const codeMatch = assistantContent.match(/```(?:html|javascript|js)?\n?([\s\S]*?)```/);
        if (codeMatch) {
          setPreviewCode(codeMatch[1]);
          setPreviewOpen(true);
        }

        if (sessions.find(s => s.id === currentSession.id)?.message_count === 0) {
          setSessions(prev => prev.map(s => 
            s.id === currentSession.id ? { ...s, title: userMessage.slice(0, 50), message_count: 2 } : s
          ));
        }
      } else {
        toast.error(data.detail || 'فشل إرسال الرسالة');
        setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
      }
    } catch (error) {
      toast.error('خطأ في الاتصال');
      setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
    } finally {
      setLoading(false);
      setIsTyping(false);
    }
  }, [inputMessage, currentSession, loading, ttsSettings, ultraMode, sessions]);

  const deleteSession = useCallback(async (sessionId) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
        setMessages([]);
      }
      toast.success('تم حذف المحادثة');
    } catch (error) {
      toast.error('فشل حذف المحادثة');
    }
  }, [currentSession]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const playAudio = useCallback((audioUrl, messageId) => {
    if (audioRef.current) {
      if (playingAudio === messageId) {
        audioRef.current.pause();
        setPlayingAudio(null);
      } else {
        audioRef.current.src = audioUrl;
        audioRef.current.play();
        setPlayingAudio(messageId);
        audioRef.current.onended = () => setPlayingAudio(null);
      }
    }
  }, [playingAudio]);

  const generateTTS = useCallback(async (text, messageId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/tts`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, ...ttsSettings })
      });
      const data = await res.json();
      if (data.audio_url) playAudio(data.audio_url, messageId);
    } catch (error) {
      toast.error('فشل توليد الصوت');
    }
  }, [ttsSettings, playAudio]);

  const toggleRecording = useCallback(async () => {
    if (isRecording) {
      mediaRecorder?.stop();
      setIsRecording(false);
      clearInterval(recordingTimerRef.current);
      setRecordingTime(0);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream);
        audioChunksRef.current = [];
        
        recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
        recorder.onstop = async () => {
          stream.getTracks().forEach(t => t.stop());
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          // TODO: Send to backend for transcription
          toast.info('تم تسجيل الصوت - ميزة التحويل قادمة قريباً');
        };
        
        recorder.start();
        setMediaRecorder(recorder);
        setIsRecording(true);
        recordingTimerRef.current = setInterval(() => setRecordingTime(t => t + 1), 1000);
      } catch (error) {
        toast.error('فشل الوصول للميكروفون');
      }
    }
  }, [isRecording, mediaRecorder]);

  const handlePreview = useCallback((code) => {
    setPreviewCode(code);
    setPreviewOpen(true);
  }, []);

  const getSessionIcon = useCallback((type) => {
    const icons = {
      image: <Image className="w-4 h-4" />,
      video: <Video className="w-4 h-4" />,
      website: <Globe className="w-4 h-4" />,
      game: <Gamepad2 className="w-4 h-4" />,
      general: <MessageSquare className="w-4 h-4" />
    };
    return icons[type] || icons.general;
  }, []);

  const downloadAsset = useCallback((url, filename) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, []);

  const renderAttachment = useCallback((attachment) => {
    switch (attachment.type) {
      case 'image':
        return (
          <div className="mt-3 rounded-xl overflow-hidden border border-slate-700/50">
            <img src={attachment.url} alt="Generated" className="w-full max-h-80 object-contain bg-slate-900" />
            <div className="p-2 bg-slate-800/50 flex justify-end gap-2">
              <Button size="sm" variant="outline" onClick={() => window.open(attachment.url, '_blank')}>
                <Eye className="w-4 h-4 me-1" /> عرض
              </Button>
              <Button size="sm" variant="outline" onClick={() => downloadAsset(attachment.url, `zitex-image-${Date.now()}.png`)}>
                <Download className="w-4 h-4 me-1" /> تحميل
              </Button>
            </div>
          </div>
        );
      case 'video':
        return (
          <div className="mt-3 rounded-xl overflow-hidden border border-slate-700/50">
            <video src={attachment.url} controls className="w-full max-h-80 bg-slate-900" />
            <div className="p-2 bg-slate-800/50 flex justify-end gap-2">
              <Button size="sm" variant="outline" onClick={() => downloadAsset(attachment.url, `zitex-video-${Date.now()}.mp4`)}>
                <Download className="w-4 h-4 me-1" /> تحميل
              </Button>
            </div>
          </div>
        );
      case 'code':
        return (
          <div className="mt-3">
            <CodeBlock code={attachment.code} language={attachment.language || 'html'} />
            <div className="flex gap-2 mt-2">
              <Button size="sm" variant="outline" onClick={() => handlePreview(attachment.code)}>
                <Eye className="w-4 h-4 me-1" /> معاينة
              </Button>
              <Button size="sm" variant="outline" onClick={() => downloadAsset(URL.createObjectURL(new Blob([attachment.code], { type: 'text/html' })), `zitex-${attachment.type}.html`)}>
                <Download className="w-4 h-4 me-1" /> تحميل
              </Button>
            </div>
          </div>
        );
      case 'video_pending':
        return (
          <div className="mt-3 p-3 bg-orange-500/10 border border-orange-500/20 rounded-xl flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-orange-400 animate-spin" />
            <span className="text-orange-300 text-sm">جاري توليد الفيديو...</span>
          </div>
        );
      default:
        return null;
    }
  }, [downloadAsset, handlePreview]);

  return (
    <div className="h-screen bg-[#0a0a12] flex flex-col overflow-hidden" data-testid="ai-chat-page">
      <Navbar user={user} transparent />
      <audio ref={audioRef} className="hidden" />
      
      <div className="flex-1 flex mt-16 overflow-hidden">
        {/* Sessions Dropdown Button - Always visible */}
        <div className="fixed top-20 right-4 z-30">
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)} 
            className={`flex items-center gap-2 px-4 py-2 rounded-xl shadow-lg border transition-all ${sidebarOpen ? 'bg-amber-600 border-amber-500 text-white' : 'bg-slate-800 border-slate-700 text-white hover:bg-slate-700'}`}
          >
            <MessageSquare className="w-4 h-4" />
            <span className="text-sm font-medium">المحادثات</span>
            <span className="bg-amber-500/20 text-amber-300 text-xs px-2 py-0.5 rounded-full">{sessions.length}</span>
          </button>
          
          {/* Dropdown Panel */}
          {sidebarOpen && (
            <div className="absolute top-12 right-0 w-80 bg-[#0d0d18] border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden animate-fadeIn">
              {/* User Credits Header */}
              <div className="p-3 border-b border-slate-800/50 bg-gradient-to-r from-slate-800/50 to-slate-900/50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center">
                      <span className="text-black text-sm font-bold">{user?.email?.[0]?.toUpperCase() || 'U'}</span>
                    </div>
                    <div>
                      <p className="text-white text-sm font-medium">{user?.role === 'owner' ? 'مالك' : 'مستخدم'}</p>
                      <p className="text-xs text-amber-400 flex items-center gap-1">
                        <Coins className="w-3 h-3" />
                        <span className="font-bold">{user?.role === 'owner' ? '∞' : userCredits}</span> نقطة
                      </p>
                    </div>
                  </div>
                  <button onClick={() => setSidebarOpen(false)} className="p-2 rounded-lg hover:bg-slate-700/50 text-gray-400">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              {/* New Chat Button */}
              <div className="p-3 border-b border-slate-800/50">
                <Button onClick={() => { createSession('general'); setSidebarOpen(false); }} className="w-full bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-700 hover:to-yellow-700 shadow-lg shadow-amber-500/20" data-testid="new-chat-btn">
                  <Plus className="w-4 h-4 me-2" /> محادثة جديدة
                </Button>
                <div className="grid grid-cols-4 gap-1.5 mt-2">
                  {[
                    { type: 'image', icon: Image, color: 'purple', label: 'صورة' },
                    { type: 'video', icon: Video, color: 'orange', label: 'فيديو' },
                    { type: 'website', icon: Globe, color: 'green', label: 'موقع' },
                    { type: 'game', icon: Gamepad2, color: 'cyan', label: 'لعبة' }
                  ].map(({ type, icon: Icon, color, label }) => (
                    <button 
                      key={type} 
                      onClick={() => { createSession(type); setSidebarOpen(false); }} 
                      className={`p-2 rounded-lg border border-${color}-500/30 bg-${color}-500/10 hover:bg-${color}-500/20 transition-all flex flex-col items-center gap-1`}
                      title={label}
                    >
                      <Icon className={`w-4 h-4 text-${color}-400`} />
                      <span className={`text-[10px] text-${color}-400`}>{label}</span>
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Sessions List */}
              <div className="max-h-80 overflow-y-auto">
                {sessionsLoading ? <SessionSkeleton /> : sessions.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Sparkles className="w-10 h-10 mx-auto mb-2 opacity-20" />
                    <p className="text-sm">لا توجد محادثات سابقة</p>
                    <p className="text-xs text-gray-600">ابدأ محادثة جديدة!</p>
                  </div>
                ) : (
                  <div className="p-2 space-y-1">
                    <p className="text-xs text-gray-500 px-2 py-1">المحادثات السابقة ({sessions.length})</p>
                    {sessions.map(session => (
                      <div key={session.id} onClick={() => { loadSession(session.id); setSidebarOpen(false); }}>
                        <SessionItem session={session} isActive={currentSession?.id === session.id} onSelect={() => {}} onDelete={deleteSession} getIcon={getSessionIcon} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        
        {/* Overlay when dropdown is open */}
        {sidebarOpen && <div className="fixed inset-0 z-20" onClick={() => setSidebarOpen(false)} />}

        {/* Main Area - Full Width */}
        <div className={`flex-1 flex ${previewOpen ? 'flex-row' : 'flex-col'} overflow-hidden w-full`}>
          {/* Chat Column */}
          <div className={`${previewOpen ? 'w-1/2 border-l border-slate-800/50' : 'w-full'} flex flex-col overflow-hidden`}>
            {!currentSession ? (
              /* Welcome Screen */
              <div className="flex-1 flex items-center justify-center p-4">
                <div className="text-center max-w-lg">
                  <ZitexLogo size="xl" isAnimating={false} />
                  <h1 className="text-3xl font-bold text-white mt-6 mb-2">
                    مرحباً في <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">Zitex</span>
                  </h1>
                  <p className="text-amber-200/80 mb-8">منصة الإبداع بالذكاء الاصطناعي</p>
                  <div className="grid grid-cols-2 gap-3 mb-6">
                    {[
                      { type: 'image', icon: Image, color: 'purple', title: 'صور', desc: 'GPT Image 1' },
                      { type: 'video', icon: Video, color: 'orange', title: 'فيديو', desc: 'Sora 2' },
                      { type: 'website', icon: Globe, color: 'green', title: 'مواقع', desc: 'GPT-5.2' },
                      { type: 'game', icon: Gamepad2, color: 'cyan', title: 'ألعاب', desc: 'Babylon.js' }
                    ].map(({ type, icon: Icon, color, title, desc }) => (
                      <Card key={type} className={`bg-slate-800/30 border-slate-700/50 cursor-pointer hover:bg-slate-800/50 hover:border-${color}-500/30 transition-all`} onClick={() => createSession(type)}>
                        <CardContent className="p-4 text-center">
                          <Icon className={`w-8 h-8 text-${color}-400 mx-auto mb-2`} />
                          <h3 className="text-white font-medium text-sm">{title}</h3>
                          <p className="text-[10px] text-gray-500">{desc}</p>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                  <Button size="lg" onClick={() => createSession('general')} className="bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-700 hover:to-yellow-700 shadow-lg shadow-amber-500/20">
                    <Zap className="w-5 h-5 me-2" /> ابدأ الآن
                  </Button>
                </div>
              </div>
            ) : (
              <>
                {/* Messages */}
                <ScrollArea className="flex-1 p-4">
                  <div className="max-w-3xl mx-auto space-y-4">
                    {messages.length === 0 && (
                      <div className="text-center py-16 text-gray-500">
                        <Bot className="w-16 h-16 mx-auto mb-4 opacity-20" />
                        <p>ابدأ المحادثة!</p>
                      </div>
                    )}
                    {messages.map((msg, idx) => (
                      <ChatMessage key={msg.id || idx} msg={msg} idx={idx} renderAttachment={renderAttachment} onPlayAudio={playAudio} onGenerateTTS={generateTTS} playingAudio={playingAudio} onPreview={handlePreview} isTyping={isTyping && idx === messages.length - 1 && msg.role === 'assistant'} />
                    ))}
                    {isTyping && (
                      <div className="flex justify-end">
                        <div className="flex items-start gap-3">
                          <div className="bg-slate-800 rounded-2xl rounded-tr-md p-4 border border-slate-700/50">
                            <div className="flex items-center gap-2">
                              {[0, 1, 2].map(i => <span key={i} className="w-2 h-2 bg-amber-500 rounded-full animate-bounce" style={{ animationDelay: `${i * 150}ms` }} />)}
                              <span className="text-gray-400 text-sm mr-2">جاري التفكير...</span>
                            </div>
                          </div>
                          <ZitexLogo size="sm" isAnimating={true} />
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                </ScrollArea>

                {/* Input Area */}
                <div className="border-t border-slate-800/50 p-3 bg-[#0d0d18]/90 backdrop-blur">
                  <div className="max-w-3xl mx-auto">
                    {/* Credits Banner */}
                    <CreditsBanner credits={userCredits} isOwner={user?.role === 'owner'} onBuyCredits={() => toast.info('سيتم إضافة هذه الميزة قريباً')} />
                    
                    {/* Input Box */}
                    <div className="bg-slate-800/50 rounded-2xl border border-slate-700/50 overflow-hidden focus-within:border-purple-500/50 transition-colors">
                      {/* Recording Indicator */}
                      {isRecording && (
                        <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/20 flex items-center gap-3">
                          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                          <span className="text-red-400 text-sm font-mono">
                            {Math.floor(recordingTime / 60).toString().padStart(2, '0')}:{(recordingTime % 60).toString().padStart(2, '0')}
                          </span>
                          <span className="text-red-300/70 text-xs">جاري التسجيل...</span>
                        </div>
                      )}
                      
                      {/* Text Area */}
                      <textarea
                        ref={textareaRef}
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Message Agent"
                        className="w-full bg-transparent text-white placeholder:text-gray-500 text-sm resize-none focus:outline-none min-h-[50px] max-h-[150px] p-4"
                        disabled={loading}
                        rows={1}
                        data-testid="chat-input"
                      />
                      
                      {/* Bottom Tools */}
                      <div className="flex items-center justify-between px-3 py-2 border-t border-slate-700/30">
                        <div className="flex items-center gap-1">
                          {/* Attach File (Disabled) */}
                          <button className="p-2 rounded-lg text-gray-500 hover:text-gray-400 hover:bg-slate-700/50 transition-all opacity-50 cursor-not-allowed" title="رفع ملفات (قريباً)" disabled>
                            <Paperclip className="w-4 h-4" />
                          </button>
                          
                          {/* Save (Disabled) */}
                          <button className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-gray-500 hover:text-gray-400 hover:bg-slate-700/50 transition-all text-xs opacity-50 cursor-not-allowed" title="حفظ (قريباً)" disabled>
                            <Save className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">Save</span>
                          </button>
                          
                          {/* Fork (Disabled) */}
                          <button className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-gray-500 hover:text-gray-400 hover:bg-slate-700/50 transition-all text-xs opacity-50 cursor-not-allowed" title="نسخ (قريباً)" disabled>
                            <GitFork className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">Fork</span>
                          </button>
                          
                          {/* Ultra Mode */}
                          <button 
                            onClick={() => setUltraMode(!ultraMode)}
                            className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs transition-all ${ultraMode ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'text-gray-500 hover:text-gray-400 hover:bg-slate-700/50'}`}
                            title="وضع Ultra"
                          >
                            <Zap className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">Ultra</span>
                            <div className={`w-6 h-3.5 rounded-full transition-colors ${ultraMode ? 'bg-amber-500' : 'bg-slate-600'}`}>
                              <div className={`w-2.5 h-2.5 rounded-full bg-white transition-transform mt-0.5 ${ultraMode ? 'translate-x-3' : 'translate-x-0.5'}`} />
                            </div>
                          </button>
                        </div>
                        
                        <div className="flex items-center gap-1">
                          {/* Mic */}
                          <button
                            onClick={toggleRecording}
                            disabled={loading}
                            className={`p-2 rounded-lg transition-all ${isRecording ? 'bg-red-500 text-white animate-pulse' : 'text-gray-400 hover:text-white hover:bg-slate-700/50'}`}
                          >
                            <Mic className="w-5 h-5" />
                          </button>
                          
                          {/* Send */}
                          <button
                            onClick={sendMessage}
                            disabled={loading || !inputMessage.trim() || isRecording}
                            className="p-2 rounded-lg bg-gradient-to-r from-amber-600 to-yellow-600 text-white disabled:opacity-50 hover:from-amber-700 hover:to-yellow-700 transition-all shadow-lg shadow-amber-500/20"
                            data-testid="send-btn"
                          >
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowUp className="w-5 h-5" />}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
          
          {/* Preview Panel */}
          {previewOpen && (
            <div className={`${previewFullscreen ? 'fixed inset-0 z-50' : 'w-1/2'}`}>
              <LivePreviewPanel code={previewCode} isOpen={previewOpen} onClose={() => setPreviewOpen(false)} onRefresh={() => {}} isFullscreen={previewFullscreen} onToggleFullscreen={() => setPreviewFullscreen(!previewFullscreen)} />
            </div>
          )}
        </div>
      </div>
      
      {/* Styles */}
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
