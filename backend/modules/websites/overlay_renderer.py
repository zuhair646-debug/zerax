"""Overlay renderer — auth + commerce overlay, floating widgets."""
from typing import Dict, Any
from .renderer_helpers import _esc


def _auth_and_commerce_overlay(slug) -> str:
    """🆕 Ships a complete site-customer auth + cart + checkout overlay with geolocation.
    Only injected on PUBLIC (approved, slugged) sites.
    """
    if not slug:
        return ""
    api_prefix = "/api/websites"  # relative — browser will hit same origin
    return f"""<!-- ZX-COMMERCE-OVERLAY -->
<button id="zx-auth-fab" data-hl="extra-auth" title="حساب">👤</button>
<div id="zx-modal" class="zx-m-root" style="display:none"><div class="zx-m-box"><button id="zx-close" class="zx-m-x">×</button><div id="zx-panel"></div></div></div>
<style>
#zx-auth-fab{{position:fixed;top:16px;left:16px;z-index:95;width:46px;height:46px;border-radius:50%;background:rgba(0,0,0,.6);color:#fff;border:2px solid rgba(255,255,255,.2);cursor:pointer;font-size:20px;backdrop-filter:blur(12px);box-shadow:0 8px 24px rgba(0,0,0,.4)}}
.zx-m-root{{position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:999;display:flex;align-items:center;justify-content:center;padding:14px;backdrop-filter:blur(4px)}}
.zx-m-box{{background:#0e1128;color:#fff;border-radius:20px;width:min(500px,100%);max-height:92vh;overflow-y:auto;padding:22px;border:1px solid rgba(234,179,8,.3);font-family:Tajawal,Cairo,sans-serif;position:relative;direction:rtl}}
.zx-m-x{{position:absolute;top:10px;left:10px;background:rgba(255,255,255,.1);border:0;color:#fff;width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:18px}}
.zx-m-box h3{{margin:0 0 14px;font-size:18px;color:#eab308}}
.zx-m-box label{{font-size:11px;opacity:.7;display:block;margin-bottom:4px}}
.zx-m-box input,.zx-m-box textarea{{width:100%;box-sizing:border-box;padding:10px 12px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.15);border-radius:10px;color:#fff;font-family:inherit;font-size:14px;margin-bottom:10px}}
.zx-m-box button.zx-btn{{width:100%;padding:11px;background:linear-gradient(90deg,#eab308,#f97316);color:#000;border:0;border-radius:10px;font-weight:900;cursor:pointer;font-size:14px;margin-top:6px}}
.zx-m-box button.zx-btn-sec{{width:100%;padding:10px;background:rgba(255,255,255,.08);color:#fff;border:1px solid rgba(255,255,255,.15);border-radius:10px;font-weight:700;cursor:pointer;font-size:13px;margin-top:6px}}
.zx-tabs{{display:flex;gap:4px;background:rgba(255,255,255,.05);padding:4px;border-radius:10px;margin-bottom:14px}}
.zx-tabs button{{flex:1;padding:8px;background:transparent;border:0;color:#fff;cursor:pointer;border-radius:7px;font-size:13px;font-weight:700}}
.zx-tabs button.active{{background:#eab308;color:#000}}
.zx-cart-item{{display:flex;align-items:center;gap:8px;padding:8px 10px;background:rgba(255,255,255,.04);border-radius:10px;margin-bottom:6px;font-size:13px}}
.zx-cart-item .zx-qty{{display:flex;align-items:center;gap:4px}}
.zx-cart-item .zx-qty button{{width:24px;height:24px;background:rgba(255,255,255,.1);border:0;color:#fff;border-radius:6px;cursor:pointer;font-weight:900}}
.zx-cart-empty{{text-align:center;padding:24px;opacity:.6}}
.zx-err{{background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.3);color:#fca5a5;padding:8px 10px;border-radius:8px;font-size:12px;margin-bottom:8px}}
.zx-ok{{background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.3);color:#86efac;padding:8px 10px;border-radius:8px;font-size:12px;margin-bottom:8px}}
.zx-loc-btn{{width:100%;padding:9px;background:rgba(59,130,246,.15);border:1px solid rgba(59,130,246,.3);color:#93c5fd;border-radius:10px;font-weight:700;cursor:pointer;font-size:12.5px;margin-bottom:8px}}
.zx-order-row{{padding:10px;background:rgba(255,255,255,.04);border-radius:10px;margin-bottom:6px;font-size:12.5px}}
.zx-pill{{font-size:10px;padding:2px 8px;border-radius:99px;font-weight:900;display:inline-block}}
.zx-pill-pending{{background:rgba(234,179,8,.2);color:#fde047}}
.zx-pill-on_the_way{{background:rgba(59,130,246,.2);color:#93c5fd}}
.zx-pill-delivered{{background:rgba(34,197,94,.2);color:#86efac}}
.zx-pill-cancelled{{background:rgba(239,68,68,.2);color:#fca5a5}}
</style>
<script>
(function(){{
  var SLUG="{slug}",API="{api_prefix}";
  var TK_KEY="zx_site_tk_"+SLUG,CART_KEY="zx_cart_"+SLUG;
  var $=function(s){{return document.querySelector(s);}};
  function tk(){{return localStorage.getItem(TK_KEY)||"";}}
  function setTk(t){{if(t)localStorage.setItem(TK_KEY,t);else localStorage.removeItem(TK_KEY);}}
  function cart(){{try{{return JSON.parse(localStorage.getItem(CART_KEY)||"[]")}}catch(e){{return []}}}}
  function setCart(c){{localStorage.setItem(CART_KEY,JSON.stringify(c));updCartBadge();}}
  function updCartBadge(){{var b=$(".zx-cart-count");if(!b)return;var n=cart().reduce(function(a,i){{return a+i.qty}},0);b.textContent=n;b.style.display=n>0?"flex":"none";}}
  async function api(p,opt){{opt=opt||{{}};opt.headers=opt.headers||{{}};opt.headers["Content-Type"]="application/json";if(tk())opt.headers["Authorization"]="SiteToken "+tk();var r=await fetch(API+p,opt);var d=await r.json().catch(function(){{return{{}}}});if(!r.ok)throw new Error(d.detail||"فشل");return d;}}
  function open_(html){{$("#zx-panel").innerHTML=html;$("#zx-modal").style.display="flex";}}
  function close_(){{$("#zx-modal").style.display="none";}}
  $("#zx-close").onclick=close_;
  $("#zx-modal").onclick=function(e){{if(e.target.id==="zx-modal")close_();}};

  // --- Cart behavior: any .zx-add-to-cart[data-name][data-price] or menu items/product cards auto-wire
  function scanAddButtons(){{
    document.querySelectorAll("[data-menu-item],[data-product-item]").forEach(function(el){{
      if(el.__zxWired)return;el.__zxWired=1;
      var name=el.getAttribute("data-name")||el.querySelector(".menu-name,.product-name,h3,h4")&&(el.querySelector(".menu-name,.product-name,h3,h4").textContent||"").trim();
      var price=parseFloat(el.getAttribute("data-price")||(el.querySelector(".menu-price,.product-price")&&el.querySelector(".menu-price,.product-price").textContent.replace(/[^0-9.]/g,""))||"0");
      var btn=document.createElement("button");btn.className="zx-btn";btn.style.marginTop="6px";btn.style.padding="6px 12px";btn.style.fontSize="12px";btn.textContent="+ أضف للسلة";
      btn.onclick=function(e){{e.stopPropagation();addToCart({{name:name,price:price}});}};
      el.appendChild(btn);
    }});
  }}
  function addToCart(item){{
    if(!tk()){{open_(renderAuth("login"));toastInPanel("سجّل دخولك أولاً لإتمام الطلب");return;}}
    var c=cart();var ex=c.find(function(x){{return x.name===item.name}});
    if(ex)ex.qty++;else c.push({{name:item.name,price:item.price,qty:1}});setCart(c);
    toast("✓ أُضيف للسلة: "+item.name);
  }}
  // Cart-float click -> open cart
  document.addEventListener("click",function(e){{
    var cf=e.target.closest(".zx-cart-float");if(cf){{e.preventDefault();openCart();}}
  }});
  function toast(msg){{var t=document.createElement("div");t.textContent=msg;t.style.cssText="position:fixed;top:70px;left:50%;transform:translateX(-50%);background:#16a34a;color:#fff;padding:8px 16px;border-radius:99px;font-size:12px;font-weight:700;z-index:1000;box-shadow:0 10px 30px rgba(0,0,0,.4)";document.body.appendChild(t);setTimeout(function(){{t.remove()}},1800);}}
  function toastInPanel(msg){{var d=document.createElement("div");d.className="zx-ok";d.textContent=msg;var p=$("#zx-panel");if(p)p.insertBefore(d,p.firstChild);}}
  function openCart(){{var c=cart();if(!c.length){{open_('<h3>🛒 سلة التسوق</h3><div class="zx-cart-empty">السلة فارغة<br><span style="font-size:11px">أضف منتجات أولاً</span></div>');return;}}
    var sub=c.reduce(function(a,i){{return a+(i.price*i.qty)}},0);
    var rows=c.map(function(i,idx){{return '<div class="zx-cart-item"><div style="flex:1">'+i.name+' <span style="opacity:.6">· '+i.price+' ر.س</span></div><div class="zx-qty"><button onclick="window.zxMinus('+idx+')">−</button><span>'+i.qty+'</span><button onclick="window.zxPlus('+idx+')">+</button></div><button onclick="window.zxRemove('+idx+')" style="background:none;color:#ef4444;border:0;cursor:pointer;font-size:16px">🗑</button></div>'}}).join("");
    open_('<h3>🛒 سلة التسوق</h3>'+rows+'<div style="padding:10px;text-align:left;font-weight:900;color:#eab308">الإجمالي: '+sub.toFixed(2)+' ر.س</div><button class="zx-btn" onclick="window.zxCheckout()">🏁 إتمام الطلب</button>');
  }}
  window.zxPlus=function(i){{var c=cart();c[i].qty++;setCart(c);openCart();}};
  window.zxMinus=function(i){{var c=cart();if(c[i].qty>1)c[i].qty--;else c.splice(i,1);setCart(c);openCart();}};
  window.zxRemove=function(i){{var c=cart();c.splice(i,1);setCart(c);openCart();}};
  window.zxCheckout=function(){{
    if(!tk()){{open_(renderAuth("login"));return;}}
    var gws=(window.__zxPayGateways||[]);
    var payOpts=gws.length? gws.map(function(g){{return '<option value="'+g.id+'">'+g.name_ar+'</option>'}}).join("") : '<option value="cod">💵 الدفع عند الاستلام</option>';
    var sub=cart().reduce(function(a,i){{return a+(i.price*i.qty)}},0);
    window.__zxSub=sub;window.__zxShip=null;
    open_('<h3>🏁 إتمام الطلب</h3>'+
      '<label>عنوان التوصيل</label><input id="zx-ord-addr" placeholder="مثال: الرياض، حي النزهة، شارع..." />'+
      '<button class="zx-loc-btn" onclick="window.zxGetLoc()">📍 استخدم موقعي الحالي</button>'+
      '<div id="zx-ord-loc" style="font-size:11px;opacity:.7;margin-bottom:8px"></div>'+
      '<div style="display:flex;gap:8px"><div style="flex:1"><label>المدينة</label><input id="zx-ord-city" placeholder="مثال: الرياض" /></div><div style="width:120px"><label>الدولة</label>'+
      '<select id="zx-ord-country" style="width:100%;padding:10px 12px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.15);border-radius:10px;color:#fff;font-family:inherit;font-size:14px;margin-bottom:10px"><option value="SA">🇸🇦 السعودية</option><option value="AE">🇦🇪 الإمارات</option><option value="KW">🇰🇼 الكويت</option><option value="BH">🇧🇭 البحرين</option><option value="OM">🇴🇲 عُمان</option><option value="QA">🇶🇦 قطر</option><option value="EG">🇪🇬 مصر</option><option value="JO">🇯🇴 الأردن</option><option value="INTL">🌍 دولة أخرى</option></select></div></div>'+
      '<label>🚚 خيارات الشحن</label>'+
      '<div id="zx-ord-ship" style="display:flex;flex-direction:column;gap:6px;margin-bottom:10px"><div style="opacity:.6;font-size:12px;padding:10px;text-align:center;background:rgba(255,255,255,.04);border-radius:10px">أدخل المدينة لعرض خيارات الشحن</div></div>'+
      '<div id="zx-ord-pickup-info" style="display:none;margin-bottom:10px"></div>'+
      '<div id="zx-ord-ins" style="display:none;padding:10px;background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.25);border-radius:10px;margin-bottom:10px"><label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="checkbox" id="zx-ord-ins-cb" onchange="window.zxRefreshTotals&&window.zxRefreshTotals()" style="accent-color:#3b82f6;margin:0"/><span style="font-size:13px"><b>🛡️ تأمين الشحنة</b> <span id="zx-ord-ins-amt" style="opacity:.85"></span><div style="font-size:11px;opacity:.65">استبدال أو إعادة المبلغ كاملاً عند تلف/فقدان الشحنة.</div></span></label></div>'+
      '<label>ملاحظات (اختياري)</label><textarea id="zx-ord-note" rows="2" placeholder="مثال: بدون بصل"></textarea>'+
      '<label>💳 طريقة الدفع</label><select id="zx-ord-pay" onchange="window.zxRefreshTotals&&window.zxRefreshTotals()">'+payOpts+'</select>'+
      '<div id="zx-ord-totals" style="margin:10px 0;padding:10px;background:rgba(234,179,8,.08);border:1px solid rgba(234,179,8,.2);border-radius:10px;font-size:13px"><div style="display:flex;justify-content:space-between"><span>المنتجات</span><b id="zx-tot-sub">'+sub.toFixed(2)+' ر.س</b></div><div style="display:flex;justify-content:space-between;margin-top:4px"><span>الشحن</span><b id="zx-tot-ship">—</b></div><div id="zx-tot-ins-row" style="display:none;justify-content:space-between;margin-top:4px"><span>🛡️ التأمين</span><b id="zx-tot-ins">—</b></div><div style="display:flex;justify-content:space-between;margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,.1);font-size:15px;color:#eab308"><span>الإجمالي</span><b id="zx-tot-total">'+sub.toFixed(2)+' ر.س</b></div></div>'+
      '<div id="zx-ord-err"></div>'+
      '<button class="zx-btn" onclick="window.zxSubmitOrder()">✓ تأكيد الطلب</button>');
    // 🆕 Wire up city/country auto-quote
    var cityEl=$("#zx-ord-city"),countryEl=$("#zx-ord-country");
    var deb=null;
    function trigQuote(){{clearTimeout(deb);deb=setTimeout(window.zxLoadShipping,400);}}
    if(cityEl)cityEl.oninput=trigQuote;
    if(countryEl)countryEl.onchange=trigQuote;
    // initial geo-detect (calls API with empty city/country to get IP-based)
    window.zxLoadShipping();
  }};
  window.zxLoadShipping=async function(){{
    var box=$("#zx-ord-ship");if(!box)return;
    var city=($("#zx-ord-city")||{{}}).value||"";
    var country=($("#zx-ord-country")||{{}}).value||"";
    box.innerHTML='<div style="opacity:.7;font-size:12px;padding:10px;text-align:center">⏳ جاري جلب خيارات الشحن...</div>';
    try{{
      var r=await fetch(API+"/public/"+SLUG+"/shipping/quote",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{city:city,country:country,cart_subtotal:window.__zxSub||0,weight_kg:1}})}});
      var d=await r.json();
      window.__zxCodMarkup=d.cod_markup_enabled?(parseFloat(d.cod_markup_sar)||0):0;
      // 🆕 Insurance config
      window.__zxInsEnabled=!!d.insurance_enabled;
      window.__zxInsPct=parseFloat(d.insurance_percent)||2;
      window.__zxInsMin=parseFloat(d.insurance_min_sar)||10;
      var insBox=$("#zx-ord-ins");
      if(insBox){{
        if(window.__zxInsEnabled){{
          var sub=window.__zxSub||0;var ifee=Math.max(window.__zxInsMin,Math.round(sub*window.__zxInsPct)/100*100/100); 
          ifee=Math.max(window.__zxInsMin,Math.round(sub*window.__zxInsPct/100*100)/100);
          var amt=$("#zx-ord-ins-amt");if(amt)amt.textContent='(+'+ifee.toFixed(2)+' ر.س)';
          insBox.style.display='block';
        }}else{{insBox.style.display='none';}}
      }}
      if(!d.options||!d.options.length){{box.innerHTML='<div style="opacity:.7;font-size:12px;padding:10px;text-align:center;background:rgba(239,68,68,.08);border-radius:10px">⚠️ لا تتوفر خيارات شحن لموقعك. تحقّق من المدينة/الدولة.</div>';return;}}
      // Auto-fill detected city if empty
      if(!city&&d.city){{var ce=$("#zx-ord-city");if(ce)ce.value=d.city;}}
      if(!country&&d.country){{var co=$("#zx-ord-country");if(co)co.value=d.country;}}
      box.innerHTML=d.options.map(function(o,idx){{
        var lbl=o.is_free?'<span style="color:#22c55e;font-weight:900">مجاني</span>':'<b style="color:#eab308">'+o.fee_sar+' ر.س</b>';
        var rec=o.is_recommended?'<span style="font-size:9px;background:#22c55e;color:#000;padding:1px 6px;border-radius:99px;font-weight:900;margin-right:4px">⭐ موصى به</span>':'';
        var codHint=(window.__zxCodMarkup>0&&o.supports_cod)?'<span style="font-size:9px;background:rgba(234,179,8,.18);color:#fde047;padding:1px 6px;border-radius:99px;margin-right:4px">+'+window.__zxCodMarkup+' عند COD</span>':'';
        return '<label style="display:flex;align-items:center;gap:10px;padding:10px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:10px;cursor:pointer"><input type="radio" name="zx-ship" value="'+idx+'" '+(idx===0?"checked":"")+' onchange="window.zxPickShip('+idx+')" style="margin:0;accent-color:#eab308"/><span style="font-size:18px">'+(o.icon||"📦")+'</span><div style="flex:1"><div style="font-weight:900;font-size:13px">'+o.provider_name+rec+codHint+'</div><div style="font-size:11px;opacity:.65">'+o.delivery_eta+(o.supports_cod?' · يدعم COD':'')+'</div></div><div>'+lbl+'</div></label>';
      }}).join("");
      window.__zxShipOpts=d.options;window.zxPickShip(0);
    }}catch(e){{box.innerHTML='<div style="font-size:12px;padding:10px;background:rgba(239,68,68,.08);color:#fca5a5;border-radius:10px">'+(e.message||"تعذّر جلب خيارات الشحن")+'</div>';}}
  }};
  window.zxPickShip=function(idx){{
    var opt=(window.__zxShipOpts||[])[idx];if(!opt)return;
    window.__zxShip=opt;window.__zxShipIdx=idx;
    var sub=window.__zxSub||0;var fee=opt.fee_sar||0;
    var pay=($("#zx-ord-pay")||{{}}).value||"cod";
    var markup=(pay==="cod"&&opt.supports_cod&&!opt.is_free)?(window.__zxCodMarkup||0):0;
    var totalFee=fee+markup;
    var st=$("#zx-tot-ship");if(st)st.textContent=opt.is_free?"مجاني":(totalFee+" ر.س"+(markup>0?" (شامل +"+markup+" COD)":""));
    // 🆕 Insurance
    var insOpted=!!(($("#zx-ord-ins-cb")||{{}}).checked) && !!window.__zxInsEnabled;
    var insFee=0;
    if(insOpted){{insFee=Math.max(window.__zxInsMin||10,Math.round(sub*(window.__zxInsPct||2)/100*100)/100);}}
    var insRow=$("#zx-tot-ins-row"),insV=$("#zx-tot-ins");
    if(insRow)insRow.style.display=insOpted?"flex":"none";
    if(insV)insV.textContent=insFee?(insFee.toFixed(2)+" ر.س"):"—";
    var tt=$("#zx-tot-total");if(tt)tt.textContent=(sub+totalFee+insFee).toFixed(2)+" ر.س";
    // 🆕 Pickup address hint
    var pkBox=$("#zx-ord-pickup-info");
    if(pkBox){{
      if(opt.provider_id==="pickup"){{
        pkBox.style.display="block";
        pkBox.innerHTML='<div style="padding:10px;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.25);border-radius:10px;font-size:12px"><b>🏬 الاستلام من المتجر</b><br><span style="opacity:.85">'+(opt.pickup_address||"اتصل بنا لمعرفة العنوان")+'</span>'+(opt.delivery_eta?'<div style="font-size:11px;opacity:.7;margin-top:4px">⏱️ '+opt.delivery_eta+'</div>':'')+'</div>';
      }}else{{pkBox.style.display="none";pkBox.innerHTML="";}}
    }}
  }};
  window.zxRefreshTotals=function(){{
    if(typeof window.__zxShipIdx==="number")window.zxPickShip(window.__zxShipIdx);
  }};
  window.zxGetLoc=function(){{
    if(!navigator.geolocation){{$("#zx-ord-loc").textContent="متصفحك لا يدعم تحديد الموقع";return;}}
    $("#zx-ord-loc").textContent="جاري تحديد موقعك...";
    navigator.geolocation.getCurrentPosition(function(pos){{
      window.__zxLat=pos.coords.latitude;window.__zxLng=pos.coords.longitude;
      $("#zx-ord-loc").textContent="✓ تم تحديد موقعك ("+pos.coords.latitude.toFixed(4)+", "+pos.coords.longitude.toFixed(4)+")";
    }},function(){{$("#zx-ord-loc").textContent="⚠️ لم نتمكن من تحديد موقعك — اكتب العنوان يدوياً";}});
  }};
  window.zxSubmitOrder=async function(){{
    var addr=$("#zx-ord-addr").value.trim();var note=$("#zx-ord-note").value.trim();
    var pay=($("#zx-ord-pay")||{{}}).value||"cod";
    var pts=parseInt(($("#zx-ord-pts")||{{}}).value||"0")||0;
    var city=($("#zx-ord-city")||{{}}).value||"";
    var country=($("#zx-ord-country")||{{}}).value||"";
    var ship=window.__zxShip||{{}};
    var insOpted=!!(($("#zx-ord-ins-cb")||{{}}).checked);
    if(!addr&&!window.__zxLat){{$("#zx-ord-err").innerHTML='<div class="zx-err">أدخل عنواناً أو استخدم موقعك</div>';return;}}
    if(!ship.provider_id){{$("#zx-ord-err").innerHTML='<div class="zx-err">اختر طريقة شحن</div>';return;}}
    try{{
      var res=await api("/public/"+SLUG+"/orders",{{method:"POST",body:JSON.stringify({{items:cart(),address:addr,lat:window.__zxLat,lng:window.__zxLng,note:note,coupon_code:window.__zxCoupon||"",redeem_points:pts,payment_method:pay,city:city,country:country,shipping_provider:ship.provider_id,shipping_provider_name:ship.provider_name,shipping_fee:ship.fee_sar,shipping_eta:ship.delivery_eta,insurance_opted:insOpted}})}});
      setCart([]);window.__zxCoupon=null;
      // If the chosen provider is a hosted gateway, redirect to payment page
      if(pay && pay!=="cod"){{
        try{{
          var init=await api("/public/"+SLUG+"/payments/init",{{method:"POST",body:JSON.stringify({{order_id:res.order_id,provider:pay}})}});
          if(init && init.redirect_url){{window.location.href=init.redirect_url;return;}}
        }}catch(pe){{$("#zx-ord-err").innerHTML='<div class="zx-err">تم استلام طلبك ولكن تعذّر بدء الدفع: '+pe.message+'</div>';}}
      }}
      var extra=res.points_earned?'<br>🎁 كسبت '+res.points_earned+' نقطة (رصيدك '+res.points_balance+')':'';
      open_('<h3>✅ تم استلام طلبك</h3><div class="zx-ok">رقم الطلب: '+res.order_id.slice(0,8)+'<br>الإجمالي: '+res.total+' ر.س'+(res.discount?'<br>🎁 وفّرت '+res.discount+' ر.س':'')+extra+'</div><button class="zx-btn-sec" onclick="window.zxMyOrders()">📦 تتبّع طلباتي</button>');
    }}catch(e){{$("#zx-ord-err").innerHTML='<div class="zx-err">'+e.message+'</div>';}}
  }};
  window.zxMyOrders=async function(){{
    try{{var d=await api("/public/"+SLUG+"/orders/my");
    if(!d.orders.length){{open_('<h3>📦 طلباتي</h3><div class="zx-cart-empty">لا طلبات بعد</div>');return;}}
    var rows=d.orders.map(function(o){{
      var trk=o.tracking_url?'<a href="'+o.tracking_url+'" target="_blank" rel="noopener" style="display:inline-block;margin-top:6px;padding:5px 10px;background:rgba(59,130,246,.15);border:1px solid rgba(59,130,246,.35);color:#93c5fd;border-radius:8px;font-size:11px;font-weight:800;text-decoration:none">📍 تتبّع الشحنة'+(o.tracking_number?' #'+String(o.tracking_number).slice(0,12):"")+'</a>':'';
      var ship=o.shipping_provider_name?'<div style="font-size:10.5px;opacity:.55;margin-top:2px">🚚 '+o.shipping_provider_name+(o.shipping_eta?' · '+o.shipping_eta:'')+'</div>':'';
      return '<div class="zx-order-row"><div style="display:flex;justify-content:space-between"><b>#'+o.id.slice(0,8)+'</b><span class="zx-pill zx-pill-'+o.status+'">'+statusLabel(o.status)+'</span></div><div style="opacity:.7;margin-top:4px">'+o.items.length+' صنف · '+o.total+' ر.س</div>'+ship+'<div style="opacity:.5;font-size:11px;margin-top:2px">'+new Date(o.at).toLocaleString("ar-SA")+'</div>'+trk+'</div>';
    }}).join("");
    open_('<h3>📦 طلباتي</h3>'+rows);}}catch(e){{open_('<h3>📦 طلباتي</h3><div class="zx-err">'+e.message+'</div>');}}
  }};
  function statusLabel(s){{return({{pending:"قيد المراجعة",accepted:"مقبول",preparing:"قيد التحضير",ready:"جاهز",on_the_way:"في الطريق",delivered:"تم التوصيل",cancelled:"ملغي"}})[s]||s;}}

  // --- Auth rendering
  function renderAuth(tab){{
    var isReg=tab==="register";
    return '<h3>'+(isReg?"✨ إنشاء حساب":"👤 تسجيل الدخول")+'</h3>'+
      '<div class="zx-tabs"><button class="'+(isReg?"":"active")+'" onclick="window.zxTab(\\'login\\')">دخول</button><button class="'+(isReg?"active":"")+'" onclick="window.zxTab(\\'register\\')">حساب جديد</button></div>'+
      (isReg?'<label>الاسم</label><input id="zx-au-name" />':"")+
      '<label>رقم الجوال</label><input id="zx-au-phone" placeholder="05xxxxxxxx" />'+
      (isReg?'<label>البريد (اختياري)</label><input id="zx-au-email" />':"")+
      '<label>كلمة المرور</label><input id="zx-au-pwd" type="password" />'+
      '<div id="zx-au-err"></div>'+
      '<button class="zx-btn" onclick="window.zxAuthDo(\\''+(isReg?"register":"login")+'\\')">'+(isReg?"إنشاء":"دخول")+'</button>';
  }}
  window.zxTab=function(t){{open_(renderAuth(t));}};
  window.zxAuthDo=async function(mode){{
    try{{
      var body={{phone:$("#zx-au-phone").value.trim(),password:$("#zx-au-pwd").value}};
      if(mode==="register"){{body.name=$("#zx-au-name").value.trim();body.email=($("#zx-au-email")||{{}}).value||"";}}
      var d=await api("/public/"+SLUG+"/auth/"+mode,{{method:"POST",body:JSON.stringify(body)}});
      setTk(d.token);close_();toast("مرحباً "+d.customer.name);updAuthBadge();
      if(cart().length)openCart();
    }}catch(e){{$("#zx-au-err").innerHTML='<div class="zx-err">'+e.message+'</div>';}}
  }};
  function updAuthBadge(){{var b=$("#zx-auth-fab");b.textContent=tk()?"✓":"👤";b.style.background=tk()?"linear-gradient(135deg,#eab308,#f97316)":"rgba(0,0,0,.6)";b.style.color=tk()?"#000":"#fff";}}
  $("#zx-auth-fab").onclick=function(){{
    if(tk()){{open_('<h3>👤 حسابي</h3><button class="zx-btn-sec" onclick="window.zxMyOrders()">📦 طلباتي</button><button class="zx-btn-sec" onclick="window.zxLogout()">🚪 تسجيل خروج</button>');}}
    else{{open_(renderAuth("login"));}}
  }};
  window.zxLogout=function(){{setTk("");updAuthBadge();close_();toast("تم تسجيل الخروج");}};

  // init
  scanAddButtons();updCartBadge();updAuthBadge();
  setTimeout(scanAddButtons,500);
  new MutationObserver(scanAddButtons).observe(document.body,{{childList:true,subtree:true}});
  // Load available payment gateways for this site
  (async function(){{try{{var pg=await api("/public/"+SLUG+"/payment-gateways");window.__zxPayGateways=(pg&&pg.gateways)||[];}}catch(_e){{window.__zxPayGateways=[];}}}})();
}})();
</script>
<!-- /ZX-COMMERCE-OVERLAY -->"""



