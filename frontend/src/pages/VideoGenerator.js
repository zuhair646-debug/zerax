import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Video, Loader2, Play, Sparkles, Clock, Gift, Download, Mic, Volume2, Upload } from 'lucide-react';

const VideoGenerator = ({ user }) => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [freeRemaining, setFreeRemaining] = useState(user?.free_videos || 0);
  
  // Voice options
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState('');
  const [voiceText, setVoiceText] = useState('');
  const [enableVoice, setEnableVoice] = useState(false);
  const [voicesLoading, setVoicesLoading] = useState(false);
  
  // TTS Preview
  const [ttsLoading, setTtsLoading] = useState(false);
  const [previewAudio, setPreviewAudio] = useState(null);
  const audioRef = useRef(null);
  
  // Upload
  const [uploadedVideo, setUploadedVideo] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchHistory();
    fetchVoices();
    setFreeRemaining(user?.free_videos || 0);
  }, [user]);

  const fetchHistory = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/generate/videos/history`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      setHistory(data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchVoices = async () => {
    setVoicesLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/voices`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      setVoices(data.voices || []);
    } catch (error) {
      console.error('Error fetching voices:', error);
    } finally {
      setVoicesLoading(false);
    }
  };

  const previewVoice = async () => {
    if (!selectedVoice || !voiceText.trim()) {
      toast.error('يرجى اختيار صوت وكتابة نص');
      return;
    }

    setTtsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/tts/generate`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: voiceText,
          voice_id: selectedVoice,
          stability: 0.5,
          similarity_boost: 0.75
        })
      });

      const data = await res.json();

      if (res.ok && data.audio_url) {
        setPreviewAudio(data.audio_url);
        toast.success('تم توليد الصوت - اضغط للاستماع');
      } else {
        toast.error(data.detail || 'فشل توليد الصوت');
      }
    } catch (error) {
      toast.error('حدث خطأ أثناء التوليد');
    } finally {
      setTtsLoading(false);
    }
  };

  const generateVideo = async () => {
    if (!prompt.trim()) {
      toast.error('يرجى كتابة وصف للفيديو');
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      let url = `${process.env.REACT_APP_BACKEND_URL}/api/generate/video?prompt=${encodeURIComponent(prompt)}`;
      
      if (enableVoice && selectedVoice && voiceText) {
        url += `&voice_id=${selectedVoice}&voice_text=${encodeURIComponent(voiceText)}`;
      }
      
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await res.json();

      if (res.ok) {
        setFreeRemaining(data.free_videos_remaining || 0);
        if (data.was_free) {
          toast.success(`تم إرسال الطلب مجاناً! متبقي ${data.free_videos_remaining} فيديوهات مجانية`);
        } else {
          toast.success('تم إرسال طلب التوليد! سيتم إشعارك عند الانتهاء');
        }
        setPrompt('');
        setVoiceText('');
        setSelectedVoice('');
        setEnableVoice(false);
        fetchHistory();
      } else {
        toast.error(data.detail || 'فشل توليد الفيديو');
      }
    } catch (error) {
      toast.error('حدث خطأ أثناء التوليد');
    } finally {
      setLoading(false);
    }
  };

  const handleVideoUpload = async (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setUploadedVideo(reader.result);
        toast.success('تم رفع الفيديو بنجاح');
      };
      reader.readAsDataURL(file);
    }
  };

  const downloadMedia = async (url, filename, type) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/download/log?item_type=${type}&item_id=${filename}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
    } catch (error) {
      console.error('Error logging download:', error);
    }
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success(`تم تحميل ${type === 'video' ? 'الفيديو' : 'الصوت'}`);
  };

  const hasSubscription = user?.subscription_type === 'videos' || user?.is_owner;
  const canGenerate = hasSubscription || freeRemaining > 0;

  // Group voices by language/gender
  const groupedVoices = voices.reduce((acc, voice) => {
    const key = voice.language === 'ar' ? 'عربي' : 'إنجليزي';
    if (!acc[key]) acc[key] = [];
    acc[key].push(voice);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-slate-900" data-testid="video-generator-page">
      <Navbar user={user} transparent />
      
      <div className="container mx-auto px-4 md:px-8 max-w-7xl pt-24 pb-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2" data-testid="page-title">
            <Video className="w-8 h-8 inline me-3 text-orange-400" />
            إنشاء الفيديو بالذكاء الاصطناعي
          </h1>
          <p className="text-gray-400">حوّل أفكارك إلى فيديوهات احترافية مع تعليق صوتي</p>
        </div>

        {/* Free Trial Banner */}
        {!hasSubscription && freeRemaining > 0 && (
          <Card className="bg-gradient-to-r from-green-500/20 to-emerald-500/20 border-green-500/30 mb-6">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Gift className="w-8 h-8 text-green-400" />
                <div>
                  <p className="text-green-300 font-semibold">لديك {freeRemaining} فيديوهات مجانية!</p>
                  <p className="text-green-400/70 text-sm">جرّب الخدمة مجاناً قبل الاشتراك</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {!canGenerate && (
          <Card className="bg-yellow-500/10 border-yellow-500/30 mb-6">
            <CardContent className="p-4 flex items-center justify-between">
              <p className="text-yellow-300">انتهت تجاربك المجانية. اشترك للاستمرار في إنشاء الفيديوهات</p>
              <Button onClick={() => window.location.href = '/pricing'} variant="outline" className="border-yellow-500 text-yellow-300">
                عرض الأسعار
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Generator */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-orange-400" />
                إنشاء فيديو جديد
                {!hasSubscription && freeRemaining > 0 && (
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full ms-2">
                    مجاني
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="اكتب وصفاً تفصيلياً للفيديو الذي تريده... مثال: طائر يحلق فوق جبال ثلجية عند شروق الشمس بحركة بطيئة سينمائية"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={4}
                className="bg-slate-700 border-slate-600 text-white placeholder:text-gray-400"
                data-testid="prompt-input"
              />

              {/* Voice Options */}
              <div className="p-4 bg-slate-700/50 rounded-xl space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-white flex items-center gap-2">
                    <Mic className="w-5 h-5 text-blue-400" />
                    إضافة تعليق صوتي
                  </Label>
                  <button
                    type="button"
                    onClick={() => setEnableVoice(!enableVoice)}
                    className={`relative w-11 h-6 rounded-full transition-colors ${enableVoice ? 'bg-blue-500' : 'bg-slate-600'}`}
                    data-testid="enable-voice-toggle"
                  >
                    <span 
                      className={`absolute top-[2px] w-5 h-5 bg-white rounded-full transition-transform ${enableVoice ? 'right-[2px]' : 'left-[2px]'}`}
                    />
                  </button>
                </div>

                {enableVoice && (
                  <>
                    <div>
                      <Label className="text-gray-300 mb-2 block">اختر الصوت</Label>
                      <select
                        value={selectedVoice}
                        onChange={(e) => setSelectedVoice(e.target.value)}
                        className="w-full p-3 rounded-lg bg-slate-700 border border-slate-600 text-white"
                        data-testid="voice-select"
                      >
                        <option value="">-- اختر صوت --</option>
                        {Object.entries(groupedVoices).map(([lang, voiceList]) => (
                          <optgroup key={lang} label={lang}>
                            {voiceList.map((voice) => (
                              <option key={voice.voice_id} value={voice.voice_id}>
                                {voice.name} ({voice.gender === 'male' ? 'ذكر' : 'أنثى'})
                              </option>
                            ))}
                          </optgroup>
                        ))}
                      </select>
                    </div>

                    <div>
                      <Label className="text-gray-300 mb-2 block">نص التعليق الصوتي</Label>
                      <Textarea
                        value={voiceText}
                        onChange={(e) => setVoiceText(e.target.value)}
                        placeholder="اكتب النص الذي تريد تحويله إلى صوت..."
                        rows={3}
                        className="bg-slate-700 border-slate-600 text-white placeholder:text-gray-400"
                        data-testid="voice-text-input"
                      />
                    </div>

                    <div className="flex gap-2">
                      <Button
                        onClick={previewVoice}
                        disabled={ttsLoading || !selectedVoice || !voiceText.trim()}
                        variant="outline"
                        className="flex-1 border-slate-600 text-white hover:bg-slate-700"
                        data-testid="preview-voice-btn"
                      >
                        {ttsLoading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            <Volume2 className="w-4 h-4 me-2" />
                            معاينة الصوت
                          </>
                        )}
                      </Button>
                      
                      {previewAudio && (
                        <Button
                          onClick={() => audioRef.current?.play()}
                          variant="outline"
                          className="border-green-500 text-green-400 hover:bg-green-500/20"
                          data-testid="play-audio-btn"
                        >
                          <Play className="w-4 h-4" />
                        </Button>
                      )}
                    </div>

                    {previewAudio && (
                      <audio ref={audioRef} src={previewAudio} className="hidden" />
                    )}
                  </>
                )}
              </div>

              <Button 
                onClick={generateVideo} 
                disabled={loading || !canGenerate}
                className="w-full bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
                data-testid="generate-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 me-2 animate-spin" />
                    جاري الإرسال...
                  </>
                ) : (
                  <>
                    <Video className="w-4 h-4 me-2" />
                    توليد الفيديو {!hasSubscription && freeRemaining > 0 && '(مجاني)'}
                  </>
                )}
              </Button>

              <div className="p-4 bg-slate-700/50 rounded-lg">
                <p className="text-sm text-gray-400 flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  توليد الفيديو قد يستغرق من 2-5 دقائق
                </p>
              </div>

              {/* Upload existing video */}
              <div className="border-t border-slate-700 pt-4 mt-4">
                <Label className="text-gray-300 mb-3 block flex items-center gap-2">
                  <Upload className="w-5 h-5" />
                  أو ارفع فيديو موجود للتعديل
                </Label>
                <div 
                  className="border-2 border-dashed border-slate-600 rounded-xl p-6 text-center cursor-pointer hover:border-orange-500 transition-colors"
                  onClick={() => fileInputRef.current?.click()}
                  data-testid="upload-video-area"
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleVideoUpload}
                    accept="video/*"
                    className="hidden"
                  />
                  {uploadedVideo ? (
                    <video src={uploadedVideo} controls className="max-h-32 mx-auto rounded-lg" />
                  ) : (
                    <>
                      <Video className="w-10 h-10 text-gray-500 mx-auto mb-2" />
                      <p className="text-gray-400 text-sm">اضغط لرفع فيديو</p>
                    </>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* History */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">الفيديوهات السابقة</CardTitle>
            </CardHeader>
            <CardContent>
              {history.length === 0 ? (
                <div className="text-center py-12">
                  <Video className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                  <p className="text-gray-400">لا توجد فيديوهات بعد</p>
                  <p className="text-gray-500 text-sm mt-2">جرّب إنشاء فيديوك الأول مجاناً!</p>
                </div>
              ) : (
                <div className="space-y-4 max-h-[600px] overflow-y-auto">
                  {history.map((item) => (
                    <div key={item.id} className="p-4 bg-slate-700/50 rounded-lg" data-testid={`history-item-${item.id}`}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <p className="text-white text-sm mb-2 line-clamp-2">{item.prompt}</p>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`text-xs px-2 py-1 rounded-full ${
                              item.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                              item.status === 'processing' ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-red-500/20 text-red-400'
                            }`}>
                              {item.status === 'completed' ? 'مكتمل' : item.status === 'processing' ? 'قيد التوليد' : 'فشل'}
                            </span>
                            {item.is_free && (
                              <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full">
                                مجاني
                              </span>
                            )}
                            {item.voice_id && (
                              <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full flex items-center gap-1">
                                <Mic className="w-3 h-3" />
                                تعليق صوتي
                              </span>
                            )}
                            <span className="text-xs text-gray-500">
                              {new Date(item.created_at).toLocaleDateString('ar-SA')}
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-col gap-2">
                          {item.video_url && (
                            <Button 
                              size="sm" 
                              variant="outline" 
                              className="border-slate-600"
                              onClick={() => downloadMedia(item.video_url, `zenrex-video-${item.id}.mp4`, 'video')}
                              data-testid="download-video-btn"
                            >
                              <Download className="w-4 h-4 me-1" />
                              فيديو
                            </Button>
                          )}
                          {item.audio_url && (
                            <Button 
                              size="sm" 
                              variant="outline" 
                              className="border-blue-500 text-blue-400"
                              onClick={() => downloadMedia(item.audio_url, `zenrex-audio-${item.id}.mp3`, 'audio')}
                              data-testid="download-audio-btn"
                            >
                              <Download className="w-4 h-4 me-1" />
                              صوت
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default VideoGenerator;
