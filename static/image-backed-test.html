<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<title>قرية الملك</title>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box;font-family:Tajawal,sans-serif}
  html,body{width:100%;height:100%;overflow:hidden;background:#000}
  .scene{position:fixed;inset:0;background-image:url('https://images.unsplash.com/photo-1518709766631-a6a7f45921c3?w=1600');background-size:cover;background-position:center;background-repeat:no-repeat}
  .scene::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.35),transparent 25%,transparent 75%,rgba(0,0,0,.45));pointer-events:none}
  .zg-hud{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;justify-content:space-between;padding:10px 16px;background:linear-gradient(180deg,rgba(0,0,0,0.75),rgba(0,0,0,0.2));backdrop-filter:blur(10px);color:#fff;font-weight:700}
  .zg-hud .left,.zg-hud .right{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  .zg-chip{display:flex;align-items:center;gap:6px;background:rgba(255,255,255,0.12);padding:6px 12px;border-radius:20px;font-size:13px;border:1px solid rgba(255,215,0,0.3)}
  .zg-foot{position:fixed;bottom:0;left:0;right:0;z-index:100;display:flex;justify-content:center;gap:8px;padding:10px;background:rgba(0,0,0,0.6);backdrop-filter:blur(10px)}
  .zg-btn{padding:9px 18px;border:2px solid rgba(255,215,0,0.5);border-radius:12px;background:rgba(255,215,0,0.15);color:#FFD700;font-weight:700;cursor:pointer;transition:all .25s;font-size:13px;font-family:inherit}
  .zg-btn:hover{background:rgba(255,215,0,0.35);transform:translateY(-2px);box-shadow:0 4px 14px rgba(255,215,0,0.3)}
  .hotspot{position:absolute;width:80px;height:80px;border-radius:50%;cursor:pointer;transition:all .3s;display:flex;align-items:center;justify-content:center;color:#FFD700;font-size:11px;font-weight:700;text-align:center;text-shadow:0 1px 3px rgba(0,0,0,.9)}
  .hotspot::before{content:"";position:absolute;inset:0;border-radius:50%;background:radial-gradient(circle,rgba(255,215,0,.35) 0%,rgba(255,215,0,0) 70%);animation:pulse 2s ease-in-out infinite}
  .hotspot:hover{transform:scale(1.15)}
  .hotspot:hover::before{background:radial-gradient(circle,rgba(255,215,0,.6) 0%,rgba(255,215,0,0) 70%)}
  .tt{display:none;position:absolute;bottom:calc(100% + 6px);left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.92);color:#fff;padding:6px 12px;border-radius:8px;white-space:nowrap;font-size:12px;border:1px solid rgba(255,215,0,0.3);z-index:99}
  .hotspot:hover .tt{display:block}
  .zg-overlay{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.78);z-index:200;backdrop-filter:blur(6px)}
  .zg-card{background:linear-gradient(135deg,#1a1f3a,#2a2f5a);padding:28px 36px;border-radius:18px;text-align:center;color:#fff;border:2px solid rgba(255,215,0,0.4);box-shadow:0 20px 60px rgba(0,0,0,.5);min-width:280px;animation:pop .35s ease}
  .zg-card h1{font-size:24px;color:#FFD700;margin-bottom:8px}
  .zg-card p{font-size:14px;opacity:.9;margin-bottom:16px;line-height:1.6}
  .zg-badge{position:fixed;bottom:60px;right:10px;z-index:90;font-size:10px;color:rgba(255,255,255,.45);background:rgba(0,0,0,.4);padding:3px 8px;border-radius:10px}
  @keyframes pulse{0%,100%{transform:scale(1);opacity:.9}50%{transform:scale(1.15);opacity:.5}}
  @keyframes pop{0%{transform:scale(.7);opacity:0}100%{transform:scale(1);opacity:1}}
</style>
</head>
<body>
<div class="scene"></div>
<div class="zg-hud"><div class="left">
        <div class="zg-chip">💰 <span id="rg">500</span></div>
        <div class="zg-chip">🪵 <span id="rw">300</span></div>
        <div class="zg-chip">🌾 <span id="rf">400</span></div>
        <div class="zg-chip">🪨 <span id="rs">150</span></div>
        <div class="zg-chip">⚔️ <span id="rsl">4</span></div></div><div class="right"><div class="zg-chip">🎮 قرية الملك</div></div></div>
<div id="hot-layer"></div>
<div class="zg-foot">
        <button class="zg-btn" onclick="ZG.act('build')">🏠 بناء</button>
        <button class="zg-btn" onclick="ZG.act('train')">⚔️ تدريب</button>
        <button class="zg-btn" onclick="ZG.act('upgrade')">⭐ ترقية</button>
        <button class="zg-btn" onclick="ZG.act('attack')">🔥 هجوم</button></div>
<div class="zg-badge">Zitex Engine · Image-backed</div>
<script>
(function(){
  const genre = 'strategy';
  const state = { gold:500, wood:300, food:400, stone:150, soldiers:4, dist:0, lives:3, score:0 };
  const upd = () => {
    const map = {rg:state.gold, rw:state.wood, rf:state.food, rs:state.stone, rsl:state.soldiers};
    if (genre==='racing'){ map.rg = state.dist; map.rsl = state.lives; }
    if (genre==='platformer'){ map.rg = state.score; map.rsl = state.lives; }
    Object.entries(map).forEach(([k,v])=>{ const el=document.getElementById(k); if(el) el.textContent=v; });
  };
  const overlay = (title,msg,btn,onBtn) => {
    const o = document.createElement('div'); o.className='zg-overlay';
    o.innerHTML = '<div class="zg-card"><h1>'+title+'</h1><p>'+msg+'</p><button class="zg-btn">'+btn+'</button></div>';
    document.body.appendChild(o);
    o.querySelector('button').onclick = () => { o.remove(); if(onBtn) onBtn(); };
  };

  // Auto place interactive hotspots across the background image (plausible building locations)
  // The image fills the viewport via background-size:cover; hotspots are placed in relative % coords.
  const hotspots = [
    {x:50, y:32, icon:'🏰', label:'القلعة الرئيسية - المستوى 5', action:'castle'},
    {x:24, y:50, icon:'🏠', label:'بيت - المستوى 2', action:'house'},
    {x:72, y:48, icon:'🏠', label:'بيت - المستوى 3', action:'house'},
    {x:18, y:68, icon:'🏡', label:'بيت - المستوى 1', action:'house'},
    {x:80, y:65, icon:'🏠', label:'بيت - المستوى 2', action:'house'},
    {x:38, y:72, icon:'🌾', label:'مزرعة - +5 طعام/ث', action:'farm'},
    {x:62, y:75, icon:'🌾', label:'مزرعة - +4 طعام/ث', action:'farm'},
    {x:88, y:80, icon:'⛏️', label:'منجم - +3 حجر/ث', action:'mine'},
    {x:45, y:55, icon:'⚔️', label:'جندي - قوة 20', action:'soldier'},
    {x:55, y:58, icon:'⚔️', label:'جندي - قوة 18', action:'soldier'},
    {x:12, y:30, icon:'🌲', label:'غابة - خشب', action:'forest'},
    {x:88, y:28, icon:'🌲', label:'غابة - خشب', action:'forest'},
  ];
  const layer = document.getElementById('hot-layer');
  if (genre === 'strategy') {
    hotspots.forEach(h => {
      const d = document.createElement('div');
      d.className = 'hotspot';
      d.style.cssText = 'left:calc('+h.x+'% - 40px);top:calc('+h.y+'% - 40px)';
      d.innerHTML = '<div class="tt">'+h.label+'</div>'+h.icon;
      d.onclick = () => {
        if (h.action === 'house') { state.gold += 10; state.wood += 5; upd(); }
        else if (h.action === 'farm') { state.food += 15; upd(); }
        else if (h.action === 'mine') { state.stone += 10; state.gold += 5; upd(); }
        else if (h.action === 'forest') { state.wood += 20; upd(); }
        else if (h.action === 'soldier') { overlay('⚔️ الجندي','قوة الهجوم: 20','موافق'); }
        else if (h.action === 'castle') { overlay('🏰 القلعة الرئيسية','المستوى 5 · السلامة 100%','موافق'); }
      };
      layer.appendChild(d);
    });
    // Passive income
    setInterval(()=>{ state.gold+=5; state.wood+=3; state.food+=4; state.stone+=2; upd(); }, 3000);
  }

  window.ZG = {
    state, upd, overlay,
    act(kind){
      if (genre !== 'strategy') return overlay('قريباً','هذا الإجراء سيُضاف في المرحلة التالية','موافق');
      if (kind === 'build')  { if (state.wood>=50 && state.stone>=30){ state.wood-=50; state.stone-=30; upd(); overlay('🏠 بُني بيت جديد','تمت إضافة مبنى جديد للقرية','رائع'); } else overlay('موارد غير كافية','تحتاج 50 خشب و 30 حجر','موافق'); }
      else if (kind === 'train')  { if (state.food>=30 && state.gold>=20){ state.food-=30; state.gold-=20; state.soldiers++; upd(); overlay('⚔️ جندي جديد','انضم جندي للجيش','رائع'); } else overlay('موارد غير كافية','تحتاج 30 طعام و 20 ذهب','موافق'); }
      else if (kind === 'upgrade'){ if (state.gold>=100){ state.gold-=100; upd(); overlay('✨ ترقية','ارتقت القلعة لمستوى أعلى','رائع'); } else overlay('ذهب غير كاف','تحتاج 100 ذهب','موافق'); }
      else if (kind === 'attack') { overlay('⚔️ هجوم','جيشك يتقدم نحو قرية العدو...','انتظار النصر'); }
    }
  };
  upd();
})();
</script>
<!-- Zitex: hint="" genre="strategy" image-backed -->
</body>
</html>