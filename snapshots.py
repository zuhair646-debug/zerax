"""E-commerce section renderers — products, menu, filtered product grid."""
from typing import Dict, Any
from .renderer_helpers import _esc


def _section_products(d, theme) -> str:
    items = d.get("items", [])
    cards = "".join(
        f"""<div class="product-card">
          <div class="product-image" style="background-image:url('{_esc(i.get('image',''))}')">{f'<span class="badge">{_esc(i["badge"])}</span>' if i.get("badge") else ''}</div>
          <div class="product-body"><h3>{_esc(i.get('name',''))}</h3>
          <div class="price-row">{f'<span class="old-price">{_esc(i["old_price"])} ر.س</span>' if i.get("old_price") else ''}<span class="price">{_esc(i.get('price',''))}</span></div>
          <button class="btn btn-sm">أضف للسلة</button></div></div>"""
        for i in items
    )
    return f"""<section class="products" id="products" data-hl="products"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div class="product-grid">{cards}</div></div></section>"""



def _section_menu(d, theme) -> str:
    style = d.get("style") or "grid"
    cats = d.get("categories", [])
    if style == "list":
        # Vertical list layout — ideal for restaurants/cafes
        cats_html = ""
        for c in cats:
            items_html = "".join(
                f"""<div class="menu-list-row"><div class="menu-list-name">{_esc(i.get('name',''))}</div><div class="menu-list-dots"></div><div class="menu-list-price">{_esc(i.get('price',''))} ر.س</div></div>"""
                + (f'<div class="menu-list-desc">{_esc(i.get("desc",""))}</div>' if i.get("desc") else "")
                for i in c.get("items", [])
            )
            cats_html += f"""<div class="menu-list-cat"><h3>{_esc(c.get('name',''))}</h3>{items_html}</div>"""
        return f"""<section class="menu menu-list-style" id="menu" data-hl="menu"><div class="container"><h2>{_esc(d.get('title',''))}</h2>{cats_html}</div><style>.menu-list-style{{background:#0b0d14}}.menu-list-cat{{margin-bottom:36px}}.menu-list-cat h3{{color:#FFD700;border-bottom:2px solid rgba(255,215,0,.3);padding-bottom:8px;margin-bottom:16px;font-size:24px}}.menu-list-row{{display:flex;align-items:center;gap:8px;padding:8px 0;font-size:16px}}.menu-list-name{{font-weight:700}}.menu-list-dots{{flex:1;border-bottom:2px dotted rgba(255,255,255,.25)}}.menu-list-price{{color:#FFD700;font-weight:900;white-space:nowrap}}.menu-list-desc{{opacity:.65;font-size:13px;padding:0 4px 8px;line-height:1.6}}</style></section>"""
    if style == "carousel":
        items = [i for c in cats for i in c.get("items", [])]
        cards = "".join(
            f"""<div class="menu-car-card">{f'<img src="{_esc(i["image"])}" alt=""/>' if i.get("image") else ''}<div class="menu-car-body"><h4>{_esc(i.get('name',''))}</h4><span class="menu-car-price">{_esc(i.get('price',''))} ر.س</span></div></div>"""
            for i in items
        )
        return f"""<section class="menu menu-carousel-style" id="menu" data-hl="menu"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div class="menu-car-strip">{cards}</div></div><style>.menu-car-strip{{display:flex;gap:16px;overflow-x:auto;padding:16px 4px;scroll-snap-type:x mandatory}}.menu-car-strip::-webkit-scrollbar{{height:6px}}.menu-car-strip::-webkit-scrollbar-thumb{{background:rgba(255,255,255,.2);border-radius:4px}}.menu-car-card{{flex:0 0 240px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:14px;overflow:hidden;scroll-snap-align:start}}.menu-car-card img{{width:100%;height:160px;object-fit:cover;display:block}}.menu-car-body{{padding:12px;display:flex;justify-content:space-between;align-items:center}}.menu-car-body h4{{margin:0;font-size:15px}}.menu-car-price{{color:#FFD700;font-weight:900}}</style></section>"""
    # default: grid (classic)
    cats_html = ""
    for c in cats:
        items_html = "".join(
            f"""<div class="menu-item">{f'<img src="{_esc(i["image"])}" alt=""/>' if i.get("image") else ''}<div class="menu-body"><div class="menu-row"><h4>{_esc(i.get('name',''))}</h4><span class="menu-price">{_esc(i.get('price',''))} ر.س</span></div>{f'<p>{_esc(i["desc"])}</p>' if i.get("desc") else ''}</div></div>"""
            for i in c.get("items", [])
        )
        cats_html += f"""<div class="menu-cat"><h3>{_esc(c.get('name',''))}</h3><div class="menu-grid">{items_html}</div></div>"""
    return f"""<section class="menu" id="menu" data-hl="menu"><div class="container"><h2>{_esc(d.get('title',''))}</h2>{cats_html}</div></section>"""



