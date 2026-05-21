import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import {
  Users, MapPin, Package, Car, Skull, Plus, Loader2, Trash2,
  Heart, Sword, Users2, GitBranch, Coins, Sparkles, MessageSquare,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const VS = `${API}/api/video-studio`;
const auth = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
});

const KIND_META = {
  character: { label: 'بطل', icon: Users,   color: 'sky',     gradient: 'from-sky-500/15 to-sky-500/5 border-sky-500/40' },
  villain:   { label: 'شرير', icon: Skull,   color: 'rose',    gradient: 'from-rose-500/15 to-rose-500/5 border-rose-500/40' },
  location:  { label: 'مكان', icon: MapPin,  color: 'emerald', gradient: 'from-emerald-500/15 to-emerald-500/5 border-emerald-500/40' },
  prop:      { label: 'غرض', icon: Package, color: 'amber',   gradient: 'from-amber-500/15 to-amber-500/5 border-amber-500/40' },
  vehicle:   { label: 'وسيلة نقل', icon: Car, color: 'violet', gradient: 'from-violet-500/15 to-violet-500/5 border-violet-500/40' },
};

const REL_KINDS = [
  { id: 'loves',   label: 'يحب',   icon: Heart, color: 'text-rose-400' },
  { id: 'hates',   label: 'يكره',  icon: Sword, color: 'text-red-400' },
  { id: 'allies',  label: 'حليف',  icon: Users2, color: 'text-emerald-400' },
  { id: 'enemies', label: 'عدوّ',  icon: Sword, color: 'text-orange-400' },
  { id: 'family',  label: 'عائلة', icon: Users2, color: 'text-amber-400' },
  { id: 'mentor',  label: 'معلّم', icon: Users2, color: 'text-violet-400' },
  { id: 'rival',   label: 'منافس', icon: Sword, color: 'text-yellow-400' },
];

const WIZARD_STEPS = [
  { id: 'discover',      label: '١. اكتشاف الفكرة' },
  { id: 'villains',      label: '٢. فريق الأشرار' },
  { id: 'heroes',        label: '٣. فريق الأبطال' },
  { id: 'locations',     label: '٤. الأماكن' },
  { id: 'relationships', label: '٥. العلاقات' },
  { id: 'ready',         label: '٦. جاهز للسيناريو' },
];

