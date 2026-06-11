import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { Image, Loader2, Download, Sparkles, Gift, Upload, Type, Palette } from 'lucide-react';

const ImageGenerator = ({ user }) => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [generatedImage, setGeneratedImage] = useState(null);
  const [history, setHistory] = useState([]);
  const [freeRemaining, setFreeRemaining] = useState(user?.free_images || 0);
  const [activeTab, setActiveTab] = useState('generate');
  
  // Edit mode state
  const [uploadedImage, setUploadedImage] = useState(null);
  const [textOverlay, setTextOverlay] = useState('');
  const [textPosition, setTextPosition] = useState('bottom');
  const [textColor, setTextColor] = useState('#FFFFFF');
  const [fontSize, setFontSize] = useState(40);
  const [editLoading, setEditLoading] = useState(false);
  const [editedImage, setEditedImage] = useState(null);
  
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchHistory();
    setFreeRemaining(user?.free_images || 0);
  }, [user]);

  const fetchHistory = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/generate/images/history`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      setHistory(data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const generateImage = async () => {
    if (!prompt.trim()) {
      toast.error('يرجى كتابة وصف للصورة');
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/generate/image?prompt=${encodeURIComponent(prompt)}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await res.json();

      if (res.ok && data.image_url) {
        setGeneratedImage(data.image_url);
        setFreeRemaining(data.free_images_remaining || 0);
        if (data.was_free) {
          toast.success(`تم توليد الصورة مجاناً! متبقي ${data.free_images_remaining} صور مجانية`);
        } else {
          toast.success('تم توليد الصورة بنجاح!');
        }
        fetchHistory();
      } else {
        toast.error(data.detail || 'فشل توليد الصورة');
      }
    } catch (error) {
      toast.error('حدث خطأ أثناء التوليد');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setUploadedImage(reader.result);
        setEditedImage(null);
      };
      reader.readAsDataURL(file);
    }
  };

  const editImage = async () => {
    if (!uploadedImage) {
      toast.error('يرجى رفع صورة أولاً');
      return;
    }

    setEditLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/images/edit`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          image_base64: uploadedImage,
          text: textOverlay,
          text_position: textPosition,
          text_color: textColor,
          font_size: fontSize
        })
      });

      const data = await res.json();

      if (res.ok && data.edited_image_url) {
        setEditedImage(data.edited_image_url);
        toast.success('تم تعديل الصورة بنجاح!');
        fetchHistory();
      } else {
        toast.error(data.detail || 'فشل تعديل الصورة');
      }
    } catch (error) {
      toast.error('حدث خطأ أثناء التعديل');
    } finally {
      setEditLoading(false);
    }
  };

  const downloadImage = async (imageUrl, filename = 'zenrex-image.png') => {
    try {
      // Log download
      const token = localStorage.getItem('token');
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/download/log?item_type=image&item_id=${filename}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
    } catch (error) {
      console.error('Error logging download:', error);
    }
    
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('تم تحميل الصورة');
  };

  const hasSubscription = user?.subscription_type === 'images' || user?.is_owner;
  const canGenerate = hasSubscription || freeRemaining > 0;

  return (
    <div className="min-h-screen bg-slate-900" data-testid="image-generator-page">
      <Navbar user={user} transparent />
      
      <div className="container mx-auto px-4 md:px-8 max-w-7xl pt-24 pb-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2" data-testid="page-title">
            <Image className="w-8 h-8 inline me-3 text-purple-400" />
            توليد وتعديل الصور بالذكاء الاصطناعي
          </h1>
          <p className="text-gray-400">أنشئ صوراً إبداعية أو عدّل صورك الخاصة</p>
        </div>

        {/* Free Trial Banner */}
        {!hasSubscription && freeRemaining > 0 && (
          <Card className="bg-gradient-to-r from-green-500/20 to-emerald-500/20 border-green-500/30 mb-6">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Gift className="w-8 h-8 text-green-400" />
                <div>
                  <p className="text-green-300 font-semibold">لديك {freeRemaining} صور مجانية!</p>
                  <p className="text-green-400/70 text-sm">جرّب الخدمة مجاناً قبل الاشتراك</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {!canGenerate && (
          <Card className="bg-yellow-500/10 border-yellow-500/30 mb-6">
            <CardContent className="p-4 flex items-center justify-between">
              <p className="text-yellow-300">انتهت تجاربك المجانية. اشترك للاستمرار في توليد الصور</p>
              <Button onClick={() => window.location.href = '/pricing'} variant="outline" className="border-yellow-500 text-yellow-300">
                عرض الأسعار
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Generator / Editor */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="grid w-full grid-cols-2 bg-slate-700">
                  <TabsTrigger value="generate" className="data-[state=active]:bg-purple-500" data-testid="generate-tab">
                    <Sparkles className="w-4 h-4 me-2" />
                    إنشاء صورة
                  </TabsTrigger>
                  <TabsTrigger value="edit" className="data-[state=active]:bg-blue-500" data-testid="edit-tab">
                    <Type className="w-4 h-4 me-2" />
                    تعديل صورة
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </CardHeader>
            <CardContent className="space-y-4">
              {activeTab === 'generate' ? (
                <>
                  <Textarea
                    placeholder="اكتب وصفاً تفصيلياً للصورة التي تريدها... مثال: قطة لطيفة تجلس على سحابة ملونة في غروب الشمس"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    rows={4}
                    className="bg-slate-700 border-slate-600 text-white placeholder:text-gray-400"
                    data-testid="prompt-input"
                  />
                  <Button 
                    onClick={generateImage} 
                    disabled={loading || !canGenerate}
                    className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
                    data-testid="generate-btn"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 me-2 animate-spin" />
                        جاري التوليد...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4 me-2" />
                        توليد الصورة {!hasSubscription && freeRemaining > 0 && '(مجاني)'}
                      </>
                    )}
                  </Button>

                  {/* Generated Image */}
                  {generatedImage && (
                    <div className="mt-6">
                      <div className="relative rounded-xl overflow-hidden bg-slate-700">
                        <img 
                          src={generatedImage} 
                          alt="Generated" 
                          className="w-full"
                          data-testid="generated-image"
                        />
                        <Button
                          onClick={() => downloadImage(generatedImage, `zenrex-${Date.now()}.png`)}
                          className="absolute bottom-4 left-4 bg-white/20 backdrop-blur-sm hover:bg-white/30"
                          size="sm"
                          data-testid="download-generated-btn"
                        >
                          <Download className="w-4 h-4 me-2" />
                          تحميل
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  {/* Upload Section */}
                  <div 
                    className="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center cursor-pointer hover:border-blue-500 transition-colors"
                    onClick={() => fileInputRef.current?.click()}
                    data-testid="upload-area"
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileUpload}
                      accept="image/*"
                      className="hidden"
                      data-testid="file-input"
                    />
                    {uploadedImage ? (
                      <img src={uploadedImage} alt="Uploaded" className="max-h-48 mx-auto rounded-lg" />
                    ) : (
                      <>
                        <Upload className="w-12 h-12 text-gray-500 mx-auto mb-3" />
                        <p className="text-gray-400">اضغط لرفع صورة</p>
                        <p className="text-gray-500 text-sm mt-1">PNG, JPG, WEBP</p>
                      </>
                    )}
                  </div>

                  {uploadedImage && (
                    <>
                      {/* Text Overlay Options */}
                      <div className="space-y-4 p-4 bg-slate-700/50 rounded-xl">
                        <h3 className="text-white font-semibold flex items-center gap-2">
                          <Type className="w-5 h-5" />
                          إضافة نص على الصورة
                        </h3>
                        
                        <div>
                          <Label className="text-gray-300 mb-2 block">النص</Label>
                          <Input
                            value={textOverlay}
                            onChange={(e) => setTextOverlay(e.target.value)}
                            placeholder="اكتب النص هنا..."
                            className="bg-slate-700 border-slate-600 text-white"
                            data-testid="text-input"
                          />
                        </div>

                        <div className="grid grid-cols-3 gap-4">
                          <div>
                            <Label className="text-gray-300 mb-2 block">الموقع</Label>
                            <select
                              value={textPosition}
                              onChange={(e) => setTextPosition(e.target.value)}
                              className="w-full p-2 rounded-md bg-slate-700 border border-slate-600 text-white"
                              data-testid="position-select"
                            >
                              <option value="top">أعلى</option>
                              <option value="center">وسط</option>
                              <option value="bottom">أسفل</option>
                            </select>
                          </div>
                          
                          <div>
                            <Label className="text-gray-300 mb-2 block">اللون</Label>
                            <div className="flex items-center gap-2">
                              <input
                                type="color"
                                value={textColor}
                                onChange={(e) => setTextColor(e.target.value)}
                                className="w-10 h-10 rounded cursor-pointer"
                                data-testid="color-input"
                              />
                              <span className="text-gray-400 text-sm">{textColor}</span>
                            </div>
                          </div>
                          
                          <div>
                            <Label className="text-gray-300 mb-2 block">الحجم</Label>
                            <Input
                              type="number"
                              value={fontSize}
                              onChange={(e) => setFontSize(parseInt(e.target.value) || 40)}
                              min="10"
                              max="200"
                              className="bg-slate-700 border-slate-600 text-white"
                              data-testid="font-size-input"
                            />
                          </div>
                        </div>
                      </div>

                      <Button 
                        onClick={editImage} 
                        disabled={editLoading}
                        className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600"
                        data-testid="edit-btn"
                      >
                        {editLoading ? (
                          <>
                            <Loader2 className="w-4 h-4 me-2 animate-spin" />
                            جاري التعديل...
                          </>
                        ) : (
                          <>
                            <Palette className="w-4 h-4 me-2" />
                            تطبيق التعديلات
                          </>
                        )}
                      </Button>

                      {/* Edited Image */}
                      {editedImage && (
                        <div className="mt-4">
                          <div className="relative rounded-xl overflow-hidden bg-slate-700">
                            <img 
                              src={editedImage} 
                              alt="Edited" 
                              className="w-full"
                              data-testid="edited-image"
                            />
                            <Button
                              onClick={() => downloadImage(editedImage, `zenrex-edited-${Date.now()}.png`)}
                              className="absolute bottom-4 left-4 bg-white/20 backdrop-blur-sm hover:bg-white/30"
                              size="sm"
                              data-testid="download-edited-btn"
                            >
                              <Download className="w-4 h-4 me-2" />
                              تحميل
                            </Button>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* History */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">الصور السابقة</CardTitle>
            </CardHeader>
            <CardContent>
              {history.length === 0 ? (
                <div className="text-center py-12">
                  <Image className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                  <p className="text-gray-400">لا توجد صور بعد</p>
                  <p className="text-gray-500 text-sm mt-2">جرّب توليد صورتك الأولى مجاناً!</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4 max-h-[600px] overflow-y-auto">
                  {history.map((item) => (
                    <div key={item.id} className="relative group" data-testid={`history-item-${item.id}`}>
                      {(item.edited_image_url || item.image_url) ? (
                        <>
                          <img 
                            src={item.edited_image_url || item.image_url} 
                            alt={item.prompt}
                            className="w-full aspect-square object-cover rounded-lg"
                          />
                          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex flex-col items-center justify-center p-2 gap-2">
                            <p className="text-white text-xs line-clamp-2 text-center">{item.prompt}</p>
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => downloadImage(item.edited_image_url || item.image_url, `zenrex-${item.id}.png`)}
                              className="bg-white/20 hover:bg-white/30 text-white"
                            >
                              <Download className="w-3 h-3 me-1" />
                              تحميل
                            </Button>
                          </div>
                        </>
                      ) : (
                        <div className="w-full aspect-square bg-slate-700 rounded-lg flex items-center justify-center">
                          <p className="text-gray-500 text-sm">فشل التوليد</p>
                        </div>
                      )}
                      {item.is_free && (
                        <span className="absolute top-2 right-2 text-xs bg-green-500 text-white px-2 py-0.5 rounded-full">
                          مجاني
                        </span>
                      )}
                      {item.is_edit && (
                        <span className="absolute top-2 left-2 text-xs bg-blue-500 text-white px-2 py-0.5 rounded-full">
                          معدّل
                        </span>
                      )}
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

export default ImageGenerator;
