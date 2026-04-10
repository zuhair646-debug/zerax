import React, { useState, useEffect, useRef, useCallback, memo } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import { 
  Send, Plus, MessageSquare, Image, Video, Globe, 
  Loader2, Download, Trash2, Mic, ChevronLeft, ChevronRight, Sparkles,
  Volume2, VolumeX, Settings, CheckCircle
} from 'lucide-react';

const SkeletonPulse = ({ className }) => (
  <div className={`animate-pulse bg-slate-700 rounded ${className}`} />
);

const SessionSkeleton = () => (
  <div className="space-y-2 p-2">
    {[1, 2, 3].map(i => (
      <div key={i} className="flex items-center gap-2 p-3 rounded-lg bg-slate-700/30">
        <SkeletonPulse className="w-10 h-10 rounded-lg" />
        <div className="flex-1">
          <SkeletonPulse className="h-4 w-3/4 mb-2" />
          <SkeletonPulse className="h-3 w-1/2" />
        </div>
      </div>
    ))}
  </div>
);

// شريط التقدم المحلي
const LocalProgressIndicator = ({ progress }) => {
  if (!progress) return null;

  const { step, status, message, percent } = progress;

  const getStepColor = () => {
    switch (status) {
      case 'analyzing': return 'border-blue-500 bg-blue-500/20';
      case 'processing': return 'border-purple-500 bg-purple-500/20';
      case 'generating': return 'border-orange-500 bg-orange-500/20';
      case 'complete': return 'border-green-500 bg-green-500/20';
      default: return 'border-gray-500 bg-gray-500/20';
    }
  };

  return (
    <div className="flex justify-end px-2 md:px-0 animate-fadeIn">
      <div className={`max-w-[85%] md:max-w-[70%] rounded-2xl p-4 border ${getStepColor()}`}>
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 rounded-full bg-white/10">
            {status === 'complete' ? (
              <CheckCircle className="w-5 h-5 text-green-400" />
            ) : (
              <Loader2 className="w-5 h-5 animate-spin text-white" />
            )}
          </div>
          <span className="font-medium text-white">{message}</span>
        </div>

        <div className="h-2 bg-slate-700 rounded-full overflow-hidden mb-3">
          <div 
            className={`h-full rounded-full transition-all duration-500 ${
              status === 'complete' ? 'bg-green-500' : 'bg-gradient-to-r from-purple-500 to-pink-500'
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>

        <div className="flex justify-between text-xs">
          {[
            { num: 1, label: 'تحليل', icon: '🔍' },
            { num: 2, label: 'معالجة', icon: '⚡' },
            { num: 3, label: 'توليد', icon: '🎨' },
            { num: 4, label: 'مكتمل', icon: '✅' }
          ].map((s) => (
            <span 
              key={s.num}
              className={step >= s.num ? 'text-white' : 'text-gray-500'}
            >
              {s.icon} {s.label}
            </span>
          ))}
        </div>

        <div className="text-center mt-2">
          <span className="text-2xl font-bold text-white">{percent}%</span>
        </div>
      </div>
    </div>
  );
};

const SessionItem = memo(({ session, isActive, onSelect, onDelete, getIcon }) => (
  <div
    className={`group flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-all duration-200 ${
      isActive ? 'bg-slate-700 shadow-lg' : 'hover:bg-slate-700/50'
    }`}
    onClick={() => onSelect(session.id)}
  >
    <div className={`p-2 rounded-lg transition-colors ${
      session.session_type === 'image' ? 'bg-purple-500/20 text-purple-400' :
      session.session_type === 'video' ? 'bg-orange-500/20 text-orange-400' :
      session.session_type === 'website' ? 'bg-green-500/20 text-green-400' :
      'bg-slate-600 text-gray-400'
    }`}>
      {getIcon(session.session_type)}
    </div>
    <div className="flex-1 min-w-0">
      <p className="text-white text-sm truncate">{session.title}</p>
      <p className="text-xs text-gray-500">{session.message_count || 0} رسالة</p>
    </div>
    <Button
      size="icon"
      variant="ghost"
      onClick={(e) => { e.stopPropagation(); onDelete(session.id); }}
      className="opacity-0 group-hover:opacity-100 h-8 w-8 text-gray-400 hover:text-red-400"
    >
      <Trash2 className="w-4 h-4" />
    </Button>
  </div>
));

const ChatMessage = memo(({ msg, idx, renderAttachment, onPlayAudio, onGenerateTTS, playingAudio }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const maxLength = 300;
  const shouldTruncate = msg.content && msg.content.length > maxLength;
  const displayContent = shouldTruncate && !isExpanded 
    ? msg.content.slice(0, maxLength) + '...' 
    : msg.content;

  return (
    <div className={`flex ${msg.role === 'user' ? 'justify-start' : 'justify-end'} animate-fadeIn px-2 md:px-0`}>
 <div className={`max-w-[85%] sm:max-w-[90%] md:max-w-[80%] ${
        msg.role === 'user' 
          ? 'bg-blue-600 rounded-2xl rounded-tr-md' 
          : 'bg-slate-700 rounded-2xl rounded-tl-md'
      } p-3 md:p-4 shadow-lg`}>
        <p className="text-white whitespace-pre-wrap leading-relaxed text-sm md:text-base">
          {displayContent}
        </p>
        {shouldTruncate && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-purple-400 hover:text-purple-300 text-xs md:text-sm mt-2 font-medium"
          >
            {isExpanded ? 'عرض أقل' : 'عرض المزيد'}
          </button>
        )}
        {msg.attachments?.map((attachment, aIdx) => (
          <div key={aIdx}>{renderAttachment(attachment)}</div>
        ))}
        <div className="flex items-center justify-between mt-2 gap-2">
          <p className="text-xs text-gray-400 opacity-70">
            {new Date(msg.created_at).toLocaleTimeString('ar-SA')}
          </p>
          {msg.role === 'assistant' && (
            <button
              onClick={() => msg.audio_url ? onPlayAudio(msg.audio_url, msg.id) : onGenerateTTS(msg.content, msg.id)}
              className={`p-1.5 rounded-full transition-all ${
                playingAudio === msg.id 
                  ? 'bg-purple-500 text-white' 
                  : 'bg-slate-600 hover:bg-slate-500 text-gray-300'
              }`}
            >
              {playingAudio === msg.id ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>
    </div>
  );
});

const AIChat = ({ user }) => {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [pendingVideoRequests, setPendingVideoRequests] = useState([]);
  const [showTTSSettings, setShowTTSSettings] = useState(false);
  const [availableVoices, setAvailableVoices] = useState([]);
  const [playingAudio, setPlayingAudio] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [localProgress, setLocalProgress] = useState(null);
  const [generationSettings, setGenerationSettings] = useState({
    duration: 4,
    size: '1280x720',
    voice_id: '21m00Tcm4TlvDq8ikWAM'
  });
  const [ttsSettings, setTtsSettings] = useState({
    enabled: false,
    provider: 'openai',
    voice: 'alloy',
    speed: 1.0
  });
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const audioRef = useRef(null);
  const pollingIntervalRef = useRef(null);
  const recordingTimerRef = useRef(null);
  const audioChunksRef = useRef([]);
  const progressIntervalRef = useRef(null);

  // دالة التقدم المحلي
  const startLocalProgress = useCallback(() => {
    let currentStep = 1;
    let currentPercent = 0;
    
    const steps = [
      { step: 1, status: 'analyzing', message: 'جاري تحليل طلبك...', targetPercent: 25 },
      { step: 2, status: 'processing', message: 'جاري المعالجة...', targetPercent: 50 },
      { step: 3, status: 'generating', message: 'جاري التوليد...', targetPercent: 75 },
    ];
    
    setLocalProgress({
      step: 1,
      status: 'analyzing',
      message: 'جاري تحليل طلبك...',
      percent: 0
    });
    
    progressIntervalRef.current = setInterval(() => {
      currentPercent += 2;
      
      if (currentPercent >= 25 && currentStep === 1) {
        currentStep = 2;
        setLocalProgress({
          step: 2,
          status: 'processing',
          message: 'جاري المعالجة...',
          percent: currentPercent
        });
      } else if (currentPercent >= 50 && currentStep === 2) {
        currentStep = 3;
        setLocalProgress({
          step: 3,
          status: 'generating',
          message: 'جاري التوليد...',
          percent: currentPercent
        });
      } else if (currentPercent >= 75) {
        // ابقى عند 75-85% حتى يصل الرد
        if (currentPercent > 85) currentPercent = 85;
        setLocalProgress(prev => ({
          ...prev,
          percent: currentPercent
        }));
      } else {
        setLocalProgress(prev => ({
          ...prev,
          percent: currentPercent
        }));
      }
    }, 150);
  }, []);

  const stopLocalProgress = useCallback((success = true) => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    
    if (success) {
      setLocalProgress({
        step: 4,
        status: 'complete',
        message: 'تم بنجاح!',
        percent: 100
      });
      
      setTimeout(() => {
        setLocalProgress(null);
      }, 800);
    } else {
      setLocalProgress(null);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
    fetchVoices();
  }, []);

  const fetchVoices = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/voices`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAvailableVoices(data.voices || []);
      }
    } catch (error) {
      console.error('Error fetching voices:', error);
    }
  };

  const playAudio = (audioUrl, messageId) => {
    if (playingAudio === messageId) {
      audioRef.current?.pause();
      setPlayingAudio(null);
    } else {
      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        audioRef.current.play();
        setPlayingAudio(messageId);
        audioRef.current.onended = () => setPlayingAudio(null);
      }
    }
  };

  const generateTTS = async (text, messageId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/tts/generate`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: text.replace(/[✅🎬⏱️📩💡🖼️🌐📁]/g, '').replace(/\[.*?\]/g, '').trim(),
          provider: ttsSettings.provider,
          voice: ttsSettings.voice,
          speed: ttsSettings.speed
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        playAudio(data.audio_url, messageId);
        setMessages(prev => prev.map(m => 
          m.id === messageId ? { ...m, audio_url: data.audio_url } : m
        ));
      }
    } catch (error) {
      toast.error('فشل توليد الصوت');
    }
  };

const startRecording = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        toast.error('المتصفح لا يدعم تسجيل الصوت');
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });

      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/mp4';
          if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = '';
          }
        }
      }

      const recorderOptions = mimeType ? { mimeType } : {};
      const recorder = new MediaRecorder(stream, recorderOptions);
      audioChunksRef.current = [];
      
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      
      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        if (audioChunksRef.current.length === 0) {
          toast.error('لم يتم تسجيل أي صوت');
          return;
        }
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType || 'audio/webm' });
        if (audioBlob.size < 1000) {
          toast.error('التسجيل قصير جداً');
          return;
        }
        await transcribeAudio(audioBlob);
      };

      recorder.onerror = (e) => {
        console.error('Recording error:', e);
        toast.error('حدث خطأ في التسجيل');
        stream.getTracks().forEach(track => track.stop());
        setIsRecording(false);
      };
      
      recorder.start(100);
      setMediaRecorder(recorder);
      setIsRecording(true);
      setRecordingTime(0);
      recordingTimerRef.current = setInterval(() => setRecordingTime(prev => prev + 1), 1000);
      toast.info('🎤 جاري التسجيل... تحدث الآن');
    } catch (error) {
      console.error('Microphone error:', error);
      if (error.name === 'NotAllowedError') {
        toast.error('يرجى السماح بالوصول للمايكروفون');
      } else if (error.name === 'NotFoundError') {
        toast.error('لم يتم العثور على مايكروفون');
      } else {
        toast.error('فشل الوصول للمايكروفون');
      }
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      setIsRecording(false);
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
    }
  };

  const transcribeAudio = async (audioBlob) => {
    if (!currentSession) {
      toast.error('اختر محادثة أولاً');
      return;
    }
    setLoading(true);
    startLocalProgress();
    
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('language', 'ar');
      
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/stt/transcribe`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        if (data.text && data.text.trim()) {
          stopLocalProgress(true);
          setInputMessage(data.text);
          toast.success('تم تحويل الصوت!');
          setTimeout(() => sendMessageDirect(data.text), 500);
        } else {
          stopLocalProgress(false);
          toast.error('لم يتم التعرف على أي كلام');
        }
      } else {
        stopLocalProgress(false);
        toast.error('فشل تحويل الصوت');
      }
    } catch (error) {
      stopLocalProgress(false);
      toast.error('خطأ في تحويل الصوت');
    } finally {
      setLoading(false);
    }
  };

  const sendMessageDirect = async (text) => {
    if (!text.trim() || !currentSession) return;
    
    const userMessage = text.trim();
    setInputMessage('');
    setLoading(true);
    startLocalProgress();

    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: userMessage,
      message_type: 'text',
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
          headers: { 
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: userMessage,
            settings: { ...generationSettings, tts: ttsSettings }
          })
        }
      );

      const data = await res.json();

      if (res.ok) {
        stopLocalProgress(true);
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== tempUserMsg.id);
          return [...filtered, data.user_message, data.assistant_message];
        });
        
        if (ttsSettings.enabled && data.assistant_message?.audio_url) {
          playAudio(data.assistant_message.audio_url, data.assistant_message.id);
        }
      } else {
        stopLocalProgress(false);
        toast.error(data.detail || 'فشل إرسال الرسالة');
        setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
      }
    } catch (error) {
      stopLocalProgress(false);
      toast.error('خطأ في الاتصال');
      setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
    } finally {
      setLoading(false);
    }
  };

  const toggleRecording = () => {
    if (isRecording) stopRecording();
    else startRecording();
  };

  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
      if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
    };
  }, [mediaRecorder]);

  useEffect(() => {
    if (pendingVideoRequests.length > 0 && currentSession) {
      pollingIntervalRef.current = setInterval(async () => {
        await checkVideoRequestsStatus();
      }, 5000);
      return () => {
        if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
      };
    }
  }, [pendingVideoRequests, currentSession]);

  const checkVideoRequestsStatus = useCallback(async () => {
    if (!currentSession || pendingVideoRequests.length === 0) return;
    
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/chat/video-requests?session_id=${currentSession.id}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (res.ok) {
        const requests = await res.json();
        const completedRequests = requests.filter(r => r.status === 'completed');
        const stillPending = requests.filter(r => r.status === 'pending' || r.status === 'processing');
        
        if (completedRequests.length > 0) {
          toast.success(`تم توليد ${completedRequests.length} فيديو بنجاح!`);
          await loadSession(currentSession.id);
        }
        
        const stillPendingIds = stillPending.map(r => r.id);
        setPendingVideoRequests(prev => prev.filter(p => stillPendingIds.includes(p.id)));
        
        if (stillPending.length === 0 && pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      }
    } catch (error) {
      console.error('Error checking video requests:', error);
    }
  }, [currentSession, pendingVideoRequests]);

  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

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
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ session_type: type })
      });
      const session = await res.json();
      setSessions(prev => [session, ...prev]);
      setCurrentSession(session);
      setMessages([]);
      setPendingVideoRequests([]);
      toast.success('تم إنشاء محادثة جديدة');
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
      
      const videoRes = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/chat/video-requests?session_id=${sessionId}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      if (videoRes.ok) {
        const requests = await videoRes.json();
        const pending = requests.filter(r => r.status === 'pending' || r.status === 'processing');
        setPendingVideoRequests(pending);
      }
    } catch (error) {
      toast.error('فشل تحميل المحادثة');
    }
  }, []);

  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim() || !currentSession || loading) return;

    const userMessage = inputMessage;
    setInputMessage('');
    setLoading(true);
    startLocalProgress();

    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: userMessage,
      message_type: 'text',
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
          headers: { 
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: userMessage,
            settings: { ...generationSettings, tts: ttsSettings }
          })
        }
      );

      const data = await res.json();

      if (res.ok) {
        stopLocalProgress(true);
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== tempUserMsg.id);
          return [...filtered, data.user_message, data.assistant_message];
        });
        
        if (ttsSettings.enabled && data.assistant_message?.audio_url) {
          playAudio(data.assistant_message.audio_url, data.assistant_message.id);
        }

        const videoPendingAttachment = data.assistant_message?.attachments?.find(
          a => a.type === 'video_pending'
        );
        if (videoPendingAttachment && videoPendingAttachment.requests) {
          setPendingVideoRequests(prev => [...prev, ...videoPendingAttachment.requests]);
          toast.info('جاري توليد الفيديو في الخلفية...');
        }

        if (sessions.find(s => s.id === currentSession.id)?.message_count === 0) {
          setSessions(prev => prev.map(s =>
            s.id === currentSession.id
              ? { ...s, title: userMessage.slice(0, 50), message_count: 2 }
              : s
          ));
        }
      } else {
        stopLocalProgress(false);
        toast.error(data.detail || 'فشل إرسال الرسالة');
        setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
      }
    } catch (error) {
      stopLocalProgress(false);
      toast.error('حدث خطأ في الاتصال');
      setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [inputMessage, currentSession, loading, generationSettings, ttsSettings, sessions, startLocalProgress, stopLocalProgress]);

  const deleteSession = useCallback(async (sessionId) => {
    if (!window.confirm('هل تريد حذف هذه المحادثة؟')) return;
    
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

  const downloadAsset = useCallback((url, filename) => {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('جاري التحميل...');
  }, []);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  const getSessionIcon = useCallback((type) => {
    switch (type) {
      case 'image': return <Image className="w-4 h-4" />;
      case 'video': return <Video className="w-4 h-4" />;
      case 'website': return <Globe className="w-4 h-4" />;
      default: return <MessageSquare className="w-4 h-4" />;
    }
  }, []);

  const renderAttachment = useCallback((attachment) => {
    switch (attachment.type) {
      case 'image':
        return (
          <div className="mt-3 relative group">
          <img src={attachment.url} alt="Generated" className="w-full max-w-[280px] sm:max-w-sm md:max-w-md rounded-xl shadow-lg" loading="lazy" />
            <Button size="sm" onClick={() => downloadAsset(attachment.url, `zitex-image.png`)}
              className="absolute bottom-2 left-2 bg-black/50 hover:bg-black/70 opacity-0 group-hover:opacity-100">
              <Download className="w-4 h-4 me-1" /> تحميل
            </Button>
          </div>
        );
      case 'video':
        return (
          <div className="mt-3 relative group">
            <video src={attachment.url} controls className="w-full max-w-[300px] sm:max-w-md md:max-w-lg rounded-xl shadow-lg" preload="metadata" />
            <Button size="sm" onClick={() => downloadAsset(attachment.url, `zitex-video.mp4`)}
              className="mt-2 bg-orange-500 hover:bg-orange-600">
              <Download className="w-4 h-4 me-1" /> تحميل الفيديو
            </Button>
          </div>
        );
      case 'website':
        return (
          <div className="mt-3 p-4 bg-slate-700/50 rounded-xl">
            <div className="flex items-center gap-2 mb-3">
              <Globe className="w-6 h-6 text-green-400" />
              <span className="text-white font-semibold">موقع جاهز للتحميل</span>
            </div>
            <Button size="sm" onClick={() => {
              const content = JSON.stringify(attachment.files, null, 2);
              const blob = new Blob([content], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              downloadAsset(url, `zitex-website.json`);
            }} className="bg-green-500 hover:bg-green-600">
              <Download className="w-4 h-4 me-1" /> تحميل الكود
            </Button>
          </div>
        );
      case 'video_pending':
        return (
          <div className="mt-3 p-4 bg-orange-500/20 border border-orange-500/50 rounded-xl animate-pulse">
            <div className="flex items-center gap-3 mb-2">
              <Loader2 className="w-6 h-6 text-orange-400 animate-spin" />
              <span className="text-orange-300 font-semibold">جاري توليد الفيديو...</span>
            </div>
            <p className="text-sm text-orange-200/80">يستغرق التوليد 2-5 دقائق</p>
          </div>
        );
      default:
        return null;
    }
  }, [downloadAsset]);

  return (
    <div className="h-screen bg-slate-900 flex flex-col overflow-hidden">
      <Navbar user={user} transparent />
      
      <div className="flex-1 flex mt-16 overflow-hidden">
        {!sidebarOpen && currentSession && (
          <button onClick={() => setSidebarOpen(true)}
            className="md:hidden fixed top-20 right-4 z-30 p-2 bg-slate-700 rounded-lg shadow-lg border border-slate-600">
            <MessageSquare className="w-5 h-5 text-white" />
          </button>
        )}
        
        {sidebarOpen && (
          <div className="md:hidden fixed inset-0 bg-black/50 z-10" onClick={() => setSidebarOpen(false)} />
        )}
        
        <div className={`${sidebarOpen ? 'w-80' : 'w-0'} ${sidebarOpen ? 'fixed md:relative inset-y-0 right-0 z-20 mt-16 md:mt-0' : ''} flex-shrink-0 transition-all duration-300 overflow-hidden bg-slate-800 border-l border-slate-700 flex flex-col`}>
          <div className="p-3 md:p-4 border-b border-slate-700">
            <div className="flex md:hidden justify-between items-center mb-3">
              <span className="text-white font-semibold">المحادثات</span>
              <Button size="sm" variant="ghost" onClick={() => setSidebarOpen(false)}>
                <ChevronRight className="w-5 h-5 text-white" />
              </Button>
            </div>
            
            <Button onClick={() => { createSession('general'); if(window.innerWidth < 768) setSidebarOpen(false); }}
              className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600">
              <Plus className="w-4 h-4 me-2" /> محادثة جديدة
            </Button>
            
            <div className="flex gap-2 mt-3">
              <Button size="sm" variant="outline" onClick={() => { createSession('image'); if(window.innerWidth < 768) setSidebarOpen(false); }}
                className="flex-1 border-purple-500/50 text-purple-400 hover:bg-purple-500/20">
                <Image className="w-4 h-4" />
              </Button>
              <Button size="sm" variant="outline" onClick={() => { createSession('video'); if(window.innerWidth < 768) setSidebarOpen(false); }}
                className="flex-1 border-orange-500/50 text-orange-400 hover:bg-orange-500/20">
                <Video className="w-4 h-4" />
              </Button>
              <Button size="sm" variant="outline" onClick={() => { createSession('website'); if(window.innerWidth < 768) setSidebarOpen(false); }}
                className="flex-1 border-green-500/50 text-green-400 hover:bg-green-500/20">
                <Globe className="w-4 h-4" />
              </Button>
            </div>
          </div>
          
          <ScrollArea className="flex-1 p-2">
            {sessionsLoading ? <SessionSkeleton /> : sessions.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>لا توجد محادثات</p>
              </div>
            ) : (
              <div className="space-y-1">
                {sessions.map(session => (
                  <SessionItem key={session.id} session={session} isActive={currentSession?.id === session.id}
                    onSelect={(id) => { loadSession(id); if(window.innerWidth < 768) setSidebarOpen(false); }}
                    onDelete={deleteSession} getIcon={getSessionIcon} />
                ))}
              </div>
            )}
          </ScrollArea>
        </div>

        <Button size="icon" variant="ghost" onClick={() => setSidebarOpen(!sidebarOpen)}
          className="hidden md:flex absolute right-0 top-1/2 transform -translate-y-1/2 z-10 bg-slate-700 rounded-r-none hover:bg-slate-600">
          {sidebarOpen ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </Button>

        <div className="flex-1 flex flex-col overflow-hidden">
          {!currentSession ? (
            <div className="flex-1 flex items-center justify-center p-4 md:p-8">
              <div className="text-center max-w-2xl animate-fadeIn">
                <div className="w-20 h-20 md:w-24 md:h-24 mx-auto mb-6 bg-gradient-to-br from-purple-500 to-pink-500 rounded-3xl flex items-center justify-center shadow-2xl">
                  <Sparkles className="w-10 h-10 md:w-12 md:h-12 text-white" />
                </div>
                <h1 className="text-2xl md:text-4xl font-bold text-white mb-4">مرحباً بك في زيتكس</h1>
                <p className="text-xl text-gray-400 mb-8">مساعدك الإبداعي الذكي</p>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                  <Card className="bg-slate-800 border-purple-500/30 cursor-pointer hover:bg-slate-700 hover:scale-105 transition-all" onClick={() => createSession('image')}>
                    <CardContent className="p-6 text-center">
                      <Image className="w-10 h-10 text-purple-400 mx-auto mb-3" />
                      <h3 className="text-white font-semibold mb-1">توليد صور</h3>
                      <p className="text-sm text-gray-400">صور احترافية بالذكاء الاصطناعي</p>
                    </CardContent>
                  </Card>
                  
                  <Card className="bg-slate-800 border-orange-500/30 cursor-pointer hover:bg-slate-700 hover:scale-105 transition-all" onClick={() => createSession('video')}>
                    <CardContent className="p-6 text-center">
                      <Video className="w-10 h-10 text-orange-400 mx-auto mb-3" />
                      <h3 className="text-white font-semibold mb-1">فيديوهات سينمائية</h3>
                      <p className="text-sm text-gray-400">مع تعليق صوتي</p>
                    </CardContent>
                  </Card>
                  
                  <Card className="bg-slate-800 border-green-500/30 cursor-pointer hover:bg-slate-700 hover:scale-105 transition-all" onClick={() => createSession('website')}>
                    <CardContent className="p-6 text-center">
                      <Globe className="w-10 h-10 text-green-400 mx-auto mb-3" />
                      <h3 className="text-white font-semibold mb-1">بناء مواقع</h3>
                      <p className="text-sm text-gray-400">مواقع احترافية قابلة للتحميل</p>
                    </CardContent>
                  </Card>
                </div>
                
                <Button size="lg" onClick={() => createSession('general')} className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600">
                  <Plus className="w-5 h-5 me-2" /> ابدأ محادثة جديدة
                </Button>
              </div>
            </div>
          ) : (
            <>
              <ScrollArea className="flex-1 p-4 overflow-y-auto">
                <div className="max-w-4xl mx-auto space-y-4">
                  {messages.length === 0 && (
                    <div className="text-center py-12 text-gray-500">
                      <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-50" />
                      <p className="text-lg">ابدأ المحادثة!</p>
                    </div>
                  )}
                  
                  {messages.map((msg, idx) => (
                    <ChatMessage key={msg.id || idx} msg={msg} idx={idx} renderAttachment={renderAttachment}
                      onPlayAudio={playAudio} onGenerateTTS={generateTTS} playingAudio={playingAudio} />
                  ))}

                  {localProgress && <LocalProgressIndicator progress={localProgress} />}
                  
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>

              <div className="border-t border-slate-700 p-2 md:p-4 bg-slate-800/50 backdrop-blur">
                <div className="max-w-4xl mx-auto">
                  <audio ref={audioRef} className="hidden" />
                  
                  {showTTSSettings && (
                    <div className="mb-3 p-3 bg-slate-700/50 border border-slate-600 rounded-lg">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="text-white font-medium flex items-center gap-2">
                          <Volume2 className="w-4 h-4 text-purple-400" /> إعدادات الصوت
                        </h4>
                        <button onClick={() => setShowTTSSettings(false)} className="text-gray-400 hover:text-white">✕</button>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">المزود</label>
                          <select value={ttsSettings.provider}
                            onChange={(e) => setTtsSettings({...ttsSettings, provider: e.target.value, voice: e.target.value === 'openai' ? 'alloy' : '21m00Tcm4TlvDq8ikWAM'})}
                            className="w-full bg-slate-600 border-slate-500 text-white rounded px-2 py-1.5 text-sm">
                            <option value="openai">OpenAI TTS</option>
                            <option value="elevenlabs">ElevenLabs</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">الصوت</label>
                          <select value={ttsSettings.voice} onChange={(e) => setTtsSettings({...ttsSettings, voice: e.target.value})}
                            className="w-full bg-slate-600 border-slate-500 text-white rounded px-2 py-1.5 text-sm">
                            {availableVoices.filter(v => v.provider === ttsSettings.provider).map(voice => (
                              <option key={voice.id} value={voice.id}>{voice.name}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">السرعة: {ttsSettings.speed}x</label>
                          <input type="range" min="0.5" max="2" step="0.1" value={ttsSettings.speed}
                            onChange={(e) => setTtsSettings({...ttsSettings, speed: parseFloat(e.target.value)})} className="w-full" />
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {pendingVideoRequests.length > 0 && (
                    <div className="mb-2 p-2 bg-orange-500/20 border border-orange-500/40 rounded-lg flex items-center gap-2 text-sm">
                      <Loader2 className="w-4 h-4 text-orange-400 animate-spin" />
                      <span className="text-orange-300">جاري توليد {pendingVideoRequests.length} فيديو...</span>
                    </div>
                  )}
                  
                  <div className="flex gap-2">
                    <Input ref={inputRef} value={inputMessage} onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={handleKeyPress} placeholder="اكتب رسالتك هنا..."
                      className="flex-1 bg-slate-700 border-slate-600 text-white placeholder:text-gray-400" disabled={loading} />
                    
                    <Button variant="outline" onClick={toggleRecording} disabled={loading} size="icon"
                      className={`flex-shrink-0 ${isRecording ? 'bg-red-500/20 border-red-500 text-red-400 animate-pulse' : 'border-slate-600 text-gray-400 hover:text-white'}`}>
                      <Mic className="w-5 h-5" />
                    </Button>
                    
                    <Button onClick={sendMessage} disabled={loading || !inputMessage.trim() || isRecording} size="icon"
                      className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600">
                      {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    </Button>
                  </div>
                  
                  {isRecording && (
                    <div className="mt-2 flex items-center gap-2 px-3 py-1.5 bg-red-500/20 border border-red-500/50 rounded-lg w-fit">
                      <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                      <span className="text-red-400 text-sm">{recordingTime}ث - اضغط للإيقاف</span>
                    </div>
                  )}
                  
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    {currentSession?.session_type === 'video' && (
                      <select value={generationSettings.duration}
                        onChange={(e) => setGenerationSettings({...generationSettings, duration: parseInt(e.target.value)})}
                        className="bg-slate-700 border-slate-600 text-white rounded px-2 py-1 text-xs">
                        <option value={4}>4 ثواني</option>
                        <option value={8}>8 ثواني</option>
                        <option value={12}>12 ثانية</option>
                        <option value={60}>دقيقة</option>
                      </select>
                    )}
                    
                    <button onClick={() => setTtsSettings({...ttsSettings, enabled: !ttsSettings.enabled})}
                      className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${ttsSettings.enabled ? 'bg-purple-500/20 border border-purple-500/50 text-purple-400' : 'bg-slate-700 text-gray-400 hover:text-white'}`}>
                      <Volume2 className="w-3.5 h-3.5" /> <span className="hidden sm:inline">صوت</span>
                    </button>
                    
                    <button onClick={() => setShowTTSSettings(!showTTSSettings)}
                      className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-slate-700 text-gray-400 hover:text-white">
                      <Settings className="w-3.5 h-3.5" /> <span className="hidden sm:inline">إعدادات</span>
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
      
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn { animation: fadeIn 0.3s ease-out; }
      `}</style>
    </div>
  );
};

export default AIChat;
