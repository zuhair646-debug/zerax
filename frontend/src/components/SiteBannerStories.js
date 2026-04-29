/**
 * SiteBannerStories — luxurious rotating banner + Stories ribbon for Zitex's own site.
 *
 * Renders:
 *   • A full-width hero banner that auto-rotates between admin-managed slides
 *     (image / video / "animated" with Ken Burns) every N seconds.
 *   • An Instagram-style stories ribbon below it.
 *
 * Both data sources are public endpoints:
 *   GET /api/site/banner?placement=outside|inside
 *   GET /api/site/stories?placement=outside|inside
 *
 * Use:
 *   <SiteBannerStories placement="outside" />   // Landing/Login/Register
 *   <SiteBannerStories placement="inside" />    // Authenticated dashboard top
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function SiteBannerStories({ placement = 'outside' }) {
  const [slides, setSlides] = useState([]);
  const [stories, setStories] = useState([]);
  const [rotateSec, setRotateSec] = useState(6);
  const [animation, setAnimation] = useState('fade');
  const [overlayOpacity, setOverlayOpacity] = useState(0.5);
  const [activeIdx, setActiveIdx] = useState(0);

  // Story viewer state
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerIdx, setViewerIdx] = useState(0);
  const [viewerProgress, setViewerProgress] = useState(0);
  const viewerTimerRef = useRef(null);
  const seenRef = useRef(loadSeen());

  function loadSeen() {
    try { return JSON.parse(localStorage.getItem('zitex_seen_stories') || '[]'); } catch (_) { return []; }
  }
  function markSeen(id) {
    if (!seenRef.current.includes(id)) {
      seenRef.current.push(id);
      try { localStorage.setItem('zitex_seen_stories', JSON.stringify(seenRef.current.slice(-100))); } catch (_) {}
    }
  }

  useEffect(() => {
    const load = async () => {
      try {
        const [bR, sR] = await Promise.all([
          fetch(`${API}/api/site/banner?placement=${placement}`),
          fetch(`${API}/api/site/stories?placement=${placement}`),
        ]);
        const bD = await bR.json();
        const sD = await sR.json();
        setSlides(bD.slides || []);
        setRotateSec(Math.max(2, Math.min(30, bD.rotate_seconds || 6)));
        setAnimation(bD.animation || 'fade');
        setOverlayOpacity(bD.overlay_opacity ?? 0.5);
        setStories(sD.stories || []);
      } catch (_) { /* silent — banner is optional */ }
    };
    load();
  }, [placement]);

  // Auto-rotate banner
  useEffect(() => {
    if (slides.length < 2) return;
    const t = setInterval(() => {
      setActiveIdx((i) => (i + 1) % slides.length);
    }, rotateSec * 1000);
    return () => clearInterval(t);
  }, [slides.length, rotateSec]);

  const openStoryViewer = (idx) => {
    setViewerIdx(idx);
    setViewerOpen(true);
    setViewerProgress(0);
  };
  const closeStoryViewer = useCallback(() => {
    setViewerOpen(false);
    if (viewerTimerRef.current) { clearInterval(viewerTimerRef.current); viewerTimerRef.current = null; }
  }, []);
  const stepStory = useCallback((delta) => {
    setViewerIdx((cur) => {
      const next = cur + delta;
      if (next < 0 || next >= stories.length) {
        closeStoryViewer();
        return cur;
      }
      setViewerProgress(0);
      return next;
    });
  }, [stories.length, closeStoryViewer]);

  // Story auto-progress
  useEffect(() => {
    if (!viewerOpen || stories.length === 0) return;
    const s = stories[viewerIdx];
    if (!s) return;
    markSeen(s.id);
    const dur = Math.max(2, Math.min(20, s.duration_sec || 6)) * 1000;
    const start = Date.now();
    if (viewerTimerRef.current) clearInterval(viewerTimerRef.current);
    viewerTimerRef.current = setInterval(() => {
      const pct = Math.min(100, ((Date.now() - start) / dur) * 100);
      setViewerProgress(pct);
      if (pct >= 100) {
        clearInterval(viewerTimerRef.current);
        viewerTimerRef.current = null;
        stepStory(+1);
      }
    }, 80);
    return () => { if (viewerTimerRef.current) clearInterval(viewerTimerRef.current); };
  }, [viewerOpen, viewerIdx, stories, stepStory]);

  // Keyboard nav
  useEffect(() => {
    if (!viewerOpen) return;
    const onKey = (e) => {
      if (e.key === 'Escape') closeStoryViewer();
      if (e.key === 'ArrowRight') stepStory(-1);
      if (e.key === 'ArrowLeft') stepStory(+1);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [viewerOpen, stepStory, closeStoryViewer]);

  if (slides.length === 0 && stories.length === 0) return null;

  return (
    <div data-testid={`site-bs-${placement}`} className="zsb-host" dir="rtl">
      <style>{css}</style>

      {/* ─── Rotating Banner (cinematic ad slot — no CTA button) ─── */}
      {slides.length > 0 && (
        <section className={`zsb-banner zsb-banner-${animation}`}>
          {slides.map((s, i) => {
            const Body = (
              <>
                {s.type === 'video' ? (
                  <video src={s.media_url} className="zsb-media" autoPlay muted loop playsInline />
                ) : (
                  <img src={s.media_url} className={`zsb-media ${animation === 'kenburns' && i === activeIdx ? 'kenburns' : ''}`} alt={s.title || ''} />
                )}
                <div className="zsb-overlay" style={{ opacity: overlayOpacity }}></div>
                <div className="zsb-content">
                  {s.title && <div className="zsb-title">{s.title}</div>}
                  {s.subtitle && <div className="zsb-subtitle">{s.subtitle}</div>}
                </div>
              </>
            );
            const className = `zsb-slide ${i === activeIdx ? 'is-active' : ''}`;
            return s.cta_link ? (
              <a key={s.id} href={s.cta_link} className={className} aria-label={s.title || 'banner'} data-testid={`zsb-slide-${i}`}>
                {Body}
              </a>
            ) : (
              <div key={s.id} className={className} data-testid={`zsb-slide-${i}`}>
                {Body}
              </div>
            );
          })}
          {/* Pagination dots */}
          {slides.length > 1 && (
            <div className="zsb-dots">
              {slides.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActiveIdx(i)}
                  className={`zsb-dot ${i === activeIdx ? 'is-active' : ''}`}
                  aria-label={`slide ${i + 1}`}
                  data-testid={`zsb-dot-${i}`}
                />
              ))}
            </div>
          )}
        </section>
      )}

      {/* ─── Stories Ribbon ─── */}
      {stories.length > 0 && (
        <div className="zsb-stories" data-testid="zsb-stories">
          {stories.map((s, i) => {
            const seen = seenRef.current.includes(s.id);
            return (
              <button key={s.id} className="zsb-story" onClick={() => openStoryViewer(i)} data-testid={`zsb-story-${i}`}>
                <div className={`zsb-ring ${seen ? 'seen' : ''}`}>
                  <img className="zsb-thumb" src={s.poster_url || (s.type === 'video' ? '' : s.media_url) || PLACEHOLDER} alt={s.caption || ''} />
                  {s.type === 'video' && <span className="zsb-vbadge">▶</span>}
                </div>
                {s.caption && <div className="zsb-cap">{s.caption}</div>}
              </button>
            );
          })}
        </div>
      )}

      {/* ─── Story Fullscreen Viewer ─── */}
      {viewerOpen && stories[viewerIdx] && (
        <div className="zsb-viewer" onClick={(e) => { if (e.target === e.currentTarget) closeStoryViewer(); }} data-testid="zsb-viewer">
          <div className="zsb-vshell">
            <div className="zsb-vprog">
              {stories.map((_, i) => (
                <div key={i} className="zsb-vbar"><div className="zsb-vfill" style={{ width: i < viewerIdx ? '100%' : i === viewerIdx ? `${viewerProgress}%` : '0%' }}></div></div>
              ))}
            </div>
            <button className="zsb-vclose" onClick={closeStoryViewer} data-testid="zsb-viewer-close">×</button>
            {stories[viewerIdx].type === 'video' ? (
              <video src={stories[viewerIdx].media_url} className="zsb-vmedia" autoPlay playsInline controls />
            ) : (
              <img src={stories[viewerIdx].media_url} className="zsb-vmedia" alt={stories[viewerIdx].caption || ''} />
            )}
            {(stories[viewerIdx].caption || stories[viewerIdx].link) && (
              <div className="zsb-vcap">
                {stories[viewerIdx].caption && <div>{stories[viewerIdx].caption}</div>}
                {stories[viewerIdx].link && (
                  <a href={stories[viewerIdx].link} target="_blank" rel="noreferrer" className="zsb-vlink">اعرف أكثر ←</a>
                )}
              </div>
            )}
            <div className="zsb-vtap zsb-vtap-left" onClick={() => stepStory(+1)}></div>
            <div className="zsb-vtap zsb-vtap-right" onClick={() => stepStory(-1)}></div>
          </div>
        </div>
      )}
    </div>
  );
}

