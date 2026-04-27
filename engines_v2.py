"""Portfolio/finance section renderers — stock ticker, gold ticker, real-estate listings, stocks overlay."""
from typing import Dict, Any
from .renderer_helpers import _esc


def _section_gold_ticker(d, theme):
    """Live gold price ticker — 24k/22k/21k/18k SAR per gram."""
    return f"""<section id="gold-ticker" style="background:linear-gradient(135deg,#1a1a1a,#2a1a0a);border-bottom:2px solid #D4AF37;padding:14px 0;overflow:hidden;font-family:Tajawal,sans-serif">
<div id="zx-gk" style="display:flex;justify-content:center;align-items:center;gap:32px;flex-wrap:wrap;font-size:14px;color:#D4AF37;font-weight:700">جاري تحميل أسعار الذهب...</div>
<script>(function(){{async function load(){{try{{var u=window.location.pathname.split('/').filter(Boolean);var slug=u[u.length-1]||'';var r=await fetch('/api/websites/public/'+slug+'/gold-prices');var d=await r.json();var pg=d.per_gram||{{}};var items=[['24k',pg['24k']],['22k',pg['22k']],['21k',pg['21k']],['18k',pg['18k']]];var html=items.map(function(i){{return '<span style=\\"display:inline-flex;align-items:center;gap:6px\\"><span style=\\"background:rgba(212,175,55,.2);padding:3px 8px;border-radius:6px\\">'+i[0]+'</span><span>'+(i[1]||'—')+' ر.س/غ</span></span>'}}).join('');var live=d.live?'<span style=\\"color:#10b981;font-size:10px\\">● مباشر</span>':'<span style=\\"color:#888;font-size:10px\\">تقديري</span>';document.getElementById('zx-gk').innerHTML='<span style=\\"color:#D4AF37\\">💰 أسعار الذهب:</span>'+html+live;}}catch(e){{}}}};load();setInterval(load,600000);}})();</script>
</section>"""



def _section_stock_ticker(d, theme):
    """Top scrolling ticker of live market quotes."""
    return f"""<section id="stock-ticker-bar" style="background:#000;border-bottom:1px solid rgba(255,255,255,.1);padding:10px 0;overflow:hidden;font-family:monospace;font-size:14px;white-space:nowrap">
<div id="zx-tk" style="display:inline-block;animation:zxTk 40s linear infinite">جاري تحميل الأسعار...</div>
<style>@keyframes zxTk{{from{{transform:translateX(100%)}}to{{transform:translateX(-100%)}}}}</style>
<script>(function(){{async function load(){{try{{var r=await fetch('/api/websites/market/quotes');var d=await r.json();var html=(d.quotes||[]).map(function(q){{var c=q.change_pct>=0?'#10b981':'#ef4444';var ar=q.change_pct>=0?'▲':'▼';return '<span style="margin:0 24px"><b>'+q.symbol.split(':')[1]+'</b> '+q.price+' <span style="color:'+c+'">'+ar+' '+Math.abs(q.change_pct)+'%</span></span>'}}).join('');document.getElementById('zx-tk').innerHTML=html+html;}}catch(e){{}}}};load();setInterval(load,60000);}})();</script>
</section>"""



