import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

const API = process.env.REACT_APP_BACKEND_URL;

const PATTERN_GRADIENTS = {
  fork_noir:        'linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#a78bfa 100%)',
  verdant_organic:  'linear-gradient(135deg,#064e3b 0%,#10b981 50%,#fbbf24 100%)',
  saudi_heritage:   'linear-gradient(135deg,#78350f 0%,#a52a2a 50%,#fbbf24 100%)',
  burger_cinema:    'linear-gradient(135deg,#7c2d12 0%,#dc2626 50%,#fde047 100%)',
  rustic_plank:     'linear-gradient(135deg,#451a03 0%,#92400e 50%,#fbbf24 100%)',
  brush_italian:    'linear-gradient(135deg,#7f1d1d 0%,#ec4899 50%,#fef3c7 100%)',
};

const TYPE_LABEL = {
  restaurant: 'مطعم',
  store: 'متجر',
  clinic: 'عيادة',
  realestate: 'عقار',
};

export default function ZeraxShowcase() {
  const [sites, setSites] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('all');

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/ready-sites/showcase?limit=200`);
        const d = await r.json();
        setSites(d.sites || []);
        setTotal(d.total_built || 0);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered = useMemo(() => {
    let out = sites;
    if (filterType !== 'all') out = out.filter((s) => s.type_id === filterType);
    if (search.trim()) {
      const q = search.toLowerCase();
      out = out.filter(
        (s) => (s.name || '').toLowerCase().includes(q) ||
               (s.tagline || '').toLowerCase().includes(q) ||
               (s.city || '').toLowerCase().includes(q)
      );
    }
    return out;
  }, [sites, search, filterType]);

  const totalVisits = useMemo(() => sites.reduce((a, s) => a + (s.visits || 0), 0), [sites]);

  return (
    <div dir="rtl" style={styles.page} data-testid="zerax-showcase-page">
      {/* Hero */}
      <section style={styles.hero}>
        <Link to="/" style={styles.backLink} data-testid="back-to-home">← العودة لـ Zerax</Link>
        <div style={styles.heroInner}>
          <div style={styles.zeraxBadge}>
            <span style={styles.zeraxBadgeDot}>Z</span>
            <span style={{ color: '#fbbf24', fontWeight: 900 }}>Zerax Showcase</span>
          </div>
          <h1 style={styles.heroTitle}>مواقع مبنية بـ <span style={styles.heroAccent}>الذكاء الاصطناعي</span></h1>
          <p style={styles.heroSub}>
            كل موقع تشوفه هنا تم بناؤه على منصة <strong>Zerax</strong> في أقل من 60 ثانية —
            من النمط البصري حتى لوحة الإدارة الكاملة وتطبيق السائق.
          </p>

          <div style={styles.statsRow}>
            <Stat label="موقع مبني" value={total} accent="#fbbf24" />
            <Stat label="معروض الآن" value={sites.length} accent="#a78bfa" />
            <Stat label="إجمالي الزيارات" value={totalVisits.toLocaleString('ar-SA')} accent="#22c55e" />
          </div>
        </div>
      </section>

      {/* Filter bar */}
      <section style={styles.filterBar}>
        <div style={styles.filterInner}>
          <input
            type="text"
            placeholder="ابحث باسم المطعم، المدينة..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={styles.searchInput}
            data-testid="showcase-search"
          />
          <div style={styles.typePills}>
            {[
              ['all', 'الكل'],
              ['restaurant', 'مطاعم'],
              ['store', 'متاجر'],
              ['clinic', 'عيادات'],
            ].map(([id, label]) => (
              <button
                key={id}
                onClick={() => setFilterType(id)}
                style={{
                  ...styles.typePill,
                  ...(filterType === id ? styles.typePillActive : {}),
                }}
                data-testid={`filter-${id}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Grid */}
      <section style={styles.gridWrap}>
        {loading ? (
          <div style={styles.empty}>جاري التحميل...</div>
        ) : filtered.length === 0 ? (
          <div style={styles.empty}>لا توجد مواقع مطابقة لبحثك بعد. كن أول من ينشر موقعه! ✨</div>
        ) : (
          <div style={styles.grid}>
            {filtered.map((s) => (
              <SiteCard key={s.id} site={s} />
            ))}
          </div>
        )}
      </section>

      {/* CTA */}
      <section style={styles.cta}>
        <h2 style={styles.ctaTitle}>هل تريد موقعك هنا؟</h2>
        <p style={styles.ctaSub}>اِبنِ موقع مطعمك الكامل بـ AI في أقل من دقيقة — مع لوحة إدارة وتطبيق سائق وسلة شراء جاهزة.</p>
        <Link to="/ready-sites" style={styles.ctaBtn} data-testid="cta-build-yours">ابدأ مجاناً ←</Link>
      </section>

      <footer style={styles.foot}>
        <span>© Zerax 2026 — منصة بناء المواقع بالذكاء الاصطناعي</span>
      </footer>
    </div>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div style={styles.stat}>
      <div style={{ ...styles.statVal, color: accent }}>{value}</div>
      <div style={styles.statLbl}>{label}</div>
    </div>
  );
}