def _floating_widgets(theme: Dict[str, Any]) -> str:
    extras = theme.get("extras", []) or []
    html = ""
    if "announce_bar" in extras:
        html += '<div class="zx-announce">🎉 عرض محدود: خصم 20% على أول طلب — استخدم كوبون WELCOME20</div>'
    if "sticky_phone" in extras:
        html += '<a href="tel:+966500000000" class="zx-sticky-phone" data-hl="extra-phone">📞 اتصل: 0500000000</a>'
    if "whatsapp_float" in extras:
        html += '<a href="https://wa.me/966500000000" class="zx-whatsapp" data-hl="extra-whatsapp" target="_blank">💬</a>'
    if "scroll_top" in extras:
        html += '<button class="zx-scroll-top" onclick="window.scrollTo({top:0,behavior:\'smooth\'})" data-hl="extra-scroll">⬆</button>'
    if "countdown" in extras:
        html += '<div class="zx-countdown" data-hl="extra-countdown">⏰ ينتهي العرض خلال: <span class="zx-cd-val">23:45:12</span></div>'
    if "rating_widget" in extras:
        html += '<div class="zx-rating" data-hl="extra-rating"><span class="zx-stars">★★★★★</span><div class="zx-rtx">4.9 من 5 · 2,450 تقييم</div></div>'
    if "social_bar" in extras:
        html += '<div class="zx-social" data-hl="extra-social"><a>📘</a><a>📸</a><a>🐦</a><a>🎬</a></div>'
    if "trust_badges" in extras:
        html += '<div class="zx-trust" data-hl="extra-trust"><span>🔒 دفع آمن</span><span>✅ ضمان جودة</span><span>🚚 توصيل سريع</span><span>💳 فيزا/مدى</span></div>'
    if "live_chat" in extras:
        html += '<div class="zx-chat" data-hl="extra-chat"><div class="zx-chat-head">💬 محادثة فورية</div><div class="zx-chat-body">أهلاً! كيف يمكننا مساعدتك؟</div></div>'
    if "cart_float" in extras:
        html += '<button class="zx-cart-float" data-hl="extra-cart" title="عربة التسوق">🛒<span class="zx-cart-count">3</span></button>'
    if "book_float" in extras:
        html += '<button class="zx-book-float" data-hl="extra-book" title="احجز موعد">📅 احجز موعد</button>'
    return html


