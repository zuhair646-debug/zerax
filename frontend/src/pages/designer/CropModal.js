import React, { useState, useRef, useEffect } from 'react';
import { toast } from 'sonner';
import { X, Scissors, ImageIcon, Trash2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * CropModal — lets the user pick a saved AI image and crop a rectangle out
 * as a personal element. The crop is stored as natural-pixel coords so the
 * designer and the final game preview show the exact same cropped region.
 */
export default function CropModal({ onClose, onExtracted }) {
  const [images, setImages] = useState([]);
  const [selectedImage, setSelectedImage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [elementName, setElementName] = useState('');
  const [category, setCategory] = useState('custom');
  const [saving, setSaving] = useState(false);

  // Crop rectangle in NATURAL image pixels
  const [crop, setCrop] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState(null);
  const imgRef = useRef(null);
  const wrapRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API}/api/user-images`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        setImages(data.images || []);
      } catch (e) { toast.error('فشل تحميل الصور'); }
      finally { setLoading(false); }
    })();
  }, []);

  const deleteImage = async (id) => {
    if (!window.confirm('حذف هذه الصورة من مكتبتك؟')) return;
    const token = localStorage.getItem('token');
    await fetch(`${API}/api/user-images/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
    setImages((prev) => prev.filter((i) => i.id !== id));
    if (selectedImage?.id === id) setSelectedImage(null);
  };

  // Convert mouse coords (inside displayed image) to NATURAL image coords
  const toNaturalCoords = (e) => {
    if (!imgRef.current) return null;
    const rect = imgRef.current.getBoundingClientRect();
    const xDisp = e.clientX - rect.left;
    const yDisp = e.clientY - rect.top;
    const nw = imgRef.current.naturalWidth;
    const nh = imgRef.current.naturalHeight;
    const ratio = nw / rect.width;
    return {
      x: Math.max(0, Math.min(nw, xDisp * ratio)),
      y: Math.max(0, Math.min(nh, yDisp * ratio)),
      dispW: rect.width,
      dispH: rect.height,
      nw, nh,
    };
  };

  const onMouseDown = (e) => {
    const p = toNaturalCoords(e);
    if (!p) return;
    setIsDragging(true);
    setDragStart({ x: p.x, y: p.y });
    setCrop({ x: p.x, y: p.y, w: 0, h: 0 });
  };

  const onMouseMove = (e) => {
    if (!isDragging || !dragStart) return;
    const p = toNaturalCoords(e);
    if (!p) return;
    const x = Math.min(dragStart.x, p.x);
    const y = Math.min(dragStart.y, p.y);
    const w = Math.abs(p.x - dragStart.x);
    const h = Math.abs(p.y - dragStart.y);
    setCrop({ x, y, w, h });
  };

  const onMouseUp = () => setIsDragging(false);

  const save = async () => {
    if (!selectedImage || !crop || crop.w < 10 || crop.h < 10) { toast.error('ارسم مستطيل حول العنصر بالماوس أولاً'); return; }
    if (!elementName.trim()) { toast.error('أعطِ العنصر اسماً (مثل: حقل قمح)'); return; }
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const nw = imgRef.current.naturalWidth;
      const nh = imgRef.current.naturalHeight;
      const res = await fetch(`${API}/api/user-elements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: elementName.trim(),
          source_image_url: selectedImage.url,
          source_image_id: selectedImage.id,
          crop: { x: Math.round(crop.x), y: Math.round(crop.y), w: Math.round(crop.w), h: Math.round(crop.h) },
          natural_width: nw,
          natural_height: nh,
          category: category || 'custom',
        }),
      });
      if (!res.ok) {
        const errTxt = await res.text();
        throw new Error(errTxt || 'server error');
      }
      const data = await res.json();
      toast.success(`✅ تم استخراج "${data.name}" — تجده الآن في الشريط الجانبي`);
      onExtracted && onExtracted(data);
      setCrop(null);
      setElementName('');
      // Close modal after successful extraction so user sees the new element in sidebar
      setTimeout(() => onClose && onClose(), 800);
    } catch (e) {
      console.error('Extract failed:', e);
      toast.error('فشل الحفظ: ' + (e.message || 'خطأ غير معروف'));
    } finally { setSaving(false); }
  };

  // Build the visible overlay rectangle in display (px) coords
  let overlayStyle = null;
  if (crop && imgRef.current) {
    const rect = imgRef.current.getBoundingClientRect();
    const nw = imgRef.current.naturalWidth || 1;
    const nh = imgRef.current.naturalHeight || 1;
    const sx = rect.width / nw;
    const sy = rect.height / nh;
    overlayStyle = {
      left: crop.x * sx,
      top: crop.y * sy,
      width: crop.w * sx,
      height: crop.h * sy,
    };
  }

  return (
    <div className="fixed inset-0 bg-black/85 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose} dir="rtl" data-testid="crop-modal">
      <div className="bg-[#0e1128] rounded-2xl w-full max-w-6xl h-[90vh] overflow-hidden border border-yellow-500/30 flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Scissors className="w-5 h-5 text-yellow-500" />
            <h2 className="text-lg font-bold">استخراج عنصر من صورة</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded" data-testid="close-crop-btn"><X className="w-5 h-5" /></button>
        </div>

        <div className="flex-1 flex min-h-0">
          {/* Gallery */}
          <aside className="w-64 border-l border-white/10 overflow-y-auto p-3 bg-[#0a0e1c]">
            <div className="text-xs font-bold text-yellow-500 mb-3 uppercase flex items-center gap-2"><ImageIcon className="w-3 h-3" />صوري المحفوظة ({images.length})</div>
            {loading ? (
              <div className="text-center py-8 text-white/50 text-sm">جارٍ التحميل...</div>
            ) : images.length === 0 ? (
              <div className="text-center py-8 text-white/50 text-sm">
                <div className="text-4xl mb-2">📷</div>
                <div>لم تحفظ أي صورة بعد</div>
                <div className="mt-2 text-[11px] opacity-70">اذهب للشات، ولدّ صورة تصميم، ثم اضغط "حفظ للمحرر"</div>
              </div>
            ) : (
              <div className="space-y-2">
                {images.map((img) => (
                  <div key={img.id} className={`relative cursor-pointer border-2 rounded-lg overflow-hidden transition-all ${selectedImage?.id === img.id ? 'border-yellow-500' : 'border-transparent hover:border-white/30'}`}
                    onClick={() => { setSelectedImage(img); setCrop(null); }} data-testid={`saved-img-${img.id}`}>
                    <img src={img.url} alt="" className="w-full h-24 object-cover" crossOrigin="anonymous" />
                    <div className="absolute bottom-0 inset-x-0 bg-black/70 text-[10px] px-2 py-1 truncate">{img.prompt || 'بدون وصف'}</div>
                    <button onClick={(e) => { e.stopPropagation(); deleteImage(img.id); }} className="absolute top-1 right-1 p-1 bg-red-600/70 hover:bg-red-600 rounded"><Trash2 className="w-3 h-3" /></button>
                  </div>
                ))}
              </div>
            )}
          </aside>

          {/* Cropping Canvas */}
          <main className="flex-1 flex flex-col min-h-0">
            <div className="p-3 border-b border-white/10 flex items-center gap-3 bg-[#0a0e1c]">
              <input
                type="text"
                placeholder="اسم العنصر (مثلاً: حقل قمح)"
                value={elementName}
                onChange={(e) => setElementName(e.target.value)}
                className="flex-1 px-3 py-2 bg-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 text-sm"
                data-testid="element-name-input"
              />
              <select value={category} onChange={(e) => setCategory(e.target.value)} className="px-3 py-2 bg-white/10 rounded-lg text-sm" data-testid="element-category-select">
                <option value="custom">فئة: مخصص</option>
                <option value="buildings">مباني</option>
                <option value="fields">حقول</option>
                <option value="nature">طبيعة</option>
                <option value="units">وحدات</option>
                <option value="weapons">أسلحة</option>
                <option value="items">أغراض</option>
              </select>
              <button onClick={save} disabled={!selectedImage || !crop || crop.w < 10 || saving} className="px-5 py-2 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-lg font-bold text-sm disabled:opacity-40" data-testid="extract-btn">
                {saving ? 'جارٍ الحفظ...' : '✂️ استخراج'}
              </button>
            </div>

            <div className="flex-1 overflow-auto p-4 bg-[#030509] flex items-start justify-center" ref={wrapRef}>
              {!selectedImage ? (
                <div className="text-center py-16 text-white/70" data-testid="empty-select-state">
                  <div className="text-6xl mb-4">👈</div>
                  <div className="text-xl font-bold mb-2">اختر صورة من اليمين</div>
                  <div className="text-sm opacity-70 max-w-md mx-auto">أولاً، احفظ صور تصميم من الشات بضغط زر "✂️ حفظ للمحرر" عليها، ثم ستظهر هنا.</div>
                </div>
              ) : (
                <div className="relative">
                  {!crop && (
                    <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 bg-yellow-500 text-black px-4 py-2 rounded-full font-bold text-sm animate-pulse shadow-xl pointer-events-none" data-testid="crop-hint">
                      🖱️ اسحب ماوسك لرسم مربع حول العنصر الذي تريده
                    </div>
                  )}
                  <div className="relative inline-block" style={{ cursor: 'crosshair', userSelect: 'none' }}
                    onMouseDown={onMouseDown}
                    onMouseMove={onMouseMove}
                    onMouseUp={onMouseUp}
                    onMouseLeave={onMouseUp}>
                    <img ref={imgRef} src={selectedImage.url} alt="source" className="max-w-full max-h-[65vh] block" draggable={false} crossOrigin="anonymous" />
                    {crop && overlayStyle && (
                      <>
                        <div className="absolute inset-0 pointer-events-none" style={{ background: 'rgba(0,0,0,0.55)', clipPath: `polygon(0 0, 100% 0, 100% 100%, 0 100%, 0 0, ${overlayStyle.left}px ${overlayStyle.top}px, ${overlayStyle.left}px ${overlayStyle.top + overlayStyle.height}px, ${overlayStyle.left + overlayStyle.width}px ${overlayStyle.top + overlayStyle.height}px, ${overlayStyle.left + overlayStyle.width}px ${overlayStyle.top}px, ${overlayStyle.left}px ${overlayStyle.top}px)` }} />
                        <div className="absolute border-[3px] border-yellow-400 pointer-events-none shadow-[0_0_20px_rgba(250,204,21,0.8)]" style={overlayStyle}>
                          <div className="absolute -top-7 left-0 text-xs text-black font-bold bg-yellow-400 px-2 py-0.5 rounded">
                            {Math.round(crop.w)} × {Math.round(crop.h)} px
                          </div>
                          {/* Corner markers */}
                          <div className="absolute -top-1 -left-1 w-3 h-3 bg-yellow-400 rounded-full" />
                          <div className="absolute -top-1 -right-1 w-3 h-3 bg-yellow-400 rounded-full" />
                          <div className="absolute -bottom-1 -left-1 w-3 h-3 bg-yellow-400 rounded-full" />
                          <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-yellow-400 rounded-full" />
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
            <div className="p-2 border-t border-white/10 text-[12px] text-white/70 text-center bg-[#0a0e1c]">
              <span className="font-bold text-yellow-500">📝 خطوات الاستخدام:</span> ١) اختر صورة ← ٢) اسحب ماوسك على العنصر ← ٣) اكتب اسمه ← ٤) اضغط "استخراج"
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