export default function ProductionTab({ seriesId }) {
  const [kinds, setKinds] = useState([]);
  const [assets, setAssets] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [step, setStep] = useState('discover');
  const [producerReply, setProducerReply] = useState('');
  const [producerBusy, setProducerBusy] = useState(false);
  const [producerMsg, setProducerMsg] = useState('');

  // Create-asset modal
  const [newAsset, setNewAsset] = useState(null);

  // Create-relationship modal
  const [newRel, setNewRel] = useState(null);

  const reload = useCallback(async () => {
    if (!seriesId) return;
    try {
      const [kr, ar] = await Promise.all([
        fetch(`${VS}/production/asset-kinds`, { headers: auth() }),
        fetch(`${VS}/production/series/${seriesId}/assets`, { headers: auth() }),
      ]);
      const kd = await kr.json(); const ad = await ar.json();
      setKinds(kd.kinds || []);
      setAssets(ad.assets || []);
      setRelationships(ad.relationships || []);
    } catch { /* silent */ }
  }, [seriesId]);

  useEffect(() => { reload(); }, [reload]);

  const askProducer = async (msg = '') => {
    if (!seriesId) return toast.error('اختر سلسلة أولاً');
    setProducerBusy(true);
    try {
      const r = await fetch(`${VS}/production/producer-chat`, {
        method: 'POST', headers: auth(),
        body: JSON.stringify({ series_id: seriesId, step, message: msg || `أرشدني في مرحلة ${step}` }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      setProducerReply(d.reply || '');
      setProducerMsg('');
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
    finally { setProducerBusy(false); }
  };

  useEffect(() => { if (seriesId) askProducer(); /* auto-ask when step changes */ // eslint-disable-next-line
  }, [step, seriesId]);

  const createAsset = async () => {
    if (!newAsset?.name?.trim() || !newAsset?.description?.trim()) {
      return toast.error('الاسم والوصف مطلوبان');
    }
    const cost = (kinds.find((k) => k.id === newAsset.kind) || {}).cost || 0;
    if (!window.confirm(`إنشاء '${newAsset.name}' كـ${KIND_META[newAsset.kind]?.label} بتكلفة ${cost} نقطة؟`)) return;
    try {
      const r = await fetch(`${VS}/production/asset`, {
        method: 'POST', headers: auth(),
        body: JSON.stringify({
          series_id: seriesId,
          kind: newAsset.kind,
          name: newAsset.name,
          description: newAsset.description,
          art_style: newAsset.art_style || 'hyperreal',
          attributes: {},
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      toast.success(`تم إنشاء ${newAsset.name} · خُصم ${d.credits_charged} نقطة`);
      setNewAsset(null);
      reload();
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
  };

  const deleteAsset = async (id) => {
    if (!window.confirm('حذف هذا الأصل؟ (لن يُسترجع، ولن تُعاد النقاط)')) return;
    try {
      await fetch(`${VS}/production/asset/${id}`, { method: 'DELETE', headers: auth() });
      reload();
    } catch { toast.error('فشل الحذف'); }
  };

  const createRel = async () => {
    if (!newRel?.from_asset_id || !newRel?.to_asset_id || !newRel?.kind) return;
    try {
      const r = await fetch(`${VS}/production/relationship`, {
        method: 'POST', headers: auth(),
        body: JSON.stringify({ series_id: seriesId, ...newRel }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      toast.success('تمت إضافة العلاقة');
      setNewRel(null);
      reload();
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
  };

  if (!seriesId) {
    return (
      <div className="p-8 text-center text-sm text-zinc-500">
        اختر سلسلة من الجنب أو أنشئ واحدة عشان تبدأ بناء عالمك.
      </div>
    );
  }

  const assetsByKind = (k) => assets.filter((a) => a.kind === k);

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-5" data-testid="production-tab">
      {/* ── Wizard steps ─────────────────────────────────────────── */}
      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-4">
        <div className="text-xs text-zinc-500 mb-3 flex items-center gap-2">
          <GitBranch className="w-3.5 h-3.5" /> رحلة بناء العالم
        </div>
        <div className="flex items-center gap-1 overflow-x-auto pb-1">
          {WIZARD_STEPS.map((s) => (
            <button key={s.id} onClick={() => setStep(s.id)}
              className={`text-xs px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
                step === s.id ? 'bg-amber-500 text-black font-semibold' : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300'
              }`} data-testid={`wizard-step-${s.id}`}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Producer AI reply ────────────────────────────────────── */}
      <div className="bg-gradient-to-br from-amber-500/10 to-violet-500/10 border border-amber-500/30 rounded-2xl p-4" data-testid="producer-chat">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-amber-300" />
          <span className="text-sm font-semibold text-amber-200">المنتج التنفيذي بزيتاكس</span>
          {producerBusy && <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-300" />}
        </div>
        <div className="text-sm text-zinc-200 leading-7 whitespace-pre-wrap min-h-[80px]" data-testid="producer-reply">
          {producerReply || (producerBusy ? 'يستشير عالمك…' : 'اضغط أي مرحلة من فوق وراح أرشدك خطوة بخطوة.')}
        </div>
        <div className="flex gap-2 mt-3">
          <input
            value={producerMsg}
            onChange={(e) => setProducerMsg(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && askProducer(producerMsg)}
            disabled={producerBusy}
            className="flex-1 bg-zinc-900 border border-amber-500/30 rounded-lg px-3 py-1.5 text-sm"
            placeholder="اسأل المنتج أو وصف فكرتك…"
            data-testid="producer-msg-input"
          />
          <button onClick={() => askProducer(producerMsg)} disabled={producerBusy || !producerMsg.trim()}
            className="bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black font-medium px-4 rounded-lg text-sm flex items-center gap-1.5"
            data-testid="producer-send-btn">
            <MessageSquare className="w-3.5 h-3.5" /> اسأل
          </button>
        </div>
      </div>

      {/* ── Asset gallery by kind ────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(KIND_META).map(([kind, meta]) => {
          const Icon = meta.icon;
          const items = assetsByKind(kind);
          const cost = (kinds.find((k) => k.id === kind) || {}).cost || 0;
          return (
            <div key={kind} className={`bg-gradient-to-br ${meta.gradient} border rounded-2xl p-4`} data-testid={`assets-group-${kind}`}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Icon className={`w-5 h-5 text-${meta.color}-300`} />
                  <h3 className="font-semibold text-sm">{meta.label} <span className="text-zinc-500 text-xs">({items.length})</span></h3>
                </div>
                <button onClick={() => setNewAsset({ kind, name: '', description: '', art_style: 'hyperreal' })}
                  className="text-xs bg-black/40 hover:bg-black/60 px-2.5 py-1 rounded-lg flex items-center gap-1"
                  data-testid={`add-${kind}-btn`}>
                  <Plus className="w-3 h-3" /> أضف <span className="text-amber-300">({cost} ن)</span>
                </button>
              </div>
              {items.length === 0 ? (
                <div className="text-xs text-zinc-500 text-center py-6">ما فيه {meta.label} بعد.</div>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  {items.map((a) => (
                    <div key={a.id} className="bg-black/40 rounded-lg overflow-hidden group relative" data-testid={`asset-${a.id}`}>
                      <div className="aspect-square bg-zinc-900">
                        {a.image_url ? (
                          <img src={`${API}${a.image_url}`} alt={a.name} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-zinc-600">
                            <Icon className="w-6 h-6" />
                          </div>
                        )}
                      </div>
                      <div className="p-2">
                        <div className="text-xs font-medium truncate">{a.name}</div>
                        <div className="text-[10px] text-zinc-400 line-clamp-2 leading-4">{a.description}</div>
                      </div>
                      <button onClick={() => deleteAsset(a.id)}
                        className="absolute top-1 left-1 bg-black/80 hover:bg-rose-500/80 opacity-0 group-hover:opacity-100 transition p-1 rounded">
                        <Trash2 className="w-3 h-3 text-white" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Relationships ───────────────────────────────────────── */}
      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-4" data-testid="relationships-section">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-violet-300" />
            <h3 className="font-semibold text-sm">خريطة العلاقات <span className="text-zinc-500 text-xs">({relationships.length})</span></h3>
          </div>
          <button onClick={() => setNewRel({ from_asset_id: '', to_asset_id: '', kind: 'loves', notes: '' })}
            className="text-xs bg-violet-500/30 hover:bg-violet-500/50 text-violet-100 px-2.5 py-1 rounded-lg flex items-center gap-1"
            data-testid="add-relationship-btn">
            <Plus className="w-3 h-3" /> أضف علاقة (مجاناً)
          </button>
        </div>
        {relationships.length === 0 ? (
          <div className="text-xs text-zinc-500 text-center py-6">ابنِ علاقات بين الشخصيات لتعميق الحبكة.</div>
        ) : (
          <div className="space-y-2">
            {relationships.map((r) => {
              const a = assets.find((x) => x.id === r.from_asset_id);
              const b = assets.find((x) => x.id === r.to_asset_id);
              const rk = REL_KINDS.find((x) => x.id === r.kind);
              return (
                <div key={r.id} className="flex items-center gap-3 text-sm bg-zinc-900/60 rounded-lg p-2">
                  <span className="text-zinc-200 font-medium">{a?.name || '?'}</span>
                  <span className={`${rk?.color} font-semibold text-xs`}>{rk?.label || r.kind}</span>
                  <span className="text-zinc-200 font-medium">{b?.name || '?'}</span>
                  {r.notes && <span className="text-zinc-500 text-xs truncate">— {r.notes}</span>}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Create-asset modal ──────────────────────────────────── */}
      {newAsset && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur z-50 flex items-center justify-center p-4">
          <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-6 w-full max-w-md" data-testid="new-asset-modal">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Plus className="w-5 h-5 text-amber-400" /> {KIND_META[newAsset.kind]?.label} جديد
            </h2>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-zinc-400 block mb-1">الاسم</label>
                <input value={newAsset.name} onChange={(e) => setNewAsset((a) => ({ ...a, name: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                  placeholder={newAsset.kind === 'villain' ? 'مثلاً: الخادم الأسود' : 'مثلاً: سالم'}
                  data-testid="asset-name-input" />
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">الوصف التفصيلي</label>
                <textarea value={newAsset.description} onChange={(e) => setNewAsset((a) => ({ ...a, description: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm h-28"
                  placeholder="شاب 25، شعر أسود قصير، ندبة فوق العين اليسرى، يلبس معطفاً جلدياً داكناً..."
                  data-testid="asset-desc-input" />
              </div>
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-xs flex items-center gap-2">
                <Coins className="w-4 h-4 text-amber-300" />
                <span className="text-amber-200">التكلفة: {(kinds.find((k) => k.id === newAsset.kind) || {}).cost || 0} نقطة (يُخصم فوراً بعد الإنشاء).</span>
              </div>
              <div className="flex gap-2 pt-2">
                <button onClick={createAsset}
                  className="flex-1 bg-amber-500 hover:bg-amber-400 text-black font-medium py-2 rounded-lg text-sm"
                  data-testid="confirm-create-asset-btn">إنشاء</button>
                <button onClick={() => setNewAsset(null)}
                  className="px-4 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm">إلغاء</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Create-relationship modal ───────────────────────────── */}
      {newRel && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur z-50 flex items-center justify-center p-4">
          <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-6 w-full max-w-md" data-testid="new-rel-modal">
            <h2 className="text-lg font-semibold mb-4">علاقة جديدة</h2>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-zinc-400 block mb-1">من</label>
                <select value={newRel.from_asset_id} onChange={(e) => setNewRel((r) => ({ ...r, from_asset_id: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm" data-testid="rel-from-select">
                  <option value="">— اختر —</option>
                  {assets.map((a) => <option key={a.id} value={a.id}>{a.name} ({KIND_META[a.kind]?.label})</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">العلاقة</label>
                <select value={newRel.kind} onChange={(e) => setNewRel((r) => ({ ...r, kind: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm" data-testid="rel-kind-select">
                  {REL_KINDS.map((k) => <option key={k.id} value={k.id}>{k.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">إلى</label>
                <select value={newRel.to_asset_id} onChange={(e) => setNewRel((r) => ({ ...r, to_asset_id: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm" data-testid="rel-to-select">
                  <option value="">— اختر —</option>
                  {assets.filter((a) => a.id !== newRel.from_asset_id).map((a) => <option key={a.id} value={a.id}>{a.name} ({KIND_META[a.kind]?.label})</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">ملاحظات (اختياري)</label>
                <input value={newRel.notes} onChange={(e) => setNewRel((r) => ({ ...r, notes: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                  placeholder="منذ الطفولة، عداوة قديمة، …" />
              </div>
              <div className="flex gap-2 pt-2">
                <button onClick={createRel} className="flex-1 bg-violet-500 hover:bg-violet-400 text-white font-medium py-2 rounded-lg text-sm" data-testid="confirm-create-rel-btn">إضافة</button>
                <button onClick={() => setNewRel(null)} className="px-4 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm">إلغاء</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