function SiteCard({ site }) {
  const gradient = PATTERN_GRADIENTS[site.pattern_id] || 'linear-gradient(135deg,#1e293b,#475569)';
  const typeLabel = TYPE_LABEL[site.type_id] || site.type_id;
  const previewUrl = `${API}${site.preview_url}`;

  return (
    <a
      href={previewUrl}
      target="_blank"
      rel="noopener noreferrer"
      style={styles.card}
      data-testid={`showcase-card-${site.id}`}
    >
      <div style={{ ...styles.cardCover, background: gradient }}>
        {site.logo_url ? (
          <img src={site.logo_url} alt={site.name} style={styles.cardLogo} />
        ) : (
          <div style={styles.cardLogoText}>{(site.logo_text || site.name || 'Z')[0]}</div>
        )}
        <div style={styles.cardTypePill}>{typeLabel}</div>
      </div>
      <div style={styles.cardBody}>
        <div style={styles.cardName}>{site.name}</div>
        {site.tagline ? <div style={styles.cardTag}>{site.tagline}</div> : null}
        <div style={styles.cardMeta}>
          {site.city ? <span>📍 {site.city}</span> : null}
          <span style={{ marginInlineStart: 'auto' }}>👁 {site.visits || 0}</span>
        </div>
      </div>
      <div style={styles.cardCta}>
        زيارة الموقع <span style={{ marginInlineStart: 6 }}>←</span>
      </div>
    </a>
  );
}