def _section_listings_grid(d, theme):
    """Real-estate listings grid — each card shows price, area, beds, location."""
    p = theme.get("primary", "#FFD700")
    t = d.get("title") or "العقارات المتاحة"
    return f"""<section id="listings-grid" style="padding:80px 20px;background:#0f0f14">
<h2 style="text-align:center;font-size:36px;font-weight:900;margin:0 0 32px">{_esc(t)}</h2>
<div id="zx-lst-filters" style="display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-bottom:24px"></div>
<div id="zx-lst-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;max-width:1200px;margin:0 auto"></div>
<script>(function(){{var SLUG=location.pathname.split('/').pop()||'';var all=[],type='all';
async function load(){{try{{var r=await fetch('/api/websites/public/'+SLUG+'/listings');var d=await r.json();all=d.listings||[];var types=['all','بيع','إيجار'];document.getElementById('zx-lst-filters').innerHTML=types.map(function(t){{return '<button data-t="'+t+'" style="padding:8px 18px;background:'+(t==type?'{p}':'rgba(255,255,255,.06)')+';color:'+(t==type?'#000':'#fff')+';border:0;border-radius:20px;font-weight:800;cursor:pointer;font-size:13px">'+(t==='all'?'الكل':t)+'</button>'}}).join('');document.querySelectorAll('#zx-lst-filters button').forEach(function(b){{b.onclick=function(){{type=b.dataset.t;load();}}}});render();}}catch(e){{}}}}
function render(){{var items=all.filter(function(l){{return type==='all'||l.transaction===type;}});var g=document.getElementById('zx-lst-grid');if(!items.length){{g.innerHTML='<div style="grid-column:1/-1;text-align:center;padding:40px;opacity:.6">لا عقارات</div>';return;}}g.innerHTML=items.map(function(l){{var img=(l.images&&l.images[0])||'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=600&q=70';var label=l.transaction==='إيجار'?'للإيجار':'للبيع';return '<div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:18px;overflow:hidden;cursor:pointer" onclick="window.zxLstOpen(\\''+l.id+'\\')"><div style="aspect-ratio:16/10;background:#000 url('+img+') center/cover;position:relative"><span style="position:absolute;top:12px;right:12px;background:{p};color:#000;padding:4px 10px;border-radius:20px;font-weight:900;font-size:11px">'+label+'</span></div><div style="padding:16px"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><span style="font-size:22px;font-weight:900;color:{p}">'+Number(l.price).toLocaleString()+' ر.س</span>'+(l.type?'<span style="font-size:11px;opacity:.7">'+l.type+'</span>':'')+'</div><div style="font-weight:800;margin-bottom:6px">'+(l.title||'')+'</div><div style="font-size:12px;opacity:.7;margin-bottom:8px">📍 '+(l.city||'')+' '+(l.district?'- '+l.district:'')+'</div><div style="display:flex;gap:12px;font-size:12px;opacity:.8">'+(l.bedrooms?'<span>🛏 '+l.bedrooms+' غرف</span>':'')+(l.bathrooms?'<span>🚿 '+l.bathrooms+'</span>':'')+(l.area_sqm?'<span>📐 '+l.area_sqm+' م²</span>':'')+'</div></div></div>'}}).join('');}}
window.zxLstOpen=function(id){{var l=all.find(function(x){{return x.id===id;}});if(!l)return;var m=document.createElement('div');m.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px';m.onclick=function(e){{if(e.target===m)m.remove();}};var imgs=(l.images||['https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=600']).map(function(i){{return '<img src="'+i+'" style="width:100%;border-radius:10px;margin-bottom:8px"/>'}}).join('');m.innerHTML='<div style="background:#0b0f1f;color:#fff;border-radius:20px;max-width:640px;width:100%;max-height:90vh;overflow:auto;padding:24px"><button onclick="this.parentElement.parentElement.remove()" style="float:left;background:rgba(255,255,255,.1);border:0;color:#fff;width:32px;height:32px;border-radius:50%;cursor:pointer">✕</button><h3 style="margin:0 0 8px">'+(l.title||'')+'</h3><div style="color:{p};font-size:28px;font-weight:900;margin-bottom:12px">'+Number(l.price).toLocaleString()+' ر.س</div>'+imgs+'<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:12px 0"><div style="background:rgba(255,255,255,.05);padding:10px;border-radius:10px"><div style="font-size:11px;opacity:.6">الموقع</div><div style="font-weight:800">'+(l.city||'')+' '+(l.district?' - '+l.district:'')+'</div></div><div style="background:rgba(255,255,255,.05);padding:10px;border-radius:10px"><div style="font-size:11px;opacity:.6">المساحة</div><div style="font-weight:800">'+(l.area_sqm||'-')+' م²</div></div><div style="background:rgba(255,255,255,.05);padding:10px;border-radius:10px"><div style="font-size:11px;opacity:.6">الغرف</div><div style="font-weight:800">'+(l.bedrooms||'-')+'</div></div><div style="background:rgba(255,255,255,.05);padding:10px;border-radius:10px"><div style="font-size:11px;opacity:.6">دورات المياه</div><div style="font-weight:800">'+(l.bathrooms||'-')+'</div></div></div>'+(l.description?'<p style="opacity:.8;line-height:1.7">'+l.description+'</p>':'')+'<a href="https://wa.me/'+(l.agent_phone||'').replace(/\\D/g,'')+'?text='+encodeURIComponent('استفسار عن: '+l.title)+'" target="_blank" style="display:block;width:100%;padding:14px;background:linear-gradient(90deg,{p},#f97316);color:#000;border:0;border-radius:12px;font-weight:900;text-align:center;text-decoration:none;margin-top:14px">💬 تواصل مع الدلّال عبر واتساب</a></div>';document.body.appendChild(m);}};
load();}})();</script></section>"""



