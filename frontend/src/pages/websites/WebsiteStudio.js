import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Sparkles, Eye, Download, ArrowLeft, Plus, FolderOpen,
  Send, Trash2, X, Code2, Check, Maximize2, Minimize2,
  MessageSquare, Monitor, RefreshCw, Copy, ExternalLink,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

/* ================================================================
   CATEGORY PICKER — first stage of empty state
   ================================================================ */
function CategoryPicker({ categories, onPick }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-start p-4 md:p-6 overflow-y-auto" data-testid="category-picker">
      <div className="text-center mb-6 max-w-xl pt-4">
        <Sparkles className="w-12 h-12 mx-auto mb-3 text-yellow-500" />
        <h2 className="text-2xl md:text-4xl font-black mb-2 bg-gradient-to-r from-yellow-300 via-yellow-500 to-orange-400 bg-clip-text text-transparent">اختر نوع موقعك</h2>
        <p className="text-white/60 text-xs md:text-sm">{categories.length} فئة • داخل كل فئة قوالب مبتكرة بصور وألوان وإطارات مختلفة</p>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 md:gap-4 w-full max-w-7xl">
        {categories.map((c) => (
          <button
            key={c.id}
            onClick={() => onPick(c)}
            className="group relative overflow-hidden rounded-2xl border border-white/10 hover:border-yellow-400/70 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl hover:shadow-yellow-500/20 aspect-[4/5] bg-slate-900"
            data-testid={`category-card-${c.id}`}
          >
            {c.image && (
              <div
                className="absolute inset-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-110"
                style={{ backgroundImage: `url('${c.image}')` }}
                aria-hidden
              />
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-black/10 group-hover:via-black/30" />
            <div
              className="absolute inset-0 opacity-0 group-hover:opacity-40 transition-opacity mix-blend-overlay"
              style={{ background: `linear-gradient(135deg, ${c.color}, transparent 70%)` }}
              aria-hidden
            />
            <div className="absolute inset-0 flex flex-col justify-between p-3 md:p-4 text-right">
              <div className="flex items-start justify-between">
                <div
                  className="w-10 h-10 md:w-11 md:h-11 rounded-xl flex items-center justify-center text-xl md:text-2xl backdrop-blur-md shadow-lg"
                  style={{ background: `${c.color}cc`, color: '#fff' }}
                >
                  {c.icon}
                </div>
                <span className="text-[10px] opacity-80 bg-black/50 backdrop-blur px-2 py-0.5 rounded-full border border-white/10">
                  {c.layouts_count} تصميم
                </span>
              </div>
              <div>
                <div className="font-black text-base md:text-lg text-white mb-0.5 drop-shadow-lg leading-tight group-hover:text-yellow-300 transition">
                  {c.name}
                </div>
                <div className="text-[11px] opacity-80 text-white/90 flex items-center gap-1">
                  <span>اختر الآن</span>
                  <span className="transition-transform group-hover:-translate-x-1">←</span>
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ================================================================
   LAYOUT BROWSER — stage 2: gallery + live preview + confirm
   ================================================================ */
function LayoutBrowser({ category, layouts, onBack, onConfirm, loading }) {
  const [selected, setSelected] = useState(layouts[0] || null);
  const [html, setHtml] = useState('');
  const [htmlLoading, setHtmlLoading] = useState(false);
  const [mixing, setMixing] = useState(false);

  useEffect(() => { if (layouts?.length && !selected) setSelected(layouts[0]); }, [layouts, selected]);

  useEffect(() => {
    if (!category?.id || !selected?.id) return;
    setHtmlLoading(true);
    fetch(`${API}/api/websites/categories/${category.id}/layouts/${selected.id}/preview-html`)
      .then((r) => r.json()).then((d) => setHtml(d.html || '')).finally(() => setHtmlLoading(false));
  }, [category?.id, selected?.id]);

  const mix = async () => {
    if (!category?.id) return;
    setMixing(true);
    try {
      const r = await fetch(`${API}/api/websites/categories/${category.id}/mix`);
      const d = await r.json();
      if (d.layout) {
        // Find the full layout object from `layouts` to include theme
        const found = layouts.find((L) => L.id === d.layout.id);
        setSelected(found || { ...d.layout, theme: {} });
        setHtml(d.html || '');
        toast.success(`🎲 تم اقتراح: ${d.layout.name}`);
      }
    } catch (_) { toast.error('فشل الخلط'); }
    finally { setMixing(false); }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0" data-testid="layout-browser">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 md:px-4 py-2.5 bg-[#0a0e1c] border-b border-white/10">
        <button onClick={onBack} className="p-1.5 hover:bg-white/10 rounded-lg" data-testid="back-to-categories-btn">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <span className="text-xl">{category?.icon}</span>
        <span className="font-bold text-sm md:text-base">{category?.name}</span>
        <span className="text-xs opacity-60">• {layouts.length} تصميم</span>
        <div className="flex-1" />
        <button
          onClick={mix}
          disabled={mixing || loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-purple-500/30 to-pink-500/30 hover:from-purple-500/50 hover:to-pink-500/50 border border-purple-400/40 rounded-lg text-xs font-bold disabled:opacity-50"
          title="اخلط تصميم عشوائي مبتكر"
          data-testid="mix-dna-btn"
        >{mixing ? <RefreshCw className="w-4 h-4 animate-spin" /> : '🎲'} اخلط تصميم</button>
        <button
          onClick={() => selected && onConfirm(selected)}
          disabled={!selected || loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-green-500 to-emerald-500 text-black rounded-lg text-xs font-bold disabled:opacity-40"
          data-testid="confirm-layout-btn"
        ><Check className="w-4 h-4" />هل أنت متأكد؟ اعتمد</button>
      </div>

      {/* Body */}
      <div className="flex-1 flex min-h-0 flex-col md:flex-row">
        {/* Layouts list */}
        <aside className="md:w-64 md:shrink-0 max-h-[200px] md:max-h-none overflow-auto bg-[#0e1128] border-b md:border-b-0 md:border-s border-white/10 p-2">
          <div className="grid grid-cols-2 md:grid-cols-1 gap-1.5">
            {layouts.map((L) => (
              <button
                key={L.id}
                onClick={() => setSelected(L)}
                className={`text-right p-2.5 rounded-lg border transition-all ${
                  selected?.id === L.id
                    ? 'bg-yellow-500/20 border-yellow-500/70 shadow-lg shadow-yellow-500/10'
                    : 'bg-white/5 border-white/10 hover:border-yellow-400/40'
                }`}
                data-testid={`layout-${L.id}`}
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="text-base">{L.icon}</span>
                  <span className="font-bold text-xs md:text-sm truncate flex-1">{L.name}</span>
                  {L.density && (
                    <span className="text-[9px] px-1.5 py-0.5 bg-white/10 rounded-full opacity-70">{L.density}</span>
                  )}
                </div>
                <div className="text-[10px] opacity-60 leading-relaxed line-clamp-2">{L.description}</div>
                <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                  <span className="text-[9px] px-1.5 py-0.5 bg-yellow-500/15 text-yellow-300 rounded">
                    {L.sections_count || 0} قسم
                  </span>
                  {L.hero_layout && (
                    <span className="text-[9px] px-1.5 py-0.5 bg-purple-500/15 text-purple-300 rounded">
                      hero: {L.hero_layout}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </aside>

        {/* Live preview */}
        <div className="flex-1 flex flex-col min-h-0 bg-[#050815] p-2">
          <div className="text-xs opacity-70 mb-1.5 px-1 flex items-center gap-1.5">
            <Eye className="w-3.5 h-3.5 text-yellow-500" />
            معاينة حيّة • {selected?.name || '—'}
            {htmlLoading && <span className="opacity-60">• جاري التحميل...</span>}
          </div>
          <iframe
            key={selected?.id}
            srcDoc={html}
            className="flex-1 w-full bg-white rounded-lg shadow-2xl"
            sandbox="allow-scripts allow-same-origin"
            title="layout-preview"
            data-testid="layout-preview-iframe"
          />
          <div className="mt-2 text-[11px] opacity-60 text-center">تصفّح تصاميم أخرى بحرّية — اضغط "اعتمد" عندما تختار</div>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   STEP RENDERERS — inline rich UI inside chat for the active step
   ================================================================ */
function VariantPicker({ variants, onPick, loading }) {
  if (!variants?.length) return null;
  return (
    <div className="grid grid-cols-2 gap-2" data-testid="inline-variants">
      {variants.map((v) => (
        <button
          key={v.id}
          onClick={() => onPick(v.id)}
          disabled={loading}
          className="p-2.5 rounded-xl border border-white/10 hover:border-yellow-400/60 transition-all text-right disabled:opacity-50 hover:scale-[1.02]"
          data-testid={`inline-variant-${v.id}`}
          style={{ background: `linear-gradient(135deg, ${v.theme.primary}22, ${v.theme.secondary}cc)` }}
        >
          <div className="flex gap-1 mb-1.5">
            {['primary', 'accent', 'secondary'].map((k) => (
              <span key={k} className="w-3.5 h-3.5 rounded-full border border-white/30 shadow-sm"
                style={{ background: v.theme[k] || '#000' }} />
            ))}
          </div>
          <div className="text-xs font-bold truncate text-white">{v.name}</div>
        </button>
      ))}
    </div>
  );
}

function ButtonShapePicker({ onPick, loading }) {
  const shapes = [
    { id: 'pill',    label: 'دائرية',    value: 'full',   radius: '999px' },
    { id: 'rounded', label: 'ناعمة',     value: 'large',  radius: '18px' },
    { id: 'medium',  label: 'متوسطة',    value: 'medium', radius: '10px' },
    { id: 'sharp',   label: 'حادة',      value: 'none',   radius: '2px' },
  ];
  return (
    <div className="grid grid-cols-2 gap-2" data-testid="inline-buttons">
      {shapes.map((s) => (
        <button
          key={s.id}
          onClick={() => onPick(s.value)}
          disabled={loading}
          className="flex flex-col items-center gap-2 p-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-yellow-400/60 transition-all disabled:opacity-50"
          data-testid={`inline-btn-${s.id}`}
        >
          <span className="px-5 py-1.5 bg-gradient-to-r from-yellow-500 to-orange-500 text-black text-xs font-bold"
            style={{ borderRadius: s.radius }}>زر</span>
          <span className="text-xs font-bold opacity-80">{s.label}</span>
        </button>
      ))}
    </div>
  );
}

function ColorPicker({ onPick, loading }) {
  const moods = [
    { id: 'classic',  label: 'كلاسيكي',  colors: ['#D4AF37', '#1a1f3a', '#8B0000'] },
    { id: 'modern',   label: 'عصري',     colors: ['#3B82F6', '#0f172a', '#22D3EE'] },
    { id: 'warm',     label: 'دافئ',      colors: ['#F59E0B', '#18181b', '#EF4444'] },
    { id: 'luxury',   label: 'فاخر',      colors: ['#D4AF37', '#0a0a0a', '#B8860B'] },
    { id: 'dark_pro', label: 'داكن احترافي', colors: ['#06B6D4', '#020617', '#F59E0B'] },
    { id: 'nature',   label: 'طبيعي',     colors: ['#10B981', '#064e3b', '#F59E0B'] },
    { id: 'pastel',   label: 'باستيل',    colors: ['#A78BFA', '#FDF2F8', '#F472B6'] },
    { id: 'bold',     label: 'جريء',      colors: ['#DC2626', '#18181b', '#FBBF24'] },
  ];
  return (
    <div className="grid grid-cols-2 gap-2" data-testid="inline-colors">
      {moods.map((m) => (
        <button
          key={m.id}
          onClick={() => onPick(m.id)}
          disabled={loading}
          className="flex items-center gap-2 p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-yellow-400/60 transition-all disabled:opacity-50"
          data-testid={`inline-color-${m.id}`}
        >
          <div className="flex gap-0.5">
            {m.colors.map((c, i) => (
              <span key={i} className="w-4 h-7 first:rounded-s-md last:rounded-e-md border border-white/10" style={{ background: c }} />
            ))}
          </div>
          <span className="text-xs font-bold flex-1 text-right truncate">{m.label}</span>
        </button>
      ))}
    </div>
  );
}

function FontPicker({ onPick, loading }) {
  const fonts = [
    { id: 'Tajawal', sample: 'Zitex — منصة عصرية', desc: 'متوازن' },
    { id: 'Cairo', sample: 'Zitex — واضح وعملي', desc: 'واضح' },
    { id: 'Amiri', sample: 'Zitex — فخم كلاسيكي', desc: 'فخم' },
    { id: 'Readex Pro', sample: 'Zitex — ناعم حديث', desc: 'حديث' },
    { id: 'Almarai', sample: 'Zitex — نظيف بسيط', desc: 'بسيط' },
  ];
  return (
    <div className="grid grid-cols-1 gap-1.5" data-testid="inline-fonts">
      {fonts.map((f) => (
        <button
          key={f.id}
          onClick={() => onPick(f.id)}
          disabled={loading}
          className="flex items-center gap-2 p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-yellow-400/60 transition-all disabled:opacity-50 text-right"
          data-testid={`inline-font-${f.id}`}
        >
          <span className="text-base truncate flex-1" style={{ fontFamily: f.id }}>{f.sample}</span>
          <span className="text-[10px] opacity-60 bg-white/10 px-2 py-0.5 rounded-full shrink-0">{f.desc}</span>
        </button>
      ))}
    </div>
  );
}

function ChipGroup({ chips, multi, onSingle, onMulti, loading, selected, setSelected }) {
  if (!chips?.length) return null;
  const toggleMulti = (id) => {
    const next = selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id];
    setSelected(next);
    // Auto-preview on every toggle
    onMulti(next);
  };
  return (
    <div>
      {multi && selected.length > 0 && (
        <div className="mb-1.5 text-[11px] opacity-70">المحدّد: {selected.length} — المعاينة تتحدّث فوراً</div>
      )}
      <div className="flex flex-wrap gap-1.5">
        {chips.map((c) => {
          const id = c.id || c.value;
          const isSel = multi && selected.includes(id);
          return (
            <button
              key={id}
              onClick={() => multi
                ? toggleMulti(id)
                : onSingle(c.value !== undefined ? c.value : id)}
              disabled={loading}
              className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all disabled:opacity-50 ${
                isSel
                  ? 'bg-yellow-500 border-yellow-500 text-black'
                  : 'bg-white/5 border-white/15 hover:bg-yellow-500/20 hover:border-yellow-500/50'
              }`}
              data-testid={`chip-${id}`}
            >{c.label}</button>
          );
        })}
      </div>
    </div>
  );
}

/* ================================================================
   INLINE STEP — rich picker rendered at the bottom of the chat
   ================================================================ */
function InlineStepRenderer({ step, variants, loading, onAnswer, selected, setSelected, project }) {
  const [aiBrief, setAiBrief] = useState('');
  const [aiBusy, setAiBusy] = useState(false);
  if (!step) return null;
  const render = step.render || 'chips';
  const handleSingle = (v) => onAnswer(v);
  const handleMulti = (ids) => onAnswer(ids);

  // 🆕 AI custom design — when user picks ai_custom in a style_<widget> step
  const isStyleStep = step.id?.startsWith('style_');
  const aiPicked = isStyleStep && selected === 'ai_custom';
  const submitAi = async () => {
    if (!aiBrief.trim() || !project?.id || !step.widget_id) return;
    setAiBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/widget-ai-design`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({ widget_id: step.widget_id, brief: aiBrief }),
      });
      if (!r.ok) throw new Error('AI failed');
      toast.success('🤖 تم تصميم الـwidget بمزاجك!');
      onAnswer('ai_custom');  // advance wizard
    } catch (_) {
      toast.error('فشل التصميم — جرّب وصفاً آخر');
    } finally {
      setAiBusy(false);
    }
  };

  if (render === 'variants') {
    return <VariantPicker variants={variants} onPick={handleSingle} loading={loading} />;
  }

  // Custom rich renderers for specific steps
  if (step.id === 'buttons') return <ButtonShapePicker onPick={handleSingle} loading={loading} />;
  if (step.id === 'colors')  return <ColorPicker       onPick={handleSingle} loading={loading} />;
  if (step.id === 'typography') return <FontPicker     onPick={handleSingle} loading={loading} />;

  // Default chip renderer + AI brief textarea when ai_custom is selected
  return (
    <div className="space-y-2">
      <ChipGroup
        chips={step.chips || []}
        multi={!!step.multi}
        loading={loading}
        onSingle={(v) => {
          if (v === 'ai_custom' && isStyleStep) {
            setSelected(v);  // mark selection but don't advance — wait for brief
            return;
          }
          handleSingle(v);
        }}
        onMulti={handleMulti}
        selected={selected}
        setSelected={setSelected}
      />
      {aiPicked && (
        <div className="mx-3 p-3 bg-gradient-to-br from-fuchsia-500/15 to-purple-500/15 border border-fuchsia-400/30 rounded-xl" data-testid="ai-brief-box">
          <div className="text-xs font-black text-fuchsia-200 mb-2">🤖 صف لي شكل الـwidget الذي تريده — وسأصممه لك:</div>
          <textarea
            value={aiBrief}
            onChange={(e) => setAiBrief(e.target.value)}
            placeholder="مثال: أبيها ذهبية فخمة بحدود ناعمة وتأثير glow، شكل دائري كبير لافت للنظر..."
            className="w-full min-h-[70px] p-2 bg-black/30 border border-white/10 rounded-lg text-sm focus:border-fuchsia-400 focus:outline-none"
            data-testid="ai-brief-input"
            dir="rtl"
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={submitAi}
              disabled={!aiBrief.trim() || aiBusy}
              className="flex-1 py-2 rounded-lg bg-gradient-to-r from-fuchsia-500 to-purple-500 hover:from-fuchsia-600 hover:to-purple-600 text-sm font-black disabled:opacity-50"
              data-testid="ai-brief-submit"
            >
              {aiBusy ? '⏳ يصمم...' : '✨ صمّم بالذكاء الاصطناعي'}
            </button>
            <button
              onClick={() => setSelected(null)}
              className="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-xs"
              data-testid="ai-brief-cancel"
            >
              ↩
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ================================================================
   PROPOSAL CARDS — 4 distinctive design proposals shown in-chat
   ================================================================ */
function ProposalCards({ proposals, onPick, onDismiss, loading }) {
  if (loading) {
    return (
      <div className="mx-3 my-2 p-3 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/30 rounded-xl text-center" data-testid="proposals-loading">
        <div className="text-xs opacity-80 flex items-center justify-center gap-2"><RefreshCw className="w-3.5 h-3.5 animate-spin" /> جاري تجهيز 4 تصاميم متنوعة لك...</div>
      </div>
    );
  }
  if (!proposals || proposals.length === 0) return null;
  return (
    <div className="mx-3 my-2 p-3 bg-gradient-to-br from-purple-500/10 to-pink-500/5 border border-purple-500/30 rounded-xl" data-testid="proposals-cards">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-black text-purple-200">💡 4 تصاميم متنوعة — اختر واحداً لتطبيقه فوراً</div>
        <button onClick={onDismiss} className="p-0.5 hover:bg-white/10 rounded" data-testid="dismiss-proposals"><X className="w-3 h-3" /></button>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {proposals.map((p) => (
          <button
            key={p.id}
            onClick={() => onPick(p)}
            className="group relative rounded-lg overflow-hidden border border-white/15 hover:border-purple-400 transition-all text-right"
            data-testid={`proposal-${p.mood_id}`}
            style={{ background: `linear-gradient(135deg, ${p.palette.primary}22, ${p.palette.accent}22)` }}
          >
            <div className="p-2.5">
              <div className="flex items-center gap-1 mb-1.5">
                <div className="w-3 h-3 rounded-full border border-white/30" style={{ background: p.palette.primary }} />
                <div className="w-3 h-3 rounded-full border border-white/30" style={{ background: p.palette.accent }} />
                <div className="w-3 h-3 rounded-full border border-white/30" style={{ background: p.palette.secondary }} />
              </div>
              <div className="text-xs font-black text-white">{p.name}</div>
              <div className="text-[10px] opacity-60 truncate">{p.layout_name || p.tagline || p.mood_id}</div>
              <div className="text-[10px] opacity-50 mt-1">خط: {p.font || '—'}</div>
            </div>
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition">
              <span className="px-3 py-1 bg-white text-black rounded-full text-[10px] font-black">✓ تطبيق هذا</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ================================================================
   QUICK ADD BAR — smart one-click chips under the chat input
   ================================================================ */
const QUICK_ADD_CHIPS = [
  { id: 'propose',       icon: '💡', label: 'اقترح تصاميم',  msg: '__PROPOSE_DESIGNS__', special: 'propose' },
  { id: 'stories',       icon: '🎬', label: 'حالات',        msg: 'أضف قسم حالات' },
  { id: 'banner',        icon: '📢', label: 'بنر',          msg: 'أضف بنر ترويجي' },
  { id: 'video',         icon: '🎥', label: 'فيديو',         msg: 'أضف قسم فيديو' },
  { id: 'gallery',       icon: '🖼️', label: 'معرض',          msg: 'أضف قسم معرض صور' },
  { id: 'testimonials',  icon: '💬', label: 'آراء',           msg: 'أضف قسم آراء العملاء' },
  { id: 'pricing',       icon: '💰', label: 'أسعار',          msg: 'أضف قسم خطط الأسعار' },
  { id: 'faq',           icon: '❓', label: 'أسئلة شائعة',    msg: 'أضف قسم الأسئلة الشائعة' },
  { id: 'team',          icon: '👥', label: 'الفريق',         msg: 'أضف قسم الفريق' },
  { id: 'stats_band',    icon: '📊', label: 'إحصائيات',      msg: 'أضف شريط إحصائيات' },
  { id: 'newsletter',    icon: '📧', label: 'نشرة بريدية',   msg: 'أضف نشرة بريدية' },
  { id: 'announce',      icon: '🔔', label: 'شريط إعلان',    msg: 'أضف شريط إعلان علوي' },
  { id: 'contact',       icon: '📞', label: 'تواصل',          msg: 'أضف قسم تواصل معنا' },
];

function QuickAddBar({ onPick, loading }) {
  return (
    <div className="px-3 py-2 border-t border-white/10 bg-gradient-to-b from-[#0a0e1c] to-[#0e1128]" data-testid="quick-add-bar">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-[10px] font-bold opacity-60 uppercase tracking-wide">⚡ اقتراحات ذكية — ضغطة لإضافة قسم</span>
      </div>
      <div className="flex gap-1.5 overflow-x-auto pb-1" style={{ scrollbarWidth: 'thin' }}>
        {QUICK_ADD_CHIPS.map((c) => (
          <button
            key={c.id}
            onClick={() => onPick(c.msg)}
            disabled={loading}
            className="shrink-0 flex items-center gap-1 px-2.5 py-1.5 bg-white/5 hover:bg-yellow-500/20 border border-white/10 hover:border-yellow-500/50 rounded-full text-[11px] font-bold transition-all disabled:opacity-40 whitespace-nowrap"
            data-testid={`quick-chip-${c.id}`}
            title={c.msg}
          >
            <span>{c.icon}</span>
            <span>{c.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ================================================================
   CHAT COLUMN — messages + inline rich step + free input
   ================================================================ */
function ChatColumn({ project, stepMeta, variants, loading, onSendText, onAnswerStep, onRequestCode, pending, onConfirm, onCancel, proposals, proposalsLoading, onPickProposal, onDismissProposals }) {
  const [msg, setMsg] = useState('');
  const [selected, setSelected] = useState([]);
  const endRef = useRef(null);
  const messages = project?.chat || [];
  const stepId = project?.wizard?.step;

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages.length, stepId]);
  useEffect(() => { setSelected([]); }, [stepId]);

  const send = async () => {
    if (!msg.trim() || loading) return;
    const m = msg.trim();
    setMsg('');
    await onSendText(m);
  };

  return (
    <div className="flex flex-col h-full bg-[#0e1128] border-s border-white/10" data-testid="chat-column">
      {/* Header */}
      <div className="px-3 py-2.5 border-b border-white/10 flex items-center gap-2 bg-[#0a0e1c]">
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-yellow-500 to-orange-500 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-black" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-sm">مستشار Zitex</div>
          <div className="text-[10px] opacity-60">{project?.wizard?.completed?.length || 0} من 11 خطوة</div>
        </div>
        <button
          onClick={onRequestCode}
          className="flex items-center gap-1 px-2 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-[11px] font-bold border border-white/10"
          title="طلب الكود والاستقلالية"
          data-testid="independence-btn"
        ><Code2 className="w-3 h-3" />استقلالية</button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5 min-h-0">
        {messages.length === 0 ? (
          <div className="text-center text-white/50 py-6">
            <Sparkles className="w-8 h-8 mx-auto mb-2 text-yellow-500" />
            <div className="text-sm">المستشار جاهز</div>
          </div>
        ) : (
          messages.slice(-30).map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-start' : 'justify-end'}`}>
              <div className={`max-w-[88%] px-3 py-2 rounded-2xl text-sm whitespace-pre-wrap ${
                m.role === 'user'
                  ? 'bg-white/10 rounded-tr-sm'
                  : 'bg-gradient-to-br from-yellow-600/25 to-orange-600/25 border border-yellow-500/30 rounded-tl-sm'
              }`}>{m.content}</div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-end">
            <div className="bg-yellow-500/10 px-3 py-2 rounded-2xl text-sm flex gap-1">
              <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full animate-bounce" />
              <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full animate-bounce" style={{ animationDelay: '.15s' }} />
              <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full animate-bounce" style={{ animationDelay: '.3s' }} />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Pending preview confirm bar */}
      {pending && (
        <div className="px-3 py-2.5 bg-gradient-to-r from-green-500/20 to-emerald-500/10 border-t border-green-500/40" data-testid="pending-confirm-bar">
          <div className="flex items-center gap-2 mb-1.5">
            <Check className="w-4 h-4 text-green-400" />
            <span className="text-xs font-bold text-green-300">معاينة فقط — هل أنت متأكد؟</span>
          </div>
          <div className="flex gap-1.5">
            <button
              onClick={onConfirm}
              disabled={loading}
              className="flex-1 px-3 py-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg text-black text-xs font-bold disabled:opacity-50 flex items-center justify-center gap-1"
              data-testid="confirm-pending-btn"
            ><Check className="w-3.5 h-3.5" />اعتمد</button>
            <button
              onClick={onCancel}
              disabled={loading}
              className="px-3 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-xs font-bold disabled:opacity-50"
              data-testid="cancel-pending-btn"
            >جرّب غيره</button>
          </div>
        </div>
      )}

      {/* Inline Step Picker */}
      {stepMeta && stepId !== 'done' && (
        <div className="px-3 py-2.5 border-t border-white/10 bg-black/30 max-h-[280px] overflow-y-auto">
          <div className="text-[10px] font-bold opacity-60 mb-1.5 uppercase tracking-wide">
            {stepMeta.title}
          </div>
          <InlineStepRenderer
            step={stepMeta}
            variants={variants}
            loading={loading}
            onAnswer={onAnswerStep}
            selected={selected}
            setSelected={setSelected}
            project={project}
          />
        </div>
      )}

      {/* 🆕 Proposals shown inline in chat */}
      {(proposalsLoading || (proposals && proposals.length > 0)) && (
        <ProposalCards proposals={proposals} onPick={onPickProposal} onDismiss={onDismissProposals} loading={proposalsLoading} />
      )}

      {/* 🆕 Quick Add Bar — always visible, one-click section add */}
      <QuickAddBar onPick={onSendText} loading={loading} />

      {/* Free text input */}
      <div className="p-2.5 border-t border-white/10 flex gap-2 items-center bg-[#0a0e1c]">
        <input
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
          placeholder={stepId && stepId !== 'done' ? 'أو اكتب طلبك الخاص...' : 'اكتب رسالتك...'}
          className="flex-1 px-3 py-2 bg-white/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-yellow-500 text-sm"
          data-testid="chat-input"
          disabled={loading}
        />
        <button
          onClick={send}
          disabled={loading || !msg.trim()}
          className="px-3 py-2 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-xl disabled:opacity-40 text-black font-bold"
          data-testid="chat-send-btn"
        ><Send className="w-4 h-4" /></button>
      </div>
    </div>
  );
}

/* ================================================================
   PREVIEW PANE — desktop + mobile toggle + fullscreen
   ================================================================ */
function PreviewPane({ html, project, fullscreen, onToggleFullscreen, onRefresh, device, onToggleDevice }) {
  const isMobile = device === 'mobile';
  return (
    <div className={`flex flex-col min-h-0 bg-[#050815] ${fullscreen ? 'fixed inset-0 z-50' : 'flex-1'}`} data-testid="preview-pane">
      <div className="flex items-center gap-2 px-3 py-2 text-xs bg-[#0a0e1c] border-b border-white/10">
        <Eye className="w-4 h-4 text-yellow-500" />
        <span className="opacity-70 font-bold">معاينة لايف</span>
        <span className="opacity-50 truncate">• {project?.sections?.length || 0} أقسام</span>
        <div className="flex-1" />
        <div className="flex items-center bg-white/5 border border-white/10 rounded-lg overflow-hidden" data-testid="device-toggle">
          <button
            onClick={() => onToggleDevice('desktop')}
            className={`px-2.5 py-1 text-[11px] font-bold flex items-center gap-1 transition-colors ${!isMobile ? 'bg-yellow-500 text-black' : 'hover:bg-white/10'}`}
            title="عرض حاسوب"
            data-testid="device-desktop-btn"
          ><Monitor className="w-3.5 h-3.5" />حاسوب</button>
          <button
            onClick={() => onToggleDevice('mobile')}
            className={`px-2.5 py-1 text-[11px] font-bold flex items-center gap-1 transition-colors ${isMobile ? 'bg-yellow-500 text-black' : 'hover:bg-white/10'}`}
            title="عرض جوال"
            data-testid="device-mobile-btn"
          ><span className="text-base leading-none">📱</span>جوال</button>
        </div>
        <button
          onClick={onRefresh}
          className="p-1.5 hover:bg-white/10 rounded-lg"
          title="تحديث المعاينة"
          data-testid="preview-refresh-btn"
        ><RefreshCw className="w-4 h-4" /></button>
        <button
          onClick={onToggleFullscreen}
          className="p-1.5 hover:bg-white/10 rounded-lg"
          title={fullscreen ? 'إنهاء ملء الشاشة' : 'ملء الشاشة'}
          data-testid="preview-fullscreen-btn"
        >{fullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}</button>
      </div>
      <div className={`flex-1 w-full ${isMobile ? 'flex items-start justify-center overflow-y-auto py-4 bg-gradient-to-b from-[#050815] to-[#0b0f1f]' : ''}`}>
        {isMobile ? (
          <div className="relative bg-black rounded-[40px] shadow-2xl border-[10px] border-[#0a0e1c] overflow-hidden" style={{ width: 390, height: 780 }} data-testid="mobile-frame">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-28 h-5 bg-black rounded-b-2xl z-10" />
            <iframe
              key={`${project?.id}-mobile`}
              srcDoc={html}
              className="w-full h-full bg-white"
              sandbox="allow-scripts allow-same-origin"
              title="preview-mobile"
              data-testid="live-preview"
            />
          </div>
        ) : (
          <iframe
            key={project?.id}
            srcDoc={html}
            className="flex-1 w-full h-full bg-white"
            sandbox="allow-scripts allow-same-origin"
            title="preview"
            data-testid="live-preview"
          />
        )}
      </div>
    </div>
  );
}

/* ================================================================
   INDEPENDENCE MODAL (unchanged logic — rearranged for mobile)
   ================================================================ */
function IndependenceModal({ onClose }) {
  return (
    <div className="fixed inset-0 bg-black/85 z-[60] flex items-center justify-center p-4" onClick={onClose} dir="rtl" data-testid="independence-modal">
      <div className="bg-[#0e1128] rounded-2xl max-w-2xl w-full border border-yellow-500/30 p-5 md:p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4 gap-3">
          <div>
            <h2 className="text-lg md:text-xl font-bold mb-1">🚀 الاستقلالية — انقل موقعك أينما شئت</h2>
            <p className="text-xs md:text-sm opacity-70">الموقع مستضاف على Zitex. لنقله لاستضافتك الخاصة:</p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded shrink-0"><X className="w-5 h-5" /></button>
        </div>
        <div className="grid md:grid-cols-3 gap-2.5 mb-4">
          {[
            { name: 'Vercel', pro: 'الأفضل للمواقع الحديثة', free: 'مجاني', url: 'https://vercel.com' },
            { name: 'Netlify', pro: 'بديل ممتاز', free: 'مجاني', url: 'https://netlify.com' },
            { name: 'GitHub Pages', pro: 'للمواقع الثابتة', free: 'مجاني 100%', url: 'https://pages.github.com' },
          ].map((o) => (
            <div key={o.name} className="bg-white/5 p-3 rounded-xl border border-white/10">
              <div className="font-bold mb-0.5 text-sm">{o.name}</div>
              <div className="text-[11px] opacity-70 mb-2">{o.pro}</div>
              <div className="text-[10px] px-2 py-0.5 bg-green-500/20 text-green-400 rounded inline-block mb-2">{o.free}</div>
              <a href={o.url} target="_blank" rel="noreferrer" className="block text-xs text-yellow-500 hover:underline">زيارة ↗</a>
            </div>
          ))}
        </div>
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-3 md:p-4 text-xs md:text-sm">
          <div className="font-bold mb-2">📋 آلية التسليم:</div>
          <ol className="list-decimal ps-5 space-y-1 opacity-90">
            <li>اعتمد التصميم النهائي أولاً</li>
            <li>ادفع رسوم الاستقلالية</li>
            <li>يرشدك المستشار خطوة بخطوة لنقل الموقع</li>
            <li>يُسلَّم الكود ملف بعد ملف مع شرح كل ملف</li>
          </ol>
        </div>
        <button onClick={onClose} className="w-full mt-3 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl font-bold text-sm" data-testid="independence-close-btn">فهمت، سأعود لاحقاً</button>
      </div>
    </div>
  );
}

/* ================================================================
   LIBRARY MODAL (compact)
   ================================================================ */
function LibraryModal({ projects, onOpen, onDelete, onDuplicate, onApprove, onClose }) {
  const approved = projects.filter((p) => p.status === 'approved');
  const drafts = projects.filter((p) => p.status !== 'approved');
  const [kitProject, setKitProject] = useState(null);

  const Card = ({ p, isApproved }) => {
    const copyPublic = () => {
      const url = `${window.location.origin}/sites/${p.slug}`;
      navigator.clipboard.writeText(url);
      toast.success('📋 تم نسخ الرابط');
    };
    return (
    <div className={`p-4 rounded-xl border relative ${isApproved ? 'bg-gradient-to-br from-green-500/10 to-emerald-500/5 border-green-500/40' : 'bg-white/5 border-white/10'}`} data-testid={`library-project-${p.id}`}>
      {isApproved && (
        <span className="absolute top-2 left-2 text-[10px] bg-green-500 text-black font-bold px-2 py-0.5 rounded-full">✓ معتمد</span>
      )}
      <div className="font-bold mb-1 truncate pr-6">{p.name}</div>
      <div className="text-xs text-white/50 mb-2">{p.template} • {(p.sections || []).length} أقسام{p.approved_at ? ` • ${new Date(p.approved_at).toLocaleDateString('ar')}` : ''}{isApproved && p.visits ? ` • 👁️ ${p.visits} زيارة` : ''}</div>
      {isApproved && p.slug && (
        <div className="mb-2 flex items-center gap-1.5 bg-black/30 rounded-lg px-2 py-1.5">
          <code className="flex-1 text-[10px] text-yellow-400 truncate">/sites/{p.slug}</code>
          <button onClick={copyPublic} className="text-xs px-2 py-0.5 bg-yellow-500/20 hover:bg-yellow-500/40 rounded" data-testid={`copy-link-${p.id}`}>📋</button>
          <a href={`/sites/${p.slug}`} target="_blank" rel="noreferrer" className="text-xs px-2 py-0.5 bg-green-500/20 hover:bg-green-500/40 rounded text-green-400" data-testid={`visit-${p.id}`}>↗</a>
        </div>
      )}
      <div className="grid grid-cols-2 gap-1.5">
        <button onClick={() => onOpen(p.id)} className="px-2 py-1.5 bg-yellow-500/20 hover:bg-yellow-500/40 rounded text-xs font-bold" data-testid={`open-${p.id}`}>✏️ تعديل</button>
        <button onClick={() => onDuplicate(p.id)} className="px-2 py-1.5 bg-white/10 hover:bg-white/20 rounded text-xs font-bold">📋 نسخ</button>
        {isApproved ? (
          <>
            <button onClick={() => setKitProject(p)} className="col-span-2 px-2 py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded text-xs font-black flex items-center justify-center gap-1" data-testid={`delivery-kit-${p.id}`}>
              📦 حزمة التسليم (مشاركة + تحكم العميل)
            </button>
          </>
        ) : (
          <>
            <button onClick={() => onApprove(p.id)} className="px-2 py-1.5 bg-green-500/20 hover:bg-green-500/40 rounded text-xs font-bold" data-testid={`approve-${p.id}`}>✅ اعتماد</button>
            <button onClick={() => onDelete(p.id)} className="px-2 py-1.5 bg-red-600/20 hover:bg-red-600/40 rounded text-xs"><Trash2 className="w-3 h-3 inline" /> حذف</button>
          </>
        )}
      </div>
    </div>
    );
  };

  return (
    <>
    <div className="fixed inset-0 bg-black/80 z-[55] flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-[#0e1128] rounded-2xl max-w-5xl w-full max-h-[85vh] overflow-y-auto border border-yellow-500/30 p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">مواقعي ({projects.length})</h2>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded"><X className="w-5 h-5" /></button>
        </div>
        {projects.length === 0 ? (
          <div className="text-center py-12 text-white/50">لم تنشئ أي موقع بعد</div>
        ) : (
          <>
            {approved.length > 0 && (
              <div className="mb-5">
                <div className="text-sm font-bold text-green-400 mb-2 flex items-center gap-2">
                  ✓ المشاريع المعتمدة ({approved.length})
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {approved.map((p) => <Card key={p.id} p={p} isApproved />)}
                </div>
              </div>
            )}
            {drafts.length > 0 && (
              <div>
                <div className="text-sm font-bold text-white/70 mb-2">مسوّدات ({drafts.length})</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {drafts.map((p) => <Card key={p.id} p={p} isApproved={false} />)}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
    {kitProject && <DeliveryKitModal project={kitProject} onClose={() => setKitProject(null)} />}
    </>
  );
}

/* ================================================================
   DELIVERY KIT — everything the owner needs to hand off the site
   ================================================================ */
function DeliveryKitModal({ project, onClose }) {
  const [kit, setKit] = useState(null);
  const [busy, setBusy] = useState(false);
  const [credentials, setCredentials] = useState(null);
  const [shareLink, setShareLink] = useState('');
  const [qc, setQc] = useState(null);
  const origin = window.location.origin;

  const loadKit = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/delivery-kit`, { headers: authH() });
      const d = await r.json();
      setKit(d);
      if (d.share_url) setShareLink(`${origin}/api/websites${d.share_url.replace('/preview-share', '/share')}`);
    } catch (_) {}
  }, [project.id, origin]);

  const loadQC = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/quality-checks`, { headers: authH() });
      const d = await r.json();
      setQc(d);
    } catch (_) {}
  }, [project.id]);

  useEffect(() => { loadKit(); loadQC(); }, [loadKit, loadQC]);

  const createShare = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/share`, { method: 'POST', headers: authH() });
      const d = await r.json();
      setShareLink(`${origin}/api/websites/share/${d.token}`);
      toast.success('✨ رابط المشاركة جاهز');
      loadKit();
    } catch (_) { toast.error('فشل'); }
    finally { setBusy(false); }
  };

  const createClientAccess = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/client-access`, { method: 'POST', headers: authH() });
      const d = await r.json();
      setCredentials({ slug: d.slug, password: d.temp_password, url: `${origin}/client/${d.slug}` });
      toast.success('✨ تم تفعيل لوحة تحكم العميل');
      loadKit();
    } catch (_) { toast.error('فشل'); }
    finally { setBusy(false); }
  };

  const copy = (t) => { navigator.clipboard.writeText(t); toast.success('تم النسخ'); };
  const publicUrl = kit?.public_url ? `${origin}${kit.public_url}` : '';

  return (
    <div className="fixed inset-0 bg-black/85 z-[60] flex items-center justify-center p-4" onClick={onClose} dir="rtl" data-testid="delivery-kit-modal">
      <div className="bg-[#0e1128] rounded-2xl max-w-2xl w-full border border-yellow-500/30 p-5 md:p-6 max-h-[92vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4 gap-3">
          <div>
            <h2 className="text-lg font-bold mb-1 flex items-center gap-2">📦 حزمة التسليم — {project.name}</h2>
            <p className="text-xs opacity-70">كل ما تحتاجه لتسليم الموقع لعميلك</p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded shrink-0"><X className="w-5 h-5" /></button>
        </div>

        {/* 1) Public URL */}
        <section className="mb-4 bg-gradient-to-br from-green-500/10 to-emerald-500/5 border border-green-500/30 rounded-xl p-4">
          <div className="text-xs font-black text-green-300 mb-2">1️⃣ الرابط العام (موقع العميل)</div>
          <div className="flex items-center gap-2 bg-black/30 rounded-lg px-3 py-2 mb-2">
            <code className="flex-1 text-xs text-yellow-300 truncate" data-testid="kit-public-url">{publicUrl || '—'}</code>
            {publicUrl && <><button onClick={() => copy(publicUrl)} className="p-1 hover:bg-white/10 rounded" data-testid="copy-public"><Copy className="w-4 h-4" /></button>
            <a href={publicUrl} target="_blank" rel="noreferrer" className="p-1 hover:bg-white/10 rounded text-green-400"><ExternalLink className="w-4 h-4" /></a></>}
          </div>
          <div className="text-[11px] opacity-70">أرسل هذا الرابط لعملاء موقعك — هو الموقع النهائي.</div>
        </section>

        {/* 2) Share link for review */}
        <section className="mb-4 bg-gradient-to-br from-blue-500/10 to-cyan-500/5 border border-blue-500/30 rounded-xl p-4">
          <div className="text-xs font-black text-blue-300 mb-2">2️⃣ رابط المعاينة الخاصة (قبل الاعتماد)</div>
          {shareLink ? (
            <>
              <div className="flex items-center gap-2 bg-black/30 rounded-lg px-3 py-2 mb-2">
                <code className="flex-1 text-xs text-blue-300 truncate" data-testid="kit-share-url">{shareLink}</code>
                <button onClick={() => copy(shareLink)} className="p-1 hover:bg-white/10 rounded" data-testid="copy-share"><Copy className="w-4 h-4" /></button>
                <a href={shareLink} target="_blank" rel="noreferrer" className="p-1 hover:bg-white/10 rounded text-blue-400"><ExternalLink className="w-4 h-4" /></a>
              </div>
              <div className="text-[11px] opacity-70">ينتهي خلال 14 يوم. العميل يرى شريط "اكتب ملاحظاتي" ويرسلها لك.</div>
            </>
          ) : (
            <button onClick={createShare} disabled={busy} className="w-full px-3 py-2 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-400/30 rounded-lg text-xs font-bold disabled:opacity-50" data-testid="create-share-btn">
              🔗 إنشاء رابط معاينة للعميل
            </button>
          )}
        </section>

        {/* 3) Client dashboard */}
        <section className="mb-4 bg-gradient-to-br from-purple-500/10 to-pink-500/5 border border-purple-500/30 rounded-xl p-4">
          <div className="text-xs font-black text-purple-300 mb-2">3️⃣ لوحة تحكم العميل (إدارة المحتوى والرسائل)</div>
          {credentials || kit?.client_access_enabled ? (
            <>
              <div className="bg-black/30 rounded-lg p-3 mb-2 space-y-1.5">
                <div className="flex items-center gap-2"><span className="text-[10px] opacity-60 w-14">الرابط:</span><code className="text-xs text-purple-300 flex-1 truncate">{credentials?.url || `${origin}/client/${kit?.slug}`}</code><button onClick={() => copy(credentials?.url || `${origin}/client/${kit?.slug}`)} className="p-1 hover:bg-white/10 rounded"><Copy className="w-3 h-3" /></button></div>
                {credentials?.password && (
                  <div className="flex items-center gap-2"><span className="text-[10px] opacity-60 w-14">الكلمة:</span><code className="text-xs text-yellow-300 font-mono flex-1">{credentials.password}</code><button onClick={() => copy(credentials.password)} className="p-1 hover:bg-white/10 rounded" data-testid="copy-password"><Copy className="w-3 h-3" /></button></div>
                )}
              </div>
              <button onClick={createClientAccess} disabled={busy} className="text-[11px] underline opacity-70 hover:opacity-100" data-testid="regen-password">🔄 إعادة إصدار كلمة مرور</button>
              {credentials?.password && <div className="text-[11px] text-yellow-400 mt-2">⚠️ احفظ كلمة المرور الآن — لن تظهر مرة أخرى.</div>}
            </>
          ) : (
            <button onClick={createClientAccess} disabled={busy} className="w-full px-3 py-2 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-400/30 rounded-lg text-xs font-bold disabled:opacity-50" data-testid="create-client-access-btn">
              🔑 تفعيل لوحة تحكم العميل (إنشاء حساب له)
            </button>
          )}
        </section>

        {/* 4) Stats */}
        <section className="mb-3 grid grid-cols-3 gap-2 text-center">
          <div className="bg-white/5 rounded-lg p-2.5"><div className="text-xl font-black text-yellow-400">{kit?.visits ?? 0}</div><div className="text-[10px] opacity-60">زيارة</div></div>
          <div className="bg-white/5 rounded-lg p-2.5"><div className="text-xl font-black text-pink-400">{kit?.messages_count ?? 0}</div><div className="text-[10px] opacity-60">رسالة</div></div>
          <div className="bg-white/5 rounded-lg p-2.5"><div className="text-xl font-black text-blue-400">{kit?.feedback_count ?? 0}</div><div className="text-[10px] opacity-60">ملاحظة</div></div>
        </section>

        <div className="text-[11px] opacity-60 text-center">جميع البيانات محفوظة تلقائياً في Zitex.</div>
      </div>
    </div>
  );
}

/* ================================================================
   LOGO STUDIO — multi-step, button-based: style → generate 3 → pick → color → apply
   ================================================================ */
const LOGO_STYLES = [
  { id: 'elegant',     label: 'أنيق',       hint: 'elegant, refined, thin strokes, serif accents' },
  { id: 'playful',     label: 'مرح',        hint: 'playful, rounded, friendly, vibrant accents' },
  { id: 'minimal',     label: 'بسيط',       hint: 'minimal, negative space, geometric, essential' },
  { id: 'luxury',      label: 'فاخر',       hint: 'luxury, gold-accent, premium, sophisticated' },
  { id: 'modern',      label: 'حديث',       hint: 'modern, clean grotesque typography, sharp' },
  { id: 'classic',     label: 'كلاسيكي',    hint: 'classic, traditional emblem, timeless' },
  { id: 'bold',        label: 'جريء',       hint: 'bold, high-contrast, solid, confident' },
  { id: 'tech',        label: 'تقني',       hint: 'tech, futuristic, digital, subtle gradients' },
];

const LOGO_COLORS = [
  { id: 'default',  label: 'تلقائي',  hint: '' },
  { id: 'gold',     label: 'ذهبي',    hint: 'gold (#D4AF37) and cream accents' },
  { id: 'black',    label: 'أسود',    hint: 'pure black (#000000) monochrome' },
  { id: 'white',    label: 'أبيض',    hint: 'white on dark background' },
  { id: 'blue',     label: 'أزرق',    hint: 'royal blue (#1D4ED8) and navy' },
  { id: 'red',      label: 'أحمر',    hint: 'crimson red (#DC2626) with dark accents' },
  { id: 'green',    label: 'أخضر',    hint: 'emerald green (#10B981)' },
  { id: 'orange',   label: 'برتقالي', hint: 'warm orange (#F97316)' },
  { id: 'purple',   label: 'بنفسجي',  hint: 'deep purple (#7C3AED)' },
  { id: 'multi',    label: 'ملوّن',    hint: 'multi-color vibrant palette' },
];

function LogoStudioModal({ project, onClose, onApplied }) {
  const [stage, setStage] = useState('brand'); // brand | style | generating | pick | applied
  const [brand, setBrand] = useState(project?.name || '');
  const [hint, setHint]   = useState('');
  const [style, setStyle] = useState(null);
  const [color, setColor] = useState(null);
  const [logos, setLogos] = useState([]);
  const [busy, setBusy]   = useState(false);

  const generate = async (selectedStyle, selectedColor) => {
    if (!project?.id) return;
    setBusy(true);
    setStage('generating');
    toast.info('🎨 جاري توليد 3 لوقوهات — 20-40 ثانية');
    const fullPrompt = `لوقو لـ "${brand || project?.name || 'نشاطي'}". ${hint}`.trim();
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/generate-logo-variants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({
          prompt: fullPrompt,
          style_hint: selectedStyle?.hint || '',
          color_hint: selectedColor?.hint || '',
          count: 3,
        }),
      });
      if (!r.ok) throw new Error('failed');
      const d = await r.json();
      setLogos(d.logos || []);
      setStage('pick');
    } catch (_) {
      toast.error('فشل التوليد — حاول بوصف أوضح');
      setStage('style');
    } finally { setBusy(false); }
  };

  const applyLogo = async (logoUrl) => {
    if (!project?.id || !logoUrl) return;
    setBusy(true);
    try {
      await fetch(`${API}/api/websites/projects/${project.id}/apply-logo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({ logo_url: logoUrl }),
      });
      onApplied(logoUrl);
      setStage('applied');
      toast.success('✨ تم تثبيت اللوقو في الموقع!');
      setTimeout(onClose, 900);
    } catch (_) { toast.error('فشل التطبيق'); }
    finally { setBusy(false); }
  };

  const regenerateWithColor = (c) => {
    setColor(c);
    generate(style, c);
  };

  return (
    <div className="fixed inset-0 bg-black/85 z-[60] flex items-center justify-center p-4" onClick={onClose} dir="rtl" data-testid="logo-studio-modal">
      <div className="bg-[#0e1128] rounded-2xl max-w-3xl w-full border border-yellow-500/30 p-5 md:p-6 max-h-[92vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4 gap-3">
          <div>
            <h2 className="text-lg md:text-xl font-bold mb-1 flex items-center gap-2"><Sparkles className="w-5 h-5 text-yellow-400" /> استوديو اللوقو</h2>
            <p className="text-xs md:text-sm opacity-70">
              {stage === 'brand' && 'الخطوة 1 من 3 — اسم العلامة التجارية'}
              {stage === 'style' && 'الخطوة 2 من 3 — اختر الأسلوب (بضغطة واحدة)'}
              {stage === 'generating' && 'جاري توليد 3 تصاميم...'}
              {stage === 'pick' && 'الخطوة 3 من 3 — اختر اللوقو المفضّل + بدّل اللون'}
              {stage === 'applied' && '✨ تم تثبيت اللوقو!'}
            </p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded shrink-0"><X className="w-5 h-5" /></button>
        </div>

        {stage === 'brand' && (
          <div className="space-y-3" data-testid="logo-stage-brand">
            <div>
              <label className="text-xs opacity-70 block mb-1">اسم العلامة التجارية</label>
              <input
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                placeholder="مثال: كوفي دافئ"
                className="w-full px-3 py-2.5 bg-white/10 border border-white/15 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 text-sm"
                data-testid="logo-brand-input"
              />
            </div>
            <div>
              <label className="text-xs opacity-70 block mb-1">تفاصيل إضافية (اختياري)</label>
              <input
                value={hint}
                onChange={(e) => setHint(e.target.value)}
                placeholder="مثال: فنجان قهوة بلمسة دفء وحبوب بن"
                className="w-full px-3 py-2.5 bg-white/10 border border-white/15 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 text-sm"
                data-testid="logo-hint-input"
              />
            </div>
            <button
              onClick={() => brand.trim() && setStage('style')}
              disabled={!brand.trim()}
              className="w-full px-4 py-2.5 bg-gradient-to-r from-yellow-500 to-orange-500 text-black rounded-xl font-bold disabled:opacity-50"
              data-testid="logo-next-style-btn"
            >التالي ← اختر الأسلوب</button>
          </div>
        )}

        {stage === 'style' && (
          <div className="space-y-3" data-testid="logo-stage-style">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {LOGO_STYLES.map((s) => (
                <button
                  key={s.id}
                  onClick={() => { setStyle(s); generate(s, color); }}
                  disabled={busy}
                  className="p-3 rounded-xl bg-white/5 hover:bg-yellow-500/15 border border-white/10 hover:border-yellow-500/50 transition-all disabled:opacity-50 font-bold text-sm"
                  data-testid={`logo-style-${s.id}`}
                >{s.label}</button>
              ))}
            </div>
            <button onClick={() => setStage('brand')} className="text-xs opacity-70 hover:opacity-100 w-full text-center mt-2">← رجوع</button>
          </div>
        )}

        {stage === 'generating' && (
          <div className="py-10 text-center" data-testid="logo-stage-generating">
            <RefreshCw className="w-12 h-12 mx-auto mb-3 text-yellow-400 animate-spin" />
            <div className="text-sm font-bold">جاري توليد 3 لوقوهات بأسلوب "{style?.label}"</div>
            <div className="text-xs opacity-60 mt-1">قد يستغرق 20-40 ثانية...</div>
          </div>
        )}

        {stage === 'pick' && (
          <div className="space-y-4" data-testid="logo-stage-pick">
            <div>
              <div className="text-xs opacity-70 mb-2">اختر لوقو (ضغطة لتثبيته)</div>
              <div className="grid grid-cols-3 gap-2">
                {logos.map((url, i) => (
                  <button
                    key={i}
                    onClick={() => applyLogo(url)}
                    disabled={busy}
                    className="group relative aspect-square rounded-xl bg-white border-2 border-white/10 hover:border-yellow-500 transition-all overflow-hidden disabled:opacity-50"
                    data-testid={`logo-pick-${i}`}
                  >
                    <img src={url} alt={`logo ${i+1}`} className="w-full h-full object-contain p-2" />
                    <div className="absolute inset-0 bg-yellow-500/0 group-hover:bg-yellow-500/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition">
                      <Check className="w-10 h-10 text-black bg-yellow-400 rounded-full p-2 shadow-xl" />
                    </div>
                  </button>
                ))}
                {logos.length === 0 && (
                  <div className="col-span-3 text-center py-8 text-white/50 text-sm">لم يتم توليد أي لوقو — جرّب وصفاً آخر</div>
                )}
              </div>
            </div>
            <div>
              <div className="text-xs opacity-70 mb-2">💡 غيّر اللون وأعد التوليد (اختياري)</div>
              <div className="flex flex-wrap gap-1.5">
                {LOGO_COLORS.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => regenerateWithColor(c)}
                    disabled={busy}
                    className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all disabled:opacity-50 ${color?.id === c.id ? 'bg-yellow-500 border-yellow-500 text-black' : 'bg-white/5 border-white/15 hover:bg-yellow-500/20 hover:border-yellow-500/50'}`}
                    data-testid={`logo-color-${c.id}`}
                  >{c.label}</button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setStage('style')} className="flex-1 px-3 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-xs font-bold">← غيّر الأسلوب</button>
              <button onClick={() => generate(style, color)} disabled={busy} className="flex-1 px-3 py-2 bg-gradient-to-r from-purple-500/40 to-pink-500/40 hover:from-purple-500/60 hover:to-pink-500/60 border border-purple-400/40 rounded-lg text-xs font-bold disabled:opacity-50 flex items-center justify-center gap-1.5"><RefreshCw className={`w-3.5 h-3.5 ${busy ? 'animate-spin' : ''}`} />جرّب 3 تصاميم أخرى</button>
            </div>
          </div>
        )}

        {stage === 'applied' && (
          <div className="py-10 text-center" data-testid="logo-stage-applied">
            <Check className="w-16 h-16 mx-auto mb-3 text-green-400 bg-green-500/20 rounded-full p-3" />
            <div className="text-base font-bold">✨ اللوقو معتمد في موقعك!</div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ================================================================
   OVERRIDE BUILDER — compute theme/section override for live preview
   ================================================================ */
const VARIANT_MAP = {
  classic:  { primary: '#D4AF37', secondary: '#1a1f3a', accent: '#8B0000' },
  modern:   { primary: '#3B82F6', secondary: '#0f172a', accent: '#22D3EE' },
  warm:     { primary: '#F59E0B', secondary: '#18181b', accent: '#EF4444' },
  luxury:   { primary: '#D4AF37', secondary: '#0a0a0a', accent: '#B8860B', background: '#0a0a0a' },
  dark_pro: { primary: '#06B6D4', secondary: '#020617', accent: '#F59E0B', background: '#020617' },
  nature:   { primary: '#10B981', secondary: '#064e3b', accent: '#F59E0B' },
  pastel:   { primary: '#A78BFA', secondary: '#FDF2F8', accent: '#F472B6', background: '#FDF2F8', text: '#581c87' },
  bold:     { primary: '#DC2626', secondary: '#18181b', accent: '#FBBF24' },
};

const DASH_ICONS = { orders: '📦', customers: '👥', products: '🏷️', analytics: '📊', messages: '💬', reports: '📈', users: '🔐', settings: '⚙️', phone: '📞', email: '📧', calendar: '📅', inventory: '📋', payments: '💳', reviews: '⭐' };
const DASH_LABELS = { orders: 'الطلبات', customers: 'العملاء', products: 'المنتجات', analytics: 'الإحصائيات', messages: 'الرسائل', reports: 'التقارير', users: 'المستخدمون', settings: 'الإعدادات', phone: 'رقم الجوال', email: 'البريد', calendar: 'التقويم', inventory: 'المخزون', payments: 'المدفوعات', reviews: 'التقييمات' };

function buildOverrides(step, value, project) {
  const theme_override = {};
  let sections_override = null;
  const sections = project?.sections || [];

  if (step === 'variant') {
    const vmap = { classic: VARIANT_MAP.classic, modern: VARIANT_MAP.modern, warm: VARIANT_MAP.warm, luxury: VARIANT_MAP.luxury, dark_pro: VARIANT_MAP.dark_pro, nature: VARIANT_MAP.nature, pastel: VARIANT_MAP.pastel, bold: VARIANT_MAP.bold };
    Object.assign(theme_override, vmap[value] || {});
  } else if (step === 'buttons') {
    theme_override.radius = value;
  } else if (step === 'colors') {
    Object.assign(theme_override, VARIANT_MAP[value] || {});
  } else if (step === 'typography') {
    theme_override.font = value;
  } else if (step === 'dashboard') {
    // Dashboard-only mode: replace ALL sections with just the dashboard
    const existing = sections.find((s) => s.type === 'dashboard');
    if (value === 'none') {
      // User said no dashboard — show the regular site without dashboard
      sections_override = sections.filter((s) => s.type !== 'dashboard').map((s, i) => ({ ...s, order: i }));
    } else {
      const dashData = { layout: value, title: 'لوحة التحكم', items: existing?.data?.items || [] };
      sections_override = [{ id: 'preview-dash', type: 'dashboard', order: 0, visible: true, data: dashData }];
    }
  } else if (step === 'dashboard_items') {
    // Dashboard-only mode with chosen items — full screen admin UI
    const items = Array.isArray(value) ? value : (value ? [value] : []);
    const existing = sections.find((s) => s.type === 'dashboard');
    const layout = existing?.data?.layout || 'sidebar';
    sections_override = [{ id: 'preview-dash', type: 'dashboard', order: 0, visible: true, data: { layout, title: 'لوحة التحكم', items } }];
  } else if (step === 'sections') {
    // Live-update: show EXACTLY the sections the user has toggled (plus footer).
    // If a wanted type is missing from current sections, create a stub so it shows instantly.
    const wanted = Array.isArray(value) ? value : [value];
    const existingByType = {};
    (sections || []).forEach((s) => { existingByType[s.type] = s; });
    const DEFAULT_STUBS = {
      hero:        { title: project?.name || 'عنوان رئيسي', subtitle: 'عنوان فرعي ملهم', cta_text: 'ابدأ الآن', layout: 'split' },
      about:       { title: 'من نحن', text: 'اكتب نبذة مختصرة عن نشاطك.' },
      features:    { title: 'مميزاتنا', items: [{ icon:'✨', title:'ميزة أولى', text:'وصف' },{ icon:'🚀', title:'ميزة ثانية', text:'وصف' },{ icon:'💎', title:'ميزة ثالثة', text:'وصف' }] },
      menu:        { title: 'قائمة الطعام', categories: [{ name:'المشروبات الساخنة', items:[{name:'قهوة تركية',price:'15'},{name:'كابتشينو',price:'20'},{name:'لاتيه',price:'22'}] },{ name:'الحلويات', items:[{name:'تشيز كيك',price:'28'},{name:'براوني',price:'24'}] }] },
      products:    { title: 'منتجاتنا', items: [{name:'منتج 1',price:'99'},{name:'منتج 2',price:'149'},{name:'منتج 3',price:'199'}] },
      gallery:     { title: 'معرض الصور', images: ['https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800','https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800','https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=800'] },
      testimonials:{ title: 'آراء عملائنا', items: [{name:'أحمد',text:'تجربة رائعة!',rating:5},{name:'سارة',text:'جودة ممتازة',rating:5}] },
      team:        { title: 'فريقنا', members: [{name:'محمد',role:'المؤسس'},{name:'أحمد',role:'المدير'},{name:'فاطمة',role:'التسويق'}] },
      pricing:     { title: 'خطط الأسعار', plans: [{name:'أساسي',price:'99',features:['ميزة 1','ميزة 2']},{name:'احترافي',price:'199',features:['كل ما سبق','ميزة 3'],highlighted:true}] },
      faq:         { title: 'أسئلة شائعة', items: [{q:'كيف أطلب؟',a:'بسهولة عبر الموقع'},{q:'مدة التوصيل؟',a:'من 1-3 أيام'}] },
      contact:     { title: 'تواصل معنا', email: 'info@example.com', phone: '+966 50 000 0000' },
      cta:         { title: 'جاهز للبدء؟', cta_text: 'انضم إلينا' },
    };
    const built = wanted.map((t) => existingByType[t] || ({ id: `preview-${t}`, type: t, order: 0, visible: true, data: DEFAULT_STUBS[t] || { title: t } }));
    // Always include footer at end if exists
    const footer = (sections || []).find((s) => s.type === 'footer');
    if (footer) built.push(footer);
    sections_override = built.map((s, i) => ({ ...s, order: i }));
  } else if (step === 'payment') {
    // Live: show selected payment methods in a small preview band (stored in theme)
    const wanted = Array.isArray(value) ? value : [value];
    theme_override.payment_methods = wanted.filter((p) => p !== 'none');
  } else if (step === 'features') {
    // 🆕 Each feature must materialize in the live preview immediately.
    const wanted = Array.isArray(value) ? value : [value];
    const FEATURE_EXTRAS = { whatsapp: 'whatsapp_float', cart: 'cart_float', booking: 'book_float', reviews: 'rating_widget' };
    const FEATURE_SECTION = {
      reservation:  { type: 'reservation', data: { title: 'احجز طاولتك', subtitle: 'اضمن مكانك قبل الزحام', cta_text: 'احجز الآن' } },
      map:          { type: 'map_embed', data: { title: 'موقعنا على الخريطة', address: 'الرياض، المملكة العربية السعودية', lat: 24.7136, lng: 46.6753 } },
      newsletter:   { type: 'newsletter', data: { title: 'اشترك في نشرتنا', subtitle: 'عروض حصرية وأخبار أولاً' } },
      delivery:     { type: 'delivery_banner', data: { title: '🛵 توصيل سريع', subtitle: 'توصيل مجاني للطلبات فوق 100 ريال', cta_text: 'اطلب الآن' } },
    };
    const featureExtrasIds = new Set(Object.values(FEATURE_EXTRAS));
    const featureSectionTypes = new Set(Object.values(FEATURE_SECTION).map((x) => x.type));
    // Merge into theme.extras (remove previously-added feature extras first)
    const existingExtras = (project?.theme?.extras || []).filter((e) => !featureExtrasIds.has(e));
    const newExtras = [...existingExtras];
    wanted.forEach((f) => { if (FEATURE_EXTRAS[f] && !newExtras.includes(FEATURE_EXTRAS[f])) newExtras.push(FEATURE_EXTRAS[f]); });
    theme_override.extras = newExtras;
    // Build sections override (remove previously-added feature sections, re-add wanted)
    const wantedSectionTypes = new Set();
    const wantedSectionsMap = {};
    wanted.forEach((f) => {
      if (FEATURE_SECTION[f]) {
        wantedSectionTypes.add(FEATURE_SECTION[f].type);
        wantedSectionsMap[FEATURE_SECTION[f].type] = FEATURE_SECTION[f];
      }
    });
    const kept = sections.filter((s) => !featureSectionTypes.has(s.type) || wantedSectionTypes.has(s.type));
    const existingTypes = new Set(kept.map((s) => s.type));
    const footerIdx = kept.findIndex((s) => s.type === 'footer');
    const insertAt = footerIdx >= 0 ? footerIdx : kept.length;
    const toInsert = [];
    wantedSectionTypes.forEach((stype) => {
      if (!existingTypes.has(stype)) {
        const m = wantedSectionsMap[stype];
        toInsert.push({ id: `preview-${stype}`, type: stype, order: 0, visible: true, data: m.data });
      }
    });
    kept.splice(insertAt, 0, ...toInsert);
    sections_override = kept.map((s, i) => ({ ...s, order: i }));
  } else if (step === 'extras') {
    // Apply extras to theme (floating widgets)
    const wanted = Array.isArray(value) ? value : [value];
    theme_override.extras = wanted;
    // Also add/remove section-extras (video, newsletter, stats_band)
    const sectionMap = {
      video_section:   { type: 'video', data: { title: 'شاهد قصتنا', url: 'https://www.youtube.com/embed/dQw4w9WgXcQ' } },
      newsletter:      { type: 'newsletter', data: { title: 'اشترك في نشرتنا', subtitle: 'خصومات حصرية' } },
      stats_band:      { type: 'stats_band', data: { title: 'أرقام نفتخر بها', items: [
        { label: 'عميل سعيد', value: '5,000+' }, { label: 'طلب', value: '12,400' },
        { label: 'سنوات خبرة', value: '10' }, { label: 'تقييم', value: '4.9★' },
      ] } },
    };
    const wantedTypes = new Set();
    wanted.forEach((e) => { if (sectionMap[e]) wantedTypes.add(sectionMap[e].type); });
    const kept = sections.filter((s) => !['video', 'newsletter', 'stats_band'].includes(s.type) || wantedTypes.has(s.type));
    const existingTypes = new Set(kept.map((s) => s.type));
    const footerIdx = kept.findIndex((s) => s.type === 'footer');
    const insertAt = footerIdx >= 0 ? footerIdx : kept.length;
    const toInsert = [];
    wanted.forEach((e) => {
      const m = sectionMap[e];
      if (m && !existingTypes.has(m.type)) {
        toInsert.push({ id: `preview-${m.type}`, type: m.type, order: 0, visible: true, data: m.data });
      }
    });
    kept.splice(insertAt, 0, ...toInsert);
    sections_override = kept.map((s, i) => ({ ...s, order: i }));
  }
  return { theme_override, sections_override };
}

/* ================================================================
   MAIN STUDIO
   ================================================================ */
export default function WebsiteStudio({ user }) {
  const nav = useNavigate();
  const [categories, setCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState(null);
  const [layouts, setLayouts] = useState([]);
  const [variants, setVariants] = useState([]);
  const [wizardSteps, setWizardSteps] = useState([]);
  const [project, setProject] = useState(null);
  const [projects, setProjects] = useState([]);
  const [previewHtml, setPreviewHtml] = useState('');
  const [showLibrary, setShowLibrary] = useState(false);
  const [showIndependence, setShowIndependence] = useState(false);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [mobileView, setMobileView] = useState('preview');
  const [pending, setPending] = useState(null); // { step, value, html }
  const [previewDevice, setPreviewDevice] = useState('desktop'); // desktop | mobile
  const [showSnapshots, setShowSnapshots] = useState(false);
  const [showEditMode, setShowEditMode] = useState(false);
  const [showPalettePicker, setShowPalettePicker] = useState(false);
  const buildTimer = useRef(null);

  useEffect(() => {
    fetch(`${API}/api/websites/categories`).then((r) => r.json()).then((d) => setCategories(d.categories || []));
    fetch(`${API}/api/websites/wizard/steps`).then((r) => r.json()).then((d) => setWizardSteps(d.steps || []));
    loadProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 🆕 Re-fetch wizard steps when project changes — to merge vertical-specific questions (vq_*)
  useEffect(() => {
    if (!project?.id) return;
    fetch(`${API}/api/websites/wizard/steps?project_id=${project.id}`)
      .then((r) => r.json())
      .then((d) => setWizardSteps(d.steps || []))
      .catch(() => {});
  }, [project?.id]);

  const loadProjects = async () => {
    try {
      const r = await fetch(`${API}/api/websites/projects`, { headers: authH() });
      const d = await r.json();
      setProjects(d.projects || []);
    } catch (_) { /* ignore */ }
  };

  // Load layouts when category is chosen
  useEffect(() => {
    if (!activeCategory?.id) { setLayouts([]); return; }
    fetch(`${API}/api/websites/categories/${activeCategory.id}/layouts`)
      .then((r) => r.json()).then((d) => setLayouts(d.layouts || []));
  }, [activeCategory?.id]);

  // Load variants when project exists
  useEffect(() => {
    if (!project?.template) { setVariants([]); return; }
    fetch(`${API}/api/websites/templates/${project.template}/variants`)
      .then((r) => r.json()).then((d) => setVariants(d.variants || []));
  }, [project?.template]);

  const refreshPreview = useCallback(async (p) => {
    if (!p?.id) return;
    try {
      const r = await fetch(`${API}/api/websites/projects/${p.id}/build`, { method: 'POST', headers: authH() });
      const d = await r.json();
      setPreviewHtml(d.html || '');
    } catch (_) { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!project) return;
    if (buildTimer.current) clearTimeout(buildTimer.current);
    buildTimer.current = setTimeout(() => refreshPreview(project), 400);
    return () => buildTimer.current && clearTimeout(buildTimer.current);
  }, [project, refreshPreview]);

  // Esc exits fullscreen
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') setFullscreen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Actions
  const confirmLayout = async (L) => {
    if (!activeCategory || !L) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({
          name: `${L.name}`,
          template: activeCategory.id,
          business_type: activeCategory.id,
          meta: { layout_id: L.id },
        }),
      });
      const d = await r.json();
      setProject(d);
      setActiveCategory(null);
      await loadProjects();
      toast.success(`✨ تم اعتماد التصميم — اختر الألوان الآن`);
      setShowPalettePicker(true);
    } catch (_) { toast.error('فشل إنشاء المشروع'); }
    finally { setLoading(false); }
  };

  const applyPalette = async (paletteId) => {
    if (!project?.id) return;
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/apply-palette`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({ palette_id: paletteId }),
      });
      const d = await r.json();
      setProject(d);
      refreshPreview(d);
      // 🆕 Auto-advance the wizard so the chat starts asking next questions (buttons, fonts, extras, whatsapp, etc.)
      try {
        const cur = d?.wizard?.step;
        if (cur === 'variant' || cur === 'colors') {
          const r2 = await fetch(`${API}/api/websites/projects/${project.id}/wizard/answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authH() },
            body: JSON.stringify({ step: cur, value: paletteId }),
          });
          const d2 = await r2.json();
          setProject(d2);
        }
      } catch (_) { /* ignore — palette still applied */ }
      setShowPalettePicker(false);
      toast.success('🎨 تم تطبيق الألوان — الآن أكمل المعالج (الأزرار، الخط، الإضافات...)');
    } catch (_) { toast.error('فشل التطبيق'); }
  };

  const answerWizard = async (value) => {
    if (!project?.id) return;
    const step = project?.wizard?.step;
    if (!step) return;
    setChatLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/wizard/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({ step, value }),
      });
      const d = await r.json();
      setProject(d);
      setPending(null);
    } catch (_) { toast.error('فشل الرد'); }
    finally { setChatLoading(false); }
  };

  // Auto-scroll the iframe to the relevant section per wizard step + pulse highlight
  const scrollIframeTo = useCallback((step, value) => {
    setTimeout(() => {
      try {
        const iframe = document.querySelector('[data-testid="live-preview"]');
        const doc = iframe && iframe.contentDocument;
        if (!doc) return;
        const SCROLL_MAP = {
          variant:      '[data-hl="hero"]',
          colors:       '[data-hl="hero"]',
          buttons:      '[data-hl="btn"]',
          typography:   '[data-hl="h1"]',
          features:     '[data-hl="features"]',
          branding:     '[data-hl="hero"]',
          payment:      '[data-hl="pricing"],[data-hl="cta"]',
          sections:     '[data-hl="features"]',
        };
        let target = null;
        if (step === 'dashboard_items' && Array.isArray(value) && value.length > 0) {
          const last = value[value.length - 1];
          target = doc.getElementById(`panel-${last}`);
        } else if (step === 'sections' && Array.isArray(value) && value.length > 0) {
          // Scroll to the LAST toggled section so user sees it instantly
          const last = value[value.length - 1];
          target = doc.querySelector(`[data-hl="${last}"]`) || doc.getElementById(last);
        } else if (step === 'payment' && Array.isArray(value) && value.length > 0) {
          target = doc.querySelector('[data-hl="payment"]') || doc.querySelector('footer,[data-hl="footer"]');
        } else if (step === 'features' && Array.isArray(value) && value.length > 0) {
          const last = value[value.length - 1];
          const featureMap = {
            whatsapp:    '[data-hl="extra-whatsapp"]',
            cart:        '[data-hl="extra-cart"]',
            booking:     '[data-hl="extra-book"]',
            reviews:     '[data-hl="extra-rating"]',
            reservation: '[data-hl="reservation"]',
            map:         '[data-hl="map"]',
            newsletter:  '[data-hl="newsletter"]',
            delivery:    '[data-hl="delivery"]',
          };
          const sel = featureMap[last];
          if (sel) target = doc.querySelector(sel);
        } else if (step === 'extras' && Array.isArray(value) && value.length > 0) {
          const last = value[value.length - 1];
          const extraMap = {
            video_section: '[data-hl="video"]',
            newsletter: '[data-hl="newsletter"]',
            stats_band: '[data-hl="stats_band"]',
            sticky_phone: '[data-hl="extra-phone"]',
            whatsapp_float: '[data-hl="extra-whatsapp"]',
            scroll_top: '[data-hl="extra-scroll"]',
            countdown: '[data-hl="extra-countdown"]',
            rating_widget: '[data-hl="extra-rating"]',
            social_bar: '[data-hl="extra-social"]',
            trust_badges: '[data-hl="extra-trust"]',
            live_chat: '[data-hl="extra-chat"]',
          };
          const sel = extraMap[last];
          if (sel) target = doc.querySelector(sel);
        } else {
          const sel = SCROLL_MAP[step];
          if (sel) target = doc.querySelector(sel);
        }
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'center' });
          target.classList.remove('zx-pulse');
          // Force reflow then add pulse
          void target.offsetWidth;
          target.classList.add('zx-pulse');
          setTimeout(() => target.classList.remove('zx-pulse'), 1600);
        }
      } catch (_) { /* ignore */ }
    }, 450);
  }, []);

  // Live-preview: applies theme/section overrides WITHOUT persisting
  const previewAnswer = async (step, value) => {
    if (!project?.id) return;
    const overrides = buildOverrides(step, value, project);
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/build-preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify(overrides),
      });
      const d = await r.json();
      setPreviewHtml(d.html || '');
      setPending({ step, value });
      scrollIframeTo(step, value);
    } catch (_) { /* ignore */ }
  };

  const confirmPending = async () => {
    if (!pending) return;
    await answerWizard(pending.value);
  };

  const cancelPending = async () => {
    setPending(null);
    // Refresh preview to the saved state
    if (project) refreshPreview(project);
  };

  const sendChat = async (message) => {
    if (!project?.id) return;
    // 🆕 Intercept special marker for design proposals
    if (message === '__PROPOSE_DESIGNS__') { fetchProposals(); return; }
    setChatLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/wizard/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({ message }),
      });
      const d = await r.json();
      if (d.project) {
        setProject(d.project);
        // Immediate refresh (bypass the 400ms debounce so the user SEES the change now)
        refreshPreview(d.project);
      }
      if (d.action && d.action.action) {
        const a = d.action.action;
        if (a === 'show_snapshots') {
          setShowSnapshots(true);
        }
        const msgs = {
          add_section: '✨ تمت إضافة قسم جديد في المعاينة',
          fill_section: '📝 تم تحديث محتوى القسم',
          patch_section: '✏️ تم تعديل القسم',
          remove_section: '🗑️ تم حذف القسم',
          apply_theme: '🎨 تم تطبيق الألوان',
          apply_button: '🔘 تم تغيير الأزرار',
          apply_font: '🔤 تم تغيير الخط',
          inject_css: '💫 تم تطبيق التأثير',
          scaffold: '🏗️ تم إعادة بناء الموقع',
          generate_logo: '🖼️ جاري توليد اللوقو...',
          show_snapshots: '📚 فتحت لك سجل التصاميم',
        };
        if (msgs[a]) toast.success(msgs[a]);
      }
    } catch (_) { toast.error('فشل الاتصال'); }
    finally { setChatLoading(false); }
  };

  const openProject = async (id) => {
    try {
      const r = await fetch(`${API}/api/websites/projects/${id}`, { headers: authH() });
      const d = await r.json();
      setProject(d);
      setShowLibrary(false);
    } catch (_) { toast.error('فشل الفتح'); }
  };

  const duplicateProject = async (id) => {
    try {
      const r = await fetch(`${API}/api/websites/projects/${id}/duplicate`, { method: 'POST', headers: authH() });
      const d = await r.json();
      toast.success('تم نسخ المشروع');
      await loadProjects();
      setProject(d);
      setShowLibrary(false);
    } catch (_) { toast.error('فشل النسخ'); }
  };

  const approveProject = async (id) => {
    try {
      await fetch(`${API}/api/websites/projects/${id}/approve`, { method: 'POST', headers: authH() });
      toast.success('✅ تم اعتماد المشروع رسمياً');
      await loadProjects();
      if (project?.id === id) setProject({ ...project, status: 'approved' });
    } catch (_) { toast.error('فشل الاعتماد'); }
  };

  const deleteProject = async (id) => {
    if (!window.confirm('حذف نهائي؟')) return;
    await fetch(`${API}/api/websites/projects/${id}`, { method: 'DELETE', headers: authH() });
    if (project?.id === id) setProject(null);
    await loadProjects();
  };

  const exportHtml = () => {
    if (!previewHtml) return;
    const blob = new Blob([previewHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(project?.name || 'website').replace(/[^\w\u0600-\u06FF]+/g, '_')}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const currentStep = project?.wizard?.step;
  const stepMeta = wizardSteps.find((s) => s.id === currentStep);
  const activeTemplate = categories.find((c) => c.id === project?.template);

  // Auto-preview an empty dashboard when entering the dashboard step (teaser)
  useEffect(() => {
    if (!project?.id || !currentStep) return;
    if (currentStep === 'dashboard' && !pending) {
      // Show empty sidebar dashboard full-screen
      previewAnswer('dashboard', 'sidebar');
    } else if (currentStep === 'dashboard_items' && !pending) {
      // Show current items as full dashboard
      const existing = (project.sections || []).find((s) => s.type === 'dashboard');
      const items = existing?.data?.items || [];
      previewAnswer('dashboard_items', items);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project?.id, currentStep]);

  // Logo generation — now opens a proper multi-step studio (no more window.prompt)
  const [logoStudioOpen, setLogoStudioOpen] = useState(false);
  const [techStackOpen, setTechStackOpen] = useState(false);
  const [proposals, setProposals] = useState(null); // array of design proposals shown inline in chat
  const [proposalsLoading, setProposalsLoading] = useState(false);

  const fetchProposals = async () => {
    if (!project?.id) { toast.info('ابدأ بإنشاء مشروع أولاً'); return; }
    setProposalsLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/propose-designs`, { method: 'POST', headers: authH() });
      const d = await r.json();
      setProposals(d.proposals || []);
      toast.success('🎨 4 تصاميم جاهزة للمعاينة');
    } catch (_) { toast.error('فشل'); }
    finally { setProposalsLoading(false); }
  };

  const applyProposal = async (p) => {
    if (!project?.id) return;
    try {
      await fetch(`${API}/api/websites/projects/${project.id}/apply-proposal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({ mood_id: p.mood_id, layout_id: p.layout_id }),
      });
      // Reload project
      const rr = await fetch(`${API}/api/websites/projects/${project.id}`, { headers: authH() });
      const pr = await rr.json();
      setProject(pr);
      refreshPreview(pr);
      toast.success(`✨ تم تطبيق "${p.name}"`);
      setProposals(null);
    } catch (_) { toast.error('فشل التطبيق'); }
  };
  const openLogoStudio = () => {
    if (!project?.id) { toast.info('ابدأ بإنشاء مشروع أولاً'); return; }
    setLogoStudioOpen(true);
  };
  const onLogoApplied = (url) => {
    setProject((prev) => prev ? ({ ...prev, theme: { ...(prev.theme || {}), logo_url: url } }) : prev);
  };

  const removeLogo = async () => {
    if (!project?.id) return;
    const newTheme = { ...(project.theme || {}) };
    delete newTheme.logo_url;
    setProject({ ...project, theme: newTheme });
    await fetch(`${API}/api/websites/projects/${project.id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json', ...authH() },
      body: JSON.stringify({ ...project, theme: newTheme }),
    });
    toast.success('تم إزالة اللوقو');
  };

  return (
    <div className="h-screen flex flex-col bg-[#0b0f1f] text-white overflow-hidden" dir="rtl" data-testid="website-studio">
      {/* Top bar (hidden in preview fullscreen) */}
      {!fullscreen && (
        <header className="flex items-center justify-between px-3 md:px-4 py-2.5 bg-gradient-to-b from-[#151937] to-[#0e1128] border-b border-yellow-500/20 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <button onClick={() => nav('/')} className="p-2 hover:bg-white/10 rounded-lg shrink-0" data-testid="back-btn"><ArrowLeft className="w-5 h-5" /></button>
            {project ? (
              <>
                <input
                  value={project.name || ''}
                  onChange={(e) => setProject({ ...project, name: e.target.value })}
                  onBlur={() => fetch(`${API}/api/websites/projects/${project.id}`, {
                    method: 'PATCH', headers: { 'Content-Type': 'application/json', ...authH() }, body: JSON.stringify(project),
                  })}
                  className="bg-transparent border-b border-white/10 focus:border-yellow-500 px-2 py-1 text-sm md:text-base font-bold focus:outline-none min-w-0 max-w-[160px] md:max-w-[260px]"
                  data-testid="project-name-input"
                />
                {activeTemplate && (
                  <button
                    onClick={() => { setProject(null); setActiveCategory(null); }}
                    className="hidden md:flex items-center gap-1.5 px-2.5 py-1 bg-yellow-500/10 hover:bg-yellow-500/20 border border-yellow-500/30 rounded-lg text-xs font-bold"
                    title="تغيير القالب"
                    data-testid="change-template-btn"
                  >
                    <span>{activeTemplate.icon}</span>
                    <span>{activeTemplate.name}</span>
                    <RefreshCw className="w-3 h-3" />
                  </button>
                )}
              </>
            ) : (
              <span className="text-base md:text-lg font-bold">استوديو المواقع</span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <button onClick={() => { setProject(null); setActiveCategory(null); }} className="p-2 md:px-3 md:py-2 bg-white/10 hover:bg-white/20 rounded-lg flex items-center gap-1.5" data-testid="new-site-btn">
              <Plus className="w-4 h-4" /><span className="hidden md:inline text-xs">جديد</span>
            </button>
            <button onClick={() => { loadProjects(); setShowLibrary(true); }} className="p-2 md:px-3 md:py-2 bg-white/10 hover:bg-white/20 rounded-lg flex items-center gap-1.5" data-testid="library-btn">
              <FolderOpen className="w-4 h-4" /><span className="hidden md:inline text-xs">مواقعي ({projects.length})</span>
            </button>
            <button onClick={openLogoStudio} disabled={!project} className="p-2 md:px-3 md:py-2 bg-gradient-to-r from-purple-500/20 to-pink-500/20 hover:from-purple-500/30 hover:to-pink-500/30 border border-purple-400/30 rounded-lg flex items-center gap-1.5 disabled:opacity-40" data-testid="gen-logo-btn" title="استوديو توليد اللوقو بالذكاء الاصطناعي">
              <Sparkles className="w-4 h-4 text-purple-300" />
              <span className="hidden md:inline text-xs">اعمل لوقو</span>
            </button>
            <button onClick={() => setTechStackOpen(true)} className="p-2 md:px-3 md:py-2 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 border border-cyan-400/30 rounded-lg flex items-center gap-1.5" data-testid="tech-stack-btn" title="التقنيات المستخدمة">
              <span className="text-base">🧩</span>
              <span className="hidden md:inline text-xs">التقنيات</span>
            </button>
            <button onClick={() => setShowSnapshots(true)} disabled={!project} className="p-2 md:px-3 md:py-2 bg-gradient-to-r from-amber-500/20 to-orange-500/20 hover:from-amber-500/30 hover:to-orange-500/30 border border-amber-400/30 rounded-lg flex items-center gap-1.5 disabled:opacity-40" data-testid="history-btn" title="سجل التصاميم السابقة">
              <span className="text-base">📚</span>
              <span className="hidden md:inline text-xs">السجل</span>
            </button>
            <button onClick={() => setShowEditMode(true)} disabled={!project} className="p-2 md:px-3 md:py-2 bg-gradient-to-r from-violet-500/20 to-fuchsia-500/20 hover:from-violet-500/30 hover:to-fuchsia-500/30 border border-violet-400/30 rounded-lg flex items-center gap-1.5 disabled:opacity-40" data-testid="edit-mode-btn" title="رتّب الأقسام يدوياً">
              <span className="text-base">✏️</span>
              <span className="hidden md:inline text-xs">تعديل</span>
            </button>
            <button onClick={() => setShowPalettePicker(true)} disabled={!project} className="p-2 md:px-3 md:py-2 bg-gradient-to-r from-pink-500/20 to-purple-500/20 hover:from-pink-500/30 hover:to-purple-500/30 border border-pink-400/30 rounded-lg flex items-center gap-1.5 disabled:opacity-40" data-testid="palette-btn" title="غيّر الألوان">
              <span className="text-base">🎨</span>
              <span className="hidden md:inline text-xs">الألوان</span>
            </button>
            {project && project.status !== 'approved' && (
              <button onClick={() => approveProject(project.id)} className="p-2 md:px-3 md:py-2 bg-gradient-to-r from-green-500/30 to-emerald-500/30 hover:from-green-500/50 hover:to-emerald-500/50 border border-green-400/40 rounded-lg flex items-center gap-1.5" data-testid="approve-btn" title="اعتماد نهائي">
                <Check className="w-4 h-4 text-green-300" /><span className="hidden md:inline text-xs font-bold">اعتماد</span>
              </button>
            )}
            {project?.status === 'approved' && (
              <span className="px-2 md:px-3 py-2 bg-green-500 text-black rounded-lg text-xs font-bold flex items-center gap-1" data-testid="approved-badge">
                <Check className="w-4 h-4" /><span className="hidden md:inline">معتمد</span>
              </span>
            )}
            {project?.theme?.logo_url && (
              <button onClick={removeLogo} className="p-2 bg-white/10 hover:bg-red-500/20 rounded-lg" title="إزالة اللوقو" data-testid="remove-logo-btn"><X className="w-4 h-4" /></button>
            )}
            <button onClick={exportHtml} disabled={!project} className="p-2 md:px-3 md:py-2 bg-white/10 hover:bg-white/20 rounded-lg flex items-center gap-1.5 disabled:opacity-40" data-testid="export-btn">
              <Download className="w-4 h-4" /><span className="hidden md:inline text-xs">تصدير</span>
            </button>
          </div>
        </header>
      )}

      {/* Body */}
      {project ? (
        <>
          {/* Mobile tab switcher */}
          {!fullscreen && (
            <div className="md:hidden flex border-b border-white/10 bg-[#0a0e1c]">
              <button
                onClick={() => setMobileView('preview')}
                className={`flex-1 py-2 text-xs font-bold flex items-center justify-center gap-1.5 ${mobileView === 'preview' ? 'bg-yellow-500/20 border-b-2 border-yellow-500' : 'opacity-60'}`}
                data-testid="mobile-tab-preview"
              ><Monitor className="w-3.5 h-3.5" />معاينة</button>
              <button
                onClick={() => setMobileView('chat')}
                className={`flex-1 py-2 text-xs font-bold flex items-center justify-center gap-1.5 ${mobileView === 'chat' ? 'bg-yellow-500/20 border-b-2 border-yellow-500' : 'opacity-60'}`}
                data-testid="mobile-tab-chat"
              ><MessageSquare className="w-3.5 h-3.5" />محادثة</button>
            </div>
          )}

          <div className="flex-1 flex min-h-0 flex-col md:flex-row">
            {/* Preview (always flex on desktop, hidden on mobile unless tab=preview) */}
            <div className={`flex-1 min-h-0 ${mobileView === 'preview' ? 'flex' : 'hidden md:flex'} flex-col`}>
              <PreviewPane
                html={previewHtml}
                project={project}
                fullscreen={fullscreen}
                onToggleFullscreen={() => setFullscreen((f) => !f)}
                onRefresh={() => refreshPreview(project)}
                device={previewDevice}
                onToggleDevice={setPreviewDevice}
              />
            </div>

            {/* Chat column */}
            {!fullscreen && (
              <div className={`${mobileView === 'chat' ? 'flex' : 'hidden md:flex'} md:w-[420px] md:shrink-0 flex-col min-h-0`}>
                <ChatColumn
                  project={project}
                  stepMeta={stepMeta}
                  variants={variants}
                  loading={chatLoading}
                  onSendText={sendChat}
                  proposals={proposals}
                  proposalsLoading={proposalsLoading}
                  onPickProposal={applyProposal}
                  onDismissProposals={() => setProposals(null)}
                  onAnswerStep={(v) => previewAnswer(project?.wizard?.step, v)}
                  onRequestCode={() => setShowIndependence(true)}
                  pending={pending}
                  onConfirm={confirmPending}
                  onCancel={cancelPending}
                />
              </div>
            )}
          </div>
        </>
      ) : (
        activeCategory ? (
          <LayoutBrowser
            category={activeCategory}
            layouts={layouts}
            onBack={() => setActiveCategory(null)}
            onConfirm={confirmLayout}
            loading={loading}
          />
        ) : (
          <CategoryPicker categories={categories} onPick={setActiveCategory} />
        )
      )}

      {showLibrary && <LibraryModal projects={projects} onOpen={openProject} onDelete={deleteProject} onDuplicate={duplicateProject} onApprove={approveProject} onClose={() => setShowLibrary(false)} />}
      {showIndependence && <IndependenceModal onClose={() => setShowIndependence(false)} />}
      {logoStudioOpen && <LogoStudioModal project={project} onClose={() => setLogoStudioOpen(false)} onApplied={onLogoApplied} />}
      {techStackOpen && <TechStackModal onClose={() => setTechStackOpen(false)} />}
      {showSnapshots && project && <SnapshotsGalleryModal project={project} onClose={() => setShowSnapshots(false)} onRestored={(p) => { setProject(p); refreshPreview(p); setShowSnapshots(false); }} />}
      {showEditMode && project && (
        <EditModeModal
          project={project}
          onClose={() => setShowEditMode(false)}
          onSaved={(p) => { setProject(p); refreshPreview(p); setShowEditMode(false); toast.success('✅ تم اعتماد الترتيب الجديد'); }}
        />
      )}
      {showPalettePicker && project && <PalettePickerModal project={project} onClose={() => setShowPalettePicker(false)} onApply={async (pid) => { await applyPalette(pid); }} />}
    </div>
  );
}

/* ================================================================
   🎨 PALETTE PICKER — Phase 2 color step (after template selection)
   ================================================================ */
function PalettePickerModal({ project, onClose, onApply }) {
  const [palettes, setPalettes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(null);
  const currentPrimary = (project?.theme || {}).primary;

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const r = await fetch(`${API}/api/websites/palettes`);
        const d = await r.json();
        setPalettes(d.palettes || []);
      } catch (_) {}
      finally { setLoading(false); }
    })();
  }, []);

  const pick = async (p) => {
    setApplying(p.id);
    try { await onApply(p.id); } finally { setApplying(null); }
  };

  return (
    <div className="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 md:p-6" onClick={onClose} data-testid="palette-picker-modal">
      <div onClick={(e) => e.stopPropagation()} className="bg-[#0e1128] border border-pink-500/30 rounded-2xl w-full max-w-3xl shadow-[0_40px_100px_rgba(236,72,153,0.25)]">
        <div className="p-5 md:p-6 border-b border-white/10 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl md:text-2xl font-black bg-gradient-to-r from-pink-400 to-purple-400 bg-clip-text text-transparent mb-1">
              🎨 اختر الألوان المناسبة لعلامتك
            </h2>
            <p className="text-xs md:text-sm opacity-70">تصميمك جاهز — الآن اختر المزاج اللوني. يمكنك تغييره لاحقاً في أي وقت.</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg shrink-0" data-testid="close-palette-btn"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-5 md:p-6">
          {loading ? (
            <div className="text-center py-10 opacity-60">...</div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
              {palettes.map((p) => {
                const active = p.primary === currentPrimary;
                const busy = applying === p.id;
                return (
                  <button
                    key={p.id}
                    onClick={() => pick(p)}
                    disabled={busy}
                    className={`group relative rounded-2xl p-3 border-2 transition-all ${
                      active ? 'border-pink-500 bg-pink-500/10 shadow-[0_0_20px_rgba(236,72,153,0.3)]' : 'border-white/10 hover:border-pink-400/50'
                    }`}
                    data-testid={`palette-${p.id}`}
                    style={{ background: active ? undefined : `linear-gradient(135deg, ${p.primary}15, ${p.accent}05)` }}
                  >
                    {/* 3 big swatches */}
                    <div className="flex gap-1 mb-2 h-14 rounded-lg overflow-hidden">
                      <div className="flex-1" style={{ background: p.primary }} />
                      <div className="flex-1" style={{ background: p.accent }} />
                      <div className="flex-1" style={{ background: p.secondary }} />
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-sm mb-0.5 truncate">{p.name}</div>
                      <div className="text-[10px] opacity-60">{p.font || 'Tajawal'}</div>
                    </div>
                    {active && (
                      <div className="absolute top-2 left-2 bg-pink-500 text-white rounded-full w-6 h-6 flex items-center justify-center shadow-lg">
                        <Check className="w-3.5 h-3.5" />
                      </div>
                    )}
                    {busy && (
                      <div className="absolute inset-0 bg-black/60 rounded-2xl flex items-center justify-center">
                        <RefreshCw className="w-5 h-5 animate-spin text-pink-400" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
        <div className="p-4 border-t border-white/10 flex items-center justify-between gap-2 flex-wrap">
          <div className="text-xs opacity-60">💡 تقدر تفتح هذه الشاشة في أي وقت من زر "🎨 الألوان"</div>
          <button onClick={onClose} className="px-5 py-2 bg-gradient-to-r from-pink-500 to-purple-500 rounded-lg text-sm font-bold text-white" data-testid="palette-done-btn">
            تم — أكمل الإعداد
          </button>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   ✏️ EDIT MODE — drag-to-reorder sections, then "اعتماد" rebuilds
   ================================================================ */
function EditModeModal({ project, onClose, onSaved }) {
  const [items, setItems] = useState(() =>
    (project.sections || [])
      .slice()
      .sort((a, b) => (a.order || 0) - (b.order || 0))
      .map((s) => ({ id: s.id || s.type, type: s.type, title: s.data?.title || s.type }))
  );
  const [dragIdx, setDragIdx] = useState(null);
  const [overIdx, setOverIdx] = useState(null);
  const [busy, setBusy] = useState(false);

  const moveItem = (from, to) => {
    if (from === to || from < 0 || to < 0) return;
    setItems((prev) => {
      const copy = [...prev];
      const [taken] = copy.splice(from, 1);
      copy.splice(to, 0, taken);
      return copy;
    });
  };

  const moveBy = (idx, delta) => {
    moveItem(idx, Math.max(0, Math.min(items.length - 1, idx + delta)));
  };

  const save = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/reorder-sections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({ section_ids: items.map((i) => i.id) }),
      });
      if (!r.ok) throw new Error('reorder failed');
      const p = await r.json();
      onSaved(p);
    } catch (_) {
      toast.error('فشل اعتماد الترتيب');
    } finally {
      setBusy(false);
    }
  };

  // Cosmetic mapping of section type → emoji/label for prettier UI
  const TYPE_META = {
    hero: { icon: '🎬', label: 'القسم الرئيسي (Hero)' },
    about: { icon: '📖', label: 'عن النشاط' },
    services: { icon: '⚙️', label: 'الخدمات' },
    products: { icon: '🛒', label: 'المنتجات' },
    menu: { icon: '🍽️', label: 'القائمة' },
    gallery: { icon: '🖼️', label: 'معرض الصور' },
    testimonials: { icon: '⭐', label: 'آراء العملاء' },
    team: { icon: '👥', label: 'الفريق' },
    features: { icon: '✨', label: 'الميزات' },
    contact: { icon: '📞', label: 'تواصل معنا' },
    footer: { icon: '🔻', label: 'التذييل' },
    stats: { icon: '📊', label: 'إحصائيات' },
    cta: { icon: '🎯', label: 'دعوة للعمل' },
    quote: { icon: '💬', label: 'اقتباس' },
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose} data-testid="edit-mode-modal">
      <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-violet-500/30 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
          <div>
            <h3 className="text-xl font-black flex items-center gap-2">
              <span className="text-2xl">✏️</span> رتّب أقسام الموقع بالشكل اللي تريده
            </h3>
            <p className="text-xs text-white/50 mt-0.5">اسحب أي قسم لأعلى/أسفل أو استخدم الأسهم — ثم اضغط "اعتماد" لإعادة البناء</p>
          </div>
          <button onClick={onClose} className="text-white/60 hover:text-white text-2xl leading-none" data-testid="edit-mode-close">×</button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-2">
          {items.map((item, idx) => {
            const meta = TYPE_META[item.type] || { icon: '📄', label: item.type };
            const isDragging = dragIdx === idx;
            const isOver = overIdx === idx && dragIdx !== null && dragIdx !== idx;
            return (
              <div
                key={item.id}
                draggable
                onDragStart={() => setDragIdx(idx)}
                onDragOver={(e) => { e.preventDefault(); setOverIdx(idx); }}
                onDragLeave={() => setOverIdx(null)}
                onDrop={(e) => { e.preventDefault(); if (dragIdx !== null) moveItem(dragIdx, idx); setDragIdx(null); setOverIdx(null); }}
                onDragEnd={() => { setDragIdx(null); setOverIdx(null); }}
                className={`p-3 rounded-xl border-2 flex items-center gap-3 cursor-grab active:cursor-grabbing transition-all ${
                  isDragging ? 'opacity-40' : ''
                } ${isOver ? 'border-fuchsia-400 bg-fuchsia-500/15 -translate-y-1' : 'border-white/10 bg-white/5 hover:border-violet-400/40'}`}
                data-testid={`edit-section-${item.id}`}
              >
                <div className="text-violet-300 text-lg cursor-grab select-none" title="اسحب">⋮⋮</div>
                <div className="text-3xl">{meta.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-sm">{meta.label}</div>
                  <div className="text-[11px] text-white/50 truncate">{item.title || item.type}</div>
                </div>
                <div className="flex flex-col gap-1">
                  <button
                    onClick={() => moveBy(idx, -1)}
                    disabled={idx === 0}
                    className="w-7 h-7 rounded-md bg-white/5 hover:bg-violet-500/30 disabled:opacity-30 text-sm"
                    data-testid={`move-up-${item.id}`}
                    title="أعلى"
                  >▲</button>
                  <button
                    onClick={() => moveBy(idx, 1)}
                    disabled={idx === items.length - 1}
                    className="w-7 h-7 rounded-md bg-white/5 hover:bg-violet-500/30 disabled:opacity-30 text-sm"
                    data-testid={`move-down-${item.id}`}
                    title="أسفل"
                  >▼</button>
                </div>
              </div>
            );
          })}
        </div>
        <div className="border-t border-white/10 p-4 flex gap-3 bg-black/30">
          <button onClick={onClose} className="flex-1 py-3 rounded-xl bg-white/5 hover:bg-white/10 font-bold text-sm" data-testid="edit-mode-cancel">إلغاء</button>
          <button
            onClick={save}
            disabled={busy}
            className="flex-[2] py-3 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:from-violet-600 hover:to-fuchsia-600 font-black text-sm disabled:opacity-50"
            data-testid="edit-mode-save"
          >
            {busy ? '⏳ جارٍ الإعادة...' : '✅ اعتماد الترتيب وإعادة البناء'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   📚 SNAPSHOTS GALLERY — version history for the studio (owner)
   ================================================================ */
function SnapshotsGalleryModal({ project, onClose, onRestored }) {
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState(null); // { id, html, label }
  const [label, setLabel] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/snapshots`, { headers: authH() });
      const d = await r.json();
      setSnapshots(d.snapshots || []);
    } catch (_) {} finally { setLoading(false); }
  }, [project.id]);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setBusy(true);
    try {
      await fetch(`${API}/api/websites/projects/${project.id}/snapshots`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({ label: (label || 'نسخة').trim().slice(0, 60) }),
      });
      setLabel('');
      toast.success('تم حفظ النسخة');
      load();
    } catch (_) { toast.error('فشل الحفظ'); } finally { setBusy(false); }
  };

  const openPreview = async (s) => {
    setPreview({ ...s, html: null });
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/snapshots/${s.id}/preview-html`, { headers: authH() });
      const d = await r.json();
      setPreview({ ...s, html: d.html || '' });
    } catch (_) { toast.error('فشل'); setPreview(null); }
  };

  const restore = async (s) => {
    if (!window.confirm(`استعادة "${s.label}"؟\nسيُحفظ تصميمك الحالي كنسخة قبل الاستعادة.`)) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/websites/projects/${project.id}/snapshots/${s.id}/restore`, { method: 'POST', headers: authH() });
      const d = await r.json();
      if (!r.ok) throw new Error();
      toast.success('✅ تمّت الاستعادة');
      onRestored(d);
    } catch (_) { toast.error('فشلت الاستعادة'); }
    finally { setBusy(false); }
  };

  const del = async (s) => {
    if (!window.confirm(`حذف نسخة "${s.label}"؟`)) return;
    try {
      await fetch(`${API}/api/websites/projects/${project.id}/snapshots/${s.id}`, { method: 'DELETE', headers: authH() });
      toast.success('تم الحذف');
      load();
    } catch (_) {}
  };

  const originBadge = (o) => {
    const map = {
      manual: { l: '✋ يدوي', c: 'bg-yellow-500/20 text-yellow-300' },
      wizard: { l: '🧭 مرشد', c: 'bg-blue-500/20 text-blue-300' },
      ai_chat: { l: '🤖 ذكاء', c: 'bg-purple-500/20 text-purple-300' },
      variant: { l: '🎨 نمط', c: 'bg-pink-500/20 text-pink-300' },
      auto: { l: '⚙️', c: 'bg-white/10 text-white/70' },
    };
    const m = map[o] || map.auto;
    return <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${m.c}`}>{m.l}</span>;
  };

  return (
    <div className="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm flex items-center justify-center p-2 md:p-6" onClick={onClose} data-testid="snapshots-gallery-modal">
      <div onClick={(e) => e.stopPropagation()} className="bg-[#0e1128] border border-amber-500/30 rounded-2xl w-full max-w-6xl h-[90vh] flex flex-col overflow-hidden">
        <div className="p-4 border-b border-white/10 flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="text-lg md:text-xl font-black flex items-center gap-2">📚 سجل تصاميم "{project.name || 'موقعك'}"</h2>
            <p className="text-xs opacity-60">كل تعديل يُحفظ تلقائياً. اضغط معاينة لرؤية أي نسخة، ثم "استعد" للرجوع لها.</p>
          </div>
          <div className="flex items-center gap-2">
            <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="اسم النسخة (اختياري)" className="px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" data-testid="owner-snap-label" />
            <button onClick={save} disabled={busy} className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-black rounded-lg text-sm font-bold" data-testid="owner-save-snap">احفظ النسخة</button>
            <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg"><X className="w-5 h-5" /></button>
          </div>
        </div>
        <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
          <div className="md:w-1/3 overflow-y-auto p-3 space-y-2 border-b md:border-b-0 md:border-l border-white/10" style={{ maxHeight: '100%' }}>
            {loading ? (
              <div className="text-center py-10 opacity-60">...</div>
            ) : snapshots.length === 0 ? (
              <div className="text-center py-10 opacity-60 text-sm">لا نسخ بعد — ستظهر تلقائياً بعد أي تعديل</div>
            ) : (
              snapshots.map((s) => {
                const active = preview && preview.id === s.id;
                return (
                  <button key={s.id} onClick={() => openPreview(s)} className={`w-full text-right p-3 rounded-xl border transition ${active ? 'bg-amber-500/20 border-amber-500' : 'bg-white/3 border-white/10 hover:bg-white/6'}`} data-testid={`owner-snap-${s.id}`}>
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="font-bold text-sm">{s.label}</span>
                      {originBadge(s.origin)}
                    </div>
                    <div className="text-[11px] opacity-60 flex justify-between">
                      <span>{new Date(s.created_at).toLocaleString('ar-SA')}</span>
                      <span>{s.sections_count} قسم</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
          <div className="flex-1 bg-white flex flex-col">
            {preview ? (
              <>
                <div className="bg-[#0e1128] p-3 flex items-center gap-2 flex-wrap border-b border-white/10 text-white">
                  <div className="flex-1 min-w-0">
                    <div className="font-bold truncate">{preview.label}</div>
                    <div className="text-[11px] opacity-60">{new Date(preview.created_at).toLocaleString('ar-SA')}</div>
                  </div>
                  <button onClick={() => restore(preview)} disabled={busy} className="px-4 py-2 bg-green-500 hover:bg-green-600 text-black rounded-lg text-sm font-bold" data-testid="owner-restore-btn">استعد هذه النسخة</button>
                  <button onClick={() => del(preview)} className="p-2 bg-red-500/20 hover:bg-red-500/40 rounded-lg"><X className="w-4 h-4" /></button>
                </div>
                <div className="flex-1">
                  {preview.html === null ? (
                    <div className="h-full flex items-center justify-center text-black opacity-60">جاري التحميل...</div>
                  ) : (
                    <iframe srcDoc={preview.html} title="preview" className="w-full h-full border-0" sandbox="allow-scripts allow-same-origin" />
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-black opacity-40">اختر نسخة من اليمين لمعاينتها</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