const styles = {
  page: {
    minHeight: '100vh',
    background: 'linear-gradient(180deg,#0a0a0b 0%,#0f172a 100%)',
    color: '#e5e7eb',
    fontFamily: "'Tajawal', 'Cairo', system-ui, sans-serif",
  },
  hero: {
    padding: '36px 24px 60px',
    background: 'radial-gradient(ellipse at top, rgba(251,191,36,0.08) 0%, transparent 70%)',
    borderBottom: '1px solid #1e293b',
  },
  backLink: {
    color: '#94a3b8',
    fontSize: 13,
    textDecoration: 'none',
    display: 'inline-block',
    marginBottom: 28,
  },
  heroInner: { maxWidth: 1100, margin: '0 auto', textAlign: 'center' },
  zeraxBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 16px',
    background: 'rgba(251,191,36,0.08)',
    border: '1px solid rgba(251,191,36,0.25)',
    borderRadius: 99,
    marginBottom: 18,
    fontSize: 13,
  },
  zeraxBadgeDot: {
    width: 24, height: 24, borderRadius: '50%',
    background: 'linear-gradient(135deg,#fbbf24,#a52a2a)',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    fontWeight: 900, color: '#fff', fontSize: 12,
  },
  heroTitle: { fontSize: 'clamp(28px,5vw,52px)', fontWeight: 900, marginBottom: 14, lineHeight: 1.2 },
  heroAccent: {
    background: 'linear-gradient(90deg,#fbbf24,#a78bfa)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  heroSub: { color: '#94a3b8', fontSize: 'clamp(13px,1.6vw,16px)', maxWidth: 700, margin: '0 auto 32px', lineHeight: 1.9 },
  statsRow: { display: 'flex', justifyContent: 'center', gap: 'clamp(16px,4vw,48px)', flexWrap: 'wrap' },
  stat: { textAlign: 'center' },
  statVal: { fontSize: 'clamp(24px,4vw,36px)', fontWeight: 900, marginBottom: 4 },
  statLbl: { fontSize: 11, color: '#64748b', letterSpacing: 1 },

  filterBar: {
    background: 'rgba(15,23,42,0.7)',
    backdropFilter: 'blur(12px)',
    borderBottom: '1px solid #1e293b',
    padding: '16px 24px',
    position: 'sticky',
    top: 0,
    zIndex: 50,
  },
  filterInner: { maxWidth: 1100, margin: '0 auto', display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' },
  searchInput: {
    flex: '1 1 220px',
    padding: '10px 14px',
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 10,
    color: '#e5e7eb',
    fontSize: 13,
    fontFamily: 'inherit',
  },
  typePills: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  typePill: {
    padding: '8px 14px',
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 99,
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: 700,
    cursor: 'pointer',
    fontFamily: 'inherit',
    transition: 'all 0.2s',
  },
  typePillActive: {
    background: 'linear-gradient(135deg,#fbbf24,#a52a2a)',
    color: '#fff',
    borderColor: 'transparent',
  },

  gridWrap: { padding: '40px 24px', maxWidth: 1300, margin: '0 auto' },
  empty: { textAlign: 'center', padding: 60, color: '#64748b', fontSize: 14 },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: 22,
  },

  card: {
    background: '#0f172a',
    border: '1px solid #1e293b',
    borderRadius: 18,
    overflow: 'hidden',
    textDecoration: 'none',
    color: 'inherit',
    display: 'flex',
    flexDirection: 'column',
    transition: 'transform 0.25s, border-color 0.25s, box-shadow 0.25s',
    cursor: 'pointer',
  },
  cardCover: {
    height: 160,
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardLogo: { maxWidth: '70%', maxHeight: '70%', filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.4))' },
  cardLogoText: {
    width: 80, height: 80, borderRadius: '50%',
    background: 'rgba(255,255,255,0.95)',
    color: '#0f172a',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 36, fontWeight: 900,
    boxShadow: '0 8px 28px rgba(0,0,0,0.4)',
  },
  cardTypePill: {
    position: 'absolute', top: 12, insetInlineStart: 12,
    background: 'rgba(0,0,0,0.5)',
    backdropFilter: 'blur(8px)',
    color: '#fff',
    fontSize: 10,
    fontWeight: 700,
    padding: '4px 10px',
    borderRadius: 99,
    letterSpacing: 0.5,
  },
  cardBody: { padding: '14px 16px', flex: 1 },
  cardName: { fontSize: 16, fontWeight: 900, color: '#e5e7eb', marginBottom: 4 },
  cardTag: { fontSize: 12, color: '#94a3b8', marginBottom: 10, lineHeight: 1.6 },
  cardMeta: { display: 'flex', fontSize: 11, color: '#64748b', gap: 10, alignItems: 'center' },
  cardCta: {
    padding: '11px 16px',
    background: 'rgba(251,191,36,0.08)',
    color: '#fbbf24',
    fontSize: 12,
    fontWeight: 700,
    textAlign: 'center',
    borderTop: '1px solid #1e293b',
  },

  cta: {
    textAlign: 'center',
    padding: '60px 24px',
    background: 'linear-gradient(135deg, rgba(251,191,36,0.04), rgba(167,139,250,0.04))',
    borderTop: '1px solid #1e293b',
    borderBottom: '1px solid #1e293b',
  },
  ctaTitle: { fontSize: 'clamp(22px,3vw,34px)', fontWeight: 900, marginBottom: 10 },
  ctaSub: { color: '#94a3b8', fontSize: 14, maxWidth: 580, margin: '0 auto 26px', lineHeight: 1.8 },
  ctaBtn: {
    display: 'inline-block',
    padding: '14px 36px',
    background: 'linear-gradient(135deg,#fbbf24,#a52a2a)',
    color: '#fff',
    fontWeight: 900,
    fontSize: 15,
    borderRadius: 99,
    textDecoration: 'none',
    boxShadow: '0 14px 40px rgba(251,191,36,0.25)',
  },

  foot: { textAlign: 'center', padding: '22px 24px', color: '#64748b', fontSize: 12 },
};