def _portfolio_overlay(slug: str) -> str:
    """Inline Portfolio widget for stocks vertical — floating button + full modal.

    Uses the same fetch helpers as the auth overlay; relies on SiteToken in localStorage.
    """
    if not slug:
        return ""
    return (
        '<button id="zx-pf-fab" title="محفظتي">📈</button>'
        '<div id="zx-pf-modal" class="zx-pf-modal" style="display:none"><div class="zx-pf-card"><div class="zx-pf-head"><div><b>📈 محفظتي</b><div id="zx-pf-total" style="font-size:13px;opacity:.75">...</div></div><button class="zx-pf-x" onclick="document.getElementById(\'zx-pf-modal\').style.display=\'none\'">✕</button></div><div class="zx-pf-stats"><div><div class="zx-pf-lbl">الرصيد النقدي</div><div id="zx-pf-bal" class="zx-pf-val">—</div></div><div><div class="zx-pf-lbl">قيمة الاستثمارات</div><div id="zx-pf-mkt" class="zx-pf-val">—</div></div><div><div class="zx-pf-lbl">الأرباح/الخسائر</div><div id="zx-pf-pnl" class="zx-pf-val">—</div></div></div><div id="zx-pf-chart"></div><div class="zx-pf-tabs"><button class="zx-pf-t zx-pf-t-on" data-tab="p">محفظتي</button><button class="zx-pf-t" data-tab="m">السوق</button><button class="zx-pf-t" data-tab="h">السجل</button></div><div id="zx-pf-body"></div><div class="zx-pf-note">⚠️ محاكاة تعليمية — لا أموال حقيقية</div></div></div>'
        '<style>'
        '#zx-pf-fab{position:fixed;top:78px;left:16px;z-index:95;width:46px;height:46px;border-radius:50%;background:linear-gradient(135deg,#2563eb,#0891b2);color:#fff;border:2px solid rgba(255,255,255,.2);cursor:pointer;font-size:20px;box-shadow:0 8px 24px rgba(37,99,235,.4)}'
        '.zx-pf-modal{position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:1200;display:flex;align-items:center;justify-content:center;padding:16px;backdrop-filter:blur(4px)}'
        '.zx-pf-card{width:100%;max-width:540px;max-height:92vh;overflow:auto;background:#0b0f1f;color:#fff;border:1px solid rgba(255,255,255,.1);border-radius:20px;padding:18px}'
        '.zx-pf-head{display:flex;justify-content:space-between;align-items:start;margin-bottom:14px;gap:10px}'
        '.zx-pf-x{background:rgba(255,255,255,.08);color:#fff;border:0;width:30px;height:30px;border-radius:50%;cursor:pointer;font-size:14px}'
        '.zx-pf-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}'
        '.zx-pf-stats>div{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:8px;text-align:center}'
        '.zx-pf-lbl{font-size:10px;opacity:.65;margin-bottom:2px}'
        '.zx-pf-val{font-size:15px;font-weight:900}'
        '#zx-pf-chart{height:70px;background:rgba(255,255,255,.03);border-radius:10px;margin-bottom:12px;position:relative;overflow:hidden}'
        '.zx-pf-tabs{display:flex;gap:6px;margin-bottom:10px}'
        '.zx-pf-t{flex:1;padding:8px;background:rgba(255,255,255,.05);border:0;border-radius:8px;color:#fff;cursor:pointer;font-size:12px;font-weight:700}'
        '.zx-pf-t-on{background:linear-gradient(90deg,#2563eb,#0891b2)}'
        '.zx-pf-row{display:flex;justify-content:space-between;align-items:center;padding:10px;background:rgba(255,255,255,.04);border-radius:10px;margin-bottom:6px;font-size:13px}'
        '.zx-pf-sym{font-weight:900}.zx-pf-sub{font-size:10px;opacity:.65}'
        '.zx-pf-up{color:#10b981}.zx-pf-dn{color:#ef4444}'
        '.zx-pf-btn{padding:5px 10px;border-radius:6px;border:0;cursor:pointer;font-size:11px;font-weight:800;margin-right:4px}'
        '.zx-pf-b{background:#10b981;color:#000}.zx-pf-s{background:#ef4444;color:#fff}'
        '.zx-pf-note{text-align:center;font-size:10px;opacity:.5;margin-top:8px;padding:6px;background:rgba(239,68,68,.1);border-radius:8px}'
        '.zx-pf-form{background:rgba(37,99,235,.1);border:1px solid rgba(37,99,235,.3);border-radius:10px;padding:10px;margin:6px 0}'
        '.zx-pf-inp{width:100%;padding:7px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.15);border-radius:6px;color:#fff;font-size:13px;margin:4px 0}'
        '.zx-pf-cta{width:100%;padding:8px;background:linear-gradient(90deg,#10b981,#059669);color:#000;border:0;border-radius:8px;font-weight:900;cursor:pointer;font-size:13px}'
        '.zx-pf-cta-s{background:linear-gradient(90deg,#ef4444,#dc2626);color:#fff}'
        '</style>'
        f'<script>(function(){{var API="";var SLUG="{slug}";'
        'function tk(){return localStorage.getItem("zx_site_token_"+SLUG);}'
        'async function api(p,o){var r=await fetch(API+"/api/websites"+p,{...o,headers:{"Content-Type":"application/json",...(o&&o.headers||{}),...(tk()?{"Authorization":"SiteToken "+tk()}:{})}});var d=await r.json();if(!r.ok)throw new Error(d.detail||"خطأ");return d;}'
        'var pf=null,mkt=[],tab="p",hist=[];'
        'async function refresh(){try{pf=await api("/public/"+SLUG+"/portfolio/me");var q=await fetch(API+"/api/websites/market/quotes");mkt=(await q.json()).quotes||[];hist.push(pf.total_value);if(hist.length>40)hist.shift();render();}catch(e){document.getElementById("zx-pf-body").innerHTML=\'<div style="text-align:center;padding:30px;opacity:.7">يجب تسجيل الدخول أولاً</div>\';}}'
        'function fmt(n){return (n||0).toLocaleString(\'ar-SA\',{minimumFractionDigits:2,maximumFractionDigits:2})}'
        'function chart(){if(hist.length<2)return"";var mi=Math.min(...hist),ma=Math.max(...hist),rn=ma-mi||1;var w=500,h=70;var pts=hist.map(function(v,i){return (i*(w/(hist.length-1)))+","+(h-((v-mi)/rn)*h)}).join(" ");var up=hist[hist.length-1]>=hist[0];return \'<svg viewBox="0 0 \'+w+\' \'+h+\'" preserveAspectRatio="none" style="width:100%;height:100%"><polyline points="\'+pts+\'" fill="none" stroke="\'+(up?"#10b981":"#ef4444")+\'" stroke-width="2"/></svg>\';}'
        'function render(){if(!pf)return;'
        'document.getElementById("zx-pf-bal").textContent=fmt(pf.balance)+" ر.س";'
        'document.getElementById("zx-pf-mkt").textContent=fmt(pf.market_value)+" ر.س";'
        'var pnl=pf.pnl_total;var pnlEl=document.getElementById("zx-pf-pnl");pnlEl.textContent=(pnl>=0?"+":"")+fmt(pnl)+" ر.س";pnlEl.className="zx-pf-val "+(pnl>=0?"zx-pf-up":"zx-pf-dn");'
        'document.getElementById("zx-pf-total").textContent="إجمالي: "+fmt(pf.total_value)+" ر.س";'
        'document.getElementById("zx-pf-chart").innerHTML=chart();'
        'var b=document.getElementById("zx-pf-body"),h="";'
        'if(tab==="p"){if(!pf.positions.length)h=\'<div style="text-align:center;padding:20px;opacity:.7">لا استثمارات بعد — تصفّح السوق 👉</div>\';pf.positions.forEach(function(p){var cls=p.pnl>=0?"zx-pf-up":"zx-pf-dn";h+=\'<div class="zx-pf-row"><div><div class="zx-pf-sym">\'+p.symbol.split(":")[1]+\'</div><div class="zx-pf-sub">\'+p.name+\' · \'+p.qty+\' سهم</div></div><div style="text-align:left"><div>\'+fmt(p.price)+\'</div><div class="\'+cls+\'" style="font-size:11px">\'+(p.pnl>=0?"+":"")+fmt(p.pnl)+\' (\'+p.pnl_pct.toFixed(1)+\'%)</div></div></div>\';if(p._sell){h+=\'<div class="zx-pf-form"><input class="zx-pf-inp" id="pf-qty-\'+p.symbol+\'" type="number" step="0.1" placeholder="الكمية للبيع"/><button class="zx-pf-cta zx-pf-cta-s" onclick="window.zxPfTrade(\\\'\'+p.symbol+\'\\\',\\\'sell\\\')">💰 بيع</button></div>\';}else{h+=\'<div style="text-align:center;margin-bottom:6px"><button class="zx-pf-btn zx-pf-s" onclick="window.zxPfMarkSell(\\\'\'+p.symbol+\'\\\')">💰 بيع</button></div>\';}});}'
        'else if(tab==="m"){mkt.forEach(function(q){var cls=q.change_pct>=0?"zx-pf-up":"zx-pf-dn";h+=\'<div class="zx-pf-row"><div><div class="zx-pf-sym">\'+q.symbol.split(":")[1]+\'</div><div class="zx-pf-sub">\'+q.name+\'</div></div><div style="text-align:left"><div>\'+fmt(q.price)+\'</div><div class="\'+cls+\'" style="font-size:11px">\'+(q.change_pct>=0?"+":"")+q.change_pct+\'%</div></div></div>\';if(q._buy){h+=\'<div class="zx-pf-form"><input class="zx-pf-inp" id="pf-qty-\'+q.symbol+\'" type="number" step="0.1" placeholder="الكمية للشراء"/><button class="zx-pf-cta" onclick="window.zxPfTrade(\\\'\'+q.symbol+\'\\\',\\\'buy\\\')">🛒 شراء</button></div>\';}else{h+=\'<div style="text-align:center;margin-bottom:6px"><button class="zx-pf-btn zx-pf-b" onclick="window.zxPfMarkBuy(\\\'\'+q.symbol+\'\\\')">🛒 شراء</button></div>\';}});}'
        'else{(pf.trades||[]).slice().reverse().forEach(function(t){var cls=t.side==="buy"?"zx-pf-up":"zx-pf-dn";h+=\'<div class="zx-pf-row"><div><div class="zx-pf-sym \'+cls+\'">\'+(t.side==="buy"?"🛒 شراء":"💰 بيع")+\' \'+t.symbol.split(":")[1]+\'</div><div class="zx-pf-sub">\'+new Date(t.at).toLocaleString("ar-SA")+\'</div></div><div style="text-align:left"><div>\'+t.qty+\' × \'+fmt(t.price)+\'</div></div></div>\';});if(!(pf.trades||[]).length)h=\'<div style="text-align:center;padding:20px;opacity:.7">لا صفقات بعد</div>\';}'
        'b.innerHTML=h;}'
        'window.zxPfMarkBuy=function(s){mkt.forEach(function(q){q._buy=q.symbol===s});mkt.forEach(function(q){if(q.symbol!==s)q._buy=false});render();};'
        'window.zxPfMarkSell=function(s){pf.positions.forEach(function(p){p._sell=p.symbol===s});render();};'
        'window.zxPfTrade=async function(sym,side){var q=parseFloat(document.getElementById("pf-qty-"+sym).value);if(!q||q<=0)return alert("أدخل كمية صحيحة");try{var r=await api("/public/"+SLUG+"/portfolio/trade",{method:"POST",body:JSON.stringify({symbol:sym,side:side,qty:q})});alert("✅ "+(side==="buy"?"تم الشراء":"تم البيع")+"\\nالرصيد الجديد: "+fmt(r.new_balance)+" ر.س");await refresh();}catch(e){alert("❌ "+e.message);}};'
        'document.querySelectorAll(".zx-pf-t").forEach(function(b){b.onclick=function(){tab=b.dataset.tab;document.querySelectorAll(".zx-pf-t").forEach(function(x){x.classList.toggle("zx-pf-t-on",x===b)});render();};});'
        'document.getElementById("zx-pf-fab").onclick=function(){document.getElementById("zx-pf-modal").style.display="flex";refresh();};'
        'setInterval(function(){if(document.getElementById("zx-pf-modal").style.display==="flex")refresh();},15000);'
        '})();</script>'
    )