def _section_product_grid_filters(d, theme):
    """E-commerce product grid with category filters + cart integration."""
    p = theme.get("primary", "#FFD700")
    t = d.get("title") or "تسوّق منتجاتنا"
    return f"""<section id="product-grid" style="padding:80px 20px;background:#0f0f14">
<h2 style="text-align:center;font-size:36px;font-weight:900;margin:0 0 32px">{_esc(t)}</h2>
<div id="zx-pg-filters" style="display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-bottom:24px;max-width:1200px;margin:0 auto 24px"></div>
<input id="zx-pg-search" placeholder="🔍 ابحث..." style="display:block;width:100%;max-width:520px;margin:0 auto 24px;padding:12px 18px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.15);border-radius:12px;color:#fff"/>
<div id="zx-pg-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;max-width:1200px;margin:0 auto"></div>
<script>(function(){{var SLUG=location.pathname.split('/').pop()||'';var all=[],cat='all',q='';
async function load(){{try{{var r=await fetch('/api/websites/public/'+SLUG+'/products');var d=await r.json();all=d.products||[];var cats=['all'].concat(d.categories||[]);document.getElementById('zx-pg-filters').innerHTML=cats.map(function(c){{return '<button data-c="'+c+'" style="padding:8px 16px;background:'+(c==cat?'{p}':'rgba(255,255,255,.06)')+';color:'+(c==cat?'#000':'#fff')+';border:0;border-radius:20px;font-weight:800;cursor:pointer;font-size:13px">'+(c==='all'?'الكل':c)+'</button>'}}).join('');document.querySelectorAll('#zx-pg-filters button').forEach(function(b){{b.onclick=function(){{cat=b.dataset.c;load();}}}});render();}}catch(e){{}}}}
document.getElementById('zx-pg-search').oninput=function(e){{q=e.target.value.trim().toLowerCase();render();}};
function render(){{var items=all.filter(function(p){{return (cat==='all'||p.category===cat)&&(!q||(p.name||'').toLowerCase().includes(q));}});var g=document.getElementById('zx-pg-grid');if(!items.length){{g.innerHTML='<div style="grid-column:1/-1;text-align:center;padding:40px;opacity:.6">لا منتجات</div>';return;}}g.innerHTML=items.map(function(p){{var img=p.image||'https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=400&q=60';return '<div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:16px;overflow:hidden;transition:transform .2s" onmouseover="this.style.transform=\\'translateY(-4px)\\'" onmouseout="this.style.transform=\\'\\'"><div style="aspect-ratio:1;background:#000 url('+img+') center/cover"></div><div style="padding:14px"><div style="font-weight:900;margin-bottom:4px">'+p.name+'</div>'+(p.category?'<div style="font-size:11px;opacity:.6;margin-bottom:6px">'+p.category+'</div>':'')+'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px"><span style="font-size:20px;font-weight:900;color:{p}">'+p.price+' ر.س</span>'+(p.stock<=5&&p.stock>0?'<span style="font-size:10px;color:#f59e0b">⚠️ آخر '+p.stock+'</span>':p.stock===0?'<span style="font-size:10px;color:#ef4444">نفدت</span>':'')+'</div><button '+(p.stock===0?'disabled':'')+' data-p=\\''+JSON.stringify({{id:p.id,name:p.name,price:p.price}}).replace(/\"/g,'&quot;')+'\\'  class="zx-pg-add" style="margin-top:10px;width:100%;padding:10px;background:{p};color:#000;border:0;border-radius:8px;font-weight:900;cursor:pointer;opacity:'+(p.stock===0?'.4':'1')+'">🛒 أضف للسلة</button></div></div>'}}).join('');g.querySelectorAll('.zx-pg-add').forEach(function(b){{b.onclick=function(){{var pd=JSON.parse(b.dataset.p.replace(/&quot;/g,'\"'));var c=JSON.parse(localStorage.getItem('zx_cart_'+SLUG)||'[]');var ex=c.find(function(x){{return x.id===pd.id;}});if(ex)ex.qty++;else c.push(Object.assign({{qty:1}},pd));localStorage.setItem('zx_cart_'+SLUG,JSON.stringify(c));b.textContent='✓ أُضيف';setTimeout(function(){{b.textContent='🛒 أضف للسلة'}},1200);var evt=new Event('storage');window.dispatchEvent(evt);var bad=document.getElementById('zx-cart-badge');if(bad)bad.textContent=c.reduce(function(s,x){{return s+x.qty;}},0);}}}});}}
load();setInterval(load,60000);
}})();</script></section>"""


