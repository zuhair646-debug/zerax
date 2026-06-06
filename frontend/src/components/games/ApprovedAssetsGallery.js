/**
 * 🖼️ ApprovedAssetsGallery
 * ────────────────────────
 * Floating panel inside the chat that lists every approved asset for the
 * current project. Each card has a "📋 نسخ ID" button that copies the
 * required tag into the user's chat input automatically, so the owner
 * doesn't have to memorize UUIDs.
 *
 * Tags inserted:
 *   • IMG_REF  → <<IMG_REF: english prompt | ref: ASSET_ID>>
 *   • IMG_EDIT → <<IMG_EDIT: english edit | ref: ASSET_ID>>
 *   • COMPOSE  → adds id to a "selected" set; user clicks "اجمع المحدد" to
 *                emit one <<COMPOSE: scene | refs: id1, id2, id3>>
 */
import React, { useState, useEffect, useMemo } from 'react';
import { X, Copy, Image as ImgIcon, Check } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ApprovedAssetsGallery({ projectId, token, onInsertTag, onClose }) {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());
  const [filter, setFilter] = useState('all'); // all|image|audio|video|model

  useEffect(() => {
    if (!projectId || !token) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${API}/api/games/project/${projectId}/approved-assets`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const d = await r.json();
        if (!cancelled) setAssets(d.assets || []);
      } catch {
        if (!cancelled) setAssets([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [projectId, token]);

  const filtered = useMemo(
    () => (filter === 'all' ? assets : assets.filter(a => a.type === filter)),
    [assets, filter]
  );

  const toggleSelected = (id) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const insertRef = (id) => {
    onInsertTag(`<<IMG_REF: describe new subject in english | ref: ${id}>>`);
  };
  const insertEdit = (id) => {
    onInsertTag(`<<IMG_EDIT: describe the edit in english | ref: ${id}>>`);
  };
  const insertCompose = () => {
    if (selected.size < 2) return alert('اختر صورتين أو أكثر للدمج');
    const ids = Array.from(selected).join(', ');
    onInsertTag(`<<COMPOSE: describe the combined scene in english | refs: ${ids}>>`);
    setSelected(new Set());
  };

  return (
    <div
      data-testid="approved-assets-gallery"
      className="fixed inset-y-0 right-0 w-[440px] max-w-[90vw] bg-zinc-950 border-l border-amber-500/30 z-50 flex flex-col shadow-2xl"
    >
      {/* Header */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <div>
          <h3 className="font-bold text-lg text-amber-200">📦 الأصول المعتمدة</h3>
          <p className="text-xs text-zinc-500">{assets.length} عنصر — اضغط 📋 لنسخ ID تلقائياً</p>
        </div>
        <button
          data-testid="close-gallery-btn"
          onClick={onClose}
          className="p-1.5 hover:bg-white/10 rounded"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Filters */}
      <div className="px-4 py-2 border-b border-white/10 flex gap-2 flex-wrap">
        {[
          ['all', 'الكل'],
          ['image', 'صور'],
          ['audio', 'صوت'],
          ['video', 'فيديو'],
          ['model_3d', '3D'],
        ].map(([k, lbl]) => (
          <button
            key={k}
            data-testid={`filter-${k}`}
            onClick={() => setFilter(k)}
            className={`px-3 py-1 text-xs rounded-full ${
              filter === k
                ? 'bg-amber-500 text-zinc-900 font-semibold'
                : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
            }`}
          >
            {lbl}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading && <p className="text-center text-zinc-500 py-8">جاري التحميل…</p>}
        {!loading && filtered.length === 0 && (
          <p className="text-center text-zinc-500 py-8">لا توجد أصول معتمدة بعد. اضغط ✓ على أي صورة لإضافتها هنا.</p>
        )}
        {!loading &&
          filtered.map(a => {
            const isImg = a.type === 'image' && a.image_url;
            const url = a.image_url || a.audio_url || a.video_url || a.model_url;
            const isSelected = selected.has(a.id);
            return (
              <div
                key={a.id}
                data-testid={`gallery-asset-${a.id}`}
                className={`bg-zinc-900 rounded-lg overflow-hidden border ${
                  isSelected ? 'border-amber-400' : 'border-white/5'
                }`}
              >
                <div className="flex gap-3 p-2">
                  {/* Thumbnail */}
                  <div className="w-20 h-20 bg-zinc-800 rounded flex-shrink-0 overflow-hidden flex items-center justify-center">
                    {isImg ? (
                      <img src={`${API}${a.image_url}`} alt={a.name} className="w-full h-full object-cover" />
                    ) : (
                      <ImgIcon className="w-8 h-8 text-zinc-500" />
                    )}
                  </div>
                  {/* Info + Actions */}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-amber-200 truncate" title={a.name}>
                      {a.name || 'unnamed'}
                    </p>
                    <p className="text-[10px] text-zinc-500 mt-0.5">
                      <span className="bg-zinc-800 px-1.5 py-0.5 rounded mr-1">{a.type}</span>
                      <span>phase: {a.phase}</span>
                    </p>
                    <p className="text-[10px] text-zinc-600 mt-0.5 font-mono truncate" title={a.id}>
                      id={a.id.slice(0, 12)}…
                    </p>
                    <div className="flex gap-1 mt-1.5 flex-wrap">
                      <button
                        data-testid={`insert-ref-${a.id}`}
                        onClick={() => insertRef(a.id)}
                        className="px-2 py-0.5 text-[10px] bg-amber-500/80 hover:bg-amber-500 text-zinc-900 rounded font-semibold"
                        title="ولّد جديد بنفس الستايل"
                      >
                        🎨 REF
                      </button>
                      <button
                        data-testid={`insert-edit-${a.id}`}
                        onClick={() => insertEdit(a.id)}
                        className="px-2 py-0.5 text-[10px] bg-blue-500/80 hover:bg-blue-500 text-white rounded font-semibold"
                        title="عدّل دقيق"
                      >
                        ✏️ EDIT
                      </button>
                      <button
                        data-testid={`toggle-compose-${a.id}`}
                        onClick={() => toggleSelected(a.id)}
                        className={`px-2 py-0.5 text-[10px] rounded font-semibold ${
                          isSelected ? 'bg-emerald-500 text-zinc-900' : 'bg-zinc-700 hover:bg-zinc-600 text-zinc-200'
                        }`}
                        title="اختر للدمج"
                      >
                        {isSelected ? <Check className="inline w-3 h-3" /> : '◯'} اختيار
                      </button>
                      <button
                        data-testid={`copy-id-${a.id}`}
                        onClick={() => navigator.clipboard.writeText(a.id)}
                        className="px-2 py-0.5 text-[10px] bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded"
                        title="نسخ ID فقط"
                      >
                        <Copy className="inline w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
      </div>

      {/* Compose footer */}
      {selected.size > 0 && (
        <div className="p-3 border-t border-amber-500/30 bg-zinc-900">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs text-amber-200">
              {selected.size} عنصر محدد للدمج
            </p>
            <button
              data-testid="insert-compose-btn"
              onClick={insertCompose}
              disabled={selected.size < 2}
              className="px-3 py-1.5 text-xs bg-amber-500 hover:bg-amber-400 text-zinc-900 font-bold rounded disabled:opacity-40"
            >
              🏞️ ادمج في مشهد
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
