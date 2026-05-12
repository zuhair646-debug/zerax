import { useState, useRef, useEffect } from 'react';
import { Paperclip, Mic, MicOff, Smile, Send, X, Image as ImageIcon, Video, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const EMOJIS = ['😊', '😂', '❤️', '👍', '🎉', '🔥', '💡', '✨', '🚀', '💪', '🙏', '👏'];

function getSupportedAudioMimeType() {
  if (typeof window === 'undefined' || !window.MediaRecorder) return '';
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
    'audio/ogg',
  ];
  return types.find((type) => window.MediaRecorder.isTypeSupported(type)) || '';
}

function audioExtension(mimeType) {
  if (mimeType.includes('mp4')) return 'mp4';
  if (mimeType.includes('ogg')) return 'ogg';
  if (mimeType.includes('mpeg')) return 'mp3';
  if (mimeType.includes('wav')) return 'wav';
  return 'webm';
}

export default function ChatInput({
  onSend,
  placeholder = 'اكتب رسالتك...',
  disabled = false,
  supportFiles = true,
  supportVoice = true,
  supportEmojis = true,
  value = '',
  onChange = null,
}) {
  const [message, setMessage] = useState(value);
  const [files, setFiles] = useState([]);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [showEmojis, setShowEmojis] = useState(false);
  const [filePreviews, setFilePreviews] = useState([]);

  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Sync with external value
  useEffect(() => {
    if (value !== undefined && value !== message) {
      setMessage(value);
    }
  }, [value]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current?.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
      mediaStreamRef.current?.getTracks?.().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    const previews = files.map((file) => ({
      file,
      url: file.type?.startsWith('image/') ? URL.createObjectURL(file) : '',
    }));
    setFilePreviews(previews);
    return () => previews.forEach((preview) => {
      if (preview.url) URL.revokeObjectURL(preview.url);
    });
  }, [files]);

  const updateMessage = (nextValue) => {
    setMessage(nextValue);
    if (onChange) onChange(nextValue);
  };

  const appendTranscript = (text) => {
    if (!text?.trim()) return;
    const normalized = text.trim();
    updateMessage(`${message ? `${message.trim()} ` : ''}${normalized}`);
  };

  const transcribeAudio = async (blob, mimeType) => {
    const token = localStorage.getItem('token');
    if (!token) {
      toast.error('سجل الدخول أولاً لاستخدام التسجيل الصوتي');
      return;
    }

    if (!blob || blob.size < 300) {
      toast.error('التسجيل قصير جداً، حاول مرة أخرى');
      return;
    }

    setTranscribing(true);
    try {
      const formData = new FormData();
      const extension = audioExtension(mimeType || blob.type || 'audio/webm');
      formData.append('audio', blob, `voice-${Date.now()}.${extension}`);
      formData.append('language', 'ar');

      const response = await fetch(`${API}/api/stt/transcribe`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      let data = {};
      try {
        data = await response.json();
      } catch (_) {
        data = {};
      }

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'فشل تحويل الصوت إلى نص');
      }

      const text = (data.text || '').trim();
      if (!text) {
        toast.error('لم يتم التعرف على صوت واضح، جرّب التسجيل لمدة أطول وبهدوء');
        return;
      }

      appendTranscript(text);
      toast.success('تم تحويل الصوت إلى نص');
    } catch (error) {
      console.error('Voice transcription error:', error);
      toast.error(error.message || 'فشل تحويل الصوت إلى نص');
    } finally {
      setTranscribing(false);
    }
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    const validFiles = selectedFiles.filter((file) => {
      const isImage = file.type.startsWith('image/');
      const isVideo = file.type.startsWith('video/');
      const isValidSize = file.size <= 50 * 1024 * 1024; // 50MB

      if (!isImage && !isVideo) {
        toast.error(`${file.name}: نوع الملف غير مدعوم`);
        return false;
      }
      if (!isValidSize) {
        toast.error(`${file.name}: الحجم أكبر من 50MB`);
        return false;
      }
      return true;
    });

    setFiles((prev) => [...prev, ...validFiles]);
    if (e.target) e.target.value = '';
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      toast.error('متصفحك لا يدعم التسجيل الصوتي، جرّب Chrome أو Safari محدث');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = getSupportedAudioMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

      audioChunksRef.current = [];
      mediaStreamRef.current = stream;
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error || event);
        toast.error('حدث خطأ أثناء التسجيل');
        setRecording(false);
      };

      recorder.onstop = async () => {
        const chunks = audioChunksRef.current;
        const finalMimeType = recorder.mimeType || mimeType || 'audio/webm';
        mediaStreamRef.current?.getTracks?.().forEach((track) => track.stop());
        mediaStreamRef.current = null;
        mediaRecorderRef.current = null;
        setRecording(false);

        if (!chunks.length) {
          toast.error('لم يتم التقاط صوت، تأكد من صلاحية الميكروفون');
          return;
        }

        const blob = new Blob(chunks, { type: finalMimeType });
        await transcribeAudio(blob, finalMimeType);
      };

      recorder.start(250);
      setRecording(true);
      toast.success('بدأ التسجيل... اضغط الميكروفون مرة ثانية للإيقاف');
    } catch (error) {
      console.error('Error starting recording:', error);
      const denied = error?.name === 'NotAllowedError' || error?.name === 'SecurityError';
      toast.error(denied ? 'اسمح للمتصفح باستخدام الميكروفون' : 'فشل بدء التسجيل الصوتي');
      mediaStreamRef.current?.getTracks?.().forEach((track) => track.stop());
      mediaStreamRef.current = null;
      setRecording(false);
    }
  };

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state === 'recording') {
      recorder.stop();
    } else {
      mediaStreamRef.current?.getTracks?.().forEach((track) => track.stop());
      mediaStreamRef.current = null;
      setRecording(false);
    }
  };

  const toggleRecording = async () => {
    if (disabled || transcribing) return;
    if (recording) {
      stopRecording();
    } else {
      await startRecording();
    }
  };

  const handleSend = () => {
    if ((!message.trim() && files.length === 0) || disabled || recording || transcribing) return;

    onSend({
      text: message.trim(),
      files,
    });

    updateMessage('');
    setFiles([]);
    setShowEmojis(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const addEmoji = (emoji) => {
    updateMessage(message + emoji);
  };

  const busyVoice = recording || transcribing;

  return (
    <div className="relative">
      {/* معاينة الملفات المرفقة */}
      {files.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {files.map((file, index) => {
            const preview = filePreviews[index];
            const isImage = file.type.startsWith('image/');
            return (
              <div key={`${file.name}-${index}`} className="relative group">
                <div className={`bg-zinc-800/50 overflow-hidden rounded-xl border border-white/10 ${isImage ? 'w-28' : 'p-2 pr-8 flex items-center gap-2'}`}>
                  {isImage && preview?.url ? (
                    <>
                      <img src={preview.url} alt={file.name} className="h-20 w-full object-cover bg-zinc-900" />
                      <div className="px-2 py-1 text-[10px] text-white/70 truncate">{file.name}</div>
                    </>
                  ) : (
                    <>
                      {isImage ? (
                        <ImageIcon className="w-4 h-4 text-amber-400" />
                      ) : (
                        <Video className="w-4 h-4 text-amber-400" />
                      )}
                      <span className="text-sm text-white/70 max-w-[150px] truncate">
                        {file.name}
                      </span>
                    </>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  className="absolute top-1 left-1 bg-red-500 hover:bg-red-600 rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3 text-white" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* لوحة الإيموجي */}
      {showEmojis && supportEmojis && (
        <div className="absolute bottom-full mb-2 left-0 bg-zinc-900 border border-white/10 rounded-xl p-3 shadow-2xl z-20">
          <div className="grid grid-cols-6 gap-2">
            {EMOJIS.map((emoji, i) => (
              <button
                key={i}
                type="button"
                onClick={() => addEmoji(emoji)}
                className="text-2xl hover:scale-125 transition-transform"
              >
                {emoji}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* حقل الإدخال */}
      <div className="flex items-end gap-2">
        <div className="flex-1 bg-black/40 border border-white/15 rounded-2xl p-3 focus-within:border-amber-400 transition-colors">
          <div className="flex items-end gap-2">
            {/* أزرار الإضافات */}
            <div className="flex items-center gap-1 pb-1">
              {/* رفع ملفات */}
              {supportFiles && (
                <>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,video/*"
                    multiple
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={disabled || busyVoice}
                    className="p-2 hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
                    title="إضافة صورة أو فيديو"
                  >
                    <Paperclip className="w-5 h-5 text-white/70" />
                  </button>
                </>
              )}

              {/* تسجيل صوتي */}
              {supportVoice && (
                <button
                  type="button"
                  onClick={toggleRecording}
                  disabled={disabled || transcribing}
                  className={`p-2 rounded-lg transition-all disabled:opacity-50 ${
                    recording
                      ? 'bg-red-500 hover:bg-red-600 animate-pulse'
                      : transcribing
                        ? 'bg-amber-500/20'
                        : 'hover:bg-white/10'
                  }`}
                  title={recording ? 'إيقاف التسجيل وتحويله إلى نص' : 'بدء التسجيل الصوتي'}
                >
                  {transcribing ? (
                    <Loader2 className="w-5 h-5 text-amber-300 animate-spin" />
                  ) : recording ? (
                    <MicOff className="w-5 h-5 text-white" />
                  ) : (
                    <Mic className="w-5 h-5 text-white/70" />
                  )}
                </button>
              )}

              {/* إيموجي */}
              {supportEmojis && (
                <button
                  type="button"
                  onClick={() => setShowEmojis(!showEmojis)}
                  disabled={disabled || busyVoice}
                  className={`p-2 rounded-lg transition-colors disabled:opacity-50 ${
                    showEmojis ? 'bg-white/10' : 'hover:bg-white/10'
                  }`}
                  title="إضافة إيموجي"
                >
                  <Smile className="w-5 h-5 text-white/70" />
                </button>
              )}
            </div>

            {/* حقل النص */}
            <textarea
              value={message}
              onChange={(e) => updateMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={recording ? 'جاري التسجيل... اضغط الميكروفون للإيقاف' : transcribing ? 'جاري تحويل الصوت إلى نص...' : placeholder}
              disabled={disabled || recording || transcribing}
              rows={1}
              className="flex-1 bg-transparent text-white placeholder:text-white/40 outline-none resize-none min-h-[32px] max-h-[120px] disabled:opacity-60"
              style={{
                direction: 'rtl',
                fieldSizing: 'content',
              }}
            />
          </div>
        </div>

        {/* زر الإرسال */}
        <button
          type="button"
          onClick={handleSend}
          disabled={disabled || recording || transcribing || (!message.trim() && files.length === 0)}
          className="bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700 disabled:cursor-not-allowed p-3 rounded-2xl transition-colors"
        >
          <Send className="w-5 h-5 text-black" />
        </button>
      </div>

      {/* مؤشر التسجيل */}
      {busyVoice && (
        <div className="absolute -top-8 right-0 text-xs text-amber-400 flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${recording ? 'bg-red-500 animate-pulse' : 'bg-amber-400'}`} />
          {recording ? 'جاري التسجيل... اضغط الميكروفون للإيقاف' : 'جاري تحويل الصوت إلى نص...'}
        </div>
      )}
    </div>
  );
}
