import { useState, useRef, useEffect } from 'react';
import { Paperclip, Mic, Send, Image as ImageIcon, Video, Smile, X, StopCircle } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// Emoji picker بسيط
const EMOJI_LIST = ['😊', '😂', '❤️', '👍', '🎉', '🔥', '💡', '✨', '🚀', '💪', '🙏', '👏'];

export default function ChatInput({ onSendMessage, onFileAttach, placeholder = "اكتب رسالتك..." }) {
  const [message, setMessage] = useState('');
  const [showEmoji, setShowEmoji] = useState(false);
  const [recording, setRecording] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recognitionRef = useRef(null);

  // تهيئة Speech Recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.lang = 'ar-SA';
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setMessage(prev => prev + ' ' + transcript);
        toast.success('تم تحويل الصوت إلى نص');
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        toast.error('فشل التعرف على الصوت');
        setRecording(false);
      };

      recognitionRef.current.onend = () => {
        setRecording(false);
      };
    }
  }, []);

  // بدء التسجيل الصوتي
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // بدء التسجيل
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        // إرسال الصوت للـbackend للتحويل
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        try {
          const token = localStorage.getItem('token');
          const response = await fetch(`${API}/api/speech/transcribe`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
            body: formData
          });

          if (response.ok) {
            const data = await response.json();
            setMessage(prev => prev + ' ' + data.text);
            toast.success('تم تحويل الصوت إلى نص');
          } else {
            throw new Error('فشل التحويل');
          }
        } catch (error) {
          console.error('Transcription error:', error);
          // Fallback: استخدام Web Speech API
          if (recognitionRef.current) {
            recognitionRef.current.start();
          } else {
            toast.error('التعرف على الصوت غير مدعوم في متصفحك');
          }
        }

        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start();
      setRecording(true);
      toast.info('جاري التسجيل... اضغط مرة أخرى للإيقاف');

    } catch (error) {
      console.error('Error accessing microphone:', error);
      toast.error('لا يمكن الوصول للميكروفون');
    }
  };

  // إيقاف التسجيل
  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
    }
  };

  // التعامل مع اختيار الملفات
  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    const newFiles = files.map(file => ({
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
      type: file.type.startsWith('image/') ? 'image' : 'video'
    }));
    
    setAttachedFiles(prev => [...prev, ...newFiles]);
    toast.success(`تم إرفاق ${files.length} ملف`);
  };

  // حذف ملف مرفق
  const removeFile = (index) => {
    setAttachedFiles(prev => {
      const newFiles = [...prev];
      if (newFiles[index].preview) {
        URL.revokeObjectURL(newFiles[index].preview);
      }
      newFiles.splice(index, 1);
      return newFiles;
    });
  };

  // إضافة emoji
  const addEmoji = (emoji) => {
    setMessage(prev => prev + emoji);
    setShowEmoji(false);
  };

  // إرسال الرسالة
  const handleSend = () => {
    if (!message.trim() && attachedFiles.length === 0) {
      toast.error('اكتب رسالة أو أرفق ملف');
      return;
    }

    onSendMessage({
      text: message.trim(),
      files: attachedFiles.map(f => f.file)
    });

    setMessage('');
    setAttachedFiles([]);
  };

  // Enter للإرسال
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-white/10 bg-zinc-900/50 backdrop-blur p-4">
      {/* معاينة الملفات المرفقة */}
      {attachedFiles.length > 0 && (
        <div className="flex gap-2 mb-3 overflow-x-auto pb-2">
          {attachedFiles.map((item, index) => (
            <div key={index} className="relative flex-shrink-0">
              {item.type === 'image' ? (
                <img 
                  src={item.preview} 
                  alt="preview" 
                  className="w-20 h-20 object-cover rounded-lg border border-white/20"
                />
              ) : (
                <div className="w-20 h-20 bg-zinc-800 rounded-lg border border-white/20 flex items-center justify-center">
                  <Video className="w-8 h-8 text-amber-400" />
                </div>
              )}
              <button
                onClick={() => removeFile(index)}
                className="absolute -top-2 -right-2 bg-red-500 rounded-full p-1 hover:bg-red-600"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* حقل الإدخال والأزرار */}
      <div className="flex items-end gap-2">
        {/* أزرار الإجراءات */}
        <div className="flex gap-1">
          {/* زر الصور/فيديو */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-2.5 bg-white/5 hover:bg-white/10 rounded-xl transition-colors"
            title="إرفاق صورة أو فيديو"
          >
            <Paperclip className="w-5 h-5 text-gray-400" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />

          {/* زر التسجيل الصوتي */}
          <button
            onClick={recording ? stopRecording : startRecording}
            className={`p-2.5 rounded-xl transition-colors ${
              recording 
                ? 'bg-red-500 hover:bg-red-600 animate-pulse' 
                : 'bg-white/5 hover:bg-white/10'
            }`}
            title={recording ? 'إيقاف التسجيل' : 'تسجيل صوتي'}
          >
            {recording ? (
              <StopCircle className="w-5 h-5 text-white" />
            ) : (
              <Mic className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {/* زر Emoji */}
          <div className="relative">
            <button
              onClick={() => setShowEmoji(!showEmoji)}
              className="p-2.5 bg-white/5 hover:bg-white/10 rounded-xl transition-colors"
              title="إضافة emoji"
            >
              <Smile className="w-5 h-5 text-gray-400" />
            </button>

            {showEmoji && (
              <div className="absolute bottom-full mb-2 left-0 bg-zinc-800 border border-white/10 rounded-xl p-2 shadow-xl">
                <div className="grid grid-cols-6 gap-1">
                  {EMOJI_LIST.map((emoji, i) => (
                    <button
                      key={i}
                      onClick={() => addEmoji(emoji)}
                      className="text-2xl hover:bg-white/10 rounded p-1 transition-colors"
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* حقل النص */}
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          rows={1}
          className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-3 
                     focus:border-amber-400 outline-none resize-none min-h-[44px] max-h-32"
          style={{ direction: 'rtl' }}
        />

        {/* زر الإرسال */}
        <button
          onClick={handleSend}
          disabled={!message.trim() && attachedFiles.length === 0}
          className="p-2.5 bg-amber-500 hover:bg-amber-400 disabled:bg-white/5 
                     disabled:text-gray-600 rounded-xl transition-colors"
          title="إرسال"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>

      {recording && (
        <p className="text-xs text-red-400 mt-2 text-center animate-pulse">
          🔴 جاري التسجيل... اضغط على زر الميكروفون للإيقاف
        </p>
      )}
    </div>
  );
}