const PLACEHOLDER = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='80' height='80'><rect width='80' height='80' fill='%23222'/></svg>";

const css = `
.zsb-host{position:relative;z-index:1;direction:rtl;font-family:inherit}
.zsb-banner{position:relative;width:100%;height:clamp(200px,28vw,380px);overflow:hidden;background:#0a0a12;border-radius:0;box-shadow:0 20px 60px -20px rgba(0,0,0,.6)}
.zsb-slide{position:absolute;inset:0;opacity:0;transition:opacity 1.1s ease;pointer-events:none;display:block;text-decoration:none;color:#fff}
.zsb-slide.is-active{opacity:1;pointer-events:auto;z-index:2}
a.zsb-slide{cursor:pointer}
.zsb-banner-slide .zsb-slide{transform:translateX(-100%);transition:transform 1s cubic-bezier(.25,.8,.25,1),opacity .6s}
.zsb-banner-slide .zsb-slide.is-active{transform:translateX(0)}
.zsb-media{width:100%;height:100%;object-fit:cover;display:block;background:#000}
.zsb-media.kenburns{animation:zsb-kb 16s ease-in-out infinite alternate}
@keyframes zsb-kb{from{transform:scale(1) translate(0,0)}to{transform:scale(1.12) translate(-3%,2%)}}
.zsb-overlay{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 30%,rgba(0,0,0,.55) 75%,rgba(0,0,0,.85) 100%);pointer-events:none}
.zsb-content{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:flex-end;align-items:flex-start;padding:clamp(20px,3vw,46px);gap:6px;color:#fff;z-index:3}
.zsb-title{font-size:clamp(20px,3vw,38px);font-weight:900;line-height:1.2;text-shadow:0 6px 28px rgba(0,0,0,.7);max-width:80%;letter-spacing:-.5px;animation:zsb-rise .9s cubic-bezier(.2,.8,.2,1) both}
.zsb-subtitle{font-size:clamp(13px,1.25vw,16px);opacity:.92;text-shadow:0 4px 18px rgba(0,0,0,.6);max-width:70%;animation:zsb-rise .9s .12s cubic-bezier(.2,.8,.2,1) both;font-weight:500}
@keyframes zsb-rise{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
.zsb-dots{position:absolute;bottom:14px;left:50%;transform:translateX(-50%);display:flex;gap:6px;z-index:4;background:rgba(0,0,0,.4);padding:6px 10px;border-radius:99px;backdrop-filter:blur(8px)}
.zsb-dot{width:7px;height:7px;border:0;background:rgba(255,255,255,.45);border-radius:99px;cursor:pointer;padding:0;transition:all .25s ease}
.zsb-dot.is-active{background:linear-gradient(135deg,#FFD700,#FF6B35);width:24px}
.zsb-stories{display:flex;gap:14px;padding:14px clamp(16px,3vw,28px);overflow-x:auto;scrollbar-width:none;background:linear-gradient(180deg,rgba(0,0,0,.35),rgba(0,0,0,0));scroll-snap-type:x proximity;border-bottom:1px solid rgba(255,255,255,.05)}
.zsb-stories::-webkit-scrollbar{display:none}
.zsb-story{flex-shrink:0;width:78px;text-align:center;cursor:pointer;background:transparent;border:0;padding:0;color:inherit;font-family:inherit;scroll-snap-align:start}
.zsb-ring{width:78px;height:78px;border-radius:50%;padding:3px;background:conic-gradient(from 180deg,#FFD700,#FF6B35,#10b981,#06b6d4,#FFD700);position:relative;transition:transform .25s ease;box-shadow:0 6px 20px rgba(255,107,53,.18)}
.zsb-story:hover .zsb-ring{transform:scale(1.07)}
.zsb-ring.seen{background:rgba(255,255,255,.18);box-shadow:none}
.zsb-thumb{width:100%;height:100%;border-radius:50%;object-fit:cover;background:#000;border:2px solid #0a0a12}
.zsb-vbadge{position:absolute;bottom:2px;left:2px;background:linear-gradient(135deg,#FF6B35,#FFD700);color:#0a0a12;font-size:11px;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:900}
.zsb-cap{font-size:11px;margin-top:6px;color:rgba(255,255,255,.85);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;direction:rtl;font-weight:500}
.zsb-viewer{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.96);display:flex;align-items:center;justify-content:center;padding:16px;animation:zsb-fadein .25s ease-out}
@keyframes zsb-fadein{from{opacity:0}to{opacity:1}}
.zsb-vshell{position:relative;width:min(420px,100%);height:min(80vh,720px);max-height:96vh;background:#000;border-radius:14px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.7)}
.zsb-vmedia{width:100%;height:100%;object-fit:cover;background:#000;display:block}
.zsb-vprog{position:absolute;top:8px;left:8px;right:8px;display:flex;gap:4px;z-index:3}
.zsb-vbar{flex:1;height:2.5px;background:rgba(255,255,255,.25);border-radius:99px;overflow:hidden}
.zsb-vfill{height:100%;background:#fff;width:0;transition:width 80ms linear}
.zsb-vcap{position:absolute;left:0;right:0;bottom:0;padding:14px 18px;color:#fff;font-size:14px;background:linear-gradient(0deg,rgba(0,0,0,.85),transparent);direction:rtl}
.zsb-vlink{display:inline-block;margin-top:8px;padding:8px 18px;background:linear-gradient(135deg,#FFD700,#FF6B35);color:#0a0a12;border-radius:99px;font-weight:900;font-size:13px;text-decoration:none}
.zsb-vclose{position:absolute;top:14px;right:14px;width:34px;height:34px;border-radius:50%;background:rgba(0,0,0,.6);color:#fff;border:0;font-size:20px;cursor:pointer;z-index:5}
.zsb-vtap{position:absolute;top:0;bottom:0;width:50%;cursor:pointer;z-index:2}
.zsb-vtap-left{left:0}.zsb-vtap-right{right:0}
`;
