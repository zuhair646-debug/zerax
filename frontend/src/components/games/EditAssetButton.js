import { useState } from 'react';
import { Pencil, Loader2, X } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * ✏️ Edit-image dialog. Calls /asset/{id}/edit (Flux Pro Redux img2img).
 * Spawns a NEW asset (original preserved) for user review.
 */
export default function EditAssetButton({ projectId, assetId, accentColor = 'amber', onEdited }) {
  const token = localStorage.getItem('token');
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);

  const accent = {
    amber: 'bg-amber-500 hover:bg-amber-400 border-amber-400 text-amber-950',
    blue: 'bg-blue-500 hover:bg-blue-400 border-blue-400 text-blue-950',
  }[accentColor] || 'bg-amber-500 hover:bg-amber-400 border-amber-400 text-amber-950';

  const submit = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/asset/${assetId}/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ edit_prompt: prompt.trim() }),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        throw new Error(e.detail || 'edit failed');
      }
      const d = await r.json();
      toast.success('✨ تم توليد النسخة المعدّلة — راح تشوفها في "المعتمدات" بانتظار اعتمادك');
      setOpen(false);
      setPrompt('');
      onEdited?.(d.asset);
    } catch (e) {
      toast.error(`فشل التعديل: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(true); }}
        data-testid={`edit-asset-${assetId}`}
        title="عدّل هذه الصورة بـ AI"
        className="absolute top-1.5 right-1.5 z-10 w-7 h-7 rounded-md bg-black/70 hover:bg-amber-500/80 border border-white/20 text-white opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
      >
        <Pencil className="w-3.5 h-3.5" />
      </button>

      {open && (
        <div className="fixed inset-0 z-[60] bg-black/80 flex items-center justify-center p-4" onClick={(e) => e.stopPropagation()}>
          <div dir="rtl" className="bg-zinc-950 border border-amber-500/30 rounded-2xl p-6 max-w-lg w-full" data-testid="edit-asset-dialog">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center text-amber-300">
                  <Pencil className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-white">عدّل الصورة بـ AI</h3>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-300 flex items-center justify-center">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-zinc-400 mb-3">
              صف التعديل اللي تبيه (مثلاً: "خل الإضاءة أكثر دفء"، "أضف ضباب خلف القلعة"، "غيّر اللون لأزرق ليلي").
              النسخة الأصلية تبقى محفوظة.
            </p>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="مثلاً: غيّر الإضاءة من نهار لـ غروب دافئ بألوان برتقالية..."
              rows={4}
              data-testid="edit-prompt-input"
              className="w-full bg-black/40 border border-white/10 rounded-lg p-3 text-sm text-white outline-none focus:border-amber-500/50 resize-none"
              autoFocus
            />
            <div className="flex items-center justify-end gap-2 mt-4">
              <button type="button" onClick={() => setOpen(false)} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-300 text-sm font-bold">
                إلغاء
              </button>
              <button type="button" onClick={submit} disabled={loading || !prompt.trim()}
                data-testid="submit-edit"
                className={`px-4 py-2 rounded-lg ${accent} border text-sm font-bold flex items-center gap-2 disabled:opacity-50`}>
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Pencil className="w-3.5 h-3.5" />}
                <span>{loading ? 'جاري التوليد...' : 'ولّد النسخة المعدّلة'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
