import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const STEP_LABELS = [
  { id: 1, label: 'النوع' },
  { id: 2, label: 'الفيديو' },
  { id: 3, label: 'النمط' },
  { id: 4, label: 'العلامة' },
  { id: 5, label: 'الميزات' },
  { id: 6, label: 'التوليد' },
];

const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
});

const post = async (path, body) => {
  const r = await fetch(`${API}/api/ready-sites${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(body || {}),
  });
  if (!r.ok) {
    const t = await r.text().catch(() => '');
    throw new Error(`${r.status}: ${t || r.statusText}`);
  }
  return r.json();
};

const getCatalog = async () => {
  const r = await fetch(`${API}/api/ready-sites/catalog`);
  return r.json();
};

export default function ReadySites({ user }) {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [catalog, setCatalog] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const [typeId, setTypeId] = useState(null);
  const [patternId, setPatternId] = useState(null);
  const [branding, setBranding] = useState({
    business_name: '',
    tagline: '',
    logo_mode: 'text',
    logo_url: '',
    logo_text: '',
    logo_ai_prompt: '',
  });
  const [enabled, setEnabled] = useState([]);
  const [readyInfo, setReadyInfo] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      navigate('/login');
      return;
    }
    getCatalog().then(setCatalog).catch(() => toast.error('فشل تحميل الكتالوج'));
  }, [navigate]);

  const ensureSession = async () => {
    if (sessionId) return sessionId;
    const { session_id } = await post('/start', {});
    setSessionId(session_id);
    return session_id;
  };

  const restaurantPatterns = catalog?.patterns?.restaurant || [];
  const restaurantFeatures = catalog?.features?.restaurant || [];

  const featureCategories = useMemo(() => {
    const g = {};
    restaurantFeatures.forEach((f) => {
      g[f.category] = g[f.category] || [];
      g[f.category].push(f);
    });
    return g;
  }, [restaurantFeatures]);

  const handlePickType = async (tid) => {
    if (!catalog) return;
    const t = catalog.types.find((x) => x.id === tid);
    if (t && !t.available) {
      toast.info('هذا النوع قريباً — حالياً المطاعم فقط متاحة');
      return;
    }
    setBusy(true);
    try {
      const sid = await ensureSession();
      await post('/select-type', { session_id: sid, type_id: tid });
      setTypeId(tid);
      setStep(2);  // → promo video
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handlePickPattern = async (pid) => {
    setBusy(true);
    try {
      await post('/select-pattern', { session_id: sessionId, pattern_id: pid });
      setPatternId(pid);
      setStep(4);  // → branding
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleBranding = async () => {
    if (!branding.business_name.trim()) {
      toast.error('اكتب اسم المطعم');
      return;
    }
    setBusy(true);
    try {
      const res = await post('/branding', { session_id: sessionId, ...branding });
      const def = res.default_enabled || [];
      setEnabled(def);
      setStep(5);  // → features
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleFeatures = async () => {
    if (enabled.length === 0) {
      toast.error('اختر ميزة واحدة على الأقل');
      return;
    }
    setBusy(true);
    try {
      const res = await post('/features', { session_id: sessionId, enabled });
      setReadyInfo(res);
      setStep(6);  // → generate
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await post('/generate', { session_id: sessionId });
      // Poll status every 3s for up to 5 minutes
      const deadline = Date.now() + 5 * 60 * 1000;
      // eslint-disable-next-line no-constant-condition
      while (true) {
        if (Date.now() > deadline) throw new Error('انتهت المهلة');
        await new Promise((r) => setTimeout(r, 3000));
        const r = await fetch(`${API}/api/ready-sites/status/${sessionId}`, { headers: authHeaders() });
        const s = await r.json();
        if (s.phase === 'done' && s.project_id) {
          setGenerated({ project_id: s.project_id, preview_url: s.preview_url });
          toast.success('تم بناء موقعك بنجاح');
          break;
        }
        if (s.phase === 'ready' && s.error) {
          throw new Error(s.error);
        }
      }
    } catch (e) {
      toast.error(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const toggleFeature = (fid) => {
    setEnabled((prev) => (prev.includes(fid) ? prev.filter((x) => x !== fid) : [...prev, fid]));
  };

  if (!catalog) {
    return (
      <div style={shellStyle} data-testid="ready-sites-loading">
        <div style={{ color: '#aaa', padding: 40 }}>جاري التحميل…</div>
      </div>
    );
  }

  return (
    <div style={shellStyle} dir="rtl" data-testid="ready-sites-page">
      <div style={containerStyle}>
        <Header step={step} />

        {step === 1 && (
          <StepTypes types={catalog.types} onPick={handlePickType} busy={busy} />
        )}
        {step === 2 && (
          <StepPromoVideo
            typeId={typeId}
            type={catalog.types.find((t) => t.id === typeId)}
            onContinue={() => setStep(3)}
            onBack={() => setStep(1)}
          />
        )}
        {step === 3 && (
          <StepPatterns
            patterns={restaurantPatterns}
            onPick={handlePickPattern}
            busy={busy}
            onBack={() => setStep(2)}
          />
        )}
        {step === 4 && (
          <StepBranding
            value={branding}
            onChange={setBranding}
            onNext={handleBranding}
            onBack={() => setStep(3)}
            busy={busy}
          />
        )}
        {step === 5 && (
          <StepFeatures
            groups={featureCategories}
            enabled={enabled}
            toggle={toggleFeature}
            onNext={handleFeatures}
            onBack={() => setStep(4)}
            busy={busy}
          />
        )}
        {step === 6 && (
          <StepGenerate
            cost={catalog.generate_cost}
            readyInfo={readyInfo}
            generating={generating}
            generated={generated}
            onGenerate={handleGenerate}
            onBack={() => setStep(5)}
          />
        )}
      </div>
    </div>
  );
}

/* ============== Sub-components ============== */

function Header({ step }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
        <div>
          <div style={{ fontSize: 12, color: '#fbbf24', letterSpacing: 4, marginBottom: 6 }}>ZITEX · المواقع الجاهزة</div>
          <h1 style={{ fontSize: 36, fontWeight: 900, margin: 0, lineHeight: 1, background: 'linear-gradient(90deg,#fbbf24,#ec4899)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            ابنِ موقع مطعمك في 6 خطوات
          </h1>
          <p style={{ color: '#9ca3af', marginTop: 8, fontSize: 14 }}>AI يبني من الصفر · 6 أنماط بصرية حصرية · 24 ميزة كاملة</p>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        {STEP_LABELS.map((s) => (
          <div
            key={s.id}
            data-testid={`step-indicator-${s.id}`}
            style={{
              flex: 1,
              padding: '10px 12px',
              borderRadius: 12,
              background: s.id <= step ? 'linear-gradient(90deg,#f59e0b,#ec4899)' : '#171717',
              color: s.id <= step ? '#000' : '#666',
              fontWeight: 700,
              fontSize: 12,
              textAlign: 'center',
              border: s.id === step ? '1px solid #fff' : '1px solid #222',
            }}
          >
            {s.id}. {s.label}
          </div>
        ))}
      </div>
    </div>
  );
}

function StepTypes({ types, onPick, busy }) {
  return (
    <div>
      <h2 style={sectionTitle}>1️⃣ اختر نوع موقعك</h2>
      <div style={gridStyle(2)}>
        {types.map((t) => (
          <button
            key={t.id}
            data-testid={`type-card-${t.id}`}
            disabled={busy || !t.available}
            onClick={() => onPick(t.id)}
            style={{
              ...tileStyle,
              opacity: t.available ? 1 : 0.45,
              cursor: t.available ? 'pointer' : 'not-allowed',
              borderColor: t.available ? '#333' : '#1a1a1a',
            }}
          >
            <div style={{ height: 6, background: t.preview_color, borderRadius: 99, width: 60, marginBottom: 14 }} />
            <div style={{ fontWeight: 900, fontSize: 20, color: '#fff', marginBottom: 6 }}>{t.name_ar}</div>
            <div style={{ color: '#888', fontSize: 13 }}>{t.tagline_ar}</div>
            {!t.available && (
              <div style={{ marginTop: 14, fontSize: 11, color: '#f59e0b', fontWeight: 700 }}>قريباً</div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function StepPromoVideo({ typeId, type, onContinue, onBack }) {
  // Inline animated CSS showcase (always loads, no external video deps).
  // FUTURE: replace with real Sora 2 AI-generated promo per business name & cuisine.
  const poster = type?.preview_color || '#f59e0b';
  const showcaseImages = {
    restaurant: [
      'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=1200&q=80',
      'https://images.unsplash.com/photo-1551782450-a2132b4ba21d?w=1200&q=80',
      'https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=1200&q=80',
      'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=1200&q=80',
    ],
  };
  const images = showcaseImages[typeId] || showcaseImages.restaurant;
  return (
    <div data-testid="step-promo-video">
      <h2 style={sectionTitle}>🎬 معاينة تجربتك</h2>
      <p style={{ color: '#9ca3af', marginBottom: 22, fontSize: 14 }}>
        نموذج لنوع التجربة اللي بنبنيها لك. شوف الإيقاع واستمر لاختيار النمط البصري.
      </p>
      <style>{`
        @keyframes rsPromoSlide {
          0%,22% { opacity:1; transform:scale(1.05) }
          25%,100% { opacity:0; transform:scale(1) }
        }
        .rs-frame { position:absolute; inset:0; background-size:cover; background-position:center; opacity:0; animation: rsPromoSlide 16s infinite; }
        .rs-frame.f0 { animation-delay: 0s }
        .rs-frame.f1 { animation-delay: 4s }
        .rs-frame.f2 { animation-delay: 8s }
        .rs-frame.f3 { animation-delay: 12s }
        @keyframes rsPromoText {
          0%,15% { opacity:0; transform:translateY(20px) }
          22%,78% { opacity:1; transform:translateY(0) }
          85%,100% { opacity:0; transform:translateY(-20px) }
        }
        .rs-text { animation: rsPromoText 4s ease-in-out infinite; }
        @keyframes rsPromoDot {
          0%,22% { background:#fbbf24; transform:scale(1.4) }
          25%,100% { background:#333; transform:scale(1) }
        }
        .rs-dot { animation: rsPromoDot 16s infinite; }
      `}</style>
      <div data-testid="promo-video" style={{ ...cardStyle, padding: 0, overflow: 'hidden', borderRadius: 22, position: 'relative', height: 460, background: '#000', marginBottom: 14 }}>
        {images.map((src, i) => (
          <div key={i} className={`rs-frame f${i}`} style={{ backgroundImage: `url(${src})` }} />
        ))}
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(0,0,0,.15) 0%, rgba(0,0,0,.55) 60%, rgba(0,0,0,.92) 100%)' }} />
        <div style={{ position: 'absolute', top: 20, left: 20, padding: '8px 16px', borderRadius: 99, background: 'rgba(0,0,0,.75)', backdropFilter: 'blur(20px)', color: poster, fontWeight: 900, fontSize: 11, letterSpacing: 2, border: `1px solid ${poster}40`, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 8, height: 8, borderRadius: 99, background: poster, boxShadow: `0 0 12px ${poster}` }} />
          مباشر · PROMO
        </div>
        <div className="rs-text" style={{ position: 'absolute', bottom: 36, right: 36, left: 36, textAlign: 'right' }}>
          <div style={{ fontSize: 48, fontWeight: 900, color: '#fff', textShadow: '0 4px 30px rgba(0,0,0,.9)', marginBottom: 12, background: 'linear-gradient(90deg,#fff,#fbbf24)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', lineHeight: 1 }}>
            {type?.name_ar}
          </div>
          <div style={{ color: '#fff', opacity: .92, fontSize: 16, textShadow: '0 2px 20px rgba(0,0,0,1)', maxWidth: 600 }}>
            {type?.tagline_ar}
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14, justifyContent: 'center' }}>
        {images.map((_, i) => (
          <span key={i} className="rs-dot" style={{ width: 8, height: 8, borderRadius: 99, background: '#333', animationDelay: `${i * 4}s` }} />
        ))}
      </div>
      <div style={navRow}>
        <button data-testid="back-btn" onClick={onBack} style={ghostBtn}>← رجوع</button>
        <button data-testid="promo-continue-btn" onClick={onContinue} style={primaryBtn}>التالي — اختر النمط ←</button>
      </div>
    </div>
  );
}


function StepPatterns({ patterns, onPick, busy, onBack }) {
  return (
    <div>
      <h2 style={sectionTitle}>3️⃣ اختر النمط البصري</h2>
      <p style={{ color: '#9ca3af', marginBottom: 22, fontSize: 14 }}>كل نمط يضم نفس الـ24 ميزة، لكن AI يبني التصميم من الصفر بأسلوب مختلف.</p>
      <div style={gridStyle(2)}>
        {patterns.map((p) => (
          <button
            key={p.id}
            data-testid={`pattern-card-${p.id}`}
            disabled={busy}
            onClick={() => onPick(p.id)}
            style={{ ...tileStyle, padding: 0, overflow: 'hidden' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', background: 'linear-gradient(90deg,#1a1a1a,#0a0a0a)' }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 18, fontWeight: 900, color: '#fff' }}>{p.name_ar}</div>
                <div style={{ fontSize: 11, color: '#888', marginTop: 4, letterSpacing: 2 }}>{p.vibe}</div>
              </div>
              <div style={{ display: 'flex', gap: 4 }}>
                {(p.palette || []).slice(0, 5).map((c, i) => (
                  <span key={i} style={{ width: 18, height: 18, borderRadius: 99, background: c, border: '1px solid #333' }} />
                ))}
              </div>
            </div>
            <iframe
              src={p.preview_url || `/patterns/${p.id}.html`}
              title={p.name}
              style={{ width: '100%', height: 300, border: 0, background: '#000', pointerEvents: 'none' }}
              scrolling="no"
            />
          </button>
        ))}
      </div>
      <div style={navRow}>
        <button data-testid="back-btn" onClick={onBack} style={ghostBtn}>← رجوع</button>
      </div>
    </div>
  );
}

function StepBranding({ value, onChange, onNext, onBack, busy }) {
  const update = (patch) => onChange({ ...value, ...patch });
  const handleFile = (file) => {
    if (!file) return;
    if (file.size > 1024 * 1024 * 2) {
      toast.error('حجم الصورة كبير — الحد الأقصى 2MB');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => update({ logo_url: String(reader.result || '') });
    reader.readAsDataURL(file);
  };
  return (
    <div>
      <h2 style={sectionTitle}>4️⃣ هوية مطعمك</h2>
      <div style={cardStyle}>
        <Field label="اسم المطعم">
          <input
            data-testid="business-name-input"
            value={value.business_name}
            onChange={(e) => update({ business_name: e.target.value })}
            placeholder="مثال: مطعم زعتر"
            style={inputStyle}
          />
        </Field>
        <Field label="شعار قصير (اختياري)">
          <input
            data-testid="tagline-input"
            value={value.tagline}
            onChange={(e) => update({ tagline: e.target.value })}
            placeholder="مذاق الأصالة، طازج كل يوم"
            style={inputStyle}
          />
        </Field>
        <Field label="اللوجو">
          <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
            {[
              { id: 'text', label: 'نص فقط' },
              { id: 'upload', label: 'رفع صورة' },
              { id: 'ai', label: 'تصميم AI' },
            ].map((m) => (
              <button
                key={m.id}
                data-testid={`logo-mode-${m.id}`}
                onClick={() => update({ logo_mode: m.id })}
                style={{
                  flex: 1,
                  padding: 12,
                  borderRadius: 10,
                  border: value.logo_mode === m.id ? '1px solid #fbbf24' : '1px solid #2a2a2a',
                  background: value.logo_mode === m.id ? 'rgba(245,158,11,.1)' : '#111',
                  color: '#fff',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: 13,
                }}
              >
                {m.label}
              </button>
            ))}
          </div>
          {value.logo_mode === 'text' && (
            <input
              data-testid="logo-text-input"
              value={value.logo_text}
              onChange={(e) => update({ logo_text: e.target.value })}
              placeholder="النص الذي يظهر كلوجو (اتركه فارغاً لاستخدام اسم المطعم)"
              style={inputStyle}
            />
          )}
          {value.logo_mode === 'upload' && (
            <div>
              <input
                type="file"
                accept="image/*"
                data-testid="logo-upload-input"
                onChange={(e) => handleFile(e.target.files?.[0])}
                style={{ color: '#aaa', fontSize: 13 }}
              />
              {value.logo_url && (
                <div style={{ marginTop: 10 }}>
                  <img src={value.logo_url} alt="logo" style={{ maxHeight: 60, background: '#fff', padding: 8, borderRadius: 6 }} />
                </div>
              )}
            </div>
          )}
          {value.logo_mode === 'ai' && (
            <input
              data-testid="logo-ai-prompt-input"
              value={value.logo_ai_prompt}
              onChange={(e) => update({ logo_ai_prompt: e.target.value })}
              placeholder="مثال: لوجو لمطعم ايطالي يدمج زيتونة وخط أنيق"
              style={inputStyle}
            />
          )}
        </Field>
      </div>
      <div style={navRow}>
        <button data-testid="back-btn" onClick={onBack} style={ghostBtn}>← رجوع</button>
        <button data-testid="branding-next-btn" disabled={busy} onClick={onNext} style={primaryBtn}>التالي ←</button>
      </div>
    </div>
  );
}

function StepFeatures({ groups, enabled, toggle, onNext, onBack, busy }) {
  const labels = { core: 'الأساسيات', marketing: 'تسويق', social: 'تفاعل', operations: 'تشغيل', admin: 'إدارة' };
  return (
    <div>
      <h2 style={sectionTitle}>5️⃣ الميزات (مفعّلة تلقائياً)</h2>
      <p style={{ color: '#9ca3af', marginBottom: 18, fontSize: 14 }}>كل المطاعم تحصل على 24 ميزة كاملة. اضغط على الميزة لإلغاء تفعيلها.</p>
      {Object.keys(groups).map((cat) => (
        <div key={cat} style={{ marginBottom: 22 }}>
          <div style={{ color: '#fbbf24', fontWeight: 900, fontSize: 13, marginBottom: 10, letterSpacing: 1 }}>
            {labels[cat] || cat} · {groups[cat].length}
          </div>
          <div style={gridStyle(3)}>
            {groups[cat].map((f) => {
              const on = enabled.includes(f.id);
              return (
                <button
                  key={f.id}
                  data-testid={`feature-${f.id}`}
                  onClick={() => toggle(f.id)}
                  style={{
                    textAlign: 'right',
                    padding: 14,
                    borderRadius: 14,
                    border: on ? '1px solid #f59e0b' : '1px solid #222',
                    background: on ? 'rgba(245,158,11,.08)' : '#0e0e0e',
                    color: on ? '#fff' : '#999',
                    cursor: 'pointer',
                    fontSize: 13,
                    fontWeight: 700,
                    transition: 'all .15s',
                  }}
                >
                  {on ? '✓ ' : ''}{f.name_ar}
                </button>
              );
            })}
          </div>
        </div>
      ))}
      <div style={navRow}>
        <button data-testid="back-btn" onClick={onBack} style={ghostBtn}>← رجوع</button>
        <button data-testid="features-next-btn" disabled={busy} onClick={onNext} style={primaryBtn}>
          التالي ({enabled.length} ميزة) ←
        </button>
      </div>
    </div>
  );
}

function StepGenerate({ cost, readyInfo, generating, generated, onGenerate, onBack }) {
  if (generated) {
    return <SuccessPanel generated={generated} />;
  }

  return (
    <div>
      <h2 style={sectionTitle}>6️⃣ توليد الموقع</h2>
      <div style={cardStyle}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16, marginBottom: 22 }}>
          <Metric label="التكلفة" value={`${cost} نقطة`} />
          <Metric label="رصيدك" value={`${readyInfo?.credits_balance ?? 0}`} />
          <Metric label="الميزات" value={`${readyInfo?.features_count ?? 0}`} />
        </div>
        {!readyInfo?.can_afford && (
          <div data-testid="not-enough-credits" style={{ background: 'rgba(220,38,38,.1)', border: '1px solid #dc2626', padding: 14, borderRadius: 10, color: '#fca5a5', fontSize: 13, marginBottom: 16 }}>
            رصيدك لا يكفي. اشحن الشعلات من <a href="/billing" style={{ color: '#fbbf24' }}>صفحة الفوترة</a>.
          </div>
        )}
        <button
          data-testid="generate-btn"
          disabled={generating || !readyInfo?.can_afford}
          onClick={onGenerate}
          style={{ ...primaryBtn, width: '100%', padding: '18px', fontSize: 16, opacity: generating ? 0.7 : 1 }}
        >
          {generating ? '⏳ Claude يبني الموقع... قد يستغرق 60-120 ثانية' : '🚀 ابدأ التوليد'}
        </button>
      </div>
      <div style={navRow}>
        <button data-testid="back-btn" disabled={generating} onClick={onBack} style={ghostBtn}>← رجوع</button>
      </div>
    </div>
  );
}

/* ============== Success Panel (Preview + Admin Creds + AI Refinement Chat) ============== */

function SuccessPanel({ generated }) {
  const [project, setProject] = useState(null);
  const [refineMsg, setRefineMsg] = useState('');
  const [refining, setRefining] = useState(false);
  const [history, setHistory] = useState([]);
  const [iframeKey, setIframeKey] = useState(0);
  const previewUrl = `${API}${generated.preview_url}`;

  useEffect(() => {
    fetch(`${API}/api/ready-sites/project/${generated.project_id}`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((p) => {
        setProject(p);
        setHistory(p.refinement_history || []);
      })
      .catch(() => {});
  }, [generated.project_id]);

  const handleRefine = async () => {
    if (!refineMsg.trim() || refineMsg.trim().length < 3) {
      toast.error('اكتب طلب التعديل بوضوح');
      return;
    }
    setRefining(true);
    try {
      const r = await fetch(`${API}/api/ready-sites/refine/${generated.project_id}`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ message: refineMsg.trim() }),
      });
      if (!r.ok) {
        const t = await r.text();
        throw new Error(t.slice(0, 200));
      }
      const res = await r.json();
      setHistory((h) => [
        ...h,
        { version: res.version, message: refineMsg.trim(), timestamp: new Date().toISOString() },
      ]);
      setRefineMsg('');
      setIframeKey((k) => k + 1); // force iframe reload
      toast.success(`تم التعديل · إصدار ${res.version}`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setRefining(false);
    }
  };

  const copy = (text, label) => {
    navigator.clipboard.writeText(text);
    toast.success(`تم نسخ ${label}`);
  };

  const creds = project?.admin_credentials;
  const adminUrl = `${previewUrl}?admin=1`;
  const driverUrl = `${previewUrl}?driver=1`;

  return (
    <div data-testid="ready-sites-success">
      <h2 style={sectionTitle}>✅ تم بناء موقعك — كل اللي تحتاجه جاهز</h2>

      {/* Admin credentials card */}
      {creds && (
        <div data-testid="admin-credentials-card" style={{ ...cardStyle, background: 'linear-gradient(135deg,#0f1e0f,#0e0e0e)', borderColor: '#22c55e30' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <span style={{ fontSize: 22 }}>🔐</span>
            <div>
              <div style={{ fontWeight: 900, color: '#22c55e', fontSize: 15 }}>بيانات الدخول للوحة التحكم</div>
              <div style={{ color: '#888', fontSize: 12, marginTop: 2 }}>احفظها — تستخدمها لإدارة الطلبات والقائمة والحجوزات</div>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <CredField label="البريد" value={creds.email} onCopy={() => copy(creds.email, 'البريد')} />
            <CredField label="كلمة المرور" value={creds.password} onCopy={() => copy(creds.password, 'كلمة المرور')} mono />
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 14, flexWrap: 'wrap' }}>
            <a href={adminUrl} target="_blank" rel="noopener noreferrer" data-testid="admin-link" style={{ ...ghostBtn, borderColor: '#22c55e', color: '#22c55e', padding: '10px 20px', textDecoration: 'none' }}>
              افتح لوحة التحكم ↗
            </a>
            <a href={driverUrl} target="_blank" rel="noopener noreferrer" data-testid="driver-link" style={{ ...ghostBtn, padding: '10px 20px', textDecoration: 'none' }}>
              تطبيق السائق ↗
            </a>
          </div>
        </div>
      )}

      {/* Preview */}
      <div style={{ ...cardStyle, padding: 0, overflow: 'hidden' }}>
        <div style={{ background: '#1a1a1a', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid #222' }}>
          <span style={{ width: 10, height: 10, borderRadius: 99, background: '#ef4444' }} />
          <span style={{ width: 10, height: 10, borderRadius: 99, background: '#f59e0b' }} />
          <span style={{ width: 10, height: 10, borderRadius: 99, background: '#22c55e' }} />
          <span style={{ flex: 1, fontSize: 11, color: '#666', textAlign: 'center' }}>{previewUrl}</span>
        </div>
        <iframe
          key={iframeKey}
          data-testid="ready-sites-preview-iframe"
          src={previewUrl}
          title="preview"
          style={{ width: '100%', height: 640, border: 0, background: '#fff' }}
        />
      </div>

      {/* AI Refinement Chat */}
      <div data-testid="refine-chat-panel" style={{ ...cardStyle, background: 'linear-gradient(135deg,#0e0820,#0e0e0e)', borderColor: '#a855f730' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <span style={{ fontSize: 22 }}>💬</span>
          <div>
            <div style={{ fontWeight: 900, color: '#c084fc', fontSize: 15 }}>عدّل موقعك بالـ AI</div>
            <div style={{ color: '#888', fontSize: 12, marginTop: 2 }}>اكتب أي تعديل بلغتك — لون، نص، قسم جديد. كل تعديل بـ 5 نقاط فقط</div>
          </div>
        </div>
        <textarea
          data-testid="refine-input"
          value={refineMsg}
          onChange={(e) => setRefineMsg(e.target.value)}
          placeholder="مثال: غيّر لون الخلفية للأخضر الغامق، أضف قسم 'وصفاتنا الخاصة'، صغّر حجم خط القائمة"
          rows={3}
          disabled={refining}
          style={{ ...inputStyle, resize: 'vertical', minHeight: 80 }}
        />
        <div style={{ display: 'flex', gap: 10, marginTop: 12, alignItems: 'center' }}>
          <button
            data-testid="refine-submit-btn"
            disabled={refining || !refineMsg.trim()}
            onClick={handleRefine}
            style={{ ...primaryBtn, background: 'linear-gradient(90deg,#a855f7,#ec4899)', opacity: refining || !refineMsg.trim() ? 0.5 : 1 }}
          >
            {refining ? '⏳ يعدّل...' : '✨ طبّق التعديل'}
          </button>
          <span style={{ color: '#666', fontSize: 12 }}>التعديل قد يستغرق 30-90 ثانية</span>
        </div>
        {history.length > 0 && (
          <div data-testid="refine-history" style={{ marginTop: 18, borderTop: '1px solid #222', paddingTop: 14 }}>
            <div style={{ color: '#888', fontSize: 11, marginBottom: 10, letterSpacing: 2 }}>سجل التعديلات</div>
            {history.slice().reverse().map((h, i) => (
              <div key={i} style={{ padding: '8px 12px', background: '#0a0a0a', borderRadius: 8, marginBottom: 6, fontSize: 12, color: '#aaa', display: 'flex', justifyContent: 'space-between' }}>
                <span>{h.message}</span>
                <span style={{ color: '#c084fc', fontWeight: 900, fontSize: 10 }}>v{h.version}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ ...navRow, gap: 12 }}>
        <a
          href={previewUrl}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="open-preview-btn"
          style={{ ...primaryBtn, textDecoration: 'none', display: 'inline-block' }}
        >
          افتح في نافذة جديدة ↗
        </a>
        <button data-testid="new-build-btn" onClick={() => window.location.reload()} style={ghostBtn}>
          ابنِ موقع آخر
        </button>
      </div>
    </div>
  );
}

function CredField({ label, value, onCopy, mono }) {
  return (
    <div style={{ background: '#0a0a0a', border: '1px solid #1a1a1a', borderRadius: 10, padding: 12 }}>
      <div style={{ color: '#666', fontSize: 10, letterSpacing: 2, marginBottom: 6 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <code style={{ flex: 1, color: '#fff', fontSize: 13, fontFamily: mono ? 'Menlo,monospace' : 'inherit', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</code>
        <button onClick={onCopy} data-testid={`copy-${label}`} style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #333', background: '#1a1a1a', color: '#fbbf24', cursor: 'pointer', fontSize: 11, fontWeight: 700 }}>نسخ</button>
      </div>
    </div>
  );
}

/* ============== Atoms ============== */

const Field = ({ label, children }) => (
  <div style={{ marginBottom: 18 }}>
    <label style={{ display: 'block', color: '#fbbf24', fontSize: 12, fontWeight: 700, marginBottom: 8, letterSpacing: 1 }}>{label}</label>
    {children}
  </div>
);

const Metric = ({ label, value }) => (
  <div style={{ background: '#0e0e0e', border: '1px solid #1a1a1a', borderRadius: 12, padding: 14, textAlign: 'center' }}>
    <div style={{ fontSize: 11, color: '#666', marginBottom: 6 }}>{label}</div>
    <div style={{ fontSize: 22, fontWeight: 900, color: '#fff' }}>{value}</div>
  </div>
);

/* ============== Styles ============== */
const shellStyle = { minHeight: '100vh', background: '#050505', color: '#fff', padding: '40px 20px 80px', fontFamily: "'Tajawal',sans-serif" };
const containerStyle = { maxWidth: 1200, margin: '0 auto' };
const sectionTitle = { fontSize: 22, fontWeight: 900, color: '#fff', marginBottom: 14 };
const gridStyle = (cols) => ({ display: 'grid', gridTemplateColumns: `repeat(${cols},1fr)`, gap: 16 });
const tileStyle = { textAlign: 'right', padding: 24, borderRadius: 18, border: '1px solid #222', background: '#0e0e0e', color: '#fff', cursor: 'pointer', transition: 'transform .15s, border-color .15s' };
const cardStyle = { background: '#0e0e0e', border: '1px solid #1a1a1a', borderRadius: 18, padding: 24, marginBottom: 18 };
const inputStyle = { width: '100%', padding: '14px 16px', borderRadius: 10, border: '1px solid #2a2a2a', background: '#000', color: '#fff', fontSize: 15, fontFamily: 'inherit' };
const navRow = { display: 'flex', justifyContent: 'space-between', marginTop: 26, gap: 12 };
const primaryBtn = { padding: '14px 28px', borderRadius: 99, border: 'none', background: 'linear-gradient(90deg,#f59e0b,#ec4899)', color: '#000', fontWeight: 900, cursor: 'pointer', fontSize: 14 };
const ghostBtn = { padding: '14px 28px', borderRadius: 99, border: '1px solid #2a2a2a', background: 'transparent', color: '#aaa', cursor: 'pointer', fontWeight: 700, fontSize: 14 };
