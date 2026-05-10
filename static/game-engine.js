/**
 * Zitex Game Engine v2.0 - Multi-Genre Playable Games
 * يدعم: استراتيجية، منصات، سباق، ثعبان، إطلاق نار، ألغاز، ذاكرة، طائرة
 * الاستخدام: ZitexGame.init({genre:'strategy', theme:'medieval', ...})
 */
(function () {
  'use strict';

  const U = {
    rnd: (a, b) => a + Math.random() * (b - a),
    pick: arr => arr[Math.floor(Math.random() * arr.length)],
    clamp: (v, a, b) => Math.max(a, Math.min(b, v)),
    el: (tag, css, html) => {
      const d = document.createElement(tag);
      if (css) d.style.cssText = css;
      if (html !== undefined) d.innerHTML = html;
      return d;
    },
  };

  // ============== SHARED SVG LIBRARY ==============
  const SVG = {
    castle: (s = 160) => `<svg viewBox="0 0 120 110" width="${s}" height="${s * 0.92}"><defs><linearGradient id="cg${s}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#A08060"/><stop offset="100%" stop-color="#7A6040"/></linearGradient></defs><rect x="25" y="45" width="70" height="55" fill="url(#cg${s})" rx="3"/><rect x="10" y="28" width="18" height="72" fill="#8B7355"/><rect x="92" y="28" width="18" height="72" fill="#8B7355"/><rect x="48" y="22" width="24" height="78" fill="#9B8465"/><polygon points="10,28 19,10 28,28" fill="#C41E3A"/><polygon points="92,28 101,10 110,28" fill="#C41E3A"/><polygon points="48,22 60,5 72,22" fill="#C41E3A"/><rect x="50" y="62" width="20" height="38" fill="#4A3322" rx="10 10 0 0"/><circle cx="65" cy="80" r="2.5" fill="#FFD700"/><rect x="30" y="52" width="12" height="12" fill="#87CEEB" rx="2"/><rect x="78" y="52" width="12" height="12" fill="#87CEEB" rx="2"/><rect x="14" y="35" width="10" height="10" fill="#87CEEB" rx="1"/><rect x="96" y="35" width="10" height="10" fill="#87CEEB" rx="1"/><rect x="57" y="8" width="6" height="16" fill="#6B5030"/><polygon points="54,8 63,0 72,8" fill="#FFD700"/></svg>`,
    house: (s = 65) => {
      const c = ['#D4A574', '#C49464', '#B88454', '#DDB584'];
      const r = ['#8B4513', '#7A3A12', '#6B3010', '#9B5523'];
      const i = Math.floor(Math.random() * 4);
      return `<svg viewBox="0 0 80 70" width="${s}" height="${s * 0.88}"><rect x="10" y="35" width="60" height="35" fill="${c[i]}" rx="2"/><polygon points="5,35 40,12 75,35" fill="${r[i]}"/><rect x="30" y="45" width="14" height="25" fill="#4A3322" rx="5 5 0 0"/><circle cx="39" cy="57" r="2" fill="#FFD700"/><rect x="13" y="40" width="11" height="10" fill="#87CEEB" rx="1"/><rect x="56" y="40" width="11" height="10" fill="#87CEEB" rx="1"/><rect x="62" y="16" width="6" height="19" fill="#8B7355"/><ellipse cx="65" cy="13" rx="7" ry="5" fill="#808080" opacity="0.5"/></svg>`;
    },
    tree: (s = 60) => {
      const g = ['#2D8B2D', '#1E7A1E', '#3AA63A', '#228B22'];
      const i = Math.floor(Math.random() * 4);
      return `<svg viewBox="0 0 60 80" width="${s}" height="${s * 1.33}"><rect x="25" y="52" width="10" height="23" fill="#6B4226" rx="3"/><ellipse cx="30" cy="35" rx="${18 + Math.random() * 8}" ry="${20 + Math.random() * 8}" fill="${g[i]}"/><ellipse cx="22" cy="30" rx="14" ry="16" fill="${g[(i + 1) % 4]}" opacity="0.9"/><ellipse cx="38" cy="32" rx="13" ry="15" fill="${g[(i + 2) % 4]}" opacity="0.85"/></svg>`;
    },
    farm: (s = 80) => `<svg viewBox="0 0 90 60" width="${s}" height="${s * 0.67}"><rect x="5" y="15" width="80" height="40" fill="#8B6914" rx="4"/><line x1="5" y1="25" x2="85" y2="25" stroke="#6B4F12" stroke-width="1"/><line x1="5" y1="35" x2="85" y2="35" stroke="#6B4F12" stroke-width="1"/><line x1="5" y1="45" x2="85" y2="45" stroke="#6B4F12" stroke-width="1"/>${Array.from({ length: 8 }, (_, i) => `<rect x="${8 + i * 10}" y="${17 + Math.random() * 4}" width="3" height="${8 + Math.random() * 6}" fill="#228B22" rx="1"/>`).join('')}${Array.from({ length: 4 }, (_, i) => `<circle cx="${12 + i * 20}" cy="${14 + Math.random() * 2}" r="4" fill="#FFD700" opacity="0.9"/>`).join('')}<rect x="35" y="2" width="3" height="13" fill="#6B4226"/><rect x="30" y="2" width="13" height="3" fill="#6B4226"/></svg>`,
    soldier: (s = 35) => `<svg viewBox="0 0 40 60" width="${s}" height="${s * 1.5}"><circle cx="20" cy="12" r="8" fill="#FDBCB4"/><rect x="12" y="20" width="16" height="20" fill="#C41E3A" rx="3"/><rect x="7" y="22" width="7" height="14" fill="#A01030" rx="2"/><rect x="26" y="22" width="7" height="14" fill="#A01030" rx="2"/><rect x="14" y="40" width="5" height="14" fill="#4A3728" rx="2"/><rect x="21" y="40" width="5" height="14" fill="#4A3728" rx="2"/><polygon points="5,22 1,36 9,36" fill="#808080"/><ellipse cx="20" cy="5" rx="10" ry="4" fill="#808080"/><circle cx="16" cy="10" r="1.5" fill="#333"/><circle cx="24" cy="10" r="1.5" fill="#333"/></svg>`,
    cloud: (s = 100) => `<svg viewBox="0 0 120 45" width="${s}" height="${s * 0.38}"><ellipse cx="60" cy="28" rx="50" ry="16" fill="white" opacity="0.85"/><ellipse cx="35" cy="22" rx="30" ry="14" fill="white" opacity="0.9"/><ellipse cx="85" cy="24" rx="28" ry="12" fill="white" opacity="0.87"/></svg>`,
    bush: (s = 30) => `<svg viewBox="0 0 40 25" width="${s}" height="${s * 0.63}"><ellipse cx="20" cy="15" rx="18" ry="10" fill="#2D8B2D"/><ellipse cx="12" cy="13" rx="10" ry="8" fill="#3AA63A"/><ellipse cx="28" cy="14" rx="9" ry="7" fill="#248F24"/></svg>`,
    flower: (s = 15) => {
      const c = ['#FF6B6B', '#FFD700', '#FF69B4', '#9370DB', '#FF8C00'];
      const cl = c[Math.floor(Math.random() * 5)];
      return `<svg viewBox="0 0 20 25" width="${s}" height="${s * 1.25}"><rect x="9" y="12" width="2" height="13" fill="#228B22"/><circle cx="10" cy="9" r="5" fill="${cl}" opacity="0.9"/><circle cx="10" cy="9" r="2.5" fill="#FFD700"/></svg>`;
    },
    rock: (s = 25) => `<svg viewBox="0 0 40 30" width="${s}" height="${s * 0.75}"><polygon points="8,28 20,8 35,28" fill="#808080"/><polygon points="2,28 12,15 22,28" fill="#696969"/><circle cx="18" cy="22" r="2" fill="#FFD700" opacity="0.6"/></svg>`,
    mine: (s = 70) => `<svg viewBox="0 0 80 60" width="${s}" height="${s * 0.75}"><polygon points="20,55 40,15 60,55" fill="#696969"/><polygon points="10,55 25,25 40,55" fill="#808080"/><polygon points="45,55 60,20 75,55" fill="#A9A9A9"/><rect x="35" y="30" width="5" height="20" fill="#6B4226"/><polygon points="32,30 40,18 48,30" fill="#555"/><circle cx="28" cy="42" r="4" fill="#FFD700"/><circle cx="55" cy="48" r="3" fill="#FFD700"/></svg>`,
  };

  // ============== SHARED UI ==============
  function injectBaseStyle() {
    if (document.getElementById('zg-style')) return;
    const s = document.createElement('style');
    s.id = 'zg-style';
    s.textContent = `
      *{margin:0;padding:0;box-sizing:border-box;font-family:Tajawal,-apple-system,BlinkMacSystemFont,sans-serif}
      html,body{width:100%;height:100%;overflow:hidden;background:#0b1020}
      .zg-hud{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;justify-content:space-between;align-items:center;padding:10px 16px;background:linear-gradient(180deg,rgba(0,0,0,0.75),rgba(0,0,0,0.3));backdrop-filter:blur(10px);color:#fff;font-weight:700}
      .zg-hud .left,.zg-hud .right{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
      .zg-chip{display:flex;align-items:center;gap:6px;background:rgba(255,255,255,0.08);padding:6px 12px;border-radius:20px;font-size:13px;border:1px solid rgba(255,215,0,0.2)}
      .zg-foot{position:fixed;bottom:0;left:0;right:0;z-index:100;display:flex;justify-content:center;gap:8px;padding:10px;background:rgba(0,0,0,0.6);backdrop-filter:blur(10px)}
      .zg-btn{padding:9px 18px;border:2px solid rgba(255,215,0,0.5);border-radius:12px;background:rgba(255,215,0,0.12);color:#FFD700;font-weight:700;cursor:pointer;transition:all .25s;font-size:13px;font-family:inherit}
      .zg-btn:hover{background:rgba(255,215,0,0.3);transform:translateY(-2px);box-shadow:0 4px 14px rgba(255,215,0,0.3)}
      .zg-overlay{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.75);z-index:200;backdrop-filter:blur(6px)}
      .zg-card{background:linear-gradient(135deg,#1a1f3a,#2a2f5a);padding:32px 40px;border-radius:20px;text-align:center;color:#fff;border:2px solid rgba(255,215,0,0.4);box-shadow:0 20px 60px rgba(0,0,0,.5);min-width:300px}
      .zg-card h1{font-size:28px;color:#FFD700;margin-bottom:10px}
      .zg-card p{font-size:15px;opacity:.85;margin-bottom:20px;line-height:1.6}
      .zg-badge{position:fixed;bottom:60px;right:10px;z-index:90;font-size:10px;color:rgba(255,255,255,.4);background:rgba(0,0,0,.4);padding:3px 8px;border-radius:10px}
      .zg-board{position:absolute;inset:50px 0 60px 0;display:flex;align-items:center;justify-content:center}
      @keyframes zgpop{0%{transform:scale(.7);opacity:0}100%{transform:scale(1);opacity:1}}
      @keyframes zgshake{0%,100%{transform:translate(0,0)}25%{transform:translate(-3px,2px)}50%{transform:translate(3px,-2px)}75%{transform:translate(-2px,-2px)}}
    `;
    document.head.appendChild(s);
    // Font
    if (!document.querySelector('link[href*="Tajawal"]')) {
      const l = document.createElement('link');
      l.rel = 'stylesheet';
      l.href = 'https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap';
      document.head.appendChild(l);
    }
    const badge = U.el('div', '', 'Zitex Engine');
    badge.className = 'zg-badge';
    document.body.appendChild(badge);
  }

  function hud(left, right) {
    const h = U.el('div', '');
    h.className = 'zg-hud';
    h.innerHTML = `<div class="left">${left}</div><div class="right">${right}</div>`;
    document.body.appendChild(h);
    return h;
  }

  function foot(buttonsHtml) {
    const f = U.el('div', '');
    f.className = 'zg-foot';
    f.innerHTML = buttonsHtml;
    document.body.appendChild(f);
    return f;
  }

  function overlay(title, msg, btnText, onBtn) {
    const o = U.el('div', '');
    o.className = 'zg-overlay';
    o.innerHTML = `<div class="zg-card" style="animation:zgpop .4s ease"><h1>${title}</h1><p>${msg}</p><button class="zg-btn">${btnText}</button></div>`;
    document.body.appendChild(o);
    o.querySelector('button').onclick = () => {
      o.remove();
      onBtn && onBtn();
    };
    return o;
  }

  // ============== STRATEGY / VILLAGE ==============
  const Strategy = {
    res: { gold: 500, wood: 300, food: 400, stone: 150, soldiers: 3 },
    world: null,
    init(cfg) {
      document.body.innerHTML = '';
      injectBaseStyle();
      this.res = { gold: 500, wood: 300, food: 400, stone: 150, soldiers: cfg.soldiers || 4 };
      this.world = U.el('div', 'position:fixed;inset:0;background:linear-gradient(180deg,#87CEEB 0%,#5BA3D9 22%,#90EE90 22%,#4A8B3F 55%,#3D7A35 100%);overflow:hidden');
      document.body.appendChild(this.world);
      this.addStyle();
      this.addHUD();
      this.addHills();
      this.addClouds(cfg.clouds || 5);
      this.addPaths();
      this.addFlowers(cfg.flowers || 22);
      this.addBushes(cfg.bushes || 10);
      this.addTrees(cfg.trees || 12);
      this.addFarms(cfg.farms || 3);
      this.addMine();
      this.addCastle();
      this.addHouses(cfg.buildings || 7);
      this.addSoldiers(cfg.soldiers || 4);
      this.addRocks(cfg.rocks || 6);
      this.addFoot();
      setInterval(() => { this.res.gold += 5; this.res.wood += 3; this.res.food += 4; this.res.stone += 2; this.upd(); }, 3000);
    },
    addStyle() {
      const s = U.el('style', '', `
        .b{position:absolute;cursor:pointer;transition:transform .3s,filter .3s;filter:drop-shadow(2px 4px 6px rgba(0,0,0,.4))}
        .b:hover{transform:scale(1.15);z-index:50;filter:drop-shadow(2px 4px 14px rgba(255,215,0,.6))}
        .tt{display:none;position:absolute;bottom:105%;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.92);color:#fff;padding:6px 12px;border-radius:8px;white-space:nowrap;font-size:11px;z-index:99;border:1px solid rgba(255,215,0,.3)}
        .b:hover .tt{display:block}
        .hill{position:absolute;border-radius:50%;opacity:.4}
        @keyframes fc{0%{transform:translateX(-200px)}100%{transform:translateX(calc(100vw + 200px))}}
        @keyframes sw{0%,100%{transform:rotate(-2deg)}50%{transform:rotate(2deg)}}
        @keyframes bn{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}
        .ts{animation:sw 3s ease-in-out infinite;transform-origin:bottom center}
        .sbn{animation:bn 2s ease-in-out infinite}
      `);
      document.head.appendChild(s);
    },
    addHUD() {
      hud(
        `<div class="zg-chip">💰 <span id="rg">${this.res.gold}</span></div>
         <div class="zg-chip">🪵 <span id="rw">${this.res.wood}</span></div>
         <div class="zg-chip">🌾 <span id="rf">${this.res.food}</span></div>
         <div class="zg-chip">🪨 <span id="rs">${this.res.stone}</span></div>
         <div class="zg-chip">⚔️ <span id="rsl">${this.res.soldiers}</span></div>`,
        `<div class="zg-chip">🏰 مستوى 5</div>`
      );
    },
    addFoot() {
      foot(`
        <button class="zg-btn" onclick="ZitexGame._s.build()">🏠 بناء</button>
        <button class="zg-btn" onclick="ZitexGame._s.train()">⚔️ تدريب جندي</button>
        <button class="zg-btn" onclick="ZitexGame._s.upgrade()">⭐ ترقية</button>
        <button class="zg-btn" onclick="ZitexGame._s.attack()">🔥 هجوم</button>
      `);
    },
    place(html, x, y, cls = 'b', tip = '') {
      const d = U.el('div', `left:${x}%;top:${y}%`, (tip ? `<div class="tt">${tip}</div>` : '') + html);
      d.className = cls;
      this.world.appendChild(d);
      return d;
    },
    addHills() {
      [[5, 38, 280, 70], [60, 35, 220, 55], [30, 40, 180, 50], [80, 36, 200, 60]].forEach(h => {
        const d = U.el('div', `left:${h[0]}%;top:${h[1]}%;width:${h[2]}px;height:${h[3]}px;background:linear-gradient(180deg,#5A9B4F,#4A8B3F)`);
        d.className = 'hill';
        this.world.appendChild(d);
      });
    },
    addClouds(n) {
      for (let i = 0; i < n; i++) {
        const d = U.el('div', `position:absolute;top:${2 + i * 5}%;opacity:.75;animation:fc ${30 + U.rnd(10, 30)}s linear infinite;animation-delay:-${U.rnd(0, 30)}s`);
        d.innerHTML = SVG.cloud(70 + U.rnd(0, 60));
        this.world.appendChild(d);
      }
    },
    addPaths() {
      [[30, 52, 220, 8, -5], [45, 60, 180, 8, 10], [20, 55, 150, 8, 3], [55, 48, 160, 8, -8]].forEach(p => {
        const d = U.el('div', `position:absolute;left:${p[0]}%;top:${p[1]}%;width:${p[2]}px;height:${p[3]}px;background:#8B7355;border-radius:4px;opacity:.5;transform:rotate(${p[4]}deg)`);
        this.world.appendChild(d);
      });
    },
    addTrees(n) { for (let i = 0; i < n; i++) { const x = U.rnd(3, 90), y = U.rnd(28, 85); const d = this.place(SVG.tree(U.rnd(35, 70)), x, y, 'b ts', 'شجرة'); d.style.zIndex = Math.floor(y); } },
    addBushes(n) { for (let i = 0; i < n; i++) this.place(SVG.bush(U.rnd(20, 40)), U.rnd(2, 95), U.rnd(35, 90), 'b', ''); },
    addFlowers(n) { for (let i = 0; i < n; i++) { const d = U.el('div', `position:absolute;left:${U.rnd(5, 92)}%;top:${U.rnd(30, 88)}%`); d.innerHTML = SVG.flower(U.rnd(8, 16)); this.world.appendChild(d); } },
    addRocks(n) { for (let i = 0; i < n; i++) this.place(SVG.rock(U.rnd(18, 35)), U.rnd(5, 90), U.rnd(35, 85), 'b', ''); },
    addCastle() { this.place(SVG.castle(170), 38, 24, 'b', 'القلعة الرئيسية'); },
    addHouses(n) { const P = [[18, 45], [62, 42], [25, 62], [70, 58], [15, 75], [55, 72], [78, 48], [30, 50], [68, 72]]; for (let i = 0; i < Math.min(n, P.length); i++) { const [x, y] = P[i]; this.place(SVG.house(U.rnd(50, 70)), x + U.rnd(-3, 3), y + U.rnd(-3, 3), 'b', `بيت ${i + 1}`); } },
    addFarms(n) { const P = [[10, 55], [72, 65], [45, 75]]; for (let i = 0; i < Math.min(n, P.length); i++) { const [x, y] = P[i]; this.place(SVG.farm(U.rnd(65, 90)), x, y, 'b', `مزرعة`); } },
    addMine() { this.place(SVG.mine(75), 82, 72, 'b', 'المنجم'); },
    addSoldiers(n) { const P = [[35, 55], [52, 55], [43, 65], [60, 50], [40, 50]]; for (let i = 0; i < Math.min(n, P.length); i++) { const [x, y] = P[i]; this.place(SVG.soldier(U.rnd(30, 38)), x, y, 'b sbn', `جندي ${i + 1}`); } },
    upd() { ['rg', 'rw', 'rf', 'rs', 'rsl'].forEach((id, i) => { const el = document.getElementById(id); if (el) el.textContent = Object.values(this.res)[i]; }); },
    build() { if (this.res.wood >= 50 && this.res.stone >= 30) { this.res.wood -= 50; this.res.stone -= 30; this.place(SVG.house(U.rnd(50, 65)), U.rnd(10, 80), U.rnd(40, 80), 'b', 'بناء جديد'); this.upd(); } else overlay('موارد غير كافية', 'تحتاج 50 خشب و 30 حجر', 'موافق'); },
    train() { if (this.res.food >= 30 && this.res.gold >= 20) { this.res.food -= 30; this.res.gold -= 20; this.res.soldiers++; this.place(SVG.soldier(32), U.rnd(30, 60), U.rnd(50, 70), 'b sbn', 'جندي جديد'); this.upd(); } else overlay('موارد غير كافية', 'تحتاج 30 طعام و 20 ذهب', 'موافق'); },
    upgrade() { if (this.res.gold >= 100) { this.res.gold -= 100; this.upd(); overlay('✨ تمت الترقية!', 'القلعة ارتقت لمستوى أعلى', 'رائع'); } else overlay('ذهب غير كاف', 'تحتاج 100 ذهب للترقية', 'موافق'); },
    attack() { overlay('⚔️ الهجوم', 'جيشك يتقدم نحو قرية العدو...', 'انتظار النصر'); },
  };

  // ============== CANVAS BASE ==============
  function canvasGame(w = 800, h = 500) {
    document.body.innerHTML = '';
    injectBaseStyle();
    const wrap = U.el('div', 'position:fixed;inset:50px 0 60px 0;display:flex;align-items:center;justify-content:center;background:radial-gradient(circle at 50% 50%,#1a1f3a,#050818)');
    const c = U.el('canvas');
    c.width = w; c.height = h;
    c.style.cssText = 'max-width:96%;max-height:96%;background:#0a0f25;border:2px solid rgba(255,215,0,.3);border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,.6)';
    wrap.appendChild(c);
    document.body.appendChild(wrap);
    return { canvas: c, ctx: c.getContext('2d'), w, h };
  }

  // ============== PLATFORMER ==============
  const Platformer = {
    init(cfg) {
      const { canvas, ctx, w, h } = canvasGame(900, 500);
      const theme = cfg.theme || 'forest';
      hud(`<div class="zg-chip">🪙 <span id="pcoin">0</span></div><div class="zg-chip">❤️ <span id="plife">3</span></div>`, `<div class="zg-chip">⭐ منصات</div>`);
      foot(`<button class="zg-btn" onclick="ZitexGame._resetCurrent()">🔄 إعادة</button><span style="color:#FFD700;align-self:center;font-size:12px">← → للحركة | Space للقفز</span>`);

      const player = { x: 60, y: 300, vx: 0, vy: 0, w: 30, h: 36, onGround: false, coins: 0, lives: 3 };
      const gravity = 0.55;
      const jumpPower = -11;
      const speed = 4;

      // Level
      const platforms = [
        { x: 0, y: 460, w: 900, h: 40 },
        { x: 150, y: 390, w: 120, h: 14 },
        { x: 320, y: 330, w: 110, h: 14 },
        { x: 480, y: 380, w: 130, h: 14 },
        { x: 670, y: 310, w: 120, h: 14 },
        { x: 230, y: 240, w: 100, h: 14 },
        { x: 540, y: 230, w: 110, h: 14 },
      ];
      const coins = [
        { x: 180, y: 360, got: false }, { x: 360, y: 300, got: false }, { x: 520, y: 350, got: false },
        { x: 710, y: 280, got: false }, { x: 270, y: 210, got: false }, { x: 580, y: 200, got: false },
        { x: 420, y: 430, got: false }, { x: 820, y: 430, got: false },
      ];
      const enemies = [
        { x: 400, y: 440, w: 28, h: 22, vx: 1.5, alive: true },
        { x: 680, y: 440, w: 28, h: 22, vx: -1.4, alive: true },
      ];

      const keys = {};
      const kd = e => { keys[e.code] = true; if (e.code === 'Space') e.preventDefault(); };
      const ku = e => { keys[e.code] = false; };
      window.addEventListener('keydown', kd);
      window.addEventListener('keyup', ku);
      ZitexGame._cleanup = () => { window.removeEventListener('keydown', kd); window.removeEventListener('keyup', ku); };

      // Touch
      let touchDir = 0, touchJump = false;
      canvas.addEventListener('touchstart', e => {
        const t = e.touches[0], r = canvas.getBoundingClientRect();
        const x = (t.clientX - r.left) / r.width;
        if (x < 0.4) touchDir = -1; else if (x > 0.6) touchDir = 1; else touchJump = true;
      });
      canvas.addEventListener('touchend', () => { touchDir = 0; touchJump = false; });

      let won = false, gameOver = false;

      function rect(a, b) { return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y; }

      function loop() {
        if (won || gameOver) { ZitexGame._cleanup && ZitexGame._cleanup(); return; }
        // Input
        if (keys.ArrowLeft || keys.KeyA || touchDir === -1) player.vx = -speed;
        else if (keys.ArrowRight || keys.KeyD || touchDir === 1) player.vx = speed;
        else player.vx *= 0.8;
        if ((keys.Space || keys.ArrowUp || keys.KeyW || touchJump) && player.onGround) { player.vy = jumpPower; player.onGround = false; }
        player.vy += gravity;
        player.x += player.vx; player.y += player.vy;
        player.onGround = false;
        platforms.forEach(p => {
          if (rect(player, p)) {
            if (player.vy > 0 && player.y + player.h - player.vy <= p.y + 1) { player.y = p.y - player.h; player.vy = 0; player.onGround = true; }
            else if (player.vy < 0 && player.y - player.vy >= p.y + p.h - 1) { player.y = p.y + p.h; player.vy = 0; }
            else if (player.vx > 0) { player.x = p.x - player.w; }
            else if (player.vx < 0) { player.x = p.x + p.w; }
          }
        });
        if (player.x < 0) player.x = 0;
        if (player.x > w - player.w) player.x = w - player.w;
        if (player.y > h) { player.lives--; player.x = 60; player.y = 300; player.vy = 0; document.getElementById('plife').textContent = player.lives; if (player.lives <= 0) gameOver = true; }

        coins.forEach(c => { if (!c.got && Math.abs(c.x - (player.x + player.w / 2)) < 20 && Math.abs(c.y - (player.y + player.h / 2)) < 20) { c.got = true; player.coins++; document.getElementById('pcoin').textContent = player.coins; if (coins.every(k => k.got)) won = true; } });
        enemies.forEach(e => {
          if (!e.alive) return;
          e.x += e.vx;
          if (e.x < 20 || e.x > w - 50) e.vx *= -1;
          if (rect(player, e)) {
            if (player.vy > 0 && player.y + player.h - e.y < 20) { e.alive = false; player.vy = -8; }
            else { player.lives--; player.x = 60; player.y = 300; document.getElementById('plife').textContent = player.lives; if (player.lives <= 0) gameOver = true; }
          }
        });

        // Draw
        const sky = ctx.createLinearGradient(0, 0, 0, h);
        sky.addColorStop(0, theme === 'night' ? '#0a0e2a' : '#87CEEB');
        sky.addColorStop(1, theme === 'night' ? '#2a1e4a' : '#FFB07C');
        ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);
        // Mountains
        ctx.fillStyle = 'rgba(100,70,120,.5)';
        ctx.beginPath(); ctx.moveTo(0, 400); ctx.lineTo(150, 200); ctx.lineTo(300, 380); ctx.lineTo(450, 150); ctx.lineTo(600, 360); ctx.lineTo(800, 220); ctx.lineTo(900, 400); ctx.fill();
        // Platforms
        platforms.forEach(p => {
          ctx.fillStyle = '#4a3322';
          ctx.fillRect(p.x, p.y, p.w, p.h);
          ctx.fillStyle = '#5a9b4f';
          ctx.fillRect(p.x, p.y, p.w, 6);
        });
        // Coins
        coins.forEach(c => {
          if (c.got) return;
          ctx.save();
          ctx.translate(c.x, c.y + Math.sin(Date.now() / 200 + c.x) * 3);
          ctx.fillStyle = '#FFD700';
          ctx.beginPath(); ctx.arc(0, 0, 8, 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = '#B8860B'; ctx.font = 'bold 10px sans-serif'; ctx.textAlign = 'center'; ctx.fillText('$', 0, 4);
          ctx.restore();
        });
        // Enemies
        enemies.forEach(e => {
          if (!e.alive) return;
          ctx.fillStyle = '#8B0000'; ctx.fillRect(e.x, e.y, e.w, e.h);
          ctx.fillStyle = '#fff'; ctx.fillRect(e.x + 5, e.y + 5, 5, 5); ctx.fillRect(e.x + 18, e.y + 5, 5, 5);
          ctx.fillStyle = '#000'; ctx.fillRect(e.x + 7, e.y + 7, 2, 2); ctx.fillRect(e.x + 20, e.y + 7, 2, 2);
        });
        // Player
        ctx.fillStyle = '#ff6b6b'; ctx.fillRect(player.x, player.y, player.w, player.h);
        ctx.fillStyle = '#fff'; ctx.fillRect(player.x + 6, player.y + 6, 6, 6); ctx.fillRect(player.x + 18, player.y + 6, 6, 6);
        ctx.fillStyle = '#000'; ctx.fillRect(player.x + 8, player.y + 8, 3, 3); ctx.fillRect(player.x + 20, player.y + 8, 3, 3);

        if (won) { overlay('🎉 فزت!', `جمعت ${player.coins} قطعة ذهبية`, 'إعادة اللعب', () => ZitexGame._resetCurrent()); return; }
        if (gameOver) { overlay('💀 انتهت اللعبة', 'حاول مرة أخرى', 'إعادة', () => ZitexGame._resetCurrent()); return; }
        requestAnimationFrame(loop);
      }
      loop();
    }
  };

  // ============== RACING ==============
  const Racing = {
    init(cfg) {
      const { canvas, ctx, w, h } = canvasGame(500, 650);
      hud(`<div class="zg-chip">🏁 المسافة: <span id="rdist">0</span> م</div><div class="zg-chip">❤️ <span id="rlife">3</span></div>`, `<div class="zg-chip">🏎️ سباق</div>`);
      foot(`<button class="zg-btn" onclick="ZitexGame._resetCurrent()">🔄 إعادة</button><span style="color:#FFD700;align-self:center;font-size:12px">← → للمسار</span>`);

      const lanes = [w / 4, w / 2, 3 * w / 4];
      let player = { lane: 1, y: h - 110, w: 50, h: 90, lives: 3 };
      let obstacles = [], dist = 0, speed = 6, gameOver = false, dashY = 0;

      const kd = e => {
        if (gameOver) return;
        if (e.code === 'ArrowLeft' || e.code === 'KeyA') player.lane = Math.max(0, player.lane - 1);
        if (e.code === 'ArrowRight' || e.code === 'KeyD') player.lane = Math.min(2, player.lane + 1);
      };
      window.addEventListener('keydown', kd);
      canvas.addEventListener('click', e => {
        const r = canvas.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width;
        if (x < 0.5) player.lane = Math.max(0, player.lane - 1);
        else player.lane = Math.min(2, player.lane + 1);
      });
      ZitexGame._cleanup = () => window.removeEventListener('keydown', kd);

      function car(x, y, col) {
        ctx.fillStyle = col; ctx.fillRect(x - 22, y - 40, 44, 80);
        ctx.fillStyle = '#1a1a2a'; ctx.fillRect(x - 18, y - 32, 36, 22);
        ctx.fillStyle = '#87CEEB'; ctx.fillRect(x - 16, y - 30, 32, 18);
        ctx.fillStyle = '#111'; ctx.fillRect(x - 24, y - 34, 4, 14); ctx.fillRect(x + 20, y - 34, 4, 14); ctx.fillRect(x - 24, y + 16, 4, 14); ctx.fillRect(x + 20, y + 16, 4, 14);
        ctx.fillStyle = '#FFD700'; ctx.fillRect(x - 14, y - 42, 8, 4); ctx.fillRect(x + 6, y - 42, 8, 4);
      }

      function loop() {
        if (gameOver) return;
        dist += speed / 10; document.getElementById('rdist').textContent = Math.floor(dist);
        speed = Math.min(14, 6 + dist / 200);
        dashY = (dashY + speed) % 40;
        if (Math.random() < 0.025 + speed / 400) obstacles.push({ lane: Math.floor(Math.random() * 3), y: -100, col: U.pick(['#e74c3c', '#3498db', '#f39c12', '#9b59b6']) });
        obstacles.forEach(o => o.y += speed);
        obstacles = obstacles.filter(o => o.y < h + 100);
        const px = lanes[player.lane];
        obstacles.forEach(o => {
          const ox = lanes[o.lane];
          if (Math.abs(ox - px) < 40 && Math.abs(o.y - player.y) < 70 && !o.hit) {
            o.hit = true; player.lives--; document.getElementById('rlife').textContent = player.lives;
            if (player.lives <= 0) gameOver = true;
          }
        });

        // Background
        ctx.fillStyle = '#2a3e1f'; ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = '#444'; ctx.fillRect(60, 0, w - 120, h);
        ctx.fillStyle = '#FFD700';
        for (let i = 0; i < 3; i++) {
          for (let y = -40 + dashY; y < h; y += 40) { ctx.fillRect(w / 2 - 3, y, 6, 20); }
          for (let y = -40 + dashY; y < h; y += 40) { ctx.fillRect(w / 4 - 2, y, 4, 20); ctx.fillRect(3 * w / 4 - 2, y, 4, 20); }
          break;
        }
        // Trees on sides
        for (let y = (dashY * 2) % 100 - 100; y < h; y += 100) {
          ctx.fillStyle = '#228B22'; ctx.beginPath(); ctx.arc(30, y, 25, 0, Math.PI * 2); ctx.fill();
          ctx.beginPath(); ctx.arc(w - 30, y + 50, 25, 0, Math.PI * 2); ctx.fill();
        }
        obstacles.forEach(o => car(lanes[o.lane], o.y, o.hit ? '#555' : o.col));
        car(px, player.y, '#2ecc71');

        if (gameOver) { overlay('💀 اصطدام!', `قطعت ${Math.floor(dist)} متر`, 'إعادة', () => ZitexGame._resetCurrent()); ZitexGame._cleanup(); return; }
        requestAnimationFrame(loop);
      }
      loop();
    }
  };

  // ============== SNAKE ==============
  const Snake = {
    init(cfg) {
      const cs = 22, cols = 28, rows = 20;
      const { canvas, ctx, w, h } = canvasGame(cols * cs, rows * cs);
      hud(`<div class="zg-chip">🍎 النقاط: <span id="sscore">0</span></div>`, `<div class="zg-chip">🐍 ثعبان</div>`);
      foot(`<button class="zg-btn" onclick="ZitexGame._resetCurrent()">🔄 إعادة</button><span style="color:#FFD700;align-self:center;font-size:12px">↑↓←→ للحركة</span>`);

      let snake = [{ x: 10, y: 10 }, { x: 9, y: 10 }, { x: 8, y: 10 }];
      let dir = { x: 1, y: 0 }, nextDir = { x: 1, y: 0 };
      let food = { x: 15, y: 10 };
      let score = 0, gameOver = false, tick = 0;

      const kd = e => {
        if (gameOver) return;
        if ((e.code === 'ArrowUp' || e.code === 'KeyW') && dir.y !== 1) nextDir = { x: 0, y: -1 };
        if ((e.code === 'ArrowDown' || e.code === 'KeyS') && dir.y !== -1) nextDir = { x: 0, y: 1 };
        if ((e.code === 'ArrowLeft' || e.code === 'KeyA') && dir.x !== 1) nextDir = { x: -1, y: 0 };
        if ((e.code === 'ArrowRight' || e.code === 'KeyD') && dir.x !== -1) nextDir = { x: 1, y: 0 };
      };
      window.addEventListener('keydown', kd);
      ZitexGame._cleanup = () => window.removeEventListener('keydown', kd);

      function spawnFood() {
        while (true) { food = { x: Math.floor(Math.random() * cols), y: Math.floor(Math.random() * rows) }; if (!snake.some(s => s.x === food.x && s.y === food.y)) break; }
      }
      function loop() {
        if (gameOver) return;
        tick++;
        if (tick % 6 === 0) {
          dir = nextDir;
          const head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };
          if (head.x < 0 || head.x >= cols || head.y < 0 || head.y >= rows || snake.some(s => s.x === head.x && s.y === head.y)) { gameOver = true; }
          else {
            snake.unshift(head);
            if (head.x === food.x && head.y === food.y) { score++; document.getElementById('sscore').textContent = score; spawnFood(); } else snake.pop();
          }
        }
        // Draw
        ctx.fillStyle = '#0a1a0a'; ctx.fillRect(0, 0, w, h);
        for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) { if ((i + j) % 2 === 0) { ctx.fillStyle = 'rgba(255,255,255,.02)'; ctx.fillRect(i * cs, j * cs, cs, cs); } }
        ctx.fillStyle = '#e74c3c';
        ctx.beginPath(); ctx.arc(food.x * cs + cs / 2, food.y * cs + cs / 2, cs / 2 - 2, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#228B22'; ctx.fillRect(food.x * cs + cs / 2 - 2, food.y * cs + 2, 4, 5);
        snake.forEach((s, i) => {
          const grad = ctx.createLinearGradient(s.x * cs, s.y * cs, s.x * cs + cs, s.y * cs + cs);
          grad.addColorStop(0, i === 0 ? '#2ecc71' : '#27ae60'); grad.addColorStop(1, i === 0 ? '#27ae60' : '#1e8449');
          ctx.fillStyle = grad; ctx.fillRect(s.x * cs + 1, s.y * cs + 1, cs - 2, cs - 2);
          if (i === 0) { ctx.fillStyle = '#fff'; ctx.fillRect(s.x * cs + 5, s.y * cs + 5, 4, 4); ctx.fillRect(s.x * cs + cs - 9, s.y * cs + 5, 4, 4); ctx.fillStyle = '#000'; ctx.fillRect(s.x * cs + 6, s.y * cs + 6, 2, 2); ctx.fillRect(s.x * cs + cs - 8, s.y * cs + 6, 2, 2); }
        });
        if (gameOver) { overlay('💀 انتهت اللعبة', `نقاطك: ${score}`, 'إعادة', () => ZitexGame._resetCurrent()); ZitexGame._cleanup(); return; }
        requestAnimationFrame(loop);
      }
      loop();
    }
  };

  // ============== SPACE SHOOTER ==============
  const Shooter = {
    init(cfg) {
      const { canvas, ctx, w, h } = canvasGame(700, 550);
      hud(`<div class="zg-chip">💥 <span id="sh_sc">0</span></div><div class="zg-chip">❤️ <span id="sh_lf">3</span></div>`, `<div class="zg-chip">🚀 فضاء</div>`);
      foot(`<button class="zg-btn" onclick="ZitexGame._resetCurrent()">🔄 إعادة</button><span style="color:#FFD700;align-self:center;font-size:12px">← → تحرك | Space اطلق</span>`);

      const player = { x: w / 2, y: h - 60, w: 40, h: 40, lives: 3 };
      const bullets = [], enemies = [], stars = [], particles = [];
      let score = 0, gameOver = false, fireCD = 0;
      for (let i = 0; i < 100; i++) stars.push({ x: Math.random() * w, y: Math.random() * h, s: Math.random() * 1.5 + 0.3 });

      const keys = {};
      const kd = e => { keys[e.code] = true; if (e.code === 'Space') e.preventDefault(); };
      const ku = e => { keys[e.code] = false; };
      window.addEventListener('keydown', kd); window.addEventListener('keyup', ku);
      ZitexGame._cleanup = () => { window.removeEventListener('keydown', kd); window.removeEventListener('keyup', ku); };

      function loop() {
        if (gameOver) return;
        if (keys.ArrowLeft || keys.KeyA) player.x = Math.max(20, player.x - 6);
        if (keys.ArrowRight || keys.KeyD) player.x = Math.min(w - 20, player.x + 6);
        if ((keys.Space || keys.ArrowUp) && fireCD <= 0) { bullets.push({ x: player.x, y: player.y - 20, vy: -10 }); fireCD = 10; }
        fireCD--;
        if (Math.random() < 0.03) enemies.push({ x: 40 + Math.random() * (w - 80), y: -40, vy: 2 + Math.random() * 2, w: 34, h: 34 });

        bullets.forEach(b => b.y += b.vy); bullets.splice(0, bullets.length, ...bullets.filter(b => b.y > -20));
        enemies.forEach(e => { e.y += e.vy; });
        // Collisions
        bullets.forEach(b => { enemies.forEach(e => { if (!e.dead && Math.abs(b.x - e.x - e.w / 2) < 22 && Math.abs(b.y - e.y - e.h / 2) < 22) { e.dead = true; b.hit = true; score += 10; document.getElementById('sh_sc').textContent = score; for (let i = 0; i < 12; i++) particles.push({ x: e.x + e.w / 2, y: e.y + e.h / 2, vx: (Math.random() - 0.5) * 6, vy: (Math.random() - 0.5) * 6, life: 30, col: U.pick(['#ff6b6b', '#ffd93d', '#ff8c00']) }); } }); });
        enemies.forEach(e => { if (!e.dead && Math.abs(e.x + e.w / 2 - player.x) < 30 && Math.abs(e.y + e.h / 2 - player.y) < 30) { e.dead = true; player.lives--; document.getElementById('sh_lf').textContent = player.lives; if (player.lives <= 0) gameOver = true; } });
        enemies.splice(0, enemies.length, ...enemies.filter(e => !e.dead && e.y < h + 50));
        bullets.splice(0, bullets.length, ...bullets.filter(b => !b.hit));
        particles.forEach(p => { p.x += p.vx; p.y += p.vy; p.life--; });
        particles.splice(0, particles.length, ...particles.filter(p => p.life > 0));

        // Draw
        ctx.fillStyle = '#03041a'; ctx.fillRect(0, 0, w, h);
        stars.forEach(s => { ctx.fillStyle = `rgba(255,255,255,${s.s / 1.5})`; ctx.fillRect(s.x, s.y, s.s, s.s); s.y += s.s * 0.5; if (s.y > h) { s.y = 0; s.x = Math.random() * w; } });
        // Player ship
        ctx.fillStyle = '#2ecc71'; ctx.beginPath(); ctx.moveTo(player.x, player.y - 22); ctx.lineTo(player.x - 20, player.y + 18); ctx.lineTo(player.x + 20, player.y + 18); ctx.closePath(); ctx.fill();
        ctx.fillStyle = '#87CEEB'; ctx.beginPath(); ctx.arc(player.x, player.y - 2, 6, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#ff8c00'; ctx.beginPath(); ctx.moveTo(player.x - 10, player.y + 18); ctx.lineTo(player.x, player.y + 28 + Math.random() * 6); ctx.lineTo(player.x + 10, player.y + 18); ctx.fill();
        // Bullets
        bullets.forEach(b => { ctx.fillStyle = '#FFD700'; ctx.fillRect(b.x - 2, b.y, 4, 14); });
        // Enemies
        enemies.forEach(e => { ctx.fillStyle = '#c0392b'; ctx.beginPath(); ctx.arc(e.x + e.w / 2, e.y + e.h / 2, 17, 0, Math.PI * 2); ctx.fill(); ctx.fillStyle = '#111'; ctx.fillRect(e.x + 8, e.y + 12, 18, 6); ctx.fillStyle = '#ff6b6b'; ctx.fillRect(e.x + 10, e.y + 13, 4, 4); ctx.fillRect(e.x + 20, e.y + 13, 4, 4); });
        particles.forEach(p => { ctx.fillStyle = p.col; ctx.globalAlpha = p.life / 30; ctx.fillRect(p.x, p.y, 3, 3); ctx.globalAlpha = 1; });

        if (gameOver) { overlay('💥 السفينة دُمّرت', `نقاطك: ${score}`, 'إعادة', () => ZitexGame._resetCurrent()); ZitexGame._cleanup(); return; }
        requestAnimationFrame(loop);
      }
      loop();
    }
  };

  // ============== MATCH 3 / PUZZLE ==============
  const Match3 = {
    init(cfg) {
      injectBaseStyle();
      document.body.innerHTML = '';
      const cols = 8, rows = 8;
      const gems = ['#ff6b6b', '#ffd93d', '#4ecdc4', '#a66bff', '#95e1a3', '#ff8c42'];
      let grid = Array.from({ length: rows }, () => Array.from({ length: cols }, () => Math.floor(Math.random() * gems.length)));
      let score = 0, sel = null;
      hud(`<div class="zg-chip">💎 <span id="m3_sc">0</span></div>`, `<div class="zg-chip">🧩 ألغاز</div>`);
      foot(`<button class="zg-btn" onclick="ZitexGame._resetCurrent()">🔄 إعادة</button><span style="color:#FFD700;align-self:center;font-size:12px">انقر على جوهرتين متجاورتين</span>`);

      const board = U.el('div', 'position:fixed;inset:60px 0 70px 0;display:flex;align-items:center;justify-content:center;background:radial-gradient(circle,#1a1f3a,#050818)');
      const gridEl = U.el('div', `display:grid;grid-template-columns:repeat(${cols},48px);gap:4px;padding:16px;background:rgba(0,0,0,.4);border-radius:16px;border:2px solid rgba(255,215,0,.3);box-shadow:0 10px 40px rgba(0,0,0,.6)`);
      board.appendChild(gridEl); document.body.appendChild(board);

      function render() {
        gridEl.innerHTML = '';
        for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
          const v = grid[r][c];
          const d = U.el('div', `width:48px;height:48px;background:${v >= 0 ? gems[v] : 'transparent'};border-radius:12px;cursor:pointer;transition:all .2s;box-shadow:inset 0 -4px 0 rgba(0,0,0,.25),inset 0 4px 0 rgba(255,255,255,.3);display:flex;align-items:center;justify-content:center;font-size:22px;${sel && sel.r === r && sel.c === c ? 'outline:3px solid #FFD700;transform:scale(1.1)' : ''}`);
          if (v >= 0) d.innerHTML = ['💎', '⭐', '🍀', '🔮', '🌟', '🔥'][v];
          d.onclick = () => click(r, c);
          gridEl.appendChild(d);
        }
      }
      function click(r, c) {
        if (!sel) { sel = { r, c }; render(); return; }
        const dx = Math.abs(sel.c - c), dy = Math.abs(sel.r - r);
        if (dx + dy === 1) {
          const tmp = grid[r][c]; grid[r][c] = grid[sel.r][sel.c]; grid[sel.r][sel.c] = tmp;
          sel = null;
          setTimeout(() => { if (!resolve()) { const tmp2 = grid[r][c]; grid[r][c] = grid[sel ? sel.r : r][sel ? sel.c : c]; } render(); }, 100);
        } else { sel = { r, c }; render(); }
      }
      function resolve() {
        let found = false;
        const mark = Array.from({ length: rows }, () => Array(cols).fill(false));
        for (let r = 0; r < rows; r++) for (let c = 0; c < cols - 2; c++) if (grid[r][c] >= 0 && grid[r][c] === grid[r][c + 1] && grid[r][c] === grid[r][c + 2]) { mark[r][c] = mark[r][c + 1] = mark[r][c + 2] = true; found = true; }
        for (let c = 0; c < cols; c++) for (let r = 0; r < rows - 2; r++) if (grid[r][c] >= 0 && grid[r][c] === grid[r + 1][c] && grid[r][c] === grid[r + 2][c]) { mark[r][c] = mark[r + 1][c] = mark[r + 2][c] = true; found = true; }
        if (found) {
          for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) if (mark[r][c]) { grid[r][c] = -1; score += 10; }
          document.getElementById('m3_sc').textContent = score;
          // Fall
          for (let c = 0; c < cols; c++) {
            const col = [];
            for (let r = rows - 1; r >= 0; r--) if (grid[r][c] !== -1) col.push(grid[r][c]);
            while (col.length < rows) col.push(Math.floor(Math.random() * gems.length));
            for (let r = rows - 1; r >= 0; r--) grid[r][c] = col[rows - 1 - r];
          }
          render(); setTimeout(resolve, 350);
        }
        return found;
      }
      render();
      setTimeout(resolve, 100);
    }
  };

  // ============== MEMORY ==============
  const Memory = {
    init(cfg) {
      injectBaseStyle();
      document.body.innerHTML = '';
      const icons = ['🎮', '🚀', '🎨', '🎵', '🏆', '🌟', '🎯', '💎'];
      const deck = [...icons, ...icons].sort(() => Math.random() - 0.5);
      let flipped = [], matched = 0, moves = 0, locked = false;
      hud(`<div class="zg-chip">🎯 الخطوات: <span id="mm_mv">0</span></div><div class="zg-chip">✨ <span id="mm_mt">0</span>/${icons.length}</div>`, `<div class="zg-chip">🧠 ذاكرة</div>`);
      foot(`<button class="zg-btn" onclick="ZitexGame._resetCurrent()">🔄 إعادة</button>`);
      const board = U.el('div', 'position:fixed;inset:60px 0 70px 0;display:flex;align-items:center;justify-content:center;background:radial-gradient(circle,#1a1f3a,#050818)');
      const grid = U.el('div', 'display:grid;grid-template-columns:repeat(4,90px);gap:10px;padding:20px;background:rgba(0,0,0,.4);border-radius:20px;border:2px solid rgba(255,215,0,.3)');
      board.appendChild(grid); document.body.appendChild(board);
      const cards = deck.map((icon, i) => {
        const c = U.el('div', 'width:90px;height:110px;perspective:800px;cursor:pointer');
        c.innerHTML = `<div style="position:relative;width:100%;height:100%;transition:transform .6s;transform-style:preserve-3d"><div style="position:absolute;inset:0;backface-visibility:hidden;background:linear-gradient(135deg,#4a3aff,#7a4aff);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:36px;color:#fff;border:2px solid rgba(255,215,0,.4)">?</div><div style="position:absolute;inset:0;backface-visibility:hidden;transform:rotateY(180deg);background:linear-gradient(135deg,#FFD700,#FF8C00);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:48px">${icon}</div></div>`;
        c.onclick = () => {
          if (locked || c.dataset.done || c.dataset.flip) return;
          c.firstChild.style.transform = 'rotateY(180deg)'; c.dataset.flip = '1';
          flipped.push({ el: c, icon });
          if (flipped.length === 2) {
            moves++; document.getElementById('mm_mv').textContent = moves;
            locked = true;
            if (flipped[0].icon === flipped[1].icon) { flipped.forEach(f => { f.el.dataset.done = '1'; f.el.style.opacity = '.4'; }); matched++; document.getElementById('mm_mt').textContent = matched; flipped = []; locked = false; if (matched === icons.length) setTimeout(() => overlay('🏆 فزت!', `أنجزت في ${moves} خطوة`, 'إعادة', () => ZitexGame._resetCurrent()), 400); }
            else { setTimeout(() => { flipped.forEach(f => { f.el.firstChild.style.transform = ''; delete f.el.dataset.flip; }); flipped = []; locked = false; }, 900); }
          }
        };
        grid.appendChild(c); return c;
      });
    }
  };

  // ============== BREAKOUT ==============
  const Breakout = {
    init(cfg) {
      const { canvas, ctx, w, h } = canvasGame(700, 500);
      hud(`<div class="zg-chip">💥 <span id="bo_sc">0</span></div><div class="zg-chip">❤️ <span id="bo_lf">3</span></div>`, `<div class="zg-chip">🧱 كسر الطوب</div>`);
      foot(`<button class="zg-btn" onclick="ZitexGame._resetCurrent()">🔄 إعادة</button><span style="color:#FFD700;align-self:center;font-size:12px">← → أو حرك الماوس</span>`);

      const paddle = { x: w / 2 - 55, y: h - 30, w: 110, h: 14 };
      const ball = { x: w / 2, y: h - 60, vx: 4, vy: -4, r: 8 };
      const bricks = [];
      const cols = 10, rows = 5, bw = 60, bh = 22, pad = 6;
      const colors = ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71', '#3498db'];
      for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) bricks.push({ x: 30 + c * (bw + pad), y: 60 + r * (bh + pad), w: bw, h: bh, alive: true, col: colors[r] });
      let score = 0, lives = 3, gameOver = false, won = false;
      const keys = {};
      const kd = e => keys[e.code] = true, ku = e => keys[e.code] = false;
      window.addEventListener('keydown', kd); window.addEventListener('keyup', ku);
      canvas.addEventListener('mousemove', e => { const r = canvas.getBoundingClientRect(); paddle.x = U.clamp((e.clientX - r.left) * (w / r.width) - paddle.w / 2, 0, w - paddle.w); });
      ZitexGame._cleanup = () => { window.removeEventListener('keydown', kd); window.removeEventListener('keyup', ku); };

      function loop() {
        if (gameOver || won) return;
        if (keys.ArrowLeft || keys.KeyA) paddle.x = Math.max(0, paddle.x - 7);
        if (keys.ArrowRight || keys.KeyD) paddle.x = Math.min(w - paddle.w, paddle.x + 7);
        ball.x += ball.vx; ball.y += ball.vy;
        if (ball.x < ball.r || ball.x > w - ball.r) ball.vx *= -1;
        if (ball.y < ball.r) ball.vy *= -1;
        if (ball.y > paddle.y && ball.x > paddle.x && ball.x < paddle.x + paddle.w && ball.vy > 0) { ball.vy *= -1; ball.vx += ((ball.x - (paddle.x + paddle.w / 2)) / (paddle.w / 2)) * 2; }
        if (ball.y > h) { lives--; document.getElementById('bo_lf').textContent = lives; if (lives <= 0) gameOver = true; else { ball.x = w / 2; ball.y = h - 60; ball.vx = 4; ball.vy = -4; } }
        bricks.forEach(b => {
          if (!b.alive) return;
          if (ball.x > b.x && ball.x < b.x + b.w && ball.y > b.y && ball.y < b.y + b.h) { b.alive = false; ball.vy *= -1; score += 10; document.getElementById('bo_sc').textContent = score; if (bricks.every(k => !k.alive)) won = true; }
        });

        const g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#0a0f25'); g.addColorStop(1, '#2a1f4a');
        ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        bricks.forEach(b => { if (!b.alive) return; ctx.fillStyle = b.col; ctx.fillRect(b.x, b.y, b.w, b.h); ctx.fillStyle = 'rgba(255,255,255,.2)'; ctx.fillRect(b.x, b.y, b.w, 3); });
        ctx.fillStyle = '#FFD700'; ctx.fillRect(paddle.x, paddle.y, paddle.w, paddle.h);
        ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(ball.x, ball.y, ball.r, 0, Math.PI * 2); ctx.fill();

        if (won) { overlay('🏆 فوز!', `نقاطك: ${score}`, 'إعادة', () => ZitexGame._resetCurrent()); ZitexGame._cleanup(); return; }
        if (gameOver) { overlay('💀 انتهت', `نقاطك: ${score}`, 'إعادة', () => ZitexGame._resetCurrent()); ZitexGame._cleanup(); return; }
        requestAnimationFrame(loop);
      }
      loop();
    }
  };

  // ============== FLAPPY-LIKE (bird) ==============
  const Flappy = {
    init(cfg) {
      const { canvas, ctx, w, h } = canvasGame(500, 600);
      hud(`<div class="zg-chip">🏆 <span id="fl_sc">0</span></div>`, `<div class="zg-chip">🐦 طيران</div>`);
      foot(`<button class="zg-btn" onclick="ZitexGame._resetCurrent()">🔄 إعادة</button><span style="color:#FFD700;align-self:center;font-size:12px">Space / انقر للقفز</span>`);
      const bird = { x: 120, y: h / 2, vy: 0, r: 16 };
      const pipes = [];
      let score = 0, gameOver = false, tick = 0;
      const jump = () => { if (!gameOver) bird.vy = -8; };
      const kd = e => { if (e.code === 'Space') { e.preventDefault(); jump(); } };
      window.addEventListener('keydown', kd);
      canvas.addEventListener('click', jump);
      ZitexGame._cleanup = () => window.removeEventListener('keydown', kd);
      function loop() {
        if (gameOver) return;
        tick++; bird.vy += 0.45; bird.y += bird.vy;
        if (tick % 90 === 0) { const gap = 160, top = 60 + Math.random() * (h - 300); pipes.push({ x: w, top, bot: top + gap, passed: false }); }
        pipes.forEach(p => p.x -= 3);
        pipes.forEach(p => { if (!p.passed && p.x + 60 < bird.x) { p.passed = true; score++; document.getElementById('fl_sc').textContent = score; } if (bird.x + bird.r > p.x && bird.x - bird.r < p.x + 60 && (bird.y - bird.r < p.top || bird.y + bird.r > p.bot)) gameOver = true; });
        if (bird.y > h - 20 || bird.y < 0) gameOver = true;
        // Draw
        const g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#87CEEB'); g.addColorStop(1, '#FFB07C');
        ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        pipes.forEach(p => {
          ctx.fillStyle = '#2ecc71'; ctx.fillRect(p.x, 0, 60, p.top); ctx.fillRect(p.x, p.bot, 60, h - p.bot);
          ctx.fillStyle = '#27ae60'; ctx.fillRect(p.x - 4, p.top - 24, 68, 24); ctx.fillRect(p.x - 4, p.bot, 68, 24);
        });
        ctx.fillStyle = '#8B4513'; ctx.fillRect(0, h - 20, w, 20);
        ctx.fillStyle = '#FFD700'; ctx.beginPath(); ctx.arc(bird.x, bird.y, bird.r, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(bird.x + 5, bird.y - 4, 5, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(bird.x + 6, bird.y - 4, 2.5, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#ff6b6b'; ctx.beginPath(); ctx.moveTo(bird.x + 12, bird.y); ctx.lineTo(bird.x + 22, bird.y - 3); ctx.lineTo(bird.x + 22, bird.y + 3); ctx.fill();
        if (gameOver) { overlay('💥 انتهت!', `نقاطك: ${score}`, 'إعادة', () => ZitexGame._resetCurrent()); ZitexGame._cleanup(); return; }
        requestAnimationFrame(loop);
      }
      loop();
    }
  };

  // ============== GENRE DETECTION ==============
  function detectGenre(cfg) {
    if (cfg.genre && cfg.genre !== 'auto') return cfg.genre;
    const hints = ((cfg.hint || '') + ' ' + (cfg.description || '')).toLowerCase();
    const map = [
      ['strategy', ['استراتيج', 'قرية', 'مبان', 'قلعة', 'حرب', 'جيش', 'مدينة', 'بناء', 'village', 'castle', 'kingdom', 'rts']],
      ['racing', ['سباق', 'سيار', 'طريق', 'race', 'car', 'racing']],
      ['platformer', ['منصات', 'platform', 'ماريو', 'mario', 'jump', 'قفز']],
      ['snake', ['ثعبان', 'snake', 'أفعى']],
      ['shooter', ['فضاء', 'إطلاق', 'shooter', 'space', 'بندقية', 'سفينة']],
      ['match3', ['ألغاز', 'match', 'puzzle', 'جواهر', 'كاندي', 'crush']],
      ['memory', ['ذاكرة', 'memory', 'بطاقات', 'مطابقة']],
      ['breakout', ['كسر', 'طوب', 'breakout', 'arkanoid']],
      ['flappy', ['طيران', 'طائر', 'flappy', 'bird']],
    ];
    for (const [g, kw] of map) if (kw.some(k => hints.includes(k))) return g;
    return 'strategy';
  }

  // ============== MAIN ==============
  const ZitexGame = {
    _cfg: null,
    _current: null,
    _s: Strategy,
    init(cfg = {}) {
      this._cfg = cfg;
      const genre = detectGenre(cfg);
      this._current = genre;
      const map = { strategy: Strategy, platformer: Platformer, racing: Racing, snake: Snake, shooter: Shooter, match3: Match3, memory: Memory, breakout: Breakout, flappy: Flappy };
      const g = map[genre] || Strategy;
      try { g.init(cfg); }
      catch (e) { console.error('ZitexGame error:', e); Strategy.init(cfg); }
    },
    _resetCurrent() {
      if (this._cleanup) { try { this._cleanup(); } catch (e) { } this._cleanup = null; }
      this.init(this._cfg || {});
    },
    _cleanup: null,
  };

  window.ZitexGame = ZitexGame;
})();
