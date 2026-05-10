import { useState, useRef, useEffect } from 'react';
import { Paperclip, Mic, MicOff, Smile, Send, X, Image as ImageIcon, Video } from 'lucide-react';
import { toast } from 'sonner';

const EMOJIS = ['😊', '😂', '❤️', '👍', '🎉', '🔥', '💡', '✨', '🚀', '💪', '🙏', '👏'];

export default function ChatInput({ 
  onSend, 
  placeholder = "اكتب رسالتك...", 
  disabled = false,
  supportFiles = true,
  supportVoice = true,
  supportEmojis = true,
  value = '',
  onChange = null
}) {
  const [message, setMessage] = useState(value);
  const [files, setFiles] = useState([]);

  // Sync with external value
  useEffect(() => {
    if (value !== undefined && value !== message) {
      setMessage(value);
    }
  }, [value]);
  const [recording, setRecording] = useState(false);
  const [showEmojis, setShowEmojis] = useState(false);
  const [recognizing, setRecognizing] = useState(false);
  
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recognitionRef = useRef(null);

  // Web Speech API للتعرف على الصوت
  useEffect(() => {
    if (!supportVoice) return;
    
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.lang = 'ar-SA';
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;

      recognitionRef.current.onresult = (event) => {
        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' ';
          } else {
            interimTranscript += transcript;
          }
        }

        if (finalTranscript) {
          setMessage(prev => prev + finalTranscript);
        }
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setRecognizing(false);
        setRecording(false);
        if (event.error !== 'no-speech') {
          toast.error('خطأ في التعرف على الصوت');
        }
      };

      recognitionRef.current.onend = () => {
        setRecognizing(false);
        if (recording) {
          recognitionRef.current.start();
        }
      };
    }
  }, [supportVoice, recording]);

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    const validFiles = selectedFiles.filter(file => {
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

    setFiles(prev => [...prev, ...validFiles]);
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const toggleRecording = async () => {
    if (!recording) {
      try {
        if (recognitionRef.current) {
          recognitionRef.current.start();
          setRecognizing(true);
        }
        setRecording(true);
        toast.success('بدأ التسجيل...');
      } catch (error) {
        console.error('Error starting recording:', error);
        toast.error('فشل بدء التسجيل');
      }
    } else {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setRecording(false);
      setRecognizing(false);
      toast.success('توقف التسجيل');
    }
  };

  const handleSend = () => {
    if (!message.trim() && files.length === 0) return;
    
    onSend({ 
      text: message.trim(), 
      files: files 
    });
    
    setMessage('');
    setFiles([]);
    setShowEmojis(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const addEmoji = (emoji) => {
    setMessage(prev => prev + emoji);
  };

  return (
    <div className="relative">
      {/* معاينة الملفات المرفقة */}
      {files.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {files.map((file, index) => (
            <div key={index} className="relative group">
              <div className="bg-zinc-800/50 rounded-lg p-2 pr-8 border border-white/10 flex items-center gap-2">
                {file.type.startsWith('image/') ? (
                  <ImageIcon className="w-4 h-4 text-amber-400" />
                ) : (
                  <Video className="w-4 h-4 text-amber-400" />
                )}
                <span className="text-sm text-white/70 max-w-[150px] truncate">
                  {file.name}
                </span>
              </div>
              <button
                onClick={() => removeFile(index)}
                className="absolute top-1 left-1 bg-red-500 hover:bg-red-600 rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="w-3 h-3 text-white" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* لوحة الإيموجي */}
      {showEmojis && supportEmojis && (
        <div className="absolute bottom-full mb-2 left-0 bg-zinc-900 border border-white/10 rounded-xl p-3 shadow-2xl">
          <div className="grid grid-cols-6 gap-2">
            {EMOJIS.map((emoji, i) => (
              <button
                key={i}
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
                    onClick={() => fileInputRef.current?.click()}
                    disabled={disabled}
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
                  onClick={toggleRecording}
                  disabled={disabled}
                  className={`p-2 rounded-lg transition-all disabled:opacity-50 ${
                    recording 
                      ? 'bg-red-500 hover:bg-red-600 animate-pulse' 
                      : 'hover:bg-white/10'
                  }`}
                  title={recording ? 'إيقاف التسجيل' : 'بدء التسجيل الصوتي'}
                >
                  {recording ? (
                    <MicOff className="w-5 h-5 text-white" />
                  ) : (
                    <Mic className="w-5 h-5 text-white/70" />
                  )}
                </button>
              )}

              {/* إيموجي */}
              {supportEmojis && (
                <button
                  onClick={() => setShowEmojis(!showEmojis)}
                  disabled={disabled}
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
              onChange={(e) => {
                setMessage(e.target.value);
                if (onChange) onChange(e.target.value);
              }}
              onKeyPress={handleKeyPress}
              placeholder={recording ? 'جاري التسجيل...' : placeholder}
              disabled={disabled}
              rows={1}
              className="flex-1 bg-transparent text-white placeholder:text-white/40 outline-none resize-none min-h-[32px] max-h-[120px]"
              style={{ 
                direction: 'rtl',
                fieldSizing: 'content'
              }}
            />
          </div>
        </div>

        {/* زر الإرسال */}
        <button
          onClick={handleSend}
          disabled={disabled || (!message.trim() && files.length === 0)}
          className="bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700 disabled:cursor-not-allowed p-3 rounded-2xl transition-colors"
        >
          <Send className="w-5 h-5 text-black" />
        </button>
      </div>

      {/* مؤشر التسجيل */}
      {recording && (
        <div className="absolute -top-8 right-0 text-xs text-amber-400 flex items-center gap-2">
          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          جاري التسجيل والتحويل للنص...
        </div>
      )}
    </div>
  );
}
