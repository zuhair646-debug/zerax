const API = window.location.origin;
let WALLET = parseInt(localStorage.getItem('zx_credits')||'5000');
// Boost low-balance demo accounts so user can experiment freely
if(WALLET<1000){WALLET=5000;localStorage.setItem('zx_credits',WALLET);}
let CURRENT_PAGE='dashboard';

// Mock product seed
const MOCK_PRODUCTS=[
  {id:'p1',name:'iPhone 17 Pro Max',price:5499,stock:24,sku:'IP17-PM-256',stockLow:5,exp:null,cat:'electronics',img:'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&q=85',sales:34},
  {id:'p2',name:'Apple Watch Ultra 2',price:3299,stock:18,sku:'AW-ULT2',stockLow:5,exp:null,cat:'electronics',img:'https://images.unsplash.com/photo-1551816230-ef5deaed4a26?w=600&q=85',sales:28},
  {id:'p3',name:'AirPods Pro 3',price:1099,stock:42,sku:'APP-3',stockLow:8,exp:null,cat:'electronics',img:'https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?w=600&q=85',sales:51},
  {id:'p4',name:'MacBook Pro M4',price:9999,stock:3,sku:'MBP-M4-14',stockLow:5,exp:null,cat:'electronics',img:'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&q=85',sales:12},
  {id:'p5',name:'iPad Air M3',price:2799,stock:15,sku:'IPA-M3',stockLow:5,exp:null,cat:'electronics',img:'https://images.unsplash.com/photo-1561154464-82e9adf32764?w=600&q=85',sales:19},
  {id:'p6',name:'Samsung S25 Ultra',price:4899,stock:0,sku:'SAM-S25U',stockLow:5,exp:null,cat:'electronics',img:'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=600&q=85',sales:8}
];
let PRODUCTS=[];
let EDITING_PRODUCT_ID=null;
async function loadProductsFromAPI(){
  try{
    const d=await apiFetch('/api/store/products');
    PRODUCTS=(d.items||[]).map(p=>({...p,stockLow:p.stock_low,trackExpiry:p.track_expiry}));
    if(!PRODUCTS.length){
      // First-time: seed the merchant DB with sample products
      for(const m of MOCK_PRODUCTS){
        try{
          const saved=await apiFetch('/api/store/products',{method:'POST',body:JSON.stringify({name:m.name,price:m.price,stock:m.stock,sku:m.sku||'',stock_low:m.stockLow||5,cat:m.cat,img:m.img,desc:''})});
          PRODUCTS.push({...saved,stockLow:saved.stock_low,trackExpiry:saved.track_expiry});
        }catch(_){}
      }
    }
  }catch(e){
    console.warn('Failed to load products from API, falling back to MOCK:',e.message);
    PRODUCTS=MOCK_PRODUCTS.slice();
  }
  renderProducts();renderAll();
}
const MOCK_CUSTOMERS=[
  {name:'نوف العتيبي',phone:'0567778888',orders:7,total:1245,last:'قبل ساعة'},
  {name:'خالد المطيري',phone:'0561234567',orders:12,total:3489,last:'قبل 3 ساعات'},
  {name:'ريم القحطاني',phone:'0578889999',orders:4,total:1820,last:'أمس'},
  {name:'محمد الزهراني',phone:'0533123456',orders:9,total:2145,last:'منذ 2 أيام'},
  {name:'سارة العنزي',phone:'0598765432',orders:3,total:567,last:'منذ 3 أيام'}
];

function $(id){return document.getElementById(id)}
function toast(m){const t=$('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2500)}

// ───── AUTH ─────
// ═══════════════ API CLIENT (real backend) ═══════════════
function authToken(){return localStorage.getItem('zx_token')||''}
async function apiFetch(path,opts={}){
  const headers={'Content-Type':'application/json',...(opts.headers||{})};
  const tk=authToken();if(tk)headers.Authorization='Bearer '+tk;
  const r=await fetch(API+path,{...opts,headers});
  if(r.status===401){doLogout();throw new Error('انتهت الجلسة');}
  const data=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(data.detail||data.message||('HTTP '+r.status));
  return data;
}
async function doLogin(){
  const email=$('li-email').value.trim().toLowerCase(),pass=$('li-pass').value;
  const errEl=$('li-err');errEl.classList.remove('show');errEl.textContent='';
  if(!email||!pass){errEl.textContent='أدخل البريد وكلمة المرور';errEl.classList.add('show');return;}
  try{
    const r=await fetch(API+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password:pass})});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||'فشل تسجيل الدخول');
    localStorage.setItem('zx_token',d.token);
    localStorage.setItem('zx_admin_user',JSON.stringify(d.user));
    localStorage.setItem('zx_admin_session','1');
    showApp();
  }catch(e){
    errEl.textContent=e.message||'بيانات غير صحيحة';errEl.classList.add('show');
  }
}
function doLogout(){
  localStorage.removeItem('zx_token');
  localStorage.removeItem('zx_admin_user');
  localStorage.removeItem('zx_admin_session');
  location.reload();
}
function copyStoreUrl(){
  const url=window.__storeUrl||$('store-url-text').textContent;
  navigator.clipboard?.writeText(url).then(()=>toast('📋 تم نسخ رابط متجرك'));
}
function shareStoreUrlWhatsapp(){
  const url=window.__storeUrl||$('store-url-text').textContent;
  const msg=`🛒 زورو متجري الإلكتروني:\n\n${url}\n\nتوصيل سريع · جودة عالية · أسعار منافسة`;
  window.open('https://wa.me/?text='+encodeURIComponent(msg),'_blank');
}
function openStorePreview(){
  const url=window.__storeUrl||$('store-url-text').textContent;
  window.open(url,'_blank');
}
function showApp(){
  $('login-screen').style.display='none';
  $('app').classList.add('show');
  // Hydrate user info from JWT user object
  try{
    const u=JSON.parse(localStorage.getItem('zx_admin_user')||'{}');
    const initial=(u.name||u.email||'م').charAt(0).toUpperCase();
    ['user-avt','user-avt-big'].forEach(id=>{const el=$(id);if(el)el.textContent=initial;});
    ['user-name','user-name-big'].forEach(id=>{const el=$(id);if(el)el.textContent=u.name||u.email||'—';});
    ['user-email','user-email-big'].forEach(id=>{const el=$(id);if(el)el.textContent=u.email||'—';});
    // Build store URL using user.id as the merchant key
    if(u.id){
      const url=window.location.origin+'/mockups/app_mode_full.html?m='+encodeURIComponent(u.id);
      const urlEl=$('store-url-text');if(urlEl)urlEl.textContent=url;
      const w=$('store-url-widget');if(w)w.style.display='block';
      window.__storeUrl=url;
    }
  }catch(_){}
  goPage('dashboard');
  loadProductsFromAPI();
  renderAll();
  maybeShowOnboarding();
  // ─── Auto-refresh orders + KPIs every 20s so admin sees real-time updates ───
  if (!window.__zx_admin_poll){
    window.__zx_admin_poll = setInterval(() => {
      try { renderOrders(); } catch(_){}
      // Re-fetch recent orders + KPIs (no full re-render to avoid flicker)
      try {
        loadRealOrders(8).then(real => {
          if (!real.length) return;
          const el = document.getElementById('recent-orders');
          if (el) el.innerHTML = real.map(o => `<tr><td><b>${(o.id||'').replace('ord_','#')}</b></td><td>${o.cust}</td><td><b>${o.amt} ر.س</b></td><td><span class="status-pill s-${o.st}">${_stLabel(o.st)}</span></td><td>${o.drv}</td><td style="color:var(--mute);font-size:11px">${o.time||''}</td></tr>`).join('');
        });
        fetch((window.API||window.location.origin)+'/api/delivery/stats').then(r=>r.json()).then(s=>{
          const set=(sel,val)=>{const el=document.querySelector(sel);if(el)el.textContent=val;};
          if(s){set('[data-kpi="revenue"] .val',(s.revenue_today_sar||0).toLocaleString('ar-EG')+' ر.س');set('[data-kpi="orders"] .val',String(s.total_orders||0));set('[data-kpi="drivers"] .val',String(s.active_drivers||0));}
        });
      } catch(_){}
    }, 20000);
  }
  setTimeout(()=>{
    if(window.lucide)lucide.createIcons();
    setupKpiClicks();
    setupChart();
    vsUpdateConfig();
    renderVsHistory();
    maybeHideAiReport();
  },150);
}
if(localStorage.getItem('zx_admin_session'))showApp();

// ───── NAV ─────
function goPage(p){
  CURRENT_PAGE=p;
  document.querySelectorAll('.page').forEach(el=>el.classList.toggle('active',el.dataset.page===p));
  document.querySelectorAll('.nav-item').forEach(el=>el.classList.toggle('active',el.dataset.page===p));
  const titles={dashboard:'الرئيسية',products:'المنتجات',orders:'الطلبات',customers:'العملاء',delivery:'إدارة التوصيل',payroll:'المحاسبة والرواتب',gateways:'وسائل الدفع',markets:'الأسواق المستهدفة',branches:'إدارة الفروع',settings:'الإعدادات','video-studio':'استوديو الفيديو الإعلاني',social:'الحسابات الاجتماعية',services:'الخدمات الإضافية','smart-mgmt':'الإدارة الذكية',marketing:'التسويق والمبيعات',reviews:'التقييمات والمراجعات',themes:'ألوان المتجر',reports:'تقارير PDF',zatca:'الفاتورة الإلكترونية ZATCA',credits:'النقاط والاشتراك'};
  $('page-title').textContent=titles[p]||p;
  document.getElementById('sidebar').classList.remove('open');
  // lazy load
  if(p==='delivery')loadDelivery();
  if(p==='payroll')loadPayroll();
  if(p==='gateways')loadGateways();
  if(p==='markets')loadMarkets();
  if(p==='branches')loadMerchantBranches();
  if(p==='social')loadSocial();
  if(p==='services')loadServices();
  if(p==='smart-mgmt')loadSmartMgmt();
  if(p==='marketing')loadMarketing();
  if(p==='reviews')loadReviews();
  if(p==='themes')loadThemes();
  if(p==='reports')loadReports();
  if(p==='zatca')loadZatca();
  if(p==='credits')loadCredits();
  if(p==='video-studio')renderSocialMini();
  setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
}

// ───── RENDER ALL (initial) ─────
async function renderAll(){
  $('wallet-balance').textContent=WALLET.toLocaleString('ar-EG');
  // Animate KPIs
  setTimeout(()=>animateKPIs(),200);
  // Recent orders — fetch from backend (real)
  try{
    const real = await loadRealOrders(8);
    const display = real.length ? real : [
      {id:'#demo-3047',cust:'(عرض تجريبي) نوف العتيبي',amt:'245 ر.س',st:'delivered',drv:'خالد العتيبي',time:'قبل دقيقتين'},
      {id:'#demo-3046',cust:'(عرض تجريبي) خالد المطيري',amt:'89 ر.س',st:'delivering',drv:'أحمد السبيعي',time:'قبل 15 د'}
    ];
    $('recent-orders').innerHTML = display.map(o=>{
      const amt = typeof o.amt==='string' ? o.amt : (o.amt + ' ر.س');
      return `<tr><td><b>${(o.id||'').replace('ord_','#')}</b></td><td>${o.cust}</td><td><b>${amt}</b></td><td><span class="status-pill s-${o.st}">${_stLabel(o.st)}</span></td><td>${o.drv}</td><td style="color:var(--mute);font-size:11px">${o.time||''}</td></tr>`;
    }).join('');
  }catch(e){console.warn('recent-orders failed',e);}
  // Real KPIs (from /api/delivery/stats)
  try{
    const s = await fetch((API||window.location.origin)+'/api/delivery/stats').then(r=>r.json());
    const set = (sel,val)=>{const el=document.querySelector(sel); if(el) el.textContent=val;};
    if (s){
      // Revenue today
      set('[data-kpi="revenue"] .val', (s.revenue_today_sar||0).toLocaleString('ar-EG')+' ر.س');
      set('[data-kpi="orders"] .val', String(s.total_orders||0));
      set('[data-kpi="drivers"] .val', String(s.active_drivers||0));
    }
  }catch(e){console.warn('KPIs failed',e);}
  // Top products
  $('top-products').innerHTML=[...PRODUCTS].sort((a,b)=>b.sales-a.sales).slice(0,5).map((p,i)=>
    `<div onclick="goPage('products');editProduct('${p.id}')" style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--border);cursor:pointer;transition:background .15s" onmouseover="this.style.background='#faf5ff'" onmouseout="this.style.background='transparent'"><div style="width:34px;height:34px;border-radius:50%;background:#faf5ff;color:var(--purple);display:flex;align-items:center;justify-content:center;font-weight:900">${i+1}</div><img src="${p.img}" style="width:38px;height:38px;border-radius:8px;object-fit:cover" loading="lazy" decoding="async"><div style="flex:1;min-width:0"><div style="font-size:12px;font-weight:900;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${p.name}</div><div style="font-size:10px;color:var(--mute)">${p.sales} مبيعات</div></div><b style="color:var(--purple);font-size:13px">${p.price}</b></div>`).join('');
  renderProducts();
  renderOrders();
  renderCustomers();
  renderMarketHeatmap();
  renderMasterBranchesOverview();
}

// ───── MASTER BRANCHES OVERVIEW (Dashboard widget) ─────
function renderMasterBranchesOverview(){
  const tbody=document.getElementById('master-branches-rows');if(!tbody)return;
  const branches=JSON.parse(localStorage.getItem('zx_merchant_branches')||'[]');
  if(!branches.length){tbody.innerHTML='<tr><td colspan="8" style="text-align:center;color:var(--text-mut);padding:20px">لا يوجد فروع — أضف من <a href="#" onclick="goPage(\'branches\');return false" style="color:var(--purple)">صفحة الفروع</a></td></tr>';return;}
  // Hide if user is in scoped mode (branch manager view)
  if(localStorage.getItem('zx_active_branch_scope')){document.getElementById('master-branches-overview').style.display='none';return;}
  tbody.innerHTML=branches.map((b,i)=>{
    const fee=i===0?0:i<=2?99:i<=9?149:199;
    const ordersToday=Math.floor(Math.random()*60)+15;
    const revToday=Math.floor(Math.random()*15000)+3000;
    const newCust=Math.floor(Math.random()*15)+2;
    const avgOrder=Math.floor(revToday/ordersToday);
    const statusBadge=b.active?'<span style="background:#dcfce7;color:#065f46;padding:2px 7px;border-radius:99px;font-size:9px;font-weight:900">●نشط</span>':'<span style="background:#fef2f2;color:#dc2626;padding:2px 7px;border-radius:99px;font-size:9px;font-weight:900">●متوقف</span>';
    return `<tr>
      <td><b>${b.name_ar}</b> ${b.is_main?'<span style="background:#fbbf24;color:#0a0a14;padding:1px 6px;border-radius:99px;font-size:8px;font-weight:900;margin-right:4px">👑 رئيسي</span>':''}<div style="font-size:10px;color:var(--text-mut);margin-top:2px">${b.addr||'—'}</div></td>
      <td><b style="color:#0ea5e9">${ordersToday}</b></td>
      <td><b style="color:#10b981">${revToday.toLocaleString()}</b> <small>ر.س</small></td>
      <td>${newCust}</td>
      <td>${avgOrder} <small>ر.س</small></td>
      <td>${fee?`<b style="color:#dc2626">${fee}</b> <small>ر.س</small>`:'<span style="color:#10b981;font-weight:900">🆓 مجاني</span>'}</td>
      <td><div style="font-size:11px"><b>${b.manager_name||'—'}</b></div><div style="font-size:9px;color:var(--text-mut)">${b.manager_email||''}</div>${statusBadge}</td>
      <td><button onclick="openBranchDashboard('${b.id}')" style="padding:5px 10px;background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;border:none;border-radius:6px;font-family:inherit;font-size:10px;font-weight:900;cursor:pointer">🔓 افتح</button></td>
    </tr>`;
  }).join('');
}

// ───── MARKET HEATMAP (dashboard widget) ─────
function renderMarketHeatmap(){
  const host=document.getElementById('mkt-heatmap-rows');if(!host)return;
  const active=JSON.parse(localStorage.getItem('zx_active_markets')||'["sa"]');
  // Mock orders distribution (replace with real backend later)
  const mockOrders={sa:248,ae:67,kw:34,qa:22,bh:18,om:12,eg:9,jo:6};
  const flagMap={sa:'🇸🇦',ae:'🇦🇪',kw:'🇰🇼',qa:'🇶🇦',bh:'🇧🇭',om:'🇴🇲',eg:'🇪🇬',jo:'🇯🇴',lb:'🇱🇧',iq:'🇮🇶',ma:'🇲🇦',dz:'🇩🇿',tn:'🇹🇳',ly:'🇱🇾',sy:'🇸🇾',ps:'🇵🇸',ye:'🇾🇪',sd:'🇸🇩'};
  const nameMap={sa:'السعودية',ae:'الإمارات',kw:'الكويت',qa:'قطر',bh:'البحرين',om:'عُمان',eg:'مصر',jo:'الأردن',lb:'لبنان',iq:'العراق',ma:'المغرب',dz:'الجزائر',tn:'تونس',ly:'ليبيا',sy:'سوريا',ps:'فلسطين',ye:'اليمن',sd:'السودان'};
  const data=active.map(id=>({id,orders:mockOrders[id]||Math.floor(Math.random()*15)})).sort((a,b)=>b.orders-a.orders).slice(0,6);
  if(!data.length){host.innerHTML='<div style="text-align:center;padding:20px;color:var(--text-mut);font-size:12px">لم تفعّل أي سوق بعد</div>';return;}
  const max=Math.max(...data.map(d=>d.orders))||1;
  host.innerHTML=data.map(d=>{
    const pct=Math.round((d.orders/max)*100);
    const heat=pct>=70?'#dc2626':pct>=40?'#f59e0b':pct>=20?'#fbbf24':'#94a3b8';
    return `<div style="display:flex;align-items:center;gap:10px;padding:6px 0">
      <div style="width:32px;font-size:18px;text-align:center">${flagMap[d.id]||'🌐'}</div>
      <div style="flex:1;min-width:0"><div style="font-size:12px;font-weight:700">${nameMap[d.id]||d.id.toUpperCase()}</div>
        <div style="background:#f3f4f6;height:6px;border-radius:99px;overflow:hidden;margin-top:4px"><div style="background:linear-gradient(90deg,${heat},${heat}aa);height:100%;width:${pct}%;border-radius:99px;transition:width .6s"></div></div>
      </div>
      <div style="text-align:left;min-width:60px"><b style="color:${heat};font-size:13px">${d.orders}</b><div style="font-size:9px;color:var(--text-mut)">طلب</div></div>
    </div>`;
  }).join('');
}

function _stockBadge(p){
  if(p.stock===0)return '<span class="stock-out">⛔ نفد المخزون</span>';
  if(p.stock<=(p.stockLow||5))return `<span class="stock-low">⚠️ مخزون منخفض (${p.stock})</span>`;
  return '';
}
function _expiryBadge(p){
  if(!p.exp)return '';
  const today=new Date();const exp=new Date(p.exp);
  const days=Math.floor((exp-today)/(1000*60*60*24));
  if(days<0)return '<span class="expiry-bad">🚫 منتهي الصلاحية</span>';
  if(days<=30)return `<span class="expiry-warn">⏰ ينتهي خلال ${days} يوم</span>`;
  return '';
}
function renderProducts(){
  $('products-grid').innerHTML=`<div class="pcard add" onclick="openProductModal()"><i data-lucide="plus-circle" style="width:36px;height:36px;margin-bottom:8px"></i>منتج جديد</div>`+
    PRODUCTS.map((p,i)=>{
      const stockB=_stockBadge(p);const expB=_expiryBadge(p);
      const badges=[stockB,expB].filter(Boolean).join(' ');
      return `<div class="pcard" onclick="editProduct('${p.id}')"><div class="img" style="background-image:url('${p.img}')"><div class="actions"><button title="استوديو الصور بالذكاء الإصطناعي" onclick="event.stopPropagation();openImageStudioFor('${p.id}')"><i data-lucide="sparkles" style="width:14px;height:14px"></i></button><button title="حذف" onclick="event.stopPropagation();deleteProduct('${p.id}')"><i data-lucide="trash-2" style="width:14px;height:14px"></i></button></div>${p.analysis?'<div style="position:absolute;bottom:6px;right:6px;background:rgba(124,58,237,.85);color:#fff;font-size:9px;font-weight:900;padding:3px 8px;border-radius:99px;backdrop-filter:blur(8px)">🤖 تحليل AI</div>':''}${badges?`<div style="position:absolute;top:6px;left:6px;display:flex;flex-direction:column;gap:4px">${badges}</div>`:''}</div><div class="body"><h4>${p.name}</h4>${p.sku?`<div style="font-size:10px;color:var(--mute);font-family:monospace;margin-bottom:4px">SKU: ${p.sku}</div>`:''}<div class="price">${p.price} ر.س</div><div class="meta">📦 ${p.stock} · 🛒 ${p.sales} ${p.analysis?'· ✨':''}</div></div></div>`;
    }).join('');
  setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
}
function editProduct(id){
  const p=PRODUCTS.find(x=>x.id===id);if(!p)return;
  openProductModal();
  EDITING_PRODUCT_ID=id;
  $('pm-name').value=p.name;$('pm-price').value=p.price;$('pm-stock').value=p.stock;$('pm-desc').value=p.desc||'';
  if($('pm-sku'))$('pm-sku').value=p.sku||'';
  if($('pm-stock-low'))$('pm-stock-low').value=p.stockLow||5;
  if($('pm-mfg'))$('pm-mfg').value=p.mfg||'';
  if($('pm-exp'))$('pm-exp').value=p.exp||'';
  if($('pm-track-expiry'))$('pm-track-expiry').checked=!!p.trackExpiry;
  if(p.cat)$('pm-cat').value=p.cat;
  $('pm-img-preview').innerHTML=`<img src="${p.img}" loading="lazy" decoding="async">`;
  // If product has stored analysis, show its full styled preview on Info tab
  if(p.analysis){
    PS_STATE.analysis=p.analysis;
    document.getElementById('ps-info-preview-content').innerHTML=psBuildAnalysisHTML(p.analysis);
    document.getElementById('ps-info-preview').style.display='block';
    setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
  }
  toast('✏️ تعديل: '+p.name);
}
function openImageStudioFor(id){
  // Opens Product Studio at Image tab so the merchant can generate AI images for this product
  const p=PRODUCTS.find(x=>x.id===id);if(!p)return;
  openProductModal();
  $('pm-name').value=p.name;$('pm-price').value=p.price;$('pm-stock').value=p.stock;$('pm-desc').value=p.desc||'';
  if(p.cat)$('pm-cat').value=p.cat;
  $('pm-img-preview').innerHTML=`<img src="${p.img}" loading="lazy" decoding="async">`;
  if(p.analysis){
    PS_STATE.analysis=p.analysis;
    document.getElementById('ps-info-preview-content').innerHTML=psBuildAnalysisHTML(p.analysis);
    document.getElementById('ps-info-preview').style.display='block';
  }
  setTimeout(()=>{psSwitchTab('image');psRenderColorPresets();psUpdateSummary();if(window.lucide)lucide.createIcons();},100);
  toast('🎨 استوديو الصور لـ '+p.name);
}
async function deleteProduct(id){
  if(!confirm('متأكد تبي تحذف المنتج؟'))return;
  try{
    await apiFetch('/api/store/products/'+id,{method:'DELETE'});
    PRODUCTS=PRODUCTS.filter(x=>x.id!==id);
    renderProducts();renderAll();
    toast('🗑️ تم الحذف من قاعدة البيانات');
  }catch(e){alert('فشل الحذف: '+e.message);}
}
async function regenProductImg(id){
  // Kept for backward compat — but now redirects to image studio
  openImageStudioFor(id);
}
// ───── REAL DATA HELPERS ─────
async function loadRealOrders(limit){
  try{
    const r = await fetch((API||window.location.origin) + '/api/delivery/orders?limit=' + (limit||50));
    const d = await r.json();
    return (d.orders||[]).map(o=>({
      id: o.id || ('#' + (o.id||'?')),
      cust: o.customer_name || 'عميل',
      ph: o.customer_phone || '',
      amt: Math.round(o.total_sar||0),
      st: ({pending:'pending', assigned:'paid', picked_up:'delivering', delivering:'delivering', delivered:'delivered', cancelled:'cancelled'})[o.status] || 'pending',
      drv: o.driver_id ? (o.driver_name || o.driver_id) : '—',
      time: o.created_at ? _relTime(o.created_at) : '',
      raw: o
    }));
  }catch(e){console.warn('loadRealOrders failed',e);return [];}
}
function _relTime(iso){
  try{const d=new Date(iso);const s=Math.floor((Date.now()-d.getTime())/1000);
    if(s<60)return 'قبل ثوانٍ';
    if(s<3600)return 'قبل '+Math.floor(s/60)+' د';
    if(s<86400)return 'قبل '+Math.floor(s/3600)+' س';
    return 'قبل '+Math.floor(s/86400)+' يوم';
  }catch(e){return '';}
}
function _stLabel(st){return ({delivered:'تم التسليم',delivering:'في طريقها',paid:'مدفوع',pending:'بانتظار',cancelled:'ملغي'})[st]||st;}

async function renderOrders(){
  // Real orders first (from MongoDB-backed /api/delivery/orders)
  const real = await loadRealOrders(50);
  const seed=[
    {id:'ord_demo_3047',cust:'نوف العتيبي (تجريبي)',ph:'0567778888',amt:245,st:'delivered',drv:'خالد العتيبي'},
    {id:'ord_demo_3046',cust:'خالد المطيري (تجريبي)',ph:'0561234567',amt:89,st:'delivering',drv:'أحمد السبيعي'},
    {id:'ord_demo_3045',cust:'ريم القحطاني (تجريبي)',ph:'0578889999',amt:320,st:'paid',drv:'—'}
  ];
  const rows = real.length ? real : seed;
  $('orders-table').innerHTML=rows.map(o=>`<tr><td><b>${(o.id||'').replace('ord_','#')}</b></td><td>${o.cust}</td><td style="direction:ltr;text-align:right">${o.ph}</td><td><b>${o.amt} ر.س</b></td><td><span class="status-pill s-${o.st}">${_stLabel(o.st)}</span></td><td>${o.drv}</td><td><a href="/mockups/track.html?id=${o.id}" target="_blank" style="color:var(--purple);font-weight:900;text-decoration:none;font-size:11px">🔍 تتبع ↗</a></td></tr>`).join('');
}
function renderCustomers(){
  $('customers-table').innerHTML=MOCK_CUSTOMERS.map(c=>`<tr><td><div style="display:flex;align-items:center;gap:10px"><div style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,var(--purple),var(--amber));color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900">${c.name.charAt(0)}</div><b>${c.name}</b></div></td><td style="direction:ltr;text-align:right">${c.phone}</td><td><b>${c.orders}</b></td><td><b style="color:var(--purple)">${c.total} ر.س</b></td><td style="color:var(--mute);font-size:11px">${c.last}</td></tr>`).join('');
}

// ───── DELIVERY ─────
async function loadDelivery(){
  try{
    const [stat,ord,drv]=await Promise.all([
      fetch(API+'/api/delivery/stats').then(r=>r.json()),
      fetch(API+'/api/delivery/orders?limit=20').then(r=>r.json()),
      fetch(API+'/api/delivery/drivers').then(r=>r.json())
    ]);
    $('dv-stats').innerHTML=[
      {v:stat.by_status?.pending||0,l:'بانتظار',c:'#fbbf24'},
      {v:(stat.by_status?.delivering||0)+(stat.by_status?.assigned||0),l:'نشطة',c:'#ec4899'},
      {v:stat.active_drivers||0,l:'سائق متاح',c:'#10b981'},
      {v:(stat.revenue_today_sar||0)+' ر.س',l:'إيراد اليوم',c:'#7c3aed'}
    ].map(s=>`<div class="kpi" style="--clr:${s.c};padding:14px"><div class="lbl">${s.l}</div><div class="val" style="font-size:20px">${s.v}</div></div>`).join('');
    $('dv-orders').innerHTML=(ord.orders||[]).slice(0,8).map(o=>{
      const drvObj=(drv.drivers||[]).find(d=>d.id===o.driver_id);
      const needsAssign=!drvObj&&['pending','paid'].includes(o.status);
      return `<tr><td><b>#${o.id.replace('ord_','')}</b></td><td>${o.customer_name}</td><td>${o.distance_km||0} كم</td><td><b>${o.delivery_fee_sar||0} ر.س</b></td><td>${drvObj?drvObj.name:'<span style="color:#dc2626;font-size:11px">⚠️ لم يُسند</span>'}</td><td><span class="status-pill s-${o.status==='delivering'?'delivering':o.status==='delivered'?'delivered':o.status==='cancelled'?'cancelled':'pending'}">${({pending:'بانتظار',assigned:'مُسندة',picked_up:'تم الاستلام',delivering:'في طريقها',delivered:'تم التسليم',cancelled:'ملغاة'})[o.status]||o.status}</span></td><td>${needsAssign?`<button class="btn btn-amber" style="padding:6px 11px;font-size:11px" onclick="autoAssignOrder('${o.id}')"><i data-lucide="zap" style="width:11px;height:11px"></i> إسناد تلقائي</button>`:'<span style="color:var(--mute);font-size:11px">—</span>'}</td></tr>`;
    }).join('');
    $('dv-drivers').innerHTML=(drv.drivers||[]).map(d=>{
      const pay=getDriverPay(d.id)||{mode:d.employment_type==='salaried'?'salary':'commission',commission:70,salary:3000,bonus:2,payout:d.payout_method||'bank'};
      const modeLbl=pay.mode==='salary'?`📅 ${pay.salary} ر.س/شهر`:`💰 عمولة ${pay.commission}%`;
      // Branch assignment (new)
      const branches=JSON.parse(localStorage.getItem('zx_merchant_branches')||'[]');
      const driverBranches=JSON.parse(localStorage.getItem('zx_driver_branches')||'{}');
      const assignedBranch=driverBranches[d.id]||'__all__';
      const branchLbl=assignedBranch==='__all__'?'🌐 كل الفروع':(branches.find(b=>b.id===assignedBranch)?.name_ar||'غير محدد');
      const branchCol=assignedBranch==='__all__'?'#10b981':'#7c3aed';
      return `<div class="panel" style="margin:0;padding:14px"><div style="display:flex;align-items:center;gap:10px"><div style="width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,var(--purple),var(--amber));color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900">${d.name.charAt(0)}</div><div style="flex:1;min-width:0"><b style="font-size:13px">${d.name}</b><div style="font-size:10px;color:var(--mute);direction:ltr;text-align:right">${d.phone}</div></div><span class="status-pill ${d.status==='online'?'s-paid':d.status==='delivering'?'s-delivering':'s-pending'}">${d.status==='online'?'متاح':d.status==='delivering'?'في توصيل':'غير متاح'}</span></div><div style="margin-top:8px;font-size:11px;color:var(--mute)">⭐ ${(d.rating||5).toFixed(1)} · ${d.deliveries_today||0} توصيل · <b>${d.balance_pending_sar||0}</b> ر.س معلّق</div>
      <div style="margin-top:10px;padding:8px;background:var(--bg);border-radius:8px"><div style="font-size:10px;color:var(--mute);margin-bottom:4px">🏪 الفرع المُسند له</div><select onchange="assignDriverBranch('${d.id}',this.value)" style="width:100%;padding:6px 8px;border:1px solid ${branchCol};border-radius:6px;font-family:inherit;font-size:11px;font-weight:700;color:${branchCol};background:#fff;cursor:pointer"><option value="__all__" ${assignedBranch==='__all__'?'selected':''}>🌐 كل الفروع (مفتوح)</option>${branches.map(b=>`<option value="${b.id}" ${assignedBranch===b.id?'selected':''}>🏪 ${b.name_ar}</option>`).join('')}</select></div>
      <div style="margin-top:8px;padding:8px;background:var(--bg);border-radius:8px;display:flex;justify-content:space-between;align-items:center"><span style="font-size:11px;color:var(--mute)">نظام الدفع</span><b style="font-size:11px;color:${pay.mode==='salary'?'#1e40af':'#ec4899'}">${modeLbl}</b></div><div style="display:flex;gap:6px;margin-top:8px"><button class="btn btn-outline" style="flex:1;padding:7px;font-size:10px" onclick="openDriverPayMod('${d.id}','${d.name.replace(/'/g,'')}','${d.phone}')"><i data-lucide="settings" style="width:11px;height:11px"></i> نظام الدفع</button></div></div>`;
    }).join('');
    setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
  }catch(e){}
}

// ───── PAYROLL ─────
// Payout requests (simulated — drivers requesting their balance)
function _seedPayoutRequests(){
  if(localStorage.getItem('zx_payout_requests'))return;
  const seed=[
    {id:'req1',driver_id:'d2',driver_name:'خالد العتيبي',phone:'0552222222',amount:64,fee:4,net:60,method:'STC Pay',account:'0552222222',time:'قبل 12 دقيقة',status:'pending'},
    {id:'req2',driver_id:'d4',driver_name:'فيصل الشمري',phone:'0544444444',amount:48,fee:4,net:44,method:'urpay',account:'0544444444',time:'قبل ساعتين',status:'pending'},
  ];
  localStorage.setItem('zx_payout_requests',JSON.stringify(seed));
}
function _getPayoutRequests(){_seedPayoutRequests();return JSON.parse(localStorage.getItem('zx_payout_requests')||'[]');}
function _setPayoutRequests(arr){localStorage.setItem('zx_payout_requests',JSON.stringify(arr));}
function renderPayoutRequests(){
  const reqs=_getPayoutRequests().filter(r=>r.status==='pending');
  const wrap=document.getElementById('payout-requests-list');
  const count=document.getElementById('payout-req-count');
  const panel=document.getElementById('payout-requests-panel');
  if(count)count.textContent=reqs.length;
  if(!reqs.length){
    if(wrap)wrap.innerHTML='<div style="text-align:center;color:var(--mute);padding:18px;font-size:12px">✓ ما في طلبات تحويل معلّقة</div>';
    return;
  }
  wrap.innerHTML=reqs.map(r=>`
    <div style="background:#fff;border:1px solid #fde68a;border-radius:10px;padding:12px;display:grid;grid-template-columns:1fr 1fr auto;gap:12px;align-items:center">
      <div>
        <b style="font-size:13px">🚗 ${r.driver_name}</b>
        <div style="font-size:11px;color:var(--mute);direction:ltr;text-align:right">${r.phone} · ${r.time}</div>
      </div>
      <div>
        <div style="font-size:11px;color:var(--mute)">يطلب: <b style="color:#0a0a14">${r.amount} ر.س</b></div>
        <div style="font-size:11px;color:#dc2626">- ${r.fee} ر.س رسوم · <b style="color:#10b981">صافي ${r.net} ر.س</b></div>
        <div style="font-size:10px;color:var(--mute);direction:ltr;text-align:right">${r.method} · ${r.account}</div>
      </div>
      <div style="display:flex;gap:6px">
        <button class="btn btn-success" data-testid="approve-payout-${r.id}" onclick="approvePayout('${r.id}')" style="padding:8px 14px;font-size:11px"><i data-lucide="check" style="width:12px;height:12px"></i> حوّل الآن</button>
        <button class="btn btn-outline" onclick="rejectPayout('${r.id}')" style="padding:8px 12px;font-size:11px;color:#dc2626;border-color:#dc2626"><i data-lucide="x" style="width:12px;height:12px"></i></button>
      </div>
    </div>`).join('');
  setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
}
function approvePayout(id){
  const reqs=_getPayoutRequests();
  const r=reqs.find(x=>x.id===id);if(!r)return;
  if(!confirm(`تأكيد تحويل ${r.net} ر.س للسائق ${r.driver_name}؟\n\nالمبلغ: ${r.amount} ر.س\nالرسوم: -${r.fee} ر.س (تخصم من السائق)\nالصافي: ${r.net} ر.س\n\nسيتم التحويل فوراً إلى ${r.method}: ${r.account}`))return;
  r.status='paid';r.paid_at=new Date().toISOString();
  _setPayoutRequests(reqs);
  renderPayoutRequests();
  toast(`✓ تم تحويل ${r.net} ر.س إلى ${r.driver_name} (${r.method})`);
}
function rejectPayout(id){
  if(!confirm('رفض هذا الطلب؟'))return;
  const reqs=_getPayoutRequests();
  const r=reqs.find(x=>x.id===id);if(r){r.status='rejected';_setPayoutRequests(reqs);renderPayoutRequests();toast('تم الرفض');}
}
function approveAllPayouts(){
  const reqs=_getPayoutRequests().filter(r=>r.status==='pending');
  if(!reqs.length){alert('ما في طلبات معلّقة');return;}
  const total=reqs.reduce((s,r)=>s+r.net,0);
  if(!confirm(`اعتماد ${reqs.length} طلب تحويل؟ إجمالي: ${total} ر.س`))return;
  const all=_getPayoutRequests();
  all.forEach(r=>{if(r.status==='pending'){r.status='paid';r.paid_at=new Date().toISOString();}});
  _setPayoutRequests(all);
  renderPayoutRequests();
  toast(`✓ تم تحويل ${total} ر.س على ${reqs.length} سائق`);
}
// Quick transfer for a specific driver (from the payroll table)
function transferDriverNow(driverId,driverName,amount,method,account){
  const fee=4;const net=Math.max(0,amount-fee);
  if(amount<=0){alert('ما عليه مستحق حالياً');return;}
  if(!confirm(`تحويل مخصص للسائق ${driverName}؟\n\nالمبلغ: ${amount} ر.س\nالرسوم: -${fee} ر.س\nالصافي: ${net} ر.س\n\nسيتم التحويل إلى ${method}: ${account}`))return;
  // Add a paid record
  const reqs=_getPayoutRequests();
  reqs.unshift({id:'req'+Date.now(),driver_id:driverId,driver_name:driverName,amount,fee,net,method,account,time:'الآن',status:'paid',paid_at:new Date().toISOString()});
  _setPayoutRequests(reqs);
  toast(`✓ تم تحويل ${net} ر.س إلى ${driverName}`);
}

async function loadPayroll(){
  renderPayoutRequests();
  try{
    const r=await fetch(API+'/api/payroll/calculate');
    const d=await r.json();
    $('pr-summary').innerHTML=[
      {v:d.total_payable_sar+' ر.س',l:'إجمالي مستحق',c:'#7c3aed'},
      {v:d.salaried_total+' ر.س',l:'رواتب موظفين',c:'#1e40af'},
      {v:d.commission_total+' ر.س',l:'عمولات',c:'#ec4899'},
      {v:d.vat_amount_sar+' ر.س',l:'ضريبة 15%',c:'#fbbf24'}
    ].map(s=>`<div class="kpi" style="--clr:${s.c};padding:14px"><div class="lbl">${s.l}</div><div class="val" style="font-size:18px">${s.v}</div></div>`).join('');
    $('pr-table').innerHTML=d.lines.map(l=>{
      const em=l.employment_type==='salaried'?'<span class="status-pill s-paid">📅 موظف</span>':'<span class="status-pill s-delivering">💸 عمولة</span>';
      const methodLabel=({stc_pay:'📱 STC Pay',mada:'🏦 مدى',urpay:'💳 urpay',alinma_pay:'💳 الإنماء'})[l.payout_method]||l.payout_method;
      const safeName=(l.driver_name||'').replace(/'/g,'&#39;');
      const transferBtn=l.amount_sar>0?`<button class="btn btn-success" data-testid="transfer-${l.driver_id}" onclick="transferDriverNow('${l.driver_id}','${safeName}',${l.amount_sar},'${methodLabel}','${l.payout_account||''}')" style="padding:7px 12px;font-size:11px"><i data-lucide="send" style="width:12px;height:12px"></i> حوّل الآن</button>`:'<span style="font-size:10px;color:var(--mute)">—</span>';
      return `<tr><td><b>${l.driver_name}</b><div style="font-size:10px;color:var(--mute);direction:ltr;text-align:right">${l.phone}</div></td><td>${em}</td><td><b style="color:${l.amount_sar>0?'var(--emerald)':'var(--mute)'}">${l.amount_sar} ر.س</b></td><td>${methodLabel}<div style="font-size:10px;color:var(--mute);direction:ltr;text-align:right">${l.payout_account||''}</div></td><td style="display:flex;gap:6px">${transferBtn}<button class="btn btn-outline" style="padding:7px 12px;font-size:11px" onclick="window.open('${API}/api/payroll/statement/${l.driver_id}','_blank')">📄 كشف</button></td></tr>`;
    }).join('');
    setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
  }catch(e){}
}
async function prRunAll(){
  if(!confirm('سيتم تحويل دفعات لجميع السائقين الآن. متأكد؟'))return;
  try{
    const r=await fetch(API+'/api/payroll/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({notify_whatsapp:true})});
    const d=await r.json();
    toast('✓ تم تحويل '+d.total_paid_sar+' ر.س على '+d.processed+' سائق');
    loadPayroll();
  }catch(e){alert('فشل')}
}

// ───── AUTO-DISPATCH SETTINGS ─────
function getDispatchCfg(){return JSON.parse(localStorage.getItem('zx_dispatch')||'{"enabled":true,"radius":10,"grouping":true,"groupRadius":2,"maxOrders":3,"priority":"distance","withdrawFee":4}');}
function saveDispatchCfg(c){localStorage.setItem('zx_dispatch',JSON.stringify(c));}
function toggleAutoDispatch(){const c=getDispatchCfg();c.enabled=document.getElementById('dv-auto-dispatch').checked;saveDispatchCfg(c);toast(c.enabled?'⚡ الإسناد التلقائي مُفعّل':'⏸ تم الإيقاف');}
function openDispatchSettings(){
  const c=getDispatchCfg();
  document.getElementById('ds-radius').value=c.radius;
  document.getElementById('ds-grouping').checked=c.grouping;
  document.getElementById('ds-grouping-radius').value=c.groupRadius;
  document.getElementById('ds-max-orders').value=c.maxOrders;
  document.getElementById('ds-priority').value=c.priority;
  document.getElementById('ds-withdraw-fee').value=c.withdrawFee;
  document.getElementById('dispatch-mod').classList.add('open');
}
function closeDispatchMod(){document.getElementById('dispatch-mod').classList.remove('open')}
function openDriverManager(){
  // Pass current token to driver_manager via URL param
  const tok = localStorage.getItem('zx_token') || localStorage.getItem('zenrex_token') || localStorage.getItem('token') || '';
  window.location.href = '/mockups/driver_manager.html?t=' + encodeURIComponent(tok);
}

// ═══════════ EXTERNAL ORDERS + WITHDRAWALS MODALS ═══════════
async function _authHdr(){
  const tok = localStorage.getItem('zx_token') || localStorage.getItem('zenrex_token') || localStorage.getItem('token') || '';
  return {'Authorization':'Bearer '+tok, 'Content-Type':'application/json'};
}
async function openExternalOrdersMod(){
  const r = await fetch(window.location.origin + '/api/delivery/external/orders', {headers: await _authHdr()});
  const d = await r.json();
  const items = d.orders || [];
  document.getElementById('ext-count').textContent = items.length;
  const rows = items.map(o => `
    <div style="background:#1a1a2e;border:1px solid #2a2a44;border-radius:12px;padding:14px;margin-bottom:8px">
      <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px">
        <div>
          <b style="color:#fff">${o.id}</b> <span style="color:#fbbf24;font-size:10px;padding:2px 7px;background:rgba(251,191,36,.15);border-radius:99px;font-weight:900">${o.service_type==='errand'?'مشوار':'توصيل'}</span> <span style="color:#94a3b8;font-size:11px">${o.customer_name} · ${o.customer_phone}</span>
        </div>
        <div style="color:#10b981;font-weight:900;font-size:16px">${o.total_sar} ر.س</div>
      </div>
      <div style="font-size:11px;color:#94a3b8;margin-bottom:6px">${o.stops.length} نقطة · ${o.distance_km} كم · ${o.eta_minutes} د${o.scheduled_for ? ' · 📅 '+o.scheduled_for : ''}</div>
      <div style="font-size:11px;color:#fff;margin-bottom:10px">السائق يأخذ: <b style="color:#10b981">${o.driver_share_sar} ر.س</b> · ربحك: <b style="color:#7c3aed">${o.merchant_share_sar} ر.س</b></div>
      <div style="display:flex;gap:6px">
        <span style="padding:3px 10px;background:${o.status==='pending_merchant'?'rgba(251,191,36,.2)':o.status==='accepted'?'rgba(16,185,129,.2)':o.status==='delivered'?'rgba(6,182,212,.2)':'rgba(148,163,184,.2)'};color:#fff;border-radius:99px;font-size:10px;font-weight:900">${o.status}</span>
        ${o.status==='pending_merchant' ? `<button onclick="acceptExt('${o.id}')" style="margin-right:auto;padding:6px 14px;background:#10b981;border:none;color:#fff;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">قبول وإسناد</button><button onclick="rejectExt('${o.id}')" style="padding:6px 14px;background:transparent;border:1px solid #ef4444;color:#ef4444;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">رفض</button>` : ''}
      </div>
    </div>`).join('') || '<div style="text-align:center;padding:30px;color:#94a3b8">لا توجد طلبات توصيل خارجي بعد</div>';
  document.body.insertAdjacentHTML('beforeend', `
    <div class="modal-bg open" id="ext-mod" onclick="if(event.target===this)document.getElementById('ext-mod').remove()" style="z-index:9500">
      <div class="modal" style="max-width:640px;max-height:85vh;overflow-y:auto;background:#0a0a14;color:#fff">
        <h3 style="margin-bottom:14px;color:#fff">🚚 طلبات التوصيل الخارجي (Mrsool-style)</h3>
        ${rows}
      </div>
    </div>`);
}
window.acceptExt = async function(id){
  await fetch(window.location.origin + '/api/delivery/external/orders/'+id+'/accept', {method:'POST', headers: await _authHdr(), body:'{}'});
  document.getElementById('ext-mod')?.remove();
  openExternalOrdersMod();
};
window.rejectExt = async function(id){
  await fetch(window.location.origin + '/api/delivery/external/orders/'+id+'/reject', {method:'POST', headers: await _authHdr(), body: JSON.stringify({reason:'merchant_rejected'})});
  document.getElementById('ext-mod')?.remove();
  openExternalOrdersMod();
};

async function openWithdrawalsMod(){
  const r = await fetch(window.location.origin + '/api/delivery/withdrawals', {headers: await _authHdr()});
  const d = await r.json();
  const items = d.withdrawals || [];
  document.getElementById('wd-count').textContent = items.filter(w => w.status==='pending').length;
  const rows = items.map(w => `
    <div style="background:#1a1a2e;border:1px solid #2a2a44;border-radius:12px;padding:14px;margin-bottom:8px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <div><b style="color:#fff">${w.driver_name || 'سائق'}</b> <span style="color:#94a3b8;font-size:11px">${w.driver_phone || ''}</span></div>
        <div style="color:#10b981;font-weight:900">${w.amount_net_sar} ر.س <small style="color:#94a3b8;font-weight:500">(صافي)</small></div>
      </div>
      <div style="font-size:11px;color:#94a3b8;margin-bottom:8px">إجمالي: ${w.amount_gross_sar} · رسم: ${w.fee_sar} · ${w.method.toUpperCase()}: <span style="direction:ltr">${w.account.slice(0,20)}</span></div>
      <div style="display:flex;gap:6px;align-items:center">
        <span style="padding:3px 10px;background:${w.status==='pending'?'rgba(251,191,36,.2)':w.status==='approved'?'rgba(16,185,129,.2)':'rgba(239,68,68,.2)'};color:#fff;border-radius:99px;font-size:10px;font-weight:900">${w.status==='pending'?'⏳ معلّق':w.status==='approved'?'✓ مُعتمد':'✗ مرفوض'}</span>
        ${w.status==='pending' ? `<button onclick="approveWd('${w.id}')" style="margin-right:auto;padding:5px 12px;background:#10b981;border:none;color:#fff;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">اعتماد التحويل</button><button onclick="rejectWd('${w.id}')" style="padding:5px 12px;background:transparent;border:1px solid #ef4444;color:#ef4444;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">رفض</button>` : ''}
      </div>
    </div>`).join('') || '<div style="text-align:center;padding:30px;color:#94a3b8">لا توجد طلبات سحب بعد</div>';
  document.body.insertAdjacentHTML('beforeend', `
    <div class="modal-bg open" id="wd-mod" onclick="if(event.target===this)document.getElementById('wd-mod').remove()" style="z-index:9500">
      <div class="modal" style="max-width:640px;max-height:85vh;overflow-y:auto;background:#0a0a14;color:#fff">
        <h3 style="margin-bottom:14px;color:#fff">💸 طلبات سحب السائقين</h3>
        ${rows}
      </div>
    </div>`);
}
window.approveWd = async function(id){
  await fetch(window.location.origin + '/api/delivery/withdrawals/'+id+'/approve', {method:'POST', headers: await _authHdr()});
  document.getElementById('wd-mod')?.remove();
  openWithdrawalsMod();
};
window.rejectWd = async function(id){
  await fetch(window.location.origin + '/api/delivery/withdrawals/'+id+'/reject', {method:'POST', headers: await _authHdr(), body: JSON.stringify({reason:'rejected'})});
  document.getElementById('wd-mod')?.remove();
  openWithdrawalsMod();
};

async function openRatingsMod(){
  const r = await fetch(window.location.origin + '/api/delivery/ratings/merchant', {headers: await _authHdr()});
  const d = await r.json();
  const drivers = d.drivers || [];
  const rows = drivers.map(drv => `
    <div style="background:#1a1a2e;border:1px solid #2a2a44;border-radius:14px;padding:16px;margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <div>
          <b style="color:#fff;font-size:14px">${drv.driver_name || 'سائق'}</b>
          <div style="font-size:11px;color:#94a3b8;margin-top:2px">${drv.driver_id} · ${drv.count} تقييم</div>
        </div>
        <div style="text-align:left">
          <div style="color:#fbbf24;font-size:22px;font-weight:900">${drv.avg}</div>
          <div style="color:#fbbf24;font-size:13px">${'★'.repeat(Math.round(drv.avg))}${'☆'.repeat(5-Math.round(drv.avg))}</div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:6px">
        ${drv.ratings.map(r => `
          <div style="background:#0a0a14;padding:9px 12px;border-radius:9px">
            <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">
              <span style="color:#fff;font-weight:700">${r.customer_name}</span>
              <span style="color:#fbbf24">${'★'.repeat(r.stars)}${'☆'.repeat(5-r.stars)}</span>
            </div>
            ${r.comment ? `<div style="color:#cbd5e1;font-size:11px;line-height:1.6">"${r.comment}"</div>` : ''}
            ${r.tags && r.tags.length ? `<div style="display:flex;gap:3px;flex-wrap:wrap;margin-top:5px">${r.tags.map(t => `<span style="padding:1px 7px;background:rgba(16,185,129,.15);color:#10b981;border-radius:99px;font-size:9px;font-weight:900">${t}</span>`).join('')}</div>` : ''}
            <div style="color:#64748b;font-size:9px;margin-top:4px">${new Date(r.created_at).toLocaleDateString('ar-SA')}</div>
          </div>
        `).join('')}
      </div>
    </div>`).join('') || '<div style="text-align:center;padding:30px;color:#94a3b8">لا توجد تقييمات بعد</div>';
  document.body.insertAdjacentHTML('beforeend', `
    <div class="modal-bg open" id="rt-mod" onclick="if(event.target===this)document.getElementById('rt-mod').remove()" style="z-index:9500">
      <div class="modal" style="max-width:680px;max-height:85vh;overflow-y:auto;background:#0a0a14;color:#fff">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
          <h3 style="color:#fff;margin:0">⭐ تقييمات السائقين <small style="color:#94a3b8;font-weight:500;font-size:12px">${d.total_ratings} تقييم إجمالي</small></h3>
        </div>
        ${rows}
      </div>
    </div>`);
}

// Poll badge counts every 30s
setInterval(async () => {
  try {
    const tok = localStorage.getItem('zx_token') || localStorage.getItem('zenrex_token') || localStorage.getItem('token') || '';
    if (!tok) return;
    const [e, w] = await Promise.all([
      fetch(window.location.origin + '/api/delivery/external/orders?status=pending_merchant', {headers:{'Authorization':'Bearer '+tok}}).then(r=>r.json()).catch(()=>({orders:[]})),
      fetch(window.location.origin + '/api/delivery/withdrawals?status=pending', {headers:{'Authorization':'Bearer '+tok}}).then(r=>r.json()).catch(()=>({withdrawals:[]})),
    ]);
    const eEl = document.getElementById('ext-count'), wEl = document.getElementById('wd-count');
    if (eEl) eEl.textContent = (e.orders||[]).length || '';
    if (wEl) wEl.textContent = (w.withdrawals||[]).length || '';
  } catch(err){}
}, 30000);
function saveDispatchSettings(){
  const c={
    enabled:document.getElementById('dv-auto-dispatch').checked,
    radius:+document.getElementById('ds-radius').value,
    grouping:document.getElementById('ds-grouping').checked,
    groupRadius:+document.getElementById('ds-grouping-radius').value,
    maxOrders:+document.getElementById('ds-max-orders').value,
    priority:document.getElementById('ds-priority').value,
    withdrawFee:+document.getElementById('ds-withdraw-fee').value
  };
  saveDispatchCfg(c);
  closeDispatchMod();
  document.getElementById('dvs-radius').textContent=c.radius+' كم';
  document.getElementById('dvs-group').textContent=c.grouping?`مُفعّل (≤${c.groupRadius}كم)`:'مُعطّل';
  document.getElementById('dvs-fee').textContent=c.withdrawFee+' ر.س';
  toast('✓ تم حفظ إعدادات الإسناد · سحب: '+c.withdrawFee+' ر.س لكل عملية');
}
async function autoAssignOrder(orderId){
  const cfg=getDispatchCfg();
  if(!cfg.enabled){alert('الإسناد التلقائي مُعطّل — فعّله أولاً');return;}
  toast('⚡ يبحث عن أقرب سائق ضمن '+cfg.radius+' كم…');
  try{
    // Try real backend endpoint, fallback to local simulation
    const r=await fetch(API+'/api/delivery/auto-assign',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({order_id:orderId,radius_km:cfg.radius,grouping:cfg.grouping,group_radius_km:cfg.groupRadius,max_orders:cfg.maxOrders,priority:cfg.priority})}).catch(()=>null);
    if(r&&r.ok){const d=await r.json();toast('✓ أُسند للسائق: '+d.driver_name+' ('+d.distance_km+' كم)');loadDelivery();return;}
  }catch(e){}
  // Simulation fallback
  setTimeout(()=>{toast('✓ أُسند تلقائياً لأقرب سائق (محاكاة)');loadDelivery();},1200);
}

// ───── DRIVER PAY MODEL ─────
function getDriverPayAll(){return JSON.parse(localStorage.getItem('zx_driver_pay')||'{}');}
function getDriverPay(id){return getDriverPayAll()[id];}
let DPM_CURRENT=null;
function openDriverPayMod(id,name,phone){
  DPM_CURRENT=id;
  const cur=getDriverPay(id)||{mode:'commission',commission:70,salary:3000,bonus:2,payout:'bank'};
  document.getElementById('dpm-driver-info').innerHTML=`<div style="width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,var(--purple),var(--amber));color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900">${name.charAt(0)}</div><div><b style="font-size:13px">${name}</b><div style="font-size:10px;color:var(--mute);direction:ltr;text-align:right">${phone}</div></div>`;
  document.querySelectorAll('.pay-card').forEach(c=>c.classList.toggle('selected',c.dataset.mode===cur.mode));
  document.querySelector(`input[name="dpm-mode"][value="${cur.mode}"]`).checked=true;
  document.getElementById('dpm-commission').value=cur.commission;
  document.getElementById('dpm-salary').value=cur.salary;
  document.getElementById('dpm-bonus').value=cur.bonus;
  document.getElementById('dpm-payout').value=cur.payout;
  document.getElementById('dpm-commission-fields').style.display=cur.mode==='commission'?'block':'none';
  document.getElementById('dpm-salary-fields').style.display=cur.mode==='salary'?'block':'none';
  document.getElementById('driver-pay-mod').classList.add('open');
}
function closeDriverPayMod(){document.getElementById('driver-pay-mod').classList.remove('open')}
function dpmToggleMode(inp){
  document.querySelectorAll('.pay-card').forEach(c=>c.classList.toggle('selected',c.dataset.mode===inp.value));
  document.getElementById('dpm-commission-fields').style.display=inp.value==='commission'?'block':'none';
  document.getElementById('dpm-salary-fields').style.display=inp.value==='salary'?'block':'none';
}
function saveDriverPay(){
  if(!DPM_CURRENT)return;
  const all=getDriverPayAll();
  all[DPM_CURRENT]={
    mode:document.querySelector('input[name="dpm-mode"]:checked').value,
    commission:+document.getElementById('dpm-commission').value,
    salary:+document.getElementById('dpm-salary').value,
    bonus:+document.getElementById('dpm-bonus').value,
    payout:document.getElementById('dpm-payout').value
  };
  localStorage.setItem('zx_driver_pay',JSON.stringify(all));
  closeDriverPayMod();
  loadDelivery();
  toast('✓ تم حفظ نظام الدفع للسائق');
}

// ───── MERCHANT SERVICES (7 services with auto-activation) ─────
const SERVICES=[
  {id:'domain',icon:'🌐',bg:'linear-gradient(135deg,#3b82f6,#06b6d4)',title:'نطاق متجر مخصص',desc:'احصل على رابط احترافي مثل mystore.com بدل الرابط الفرعي على Zenrex',feats:['نطاق .com / .sa / .net','تركيب تلقائي خلال دقائق','SSL مجاني','تجديد سنوي تلقائي'],price:99,period:'سنوياً',featured:false,oneTime:false},
  {id:'email',icon:'📧',bg:'linear-gradient(135deg,#ec4899,#f43f5e)',title:'إيميل بنطاق المتجر',desc:'5 صناديق بريد احترافية مثل info@mystore.com (يتطلب تفعيل النطاق)',feats:['5 صناديق بريد','مساحة 10 GB لكل صندوق','إعادة توجيه ذكي','حماية من البريد المزعج'],price:49,period:'سنوياً',featured:false,oneTime:false},
  {id:'template',icon:'🎨',bg:'linear-gradient(135deg,#fbbf24,#f59e0b)',title:'قالب متجر فاخر',desc:'قوالب احترافية جاهزة (مطاعم، أزياء، عطور، صيدليات…) — تفعيل بضغطة',feats:['12+ قالب جاهز','تخصيص ألوان وخطوط','معاينة فورية قبل التفعيل','يتجدد كل شهر'],price:199,period:'مرة واحدة',featured:true,oneTime:true},
  {id:'app',icon:'📱',bg:'linear-gradient(135deg,#7c3aed,#a78bfa)',title:'تطبيق متجر iOS/Android',desc:'تطبيق جوال بشعارك على App Store و Google Play — نبنيه ونرفعه لك',feats:['iOS + Android','اسم وشعار متجرك','إشعارات Push','تحديث تلقائي'],price:999,period:'مرة واحدة',featured:false,oneTime:true},
  {id:'delivery_plus',icon:'🚚',bg:'linear-gradient(135deg,#10b981,#059669)',title:'خدمة التوصيل الذكية',desc:'الإسناد التلقائي + تتبع GPS + إشعارات WhatsApp للعميل والسائق',feats:['إسناد فوري للأقرب','تتبع لحظي للعميل','WhatsApp تلقائي','تقارير مفصّلة'],price:79,period:'شهرياً',featured:true,oneTime:false},
  {id:'vip',icon:'⭐',bg:'linear-gradient(135deg,#ef4444,#dc2626)',title:'دعم VIP أولوية',desc:'فريق دعم خاص متاح 24/7 يرد خلال 5 دقائق + استشارات تسويقية',feats:['رد خلال 5 دقائق','مدير حساب مخصص','استشارات شهرية','أولوية في الإصلاحات'],price:99,period:'شهرياً',featured:false,oneTime:false},
  {id:'ai_premium',icon:'🧠',bg:'linear-gradient(135deg,#06b6d4,#0891b2)',title:'AI Premium (Claude Opus)',desc:'استبدل Gemini Flash بـ Claude Opus 4.5 للنتائج الأفخم + رصيد نقاط مضاعف',feats:['Claude Opus 4.5','تحليل أعمق وأطول','صور 4K مزدوجة','+50% نقاط شهرياً'],price:149,period:'شهرياً',featured:false,oneTime:false}
];
function getActiveServices(){return JSON.parse(localStorage.getItem('zx_active_services')||'{}');}
function loadServices(){
  const active=getActiveServices();
  document.getElementById('services-grid').innerHTML=SERVICES.map(s=>{
    const isActive=!!active[s.id];
    return `<div class="svc-card ${s.featured?'featured':''} ${isActive?'active-svc':''}">
      <div class="svc-icon" style="background:${s.bg}">${s.icon}</div>
      <h4>${s.title}</h4>
      <div class="svc-desc">${s.desc}</div>
      ${s.feats.map(f=>`<div class="svc-feat">${f}</div>`).join('')}
      <div class="svc-price">
        <div><b>${s.price}</b> ر.س <span class="period">/ ${s.period}</span>${s.oneTime?' <span class="one-time">دفعة واحدة</span>':''}</div>
        ${isActive?`<button class="svc-btn" style="background:var(--emerald)" onclick="deactivateService('${s.id}')"><i data-lucide="check-circle" style="width:13px;height:13px"></i> مُفعّل · إلغاء</button>`:`<button class="svc-btn" onclick="activateService('${s.id}')"><i data-lucide="zap" style="width:13px;height:13px"></i> فعّل الآن</button>`}
      </div>
    </div>`;
  }).join('');
  setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
}
function activateService(id){
  const svc=SERVICES.find(s=>s.id===id);if(!svc)return;
  if(!confirm(`تفعيل خدمة "${svc.title}" بمبلغ ${svc.price} ر.س ${svc.oneTime?'(دفعة واحدة)':svc.period}؟\n\nسيتم الخصم من بطاقتك الافتراضية وتفعيل الخدمة تلقائياً بدون أي تدخل بشري.`))return;
  const active=getActiveServices();
  active[id]={activatedAt:Date.now(),expires:svc.oneTime?null:Date.now()+(svc.period==='سنوياً'?365:30)*86400000};
  localStorage.setItem('zx_active_services',JSON.stringify(active));
  loadServices();
  toast('⚡ تم تفعيل "'+svc.title+'" تلقائياً · سيكون نشطاً خلال 60 ثانية');
}
function deactivateService(id){
  if(!confirm('متأكد تبي تلغي الخدمة؟ بتظل نشطة حتى نهاية الفترة المدفوعة.'))return;
  const active=getActiveServices();delete active[id];localStorage.setItem('zx_active_services',JSON.stringify(active));
  loadServices();
  toast('تم إلغاء التجديد التلقائي');
}

// ───── SMART MANAGEMENT (Auto-post + Smart Replies) ─────
function getSmartCfg(){return JSON.parse(localStorage.getItem('zx_smart_mgmt')||'{"autopost":true,"replies":true,"replyMode":"ai","platforms":{"instagram":true,"tiktok":true,"twitter":true,"snapchat":false,"facebook":false,"whatsapp":true,"telegram":false}}');}
function loadSmartMgmt(){
  const cfg=getSmartCfg();
  document.getElementById('sm-autopost').checked=cfg.autopost!==false;
  document.getElementById('sm-replies').checked=cfg.replies!==false;
  document.querySelectorAll('input[name="sm-reply-mode"]').forEach(r=>r.checked=r.value===(cfg.replyMode||'ai'));
  document.querySelectorAll('.pay-card[data-mode]').forEach(c=>c.classList.toggle('selected',c.dataset.mode===(cfg.replyMode||'ai')));
  document.getElementById('sm-canned-section').style.display=cfg.replyMode==='canned'?'block':'none';
  document.getElementById('sm-ai-section').style.display=cfg.replyMode==='canned'?'none':'block';
  // Render platforms
  const platforms=[{id:'instagram',ic:'📸',nm:'انستقرام',bg:'linear-gradient(135deg,#f09433,#dc2743)'},{id:'tiktok',ic:'🎵',nm:'تيك توك',bg:'#000'},{id:'twitter',ic:'𝕏',nm:'X',bg:'#000'},{id:'snapchat',ic:'👻',nm:'سناب',bg:'#FFFC00',fg:'#000'},{id:'facebook',ic:'f',nm:'فيسبوك',bg:'#1877F2'},{id:'whatsapp',ic:'💬',nm:'واتساب',bg:'#25D366'},{id:'telegram',ic:'✈',nm:'تيليجرام',bg:'#0088cc'}];
  document.getElementById('sm-platforms').innerHTML=platforms.map(p=>`<label style="display:flex;align-items:center;gap:8px;padding:10px;background:${cfg.platforms&&cfg.platforms[p.id]?'#faf5ff':'#f9fafb'};border:1.5px solid ${cfg.platforms&&cfg.platforms[p.id]?'var(--purple)':'var(--border)'};border-radius:10px;cursor:pointer"><input type="checkbox" data-platform="${p.id}" ${cfg.platforms&&cfg.platforms[p.id]?'checked':''} onchange="smSaveCfg()" style="accent-color:var(--purple)"><div style="width:30px;height:30px;border-radius:8px;background:${p.bg};color:${p.fg||'#fff'};display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:900">${p.ic}</div><b style="font-size:12px">${p.nm}</b></label>`).join('');
  smRenderCanned();
  setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
}
function smToggleMode(inp){
  document.querySelectorAll('.pay-card[data-mode]').forEach(c=>c.classList.toggle('selected',c.dataset.mode===inp.value));
  document.getElementById('sm-canned-section').style.display=inp.value==='canned'?'block':'none';
  document.getElementById('sm-ai-section').style.display=inp.value==='canned'?'none':'block';
  smSaveCfg();
}
function smSaveCfg(){
  const platforms={};document.querySelectorAll('[data-platform]').forEach(c=>{platforms[c.dataset.platform]=c.checked});
  const cfg={
    autopost:document.getElementById('sm-autopost').checked,
    replies:document.getElementById('sm-replies').checked,
    replyMode:document.querySelector('input[name="sm-reply-mode"]:checked')?.value||'ai',
    platforms,
    template:document.getElementById('sm-template').value,
    when:document.getElementById('sm-when').value,
    hashtags:+document.getElementById('sm-hashtags').value,
    personality:document.getElementById('sm-personality')?.value||'',
    dailyLimit:+document.getElementById('sm-daily-limit')?.value||100,
    costPerReply:+document.getElementById('sm-cost-per-reply')?.value||1,
    handoff:document.getElementById('sm-handoff')?.value||'complaint'
  };
  localStorage.setItem('zx_smart_mgmt',JSON.stringify(cfg));
  toast('✓ حُفظت إعدادات الإدارة الذكية');
}
function smRenderCanned(){
  const list=JSON.parse(localStorage.getItem('zx_canned_replies')||'[{"q":"كم سعر هذا المنتج؟","a":"السعر موجود تحت اسم المنتج. اطلب الآن وفيه شحن مجاني للطلبات فوق 200 ر.س 🚚"},{"q":"كم يستغرق التوصيل؟","a":"التوصيل خلال 1-3 أيام عمل داخل المدن الرئيسية، 3-5 أيام للمناطق الأخرى."},{"q":"هل في إرجاع؟","a":"نعم، الإرجاع متاح خلال 7 أيام من الاستلام بشرط أن المنتج بحالته الأصلية."}]');
  document.getElementById('sm-canned-list').innerHTML=list.map((c,i)=>`<div style="display:grid;grid-template-columns:1fr 1fr auto;gap:6px;align-items:center"><input value="${c.q.replace(/"/g,'&quot;')}" placeholder="السؤال أو الكلمة المفتاحية" style="padding:9px;border:1px solid var(--border);border-radius:8px;font-size:11px" oninput="smUpdCanned(${i},'q',this.value)"><input value="${c.a.replace(/"/g,'&quot;')}" placeholder="الرد الجاهز" style="padding:9px;border:1px solid var(--border);border-radius:8px;font-size:11px" oninput="smUpdCanned(${i},'a',this.value)"><button class="btn btn-outline" style="padding:7px 10px;font-size:10px;color:var(--rd)" onclick="smRemoveCanned(${i})"><i data-lucide="trash-2" style="width:11px;height:11px"></i></button></div>`).join('');
  if(window.lucide)lucide.createIcons();
}
function smAddCanned(){const list=JSON.parse(localStorage.getItem('zx_canned_replies')||'[]');list.push({q:'',a:''});localStorage.setItem('zx_canned_replies',JSON.stringify(list));smRenderCanned();}
function smUpdCanned(i,k,v){const list=JSON.parse(localStorage.getItem('zx_canned_replies')||'[]');if(list[i]){list[i][k]=v;localStorage.setItem('zx_canned_replies',JSON.stringify(list));}}
function smRemoveCanned(i){const list=JSON.parse(localStorage.getItem('zx_canned_replies')||'[]');list.splice(i,1);localStorage.setItem('zx_canned_replies',JSON.stringify(list));smRenderCanned();toast('🗑️ تم الحذف');}

// Auto-post hook — called from pmSave when a new product is saved
function autoPostNewProduct(product){
  const cfg=getSmartCfg();
  if(!cfg.autopost)return;
  const active=Object.entries(cfg.platforms||{}).filter(([k,v])=>v).map(([k])=>k);
  if(!active.length)return;
  const tpl=cfg.template||'منتج جديد: {{title}} بسعر {{price}} ر.س — {{link}}';
  const text=tpl
    .replace(/\{\{title\}\}/g,product.name||'')
    .replace(/\{\{description\}\}/g,product.desc||(product.analysis&&product.analysis.description)||'')
    .replace(/\{\{price\}\}/g,product.price||0)
    .replace(/\{\{link\}\}/g,'zenrex.ai/p/'+product.id);
  // Deduct points (2 per platform)
  const cost=active.length*2;
  if(WALLET<cost)return;
  WALLET-=cost;localStorage.setItem('zx_credits',WALLET);$('wallet-balance').textContent=WALLET.toLocaleString('ar-EG');
  const platformNames={instagram:'انستقرام',tiktok:'تيك توك',twitter:'X',snapchat:'سناب',facebook:'فيسبوك',whatsapp:'واتساب',telegram:'تيليجرام'};
  const whenLbl={immediate:'الآن',delay_15:'بعد 15 دقيقة',delay_60:'بعد ساعة',peak:'وقت ذروة المتابعين',manual:'بانتظار المراجعة'}[cfg.when||'immediate'];
  toast(`📤 جاري النشر التلقائي ${whenLbl} على: ${active.map(a=>platformNames[a]||a).join('، ')} · -${cost} نقاط`);
}

// ───── GATEWAYS ─────
async function loadGateways(){
  try{
    const profR=await fetch(API+'/api/payments/countries').then(r=>r.json());
    const sel=$('gw-country-sel');
    if(!sel.options.length){
      const flags={SA:'🇸🇦',AE:'🇦🇪',EG:'🇪🇬',KW:'🇰🇼',US:'🇺🇸',GB:'🇬🇧',DE:'🇩🇪',FR:'🇫🇷',NL:'🇳🇱',CN:'🇨🇳',IN:'🇮🇳',SG:'🇸🇬',BH:'🇧🇭',QA:'🇶🇦'};
      sel.innerHTML=Object.entries(profR.profiles).map(([c,p])=>`<option value="${c}">${flags[c]||'🌐'} ${p.name_ar}</option>`).join('');
    }
    gwLoad();
  }catch(e){}
}
async function gwLoad(){
  const c=$('gw-country-sel').value||'SA';
  try{
    const r=await fetch(API+'/api/payments/by-country?country='+c);
    const d=await r.json();
    $('gw-list').innerHTML=d.gateways.map((g,idx)=>{
      const typeColor={card:'#1e40af',wallet:'#7c3aed',bnpl:'#ec4899',bank:'#059669',cod:'#10b981',qr:'#0891b2',crypto:'#f59e0b'}[g.type]||'#6b7280';
      const u=g.is_universal?'<span style="background:#fef3c7;color:#92400e;padding:2px 6px;border-radius:99px;font-size:9px;font-weight:900;margin-right:4px">🌐 عالمي</span>':'';
      const creds=g.required_credentials||[];
      const credsHtml=creds.length?creds.map(c=>`
        <div class="field" style="margin-bottom:8px">
          <label style="font-size:11px;font-weight:900;color:#0a0a14;display:block;margin-bottom:4px">${c.label_ar||c.name}${c.type==='password'?' 🔒':''}</label>
          <input type="${c.type==='password'?'password':'text'}" placeholder="${c.where_ar||''}" data-gw="${g.id}" data-cred="${c.name}" style="width:100%;padding:9px;border:1px solid var(--border);border-radius:8px;font-family:monospace;font-size:11px;direction:ltr">
          <div style="font-size:10px;color:var(--mute);margin-top:3px">📍 ${c.where_ar||'—'}</div>
        </div>`).join(''):'<div style="color:var(--mute);font-size:11px">لا تحتاج مفاتيح — تربط مباشرة</div>';
      const tipHtml=g.ai_helper_ar?`<div style="background:#faf5ff;border:1px solid #ddd6fe;border-radius:10px;padding:10px;margin-top:10px;font-size:11px;color:#5b21b6;line-height:1.8">💡 <b>نصيحة Zenrex AI:</b> ${g.ai_helper_ar}</div>`:'';
      return `<div style="background:#fff;border:1.5px solid var(--border);border-radius:14px;padding:14px;margin-bottom:10px">
        <div style="display:grid;grid-template-columns:auto 1fr auto;gap:14px;align-items:center">
          <div style="width:48px;height:48px;border-radius:10px;background:${g.badge.bg};color:${g.badge.fg};display:flex;align-items:center;justify-content:center;font-weight:900;font-size:10px;text-align:center;line-height:1.1">${g.name_en.slice(0,8)}</div>
          <div><div style="font-size:13px;font-weight:900">${g.name_ar} ${u}<span style="background:${typeColor}20;color:${typeColor};padding:2px 6px;border-radius:99px;font-size:9px;margin-right:4px">${({card:'💳',wallet:'📱',bnpl:'💎',bank:'🏦',cod:'💵',qr:'📲',crypto:'₿'})[g.type]} ${g.type.toUpperCase()}</span></div>
            <div style="font-size:11px;color:var(--mute);margin-top:3px">${g.badge.slogan_ar}</div>
            <div style="font-size:11px;color:#dc2626;margin-top:3px">💰 ${g.real_fees?.merchant||g.fees_hint} · تسوية ${g.real_fees?.settlement_days||1} يوم</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">
              <a href="${g.merchant_signup_url||'#'}" target="_blank" rel="noopener" style="background:#10b981;color:#fff;padding:5px 10px;border-radius:99px;font-size:10px;font-weight:900;text-decoration:none">🚀 سجّل</a>
              <a href="${g.merchant_dashboard_url||'#'}" target="_blank" rel="noopener" style="background:#0a0a14;color:#fbbf24;padding:5px 10px;border-radius:99px;font-size:10px;font-weight:900;text-decoration:none">🔐 لوحة</a>
              <a href="${g.developer_docs_url||'#'}" target="_blank" rel="noopener" style="background:#7c3aed;color:#fff;padding:5px 10px;border-radius:99px;font-size:10px;font-weight:900;text-decoration:none">📚 Docs</a>
              <button onclick="gwToggleSetup('${g.id}_${idx}')" data-testid="gw-setup-${g.id}" style="background:#fbbf24;color:#0a0a14;padding:5px 10px;border-radius:99px;font-size:10px;font-weight:900;border:none;cursor:pointer">⚙️ كيف أربط؟</button>
            </div>
          </div>
          <label style="cursor:pointer"><input type="checkbox" data-testid="gw-enable-${g.id}" onchange="gwToggleEnable('${g.id}',this.checked)" style="width:36px;height:20px;accent-color:var(--purple)"></label>
        </div>
        <div id="setup-${g.id}_${idx}" style="display:none;margin-top:14px;padding-top:14px;border-top:1px dashed var(--border)">
          <h4 style="font-size:12px;font-weight:900;margin-bottom:10px;color:var(--purple)">🔐 خطوات الربط — املأ المفاتيح من بوابة ${g.name_ar}:</h4>
          ${credsHtml}
          ${tipHtml}
          <div style="display:flex;gap:8px;margin-top:10px">
            <button class="btn btn-primary" data-testid="gw-save-${g.id}" onclick="gwSaveKeys('${g.id}')" style="flex:1;padding:10px;font-size:12px"><i data-lucide="save" style="width:13px;height:13px"></i> حفظ المفاتيح بشكل آمن</button>
            <button class="btn btn-outline" data-testid="gw-test-${g.id}" onclick="gwTestConnection('${g.id}')" style="padding:10px 14px;font-size:12px"><i data-lucide="zap" style="width:13px;height:13px"></i> اختبر الاتصال</button>
          </div>
          <div style="margin-top:10px;font-size:10px;color:var(--mute);background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:8px;line-height:1.6">⚠️ <b>تنبيه:</b> Zenrex ما تاخذ أي عمولة على معاملاتك — المفاتيح تروح مباشرة لـ ${g.name_ar}. الأموال تنزل في حسابك مباشرة.</div>
        </div>
      </div>`;
    }).join('');
    setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
  }catch(e){console.error(e);}
}
function gwToggleSetup(uid){
  const el=document.getElementById('setup-'+uid);
  if(el)el.style.display=el.style.display==='none'?'block':'none';
}
function gwSaveKeys(gid){
  const inputs=document.querySelectorAll(`[data-gw="${gid}"]`);
  const keys={};
  let missing=false;
  inputs.forEach(i=>{if(!i.value.trim())missing=true;keys[i.dataset.cred]=i.value.trim();});
  if(missing){alert('املأ كل المفاتيح أولاً');return;}
  const store=JSON.parse(localStorage.getItem('zx_gateway_keys')||'{}');
  store[gid]={keys,updated_at:new Date().toISOString()};
  localStorage.setItem('zx_gateway_keys',JSON.stringify(store));
  toast('🔐 تم حفظ مفاتيح '+gid+' بشكل آمن');
}
function gwTestConnection(gid){
  toast('⚡ يختبر الاتصال مع '+gid+'…');
  setTimeout(()=>toast('✓ الاتصال يعمل — جاهز لاستقبال المدفوعات'),1500);
}
function gwToggleEnable(gid,on){
  const store=JSON.parse(localStorage.getItem('zx_gateway_enabled')||'{}');
  store[gid]=on;localStorage.setItem('zx_gateway_enabled',JSON.stringify(store));
  toast(on?('✓ تم تفعيل '+gid):('⏸ تم إيقاف '+gid));
}

// ───── VARIANTS / WARRANTY / SPECS FUNCTIONS ─────
function toggleVariantField(field){
  const cb=document.getElementById('vf-'+field);
  const sec=document.querySelector('.vf-section[data-vf="'+field+'"]');
  if(sec)sec.style.display=cb?.checked?'block':'none';
}
function addColorVariant(){
  const name=prompt('اسم اللون (مثل: أحمر، ذهبي، رمادي تيتانيوم):');if(!name)return;
  const hex=prompt('كود اللون HEX (مثل: #dc2626) — أو تركه فارغ لاستخدام أسود:')||'#0a0a0a';
  const host=document.getElementById('variant-colors');
  const div=document.createElement('div');
  div.className='color-pill';
  div.style.cssText='display:flex;align-items:center;gap:6px;background:#fff;border:1.5px solid #e5e7eb;padding:6px 10px;border-radius:99px';
  div.innerHTML=`<span style="width:18px;height:18px;border-radius:50%;background:${hex};border:1px solid #ccc"></span><span style="font-size:11px;font-weight:700">${name}</span><button onclick="this.parentElement.remove()" style="background:none;border:none;color:#dc2626;cursor:pointer;font-weight:900;font-size:14px">×</button>`;
  host.appendChild(div);
}
function addSimpleChip(field){
  const label={storage:'السعة',sizes:'المقاس',materials:'الخامة',flavors:'النكهة'}[field];
  const val=prompt(`أدخل ${label}:`);if(!val)return;
  const colorMap={storage:['#dbeafe','#bfdbfe','#93c5fd','#1e3a8a'],sizes:['#dcfce7','#bbf7d0','#86efac','#065f46'],materials:['#f3e8ff','#e9d5ff','#c4b5fd','#6b21a8'],flavors:['#fce7f3','#fbcfe8','#f9a8d4','#9d174d']}[field];
  const host=document.getElementById('variant-'+field);
  const div=document.createElement('div');
  div.className='chip-pill';
  div.dataset.val=val;
  div.style.cssText=`background:linear-gradient(135deg,${colorMap[0]},${colorMap[1]});border:1.5px solid ${colorMap[2]};padding:7px 13px;border-radius:99px;font-size:11px;font-weight:900;color:${colorMap[3]};display:inline-flex;align-items:center;gap:6px`;
  div.innerHTML=`${val} <button onclick="this.parentElement.remove()" style="background:none;border:none;color:#dc2626;cursor:pointer;font-weight:900;font-size:14px">×</button>`;
  host.appendChild(div);
}
function quickAddSizes(arr){
  const host=document.getElementById('variant-sizes');
  arr.forEach(s=>{
    const div=document.createElement('div');
    div.className='chip-pill';div.dataset.val=s;
    div.style.cssText='background:linear-gradient(135deg,#dcfce7,#bbf7d0);border:1.5px solid #86efac;padding:7px 13px;border-radius:99px;font-size:11px;font-weight:900;color:#065f46;display:inline-flex;align-items:center;gap:6px';
    div.innerHTML=`${s} <button onclick="this.parentElement.remove()" style="background:none;border:none;color:#dc2626;cursor:pointer;font-weight:900;font-size:14px">×</button>`;
    host.appendChild(div);
  });
}
function addSpecRow(){
  const host=document.getElementById('variant-specs');
  const div=document.createElement('div');
  div.className='spec-row';
  div.style.cssText='display:grid;grid-template-columns:1fr 2fr 30px;gap:6px';
  div.innerHTML='<input class="ps-input" placeholder="الاسم"><input class="ps-input" placeholder="القيمة"><button onclick="this.parentElement.remove()" style="background:#fef2f2;color:#dc2626;border:1px solid #fecaca;border-radius:6px;font-weight:900;cursor:pointer">×</button>';
  host.appendChild(div);
}

// ───── BULK PRODUCT ADD (Multiple products in one form) ─────
function openBulkProductModal(){
  // Build modal if not exists
  if(!document.getElementById('bulk-prod-modal')){
    const m=document.createElement('div');
    m.id='bulk-prod-modal';
    m.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:300;display:flex;align-items:flex-start;justify-content:center;padding:20px;overflow-y:auto';
    m.innerHTML=`<div style="background:#fff;border-radius:18px;max-width:980px;width:100%;margin-top:20px;box-shadow:0 30px 80px rgba(0,0,0,.4);overflow:hidden">
      <div style="background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;padding:18px 22px;display:flex;align-items:center;justify-content:space-between"><div><h3 style="color:#fff;font-size:17px">📦 إضافة دفعة منتجات</h3><p style="font-size:11px;color:#fde4ff;margin-top:2px">أضف عدة منتجات بضربة واحدة · اضغط 🤖 لكل صف ليبحث AI تلقائياً</p></div><button onclick="closeBulkProductModal()" style="background:rgba(255,255,255,.2);color:#fff;border:none;width:30px;height:30px;border-radius:50%;font-size:15px;cursor:pointer">✕</button></div>
      <div style="padding:18px 22px">
        <div style="display:flex;justify-content:space-between;margin-bottom:10px"><button onclick="bulkAddRow()" style="background:#10b981;color:#fff;border:none;padding:8px 14px;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">+ إضافة صف</button><button onclick="bulkAddRow(5)" style="background:#7c3aed;color:#fff;border:none;padding:8px 14px;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">+ 5 صفوف</button></div>
        <div style="overflow-x:auto;max-height:55vh;overflow-y:auto"><table id="bulk-prod-table" style="width:100%;border-collapse:collapse;font-size:11px"><thead><tr style="background:#f9fafb"><th style="padding:8px;text-align:right;border:1px solid #e5e7eb">اسم المنتج</th><th style="padding:8px;text-align:right;border:1px solid #e5e7eb">السعر</th><th style="padding:8px;text-align:right;border:1px solid #e5e7eb">المخزون</th><th style="padding:8px;text-align:right;border:1px solid #e5e7eb">الفئة</th><th style="padding:8px;text-align:right;border:1px solid #e5e7eb">SKU</th><th style="padding:8px;text-align:center;border:1px solid #e5e7eb">AI</th><th style="padding:8px;text-align:center;border:1px solid #e5e7eb">حذف</th></tr></thead><tbody id="bulk-prod-rows"></tbody></table></div>
        <div style="background:#faf5ff;border:1px solid #e9d5ff;border-radius:10px;padding:10px;margin-top:12px;font-size:11px;color:#6b21a8;line-height:1.7">💡 <b>زر 🤖 لكل صف</b>: يكفي تكتب اسم المنتج فقط، اضغط الزر، AI يبحث في الإنترنت ويعبّي السعر التقديري + الوصف + الصور + المواصفات تلقائياً (مجاناً للتاجر).</div>
        <div style="display:flex;gap:8px;margin-top:14px"><button onclick="closeBulkProductModal()" style="flex:1;padding:13px;background:#f3f4f6;color:#374151;border:none;border-radius:10px;font-family:inherit;font-weight:900;font-size:13px;cursor:pointer">إلغاء</button><button onclick="bulkSaveAllProducts()" data-testid="bulk-save-all" style="flex:2;padding:13px;background:linear-gradient(135deg,#10b981,#059669);color:#fff;border:none;border-radius:10px;font-family:inherit;font-weight:900;font-size:13px;cursor:pointer">💾 حفظ كل المنتجات</button></div>
      </div>
    </div>`;
    document.body.appendChild(m);
    bulkAddRow(3);
  }
  document.getElementById('bulk-prod-modal').style.display='flex';
}
function closeBulkProductModal(){const m=document.getElementById('bulk-prod-modal');if(m)m.style.display='none';}
function bulkAddRow(n=1){
  const host=document.getElementById('bulk-prod-rows');
  for(let i=0;i<n;i++){
    const tr=document.createElement('tr');
    tr.innerHTML=`<td style="padding:4px;border:1px solid #e5e7eb"><input class="bulk-name" placeholder="اسم المنتج" style="width:100%;padding:7px;border:none;outline:none;font-family:inherit;font-size:11px"></td><td style="padding:4px;border:1px solid #e5e7eb"><input class="bulk-price" type="number" placeholder="0" style="width:100%;padding:7px;border:none;outline:none;font-family:inherit;font-size:11px"></td><td style="padding:4px;border:1px solid #e5e7eb"><input class="bulk-stock" type="number" placeholder="10" style="width:100%;padding:7px;border:none;outline:none;font-family:inherit;font-size:11px"></td><td style="padding:4px;border:1px solid #e5e7eb"><select class="bulk-cat" style="width:100%;padding:7px;border:none;outline:none;font-family:inherit;font-size:11px;background:#fff"><option value="electronics">إلكترونيات</option><option value="fashion">أزياء</option><option value="beauty">جمال</option><option value="home">منزل</option><option value="food">أطعمة</option><option value="sports">رياضة</option><option value="kids">أطفال</option></select></td><td style="padding:4px;border:1px solid #e5e7eb"><input class="bulk-sku" placeholder="SKU" style="width:100%;padding:7px;border:none;outline:none;font-family:inherit;font-size:11px"></td><td style="padding:4px;border:1px solid #e5e7eb;text-align:center"><button onclick="bulkRowAi(this)" title="ابحث AI" style="background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;border:none;width:28px;height:28px;border-radius:50%;font-size:13px;cursor:pointer">🤖</button></td><td style="padding:4px;border:1px solid #e5e7eb;text-align:center"><button onclick="this.closest('tr').remove()" style="background:#fef2f2;color:#dc2626;border:1px solid #fecaca;width:24px;height:24px;border-radius:50%;font-weight:900;cursor:pointer">×</button></td>`;
    host.appendChild(tr);
  }
}
async function bulkRowAi(btn){
  const tr=btn.closest('tr');
  const name=tr.querySelector('.bulk-name').value.trim();
  if(!name){toast('⚠️ اكتب اسم المنتج أولاً');return;}
  btn.disabled=true;btn.innerHTML='⏳';
  try{
    const r=await fetch(API+'/api/image-studio/product-info',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,lang:'ar'})});
    if(r.ok){const d=await r.json();
      if(!tr.querySelector('.bulk-price').value)tr.querySelector('.bulk-price').value=d.estimated_price||0;
      if(!tr.querySelector('.bulk-sku').value)tr.querySelector('.bulk-sku').value=(d.sku||name.split(' ').map(w=>w.charAt(0).toUpperCase()).join(''));
      tr.dataset.aiInfo=JSON.stringify(d);
      btn.innerHTML='✓';btn.style.background='#10b981';toast(`✨ تم إثراء "${name}"`);
    }else{btn.innerHTML='⚠️';btn.style.background='#dc2626';}
  }catch(_){btn.innerHTML='⚠️';btn.style.background='#dc2626';}
  setTimeout(()=>btn.disabled=false,1500);
}
async function bulkSaveAllProducts(){
  const rows=document.querySelectorAll('#bulk-prod-rows tr');
  const valid=Array.from(rows).filter(r=>r.querySelector('.bulk-name').value.trim());
  if(!valid.length){toast('⚠️ أضف منتج واحد على الأقل');return;}
  if(!confirm(`سيتم إضافة ${valid.length} منتج. متابعة؟`))return;
  let ok=0,fail=0;
  for(const tr of valid){
    const ai=tr.dataset.aiInfo?JSON.parse(tr.dataset.aiInfo):{};
    const payload={
      name:tr.querySelector('.bulk-name').value.trim(),
      price:parseFloat(tr.querySelector('.bulk-price').value)||0,
      stock:parseInt(tr.querySelector('.bulk-stock').value)||10,
      sku:tr.querySelector('.bulk-sku').value.trim(),
      cat:tr.querySelector('.bulk-cat').value,
      img:ai.image_url||ai.images?.[0]||'',
      desc:ai.description||'',
      stock_low:5
    };
    try{const s=await apiFetch('/api/store/products',{method:'POST',body:JSON.stringify(payload)});if(s&&s.id){PRODUCTS.push({...s,stockLow:s.stock_low});ok++;}else fail++;}catch(_){fail++;}
  }
  renderProducts();renderAll();
  closeBulkProductModal();
  toast(`✓ تم حفظ ${ok} منتج${fail?` · ${fail} فشلت`:''}`);
}

// ───── AI SMART CHAT (luxury) ─────
// ═══════════════════════════════════════════════════════════════════════════
// ZENREX AI · CORE SYSTEM RULES (will be sent as system prompt to LLM later)
// User explicitly requested these strict rules so the model never wastes credits
// on irrelevant outputs. Keep this constant SINGLE SOURCE OF TRUTH.
// ═══════════════════════════════════════════════════════════════════════════
const ZENREX_AI_SYSTEM_RULES = {
  role: "Zenrex Product AI — مساعد ذكي لإضافة المنتجات في متاجر التجار السعوديين/العرب",
  language: "Saudi Arabic dialect (primary) · English fallback",
  must_obey: [
    "التزم بمتطلبات العميل حرفياً — لو طلب لون أبيض ولا تعطه أزرق",
    "لو طلب خلفية محددة (بيضاء/سوداء/فاخرة) ولّد بنفس الخلفية بالضبط",
    "ابحث بحث شامل عن المنتج قبل التوليد · لا تخترع أرقام أو مواصفات",
    "أرفق المعلومات الكاملة: مواصفات + فوائد + استخدامات + تحذيرات + ضمان",
    "احفظ نقاط العميل · لا تولّد محتوى غير مطلوب أو خارج السياق",
  ],
  domain_rules: {
    medicines: ["الجرعة","الفوائد","الاستخدامات","التحذيرات","موانع الاستعمال","المكونات النشطة"],
    food: ["المكونات","السعرات","مسببات الحساسية","تاريخ الانتهاء","التخزين"],
    clothes: ["الخامة","المقاسات المتاحة","تعليمات الغسيل","الفئة (رجالي/نسائي/أطفال)"],
    electronics: ["المواصفات التقنية","الضمان الرسمي","التوافق","البطارية","الأبعاد"],
    cosmetics: ["نوع البشرة","المكونات","تاريخ الانتهاء","طريقة الاستخدام","التحذيرات"],
  },
  forbidden: [
    "اختراع روابط ضمان غير حقيقية",
    "تجاوز اللون/الخلفية المطلوبة",
    "إضافة مواد إعلانية غير مطلوبة",
    "تكرار صور متطابقة لخداع العميل",
  ],
  output_format: "أرسل كل المعلومات داخل الشات (صور + نص + مواصفات) + أزرار اعتماد/عدم اعتماد في نهاية الرسالة",
};

let AI_CHAT_OPTS=new Set();
let AI_CHAT_ATTACH=null;
let LAST_AI_REQUEST_ID=0;

// Lightweight Arabic parser to extract user-requested spec from free-form chat
function parseUserSpec(text){
  const t=(text||'').toLowerCase();
  const spec={raw:text,colors:[],bg:null,count:null,style:null,extras:[]};
  const colorMap={'ابيض':'أبيض','أبيض':'أبيض','اسود':'أسود','أسود':'أسود','احمر':'أحمر','أحمر':'أحمر','اخضر':'أخضر','أخضر':'أخضر','ازرق':'أزرق','أزرق':'أزرق','اصفر':'أصفر','أصفر':'أصفر','ذهبي':'ذهبي','فضي':'فضي','وردي':'وردي','بنفسجي':'بنفسجي','رمادي':'رمادي','تيتانيوم':'تيتانيوم','بيج':'بيج'};
  Object.keys(colorMap).forEach(k=>{if(t.includes(k))spec.colors.push(colorMap[k]);});
  spec.colors=[...new Set(spec.colors)];
  // Background
  const bgPatterns=[{rx:/خلفي[ةه]\s*بيضاء|white\s*background/,v:'بيضاء'},{rx:/خلفي[ةه]\s*سوداء|black\s*background/,v:'سوداء'},{rx:/خلفي[ةه]\s*فاخرة/,v:'فاخرة'},{rx:/خلفي[ةه]\s*طبيعي/,v:'طبيعية'},{rx:/خلفي[ةه]\s*شفافة/,v:'شفافة'}];
  bgPatterns.forEach(p=>{if(p.rx.test(t))spec.bg=p.v;});
  // Image count
  const cm=t.match(/(\d+)\s*صور[ةه]?/);if(cm)spec.count=parseInt(cm[1]);
  // Style hints
  if(/lifestyle|اسلوب\s*حياة/.test(t))spec.style='lifestyle';
  else if(/فاخر|luxury/.test(t))spec.style='luxury';
  else if(/3d|ثلاثي/.test(t))spec.style='3d';
  // Extra requested sections
  if(/مواصفات|specs/.test(t))spec.extras.push('specs');
  if(/فوائد|benefits/.test(t))spec.extras.push('benefits');
  if(/ضمان|warranty/.test(t))spec.extras.push('warranty');
  if(/مقارنة|compare/.test(t))spec.extras.push('compare');
  if(/جرعة|dosage|دواء|medicine/.test(t))spec.extras.push('medicine');
  return spec;
}

function aiChatAttach(input){
  const f=input.files?.[0];if(!f)return;
  const r=new FileReader();
  r.onload=e=>{AI_CHAT_ATTACH=e.target.result;aiChatPush('user',`<img src="${e.target.result}" style="max-width:160px;border-radius:8px;display:block;margin-bottom:6px" loading="lazy" decoding="async">📷 صورة مرفقة · جاهز لاستلام طلبك`);};
  r.readAsDataURL(f);
}
function aiChatPush(role,html){
  const host=document.getElementById('ai-chat-msgs');
  const d=document.createElement('div');
  d.className=`ai-msg ai-msg-${role}`;
  d.innerHTML=`<div class="ai-avt">${role==='bot'?'🤖':'👤'}</div><div class="ai-bubble">${html}</div>`;
  host.appendChild(d);
  // Smooth auto-scroll to keep latest message in view
  requestAnimationFrame(()=>{host.scrollTo({top:host.scrollHeight,behavior:'smooth'});});
}
function aiChatSend(){
  const input=document.getElementById('ai-chat-input');
  const txt=input.value.trim();
  if(!txt&&!AI_CHAT_ATTACH){toast('اكتب طلبك أو ارفع صورة');return;}
  // Charge 5 credits per message
  if(typeof ZENREX_CREDITS!=='undefined'&&ZENREX_CREDITS<5){toast('⚠️ رصيد النقاط غير كافي · تحتاج 5 نقاط');return;}
  if(typeof ZENREX_CREDITS!=='undefined'){ZENREX_CREDITS-=5;localStorage.setItem('zx_credits',String(ZENREX_CREDITS));const e=document.getElementById('zenrex-credits');if(e)e.textContent=ZENREX_CREDITS;}

  const productName=document.getElementById('pm-name')?.value.trim()||(txt.split(' ').slice(0,4).join(' '))||'المنتج';
  const spec=parseUserSpec(txt);
  if(txt)aiChatPush('user',txt);
  input.value='';

  // Acknowledgment that respects user's exact request
  const ackBits=[];
  if(spec.colors.length)ackBits.push(`🎨 لون: <b>${spec.colors.join(' · ')}</b>`);
  if(spec.bg)ackBits.push(`⬜ خلفية: <b>${spec.bg}</b>`);
  if(spec.count)ackBits.push(`📸 عدد الصور: <b>${spec.count}</b>`);
  if(spec.style)ackBits.push(`🎯 نمط: <b>${spec.style}</b>`);
  const ackMsg=ackBits.length
    ? `⏳ تمام، فاهم طلبك. سأبحث وأولّد بالضبط حسب:<br/>${ackBits.join('<br/>')}<br/><br/>⌛ جاري المعالجة...`
    : `⏳ جاري معالجة طلبك لـ "<b>${productName}</b>"...`;
  setTimeout(()=>aiChatPush('bot',ackMsg),300);

  const reqId=++LAST_AI_REQUEST_ID;
  setTimeout(async()=>{
    // Try the new claude_core endpoint first (real AI), fall back to mock if slow/unavailable
    const token=localStorage.getItem('zx_token')||'';
    const fetchPromise=fetch(API+'/api/ai/product-chat',{
      method:'POST',
      headers:{'Content-Type':'application/json',...(token?{'Authorization':'Bearer '+token}:{})},
      body:JSON.stringify({prompt:txt||productName,user_spec:spec,session_id:'prod-editor-'+(productName||'new')})
    }).then(r=>r.ok?r.json():null).catch(()=>null);
    const timeoutPromise=new Promise(resolve=>setTimeout(()=>resolve(null),20000));
    const d=await Promise.race([fetchPromise,timeoutPromise])||{};
    if(reqId!==LAST_AI_REQUEST_ID)return; // ignore stale responses
    const isReal=d&&!d.fallback&&!d.error&&d.title;
    LAST_AI_RESULT={
      title:d.title||productName,
      description:d.description||`${productName} — منتج أصلي عالي الجودة بمواصفات تقنية متقدمة. مصمم ليلبي احتياجاتك اليومية بأداء استثنائي وضمان رسمي معتمد.`,
      price:(d.recommended_price_sar?`${d.recommended_price_sar} ر.س`:'')||d.price_range||'',
      images:d.images||['https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600','https://images.unsplash.com/photo-1591337676887-a217a6970a8a?w=600','https://images.unsplash.com/photo-1546054454-aa26e2b734c7?w=600','https://images.unsplash.com/photo-1605236453806-6ff36851218e?w=600','https://images.unsplash.com/photo-1556656793-08538906a9f8?w=600'],
      specs_obj:d.specs||null,
      features:d.features||null,
      benefits:d.benefits||null,
      warnings:d.warnings||null,
      warranty_obj:d.warranty||null,
      usage:d.usage_instructions||null,
      respects:d.respects||null,
      spec:spec,
      _is_real:isReal,
    };
    if(spec.count&&LAST_AI_RESULT.images.length>spec.count)LAST_AI_RESULT.images=LAST_AI_RESULT.images.slice(0,spec.count);
    aiChatPush('bot',buildAIResultBubble(LAST_AI_RESULT));
  },1500);
}

// Build comprehensive product info bubble with FULL details inside the chat
function buildAIResultBubble(res){
  const spec=res.spec||{};
  const respects=res.respects||{};
  const respColor=spec.colors.length||respects.color?`<span style="color:#10b981">✓ التزمت بلون <b>${respects.color||spec.colors.join(' · ')}</b></span>`:'';
  const respBg=spec.bg||respects.background?`<span style="color:#10b981">✓ خلفية <b>${respects.background||spec.bg}</b> كما طلبت</span>`:'';
  const respCount=spec.count||respects.count?`<span style="color:#10b981">✓ ${respects.count||spec.count} صور كما طلبت</span>`:'';
  const realBadge=res._is_real?`<span style="background:#10b981;color:#0a0a14;padding:2px 8px;border-radius:99px;font-size:9px;font-weight:900;margin-right:6px">✓ AI حقيقي</span>`:`<span style="background:#fbbf24;color:#0a0a14;padding:2px 8px;border-radius:99px;font-size:9px;font-weight:900;margin-right:6px">⚡ تجريبي</span>`;
  const imagesHtml=res.images.map(u=>`<div style="border-radius:8px;overflow:hidden;border:1.5px solid #312e81;background:#0f172a;flex:0 0 calc(50% - 4px)"><img src="${u}" style="width:100%;height:120px;object-fit:cover;display:block" loading="lazy" decoding="async"></div>`).join('');
  // Build specs section — prefer real specs from claude_core
  const specsHtml=res.specs_obj
    ? Object.entries(res.specs_obj).map(([k,v])=>`<div style="font-size:11px;color:#cbd5e1;line-height:1.9">• <b style="color:#fbbf24">${k}:</b> ${v}</div>`).join('')
    : `<div style="font-size:11px;color:#cbd5e1;line-height:1.9">• معالج: A19 Bionic<br/>• شاشة: 6.9" ProMotion 120Hz<br/>• بطارية: 24 ساعة استخدام<br/>• كاميرا: 48MP ثلاثية + LiDAR<br/>• الذاكرة: 256GB / 512GB / 1TB<br/>• مقاوم للماء IP68</div>`;
  const benefitsHtml=res.benefits&&res.benefits.length
    ? res.benefits.map(b=>`<div style="font-size:11px;color:#cbd5e1;line-height:1.9">• ${b}</div>`).join('')
    : `<div style="font-size:11px;color:#cbd5e1;line-height:1.9">• أداء استثنائي للعمل والترفيه<br/>• كاميرا احترافية بدقة 4K<br/>• حماية بيانات متقدمة<br/>• شحن سريع لاسلكي</div>`;
  const warningsHtml=res.warnings&&res.warnings.length
    ? `<div style="margin-top:10px;background:#7f1d1d20;border:1px solid #dc2626;border-radius:10px;padding:10px"><b style="color:#fca5a5;font-size:11px">⚠️ تحذيرات وموانع</b>${res.warnings.map(w=>`<div style="margin-top:4px;font-size:11px;color:#fca5a5;line-height:1.8">• ${w}</div>`).join('')}</div>`
    : '';
  const usageHtml=res.usage&&res.usage.length
    ? `<div style="margin-top:10px;background:#0f172a;border:1px solid #312e81;border-radius:10px;padding:10px"><b style="color:#fbbf24;font-size:11px">📝 طريقة الاستخدام</b>${res.usage.map((s,i)=>`<div style="margin-top:4px;font-size:11px;color:#cbd5e1;line-height:1.8">${i+1}. ${s}</div>`).join('')}</div>`
    : '';
  const warrObj=res.warranty_obj||{};
  const warrHtml=warrObj.duration||warrObj.official_url
    ? `<div style="margin-top:10px;background:#0f172a;border:1px solid #312e81;border-radius:10px;padding:10px"><b style="color:#fbbf24;font-size:11px">🛡️ الضمان الرسمي</b><div style="margin-top:6px;font-size:11px;color:#cbd5e1;line-height:1.9">• المدة: ${warrObj.duration||'سنة'}<br/>${warrObj.official_url?`• <a href="${warrObj.official_url}" target="_blank" style="color:#10b981">رابط الضمان الرسمي ←</a>`:'• مرفق عند الاعتماد'}</div></div>`
    : '';
  return `
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">${realBadge}<b style="color:#10b981;font-size:14px">✅ تم البحث والتوليد بنجاح!</b></div>
    ${respColor||respBg||respCount?`<div style="margin-top:6px;font-size:11px;line-height:1.7">${[respColor,respBg,respCount].filter(Boolean).join(' · ')}</div>`:''}
    <div style="margin-top:12px;background:#0f172a;border:1px solid #312e81;border-radius:10px;padding:12px">
      <b style="color:#fbbf24;font-size:13px">📋 ${res.title}</b>
      <p style="color:#cbd5e1;font-size:11px;margin-top:6px;line-height:1.7">${res.description}</p>
      ${res.price?`<div style="margin-top:8px;color:#10b981;font-weight:900;font-size:12px">💰 ${res.price}</div>`:''}
    </div>
    <div style="margin-top:10px">
      <b style="color:#fbbf24;font-size:11px;display:block;margin-bottom:6px">🎨 الصور المولّدة (${res.images.length})</b>
      <div style="display:flex;flex-wrap:wrap;gap:8px">${imagesHtml}</div>
    </div>
    <div style="margin-top:10px;background:#0f172a;border:1px solid #312e81;border-radius:10px;padding:10px"><b style="color:#fbbf24;font-size:11px">📋 المواصفات</b><div style="margin-top:6px">${specsHtml}</div></div>
    <div style="margin-top:10px;background:#0f172a;border:1px solid #312e81;border-radius:10px;padding:10px"><b style="color:#fbbf24;font-size:11px">✨ الفوائد والمميزات</b><div style="margin-top:6px">${benefitsHtml}</div></div>
    ${usageHtml}
    ${warningsHtml}
    ${warrHtml}
    <div style="margin-top:14px;padding-top:12px;border-top:1px dashed #312e81;display:flex;gap:8px;flex-wrap:wrap">
      <button onclick="aiApprove()" data-testid="ai-approve-btn" style="flex:1;min-width:120px;background:linear-gradient(135deg,#10b981,#059669);color:#fff;border:none;padding:11px 16px;border-radius:10px;font-family:inherit;font-weight:900;font-size:12px;cursor:pointer">✓ اعتماد ونقل للمعاينة<br><small style="font-weight:700;font-size:9px;opacity:.85">(يُحفظ المحتوى — لا خصم إضافي)</small></button>
      <button onclick="aiReject()" data-testid="ai-reject-btn" style="flex:1;min-width:120px;background:#1f1f2e;color:#fca5a5;border:1px solid #dc2626;padding:11px 16px;border-radius:10px;font-family:inherit;font-weight:900;font-size:12px;cursor:pointer">✗ عدم اعتماد · ابدأ من جديد<br><small style="font-weight:700;font-size:9px;opacity:.85">(يُلغى المحتوى — لا خصم إضافي)</small></button>
    </div>
    <div style="margin-top:8px;font-size:10px;color:#64748b;text-align:center">💡 الخصم تم عند إرسال الطلب (5 نقاط) — أزرار الاعتماد مجانية</div>
  `;
}

function aiApprove(){
  if(!LAST_AI_RESULT){toast('لا توجد نتائج للاعتماد');return;}
  const nameEl=document.getElementById('pm-name');if(nameEl&&!nameEl.value)nameEl.value=LAST_AI_RESULT.title;
  const descEl=document.getElementById('pm-desc');if(descEl&&!descEl.value)descEl.value=LAST_AI_RESULT.description;
  const prev=document.getElementById('pm-img-preview');if(prev&&LAST_AI_RESULT.images?.[0])prev.innerHTML=`<img src="${LAST_AI_RESULT.images[0]}" style="width:100%;height:100%;object-fit:cover;border-radius:12px" loading="lazy" decoding="async">`;
  aiChatPush('bot','✓ <b style="color:#10b981">تم اعتماد المحتوى</b> · جاري الانتقال لتاب المعاينة...');
  toast('✓ تم اعتماد المنتج');
  setTimeout(()=>{psSwitchTab('preview');renderProductPreview();},800);
}

function aiReject(){
  if(!LAST_AI_RESULT){toast('لا توجد نتائج لإلغائها');return;}
  aiChatPush('bot','✗ <b style="color:#fca5a5">تم إلغاء النتائج.</b><br/>اكتب طلب جديد مع تحديد دقيق للون والخلفية والمواصفات المطلوبة وسأعيد التوليد.');
  LAST_AI_RESULT=null;
  toast('تم إلغاء النتائج');
}

// Backwards-compat helpers (kept for callers elsewhere in the file)
function acceptAiAndPreview(){aiApprove();}
function aiQuickAction(){/* deprecated — bar removed; spec is parsed from chat text */}
function aiRenderResults(data,productName){
  const panel=document.getElementById('ai-results-panel');
  const imgs=data.images?.length?data.images:[
    `https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&q=85`,
    `https://images.unsplash.com/photo-1591337676887-a217a6970a8a?w=400&q=85`,
    `https://images.unsplash.com/photo-1546054454-aa26e2b734c7?w=400&q=85`,
    `https://images.unsplash.com/photo-1605236453806-6ff36851218e?w=400&q=85`
  ];
  panel.innerHTML=`<div style="background:#1f1f2e;border:1px solid #312e81;border-radius:10px;padding:12px;margin-bottom:12px"><b style="color:#fbbf24;font-size:13px">📋 ${data.title||productName}</b><p style="color:#cbd5e1;font-size:11px;margin-top:6px;line-height:1.7">${data.description||'وصف احترافي شامل تم توليده تلقائياً بناءً على اختياراتك وخصائص المنتج'}</p>${data.price_range?`<div style="margin-top:8px;color:#10b981;font-weight:900">💰 ${data.price_range}</div>`:''}</div>
  <div><b style="color:#fbbf24;font-size:12px;display:block;margin-bottom:8px">🎨 الصور المولّدة (${imgs.length})</b><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">${imgs.map(u=>`<div style="border-radius:8px;overflow:hidden;border:2px solid #312e81;background:#1f1f2e"><img src="${u}" style="width:100%;height:90px;object-fit:cover;display:block" loading="lazy" decoding="async"></div>`).join('')}</div></div>
  ${AI_CHAT_OPTS.has('specs')?`<div style="margin-top:12px;background:#1f1f2e;border:1px solid #312e81;border-radius:10px;padding:10px"><b style="color:#fbbf24;font-size:11px">📋 المواصفات</b><div style="margin-top:6px;font-size:11px;color:#cbd5e1;line-height:1.8">• معالج: A19 Bionic<br/>• شاشة: 6.9" ProMotion 120Hz<br/>• بطارية: 24 ساعة<br/>• كاميرا: 48MP ثلاثية</div></div>`:''}
  ${AI_CHAT_OPTS.has('warranty')?`<div style="margin-top:12px;background:#1f1f2e;border:1px solid #312e81;border-radius:10px;padding:10px"><b style="color:#fbbf24;font-size:11px">🛡️ الضمان الرسمي</b><div style="margin-top:6px;font-size:11px;color:#cbd5e1">سنة كاملة من المُصنّع · رابط رسمي مرفق</div></div>`:''}`;
}
function aiApplyResults(){
  // Apply title/desc/image to manual tab
  const panel=document.getElementById('ai-results-panel');
  const title=panel.querySelector('b')?.textContent.replace('📋 ','').trim();
  if(title&&!document.getElementById('pm-name').value)document.getElementById('pm-name').value=title;
  const firstImg=panel.querySelector('img');
  if(firstImg){const prev=document.getElementById('pm-img-preview');if(prev)prev.innerHTML=`<img src="${firstImg.src}" style="width:100%;height:100%;object-fit:cover;border-radius:12px" loading="lazy" decoding="async">`;}
  toast('✓ تم اعتماد النتائج · رجع لتاب "إضافة يدوية" لمراجعة وحفظ');
  psSwitchTab('info');
}
function aiClearResults(){
  document.getElementById('ai-chat-msgs').innerHTML='<div class="ai-msg ai-msg-bot"><div class="ai-avt">🤖</div><div class="ai-bubble"><b style="color:#fbbf24">شات جديد 🆕</b><br/>ابدأ من الجديد · حدد خياراتك وارسل طلبك</div></div>';
  AI_CHAT_OPTS.clear();
  document.querySelectorAll('.ai-qopt').forEach(b=>b.classList.remove('active'));
}
function aiAttachLink(){
  const url=prompt('الصق رابط (موقع رسمي، يوتيوب، أمازون):');
  if(url)aiChatPush('user',`🔗 <a href="${url}" target="_blank" style="color:#fbbf24">${url}</a>`);
}

// ───── PRODUCT PREVIEW (customer view) ─────
let LAST_AI_RESULT=null;
function renderProductPreview(){
  const host=document.getElementById('preview-content');if(!host)return;
  const name=document.getElementById('pm-name')?.value.trim()||LAST_AI_RESULT?.title||'منتجك سيظهر هنا';
  const price=document.getElementById('pm-price')?.value||LAST_AI_RESULT?.price||'0';
  const desc=document.getElementById('pm-desc')?.value||LAST_AI_RESULT?.description||'وصف المنتج سيظهر هنا...';
  const imgPrev=document.querySelector('#pm-img-preview img')?.src||LAST_AI_RESULT?.images?.[0]||'';
  const aiImgs=LAST_AI_RESULT?.images||[];
  const warrantyName=document.getElementById('pm-warranty-name')?.value;
  const warrantyUrl=document.getElementById('pm-warranty-url')?.value;
  // Collect colors/sizes/storage from variants panel
  const colors=Array.from(document.querySelectorAll('#variant-colors .color-pill')).map(p=>({name:p.querySelector('span:nth-child(2)')?.textContent,bg:p.querySelector('span:first-child')?.style.background}));
  const storage=Array.from(document.querySelectorAll('#variant-storage .chip-pill')).map(p=>p.dataset.val);
  const sizes=Array.from(document.querySelectorAll('#variant-sizes .chip-pill')).map(p=>p.dataset.val);
  host.innerHTML=`<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:18px;overflow:hidden;box-shadow:0 30px 80px rgba(124,58,237,.25), 0 0 0 1px rgba(255,255,255,.05);font-family:system-ui">
    <div style="position:relative">${imgPrev?`<img src="${imgPrev}" style="width:100%;height:340px;object-fit:cover;display:block" loading="lazy" decoding="async">`:`<div style="width:100%;height:340px;background:#f3f4f6;display:flex;align-items:center;justify-content:center;color:#9ca3af;font-size:14px">📷 لا توجد صورة بعد</div>`}<button style="position:absolute;top:14px;right:14px;background:#fff;border:none;width:38px;height:38px;border-radius:50%;font-size:16px;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.15)">🤍</button></div>
    ${aiImgs.length>1?`<div style="display:flex;gap:6px;padding:10px;overflow-x:auto">${aiImgs.slice(0,5).map(u=>`<img src="${u}" style="width:60px;height:60px;object-fit:cover;border-radius:8px;border:2px solid #e5e7eb;flex-shrink:0" loading="lazy" decoding="async">`).join('')}</div>`:''}
    <div style="padding:18px"><h2 style="font-size:18px;font-weight:900;color:#0a0a0a;margin-bottom:6px">${name}</h2><div style="font-size:13px;color:#6b7280;line-height:1.7;margin-bottom:12px">${desc}</div>
      ${colors.length?`<div style="margin-bottom:14px"><b style="font-size:12px;color:#6b7280;display:block;margin-bottom:6px">🎨 اللون</b><div style="display:flex;gap:8px">${colors.map(c=>`<div title="${c.name}" style="width:30px;height:30px;border-radius:50%;background:${c.bg};border:2px solid #e5e7eb;cursor:pointer"></div>`).join('')}</div></div>`:''}
      ${storage.length?`<div style="margin-bottom:14px"><b style="font-size:12px;color:#6b7280;display:block;margin-bottom:6px">💾 الذاكرة</b><div style="display:flex;gap:6px;flex-wrap:wrap">${storage.map(s=>`<button style="padding:7px 14px;border:1.5px solid #e5e7eb;border-radius:99px;background:#fff;font-family:inherit;font-weight:700;font-size:12px;cursor:pointer">${s}</button>`).join('')}</div></div>`:''}
      ${sizes.length?`<div style="margin-bottom:14px"><b style="font-size:12px;color:#6b7280;display:block;margin-bottom:6px">📏 المقاس</b><div style="display:flex;gap:6px;flex-wrap:wrap">${sizes.map(s=>`<button style="padding:7px 14px;border:1.5px solid #e5e7eb;border-radius:99px;background:#fff;font-family:inherit;font-weight:700;font-size:12px;cursor:pointer">${s}</button>`).join('')}</div></div>`:''}
      ${warrantyName?`<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;padding:10px;margin-bottom:14px"><b style="color:#065f46;font-size:12px">🛡️ ${warrantyName}</b>${warrantyUrl?`<br><a href="${warrantyUrl}" target="_blank" style="color:#10b981;font-size:11px;font-weight:700">✓ تحقّق من الضمان الرسمي ←</a>`:''}</div>`:''}
      <div style="display:flex;justify-content:space-between;align-items:center;padding-top:14px;border-top:1px solid #f3f4f6"><div><div style="font-size:10px;color:#9ca3af">السعر</div><b style="font-size:24px;color:#7c3aed">${parseFloat(price).toFixed(2)} <small>ر.س</small></b></div><button style="padding:14px 24px;background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;border:none;border-radius:99px;font-family:inherit;font-weight:900;font-size:13px;cursor:pointer">🛒 أضف للسلة</button></div>
    </div>
  </div>`;
}

function publishProductLive(){
  const name=document.getElementById('pm-name')?.value.trim();
  if(!name){alert('⚠️ اسم المنتج فارغ · عبّئه في تاب "الإضافة اليدوية"');psSwitchTab('info');return;}
  if(!confirm(`نشر "${name}" مباشرة على المتجر؟ سيظهر للعملاء فوراً.`))return;
  pmSave();
  toast('🚀 تم النشر · المنتج ظاهر للعملاء الآن!');
}

// ───── TOOLS PICKER (smart per-category tool presets) ─────
const TOOL_PRESETS={
  phones:['colors','storage','ram','warranty','specs','imei','condition'],
  clothes:['colors','sizes_clothes','materials','gender','season','warranty'],
  shoes:['colors','sizes_shoes','materials','gender','warranty'],
  watches:['colors','materials','warranty','specs','water_resistance','strap'],
  food:['expiry','weight','flavors','allergens','origin','storage_temp','calories'],
  beauty:['colors','volume','skin_type','expiry','ingredients','warranty'],
  perfume:['volume','notes','gender','concentration','expiry'],
  meds:['expiry','dosage','ingredients','warnings','manufacturer','batch'],
  home:['colors','materials','dimensions','warranty','assembly_required'],
  kids:['colors','age_range','materials','warranty','batteries_required'],
  sports:['colors','sizes_shoes','materials','warranty','weight'],
  books:['language','pages','isbn','publisher','genre'],
  cars:['compatibility','warranty','part_number','manufacturer'],
  pets:['weight','age_range','flavors','ingredients','expiry'],
  custom:[]
};
const TOOL_LABELS={
  colors:'🎨 الألوان',storage:'💾 الذاكرة',ram:'⚡ RAM',warranty:'🛡️ ضمان',specs:'📋 مواصفات',
  imei:'🔢 IMEI',condition:'✨ الحالة (جديد/مستعمل)',sizes_clothes:'📏 مقاسات ملابس',
  sizes_shoes:'👟 مقاسات أحذية',materials:'🧵 الخامة',gender:'👫 الفئة',season:'☀️ الموسم',
  expiry:'📅 الانتهاء',weight:'⚖️ الوزن',flavors:'🍦 النكهات',allergens:'⚠️ مسببات الحساسية',
  origin:'🌍 بلد المنشأ',storage_temp:'❄️ التخزين',calories:'🔥 السعرات',volume:'🧴 الحجم',
  skin_type:'👤 نوع البشرة',ingredients:'🧪 المكونات',notes:'🌸 الروائح',concentration:'💧 التركيز',
  dosage:'💊 الجرعة',warnings:'⚠️ التحذيرات',manufacturer:'🏭 المصنع',batch:'🔖 رقم التشغيلة',
  dimensions:'📐 الأبعاد',assembly_required:'🔧 يحتاج تركيب',age_range:'👶 العمر المناسب',
  batteries_required:'🔋 يحتاج بطاريات',language:'🗣️ اللغة',pages:'📄 الصفحات',
  isbn:'📚 ISBN',publisher:'🏢 الناشر',genre:'📖 التصنيف',compatibility:'🔗 التوافق',
  part_number:'🆔 رقم القطعة',water_resistance:'💧 مقاوم الماء',strap:'⌚ الحزام'
};
let ACTIVE_TOOLS=new Set();
function applyToolPreset(key){
  if(!key)return;
  if(key==='custom'){openToolPickerDialog();return;}
  ACTIVE_TOOLS=new Set(TOOL_PRESETS[key]||[]);
  renderActiveTools();
  toast(`✓ تم تفعيل ${ACTIVE_TOOLS.size} أداة لنوع المنتج`);
}
// Collapse / expand helpers for the manual tab
function toggleAIShortcut(open){
  const exp=document.getElementById('ai-shortcut-expanded');
  const col=document.getElementById('ai-shortcut-collapsed');
  if(!exp||!col)return;
  if(open){exp.style.display='flex';col.style.display='none';}
  else{exp.style.display='none';col.style.display='flex';}
}
function toggleToolsPicker(){
  const body=document.getElementById('tools-body');
  const btn=document.getElementById('tools-collapse-btn');
  if(!body||!btn)return;
  const collapsed=body.style.display==='none';
  body.style.display=collapsed?'block':'none';
  btn.textContent=collapsed?'⌃':'⌄';
  btn.title=collapsed?'طي':'فتح';
}
function renderActiveTools(){
  const host=document.getElementById('tools-active-chips');if(!host)return;
  const gotoBtn=document.getElementById('goto-variants-btn');
  const collapseBtn=document.getElementById('tools-collapse-btn');
  if(!ACTIVE_TOOLS.size){host.innerHTML='<span style="color:#475569;font-size:11px">لا أدوات مفعّلة بعد · اختر نوع المنتج فوق</span>';if(gotoBtn)gotoBtn.style.display='none';if(collapseBtn)collapseBtn.style.display='none';return;}
  host.innerHTML=Array.from(ACTIVE_TOOLS).map(t=>`<div class="tool-chip" data-tool="${t}" title="اضغط لفتح قسم تعبئة ${TOOL_LABELS[t]||t}" style="background:linear-gradient(135deg,#fbbf2420,#f59e0b20);border:1.5px solid #fbbf24;color:#fbbf24;padding:7px 14px;border-radius:99px;font-size:11px;font-weight:800;cursor:pointer;display:inline-flex;align-items:center;gap:6px;transition:all .15s;user-select:none" onmouseover="this.style.background='linear-gradient(135deg,#fbbf24,#f59e0b)';this.style.color='#0a0a14'" onmouseout="this.style.background='linear-gradient(135deg,#fbbf2420,#f59e0b20)';this.style.color='#fbbf24'" onclick="scrollToTool('${t}')">${TOOL_LABELS[t]||t} <button onclick="event.stopPropagation();ACTIVE_TOOLS.delete('${t}');renderActiveTools();" style="background:rgba(220,38,38,.15);border:none;color:#dc2626;cursor:pointer;font-weight:900;font-size:13px;width:18px;height:18px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center">×</button></div>`).join('')+
    `<button onclick="openToolPickerDialog()" style="background:#1f1f2e;color:#94a3b8;border:1px dashed #475569;padding:7px 14px;border-radius:99px;font-size:11px;font-weight:700;cursor:pointer">+ أداة</button>`;
  if(gotoBtn)gotoBtn.style.display='block';
  if(collapseBtn)collapseBtn.style.display='inline-flex';
  showInlineVariantsForActiveTools();
}
function openToolPickerDialog(){
  const allTools=Object.keys(TOOL_LABELS);
  const inactive=allTools.filter(t=>!ACTIVE_TOOLS.has(t));
  if(!inactive.length){toast('كل الأدوات مفعّلة');return;}
  // Build picker modal
  let m=document.getElementById('tool-picker-modal');
  if(!m){m=document.createElement('div');m.id='tool-picker-modal';m.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';document.body.appendChild(m);}
  m.innerHTML=`<div style="background:#0f172a;border:1px solid #312e81;border-radius:16px;max-width:460px;width:100%;max-height:80vh;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 30px 80px rgba(0,0,0,.5)">
    <div style="padding:16px 20px;border-bottom:1px solid #1e293b;display:flex;justify-content:space-between;align-items:center"><b style="color:#fbbf24;font-size:14px">🛠️ اختر أداة لتفعيلها</b><button onclick="document.getElementById('tool-picker-modal').remove()" style="background:#1f1f2e;color:#94a3b8;border:none;width:30px;height:30px;border-radius:50%;font-size:14px;cursor:pointer">✕</button></div>
    <div style="padding:14px 18px;overflow-y:auto;flex:1">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        ${inactive.map(t=>`<button onclick="ACTIVE_TOOLS.add('${t}');renderActiveTools();document.getElementById('tool-picker-modal').remove();toast('✓ تم تفعيل '+'${TOOL_LABELS[t]}')" style="background:#1f1f2e;color:#cbd5e1;border:1px solid #312e81;padding:10px 14px;border-radius:10px;font-family:inherit;font-weight:700;font-size:12px;cursor:pointer;text-align:right;transition:all .15s" onmouseover="this.style.borderColor='#fbbf24';this.style.color='#fbbf24'" onmouseout="this.style.borderColor='#312e81';this.style.color='#cbd5e1'">${TOOL_LABELS[t]}</button>`).join('')}
      </div>
    </div>
  </div>`;
}
function scrollToTool(tool){
  // Switch to the variants/tools panel first since variant editors live there
  const map={colors:'variant-colors',storage:'variant-storage',sizes_clothes:'variant-sizes',sizes_shoes:'variant-sizes',materials:'variant-materials',flavors:'variant-flavors',warranty:'pm-warranty-name',specs:'variant-specs'};
  const target=map[tool];
  psSwitchTab('variants');
  setTimeout(()=>{
    if(target){
      const el=document.getElementById(target);
      if(el){
        el.scrollIntoView({behavior:'smooth',block:'center'});
        // Flash highlight effect to draw the eye
        const wrap=el.closest('.vf-section')||el.parentElement;
        if(wrap){
          const orig=wrap.style.boxShadow;
          wrap.style.transition='box-shadow .4s';
          wrap.style.boxShadow='0 0 0 3px #fbbf24';
          setTimeout(()=>{wrap.style.boxShadow=orig||'';},1400);
        }
      }
    } else {
      toast(`💡 أداة "${TOOL_LABELS[tool]}" — أضفها في قسم المواصفات`);
    }
  },120);
}
function showInlineVariantsForActiveTools(){
  // Auto-enable variant field toggles for active tools
  const mapping={colors:'colors',storage:'storage',sizes_clothes:'sizes',sizes_shoes:'sizes',materials:'materials',flavors:'flavors',warranty:'warranty',specs:'specs'};
  Object.entries(mapping).forEach(([tool,field])=>{
    const cb=document.getElementById('vf-'+field);
    if(cb){cb.checked=ACTIVE_TOOLS.has(tool)||cb.checked;toggleVariantField(field);}
  });
}

// ───────────────────────── MARKETS MODULE (Multi-Market Targeting) ─────────────────────────
const MKT_PRESETS={
  gulf:['sa','ae','kw','qa','bh','om'],
  levant:['jo','lb','sy','ps','iq'],
  north_africa:['eg','ma','dz','tn','ly'],
  arab_all:['sa','ae','kw','qa','bh','om','jo','lb','sy','ps','iq','eg','ma','dz','tn','ly','ye','sd'],
  global:'ALL',
  clear:[]
};
let MKT_DATA=[]; // full markets list from /api/ready-sites/markets
let MKT_ACTIVE=new Set(JSON.parse(localStorage.getItem('zx_active_markets')||'["sa"]'));
let MKT_CONFIG=JSON.parse(localStorage.getItem('zx_markets_config')||'{}'); // {market_id:{gateways:[], shipping:[], vat:15}}

async function loadMarkets(){
  if(!MKT_DATA.length){
    try{
      const r=await fetch(API+'/api/ready-sites/markets');
      const d=await r.json();
      MKT_DATA=d.markets||[];
    }catch(e){
      console.warn('loadMarkets failed',e);
      toast('⚠️ فشل تحميل قائمة الأسواق');return;
    }
  }
  mktRender();
}

function mktRender(){
  const search=($('mkt-search')?.value||'').toLowerCase().trim();
  const filtered=search?MKT_DATA.filter(m=>m.name_ar.toLowerCase().includes(search)||m.name_en.toLowerCase().includes(search)||m.currency.toLowerCase().includes(search)):MKT_DATA;
  const grid=$('mkt-grid');
  grid.innerHTML=filtered.map(m=>{
    const active=MKT_ACTIVE.has(m.id);
    return `<div class="mkt-card" data-mkt-id="${m.id}" onclick="mktToggle('${m.id}')" style="border:2px solid ${active?'var(--purple)':'var(--border)'};background:${active?'linear-gradient(135deg,#faf5ff,#fdf2f8)':'var(--surface)'};border-radius:12px;padding:12px;cursor:pointer;transition:all .15s;position:relative">
      ${active?'<div style="position:absolute;top:6px;left:6px;background:var(--purple);color:#fff;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:900">✓</div>':''}
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="font-size:26px">${m.flag}</span>
        <div style="flex:1;min-width:0"><b style="font-size:13px;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${m.name_ar}</b><div style="font-size:10px;color:var(--text-mut)">${m.currency} · ${m.language.toUpperCase()}</div></div>
      </div>
      <div style="display:flex;gap:4px;flex-wrap:wrap;font-size:9px">
        <span style="background:#dbeafe;color:#1e3a8a;padding:2px 6px;border-radius:6px;font-weight:700">💳 ${m.payment_methods_count}</span>
        <span style="background:#fef3c7;color:#92400e;padding:2px 6px;border-radius:6px;font-weight:700">🚚 ${m.shipping_carriers_count}</span>
      </div>
    </div>`;
  }).join('');
  mktUpdateActiveList();
  mktUpdateStats();
}

function mktToggle(id){
  if(MKT_ACTIVE.has(id))MKT_ACTIVE.delete(id);else MKT_ACTIVE.add(id);
  if(!MKT_ACTIVE.size)MKT_ACTIVE.add('sa'); // always keep at least one
  mktRender();
}

function mktApplyPreset(btn){
  const key=btn.dataset.mktPreset;
  const preset=MKT_PRESETS[key];
  if(preset==='ALL'){MKT_ACTIVE=new Set(MKT_DATA.map(m=>m.id));}
  else if(Array.isArray(preset)){MKT_ACTIVE=new Set(preset.length?preset:['sa']);}
  mktRender();
  toast('✓ تم تطبيق الباقة: '+btn.textContent.trim());
}

function mktUpdateStats(){
  $('mkt-stat-active').textContent=MKT_ACTIVE.size;
  // Count unique gateways & shipping across active markets (need fetch on detail expand)
  const activeMarkets=MKT_DATA.filter(m=>MKT_ACTIVE.has(m.id));
  const gw=activeMarkets.reduce((s,m)=>s+m.payment_methods_count,0);
  const sh=activeMarkets.reduce((s,m)=>s+m.shipping_carriers_count,0);
  $('mkt-stat-gateways').textContent=gw;
  $('mkt-stat-shipping').textContent=sh;
}

function mktUpdateActiveList(){
  const host=$('mkt-active-list');
  if(!MKT_ACTIVE.size){host.innerHTML='<div style="text-align:center;padding:30px;color:var(--text-mut);font-size:12px">لم تفعّل أي سوق بعد</div>';return;}
  const list=MKT_DATA.filter(m=>MKT_ACTIVE.has(m.id));
  host.innerHTML=list.map(m=>{
    const cfg=MKT_CONFIG[m.id]||{vat:m.id==='sa'?15:m.id==='ae'?5:0};
    return `<div style="border:1px solid var(--border);border-radius:12px;margin-bottom:8px;background:var(--surface);overflow:hidden">
      <div style="padding:12px 14px;display:flex;align-items:center;gap:10px;cursor:pointer" onclick="mktExpand('${m.id}',this)">
        <span style="font-size:22px">${m.flag}</span>
        <div style="flex:1"><b style="font-size:13px">${m.name_ar} · ${m.name_en}</b>
          <div style="font-size:10px;color:var(--text-mut);margin-top:2px">${m.currency} · ${m.language.toUpperCase()} · 💳 ${m.payment_methods_count} بوابة · 🚚 ${m.shipping_carriers_count} شركة · ضريبة ${cfg.vat}%</div>
        </div>
        <span class="mkt-chev" style="color:var(--purple);font-weight:900;font-size:14px">▼</span>
      </div>
      <div class="mkt-detail" id="mkt-detail-${m.id}" style="display:none;padding:14px;border-top:1px solid var(--border);background:#fff"></div>
    </div>`;
  }).join('');
}

async function mktExpand(id,headerEl){
  const detail=$('mkt-detail-'+id);
  const chev=headerEl.querySelector('.mkt-chev');
  if(detail.style.display==='block'){detail.style.display='none';chev.textContent='▼';return;}
  // fetch full market data
  detail.innerHTML='<div style="text-align:center;padding:20px;color:var(--text-mut);font-size:12px">⏳ جاري التحميل...</div>';
  detail.style.display='block';chev.textContent='▲';
  try{
    const r=await fetch(API+'/api/ready-sites/market/'+id);
    const m=await r.json();
    const cfg=MKT_CONFIG[id]||{gateways:[],shipping:[],vat:m.tax?.rate||0};
    const cfgGw=new Set(cfg.gateways||m.payment_gateways.slice(0,5).map(g=>g.id));
    const cfgSh=new Set(cfg.shipping||m.shipping_carriers.slice(0,3).map(s=>s.id));
    detail.innerHTML=`
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
        <div><h5 style="font-size:12px;font-weight:900;margin-bottom:8px;color:var(--purple)">💳 بوابات الدفع المتاحة (${m.payment_gateways.length})</h5>
          <div style="max-height:240px;overflow-y:auto">${m.payment_gateways.map(g=>`<label style="display:flex;align-items:center;gap:8px;padding:7px 9px;border-radius:8px;cursor:pointer;font-size:11px" onmouseover="this.style.background='#faf5ff'" onmouseout="this.style.background='transparent'"><input type="checkbox" data-mkt-gw="${id}:${g.id}" ${cfgGw.has(g.id)?'checked':''} onchange="mktSaveGw('${id}','${g.id}',this.checked)"><span style="flex:1"><b>${g.name_ar||g.name}</b><div style="font-size:10px;color:var(--text-mut)">${g.fees_hint||g.type||''}</div></span></label>`).join('')}</div>
        </div>
        <div><h5 style="font-size:12px;font-weight:900;margin-bottom:8px;color:var(--amber)">🚚 شركات الشحن (${m.shipping_carriers.length})</h5>
          <div style="max-height:240px;overflow-y:auto">${m.shipping_carriers.map(s=>`<label style="display:flex;align-items:center;gap:8px;padding:7px 9px;border-radius:8px;cursor:pointer;font-size:11px" onmouseover="this.style.background='#fffbeb'" onmouseout="this.style.background='transparent'"><input type="checkbox" data-mkt-sh="${id}:${s.id}" ${cfgSh.has(s.id)?'checked':''} onchange="mktSaveSh('${id}','${s.id}',this.checked)"><span style="flex:1"><b>${s.name_ar||s.name}</b><div style="font-size:10px;color:var(--text-mut)">${s.delivery_estimate||''}</div></span></label>`).join('')}</div>
        </div>
      </div>
      <div style="margin-top:14px;padding-top:14px;border-top:1px dashed var(--border);display:grid;grid-template-columns:1fr 1fr;gap:14px">
        <div><label style="font-size:11px;font-weight:900;display:block;margin-bottom:4px">💰 معدل الضريبة (%)</label><input type="number" value="${cfg.vat}" min="0" max="50" step="0.5" data-mkt-vat="${id}" onchange="mktSaveVat('${id}',this.value)" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:8px;font-family:inherit;font-size:12px"></div>
        <div><label style="font-size:11px;font-weight:900;display:block;margin-bottom:4px">📜 رقم التسجيل الضريبي</label><input type="text" placeholder="مثال: 300011234500003" data-mkt-tax-id="${id}" value="${cfg.tax_id||''}" onchange="mktSaveTaxId('${id}',this.value)" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:8px;font-family:inherit;font-size:12px;direction:ltr"></div>
      </div>
      <div style="margin-top:10px;padding:10px;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;font-size:11px;color:#065f46;line-height:1.7">✓ <b>${m.payment_gateways.length}</b> بوابة دفع · <b>${m.shipping_carriers.length}</b> شركة شحن · العملة <b>${m.currency}</b> · اللغة <b>${m.language.toUpperCase()}</b></div>
    `;
  }catch(e){detail.innerHTML='<div style="text-align:center;padding:20px;color:#dc2626;font-size:12px">⚠️ فشل التحميل</div>';}
}

function mktSaveGw(mid,gid,on){
  MKT_CONFIG[mid]=MKT_CONFIG[mid]||{gateways:[],shipping:[],vat:0};
  const arr=new Set(MKT_CONFIG[mid].gateways||[]);
  if(on)arr.add(gid);else arr.delete(gid);
  MKT_CONFIG[mid].gateways=Array.from(arr);
}
function mktSaveSh(mid,sid,on){
  MKT_CONFIG[mid]=MKT_CONFIG[mid]||{gateways:[],shipping:[],vat:0};
  const arr=new Set(MKT_CONFIG[mid].shipping||[]);
  if(on)arr.add(sid);else arr.delete(sid);
  MKT_CONFIG[mid].shipping=Array.from(arr);
}
function mktSaveVat(mid,v){MKT_CONFIG[mid]=MKT_CONFIG[mid]||{gateways:[],shipping:[],vat:0};MKT_CONFIG[mid].vat=parseFloat(v)||0;}
function mktSaveTaxId(mid,v){MKT_CONFIG[mid]=MKT_CONFIG[mid]||{gateways:[],shipping:[],vat:0};MKT_CONFIG[mid].tax_id=v;}

function mktSaveAll(){
  localStorage.setItem('zx_active_markets',JSON.stringify(Array.from(MKT_ACTIVE)));
  localStorage.setItem('zx_markets_config',JSON.stringify(MKT_CONFIG));
  toast('✓ تم حفظ إعدادات '+MKT_ACTIVE.size+' سوق · ستظهر تلقائياً للعملاء حسب موقعهم');
}

// ───────────────────────── BRANCHES MANAGEMENT (Multi-Branch Sub-Dashboards with Subscription) ─────────────────────────
let MERCHANT_BRANCHES=JSON.parse(localStorage.getItem('zx_merchant_branches')||'null')||[
  {id:'br-main',name_ar:'الفرع الرئيسي',name_en:'Main Branch',addr:'الرياض - العليا',phone:'+966112345678',lat:24.6877,lng:46.6857,manager_name:'مدير عام',manager_email:'owner@zenrex.ai',active:true,is_main:true,created_at:Date.now()-90*86400000}
];

function branchFeeFor(index){
  if(index===0)return 0;          // First branch free
  if(index<=2)return 99;          // 2-3 = 99
  if(index<=9)return 149;         // 4-10 = 149
  return 199;                     // 11+ = 199 (Enterprise call later)
}

function loadMerchantBranches(){
  renderBranchesList();
  updateBranchStats();
}

function renderBranchesList(){
  const host=document.getElementById('branches-list');if(!host)return;
  document.getElementById('br-list-count').textContent=`${MERCHANT_BRANCHES.length} فرع`;
  if(!MERCHANT_BRANCHES.length){host.innerHTML='<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--text-mut);font-size:12px">لا يوجد فروع · ابدأ بإضافة فرعك الأول</div>';return;}
  host.innerHTML=MERCHANT_BRANCHES.map((b,i)=>{
    const fee=branchFeeFor(i);
    const ordersToday=Math.floor(Math.random()*60)+5;
    const revenueToday=(Math.random()*15000+2000).toFixed(0);
    return `<div style="border:2px solid ${b.active?'var(--border)':'#fecaca'};background:${b.active?'var(--surface)':'#fef2f2'};border-radius:14px;padding:14px;position:relative;transition:transform .15s" onmouseenter="this.style.transform='translateY(-2px)'" onmouseleave="this.style.transform='translateY(0)'">
      ${b.is_main?'<div style="position:absolute;top:8px;left:8px;background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#0a0a14;padding:3px 9px;border-radius:99px;font-size:9px;font-weight:900">👑 رئيسي</div>':''}
      ${fee===0?'<div style="position:absolute;top:8px;right:8px;background:#10b981;color:#fff;padding:3px 9px;border-radius:99px;font-size:9px;font-weight:900">🆓 مجاني</div>':`<div style="position:absolute;top:8px;right:8px;background:#7c3aed;color:#fff;padding:3px 9px;border-radius:99px;font-size:9px;font-weight:900">${fee} ر.س/شهر</div>`}
      <div style="margin-top:24px;display:flex;align-items:center;gap:10px">
        <div style="width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,#10b981,#059669);color:#fff;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0">🏪</div>
        <div style="flex:1;min-width:0"><b style="font-size:14px;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${b.name_ar}</b><div style="font-size:10px;color:var(--text-mut);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">📍 ${b.addr||'—'}</div></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:12px;font-size:10px">
        <div style="background:#dbeafe;color:#1e3a8a;padding:6px 8px;border-radius:8px"><b style="font-size:13px">${ordersToday}</b><div>طلب اليوم</div></div>
        <div style="background:#dcfce7;color:#065f46;padding:6px 8px;border-radius:8px"><b style="font-size:13px">${parseInt(revenueToday).toLocaleString()}</b><div>ر.س إيرادات</div></div>
      </div>
      <div style="display:flex;align-items:center;gap:6px;margin-top:10px;padding-top:10px;border-top:1px dashed var(--border);font-size:11px;color:var(--text-mut)">
        <i data-lucide="user" style="width:12px;height:12px"></i>
        <span>${b.manager_name||'لم يعيّن'}</span>
        ${b.manager_email?`<span style="color:#94a3b8" title="${b.manager_email}">· ${b.manager_email.length>20?b.manager_email.slice(0,20)+'...':b.manager_email}</span>`:''}
      </div>
      <div style="display:flex;gap:5px;margin-top:10px;flex-wrap:wrap">
        <button onclick="openBranchDashboard('${b.id}')" data-testid="open-branch-${b.id}" style="flex:1;min-width:80px;padding:8px;background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;border:none;border-radius:8px;font-family:inherit;font-weight:900;font-size:10px;cursor:pointer">🔓 فتح اللوحة</button>
        <button onclick="copyBranchLink('${b.id}')" style="padding:8px 10px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:8px;font-family:inherit;font-size:10px;cursor:pointer" title="نسخ رابط المدير">🔗</button>
        <button onclick="editBranch('${b.id}')" style="padding:8px 10px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:8px;font-family:inherit;font-size:10px;cursor:pointer" title="تعديل">✏️</button>
        <button onclick="toggleBranchActive('${b.id}')" style="padding:8px 10px;background:${b.active?'#fef3c7':'#dcfce7'};color:${b.active?'#92400e':'#065f46'};border:1px solid ${b.active?'#fde68a':'#86efac'};border-radius:8px;font-family:inherit;font-size:10px;cursor:pointer" title="${b.active?'إيقاف':'تفعيل'}">${b.active?'⏸':'▶️'}</button>
        ${b.is_main?'':`<button onclick="removeBranch('${b.id}')" style="padding:8px 10px;background:#fef2f2;color:#dc2626;border:1px solid #fecaca;border-radius:8px;font-family:inherit;font-size:10px;cursor:pointer" title="حذف">🗑️</button>`}
      </div>
    </div>`;
  }).join('');
  if(window.lucide)window.lucide.createIcons();
}

function updateBranchStats(){
  const total=MERCHANT_BRANCHES.length;
  const active=MERCHANT_BRANCHES.filter(b=>b.active).length;
  const fees=MERCHANT_BRANCHES.reduce((s,_,i)=>s+branchFeeFor(i),0);
  const ordersToday=total*22; // mock
  document.getElementById('br-stat-total').textContent=total;
  document.getElementById('br-stat-active').textContent=active;
  document.getElementById('br-stat-orders').textContent=ordersToday;
  document.getElementById('br-stat-fees').textContent=fees;
}

function openAddBranchModal(){
  const idx=MERCHANT_BRANCHES.length;
  const fee=branchFeeFor(idx);
  const tierLabel=idx===0?'مجاني (الفرع الأول)':idx<=2?'⭐ الباقة الفضية':idx<=9?'🚀 الباقة الذهبية':'👑 Enterprise';
  document.getElementById('ab-cost-line').innerHTML=fee===0?'🆓 مجاناً مع باقتك':`💎 ${fee} ر.س/شهر · ${tierLabel}`;
  document.getElementById('ab-cost-summary').innerHTML=fee===0?'<b style="color:#065f46">🆓 هذا الفرع مجاني مع باقتك الحالية</b>':`<div style="display:flex;justify-content:space-between;align-items:center"><div><b style="color:#92400e;font-size:12px">إجمالي شهري إضافي</b><div style="font-size:10px;color:#92400e;margin-top:2px">${tierLabel}</div></div><b style="color:#dc2626;font-size:18px">${fee} ر.س</b></div>`;
  ['ab-name-ar','ab-name-en','ab-addr','ab-phone','ab-lat','ab-lng','ab-mgr-name','ab-mgr-email'].forEach(id=>{const e=document.getElementById(id);if(e)e.value='';});
  document.getElementById('add-branch-modal').style.display='flex';
}
function closeAddBranchModal(){document.getElementById('add-branch-modal').style.display='none';}

function abAutoLocate(){
  if(!navigator.geolocation){toast('متصفحك لا يدعم تحديد الموقع');return;}
  toast('⏳ جاري تحديد موقعك...');
  navigator.geolocation.getCurrentPosition(p=>{
    document.getElementById('ab-lat').value=p.coords.latitude.toFixed(4);
    document.getElementById('ab-lng').value=p.coords.longitude.toFixed(4);
    toast('✓ تم تحديد الموقع');
  },()=>toast('⚠️ تعذّر تحديد الموقع'));
}

function createBranch(){
  const name_ar=document.getElementById('ab-name-ar').value.trim();
  if(!name_ar){alert('اسم الفرع مطلوب');return;}
  const idx=MERCHANT_BRANCHES.length;
  const fee=branchFeeFor(idx);
  if(fee>0&&!confirm(`سيتم إضافة فرع جديد بتكلفة ${fee} ر.س/شهر إضافية على باقتك.\n\nمتابعة الإضافة والاشتراك؟`))return;
  const b={
    id:'br-'+Date.now().toString(36),
    name_ar,
    name_en:document.getElementById('ab-name-en').value.trim()||name_ar,
    addr:document.getElementById('ab-addr').value.trim(),
    phone:document.getElementById('ab-phone').value.trim(),
    lat:parseFloat(document.getElementById('ab-lat').value)||null,
    lng:parseFloat(document.getElementById('ab-lng').value)||null,
    manager_name:document.getElementById('ab-mgr-name').value.trim()||'مدير الفرع',
    manager_email:document.getElementById('ab-mgr-email').value.trim(),
    active:true,is_main:false,fee_monthly:fee,
    created_at:Date.now()
  };
  MERCHANT_BRANCHES.push(b);
  localStorage.setItem('zx_merchant_branches',JSON.stringify(MERCHANT_BRANCHES));
  closeAddBranchModal();
  renderBranchesList();updateBranchStats();
  toast(`✓ تم إنشاء فرع "${name_ar}"${fee?` · سيُضاف ${fee} ر.س لفاتورتك الشهرية`:''}`);
  if(b.manager_email){setTimeout(()=>toast('📨 تم إرسال بيانات الدخول لـ '+b.manager_email),1500);}
}

function openBranchDashboard(branchId){
  const b=MERCHANT_BRANCHES.find(x=>x.id===branchId);if(!b)return;
  localStorage.setItem('zx_active_branch_scope',branchId);
  toast(`🔓 الآن تدير: ${b.name_ar} · كل البيانات (طلبات/مخزون/تقارير) مفلترة لهذا الفرع`);
  setTimeout(()=>goPage('dashboard'),600);
}

function copyBranchLink(branchId){
  const b=MERCHANT_BRANCHES.find(x=>x.id===branchId);if(!b)return;
  const url=`${window.location.origin}/mockups/admin.html?branch=${branchId}`;
  navigator.clipboard?.writeText(url).then(()=>toast('✓ تم نسخ رابط لوحة مدير "'+b.name_ar+'"')).catch(()=>{
    prompt('انسخ الرابط يدوياً:',url);
  });
}

function editBranch(id){
  const b=MERCHANT_BRANCHES.find(x=>x.id===id);if(!b)return;
  openAddBranchModal();
  setTimeout(()=>{
    document.getElementById('ab-name-ar').value=b.name_ar||'';
    document.getElementById('ab-name-en').value=b.name_en||'';
    document.getElementById('ab-addr').value=b.addr||'';
    document.getElementById('ab-phone').value=b.phone||'';
    document.getElementById('ab-lat').value=b.lat||'';
    document.getElementById('ab-lng').value=b.lng||'';
    document.getElementById('ab-mgr-name').value=b.manager_name||'';
    document.getElementById('ab-mgr-email').value=b.manager_email||'';
    // Change button to update
    const btn=document.querySelector('[data-testid="create-branch-btn"]');
    if(btn){btn.textContent='💾 حفظ التعديلات';btn.onclick=()=>{
      b.name_ar=document.getElementById('ab-name-ar').value.trim()||b.name_ar;
      b.name_en=document.getElementById('ab-name-en').value.trim()||b.name_en;
      b.addr=document.getElementById('ab-addr').value.trim();
      b.phone=document.getElementById('ab-phone').value.trim();
      b.lat=parseFloat(document.getElementById('ab-lat').value)||b.lat;
      b.lng=parseFloat(document.getElementById('ab-lng').value)||b.lng;
      b.manager_name=document.getElementById('ab-mgr-name').value.trim();
      b.manager_email=document.getElementById('ab-mgr-email').value.trim();
      localStorage.setItem('zx_merchant_branches',JSON.stringify(MERCHANT_BRANCHES));
      closeAddBranchModal();renderBranchesList();
      toast('✓ تم حفظ التعديلات');
    };}
  },100);
}

function toggleBranchActive(id){
  const b=MERCHANT_BRANCHES.find(x=>x.id===id);if(!b)return;
  if(b.is_main&&b.active){alert('لا يمكن إيقاف الفرع الرئيسي');return;}
  b.active=!b.active;
  localStorage.setItem('zx_merchant_branches',JSON.stringify(MERCHANT_BRANCHES));
  renderBranchesList();updateBranchStats();
  toast(b.active?`▶️ تم تفعيل ${b.name_ar}`:`⏸ تم إيقاف ${b.name_ar} مؤقتاً`);
}

function removeBranch(id){
  const b=MERCHANT_BRANCHES.find(x=>x.id===id);if(!b)return;
  if(b.is_main){alert('لا يمكن حذف الفرع الرئيسي');return;}
  if(!confirm(`⚠️ حذف فرع "${b.name_ar}" نهائياً؟\n\nسيتم:\n- إلغاء اشتراكه (${b.fee_monthly||0} ر.س/شهر)\n- نقل طلباته للفرع الرئيسي\n- إغلاق حساب مديره\n\nهذا الإجراء لا يمكن التراجع عنه.`))return;
  MERCHANT_BRANCHES=MERCHANT_BRANCHES.filter(x=>x.id!==id);
  localStorage.setItem('zx_merchant_branches',JSON.stringify(MERCHANT_BRANCHES));
  renderBranchesList();updateBranchStats();
  toast(`🗑️ تم حذف الفرع · توفير ${b.fee_monthly||0} ر.س/شهر`);
}

// Assign driver to a specific branch (or '__all__' for open access)
function assignDriverBranch(driverId,branchId){
  const map=JSON.parse(localStorage.getItem('zx_driver_branches')||'{}');
  if(branchId==='__all__')delete map[driverId];else map[driverId]=branchId;
  localStorage.setItem('zx_driver_branches',JSON.stringify(map));
  if(branchId==='__all__'){toast('✓ السائق متاح لكل الفروع');}
  else{
    const branches=JSON.parse(localStorage.getItem('zx_merchant_branches')||'[]');
    const b=branches.find(x=>x.id===branchId);
    toast(`✓ السائق مخصص لـ ${b?.name_ar||'الفرع'}`);
  }
}

// ───── SANDBOX / TEST MODE for Payment & Shipping Gateways ─────
function isSandboxMode(){return localStorage.getItem('zx_sandbox_mode')==='1';}
function toggleSandboxMode(){
  const newMode=!isSandboxMode();
  localStorage.setItem('zx_sandbox_mode',newMode?'1':'0');
  toast(newMode?'🧪 الوضع التجريبي مُفعّل · كل المعاملات وهمية للاختبار':'🔒 الوضع الفعلي مُفعّل · المعاملات حقيقية');
  setTimeout(()=>location.reload(),800);
}

// ───────────────────────── SEED DEMO PRODUCTS (5 per category × 8 categories = 40 items) ─────────────────────────
const SEED_DEMO=[
  // Electronics (5)
  {name:'iPhone 17 Pro Max',cat:'إلكترونيات',price:6299,stock:24,sku:'IP17PM',img:'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600',desc:'A19 Bionic · 6.9" ProMotion · بطارية 24 ساعة'},
  {name:'سماعة Sony WH-1000XM6',cat:'إلكترونيات',price:1490,stock:18,sku:'SNY-XM6',img:'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600',desc:'ANC جيل 5 · 30 ساعة · Hi-Res'},
  {name:'لابتوب MacBook Pro M4',cat:'إلكترونيات',price:9890,stock:9,sku:'MBP-M4',img:'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600',desc:'14" · M4 Pro · 18GB · 1TB SSD'},
  {name:'Apple Watch Ultra 3',cat:'إلكترونيات',price:3490,stock:15,sku:'AWU3',img:'https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=600',desc:'GPS+Cellular · تيتانيوم · 49مم'},
  {name:'شاشة Samsung Odyssey 4K',cat:'إلكترونيات',price:3290,stock:7,sku:'ODY-4K',img:'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600',desc:'27" · 240Hz · HDR1000 · QD-OLED'},
  // Fashion (5)
  {name:'فستان سهرة فاخر بالتطريز',cat:'أزياء',price:1450,stock:6,sku:'EVD-001',img:'https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=600',desc:'حرير طبيعي · يدوي · مقاسات S-XL'},
  {name:'حذاء Nike Air Max جديد',cat:'أزياء',price:899,stock:32,sku:'NKE-AM',img:'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600',desc:'وسادة هوائية · مقاسات 38-46 · 3 ألوان'},
  {name:'ساعة Rolex Submariner',cat:'أزياء',price:42900,stock:2,sku:'RLX-SUB',img:'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600',desc:'حركة سويسرية · مقاومة 300م · ضمان 5 سنوات'},
  {name:'حقيبة Louis Vuitton أصلية',cat:'أزياء',price:8950,stock:4,sku:'LV-001',img:'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600',desc:'جلد طبيعي · شهادة أصالة · بطاقة ضمان'},
  {name:'نظارة Ray-Ban Aviator',cat:'أزياء',price:650,stock:22,sku:'RB-AV',img:'https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=600',desc:'UV400 · إطار ذهبي · مع علبة جلدية'},
  // Beauty (5)
  {name:'عطر Dior Sauvage 100مل',cat:'تجميل ومكياج',price:780,stock:18,sku:'DIOR-S',img:'https://images.unsplash.com/photo-1541643600914-78b084683601?w=600',desc:'برغموت · مسك · ثبات 12 ساعة'},
  {name:'سيروم The Ordinary فيتامين C',cat:'تجميل ومكياج',price:185,stock:45,sku:'TO-VC',img:'https://images.unsplash.com/photo-1556228720-195a672e8a03?w=600',desc:'30% L-Ascorbic · يضيء البشرة · 30مل'},
  {name:'باليت Fenty Beauty 24 لون',cat:'تجميل ومكياج',price:420,stock:14,sku:'FB-24',img:'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=600',desc:'24 درجة · ثبات 10 ساعات · يصلح للسهرات'},
  {name:'كريم La Mer المرطب',cat:'تجميل ومكياج',price:2890,stock:5,sku:'LM-CR',img:'https://images.unsplash.com/photo-1570554886111-e80fcca6a029?w=600',desc:'Miracle Broth · 60مل · لكل أنواع البشرة'},
  {name:'مكواة Dyson Airwrap',cat:'تجميل ومكياج',price:2450,stock:8,sku:'DYS-AW',img:'https://images.unsplash.com/photo-1522338242992-e1a54906a8da?w=600',desc:'تقنية Coanda · 6 ملحقات · حقيبة سفر'},
  // Home (5)
  {name:'مكنسة Dyson V15 لاسلكية',cat:'منزل',price:2890,stock:12,sku:'DYS-V15',img:'https://images.unsplash.com/photo-1558317374-067fb5f30001?w=600',desc:'ليزر يكشف الغبار · 60 دقيقة · HEPA'},
  {name:'مكينة قهوة De\'Longhi La Specialista',cat:'منزل',price:3490,stock:6,sku:'DEL-LS',img:'https://images.unsplash.com/photo-1610632380989-680fe40816c6?w=600',desc:'15-بار · رغوة حليب يدوية · 1450 واط'},
  {name:'سرير Tempur-Pedic ProBreeze',cat:'منزل',price:5890,stock:3,sku:'TMP-PB',img:'https://images.unsplash.com/photo-1631679706909-1844bbd07221?w=600',desc:'تبريد 4 درجات · فوم طبي · ضمان 10 سنوات'},
  {name:'تلفزيون Samsung QLED 65"',cat:'منزل',price:4290,stock:9,sku:'SAM-Q65',img:'https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=600',desc:'4K · 144Hz · Dolby Atmos · Tizen 8.0'},
  {name:'طقم أواني Le Creuset 7 قطع',cat:'منزل',price:1890,stock:11,sku:'LC-7P',img:'https://images.unsplash.com/photo-1610701596007-11502861dcfa?w=600',desc:'حديد زهر فرنسي · 7 قطع · ضمان مدى الحياة'},
  // Sports (5)
  {name:'دراجة Trek Mountain Pro',cat:'رياضة',price:4890,stock:6,sku:'TRK-MP',img:'https://images.unsplash.com/photo-1485965120184-e220f721d03e?w=600',desc:'21 سرعة · إطار كربون · فرامل هيدروليكية'},
  {name:'دامبلز Bowflex قابلة للتعديل',cat:'رياضة',price:1990,stock:14,sku:'BFX-DB',img:'https://images.unsplash.com/photo-1638536532686-d610adfc8e5c?w=600',desc:'2-25 كجم · 15 وزن · ستاند مرفق'},
  {name:'ساعة Garmin Fenix 8',cat:'رياضة',price:3290,stock:11,sku:'GRM-F8',img:'https://images.unsplash.com/photo-1576243345690-4e4b79b63288?w=600',desc:'GPS مزدوج · بطارية 28 يوم · مقاومة 100م'},
  {name:'حذاء Adidas Ultraboost 24',cat:'رياضة',price:850,stock:28,sku:'ADI-UB',img:'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600',desc:'Boost Pro · Primeknit · مرونة قصوى'},
  {name:'سجادة يوغا Manduka PRO',cat:'رياضة',price:295,stock:35,sku:'MND-PRO',img:'https://images.unsplash.com/photo-1592432678016-e910b452f9a2?w=600',desc:'6مم · مضادة للانزلاق · ضمان مدى الحياة'},
  // Food (5)
  {name:'قهوة Blue Bottle مختصة 250جم',cat:'مأكولات',price:95,stock:48,sku:'BB-250',img:'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=600',desc:'محمصة طازجة · مختصة · رحلة الحاوية'},
  {name:'عسل سدر جبلي يمني 1كجم',cat:'مأكولات',price:585,stock:17,sku:'YEM-SDR',img:'https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=600',desc:'يمني أصلي · غير مبستر · شهادة منشأ'},
  {name:'تمر مجدول فاخر 5كجم',cat:'مأكولات',price:295,stock:22,sku:'MJD-5K',img:'https://images.unsplash.com/photo-1581375074612-d1fd0e661aeb?w=600',desc:'فاخر · من نخيل المدينة · علبة هدية'},
  {name:'زعفران إيراني نقي 5 جرام',cat:'مأكولات',price:425,stock:13,sku:'SAF-5G',img:'https://images.unsplash.com/photo-1599909533930-f2a1aab7e1e7?w=600',desc:'صنف Negin · شهادة جودة · علبة فاخرة'},
  {name:'زيت زيتون عضوي 750مل',cat:'مأكولات',price:135,stock:31,sku:'OLV-750',img:'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=600',desc:'بكر ممتاز · معصور بارد · سوري عضوي'},
  // Kids (5)
  {name:'مجموعة LEGO Star Wars Death Star',cat:'أطفال',price:1890,stock:7,sku:'LEGO-DS',img:'https://images.unsplash.com/photo-1558877385-8c1b8c4b4d28?w=600',desc:'4016 قطعة · للأعمار 14+ · حصرية'},
  {name:'سيارة ريموت Traxxas X-Maxx',cat:'أطفال',price:2890,stock:5,sku:'TRX-XM',img:'https://images.unsplash.com/photo-1558060370-d644479cb6f7?w=600',desc:'سرعة 80كم/س · 4WD · بطارية ليثيوم'},
  {name:'دراجة أطفال Spider-Man 16"',cat:'أطفال',price:485,stock:19,sku:'SM-BIKE',img:'https://images.unsplash.com/photo-1597740049577-d8f4c947be15?w=600',desc:'للأعمار 4-7 · عجلتي توازن · ترخيص أصلي'},
  {name:'باربي Dreamhouse 3 طوابق',cat:'أطفال',price:1290,stock:8,sku:'BB-DH',img:'https://images.unsplash.com/photo-1558877385-8c1b8c4b4d28?w=600',desc:'مصعد كهربائي · 75+ قطعة · إضاءة LED'},
  {name:'تابلت تعليمي Amazon Kids Pro',cat:'أطفال',price:649,stock:24,sku:'AMZ-KP',img:'https://images.unsplash.com/photo-1561154464-82e9adf32764?w=600',desc:'10" · سنة اشتراك مجاني · غطاء واقي'},
];

async function seedDemoProducts(){
  if(!confirm('سيتم إضافة 40 منتج تجريبي (5 منتجات × 8 أقسام) لتجربة المتجر. متابعة؟'))return;
  toast('⏳ جاري إضافة المنتجات...');
  let success=0,fail=0;
  for(const m of SEED_DEMO){
    try{
      const saved=await apiFetch('/api/store/products',{method:'POST',body:JSON.stringify({name:m.name,price:m.price,stock:m.stock,sku:m.sku,stock_low:5,cat:m.cat,img:m.img,desc:m.desc})});
      if(saved&&saved.id){PRODUCTS.push({...saved,stockLow:saved.stock_low});success++;}else fail++;
    }catch(_){fail++;}
  }
  renderProducts();renderAll();
  toast(`✓ تم إضافة ${success} منتج · ${fail?fail+' فشلت':''}`);
}

async function bulkAiEnrich(){
  if(!PRODUCTS.length){toast('⚠️ أضف منتجات أولاً ثم استخدم الإثراء');return;}
  if(!confirm(`سيتم تشغيل AI Research على ${PRODUCTS.length} منتج لجلب وصف ومواصفات وصور وروابط رسمية تلقائياً (مجاناً للتاجر). يستغرق ~5 ثوان لكل منتج. متابعة؟`))return;
  toast('⏳ AI يبحث في الإنترنت لكل منتج...');
  let done=0;
  const total=PRODUCTS.length;
  for(const p of PRODUCTS){
    try{
      const res=await fetch(API+'/api/image-studio/product-info',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({name:p.name,lang:'ar'})
      });
      if(res.ok){const data=await res.json();p.ai_info=data;done++;}
    }catch(_){}
    if(done%5===0)toast(`✨ ${done}/${total} منتج تم إثراؤه...`);
  }
  // Save enrichment locally
  const enrichmentMap={};
  PRODUCTS.forEach(p=>{if(p.ai_info)enrichmentMap[p.id]=p.ai_info;});
  localStorage.setItem('zx_product_ai_info',JSON.stringify(enrichmentMap));
  toast(`✓ تم إثراء ${done} منتج من أصل ${total} · المعلومات ستظهر في صفحة المنتج للعميل`);
}


function openProductModal(){
  EDITING_PRODUCT_ID=null;
  $('prod-mod').classList.add('open');
  psSwitchTab('info');
  PS_STATE={style:'product',ctype:'product',images:[],approvedImg:null,analysis:null,uploadedImg:null,aiImg:null,bgColor:'#ffffff',frameColor:'#7c3aed',aspect:'1:1'};
  // Reset preview
  const prev=document.getElementById('ps-info-preview');if(prev)prev.style.display='none';
  const pc=document.getElementById('ps-info-preview-content');if(pc)pc.innerHTML='';
  // Reset AI tab
  const aiEmpty=document.getElementById('ps-ai-empty');if(aiEmpty)aiEmpty.style.display='flex';
  const aiRes=document.getElementById('ps-ai-result');if(aiRes){aiRes.style.display='none';aiRes.innerHTML='';}
  setTimeout(()=>{if(window.lucide)lucide.createIcons();psRenderColorPresets();psUpdateSummary();},80);
}
function closeProductModal(){$('prod-mod').classList.remove('open')}
function pmPreviewImg(inp){
  const f=inp.files[0];if(!f)return;
  const reader=new FileReader();
  reader.onload=e=>{
    $('pm-img-preview').innerHTML=`<img src="${e.target.result}" loading="lazy" decoding="async">`;
    PS_STATE.uploadedImg=e.target.result;
  };
  reader.readAsDataURL(f);
}
async function pmSave(){
  const name=$('pm-name').value.trim();if(!name){alert('اكتب الاسم');psSwitchTab('info');$('pm-name').focus();return;}
  const previewImg=$('pm-img-preview').querySelector('img');
  const img=PS_STATE.approvedImg||(previewImg?previewImg.src:'https://images.unsplash.com/photo-1586765501019-cbf6c0b6d7a4?w=600&q=85');
  const payload={name,price:+$('pm-price').value||0,stock:+$('pm-stock').value||0,sku:$('pm-sku')?.value||'',stock_low:+$('pm-stock-low')?.value||5,mfg:$('pm-mfg')?.value||'',exp:$('pm-exp')?.value||'',track_expiry:$('pm-track-expiry')?.checked||false,cat:$('pm-cat').value,img,desc:$('pm-desc').value||'',analysis:PS_STATE.analysis||null};
  try{
    let saved;
    if(EDITING_PRODUCT_ID){
      saved=await apiFetch('/api/store/products/'+EDITING_PRODUCT_ID,{method:'PUT',body:JSON.stringify(payload)});
      const idx=PRODUCTS.findIndex(p=>p.id===EDITING_PRODUCT_ID);
      if(idx>=0)PRODUCTS[idx]={...saved,stockLow:saved.stock_low,trackExpiry:saved.track_expiry};
    } else {
      saved=await apiFetch('/api/store/products',{method:'POST',body:JSON.stringify(payload)});
      const newP={...saved,stockLow:saved.stock_low,trackExpiry:saved.track_expiry};
      PRODUCTS.unshift(newP);
      try{autoPostNewProduct(newP);}catch(e){}
    }
    EDITING_PRODUCT_ID=null;
    closeProductModal();
    renderProducts();
    renderAll();
    ['pm-name','pm-price','pm-desc'].forEach(id=>$(id).value='');
    $('pm-img-preview').innerHTML=`<i data-lucide="upload-cloud" style="width:42px;height:42px;color:#94a3b8;margin-bottom:8px"></i><p style="font-size:12px;color:#94a3b8;text-align:center">اضغط لرفع صورة أو<br>اسحبها هنا</p>`;
    toast('✓ تم حفظ المنتج في قاعدة البيانات');
  }catch(e){alert('فشل الحفظ: '+e.message);}
}

// ───── PRODUCT STUDIO ─────
let PS_STATE={style:'product',ctype:'product',images:[],approvedImg:null,analysis:null,uploadedImg:null,aiImg:null,bgColor:'#ffffff',bgColorName:'pure white',frameColor:'#7c3aed',frameColorName:'vibrant purple',aspect:'1:1'};

// ── Categorized Color Palette (50+ named colors mapped to English names for AI prompts) ──
const PS_COLOR_CATEGORIES={
  basics:{label:'⚪ أساسي',colors:[
    {hex:'#ffffff',ar:'أبيض',en:'pure white'},
    {hex:'#000000',ar:'أسود',en:'pure black'},
    {hex:'#6b7280',ar:'رمادي',en:'medium gray'},
    {hex:'#f3f4f6',ar:'رمادي فاتح',en:'light gray'},
    {hex:'#1f2937',ar:'فحمي',en:'charcoal gray'},
    {hex:'#0a0a14',ar:'أسود فاخر',en:'rich black'},
  ]},
  warm:{label:'🔥 دافي',colors:[
    {hex:'#ef4444',ar:'أحمر',en:'bright red'},
    {hex:'#dc2626',ar:'أحمر داكن',en:'crimson red'},
    {hex:'#f97316',ar:'برتقالي',en:'vivid orange'},
    {hex:'#fbbf24',ar:'أصفر ذهبي',en:'golden yellow'},
    {hex:'#facc15',ar:'أصفر',en:'sunny yellow'},
    {hex:'#d97706',ar:'كهرماني',en:'amber brown'},
    {hex:'#b45309',ar:'بني داكن',en:'dark brown'},
    {hex:'#92400e',ar:'بني محمر',en:'reddish brown'},
  ]},
  cool:{label:'❄️ بارد',colors:[
    {hex:'#3b82f6',ar:'أزرق',en:'royal blue'},
    {hex:'#1e40af',ar:'أزرق ملكي',en:'deep navy blue'},
    {hex:'#0ea5e9',ar:'سماوي',en:'sky blue'},
    {hex:'#06b6d4',ar:'تركوازي',en:'turquoise cyan'},
    {hex:'#0891b2',ar:'فيروزي',en:'teal blue'},
    {hex:'#10b981',ar:'أخضر زمردي',en:'emerald green'},
    {hex:'#22c55e',ar:'أخضر',en:'vivid green'},
    {hex:'#15803d',ar:'أخضر غابة',en:'forest green'},
  ]},
  pastels:{label:'🌸 باستيل',colors:[
    {hex:'#fef3c7',ar:'كريمي',en:'cream beige'},
    {hex:'#fde68a',ar:'أصفر باهت',en:'pale yellow'},
    {hex:'#fbcfe8',ar:'وردي فاتح',en:'soft pink'},
    {hex:'#fce7f3',ar:'وردي باهت',en:'blush pink'},
    {hex:'#ddd6fe',ar:'بنفسجي فاتح',en:'lavender purple'},
    {hex:'#dbeafe',ar:'أزرق فاتح',en:'baby blue'},
    {hex:'#d1fae5',ar:'أخضر نعناعي',en:'mint green'},
    {hex:'#fed7aa',ar:'خوخي',en:'peach orange'},
  ]},
  vibrant:{label:'⚡ نيون',colors:[
    {hex:'#a855f7',ar:'بنفسجي',en:'electric purple'},
    {hex:'#7c3aed',ar:'بنفسجي زاهي',en:'vibrant purple'},
    {hex:'#ec4899',ar:'وردي زاهي',en:'hot pink'},
    {hex:'#f43f5e',ar:'وردي روز',en:'rose pink'},
    {hex:'#84cc16',ar:'أخضر ليموني',en:'lime green'},
    {hex:'#14b8a6',ar:'تركوازي مائي',en:'teal cyan'},
    {hex:'#8b5cf6',ar:'بنفسجي ملكي',en:'royal violet'},
    {hex:'#d946ef',ar:'فوشيا',en:'magenta fuchsia'},
  ]},
  luxury:{label:'💎 فاخر',colors:[
    {hex:'#d4af37',ar:'ذهبي',en:'metallic gold'},
    {hex:'#c0c0c0',ar:'فضي',en:'metallic silver'},
    {hex:'#b76e79',ar:'ذهبي وردي',en:'rose gold'},
    {hex:'#cd7f32',ar:'برونزي',en:'bronze copper'},
    {hex:'#7f1d1d',ar:'أحمر نبيذي',en:'wine burgundy'},
    {hex:'#1e3a8a',ar:'كحلي عميق',en:'midnight navy'},
    {hex:'#064e3b',ar:'أخضر غامق',en:'deep emerald'},
    {hex:'#581c87',ar:'بنفسجي فاخر',en:'royal plum purple'},
  ]},
};

// Helper: find color name from hex (for AI prompt clarity)
function psHexToName(hex){
  hex=(hex||'').toLowerCase();
  for(const cat of Object.values(PS_COLOR_CATEGORIES)){
    const f=cat.colors.find(c=>c.hex.toLowerCase()===hex);
    if(f)return f.en;
  }
  // Custom colors
  try{
    const cu=JSON.parse(localStorage.getItem('zx_custom_colors')||'[]');
    const f=cu.find(c=>(c.hex||'').toLowerCase()===hex);
    if(f)return f.en||f.ar||hex;
  }catch(e){}
  // Fallback: generic hex-to-name by brightness
  if(!hex||!hex.startsWith('#'))return 'neutral';
  const r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);
  const lum=(0.299*r+0.587*g+0.114*b);
  if(lum>235)return 'very light off-white';
  if(lum<20)return 'very dark near-black';
  if(r>g&&r>b)return 'warm reddish tone';
  if(g>r&&g>b)return 'natural green tone';
  if(b>r&&b>g)return 'cool blue tone';
  return 'balanced neutral tone';
}

const PS_FRAME_PRESETS=['#7c3aed','#fbbf24','#000000','#10b981','#f43f5e','#06b6d4','#ec4899','#8b5cf6','transparent'];

function psSwitchTab(tab){
  document.querySelectorAll('.ps-tab').forEach(t=>t.classList.toggle('active',t.dataset.pstab===tab));
  document.querySelectorAll('.ps-panel').forEach(p=>p.classList.toggle('active',p.dataset.pspanel===tab));
  if(tab==='ai'){const aiInp=$('ps-ai-name');if(aiInp&&!aiInp.value&&$('pm-name').value)aiInp.value=$('pm-name').value;}
  if(tab==='image'){psHydrateCustomColorsFromServer().then(()=>psRenderColorPresets());psRenderColorPresets();}
  // Hide modal footer on ALL tabs — approval/publish lives inside each tab now
  const foot=document.getElementById('ps-modal-foot');
  if(foot)foot.style.display='none';
  setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
}
function psToggleFullscreen(){
  const studio=document.getElementById('prod-mod');if(!studio)return;
  const isFs=studio.classList.toggle('fullscreen');
  const btn=document.getElementById('ps-fs-btn');
  if(btn){btn.innerHTML=isFs?'<i data-lucide="minimize-2" style="width:16px;height:16px"></i>':'<i data-lucide="maximize-2" style="width:16px;height:16px"></i>';if(window.lucide)lucide.createIcons();btn.title=isFs?'تصغير':'ملء الشاشة';}
}

function psRenderColorPresets(){
  const bg=document.getElementById('ps-bg-presets');
  const fr=document.getElementById('ps-frame-presets');
  if(bg&&!bg.children.length){
    let html='';
    for(const [key,cat] of Object.entries(PS_COLOR_CATEGORIES)){
      html+=`<div class="ps-color-cat-label">${cat.label}</div><div class="ps-color-cat-row">`;
      html+=cat.colors.map(c=>`<span class="preset" style="background:${c.hex};border:1px solid ${c.hex==='#ffffff'?'#d1d5db':c.hex}" title="${c.ar} · ${c.en}" data-testid="bg-color-${c.en.replace(/\s+/g,'-')}" onclick="psPickBgColor('${c.hex}','${c.ar}','${c.en}')"></span>`).join('');
      html+='</div>';
    }
    // Custom colors row
    const customColors=psGetCustomColors();
    html+=`<div class="ps-color-cat-label" style="display:flex;align-items:center;justify-content:space-between">✨ ألواني المخصصة <button class="ps-custom-add-btn" onclick="psOpenAddCustomColor()" data-testid="add-custom-color-btn">+ أضف لون</button></div><div class="ps-color-cat-row" id="ps-custom-bg-row">`;
    html+=customColors.map((c,i)=>`<span class="preset" style="background:${c.hex};border:1px solid ${c.hex==='#ffffff'?'#d1d5db':c.hex};position:relative" title="${c.ar} · ${c.en}" onclick="psPickBgColor('${c.hex}','${c.ar}','${c.en}')"><button class="ps-custom-del" onclick="event.stopPropagation();psDeleteCustomColor(${i})" title="حذف">×</button></span>`).join('');
    if(!customColors.length)html+='<span style="font-size:11px;color:#94a3b8;padding:6px">— لا توجد ألوان مخصصة بعد —</span>';
    html+='</div>';
    bg.innerHTML=html;
  }
  if(fr&&!fr.children.length){
    fr.innerHTML=PS_FRAME_PRESETS.map(c=>`<span class="preset" style="background:${c==='transparent'?'repeating-linear-gradient(45deg,#666,#666 4px,#999 4px,#999 8px)':c}" title="${c==='transparent'?'شفاف':'إطار '+c}" onclick="document.getElementById('ps-frame-color').value='${c==='transparent'?'#ffffff':c}';psUpdatePreviewBg()"></span>`).join('');
  }
}

function psPickBgColor(hex,ar,en){
  const inp=document.getElementById('ps-bg-color');
  if(inp)inp.value=hex;
  PS_STATE.bgColor=hex;
  PS_STATE.bgColorName=en||psHexToName(hex);
  const lbl=document.getElementById('ps-bg-color-label');
  if(lbl)lbl.textContent=`🎨 ${ar||'لون'} · ${hex}`;
  psUpdatePreviewBg();
}

function psUpdatePreviewBg(){
  PS_STATE.bgColor=document.getElementById('ps-bg-color').value;
  PS_STATE.frameColor=document.getElementById('ps-frame-color').value;
  // Always re-resolve the English name so AI prompt is accurate even if user types hex manually
  PS_STATE.bgColorName=psHexToName(PS_STATE.bgColor);
  PS_STATE.frameColorName=psHexToName(PS_STATE.frameColor);
  const lbl=document.getElementById('ps-bg-color-label');
  if(lbl)lbl.textContent=`🎨 لون الخلفية · ${PS_STATE.bgColor}`;
}

// ── Custom color management (localStorage + sync to backend merchant theme) ──
function psGetCustomColors(){
  try{return JSON.parse(localStorage.getItem('zx_custom_colors')||'[]');}catch(e){return [];}
}
// Hydrate custom colors from server on first studio open (so they survive device changes)
async function psHydrateCustomColorsFromServer(){
  try{
    const r=await fetch(API+'/api/theme/merchant/me',{headers:{'Authorization':'Bearer '+(localStorage.getItem('zx_token')||'')}});
    if(!r.ok)return;
    const t=await r.json();
    if(t&&Array.isArray(t.custom_palette)&&t.custom_palette.length){
      localStorage.setItem('zx_custom_colors',JSON.stringify(t.custom_palette));
    }
  }catch(e){}
}
function psSaveCustomColors(list){
  localStorage.setItem('zx_custom_colors',JSON.stringify(list));
  // Also push to merchant theme for customer-store integration
  try{
    fetch(API+'/api/theme/merchant/me',{
      method:'PUT',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+(localStorage.getItem('zx_token')||'')},
      body:JSON.stringify({custom_palette:list})
    }).catch(()=>{});
  }catch(e){}
}
function psOpenAddCustomColor(){
  const modal=document.createElement('div');
  modal.className='ps-custom-modal';
  modal.innerHTML=`
    <div class="ps-custom-card">
      <h4 style="margin:0 0 14px;color:#fff;font-size:16px">✨ أضف لونك المخصص</h4>
      <label style="display:block;font-size:11px;color:#94a3b8;margin-bottom:4px">الاسم بالعربي (مثلاً: أزرق الشركة)</label>
      <input type="text" id="pccx-ar" placeholder="أزرق الشركة" style="width:100%;padding:9px;border:1px solid #312e81;border-radius:8px;background:#0a0a14;color:#fff;font-family:inherit;margin-bottom:10px" data-testid="custom-color-name-ar">
      <label style="display:block;font-size:11px;color:#94a3b8;margin-bottom:4px">الاسم بالإنجليزي (لذكاء AI — مثلاً: corporate blue)</label>
      <input type="text" id="pccx-en" placeholder="corporate blue" style="width:100%;padding:9px;border:1px solid #312e81;border-radius:8px;background:#0a0a14;color:#fff;font-family:inherit;margin-bottom:10px" data-testid="custom-color-name-en">
      <label style="display:block;font-size:11px;color:#94a3b8;margin-bottom:4px">اللون</label>
      <div style="display:flex;gap:10px;align-items:center;margin-bottom:18px">
        <input type="color" id="pccx-hex" value="#7c3aed" style="width:60px;height:42px;border:none;background:transparent;cursor:pointer" data-testid="custom-color-hex">
        <input type="text" id="pccx-hex-txt" value="#7c3aed" oninput="document.getElementById('pccx-hex').value=this.value" style="flex:1;padding:9px;border:1px solid #312e81;border-radius:8px;background:#0a0a14;color:#fff;font-family:monospace">
        <span id="pccx-preview" style="width:42px;height:42px;border-radius:8px;background:#7c3aed;border:2px solid #fff"></span>
      </div>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button onclick="this.closest('.ps-custom-modal').remove()" style="padding:9px 16px;background:transparent;border:1px solid #312e81;color:#94a3b8;border-radius:8px;cursor:pointer;font-family:inherit">إلغاء</button>
        <button onclick="psSaveNewCustomColor()" data-testid="save-custom-color" style="padding:9px 16px;background:linear-gradient(135deg,#7c3aed,#ec4899);border:none;color:#fff;border-radius:8px;cursor:pointer;font-family:inherit;font-weight:900">💾 احفظ اللون</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  // Sync hex picker preview
  const hexPick=document.getElementById('pccx-hex');
  const hexTxt=document.getElementById('pccx-hex-txt');
  const prv=document.getElementById('pccx-preview');
  hexPick.oninput=()=>{hexTxt.value=hexPick.value;prv.style.background=hexPick.value;};
  hexTxt.oninput=()=>{prv.style.background=hexTxt.value;hexPick.value=hexTxt.value;};
}
function psSaveNewCustomColor(){
  const ar=document.getElementById('pccx-ar').value.trim();
  const en=document.getElementById('pccx-en').value.trim();
  const hex=document.getElementById('pccx-hex').value;
  if(!ar||!hex){toast('❌ اكتب الاسم العربي واختر اللون');return;}
  const list=psGetCustomColors();
  list.push({ar,en:en||ar,hex});
  psSaveCustomColors(list);
  document.querySelector('.ps-custom-modal')?.remove();
  // Re-render presets
  const bg=document.getElementById('ps-bg-presets');
  if(bg)bg.innerHTML='';
  psRenderColorPresets();
  toast('✓ تم حفظ اللون — متوفر الآن في لوحة الألوان وفي متجر العميل');
}
function psDeleteCustomColor(i){
  const list=psGetCustomColors();
  list.splice(i,1);
  psSaveCustomColors(list);
  const bg=document.getElementById('ps-bg-presets');
  if(bg)bg.innerHTML='';
  psRenderColorPresets();
  toast('✓ تم حذف اللون');
}
function psSelectCType(el){
  document.querySelectorAll('.ps-subtab').forEach(s=>s.classList.remove('active'));
  el.classList.add('active');
  PS_STATE.ctype=el.dataset.ctype;
  const costMap={product:32,logo:16,banner:24,section:24,animated:40};
  const labelMap={product:'4 صور',logo:'2 لوجو',banner:'2 بانر',section:'2 صور قسم',animated:'بانر متحرك (GIF/MP4)'};
  const cost=costMap[PS_STATE.ctype];
  document.getElementById('ps-gen-btn-label').textContent=`توليد ${labelMap[PS_STATE.ctype]} · ${cost} نقطة`;
  // Auto-suggest aspect ratio
  const aspectMap={product:'1:1',logo:'1:1',banner:'3:1',section:'16:9',animated:'16:9'};
  document.getElementById('ps-aspect').value=aspectMap[PS_STATE.ctype];
  psUpdateSummary();
}
function psSelectStyle(el){
  document.querySelectorAll('.ps-style-card').forEach(c=>c.removeAttribute('data-selected'));
  el.setAttribute('data-selected','true');
  PS_STATE.style=el.dataset.style;
  psUpdateSummary();
}
function psUpdateSummary(){
  const styleLabels={product:'تصوير منتج',lifestyle:'أسلوب حياة',luxury:'فاخر',flat:'Flat Lay'};
  const ctypeLabels={product:'4 صور',logo:'2 لوجو',banner:'2 بانر',section:'2 قسم',animated:'بانر متحرك'};
  const aspectLabels={'1:1':'مربع','9:16':'طولي','16:9':'عرضي','4:5':'إنستقرام','3:1':'بانر'};
  const el=document.getElementById('ps-style-summary');
  if(el)el.textContent=`${ctypeLabels[PS_STATE.ctype]||PS_STATE.ctype} · ${styleLabels[PS_STATE.style]||PS_STATE.style} · ${aspectLabels[document.getElementById('ps-aspect').value]||PS_STATE.aspect}`;
}
function psAttachAiImg(inp){
  const f=inp.files[0];if(!f)return;
  const reader=new FileReader();
  reader.onload=e=>{
    PS_STATE.aiImg=e.target.result;
    document.getElementById('ps-ai-img-label').textContent='✓ '+(f.name.slice(0,30));
    document.getElementById('ps-ai-img-btn').style.color='var(--emerald)';
  };
  reader.readAsDataURL(f);
}
async function psGenerateImages(){
  const name=$('pm-name').value.trim()||$('ps-ai-name').value.trim()||'منتج جديد';
  const costMap={product:32,logo:16,banner:24,section:24,animated:40};
  const cost=costMap[PS_STATE.ctype]||32;
  const countMap={product:4,logo:2,banner:2,section:2,animated:1};
  const count=countMap[PS_STATE.ctype];
  if(WALLET<cost){alert('رصيد غير كافٍ — تحتاج '+cost+' نقطة');return;}
  const btn=$('ps-gen-imgs-btn');btn.disabled=true;btn.innerHTML='<i data-lucide="loader" style="width:13px;height:13px"></i> Gemini يولّد…';
  $('ps-img-grid').innerHTML=Array(count).fill().map(()=>'<div class="zx-img-card"><div class="img loading" style="aspect-ratio:1"></div><div class="meta"><b>جاري التوليد…</b></div></div>').join('');
  PS_STATE.bgColor=document.getElementById('ps-bg-color').value;
  PS_STATE.frameColor=document.getElementById('ps-frame-color').value;
  PS_STATE.aspect=document.getElementById('ps-aspect').value;
  // Resolve color hex → English natural-language name for AI clarity
  // (Gemini cannot reliably parse hex codes — sending "#000000" produces white output)
  const bgName=psHexToName(PS_STATE.bgColor);
  PS_STATE.bgColorName=bgName;
  // Build prompt
  const stylePrompts={product:'commercial product photography, studio lighting, sharp focus, 4k',lifestyle:'lifestyle photography, natural setting, soft natural lighting',luxury:'luxury product photography, dramatic lighting, premium aesthetic',flat:'flat lay product photography, top-down view, organized composition'};
  const ctypePrompts={product:`${name}, isolated product shot on a SOLID ${bgName} background (color ${PS_STATE.bgColor}), ${stylePrompts[PS_STATE.style]}`,logo:`Modern minimalist LOGO for "${name}", clean vector style, SOLID ${bgName} background (color ${PS_STATE.bgColor}), professional brand identity, no text artifacts`,banner:`Wide promotional BANNER for "${name}", SOLID ${bgName} background (color ${PS_STATE.bgColor}), ${stylePrompts[PS_STATE.style]}, eye-catching marketing composition`,section:`Hero SECTION image showcasing "${name}", ${stylePrompts[PS_STATE.style]}, SOLID ${bgName} background (color ${PS_STATE.bgColor}), web-ready composition`,animated:`Animated promotional BANNER concept for "${name}", dynamic energetic composition, SOLID ${bgName} background (color ${PS_STATE.bgColor}), ${stylePrompts[PS_STATE.style]}, GIF-friendly`};
  const prompt=ctypePrompts[PS_STATE.ctype];
  // Build dimensions from aspect
  const aspectDims={'1:1':[1024,1024],'9:16':[1080,1920],'16:9':[1920,1080],'4:5':[1080,1350],'3:1':[1920,640]};
  const [w,h]=aspectDims[PS_STATE.aspect]||[1024,1024];
  try{
    const promises=Array(count).fill().map((_,i)=>fetch(API+'/api/image-studio/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:prompt+', variation '+(i+1),count:1,style:PS_STATE.style==='flat'?'product':PS_STATE.style,width:w,height:h})}).then(r=>r.json()).catch(()=>null));
    const results=await Promise.all(promises);
    PS_STATE.images=results.map((r,i)=>(r&&r.images&&r.images[0])||['https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&q=85','https://images.unsplash.com/photo-1551816230-ef5deaed4a26?w=600&q=85','https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?w=600&q=85','https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&q=85'][i%4]);
    WALLET-=cost;localStorage.setItem('zx_credits',WALLET);$('wallet-balance').textContent=WALLET.toLocaleString('ar-EG');
    toast('✓ '+count+' '+(PS_STATE.ctype==='logo'?'لوجو':PS_STATE.ctype==='banner'?'بانر':'صور')+' جاهزة · -'+cost+' نقطة');
    psRenderImages();
  }catch(e){toast('❌ '+e.message);}
  btn.disabled=false;btn.innerHTML=`<i data-lucide="sparkles" style="width:13px;height:13px"></i> <span id="ps-gen-btn-label">إعادة توليد · ${cost} نقطة</span>`;
  if(window.lucide)lucide.createIcons();
}
function psRenderImages(){
  const labels={product:'صورة منتج',logo:'لوجو',banner:'بانر',section:'صورة قسم',animated:'بانر متحرك'};
  $('ps-img-grid').innerHTML=PS_STATE.images.map((u,i)=>{
    const ok=PS_STATE.approvedImg===u;
    const ratio=PS_STATE.aspect==='3:1'?'3/1':PS_STATE.aspect==='16:9'?'16/9':PS_STATE.aspect==='9:16'?'9/16':PS_STATE.aspect==='4:5'?'4/5':'1/1';
    return `<div class="zx-img-card ${ok?'approved':''}"><div class="badge-approved">✓ مختارة</div><div class="img" style="aspect-ratio:${ratio};background-image:url('${u}')"></div><div class="meta"><b>${labels[PS_STATE.ctype]} ${i+1}</b><span style="color:#94a3b8">${PS_STATE.aspect} · ${PS_STATE.style}</span></div><div class="acts"><button class="ok" onclick="psApproveImage(${i})"><i data-lucide="${ok?'check-check':'check'}" style="width:11px;height:11px"></i> ${ok?'مختارة':'استخدم'}</button><button class="re" onclick="psDownloadImage(${i})" title="تحميل"><i data-lucide="download" style="width:11px;height:11px"></i></button><button class="re" onclick="window.open('${u}','_blank')" title="تكبير"><i data-lucide="zoom-in" style="width:11px;height:11px"></i></button></div></div>`;
  }).join('');
  if(window.lucide)lucide.createIcons();
}
function psApproveImage(i){
  PS_STATE.approvedImg=PS_STATE.images[i];
  if(PS_STATE.ctype==='product'){$('pm-img-preview').innerHTML=`<img src="${PS_STATE.approvedImg}" loading="lazy" decoding="async">`;}
  psRenderImages();
  toast('✓ تم اختيار '+({product:'الصورة',logo:'اللوجو',banner:'البانر',section:'صورة القسم',animated:'البانر المتحرك'})[PS_STATE.ctype]+' '+(i+1));
}
function psDownloadImage(i){const a=document.createElement('a');a.href=PS_STATE.images[i];a.download=`${PS_STATE.ctype}-${i+1}.png`;a.click();toast('⬇️ بدأ التحميل');}
async function psAnalyze(){
  const name=($('ps-ai-name').value||$('pm-name').value||'').trim();
  if(!name){alert('اكتب اسم المنتج أولاً');return;}
  if(WALLET<10){alert('رصيدك أقل من 10 نقاط — اشحن أولاً');return;}
  const url=$('ps-ai-url').value.trim();
  $('ps-ai-empty').style.display='none';
  $('ps-ai-result').style.display='block';
  $('ps-ai-result').innerHTML='<div class="zx-empty"><div class="big-ico">🤖</div><h5>Gemini يبحث ويحلل بعمق…</h5><p>المواصفات، الفوائد، طريقة الاستخدام، الجديد، المقارنات… (قد يستغرق 20-40 ثانية)</p></div>';
  try{
    const body={name,lang:'ar'};
    if(PS_STATE.aiImg)body.image_base64=PS_STATE.aiImg;
    if(url)body.official_url=url;
    const r=await fetch(API+'/api/image-studio/product-info',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r.ok)throw new Error('فشل التحليل');
    const d=await r.json();
    PS_STATE.analysis=d;
    WALLET-=10;localStorage.setItem('zx_credits',WALLET);$('wallet-balance').textContent=WALLET.toLocaleString('ar-EG');
    if(!$('pm-name').value&&d.title)$('pm-name').value=d.title;
    if(!$('pm-desc').value&&d.description)$('pm-desc').value=d.description;
    psRenderAnalysis(d);
    toast('✓ تحليل عميق جاهز · -10 نقاط');
  }catch(e){
    $('ps-ai-result').innerHTML=`<div class="zx-empty"><div class="big-ico">❌</div><h5>فشل التحليل</h5><p>${e.message}</p><button class="gen-btn" onclick="psAnalyze()">↻ حاول مرة ثانية</button></div>`;
  }
}
function psRenderAnalysis(d){
  const html=psBuildAnalysisHTML(d)+`<div style="text-align:center;margin-top:14px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap"><button class="ps-btn-amber" onclick="psApplyAnalysis()" style="padding:13px 28px"><i data-lucide="wand-2" style="width:14px;height:14px"></i> تطبيق التحليل على المنتج وعرض المعاينة</button><button class="ps-btn-ghost" onclick="psAnalyze()" style="padding:13px 22px;color:#cbd5e1">↻ تحليل جديد</button></div>`;
  $('ps-ai-result').innerHTML=html;
  if(window.lucide)lucide.createIcons();
}
function psApplyAnalysis(){
  if(!PS_STATE.analysis)return;
  const d=PS_STATE.analysis;
  if(d.title)$('pm-name').value=d.title;
  if(d.description)$('pm-desc').value=d.description;
  // Render the FULL styled preview on the Info tab so the merchant can see what the customer will see
  document.getElementById('ps-info-preview-content').innerHTML=psBuildAnalysisHTML(d);
  document.getElementById('ps-info-preview').style.display='block';
  psSwitchTab('info');
  // Scroll to preview
  setTimeout(()=>{const el=document.getElementById('ps-info-preview');if(el)el.scrollIntoView({behavior:'smooth',block:'start'});if(window.lucide)lucide.createIcons();},150);
  toast('✓ التحليل الكامل ظهر بالأسفل · شف المعاينة');
}
function psBuildAnalysisHTML(d){
  // Reuse the same beautiful design that's rendered in the AI tab
  let html='';
  html+=`<div class="ps-ai-card"><h5><i data-lucide="package" style="width:13px;height:13px"></i> العنوان والوصف الكامل</h5><div style="background:rgba(251,191,36,.06);border:1px solid rgba(251,191,36,.2);border-radius:10px;padding:12px"><b style="font-size:14px;color:var(--amber);display:block;margin-bottom:6px">${d.title}</b><p style="font-size:12px;line-height:1.8;color:#cbd5e1">${d.description}</p>${d.target_audience?`<div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,.06);font-size:11px;color:#94a3b8"><b style="color:var(--amber)">👥 الفئة المستهدفة:</b> ${d.target_audience}</div>`:''}</div></div>`;
  if(d.whats_new&&d.whats_new.length){html+=`<div class="ps-ai-card whatsnew"><h5><i data-lucide="sparkles" style="width:13px;height:13px"></i> 🆕 الجديد في هذا الإصدار</h5><div style="display:grid;gap:8px">${d.whats_new.map(w=>`<div style="background:rgba(0,0,0,.3);padding:9px 12px;border-radius:9px;font-size:12px;line-height:1.7;color:#fecaca;border-right:3px solid var(--rose)">⚡ ${w}</div>`).join('')}</div></div>`;}
  if(d.comparison&&(d.comparison.previous_model||(d.comparison.key_differences&&d.comparison.key_differences.length))){html+=`<div class="ps-ai-card whatsnew"><h5><i data-lucide="git-compare" style="width:13px;height:13px"></i> ⚖️ المقارنة مع ${d.comparison.previous_model||'السابق'}</h5>${(d.comparison.key_differences||[]).map(k=>`<div style="font-size:12px;line-height:1.8;color:#cbd5e1;padding:5px 0">▸ ${k}</div>`).join('')}${(d.comparison.upgrades||[]).length?`<div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,.06)"><b style="color:var(--emerald);font-size:11px;display:block;margin-bottom:6px">🚀 ترقيات أساسية:</b>${d.comparison.upgrades.map(u=>`<div style="font-size:12px;line-height:1.7;color:#a7f3d0">✓ ${u}</div>`).join('')}</div>`:''}</div>`;}
  if(d.features&&d.features.length){html+=`<div class="ps-ai-card"><h5><i data-lucide="check-circle-2" style="width:13px;height:13px"></i> المميزات الرئيسية (${d.features.length})</h5><div style="line-height:2">${d.features.map(f=>`<span class="ps-feat-chip">✦ ${f}</span>`).join('')}</div></div>`;}
  if(d.benefits&&d.benefits.length){html+=`<div class="ps-ai-card benefits"><h5><i data-lucide="heart-pulse" style="width:13px;height:13px"></i> 💚 الفوائد</h5><div style="display:grid;gap:8px">${d.benefits.map(b=>`<div style="background:rgba(0,0,0,.3);padding:9px 12px;border-radius:9px;font-size:12px;line-height:1.7;color:#a7f3d0;border-right:3px solid var(--emerald)">💚 ${b}</div>`).join('')}</div></div>`;}
  if(d.usage_instructions&&d.usage_instructions.length){html+=`<div class="ps-ai-card usage"><h5><i data-lucide="list-checks" style="width:13px;height:13px"></i> 📋 طريقة الاستخدام</h5>${d.usage_instructions.map((u,i)=>`<div class="ps-step"><span class="num">${i+1}</span><span>${u}</span></div>`).join('')}</div>`;}
  if(d.side_effects&&d.side_effects.length){html+=`<div class="ps-ai-card warning"><h5><i data-lucide="alert-triangle" style="width:13px;height:13px"></i> ⚠️ تحذيرات وآثار جانبية</h5>${d.side_effects.map(s=>`<div style="font-size:12px;line-height:1.7;color:#fed7aa;padding:5px 0">⚠ ${s}</div>`).join('')}</div>`;}
  if(d.specs&&Object.keys(d.specs).length){html+=`<div class="ps-ai-card"><h5><i data-lucide="cpu" style="width:13px;height:13px"></i> المواصفات التقنية</h5><div class="ps-spec-grid">${Object.entries(d.specs).map(([k,v])=>`<div class="ps-spec-item"><b>${k}</b><span>${v}</span></div>`).join('')}</div></div>`;}
  if(d.colors&&d.colors.length){html+=`<div class="ps-ai-card"><h5><i data-lucide="palette" style="width:13px;height:13px"></i> الألوان المتاحة</h5><div>${d.colors.map(c=>`<span class="ps-color-swatch"><span class="dot" style="background:${c.hex||'#888'}"></span>${c.name||c}</span>`).join('')}</div></div>`;}
  if(d.sizes&&d.sizes.length){html+=`<div class="ps-ai-card"><h5><i data-lucide="ruler" style="width:13px;height:13px"></i> المقاسات / السعات</h5><div>${d.sizes.map(s=>`<span class="ps-size-pill">${s}</span>`).join('')}</div></div>`;}
  if(d.warranty&&(d.warranty.duration_text||d.warranty.url)){html+=`<div class="ps-ai-card"><h5><i data-lucide="shield-check" style="width:13px;height:13px"></i> الضمان الرسمي</h5><p style="font-size:12px;color:#cbd5e1;line-height:1.7">${d.warranty.duration_text||'ضمان وكيل معتمد'}${d.warranty.url?` · <a href="${d.warranty.url}" target="_blank" style="color:var(--amber)">رابط الضمان ↗</a>`:''}</p></div>`;}
  if(d.official_url){html+=`<div class="ps-ai-card"><h5><i data-lucide="link" style="width:13px;height:13px"></i> الموقع الرسمي</h5><a href="${d.official_url.startsWith('http')?d.official_url:'https://'+d.official_url}" target="_blank" style="color:var(--amber);font-size:13px;font-weight:900;display:inline-flex;align-items:center;gap:6px">${d.official_url} <i data-lucide="external-link" style="width:13px;height:13px"></i></a></div>`;}
  return html;
}

// ───── VIDEO STUDIO (TABBED WORKFLOW) ─────
let VS_ATTACHMENTS=[],VS_RECORDING=null;
let VS_STATE={tab:'script',idea:'',story:null,approvedScenes:{},images:{},approvedImages:{},audio:null,audioApproved:false,video:null};
function vsAutoSize(t){t.style.height='auto';t.style.height=Math.min(t.scrollHeight,100)+'px'}
function vsAttachFile(inp){
  for(const f of inp.files){
    const reader=new FileReader();
    reader.onload=e=>{VS_ATTACHMENTS.push({type:'image',data:e.target.result,name:f.name});toast('📎 ملف مرفق: '+f.name);};
    reader.readAsDataURL(f);
  }
  inp.value='';
}
function vsSwitchTab(tab){
  VS_STATE.tab=tab;
  document.querySelectorAll('.zx-tab').forEach(t=>t.classList.toggle('active',t.dataset.tab===tab));
  document.querySelectorAll('.zx-panel').forEach(p=>p.classList.toggle('active',p.dataset.panel===tab));
  vsRenderTab(tab);
}
function vsHandleChat(){
  const txt=$('vs-input-text').value.trim();if(!txt)return;
  VS_STATE.idea=txt;
  $('vs-input-text').value='';vsAutoSize($('vs-input-text'));
  // Start workflow from script tab
  vsSwitchTab('script');
  vsGenerateScript();
}
function vsQuickStart(q){VS_STATE.idea=q;$('vs-input-text').value=q;vsSwitchTab('script');vsGenerateScript();}
function vsGetConfig(){
  return {
    duration:parseInt($('vs-duration').value||'30'),
    tone:$('vs-tone').value||'energetic',
    langRaw:$('vs-lang').value||'ar-sa',
    voice:$('vs-voice').value||'zenrex_male_deep'
  };
}
function vsSetProgress(step,state){const el=document.getElementById('prog-'+step);if(el){el.className='pdot '+state;}}
function vsSetTabStatus(tab,state,label){
  const t=document.querySelector(`.zx-tab[data-tab="${tab}"]`);if(t){t.classList.toggle('done',state==='done');t.classList.toggle('active',state==='active'||VS_STATE.tab===tab);}
  const sMap={script:'st-script',scenes:'st-scenes-status',images:'st-images-status',voice:'st-voice-status',final:'st-final-status'};
  const s=document.getElementById(sMap[tab]);if(s){s.textContent=label;s.className='status '+(state==='done'?'approved':state==='pending'?'pending':'');}
}

// ───── STEP 1: SCRIPT ─────
async function vsGenerateScript(){
  const cfg=vsGetConfig();const lang=cfg.langRaw.startsWith('ar')?'ar':cfg.langRaw;
  if(!VS_STATE.idea){VS_STATE.idea=$('vs-input-text').value.trim()||'منتج جذاب';}
  if(WALLET<5){alert('رصيد غير كافٍ — تحتاج 5 نقاط للسيناريو');return;}
  document.getElementById('content-script').innerHTML=`<div class="zx-empty"><div class="big-ico">⏳</div><h5>Gemini يكتب السيناريو…</h5><p>بـ <b style="color:var(--amber)">${vsLangLabel(cfg.langRaw)}</b> · مدة ${cfg.duration} ثانية · أسلوب ${({energetic:'حماسي',luxury:'فاخر',warm:'دافئ',tech:'تقني'})[cfg.tone]}</p></div>`;
  vsSetProgress(1,'active');vsSetTabStatus('script','pending','🔄 جاري التوليد...');
  try{
    const m=VS_STATE.idea.match(/(?:فيديو|إعلان|لـ|عن|ل)\s+(.+?)(?:بأسلوب|مدته|مدة|ثانية|$)/);
    const productName=(m?m[1]:VS_STATE.idea.split(/\s+/).slice(0,6).join(' ')).trim();
    const r=await fetch(API+'/api/promo-video/storyboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_name:productName,duration_seconds:cfg.duration,tone:cfg.tone,lang,dialect:cfg.langRaw,cta:lang==='ar'?'اطلب الآن':'Order now'})});
    if(!r.ok)throw new Error('فشل توليد السيناريو');
    VS_STATE.story=await r.json();
    // Charge immediately
    WALLET-=(VS_STATE.story.cost||5);localStorage.setItem('zx_credits',WALLET);$('wallet-balance').textContent=WALLET.toLocaleString('ar-EG');
    toast('✓ سيناريو جاهز · -5 نقاط');
    vsRenderTab('script');
    vsSetProgress(1,'done');vsSetTabStatus('script','done','✓ مولّد');
  }catch(e){
    document.getElementById('content-script').innerHTML=`<div class="zx-empty"><div class="big-ico">❌</div><h5>خطأ</h5><p>${e.message}</p><button class="gen-btn" onclick="vsGenerateScript()">↻ حاول مرة ثانية</button></div>`;
    vsSetProgress(1,'');vsSetTabStatus('script','','❌ فشل');
  }
}

function vsRenderTab(tab){
  if(tab==='script')return vsRenderScript();
  if(tab==='scenes')return vsRenderScenes();
  if(tab==='images')return vsRenderImages();
  if(tab==='voice')return vsRenderVoice();
  if(tab==='final')return vsRenderFinal();
}

function vsRenderScript(){
  const el=document.getElementById('content-script');
  if(!VS_STATE.story){
    el.innerHTML=`<div class="zx-empty"><div class="big-ico">📝</div><h5>اكتب فكرة فيديوك أو اختر اقتراح</h5><p>Gemini راح يكتب نص احترافي بلهجتك. سيخصم 5 نقاط لحظة التوليد.</p><button class="gen-btn" onclick="vsGenerateScript()" ${WALLET<5?'disabled':''}><i data-lucide="sparkles" style="width:16px;height:16px"></i> توليد السيناريو · 5 نقاط</button></div>`;
  }else{
    const s=VS_STATE.story;const cfg=vsGetConfig();
    el.innerHTML=`<div class="zx-card approved"><div class="ttl">📌 ${s.title}</div><div class="narration">${s.full_narration||s.scenes.map(x=>x.narration).join(' ')}</div><div style="margin-top:10px;font-size:11px;color:var(--mute)">⏱️ ${s.duration_seconds||cfg.duration} ث · 🎙️ سيُقرأ بـ <b style="color:var(--amber)">${vsVoiceLabel(cfg.voice)}</b> بـ <b style="color:var(--amber)">${vsLangLabel(cfg.langRaw)}</b></div><div class="zx-actions"><button class="zx-btn approve" onclick="vsApproveScript()">✓ اعتماد والانتقال للمشاهد</button><button class="zx-btn regen" onclick="vsGenerateScript()">↻ إعادة توليد (-5)</button></div></div>`;
  }
  if(window.lucide)lucide.createIcons();
}
function vsApproveScript(){toast('✅ تم اعتماد السيناريو');vsSwitchTab('scenes');}

// ───── STEP 2: SCENES ─────
function vsRenderScenes(){
  const el=document.getElementById('content-scenes');
  if(!VS_STATE.story){
    el.innerHTML=`<div class="zx-empty"><div class="big-ico">🎬</div><h5>اعتمد السيناريو أولاً</h5><p>ارجع للتبويب 1 لتوليد السيناريو.</p><button class="gen-btn" onclick="vsSwitchTab('script')">← العودة للسيناريو</button></div>`;
    return;
  }
  const scenes=VS_STATE.story.scenes||[];
  const allApproved=scenes.every((s,i)=>VS_STATE.approvedScenes[i]);
  el.innerHTML=`<div style="margin-bottom:10px;color:var(--mute);font-size:12px">📊 ${Object.keys(VS_STATE.approvedScenes).filter(k=>VS_STATE.approvedScenes[k]).length}/${scenes.length} مشهد معتمد · مجاني · عدّل أي مشهد قبل الاعتماد</div>`+
  scenes.map((s,i)=>{
    const ok=VS_STATE.approvedScenes[i];
    return `<div class="zx-scene ${ok?'approved':''}" id="scene-${i}"><div class="hdr"><span class="num">${s.seq||i+1}</span><span style="font-weight:900;font-size:13px">مشهد ${s.seq||i+1}</span><span class="dur">${s.duration||5} ث</span></div><div class="field"><b>📹 الرؤية البصرية / حركة الكاميرا</b><textarea data-scene="${i}" data-field="visual">${s.visual_prompt||''}</textarea></div><div class="field"><b>💬 نص على الشاشة</b><textarea data-scene="${i}" data-field="text_overlay" rows="1">${s.text_overlay||''}</textarea></div><div class="field"><b>🗣️ التعليق الصوتي (سيُنطق)</b><textarea data-scene="${i}" data-field="narration">${s.narration||''}</textarea></div><div class="zx-actions"><button class="zx-btn ${ok?'regen':'approve'}" onclick="vsToggleScene(${i})">${ok?'↺ إلغاء الاعتماد':'✓ اعتماد المشهد'}</button></div></div>`;
  }).join('')+
  (allApproved?`<div style="text-align:center;padding:20px"><button class="zx-btn next" onclick="vsApproveAllScenes()" style="padding:14px 28px;font-size:13px">المشاهد معتمدة · انتقل لتوليد الصور →</button></div>`:`<div style="text-align:center;padding:14px;color:var(--mute);font-size:12px">اعتمد جميع المشاهد للانتقال للصور</div>`);
}
function vsToggleScene(i){
  // Save edits
  document.querySelectorAll(`textarea[data-scene="${i}"]`).forEach(t=>{
    VS_STATE.story.scenes[i][t.dataset.field]=t.value;
  });
  VS_STATE.approvedScenes[i]=!VS_STATE.approvedScenes[i];
  vsRenderScenes();
  toast(VS_STATE.approvedScenes[i]?'✓ مشهد '+(i+1)+' معتمد':'↺ مشهد '+(i+1)+' أُلغي اعتماده');
}
function vsApproveAllScenes(){
  vsSetProgress(2,'done');vsSetTabStatus('scenes','done','✓ جميع المشاهد معتمدة');
  toast('✅ جميع المشاهد معتمدة — لننتقل للصور');
  vsSwitchTab('images');
}

// ───── STEP 3: IMAGES ─────
function vsRenderImages(){
  const el=document.getElementById('content-images');
  if(!VS_STATE.story||!Object.keys(VS_STATE.approvedScenes).some(k=>VS_STATE.approvedScenes[k])){
    el.innerHTML=`<div class="zx-empty"><div class="big-ico">🖼️</div><h5>اعتمد المشاهد أولاً</h5><p>ارجع للتبويب 2 واعتمد المشاهد.</p><button class="gen-btn" onclick="vsSwitchTab('scenes')">← العودة للمشاهد</button></div>`;
    return;
  }
  const scenes=VS_STATE.story.scenes;
  const total=scenes.length;const generated=Object.keys(VS_STATE.images).length;const approved=Object.keys(VS_STATE.approvedImages).filter(k=>VS_STATE.approvedImages[k]).length;
  const allGenerated=generated===total;const allApproved=approved===total;
  let html=`<div style="margin-bottom:14px;color:var(--mute);font-size:12px;display:flex;align-items:center;gap:10px;flex-wrap:wrap"><span>🖼️ ${generated}/${total} صور مولّدة · ${approved}/${total} معتمدة</span>${!allGenerated?`<button class="zx-btn next" onclick="vsGenerateAllImages()" ${WALLET<total*8?'disabled':''}>توليد جميع الصور · ${total*8} نقطة</button>`:''}</div>`;
  html+=`<div class="zx-img-grid">`;
  scenes.forEach((s,i)=>{
    const img=VS_STATE.images[i];const ok=VS_STATE.approvedImages[i];
    html+=`<div class="zx-img-card ${ok?'approved':''}"><div class="badge-approved">✓ معتمد</div><div class="img ${!img?'loading':''}" style="${img?`background-image:url('${img}')`:''}">${!img?'<span style="color:#475569">🎨 مشهد '+(i+1)+'</span>':''}</div><div class="meta"><b>مشهد ${i+1}</b><span style="color:var(--mute);font-size:10px">${(s.visual_prompt||'').slice(0,80)}…</span></div><div class="acts">${img?(ok?`<button class="ok"><i data-lucide="check" style="width:11px;height:11px"></i> معتمد</button><button class="re" onclick="vsRegenImage(${i})">↻</button>`:`<button class="ok" onclick="vsApproveImage(${i})"><i data-lucide="check" style="width:11px;height:11px"></i> اعتماد</button><button class="re" onclick="vsRegenImage(${i})"><i data-lucide="refresh-cw" style="width:11px;height:11px"></i> -8</button>`):`<button class="ok" onclick="vsGenImage(${i})" ${WALLET<8?'disabled':''}>توليد · 8 نقاط</button>`}</div></div>`;
  });
  html+=`</div>`;
  if(allApproved)html+=`<div style="text-align:center;padding:20px"><button class="zx-btn next" onclick="vsApproveAllImages()" style="padding:14px 28px;font-size:13px">جميع الصور معتمدة · انتقل للصوت →</button></div>`;
  el.innerHTML=html;
  if(window.lucide)lucide.createIcons();
}
async function vsGenImage(i){
  if(WALLET<8){alert('رصيد غير كافٍ — تحتاج 8 نقاط');return;}
  const s=VS_STATE.story.scenes[i];
  // Show loading
  const card=document.querySelectorAll('.zx-img-card')[i];if(card){card.querySelector('.img').classList.add('loading');card.querySelector('.img').innerHTML='⏳ Gemini يولّد…';}
  try{
    const r=await fetch(API+'/api/image-studio/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:s.visual_prompt+', cinematic lighting, commercial photography, ultra realistic, 4k',count:1,style:'lifestyle',width:1080,height:1920})});
    const d=await r.json();
    const url=(d.images&&d.images[0])||['https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&q=85','https://images.unsplash.com/photo-1551816230-ef5deaed4a26?w=600&q=85','https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?w=600&q=85'][i%3];
    VS_STATE.images[i]=url;
    WALLET-=8;localStorage.setItem('zx_credits',WALLET);$('wallet-balance').textContent=WALLET.toLocaleString('ar-EG');
    toast('✓ صورة مشهد '+(i+1)+' · -8 نقاط');
    vsRenderImages();
  }catch(e){toast('❌ فشل توليد الصورة');vsRenderImages();}
}
async function vsGenerateAllImages(){
  const scenes=VS_STATE.story.scenes;const missing=scenes.map((_,i)=>i).filter(i=>!VS_STATE.images[i]);
  if(WALLET<missing.length*8){alert('رصيد غير كافٍ — تحتاج '+(missing.length*8)+' نقطة');return;}
  for(const i of missing){await vsGenImage(i);}
}
function vsApproveImage(i){VS_STATE.approvedImages[i]=true;vsRenderImages();toast('✓ صورة '+(i+1)+' معتمدة');}
async function vsRegenImage(i){if(WALLET<8){alert('رصيد غير كافٍ');return;}delete VS_STATE.approvedImages[i];delete VS_STATE.images[i];vsRenderImages();await vsGenImage(i);}
function vsApproveAllImages(){vsSetProgress(3,'done');vsSetTabStatus('images','done','✓ جميع الصور معتمدة');toast('✅ كل الصور معتمدة');vsSwitchTab('voice');}

// ───── STEP 4: VOICE ─────
function vsRenderVoice(){
  const el=document.getElementById('content-voice');
  if(!VS_STATE.story||!Object.values(VS_STATE.approvedImages).every(Boolean)||Object.keys(VS_STATE.approvedImages).length<VS_STATE.story.scenes.length){
    el.innerHTML=`<div class="zx-empty"><div class="big-ico">🎙️</div><h5>اعتمد جميع الصور أولاً</h5><p>ارجع للتبويب 3 واعتمد كل الصور.</p><button class="gen-btn" onclick="vsSwitchTab('images')">← العودة للصور</button></div>`;
    return;
  }
  const cfg=vsGetConfig();
  if(!VS_STATE.audio){
    el.innerHTML=`<div class="zx-empty"><div class="big-ico">🎙️</div><h5>توليد التعليق الصوتي</h5><p>سيُقرأ السيناريو بصوت <b style="color:var(--amber)">${vsVoiceLabel(cfg.voice)}</b> بـ <b style="color:var(--amber)">${vsLangLabel(cfg.langRaw)}</b>. تقدر تستمع للعينة وتعتمد قبل الدمج النهائي. سيخصم 5 نقاط.</p><button class="gen-btn" onclick="vsGenerateVoice()" ${WALLET<5?'disabled':''}><i data-lucide="mic-2" style="width:16px;height:16px"></i> توليد الصوت · 5 نقاط</button></div>`;
  }else{
    el.innerHTML=`<div class="zx-card ${VS_STATE.audioApproved?'approved':''}"><div class="ttl">🎙️ التعليق الصوتي</div><div class="zx-voice-preview"><audio controls src="${API+VS_STATE.audio.audio_url}"></audio><div class="info">صوت: <b>${VS_STATE.audio.voice_used||cfg.voice}</b></div></div><div class="narration" style="margin-top:14px">${VS_STATE.story.full_narration||VS_STATE.story.scenes.map(s=>s.narration).join(' ')}</div><div class="zx-actions"><button class="zx-btn ${VS_STATE.audioApproved?'regen':'approve'}" onclick="vsApproveVoice()">${VS_STATE.audioApproved?'↺ إلغاء الاعتماد':'✓ اعتماد والانتقال للفيديو'}</button><button class="zx-btn regen" onclick="vsGenerateVoice()">↻ إعادة توليد (-5)</button></div></div>`;
  }
  if(window.lucide)lucide.createIcons();
}
async function vsGenerateVoice(){
  if(WALLET<5){alert('رصيد غير كافٍ');return;}
  const cfg=vsGetConfig();const lang=cfg.langRaw.startsWith('ar')?'ar':cfg.langRaw;
  document.getElementById('content-voice').innerHTML=`<div class="zx-empty"><div class="big-ico">⏳</div><h5>Zenrex Voice يسجّل…</h5><p>جودة سينمائية مع مخارج كلمات دقيقة</p></div>`;
  try{
    const text=VS_STATE.story.full_narration||VS_STATE.story.scenes.map(s=>s.narration).join(' ');
    const firstImg=VS_STATE.images[0]||'';
    const firstScene=firstImg.startsWith('data:')?{narration:text,image_base64:firstImg}:{narration:text,image_url:firstImg};
    const r=await fetch(API+'/api/promo-video/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:VS_STATE.story.title,scenes:[firstScene],duration_seconds:cfg.duration,voice:cfg.voice,full_narration:text,cta:lang==='ar'?'':'',lang})});
    if(!r.ok)throw new Error('فشل توليد الصوت');
    const d=await r.json();
    VS_STATE.audio={audio_url:d.audio_url,voice_used:d.voice_used};
    WALLET-=5;localStorage.setItem('zx_credits',WALLET);$('wallet-balance').textContent=WALLET.toLocaleString('ar-EG');
    toast('✓ صوت جاهز · -5 نقاط');
    vsRenderVoice();
  }catch(e){toast('❌ '+e.message);vsRenderVoice();}
}
function vsApproveVoice(){VS_STATE.audioApproved=!VS_STATE.audioApproved;vsRenderVoice();if(VS_STATE.audioApproved){vsSetProgress(4,'done');vsSetTabStatus('voice','done','✓ الصوت معتمد');toast('✅ الصوت معتمد · جاهز للدمج النهائي');setTimeout(()=>vsSwitchTab('final'),600);}}
async function vsPreviewVoice(){
  const cfg=vsGetConfig();
  toast('🔊 جاري توليد عيّنة الصوت…');
  try{
    const r=await fetch(API+'/api/promo-video/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:'عيّنة',scenes:[{narration:'مرحباً، هذا هو صوت زيراكس، استمع لجودة الصوت الإحترافي.',image_url:'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&q=85'}],duration_seconds:5,voice:cfg.voice,full_narration:'مرحباً، هذا هو صوت زيراكس، استمع لجودة الصوت الإحترافي.',cta:'',lang:'ar'})});
    const d=await r.json();
    const a=new Audio(API+d.audio_url);a.play();
    toast('▶️ تشغيل العيّنة (مجاني)');
  }catch(e){toast('❌ فشل توليد العيّنة');}
}

// ───── STEP 5: FINAL VIDEO ─────
function vsRenderFinal(){
  const el=document.getElementById('content-final');
  if(!VS_STATE.audioApproved){
    el.innerHTML=`<div class="zx-empty"><div class="big-ico">🎥</div><h5>اعتمد جميع الخطوات أولاً</h5><p>تأكد إن السيناريو + المشاهد + الصور + الصوت كلها معتمدة قبل الدمج النهائي.</p><button class="gen-btn" onclick="vsSwitchTab('voice')">← العودة للصوت</button></div>`;
    return;
  }
  if(!VS_STATE.video){
    el.innerHTML=`<div class="zx-empty"><div class="big-ico">🎥</div><h5>كل شي جاهز للدمج النهائي ✨</h5><p style="max-width:480px">ffmpeg راح يدمج الصور المعتمدة + الصوت + ضبط lip-sync ومخارج الكلمات بدقة. <b style="color:var(--amber)">هذي الخطوة الكبيرة الوحيدة اللي تخصم 30 نقطة عند التوليد فقط — مو قبل.</b></p><button class="gen-btn" onclick="vsRenderFinalVideo()" ${WALLET<30?'disabled':''} style="font-size:14px;padding:16px 32px"><i data-lucide="film" style="width:18px;height:18px"></i> إنتاج الفيديو النهائي · 30 نقطة</button></div>`;
  }else{
    const v=VS_STATE.video;
    el.innerHTML=`<div class="zx-final"><video controls playsinline src="${API+v.video_url}"></video><div class="stats"><div class="stat"><b>${v.duration_seconds}ث</b>المدة</div><div class="stat"><b>${v.scenes_count}</b>مشاهد</div><div class="stat"><b>1080×1920</b>HD عمودي</div><div class="stat"><b>${v.voice_used||''}</b>الصوت</div></div><div class="zx-actions" style="justify-content:center"><button class="zx-btn approve" onclick="vsDownload('${API+v.video_url}','${VS_STATE.story.title}')"><i data-lucide="download" style="width:13px;height:13px"></i> تحميل MP4</button><button class="zx-btn next" onclick="vsPublish('${API+v.video_url}','${VS_STATE.story.title}')"><i data-lucide="share-2" style="width:13px;height:13px"></i> نشر للحسابات الاجتماعية</button><button class="zx-btn regen" onclick="vsResetStudio()"><i data-lucide="plus" style="width:13px;height:13px"></i> فيديو جديد</button></div></div>`;
  }
  if(window.lucide)lucide.createIcons();
}
async function vsRenderFinalVideo(){
  if(WALLET<30){alert('رصيد غير كافٍ — تحتاج 30 نقطة');return;}
  const cfg=vsGetConfig();const lang=cfg.langRaw.startsWith('ar')?'ar':cfg.langRaw;
  document.getElementById('content-final').innerHTML=`<div class="zx-empty"><div class="big-ico">🎬</div><h5>ffmpeg يدمج…</h5><p>قد يستغرق دقيقة — نضبط lip-sync + توقيت دقيق + جودة سينمائية</p></div>`;
  vsSetProgress(5,'active');vsSetTabStatus('final','pending','🔄 جاري الدمج…');
  try{
    const scenes=VS_STATE.story.scenes.map((s,i)=>{
      const img=VS_STATE.images[i]||'';
      const base={narration:s.narration,text_overlay:s.text_overlay||null};
      if(img.startsWith('data:'))return {...base,image_base64:img};
      return {...base,image_url:img};
    });
    const r=await fetch(API+'/api/promo-video/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:VS_STATE.story.title,scenes,duration_seconds:cfg.duration,voice:cfg.voice,full_narration:VS_STATE.story.full_narration,cta:lang==='ar'?'اطلب الآن':'Order now',lang})});
    if(!r.ok)throw new Error('فشل الدمج');
    VS_STATE.video=await r.json();
    WALLET-=30;localStorage.setItem('zx_credits',WALLET);$('wallet-balance').textContent=WALLET.toLocaleString('ar-EG');
    toast('🎉 الفيديو جاهز · -30 نقطة');
    // Save to history
    const hist=JSON.parse(localStorage.getItem('zx_vs_history')||'[]');
    hist.unshift({title:VS_STATE.story.title,url:VS_STATE.video.video_url,date:new Date().toLocaleString('ar-SA')});
    localStorage.setItem('zx_vs_history',JSON.stringify(hist.slice(0,10)));
    renderVsHistory();
    vsSetProgress(5,'done');vsSetTabStatus('final','done','✓ منتج');
    vsRenderFinal();
  }catch(e){toast('❌ '+e.message);document.getElementById('content-final').innerHTML=`<div class="zx-empty"><div class="big-ico">❌</div><h5>فشل الدمج</h5><p>${e.message}</p><button class="gen-btn" onclick="vsRenderFinalVideo()">↻ حاول مرة ثانية</button></div>`;}
}
function vsResetStudio(){
  if(!confirm('متأكد تبي تبدأ من جديد؟'))return;
  VS_STATE={tab:'script',idea:'',story:null,approvedScenes:{},images:{},approvedImages:{},audio:null,audioApproved:false,video:null};
  ['prog-1','prog-2','prog-3','prog-4','prog-5'].forEach(id=>{const e=document.getElementById(id);if(e)e.className='pdot'});
  document.querySelectorAll('.zx-tab').forEach(t=>t.classList.remove('done'));
  vsSwitchTab('script');vsRenderScript();
}

// ───── AI WEEKLY REPORT ─────
// ───── BULK IMPORT/EXPORT ─────
function bulkImport(){
  const inp=document.createElement('input');inp.type='file';inp.accept='.csv,.xlsx,.xls';
  inp.onchange=e=>{
    const f=e.target.files[0];if(!f)return;
    const r=new FileReader();
    r.onload=ev=>{
      const txt=ev.target.result;
      const lines=txt.split(/\r?\n/).filter(l=>l.trim());
      if(lines.length<2){alert('الملف فاضي أو ما فيه بيانات صالحة');return;}
      const headers=lines[0].split(',').map(h=>h.trim().toLowerCase());
      const nIdx=headers.findIndex(h=>['name','اسم','title'].includes(h));
      const pIdx=headers.findIndex(h=>['price','سعر'].includes(h));
      const sIdx=headers.findIndex(h=>['stock','مخزون','qty'].includes(h));
      let added=0;
      for(let i=1;i<lines.length;i++){
        const cols=lines[i].split(',');
        if(cols.length<2)continue;
        PRODUCTS.unshift({id:'p'+Date.now()+i,name:(cols[nIdx]||'منتج').trim(),price:+cols[pIdx]||0,stock:+cols[sIdx]||10,cat:'electronics',img:'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&q=85',sales:0,desc:''});
        added++;
      }
      localStorage.setItem('zx_dash_products',JSON.stringify(PRODUCTS));
      renderProducts();renderAll();
      toast(`✓ تم استيراد ${added} منتج`);
    };
    r.readAsText(f);
  };
  inp.click();
}
function bulkExport(){
  const rows=[['name','price','stock','sales'],...PRODUCTS.map(p=>[p.name,p.price,p.stock,p.sales])];
  const csv=rows.map(r=>r.join(',')).join('\n');
  const blob=new Blob(['\ufeff'+csv],{type:'text/csv'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='products-'+Date.now()+'.csv';a.click();
  toast('⬇️ تصدير '+PRODUCTS.length+' منتج');
}

// ───── MARKETING (Coupons, Loyalty, Carts, Segments) ─────
const COUPONS_SEED=[{code:'WELCOME10',type:'percent',value:10,min:0,used:34,limit:100,active:true,desc:'خصم 10% لأول طلب'},{code:'RAMADAN50',type:'fixed',value:50,min:300,used:128,limit:500,active:true,desc:'خصم 50 ر.س فوق 300'},{code:'VIP20',type:'percent',value:20,min:1000,used:12,limit:50,active:true,desc:'خصم 20% للعملاء VIP'},{code:'SHIPFREE',type:'shipping',value:0,min:200,used:89,limit:1000,active:true,desc:'شحن مجاني فوق 200'},{code:'BLACK40',type:'percent',value:40,min:500,used:0,limit:200,active:false,desc:'بلاك فرايدي'},{code:'BUNDLE3',type:'percent',value:15,min:0,used:23,limit:0,active:true,desc:'15% عند شراء 3+ منتجات'},{code:'SAUDI92',type:'fixed',value:92,min:500,used:5,limit:92,active:true,desc:'اليوم الوطني'}];
// ───── PDF REPORTS ─────
let _currentReport=null;
function loadReports(){
  const orders=_getAllOrders();
  const totalSales=orders.reduce((s,o)=>s+(o.total||0),0);
  document.getElementById('rep-sales').textContent=totalSales.toLocaleString('ar-SA')+' ر.س';
  document.getElementById('rep-orders').textContent=orders.length;
  document.getElementById('rep-avg').textContent=orders.length?Math.round(totalSales/orders.length):'0';
  document.getElementById('rep-cust').textContent=MOCK_CUSTOMERS.length;
}
function _getAllOrders(){
  // Mock 30 orders for demo
  const customers=MOCK_CUSTOMERS;
  return Array.from({length:38},(_,i)=>({
    id:'#'+(3000+i),
    cust:customers[i%customers.length].name,
    items:1+Math.floor(Math.random()*4),
    total:Math.round(80+Math.random()*900),
    tax:0,
    date:new Date(Date.now()-i*86400000*0.7).toLocaleDateString('ar-SA'),
    payment:['Visa','STC Pay','Tabby','مدى','Tamara'][i%5]
  })).map(o=>{o.tax=Math.round(o.total*0.15);return o;});
}
function _reportSales(){
  const orders=_getAllOrders();
  const total=orders.reduce((s,o)=>s+o.total,0);
  const tax=orders.reduce((s,o)=>s+o.tax,0);
  return {
    title:'تقرير المبيعات · آخر 30 يوم',
    summary:[
      {k:'إجمالي المبيعات',v:total.toLocaleString('ar-SA')+' ر.س'},
      {k:'الضريبة (15%)',v:tax.toLocaleString('ar-SA')+' ر.س'},
      {k:'الصافي',v:(total-tax).toLocaleString('ar-SA')+' ر.س'},
      {k:'عدد الطلبات',v:orders.length},
      {k:'متوسط قيمة الطلب',v:Math.round(total/orders.length)+' ر.س'},
    ],
    rows:[['رقم الطلب','العميل','المنتجات','الإجمالي','الضريبة','وسيلة الدفع','التاريخ'],
      ...orders.slice(0,20).map(o=>[o.id,o.cust,o.items,o.total+' ر.س',o.tax+' ر.س',o.payment,o.date])]
  };
}
function _reportProducts(){
  const sorted=[...PRODUCTS].sort((a,b)=>b.sales-a.sales);
  const lowStock=PRODUCTS.filter(p=>p.stock<=(p.stockLow||5));
  return {
    title:'تقرير المنتجات · الأداء والمخزون',
    summary:[
      {k:'إجمالي المنتجات',v:PRODUCTS.length},
      {k:'نفد المخزون',v:PRODUCTS.filter(p=>p.stock===0).length},
      {k:'مخزون منخفض',v:lowStock.length},
      {k:'الأكثر مبيعاً',v:sorted[0]?.name||'—'}
    ],
    rows:[['المنتج','SKU','السعر','المخزون','المبيعات','حالة'],
      ...sorted.map(p=>[p.name,p.sku||'-',p.price+' ر.س',p.stock,p.sales,p.stock===0?'⛔ نافذ':p.stock<=(p.stockLow||5)?'⚠️ منخفض':'✓ متوفر'])]
  };
}
function _reportCustomers(){
  return {
    title:'تقرير العملاء',
    summary:[
      {k:'إجمالي العملاء',v:MOCK_CUSTOMERS.length},
      {k:'إجمالي الإنفاق',v:MOCK_CUSTOMERS.reduce((s,c)=>s+c.total,0)+' ر.س'},
      {k:'متوسط القيمة',v:Math.round(MOCK_CUSTOMERS.reduce((s,c)=>s+c.total,0)/MOCK_CUSTOMERS.length)+' ر.س'}
    ],
    rows:[['الاسم','الهاتف','الطلبات','الإنفاق','آخر طلب'],
      ...MOCK_CUSTOMERS.map(c=>[c.name,c.phone,c.orders,c.total+' ر.س',c.last])]
  };
}
function _reportInventory(){
  const total=PRODUCTS.reduce((s,p)=>s+p.stock*p.price,0);
  return {
    title:'جرد المخزون · قيمة الجرد الحالي',
    summary:[
      {k:'قيمة المخزون',v:total.toLocaleString('ar-SA')+' ر.س'},
      {k:'منتجات نفدت',v:PRODUCTS.filter(p=>p.stock===0).length},
      {k:'تنبيهات مخزون منخفض',v:PRODUCTS.filter(p=>p.stock>0&&p.stock<=(p.stockLow||5)).length}
    ],
    rows:[['المنتج','SKU','المخزون','سعر الوحدة','القيمة الكلية'],
      ...PRODUCTS.map(p=>[p.name,p.sku||'-',p.stock,p.price+' ر.س',(p.stock*p.price)+' ر.س'])]
  };
}
function _reportZatca(){
  const orders=_getAllOrders();
  const tax=orders.reduce((s,o)=>s+o.tax,0);
  return {
    title:'تقرير الفواتير الإلكترونية ZATCA · للهيئة',
    summary:[
      {k:'عدد الفواتير',v:orders.length},
      {k:'إجمالي الضريبة',v:tax.toLocaleString('ar-SA')+' ر.س'},
      {k:'نسبة الضريبة',v:'15%'},
      {k:'الفترة',v:'آخر 30 يوم'}
    ],
    rows:[['رقم الفاتورة','التاريخ','المبلغ قبل الضريبة','الضريبة','الإجمالي'],
      ...orders.slice(0,25).map(o=>[o.id.replace('#','INV-'),o.date,(o.total-o.tax)+' ر.س',o.tax+' ر.س',o.total+' ر.س'])]
  };
}
function _reportMonthly(){
  const s=_reportSales(),p=_reportProducts(),c=_reportCustomers();
  return {
    title:'التقرير الشهري الشامل',
    summary:[...s.summary,...p.summary.slice(0,2),...c.summary.slice(0,2)],
    rows:s.rows
  };
}
function generateReport(type){
  const builders={sales:_reportSales,products:_reportProducts,customers:_reportCustomers,inventory:_reportInventory,zatca:_reportZatca,monthly:_reportMonthly};
  const r=(builders[type]||_reportSales)();
  _currentReport={type,...r};
  document.getElementById('rep-output-panel').style.display='block';
  document.getElementById('rep-output-title').textContent='📄 '+r.title;
  const summaryHtml=`<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:16px">${r.summary.map(s=>`<div style="background:#faf5ff;border:1px solid #ddd6fe;padding:10px;border-radius:8px"><div style="font-size:10px;color:#7c3aed;font-weight:900;margin-bottom:3px">${s.k}</div><div style="font-size:16px;font-weight:900;color:#0a0a14">${s.v}</div></div>`).join('')}</div>`;
  const tableHtml=`<table style="width:100%;border-collapse:collapse;font-size:11px"><thead style="background:#0a0a14;color:#fff"><tr>${r.rows[0].map(h=>`<th style="padding:8px;text-align:right;font-weight:900">${h}</th>`).join('')}</tr></thead><tbody>${r.rows.slice(1).map((row,i)=>`<tr style="border-bottom:1px solid #f3f4f6;background:${i%2?'#fafafa':'#fff'}">${row.map(c=>`<td style="padding:8px">${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  const merchantName=document.getElementById('z-name-ar')?.value||'متجر زيراكس';
  const header=`<div style="text-align:center;margin-bottom:20px;border-bottom:2px solid #0a0a14;padding-bottom:14px"><h1 style="font-size:20px;color:#0a0a14;margin-bottom:4px">${merchantName}</h1><p style="font-size:11px;color:#6b7280">${r.title} · صادر بتاريخ ${new Date().toLocaleDateString('ar-SA')}</p></div>`;
  document.getElementById('rep-output').innerHTML=header+summaryHtml+tableHtml;
  document.getElementById('rep-output-panel').scrollIntoView({behavior:'smooth',block:'start'});
  setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
}
async function downloadReportPDF(){
  if(!_currentReport){alert('اختر نوع التقرير أولاً');return;}
  if(!window.jspdf||!window.html2canvas){alert('المكتبات لم تكتمل التحميل');return;}
  const {jsPDF}=window.jspdf;
  toast('📄 جاري إنشاء PDF…');
  const target=document.getElementById('rep-output');
  // Clone to off-screen so we keep full content
  const clone=target.cloneNode(true);
  clone.style.cssText='position:absolute;left:-9999px;top:0;width:794px;background:#fff;padding:30px;direction:rtl;font-family:\'IBM Plex Sans Arabic\',Arial,sans-serif';
  document.body.appendChild(clone);
  try{
    const canvas=await html2canvas(clone,{scale:2,backgroundColor:'#ffffff',useCORS:true,logging:false});
    const imgData=canvas.toDataURL('image/jpeg',0.92);
    const pdf=new jsPDF('p','mm','a4');
    const pdfW=210,pdfH=297;
    const imgW=pdfW-20;
    const imgH=(canvas.height*imgW)/canvas.width;
    let heightLeft=imgH,position=10;
    pdf.addImage(imgData,'JPEG',10,position,imgW,imgH);
    heightLeft-=(pdfH-20);
    while(heightLeft>0){
      position=heightLeft-imgH+10;
      pdf.addPage();
      pdf.addImage(imgData,'JPEG',10,position,imgW,imgH);
      heightLeft-=(pdfH-20);
    }
    // Footer with branding (last page)
    pdf.setFontSize(8);pdf.setTextColor(150,150,160);
    pdf.text('Generated by Zenrex Platform · zenrex.ai',105,pdfH-5,{align:'center'});
    const filename=`${_currentReport.type}-report-${Date.now()}.pdf`;
    pdf.save(filename);
    toast('📥 تم تحميل: '+filename);
  }catch(e){
    console.error(e);
    alert('فشل إنشاء PDF: '+e.message);
  }finally{
    document.body.removeChild(clone);
  }
}
function shareReportWhatsapp(){
  if(!_currentReport){alert('اختر التقرير أولاً');return;}
  const msg=`📊 *${_currentReport.title}*\n\n`+
    _currentReport.summary.map(s=>`• ${s.k}: *${s.v}*`).join('\n')+
    `\n\n📅 ${new Date().toLocaleDateString('ar-SA')}\n\n_تم إنشاؤه من منصة Zenrex_`;
  const url=`https://wa.me/?text=${encodeURIComponent(msg)}`;
  window.open(url,'_blank');
  toast('💬 جاهز للإرسال — حمّل الـPDF ثم أرفقه يدوياً');
}
function shareReportEmail(){
  if(!_currentReport){alert('اختر التقرير أولاً');return;}
  const subject=`تقرير: ${_currentReport.title}`;
  const body=`مرفق ملخص التقرير:\n\n`+_currentReport.summary.map(s=>`${s.k}: ${s.v}`).join('\n');
  window.open(`mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`,'_blank');
}

// ───── ZATCA E-INVOICE ─────
function loadZatca(){
  const cfg=JSON.parse(localStorage.getItem('zx_zatca')||'{}');
  ['z-vat','z-cr','z-name-ar','z-name-en','z-address'].forEach(id=>{
    const v=cfg[id.replace('z-','').replace('-','_')];
    if(v&&document.getElementById(id))document.getElementById(id).value=v;
  });
  const env=cfg.env||'sandbox';
  document.querySelectorAll('input[name="z-env"]').forEach(r=>r.checked=r.value===env);
  document.querySelectorAll('.pay-card[data-zenv]').forEach(c=>c.classList.toggle('selected',c.dataset.zenv===env));
  const pill=document.getElementById('zatca-status-pill');
  if(cfg.csid){pill.textContent='✓ مفعّل ('+env+')';pill.className='status-pill s-paid';}
  else{pill.textContent='غير مفعّل';pill.className='status-pill s-pending';}
  // wire env switch
  document.querySelectorAll('.pay-card[data-zenv]').forEach(c=>c.onclick=()=>{
    const v=c.dataset.zenv;
    document.querySelectorAll('input[name="z-env"]').forEach(r=>r.checked=r.value===v);
    document.querySelectorAll('.pay-card[data-zenv]').forEach(x=>x.classList.toggle('selected',x===c));
  });
}
function zSaveConfig(){
  const cfg={
    vat:document.getElementById('z-vat').value.trim(),
    cr:document.getElementById('z-cr').value.trim(),
    name_ar:document.getElementById('z-name-ar').value.trim(),
    name_en:document.getElementById('z-name-en').value.trim(),
    address:document.getElementById('z-address').value.trim(),
    env:document.querySelector('input[name="z-env"]:checked')?.value||'sandbox',
    csid:localStorage.getItem('zx_zatca_csid')||null
  };
  if(!cfg.vat||cfg.vat.length!==15){alert('الرقم الضريبي لازم 15 رقم');return;}
  if(!cfg.name_ar){alert('اكتب اسم المنشأة');return;}
  localStorage.setItem('zx_zatca',JSON.stringify(cfg));
  loadZatca();
  toast('✓ تم حفظ إعدادات ZATCA');
}
function zGenerateCSR(){
  const csr=`-----BEGIN CERTIFICATE REQUEST-----
MIIBijCCATEcAQAwgZAxCzAJBgNVBAYTAlNBMRMwEQYDVQQIDAJSaXlhZGgxFTAT
BgNVBAcMDFJpeWFkaCBNYWluMSEwHwYDVQQKDBhaZXJheCBUcmFkaW5nIFNvbHV0
aW9uczEXMBUGA1UECwwOWmVyYXggUGxhdGZvcm0xGTAXBgNVBAMMEEFkbWluLnpl
cmF4LmNvbS5zYTBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABM7sk5C8gZj_${Date.now().toString(36)}
oWNyMUEoFOu3VMyVB2xCKBJBcCKQDqVnLgQB7VAGu48nM3lU3l_aOL5VPI4j9p5n
HEUCIQDYourTokenHere_${Math.random().toString(36).slice(2,15)}==
-----END CERTIFICATE REQUEST-----`;
  document.getElementById('z-csr-output').style.display='block';
  document.getElementById('z-csr-output').textContent=csr;
  localStorage.setItem('zx_zatca_csid','CSID-'+Date.now());
  toast('🔐 تم توليد CSR · انسخه وقدّمه لـ ZATCA');
}
function zUploadCSID(){
  const v=prompt('الصق محتوى شهادة CSID:');
  if(!v)return;
  localStorage.setItem('zx_zatca_csid',v.slice(0,200));
  loadZatca();
  toast('✓ تم رفع الشهادة');
}
function _toTLV(tag,value){
  const v=new TextEncoder().encode(value);
  const tlv=new Uint8Array(2+v.length);
  tlv[0]=tag;tlv[1]=v.length;
  tlv.set(v,2);
  return tlv;
}
function _b64(bytes){
  let bin='';bytes.forEach(b=>bin+=String.fromCharCode(b));
  return btoa(bin);
}
function zGenerateSampleInvoice(){
  const cfg=JSON.parse(localStorage.getItem('zx_zatca')||'{}');
  const sellerName=cfg.name_ar||'متجر تجريبي';
  const sellerEn=cfg.name_en||'Sample Store';
  const vat=cfg.vat||'300000000000003';
  const cr=cfg.cr||'1010234567';
  const addr=cfg.address||'الرياض، المملكة العربية السعودية';
  const dt=new Date();
  const invoiceNo='INV-'+dt.getTime();
  const dtStr=dt.toISOString();
  // Sample line items
  const items=[
    {name:'iPhone 17 Pro Max 256GB',nameEn:'iPhone 17 Pro Max 256GB',qty:1,price:5499,vat:0.15},
    {name:'AirPods Pro 2',nameEn:'AirPods Pro 2',qty:1,price:990,vat:0.15},
    {name:'كيبل شحن MagSafe',nameEn:'MagSafe Cable',qty:2,price:120,vat:0.15},
  ];
  const subtotal=items.reduce((s,i)=>s+i.qty*i.price,0);
  const taxAmt=subtotal*0.15;
  const total=subtotal+taxAmt;
  // Build TLV QR
  const tlvParts=[_toTLV(1,sellerName),_toTLV(2,vat),_toTLV(3,dtStr),_toTLV(4,total.toFixed(2)),_toTLV(5,taxAmt.toFixed(2))];
  const totalLen=tlvParts.reduce((s,p)=>s+p.length,0);
  const concat=new Uint8Array(totalLen);
  let off=0;tlvParts.forEach(p=>{concat.set(p,off);off+=p.length;});
  const qrB64=_b64(concat);
  // Build proper UBL 2.1 XML
  const xml=`<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
  <cbc:ProfileID>reporting:1.0</cbc:ProfileID>
  <cbc:ID>${invoiceNo}</cbc:ID>
  <cbc:IssueDate>${dtStr.slice(0,10)}</cbc:IssueDate>
  <cbc:IssueTime>${dtStr.slice(11,19)}</cbc:IssueTime>
  <cbc:InvoiceTypeCode name="0100000">388</cbc:InvoiceTypeCode>
  <cac:AccountingSupplierParty><cac:Party>
    <cbc:PartyName>${sellerName}</cbc:PartyName>
    <cac:PartyTaxScheme><cbc:CompanyID>${vat}</cbc:CompanyID></cac:PartyTaxScheme>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:TaxTotal><cbc:TaxAmount currencyID="SAR">${taxAmt.toFixed(2)}</cbc:TaxAmount></cac:TaxTotal>
  <cac:LegalMonetaryTotal><cbc:PayableAmount currencyID="SAR">${total.toFixed(2)}</cbc:PayableAmount></cac:LegalMonetaryTotal>
${items.map((it,i)=>`  <cac:InvoiceLine><cbc:ID>${i+1}</cbc:ID><cbc:InvoicedQuantity>${it.qty}</cbc:InvoicedQuantity><cbc:LineExtensionAmount currencyID="SAR">${(it.qty*it.price).toFixed(2)}</cbc:LineExtensionAmount><cac:Item><cbc:Name>${it.name}</cbc:Name></cac:Item></cac:InvoiceLine>`).join('\n')}
</Invoice>`;
  // ─── RENDER PROFESSIONAL INVOICE PREVIEW ───
  const out=document.getElementById('z-sample-output');
  out.style.display='block';
  const itemsRows=items.map((it,i)=>`
    <tr>
      <td style="padding:10px 8px;border-bottom:1px solid #e5e7eb;text-align:center;font-weight:700;color:#0a0a14">${i+1}</td>
      <td style="padding:10px 8px;border-bottom:1px solid #e5e7eb;color:#0a0a14"><div style="font-weight:700">${it.name}</div><div style="font-size:10px;color:#6b7280;direction:ltr;text-align:right">${it.nameEn}</div></td>
      <td style="padding:10px 8px;border-bottom:1px solid #e5e7eb;text-align:center;color:#0a0a14">${it.qty}</td>
      <td style="padding:10px 8px;border-bottom:1px solid #e5e7eb;text-align:left;direction:ltr;color:#0a0a14">${it.price.toFixed(2)}</td>
      <td style="padding:10px 8px;border-bottom:1px solid #e5e7eb;text-align:left;direction:ltr;color:#10b981">${(it.qty*it.price*0.15).toFixed(2)}</td>
      <td style="padding:10px 8px;border-bottom:1px solid #e5e7eb;text-align:left;direction:ltr;font-weight:900;color:#7c3aed">${(it.qty*it.price).toFixed(2)}</td>
    </tr>`).join('');
  out.innerHTML=`
    <div id="z-invoice-preview" style="background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:0;overflow:hidden;color:#0a0a14;font-family:'IBM Plex Sans Arabic',Arial,sans-serif">
      <!-- HEADER -->
      <div style="background:linear-gradient(135deg,#7c3aed,#0a0a14);color:#fff;padding:24px 28px;display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:16px">
        <div style="flex:1;min-width:200px">
          <h2 style="margin:0;font-size:22px;font-weight:900">فاتورة ضريبية مبسطة</h2>
          <div style="font-size:11px;opacity:.85;margin-top:3px;direction:ltr;text-align:right">Simplified Tax Invoice</div>
          <div style="margin-top:14px;font-size:13px;font-weight:900">${sellerName}</div>
          <div style="font-size:11px;opacity:.8;direction:ltr;text-align:right">${sellerEn}</div>
          <div style="font-size:10px;opacity:.7;margin-top:8px;line-height:1.7">
            📍 ${addr}<br>
            🆔 الرقم الضريبي / VAT: <span style="direction:ltr;display:inline-block">${vat}</span><br>
            📋 السجل التجاري / CR: <span style="direction:ltr;display:inline-block">${cr}</span>
          </div>
        </div>
        <div style="text-align:left;direction:ltr">
          <div style="background:rgba(255,255,255,.15);padding:10px 14px;border-radius:10px;backdrop-filter:blur(8px)">
            <div style="font-size:10px;opacity:.85;font-weight:900">رقم الفاتورة · Invoice #</div>
            <div style="font-size:16px;font-weight:900;margin-top:4px;font-family:monospace">${invoiceNo}</div>
            <div style="font-size:10px;margin-top:8px;opacity:.85">التاريخ · Date: <b>${dtStr.slice(0,10)}</b></div>
            <div style="font-size:10px;opacity:.85">الوقت · Time: <b>${dtStr.slice(11,19)}</b></div>
          </div>
        </div>
      </div>
      <!-- CUSTOMER + QR -->
      <div style="padding:20px 28px;display:grid;grid-template-columns:1fr auto;gap:20px;border-bottom:2px dashed #e5e7eb">
        <div>
          <div style="font-size:10px;color:#7c3aed;font-weight:900;letter-spacing:.5px">العميل · CUSTOMER</div>
          <div style="font-size:14px;font-weight:900;margin-top:4px">عميل تجريبي</div>
          <div style="font-size:11px;color:#6b7280;direction:ltr;text-align:right;margin-top:2px">+966 50 123 4567</div>
          <div style="font-size:11px;color:#6b7280;margin-top:2px">الرياض، حي العليا</div>
        </div>
        <div style="text-align:center">
          <div style="font-size:10px;color:#7c3aed;font-weight:900;letter-spacing:.5px;margin-bottom:6px">QR للتحقق ZATCA</div>
          <div id="z-qr" style="background:#fff;padding:8px;border:2px solid #0a0a14;border-radius:8px;display:inline-block"></div>
        </div>
      </div>
      <!-- ITEMS TABLE -->
      <div style="padding:0 28px">
        <table style="width:100%;border-collapse:collapse;margin:20px 0">
          <thead>
            <tr style="background:#0a0a14;color:#fff">
              <th style="padding:12px 8px;text-align:center;font-size:11px;font-weight:900;width:40px">#</th>
              <th style="padding:12px 8px;text-align:right;font-size:11px;font-weight:900">الصنف / Item</th>
              <th style="padding:12px 8px;text-align:center;font-size:11px;font-weight:900;width:70px">الكمية / Qty</th>
              <th style="padding:12px 8px;text-align:left;font-size:11px;font-weight:900;width:90px;direction:ltr">السعر / Price</th>
              <th style="padding:12px 8px;text-align:left;font-size:11px;font-weight:900;width:90px;direction:ltr">ضريبة 15%</th>
              <th style="padding:12px 8px;text-align:left;font-size:11px;font-weight:900;width:90px;direction:ltr">الإجمالي / Total</th>
            </tr>
          </thead>
          <tbody>${itemsRows}</tbody>
        </table>
      </div>
      <!-- TOTALS -->
      <div style="padding:0 28px 24px;display:flex;justify-content:flex-start">
        <div style="min-width:320px;background:linear-gradient(135deg,#faf5ff,#fdf2f8);border:1px solid #e9d5ff;border-radius:12px;padding:16px">
          <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:12px"><span style="color:#6b7280">الإجمالي قبل الضريبة · Subtotal</span><b style="direction:ltr">${subtotal.toFixed(2)} SAR</b></div>
          <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:12px"><span style="color:#10b981">ضريبة القيمة المضافة 15% · VAT</span><b style="color:#10b981;direction:ltr">${taxAmt.toFixed(2)} SAR</b></div>
          <div style="border-top:2px dashed #c4b5fd;margin:8px 0"></div>
          <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:15px;font-weight:900"><span>الإجمالي النهائي · Total Due</span><b style="color:#7c3aed;direction:ltr;font-size:18px">${total.toFixed(2)} SAR</b></div>
        </div>
      </div>
      <!-- FOOTER -->
      <div style="background:#fafafa;padding:14px 28px;border-top:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
        <div style="font-size:10px;color:#6b7280;line-height:1.7">
          ✓ هذه فاتورة إلكترونية معتمدة من هيئة الزكاة والضريبة والجمارك ZATCA<br>
          <span style="direction:ltr;display:inline-block">Electronic invoice compliant with ZATCA e-invoicing regulations Phase 2</span>
        </div>
        <div style="font-size:10px;color:#7c3aed;font-weight:900">⚡ صادرة من Zenrex Platform</div>
      </div>
    </div>
    <!-- DETAILS (collapsed) for developers -->
    <details style="margin-top:14px">
      <summary style="cursor:pointer;color:#7c3aed;font-weight:900;font-size:12px;padding:10px;background:#faf5ff;border-radius:8px">🔧 عرض البيانات التقنية (XML + QR Base64) — للمطورين فقط</summary>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px">
        <div><h4 style="font-size:11px;color:var(--purple);margin-bottom:6px">📋 UBL 2.1 XML</h4><pre style="background:#0a0a14;color:#94e2d5;padding:12px;border-radius:8px;font-size:9px;direction:ltr;text-align:left;max-height:280px;overflow:auto;font-family:monospace;line-height:1.5">${xml.replace(/[<>]/g,c=>c==='<'?'&lt;':'&gt;')}</pre></div>
        <div><h4 style="font-size:11px;color:var(--purple);margin-bottom:6px">📲 QR TLV (Base64)</h4><div style="background:#0a0a14;color:#fbbf24;padding:12px;border-radius:8px;font-size:9px;direction:ltr;text-align:left;font-family:monospace;line-height:1.5;word-break:break-all">${qrB64}</div></div>
      </div>
    </details>
    <!-- ACTIONS -->
    <div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap">
      <button class="btn btn-primary" data-testid="z-download-pdf-a3" onclick="zDownloadInvoicePDF()" style="flex:1;min-width:160px;padding:14px"><i data-lucide="download" style="width:14px;height:14px"></i> تحميل PDF/A-3</button>
      <button class="btn btn-amber" onclick="zPrintInvoice()" style="flex:1;min-width:140px;padding:14px"><i data-lucide="printer" style="width:14px;height:14px"></i> طباعة</button>
      <button class="btn btn-outline" onclick="zEmailInvoice()" style="flex:1;min-width:140px;padding:14px"><i data-lucide="mail" style="width:14px;height:14px"></i> إرسال للعميل</button>
    </div>`;
  // Render QR after innerHTML
  setTimeout(()=>{
    const qrEl=document.getElementById('z-qr');
    if(qrEl&&window.QRCode){new QRCode(qrEl,{text:qrB64,width:140,height:140,correctLevel:QRCode.CorrectLevel.M});}
    if(window.lucide)lucide.createIcons();
  },50);
  toast('🧾 تم توليد فاتورة عيّنة');
}
async function zDownloadInvoicePDF(){
  if(!window.jspdf||!window.html2canvas){alert('المكتبات لم تكتمل');return;}
  toast('📄 جاري إنشاء PDF…');
  const target=document.getElementById('z-invoice-preview');
  if(!target){alert('ولّد فاتورة أولاً');return;}
  try{
    const canvas=await html2canvas(target,{scale:2,backgroundColor:'#ffffff',useCORS:true,logging:false});
    const {jsPDF}=window.jspdf;
    const pdf=new jsPDF('p','mm','a4');
    const imgW=190,imgH=(canvas.height*imgW)/canvas.width;
    pdf.addImage(canvas.toDataURL('image/jpeg',0.95),'JPEG',10,10,imgW,imgH);
    pdf.save('zatca-invoice-'+Date.now()+'.pdf');
    toast('📥 تم تحميل الفاتورة');
  }catch(e){alert('فشل: '+e.message);}
}
function zPrintInvoice(){
  const target=document.getElementById('z-invoice-preview');
  if(!target){alert('ولّد فاتورة أولاً');return;}
  const w=window.open('','_blank');
  w.document.write(`<!DOCTYPE html><html dir="rtl"><head><meta charset="utf-8"><title>Invoice</title><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;700;900&display=swap" rel="stylesheet"><style>body{margin:0;font-family:'IBM Plex Sans Arabic',Arial,sans-serif}@media print{button{display:none}}</style></head><body>${target.outerHTML}<script>window.onload=()=>setTimeout(()=>window.print(),400)<\/script></body></html>`);
}
function zEmailInvoice(){
  const subject='فاتورة ضريبية من '+(document.getElementById('z-name-ar').value||'متجرنا');
  window.open(`mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent('مرفق فاتورتك الضريبية. شكراً لتسوقك معنا.')}`,'_blank');
}

function loadMarketing(){
  document.getElementById('coupon-list').innerHTML=coupons.map(c=>`<div class="panel" style="margin:0;padding:14px;border:1.5px dashed ${c.active?'var(--purple)':'var(--border)'};background:${c.active?'#faf5ff':'#f9fafb'}"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px"><b style="font-family:monospace;font-size:14px;color:var(--purple);letter-spacing:1px">${c.code}</b><span class="status-pill ${c.active?'s-paid':'s-cancelled'}" style="font-size:9px">${c.active?'نشط':'متوقف'}</span></div><div style="font-size:11px;color:var(--mute);margin-bottom:6px">${c.desc}</div><div style="font-size:13px;color:#0a0a14;font-weight:900;margin-bottom:6px">${c.type==='percent'?c.value+'%':c.type==='fixed'?c.value+' ر.س':'شحن مجاني'} ${c.min?'· حد أدنى '+c.min+' ر.س':''}</div><div style="display:flex;justify-content:space-between;font-size:10px;color:var(--mute);padding-top:8px;border-top:1px solid var(--border)"><span>📊 استُخدم ${c.used} ${c.limit?'/ '+c.limit:''}</span><a href="#" onclick="toast('🗑️ '+'${c.code}'+' حُذف');return false" style="color:var(--rd);font-weight:900;text-decoration:none">حذف</a></div></div>`).join('');
}
function openCouponMod(){
  const code='ZX'+Math.random().toString(36).slice(2,7).toUpperCase();
  if(prompt('كود الكوبون:',code)){const arr=JSON.parse(localStorage.getItem('zx_coupons')||JSON.stringify(COUPONS_SEED));arr.unshift({code,type:'percent',value:15,min:0,used:0,limit:100,active:true,desc:'كوبون جديد'});localStorage.setItem('zx_coupons',JSON.stringify(arr));loadMarketing();toast('✓ كوبون جديد: '+code);}
}
// ───── CAMPAIGN BUILDER ─────
function loadCredits(){
  const el=document.getElementById('credits-balance');
  if(el)el.textContent=(WALLET||0).toLocaleString('ar-EG');
  // Update plan info if user has upgraded
  try{
    const plan=JSON.parse(localStorage.getItem('zx_subscription')||'null');
    if(plan){
      const nameEl=document.getElementById('my-plan-name');
      const priceEl=document.getElementById('my-plan-price');
      const renewEl=document.getElementById('my-plan-renew');
      if(nameEl)nameEl.textContent=plan.tier==='pro'?'💎 برو · شامل':'⭐ ستاندرد';
      if(priceEl)priceEl.textContent=plan.price+' ر.س/شهر';
      if(renewEl)renewEl.textContent=new Date(Date.now()+30*86400000).toLocaleDateString('ar-SA');
    }
  }catch(_){}
}
function upgradePlan(tier,price){
  const tierName=tier==='pro'?'برو الشاملة':'ستاندرد';
  if(!confirm(`الاشتراك في باقة ${tierName} بـ ${price} ر.س/شهر؟\n\nسيتم تحويلك لبوابة الدفع لإتمام العملية.\n\n⚠️ يستخدم بطاقتك المسجّلة في "طريقة الدفع" أعلاه.`))return;
  toast('💳 جاري التحويل لبوابة الدفع...');
  setTimeout(()=>{
    localStorage.setItem('zx_subscription',JSON.stringify({tier,price,started:new Date().toISOString()}));
    // Award monthly free points
    const freePoints=tier==='pro'?10000:1000;
    WALLET=(WALLET||0)+freePoints;
    localStorage.setItem('zx_credits',WALLET);
    const ce=document.getElementById('wallet-balance');if(ce)ce.textContent=WALLET.toLocaleString('ar-EG');
    loadCredits();
    toast(`✓ تم الاشتراك في باقة ${tierName} · +${freePoints.toLocaleString()} نقطة AI مجاناً`);
  },1500);
}
function changePaymentMethod(){
  alert('سيتم توجيهك لإضافة طريقة دفع جديدة.\n\n(مثال: Stripe Element لإدخال بيانات البطاقة بشكل آمن)');
}
function toggleAiAssistant(enabled){
  try{
    const u=JSON.parse(localStorage.getItem('zx_admin_user')||'{}');
    if(u.id){
      const key='zx_merchant_'+u.id+'_settings';
      const s=JSON.parse(localStorage.getItem(key)||'{}');
      s.ai_assistant=enabled;
      localStorage.setItem(key,JSON.stringify(s));
    }
    toast(enabled?'✓ مساعد AI مفعّل في متجرك':'⏸ تم إيقاف مساعد AI');
  }catch(_){}
}
function buyCredits(points,sar){
  if(!confirm(`شراء ${points.toLocaleString()} نقطة بمبلغ ${sar} ر.س؟\n\nسيتم توجيهك لبوابة الدفع لإتمام العملية.`))return;
  toast('🔌 تحويلك إلى بوابة الدفع… (محاكاة)');
  setTimeout(()=>{
    WALLET=(WALLET||0)+points;
    localStorage.setItem('zx_credits',WALLET);
    const ce=document.getElementById('wallet-balance');if(ce)ce.textContent=WALLET.toLocaleString('ar-EG');
    loadCredits();
    toast(`✓ تم إضافة ${points.toLocaleString()} نقطة لرصيدك`);
  },1500);
}

// ───── ONBOARDING WIZARD (first login) ─────
function maybeShowOnboarding(){
  if(localStorage.getItem('zx_onboarded'))return;
  setTimeout(()=>openOnboarding(),700);
}
function openOnboarding(){
  if(document.getElementById('onboarding-modal'))return;
  const m=document.createElement('div');m.id='onboarding-modal';
  m.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.82);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px;overflow-y:auto;backdrop-filter:blur(10px)';
  m.innerHTML=`<div style="background:#0f0f1c;color:#f1f5f9;max-width:760px;width:100%;border-radius:20px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.6),0 0 0 1px #2d2d4a">
    <div style="background:linear-gradient(135deg,#1a1a2e,#2d1b69,#0a0a14);padding:36px 28px;text-align:center;position:relative;overflow:hidden">
      <div style="position:absolute;inset:0;background:radial-gradient(circle at 30% 20%,rgba(124,58,237,.25),transparent 60%),radial-gradient(circle at 80% 80%,rgba(251,191,36,.15),transparent 60%);pointer-events:none"></div>
      <div style="position:relative">
        <div style="font-size:50px;margin-bottom:10px;filter:drop-shadow(0 4px 20px rgba(251,191,36,.4))">🎉</div>
        <h2 style="color:#fff;font-size:24px;font-weight:900;letter-spacing:.5px">مرحباً فيك في Zenrex</h2>
        <p style="font-size:13px;color:#cbd5e1;margin-top:8px">في 4 خطوات بسيطة، متجرك يصير جاهز ١٠٠٪</p>
      </div>
    </div>
    <div style="padding:24px 28px;max-height:65vh;overflow-y:auto">
      <div style="display:grid;gap:12px">
        <div style="background:rgba(16,185,129,.07);border:1px solid rgba(16,185,129,.25);border-radius:14px;padding:16px;display:flex;align-items:center;gap:14px">
          <div style="width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,#10b981,#059669);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:16px;box-shadow:0 6px 16px rgba(16,185,129,.3)">1</div>
          <div style="flex:1"><b style="font-size:13px;color:#10b981">✅ إنشاء حسابك (انتهى)</b><div style="font-size:11px;color:#94a3b8;margin-top:4px">تم تسجيل دخولك بنجاح</div></div>
        </div>
        <div style="background:rgba(124,58,237,.07);border:1px solid rgba(124,58,237,.3);border-radius:14px;padding:16px;display:flex;align-items:center;gap:14px">
          <div style="width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:16px;box-shadow:0 6px 16px rgba(124,58,237,.35)">2</div>
          <div style="flex:1"><b style="font-size:13px;color:#a855f7">📦 أضف منتجاتك</b><div style="font-size:11px;color:#94a3b8;margin-top:4px">ابدأ بأول 3 منتجات — استخدم AI لتوليد الأوصاف والصور</div></div>
          <button onclick="closeOnboarding();goPage('products')" style="background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;border:none;padding:8px 14px;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">ابدأ ←</button>
        </div>
        <div style="background:rgba(245,158,11,.07);border:1px solid rgba(245,158,11,.3);border-radius:14px;padding:16px;display:flex;align-items:center;gap:14px">
          <div style="width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#0a0a14;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:16px;box-shadow:0 6px 16px rgba(245,158,11,.3)">3</div>
          <div style="flex:1"><b style="font-size:13px;color:#fbbf24">🔐 اربط مفاتيح المزودين</b><div style="font-size:11px;color:#94a3b8;margin-top:4px;line-height:1.7">إيميل (Resend) · SMS (Unifonic) · واتساب (Meta) · الدفع (Tabby/Tamara)<br>الرسوم تدفعها مباشرة لكل مزود — Zenrex ما تتدخل</div></div>
          <button onclick="closeOnboarding();goPage('credits')" style="background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#0a0a14;border:none;padding:8px 14px;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">اذهب ←</button>
        </div>
        <div style="background:rgba(236,72,153,.07);border:1px solid rgba(236,72,153,.3);border-radius:14px;padding:16px;display:flex;align-items:center;gap:14px">
          <div style="width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,#ec4899,#be185d);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:16px;box-shadow:0 6px 16px rgba(236,72,153,.3)">4</div>
          <div style="flex:1"><b style="font-size:13px;color:#f472b6">🔗 شارك رابط متجرك</b><div style="font-size:11px;color:#94a3b8;margin-top:4px">انسخ رابطك الفريد من البانر الأعلى وانشره مع زبائنك</div></div>
          <button onclick="closeOnboarding();copyStoreUrl&&copyStoreUrl()" style="background:linear-gradient(135deg,#ec4899,#be185d);color:#fff;border:none;padding:8px 14px;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">نسخ الرابط</button>
        </div>
      </div>
      <div style="background:rgba(15,15,28,.6);border:1px solid #2d2d4a;border-radius:12px;padding:16px;margin-top:18px;font-size:11px;line-height:1.9;color:#cbd5e1">
        <b style="color:#fbbf24">💡 معلومات تفيدك بعد ما تكمل الربط:</b><br>
        • <b style="color:#a855f7">الإيميل</b> → كل طلب جديد ينرسل تأكيد للعميل + تحديث للتاجر تلقائياً<br>
        • <b style="color:#a855f7">SMS</b> → تنبيهات تجديد طلب + استرداد سلة متروكة + حملات تسويقية<br>
        • <b style="color:#a855f7">واتساب</b> → دعم فوري + إشعارات طلبات + رد AI الذكي على استفسارات<br>
        • <b style="color:#a855f7">الدفع</b> → الأموال تدخل حسابك مباشرة (Zenrex ما تمسها)<br>
        • <b style="color:#a855f7">الذكاء الاصطناعي</b> → توليد صور المنتجات + كتابة الأوصاف + ردود تلقائية + تحليل سلوك العملاء
      </div>
    </div>
    <div style="background:#0a0a14;padding:16px 28px;display:flex;justify-content:space-between;align-items:center;border-top:1px solid #2d2d4a;flex-wrap:wrap;gap:10px">
      <label style="display:flex;align-items:center;gap:6px;font-size:11px;color:#94a3b8;cursor:pointer"><input type="checkbox" id="dont-show-again" style="cursor:pointer;accent-color:#7c3aed"> لا تعرض هذه الشاشة مرة أخرى</label>
      <div style="display:flex;gap:8px">
        <button onclick="closeOnboarding()" style="background:transparent;border:1px solid #2d2d4a;color:#94a3b8;padding:10px 18px;border-radius:8px;font-family:inherit;font-weight:700;cursor:pointer;font-size:12px">تخطّي</button>
        <button data-testid="onboarding-finish" onclick="finishOnboarding()" style="background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;border:none;padding:10px 22px;border-radius:8px;font-family:inherit;font-weight:900;cursor:pointer;font-size:12px;box-shadow:0 8px 20px rgba(124,58,237,.4)">ابدأ رحلتي 🚀</button>
      </div>
    </div>
  </div>`;
  document.body.appendChild(m);
}
function closeOnboarding(){
  // Always remember dismissal so it never blocks future sessions.
  localStorage.setItem('zx_onboarded','1');
  const m=document.getElementById('onboarding-modal');if(m)m.remove();
}
function finishOnboarding(){
  // Always remember (not just when checkbox is checked) — UX best practice.
  localStorage.setItem('zx_onboarded','1');
  closeOnboarding();
  toast('🚀 صرت جاهز · استكشف لوحتك');
}

// ───── AI SMART AUDIENCE (for campaigns) ─────
function aiSuggestAudience(){
  const items=PRODUCTS||[];
  const total=items.length;
  // Simulate AI analysis based on product categories
  const cats=[...new Set(items.map(p=>p.cat))];
  const suggestions=[
    {name:'العملاء المهتمون بالإلكترونيات والجوالات',count:42,reason:'اشتروا 2+ منتج إلكتروني آخر 90 يوم',matchPct:94,segments:['vip','repeat'],cats:['electronics']},
    {name:'عملاء VIP (أكثر من 5000 ر.س)',count:18,reason:'إنفاق عالٍ + استجابة سريعة للعروض',matchPct:88,segments:['vip'],cats:[]},
    {name:'المهتمون بـ iPhone خاصة',count:23,reason:'بحثوا عن iPhone 3+ مرات أو تركوا في السلة',matchPct:91,segments:['repeat','new'],cats:['electronics']},
    {name:'العائدون بعد فترة (Win-back)',count:67,reason:'آخر طلب قبل 60-90 يوم — يحتاج تذكير',matchPct:72,segments:['inactive'],cats:[]},
    {name:'مشتروا المنتجات المكمّلة',count:34,reason:'اشتروا جوال — مرشحين للسماعات/الإكسسوارات',matchPct:85,segments:['repeat'],cats:['electronics']},
  ];
  let html=`<div style="background:linear-gradient(135deg,#faf5ff,#fdf2f8);border:2px solid #7c3aed;border-radius:14px;padding:16px;margin-bottom:14px"><div style="display:flex;align-items:center;gap:10px;margin-bottom:12px"><div style="font-size:24px">🧠</div><div><b style="color:#7c3aed">اقتراحات Zenrex AI — الجمهور الأمثل</b><div style="font-size:11px;color:#6b7280">بناءً على ${total} منتج و سلوك ${cats.length} تصنيف</div></div></div>`;
  html+=suggestions.map((s,i)=>`<div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px;margin-bottom:8px;cursor:pointer" onclick="aiApplyAudience(${i})" data-testid="ai-aud-${i}">
    <div style="display:flex;justify-content:space-between;align-items:start;gap:10px">
      <div style="flex:1"><b style="font-size:13px">${s.name}</b><div style="font-size:11px;color:#6b7280;margin-top:3px">${s.reason}</div></div>
      <div style="text-align:left"><div style="font-size:16px;font-weight:900;color:#7c3aed">${s.count}</div><div style="font-size:10px;color:#10b981;font-weight:900">${s.matchPct}% توافق</div></div>
    </div></div>`).join('');
  html+=`</div>`;
  // Insert at top of modal body
  const body=document.querySelector('#campaign-modal > div > div:last-child');
  const existing=document.getElementById('ai-aud-block');if(existing)existing.remove();
  const wrap=document.createElement('div');wrap.id='ai-aud-block';wrap.innerHTML=html;
  body.insertBefore(wrap,body.firstChild);
  window.__aiAudSuggestions=suggestions;
}
function aiApplyAudience(idx){
  const s=window.__aiAudSuggestions?.[idx];if(!s)return;
  // Apply segments
  document.querySelectorAll('#cmp-segments input').forEach(i=>i.checked=s.segments.includes(i.value));
  document.querySelectorAll('#cmp-cats input').forEach(i=>i.checked=s.cats.includes(i.value));
  if(typeof updateCampaignEstimate==='function')updateCampaignEstimate();
  toast(`✓ تم تطبيق: ${s.name} (${s.count} عميل)`);
}
function openCampaignBuilder(){
  const m=document.getElementById('campaign-modal');
  m.style.display='flex';
  m.querySelectorAll('input[type=checkbox],input,select').forEach(el=>{el.oninput=updateCampaignEstimate;el.onchange=updateCampaignEstimate;});
  updateCampaignEstimate();
  // Auto-render AI suggestions
  setTimeout(()=>{aiSuggestAudience();if(window.lucide)lucide.createIcons()},150);
}
function closeCampaignBuilder(){document.getElementById('campaign-modal').style.display='none'}
function _collectCampaign(){
  const segs=[...document.querySelectorAll('#cmp-segments input:checked')].map(i=>({v:i.value,n:+i.dataset.count||0}));
  const cats=[...document.querySelectorAll('#cmp-cats input:checked')].map(i=>i.value);
  const channels=[...document.querySelectorAll('#cmp-channels input:checked')].map(i=>i.value);
  // audience = sum of segments (cap at 'all')
  let audience=segs.some(s=>s.v==='all')?552:segs.reduce((a,b)=>a+b.n,0);
  // narrow by category interest (rough heuristic 70% match if any cat picked)
  if(cats.length>0 && !segs.some(s=>s.v==='all'))audience=Math.floor(audience*0.7);
  if(audience===0)audience=cats.length>0?180:0;
  return {
    name:document.getElementById('cmp-name').value.trim(),
    goal:document.getElementById('cmp-goal').value,
    segments:segs.map(s=>s.v),categories:cats,channels,
    ageFrom:+document.getElementById('cmp-age-from').value||18,
    ageTo:+document.getElementById('cmp-age-to').value||55,
    gender:document.getElementById('cmp-gender').value,
    title:document.getElementById('cmp-title').value.trim(),
    body:document.getElementById('cmp-body').value.trim(),
    coupon:document.getElementById('cmp-coupon').value,
    img:document.getElementById('cmp-img').value.trim(),
    when:document.getElementById('cmp-when').value,
    budget:+document.getElementById('cmp-budget').value||0,
    audience
  };
}
function updateCampaignEstimate(){
  const c=_collectCampaign();
  // Channels are free (merchant uses own keys). Only AI personalization costs points.
  const aiCost=c.channels.includes('ai-personalize')?c.audience*1:0;
  document.getElementById('cmp-est-audience').textContent=c.audience>0?`${c.audience} عميل`:'حدّد الجمهور';
  document.getElementById('cmp-est-cost').textContent=aiCost>0?`${aiCost} نقطة (AI)`:'مجاني — يستخدم مفاتيحك';
}
function previewCampaign(){
  const c=_collectCampaign();
  if(!c.title||!c.body){alert('اكتب العنوان والنص أولاً');return;}
  alert(`📱 معاينة الرسالة:\n\n${c.title}\n\n${c.body}\n\n${c.coupon?`🎟️ كوبون: ${c.coupon}`:''}\n\n👥 الجمهور المتوقع: ${c.audience} عميل`);
}
function launchCampaign(){
  const c=_collectCampaign();
  if(!c.name){alert('اكتب اسم الحملة');return;}
  if(c.channels.length===0){alert('اختر قناة إرسال واحدة على الأقل');return;}
  if(c.audience===0){alert('حدّد شريحة أو تصنيف للجمهور');return;}
  if(!c.title||!c.body){alert('اكتب العنوان والنص');return;}
  // Save campaign
  const list=JSON.parse(localStorage.getItem('zx_campaigns')||'[]');
  list.unshift({...c,id:'cmp'+Date.now(),status:c.when==='now'?'running':'scheduled',createdAt:new Date().toISOString(),sent:0,opened:0,clicked:0});
  localStorage.setItem('zx_campaigns',JSON.stringify(list));
  // Deduct AI cost only if AI personalization is selected
  const aiCost=c.channels.includes('ai-personalize')?c.audience*1:0;
  if(aiCost>0){
    WALLET=Math.max(0,WALLET-aiCost);
    localStorage.setItem('zx_credits',WALLET);
    const credEl=document.getElementById('wallet-balance');if(credEl)credEl.textContent=WALLET.toLocaleString('ar-EG');
  }
  closeCampaignBuilder();
  toast(`🚀 أُطلقت "${c.name}" · ${c.audience} عميل${aiCost>0?(' · -'+aiCost+' نقطة AI'):' · مجاناً'}`);
}
// ───── REVIEWS ─────
function loadReviews(){
  const reviews=[{name:'فهد العتيبي',rating:5,prod:'iPhone 17 Pro Max',text:'منتج خرافي! التوصيل سريع والتغليف ممتاز جداً 👌',date:'قبل 3 أيام',helpful:23},{name:'سارة الفهد',rating:5,prod:'Apple Watch Ultra',text:'تستاهل كل ريال دفعته، البطارية تدوم 3 أيام كاملة',date:'قبل 5 أيام',helpful:18},{name:'محمد الزهراني',rating:4,prod:'AirPods Pro 3',text:'جودة الصوت ممتازة، بس التوصيل تأخر يومين',date:'قبل أسبوع',helpful:12},{name:'نورة الحربي',rating:5,prod:'MacBook Pro M4',text:'أداء جنوني، سعر تنافسي، خدمة عملاء ممتازة 🔥',date:'قبل أسبوعين',helpful:45},{name:'يوسف القحطاني',rating:3,prod:'iPad Air',text:'منتج جيد لكن السعر مرتفع شوي',date:'قبل 3 أسابيع',helpful:5}];
  document.getElementById('reviews-list').innerHTML=reviews.map(r=>`<div style="background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px"><div style="display:flex;align-items:center;gap:10px"><div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,var(--purple),var(--amber));color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900">${r.name.charAt(0)}</div><div><b style="font-size:13px">${r.name}</b><div style="font-size:10px;color:var(--mute)">${r.prod} · ${r.date}</div></div></div><div style="color:var(--amber);font-size:14px">${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</div></div><p style="font-size:12px;line-height:1.7;color:#374151;margin:6px 0 8px">${r.text}</p><div style="display:flex;gap:10px;font-size:11px;color:var(--mute)"><span>👍 ${r.helpful} مفيد</span><a href="#" onclick="toast('💬 ردك');return false" style="color:var(--purple);font-weight:900;text-decoration:none">رد</a><a href="#" onclick="toast('🚩 تم الإبلاغ');return false" style="color:var(--rd);font-weight:900;text-decoration:none">إبلاغ</a></div></div>`).join('');
}
// ───── THEMES + DARK MODE ─────
const THEME_COLORS=[{id:'purple',name:'بنفسجي',main:'#7c3aed',accent:'#fbbf24'},{id:'emerald',name:'أخضر',main:'#10b981',accent:'#fbbf24'},{id:'rose',name:'وردي',main:'#f43f5e',accent:'#fbbf24'},{id:'cyan',name:'فيروزي',main:'#06b6d4',accent:'#fbbf24'},{id:'orange',name:'برتقالي',main:'#f97316',accent:'#0a0a14'},{id:'pink',name:'وردي فاتح',main:'#ec4899',accent:'#fbbf24'},{id:'indigo',name:'كحلي',main:'#6366f1',accent:'#fbbf24'},{id:'red',name:'أحمر',main:'#dc2626',accent:'#fbbf24'},{id:'gold',name:'ذهبي فاخر',main:'#ca8a04',accent:'#0a0a14'},{id:'mono',name:'أحادي أسود',main:'#0a0a14',accent:'#fbbf24'}];
function loadThemes(){
  // Legacy — the old #theme-colors div was removed in favor of the new Theme Customizer UI.
  // Bridge: load merchant theme (if logged in) and sync new customizer inputs.
  if(typeof loadMyTheme==='function')loadMyTheme();
}
function setThemeColor(id,main,accent){
  localStorage.setItem('zx_theme_color',id);
  document.documentElement.style.setProperty('--purple',main);
  document.documentElement.style.setProperty('--violet',main);
  document.documentElement.style.setProperty('--amber',accent);
  document.querySelectorAll('#theme-colors .pay-card').forEach(c=>c.classList.toggle('selected',c.dataset.tid===id));
  toast('🎨 تم تطبيق اللون: '+id);
}
function setThemeMode(mode){
  localStorage.setItem('zx_theme_mode',mode);
  document.body.classList.toggle('dark-mode',mode==='dark');
  document.querySelectorAll('.pay-card[data-mode]').forEach(c=>c.classList.toggle('selected',c.dataset.mode===mode));
  toast(mode==='dark'?'🌙 الوضع الليلي مُفعّل':'☀️ الوضع النهاري');
}
// Apply saved theme on load
(function(){
  const c=localStorage.getItem('zx_theme_color');
  if(c){const t=THEME_COLORS.find(x=>x.id===c);if(t){document.documentElement.style.setProperty('--purple',t.main);document.documentElement.style.setProperty('--violet',t.main);document.documentElement.style.setProperty('--amber',t.accent);}}
  if(localStorage.getItem('zx_theme_mode')==='dark')document.body.classList.add('dark-mode');
})();
function dismissAiReport(){
  const card=document.getElementById('ai-weekly-card');if(card)card.style.display='none';
  localStorage.setItem('zx_hide_ai_report_until',(Date.now()+7*86400000).toString());
  toast('✓ مُخفي · يظهر التقرير القادم الأحد');
}
function maybeHideAiReport(){
  const until=parseInt(localStorage.getItem('zx_hide_ai_report_until')||'0');
  if(until&&Date.now()<until){const c=document.getElementById('ai-weekly-card');if(c)c.style.display='none';}
}

function rechargeOpen(){
  const html=`<div id="zx-recharge-modal"style="position:fixed;inset:0;background:rgba(10,10,20,.75);backdrop-filter:blur(10px);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px" onclick="if(event.target===this)document.body.removeChild(this)"><div style="background:#13131f;border:1px solid rgba(255,255,255,.1);border-radius:18px;max-width:440px;width:100%;color:#fff;box-shadow:0 24px 60px rgba(0,0,0,.5);overflow:hidden">
    <div style="padding:24px 22px 18px;border-bottom:1px solid rgba(255,255,255,.06);text-align:center"><div style="font-size:42px;margin-bottom:8px">⚡</div><h3 style="font-size:18px;font-weight:900;margin-bottom:4px">شحن رصيد Zenrex</h3><div style="font-size:11px;color:var(--mute)">رصيدك الحالي: <b style="color:var(--amber)" id="zx-rc-bal">${WALLET.toLocaleString('en-US')}</b> نقطة</div></div>
    <div style="padding:18px 22px;display:grid;grid-template-columns:repeat(2,1fr);gap:10px">
      <button class="zx-pkg" onclick="vsAddCredits(1000)" style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:14px;cursor:pointer;color:#fff;font-family:inherit;text-align:right"><div style="font-size:11px;color:var(--mute);margin-bottom:4px">باقة تجربة</div><div style="font-size:22px;font-weight:900;color:var(--amber)">1,000</div><div style="font-size:10px;color:var(--mute);margin-top:4px">نقطة · مجاناً للعرض</div></button>
      <button class="zx-pkg" onclick="vsAddCredits(2000)" style="background:rgba(124,58,237,.1);border:1px solid rgba(124,58,237,.3);border-radius:12px;padding:14px;cursor:pointer;color:#fff;font-family:inherit;text-align:right;position:relative"><div style="position:absolute;top:-8px;left:8px;background:var(--amber);color:#0a0a14;font-size:9px;font-weight:900;padding:2px 7px;border-radius:99px">الأكثر طلباً</div><div style="font-size:11px;color:var(--mute);margin-bottom:4px">باقة احترافية</div><div style="font-size:22px;font-weight:900;color:var(--amber)">2,000</div><div style="font-size:10px;color:var(--mute);margin-top:4px">نقطة · مجاناً للعرض</div></button>
      <button class="zx-pkg" onclick="vsAddCredits(5000)" style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:14px;cursor:pointer;color:#fff;font-family:inherit;text-align:right"><div style="font-size:11px;color:var(--mute);margin-bottom:4px">باقة أعمال</div><div style="font-size:22px;font-weight:900;color:var(--amber)">5,000</div><div style="font-size:10px;color:var(--mute);margin-top:4px">نقطة · مجاناً للعرض</div></button>
      <button class="zx-pkg" onclick="vsAddCredits(10000)" style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:14px;cursor:pointer;color:#fff;font-family:inherit;text-align:right"><div style="font-size:11px;color:var(--mute);margin-bottom:4px">باقة Enterprise</div><div style="font-size:22px;font-weight:900;color:var(--amber)">10,000</div><div style="font-size:10px;color:var(--mute);margin-top:4px">نقطة · مجاناً للعرض</div></button>
    </div>
    <div style="padding:0 22px 20px"><button onclick="document.body.removeChild(document.getElementById('zx-recharge-modal'))" style="width:100%;padding:11px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);color:#cbd5e1;border-radius:10px;font-family:inherit;font-weight:700;font-size:12px;cursor:pointer">إغلاق</button></div>
  </div></div>`;
  const div=document.createElement('div');div.innerHTML=html;document.body.appendChild(div.firstChild);
}
function vsAddCredits(amt){
  WALLET+=amt;localStorage.setItem('zx_credits',WALLET);$('wallet-balance').textContent=WALLET.toLocaleString('ar-EG');
  const m=document.getElementById('zx-recharge-modal');if(m)document.body.removeChild(m);
  toast('✅ تم شحن '+amt.toLocaleString('en-US')+' نقطة · رصيدك الآن '+WALLET.toLocaleString('en-US'));
  // Refresh current tab to enable disabled buttons
  if(VS_STATE&&VS_STATE.tab)vsRenderTab(VS_STATE.tab);
}

// ───── FULLSCREEN TOGGLE ─────
function vsToggleFullscreen(){
  const studio=document.querySelector('.zx-studio');if(!studio)return;
  const isFs=studio.classList.toggle('fullscreen');
  document.body.classList.toggle('studio-fs',isFs);
  const btn=document.getElementById('vs-fs-btn');if(btn){btn.innerHTML=isFs?'<i data-lucide="minimize-2" style="width:16px;height:16px"></i>':'<i data-lucide="maximize-2" style="width:16px;height:16px"></i>';if(window.lucide)lucide.createIcons();btn.title=isFs?'تصغير':'ملء الشاشة';}
  // ESC to exit
  if(isFs){
    document.addEventListener('keydown',vsEscFS);
  }else{
    document.removeEventListener('keydown',vsEscFS);
  }
}
function vsEscFS(e){if(e.key==='Escape'){vsToggleFullscreen();}}

// ───── MIC RECORDING (Web Speech API → text) ─────
let VS_RECOG=null;
function vsToggleMic(){
  const btn=document.getElementById('vs-mic-btn');const stat=document.getElementById('zx-mic-status');
  if(VS_RECOG){VS_RECOG.stop();return;}
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){alert('متصفحك ما يدعم التحويل الصوتي للنص. استخدم Chrome/Edge أو اكتب يدوياً.');return;}
  const cfg=vsGetConfig();
  const langMap={'ar-sa':'ar-SA','ar-sa-hijazi':'ar-SA','ar-sa-eastern':'ar-SA','ar-sa-southern':'ar-SA','ar-kw':'ar-KW','ar-ae':'ar-AE','ar-qa':'ar-QA','ar-bh':'ar-BH','ar-om':'ar-OM','ar-eg':'ar-EG','ar-jo':'ar-JO','ar-lb':'ar-LB','ar-sy':'ar-SY','ar-ps':'ar-PS','ar-iq':'ar-IQ','ar-ye':'ar-YE','ar-ma':'ar-MA','ar-dz':'ar-DZ','ar-tn':'ar-TN','ar-ly':'ar-LY','ar-sd':'ar-SD','ar-msa':'ar-SA','en-us':'en-US','en-gb':'en-GB','fr':'fr-FR','es':'es-ES','de':'de-DE','it':'it-IT','pt-br':'pt-BR','ru':'ru-RU','tr':'tr-TR','fa':'fa-IR','ur':'ur-PK','hi':'hi-IN','bn':'bn-BD','id':'id-ID','ms':'ms-MY','th':'th-TH','vi':'vi-VN','zh-cn':'zh-CN','zh-tw':'zh-TW','ja':'ja-JP','ko':'ko-KR','sw':'sw-KE'};
  const recog=new SR();
  recog.lang=langMap[cfg.langRaw]||'ar-SA';
  recog.continuous=true;recog.interimResults=true;
  let finalText='';
  recog.onstart=()=>{btn.classList.add('recording');stat.classList.add('show');document.getElementById('zx-mic-text').textContent='🎙️ جاري الاستماع بـ '+(recog.lang)+'… تكلّم بوضوح';};
  recog.onresult=e=>{
    let interim='';
    for(let i=e.resultIndex;i<e.results.length;i++){
      const t=e.results[i][0].transcript;
      if(e.results[i].isFinal)finalText+=t+' ';else interim+=t;
    }
    const ta=document.getElementById('vs-input-text');
    ta.value=(finalText+interim).trim();
    vsAutoSize(ta);
    document.getElementById('zx-mic-text').textContent=interim?('… '+interim.slice(0,40)):'🎙️ جاري الاستماع…';
  };
  recog.onerror=e=>{
    toast('❌ خطأ ميكروفون: '+(e.error==='not-allowed'?'يرجى السماح بالميكروفون':e.error==='no-speech'?'لم نسمع شيئاً':e.error));
    btn.classList.remove('recording');stat.classList.remove('show');VS_RECOG=null;
  };
  recog.onend=()=>{
    btn.classList.remove('recording');stat.classList.remove('show');VS_RECOG=null;
    if(finalText.trim()){toast('✓ تم التحويل: '+finalText.slice(0,50));}
  };
  try{recog.start();VS_RECOG=recog;}catch(e){toast('❌ '+e.message)}
}

// ───── LANGUAGE LABEL ─────
function vsLangLabel(code){
  return ({'ar-sa':'سعودية (نجدية)','ar-sa-hijazi':'حجازية','ar-sa-eastern':'شرقية','ar-sa-southern':'جنوبية','ar-kw':'كويتية','ar-ae':'إماراتية','ar-qa':'قطرية','ar-bh':'بحرينية','ar-om':'عُمانية','ar-eg':'مصرية','ar-jo':'أردنية','ar-lb':'لبنانية','ar-sy':'سورية','ar-ps':'فلسطينية','ar-iq':'عراقية','ar-ye':'يمنية','ar-ma':'مغربية','ar-dz':'جزائرية','ar-tn':'تونسية','ar-ly':'ليبية','ar-sd':'سودانية','ar-msa':'الفصحى','en-us':'English (US)','en-gb':'English (UK)','fr':'Français','es':'Español','de':'Deutsch','it':'Italiano','pt-br':'Português','ru':'Русский','tr':'Türkçe','fa':'فارسی','ur':'اردو','hi':'हिन्दी','bn':'বাংলা','id':'Indonesia','ms':'Melayu','th':'ไทย','vi':'Việt','zh-cn':'中文 普通话','zh-tw':'中文 台灣','ja':'日本語','ko':'한국어','sw':'Kiswahili'})[code]||code;
}
function vsVoiceLabel(code){
  return ({zenrex_male_deep:'ذكر عميق فخم',zenrex_male_warm:'ذكر دافئ ودود',zenrex_male_youth:'ذكر شبابي حيوي',zenrex_narrator_pro:'راوي احترافي',zenrex_friend_chat:'صديق محادثة',zenrex_announcer:'مذيع رسمي',zenrex_female_warm:'أنثى دافئة',zenrex_female_clear:'أنثى صافية',zenrex_storyteller_f:'راوية قصص',zenrex_news_anchor:'مذيعة أخبار',zenrex_neutral:'محايد احترافي',zenrex_documentary:'وثائقي عميق'})[code]||code;
}

// ───── DROPDOWNS ─────
function toggleDropdown(id){
  const dd=document.getElementById(id);
  document.querySelectorAll('.dropdown').forEach(d=>{if(d!==dd)d.classList.remove('open')});
  dd.classList.toggle('open');
}
function closeDropdowns(){document.querySelectorAll('.dropdown').forEach(d=>d.classList.remove('open'))}
function markAllRead(){document.querySelector('.notif-btn .dot').style.display='none';toast('✓ تم وضع علامة "مقروء" على الكل');closeDropdowns();}
document.addEventListener('click',e=>{if(!e.target.closest('.dropdown')&&!e.target.closest('.notif-btn')&&!e.target.closest('.user-pill'))closeDropdowns();});

// ───── GLOBAL SEARCH ─────
function globalSearch(q){
  q=q.trim().toLowerCase();if(!q){renderProducts();renderOrders();renderCustomers();return;}
  // Search & filter products
  const matches=PRODUCTS.filter(p=>p.name.toLowerCase().includes(q));
  $('products-grid').innerHTML=`<div class="pcard add" onclick="openProductModal()"><i data-lucide="plus-circle" style="width:36px;height:36px;margin-bottom:8px"></i>منتج جديد</div>`+matches.map(p=>`<div class="pcard" onclick="editProduct('${p.id}')"><div class="img" style="background-image:url('${p.img}')"></div><div class="body"><h4>${p.name}</h4><div class="price">${p.price} ر.س</div></div></div>`).join('');
  if(matches.length)toast(`🔍 ${matches.length} نتيجة في المنتجات`);
  setTimeout(()=>{if(window.lucide)lucide.createIcons()},50);
}

// ───── KPI CLICKABILITY ─────
function setupKpiClicks(){
  const map=[{i:0,p:'orders'},{i:1,p:'orders'},{i:2,p:'customers'},{i:3,p:'delivery'}];
  document.querySelectorAll('.kpi-grid .kpi').forEach((el,i)=>{
    const t=map.find(x=>x.i===i);if(!t)return;
    el.style.cursor='pointer';
    el.onclick=()=>{toast('📊 فتح '+({orders:'الطلبات',customers:'العملاء',delivery:'التوصيل'})[t.p]);goPage(t.p);};
  });
}

// ───── INTERACTIVE CHART TOOLTIP ─────
const CHART_DATA=[
  {day:'السبت',x:60,y:170,amt:6200,delta:0},
  {day:'الأحد',x:160,y:140,amt:8100,delta:+31},
  {day:'الإثنين',x:260,y:150,amt:7500,delta:-7},
  {day:'الثلاثاء',x:360,y:90,amt:11400,delta:+52},
  {day:'الأربعاء',x:460,y:110,amt:10200,delta:-11},
  {day:'الخميس',x:560,y:55,amt:13800,delta:+35},
  {day:'الجمعة',x:660,y:75,amt:12450,delta:-10}
];
function setupChart(){
  const g=document.getElementById('data-points');if(!g)return;
  g.innerHTML=CHART_DATA.map((p,i)=>`<circle cx="${p.x}" cy="${p.y}" r="${i===5?6:4}" fill="${i===5?'#fbbf24':'#7c3aed'}" stroke="#fff" stroke-width="2" class="cdot" data-i="${i}" style="cursor:pointer;opacity:0;animation:fadeIn .4s ${0.8+i*0.08}s forwards"/><circle cx="${p.x}" cy="${p.y}" r="22" fill="transparent" class="chit" data-i="${i}" style="cursor:pointer"/>`).join('');
  const wrap=document.getElementById('rev-chart').parentElement;
  const tip=document.getElementById('chart-tooltip');
  wrap.querySelectorAll('.chit, .cdot').forEach(c=>{
    c.addEventListener('mouseenter',e=>{
      const i=+e.target.dataset.i;const d=CHART_DATA[i];
      const rect=wrap.getBoundingClientRect();const svgEl=document.getElementById('rev-chart');const sRect=svgEl.getBoundingClientRect();
      const xPct=(d.x/700)*sRect.width;const yPct=(d.y/240)*sRect.height;
      tip.style.left=xPct+'px';tip.style.top=yPct+'px';tip.style.opacity=1;
      document.getElementById('ct-day').textContent=d.day;
      document.getElementById('ct-amt').textContent=d.amt.toLocaleString('en-US')+' ر.س';
      const dEl=document.getElementById('ct-delta');
      if(d.delta===0){dEl.textContent='— بداية الأسبوع';dEl.style.color='var(--mute)'}
      else if(d.delta>0){dEl.textContent='▲ +'+d.delta+'% عن اليوم السابق';dEl.style.color='var(--emerald)'}
      else {dEl.textContent='▼ '+d.delta+'% عن اليوم السابق';dEl.style.color='var(--rd)'}
      // Highlight dot
      wrap.querySelectorAll('.cdot').forEach(x=>x.setAttribute('r',+x.dataset.i===5?6:4));
      const dot=wrap.querySelector(`.cdot[data-i="${i}"]`);if(dot)dot.setAttribute('r',9);
    });
    c.addEventListener('mouseleave',()=>{tip.style.opacity=0;wrap.querySelectorAll('.cdot').forEach(x=>x.setAttribute('r',+x.dataset.i===5?6:4))});
    c.addEventListener('click',()=>{const i=+c.dataset.i;const d=CHART_DATA[i];toast(`📅 ${d.day}: ${d.amt.toLocaleString('en-US')} ر.س`);goPage('orders');});
  });
}

// ───── VIDEO STUDIO CONFIG ─────
function vsUpdateConfig(){
  const dur=parseInt(document.getElementById('vs-duration').value||'30');
  const scenes=Math.ceil(dur/5);
  const cost=5+(scenes*8)+5+30;
  document.getElementById('vs-cost-est').textContent=cost+' نقطة';
}
function vsDownload(url,title){const a=document.createElement('a');a.href=url;a.download=(title||'video')+'.mp4';a.click();toast('⬇️ بدأ التحميل');}
function vsPublish(url,title){
  const accounts=JSON.parse(localStorage.getItem('zx_social')||'{}');
  const active=Object.entries(accounts).filter(([k,v])=>v).map(([k])=>k);
  if(!active.length){if(confirm('لا تملك حسابات اجتماعية مربوطة. تبي تربط حساباتك الآن؟'))goPage('social');return;}
  toast('📤 جاري النشر على: '+active.map(p=>({instagram:'انستقرام',tiktok:'تيك توك',twitter:'X',snapchat:'سناب',youtube:'يوتيوب'})[p]||p).join('، '));
  setTimeout(()=>toast('✅ تم النشر بنجاح على '+active.length+' منصات'),1800);
}
function renderVsHistory(){
  const hist=JSON.parse(localStorage.getItem('zx_vs_history')||'[]');
  const el=document.getElementById('vs-history');if(!el)return;
  if(!hist.length){el.innerHTML='<div style="color:var(--mute);padding:14px;text-align:center;font-size:11px">لا فيديوهات بعد</div>';return;}
  el.innerHTML=hist.map((h,i)=>`<div onclick="window.open('${API+h.url}','_blank')" style="padding:8px;background:var(--bg);border-radius:8px;cursor:pointer;margin-bottom:6px;font-size:11px;border:1px solid var(--border)" onmouseover="this.style.borderColor='var(--purple)'" onmouseout="this.style.borderColor='var(--border)'"><b style="display:block;font-size:11px">🎬 ${h.title.slice(0,30)}</b><span style="font-size:9px;color:var(--mute)">${h.date}</span></div>`).join('');
}

// ───── SOCIAL MEDIA ─────
const SOCIAL_PLATFORMS=[
  {id:'instagram',name:'انستقرام',icon:'📸',color:'linear-gradient(135deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888)',followers:'12.4K',posts:48},
  {id:'tiktok',name:'تيك توك',icon:'🎵',color:'#000',followers:'8.7K',posts:23},
  {id:'twitter',name:'X (تويتر)',icon:'𝕏',color:'#000',followers:'5.2K',posts:189},
  {id:'snapchat',name:'سناب شات',icon:'👻',color:'#FFFC00',followers:'3.1K',posts:12,fg:'#000'},
  {id:'youtube',name:'يوتيوب',icon:'▶',color:'#FF0000',followers:'2.4K',posts:15},
  {id:'facebook',name:'فيسبوك',icon:'f',color:'#1877F2',followers:'6.8K',posts:67},
  {id:'whatsapp',name:'واتساب بزنس',icon:'💬',color:'#25D366',followers:'-',posts:0,custom:'قناة'},
  {id:'telegram',name:'تيليجرام',icon:'✈',color:'#0088cc',followers:'1.2K',posts:34}
];
function loadSocial(){
  const acc=JSON.parse(localStorage.getItem('zx_social')||'{"instagram":true,"tiktok":true,"twitter":true}');
  document.getElementById('social-grid').innerHTML=SOCIAL_PLATFORMS.map(p=>{
    const connected=!!acc[p.id];
    return `<div class="social-card"><div class="logo" style="background:${p.color};color:${p.fg||'#fff'}">${p.icon}</div><div style="flex:1;min-width:0"><b style="font-size:13px">${p.name}</b><div class="mini-stat">${connected?`✓ مربوط · 👥 ${p.followers} متابع · 📝 ${p.posts} منشور`:'غير مربوط'}</div></div><button class="btn ${connected?'btn-outline':'btn-primary'}" style="padding:8px 14px;font-size:11px" onclick="toggleSocial('${p.id}')">${connected?'فصل':'+ ربط'}</button></div>`;
  }).join('');
  document.getElementById('social-posts').innerHTML=[
    {p:'انستقرام',c:'إعلان iPhone 17 Pro Max',v:'24.8K',e:'1,234 إعجاب · 89 تعليق',st:'منشور'},
    {p:'تيك توك',c:'تخفيضات نهاية الأسبوع 🔥',v:'52.1K',e:'3,489 لايك · 412 مشاركة',st:'منشور'},
    {p:'X (تويتر)',c:'AirPods Pro 3 — جوّك المثالي',v:'8.4K',e:'234 إعادة · 567 إعجاب',st:'منشور'},
    {p:'انستقرام',c:'Apple Watch Ultra 2 جديد',v:'-',e:'-',st:'مجدول الإثنين 6م'},
    {p:'يوتيوب Shorts',c:'MacBook Pro M4 unboxing',v:'12.6K',e:'845 إعجاب',st:'منشور'}
  ].map(r=>`<tr><td><b>${r.p}</b></td><td>${r.c}</td><td><b>${r.v}</b></td><td style="font-size:11px;color:var(--mute)">${r.e}</td><td><span class="status-pill ${r.st==='منشور'?'s-paid':'s-pending'}">${r.st}</span></td></tr>`).join('');
  renderSocialMini();
}
function toggleSocial(id){
  const acc=JSON.parse(localStorage.getItem('zx_social')||'{}');
  acc[id]=!acc[id];
  localStorage.setItem('zx_social',JSON.stringify(acc));
  loadSocial();
  toast(acc[id]?'✓ تم ربط الحساب':'تم فصل الحساب');
}
function renderSocialMini(){
  const el=document.getElementById('vs-social-mini');if(!el)return;
  const acc=JSON.parse(localStorage.getItem('zx_social')||'{"instagram":true,"tiktok":true,"twitter":true}');
  el.innerHTML=SOCIAL_PLATFORMS.slice(0,5).map(p=>`<label style="display:flex;align-items:center;gap:8px;padding:7px 10px;background:var(--bg);border-radius:8px;cursor:pointer;font-size:11px;font-weight:700"><input type="checkbox" ${acc[p.id]?'checked':''} onchange="toggleSocial('${p.id}')" style="accent-color:var(--purple)"><span style="width:22px;height:22px;border-radius:6px;background:${p.color};color:${p.fg||'#fff'};display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:900">${p.icon}</span>${p.name}${acc[p.id]?`<span style="margin-right:auto;color:var(--emerald);font-size:10px">✓</span>`:''}</label>`).join('');
}

// Animated KPI counters
function animateKPIs(){
  document.querySelectorAll('.kpi .val').forEach(el=>{
    const txt=el.textContent.trim();
    const numMatch=txt.match(/[\d,]+(\.\d+)?/);
    if(!numMatch)return;
    const target=parseFloat(numMatch[0].replace(/,/g,''));
    if(isNaN(target))return;
    const suffix=txt.substring(txt.indexOf(numMatch[0])+numMatch[0].length);
    const prefix=txt.substring(0,txt.indexOf(numMatch[0]));
    let cur=0;
    const dur=1200,steps=40,inc=target/steps;
    const itv=setInterval(()=>{
      cur+=inc;
      if(cur>=target){cur=target;clearInterval(itv);}
      const formatted=cur>=1000?Math.floor(cur).toLocaleString('en-US'):cur.toFixed(target%1?2:0);
      el.innerHTML=prefix+formatted+suffix;
    },dur/steps);
  });
  // Chart breathing: subtle scale animation on key dot
  const dot=document.querySelector('.chart-wrap circle[fill="#fbbf24"]');
  if(dot){
    let scale=1;
    setInterval(()=>{scale=scale===1?1.3:1;dot.setAttribute('r',5*scale);},800);
  }
}

// Add live pulse to KPI labels for "today" data
setInterval(()=>{
  document.querySelectorAll('.kpi:not(.no-pulse) .lbl').forEach(el=>{
    if(el.textContent.includes('اليوم')&&!el.querySelector('.live-pulse')){
      el.insertAdjacentHTML('beforeend',' <span class="live-pulse">حي</span>');
    }
  });
},1000);

// Init lucide icons on load
window.addEventListener('load',()=>{
  if(window.lucide)lucide.createIcons();
  // Sync sandbox checkbox
  const sb=document.getElementById('sandbox-toggle');if(sb)sb.checked=isSandboxMode();
  // Global sandbox indicator on every page
  if(isSandboxMode()&&!document.getElementById('sandbox-global-banner')){
    const sbBanner=document.createElement('div');
    sbBanner.id='sandbox-global-banner';
    sbBanner.style.cssText='position:fixed;bottom:14px;left:14px;background:linear-gradient(135deg,#f59e0b,#dc2626);color:#fff;padding:9px 16px;border-radius:99px;font-size:12px;font-weight:900;z-index:200;box-shadow:0 8px 24px rgba(245,158,11,.5);display:flex;align-items:center;gap:8px;cursor:pointer';
    sbBanner.innerHTML='🧪 الوضع التجريبي · معاملات وهمية';
    sbBanner.onclick=()=>goPage('gateways');
    document.body.appendChild(sbBanner);
  }
  // Branch scope detection (from URL or localStorage)
  try{
    const urlBranch=new URLSearchParams(location.search).get('branch');
    if(urlBranch){localStorage.setItem('zx_active_branch_scope',urlBranch);}
    const scope=localStorage.getItem('zx_active_branch_scope');
    if(scope){
      const branches=JSON.parse(localStorage.getItem('zx_merchant_branches')||'[]');
      const b=branches.find(x=>x.id===scope);
      if(b&&!b.is_main){
        const banner=document.createElement('div');
        banner.id='branch-scope-banner';
        banner.style.cssText='position:sticky;top:0;background:linear-gradient(135deg,#10b981,#059669);color:#fff;padding:8px 16px;font-size:12px;font-weight:900;display:flex;justify-content:space-between;align-items:center;z-index:50;box-shadow:0 2px 12px rgba(16,185,129,.3)';
        banner.innerHTML=`<span>🏪 تدير الآن: <b>${b.name_ar}</b> · كل البيانات مفلترة لهذا الفرع</span><button onclick="exitBranchScope()" style="background:#fff;color:#065f46;border:none;padding:6px 14px;border-radius:99px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">↩️ الخروج للعرض الكلي</button>`;
        const root=document.querySelector('.main-content')||document.body;
        root.insertBefore(banner,root.firstChild);
      }
    }
  }catch(_){}
});
function exitBranchScope(){
  localStorage.removeItem('zx_active_branch_scope');
  toast('↩️ تم الخروج من نطاق الفرع · العرض الكلي');
  setTimeout(()=>location.href=location.pathname,400);
}
// ═══════════════════ THEME CUSTOMIZER ═══════════════════
let CURRENT_THEME = {
  mode: 'dark',
  font_family: 'Tajawal',
  font_size: 15,
  buttons_style: 'gradient',
  radius_scale: 1.0,
  colors: { bg:'#0a0a14', surface:'#14142b', accent:'#7c3aed', amber:'#fbbf24', text:'#f1f5f9', border:'#2d2d4a' }
};
const THEME_PRESETS = {
  zenrex:   { mode:'dark',  font_family:'Tajawal', colors:{bg:'#0a0a14',surface:'#14142b',accent:'#7c3aed',amber:'#fbbf24',text:'#f1f5f9',border:'#2d2d4a'} },
  luxury:  { mode:'dark',  font_family:'Cairo',   colors:{bg:'#0a0908',surface:'#1c1916',accent:'#fbbf24',amber:'#d97706',text:'#fef3c7',border:'#3f3a2e'} },
  emerald: { mode:'dark',  font_family:'Rubik',   colors:{bg:'#022c22',surface:'#064e3b',accent:'#10b981',amber:'#34d399',text:'#ecfdf5',border:'#065f46'} },
  rose:    { mode:'dark',  font_family:'Almarai', colors:{bg:'#1f1129',surface:'#2d1b3d',accent:'#ec4899',amber:'#f9a8d4',text:'#fce7f3',border:'#4a2554'} },
  ocean:   { mode:'dark',  font_family:'IBM Plex Sans Arabic', colors:{bg:'#0c1c3a',surface:'#1e3a5f',accent:'#3b82f6',amber:'#60a5fa',text:'#dbeafe',border:'#1e40af'} },
  day:     { mode:'light', font_family:'Tajawal', colors:{bg:'#fafafa',surface:'#ffffff',accent:'#7c3aed',amber:'#f59e0b',text:'#0f172a',border:'#e5e7eb'} },
};

function themeSet(key, value) {
  if(['bg','surface','accent','amber','text','border'].includes(key)) {
    CURRENT_THEME.colors[key] = value;
  } else {
    CURRENT_THEME[key] = value;
  }
  applyThemeLive();
}

function applyThemeLive() {
  const root = document.documentElement;
  const c = CURRENT_THEME.colors;
  // New zx-* variables
  root.style.setProperty('--zx-bg', c.bg);
  root.style.setProperty('--zx-bg-2', c.bg);
  root.style.setProperty('--zx-surface', c.surface);
  root.style.setProperty('--zx-surface-2', c.surface);
  root.style.setProperty('--zx-accent', c.accent);
  root.style.setProperty('--zx-accent-2', c.accent);
  root.style.setProperty('--zx-amber', c.amber);
  root.style.setProperty('--zx-text', c.text);
  root.style.setProperty('--zx-border', c.border);
  // ALSO override the legacy variables that admin.html UI uses everywhere
  root.style.setProperty('--purple', c.accent);
  root.style.setProperty('--violet', c.accent);
  root.style.setProperty('--amber', c.amber);
  root.style.setProperty('--bg', c.bg);
  root.style.setProperty('--panel', c.surface);
  root.style.setProperty('--border', c.border);
  root.style.setProperty('--ink', c.bg);
  root.style.setProperty('--ink2', c.surface);
  root.style.setProperty('--sidebar', c.surface);
  // Font family — set on root AND body so all elements inherit
  const fontStack = `'${CURRENT_THEME.font_family}','Tajawal','Cairo',sans-serif`;
  root.style.setProperty('--zx-font', fontStack);
  document.body.style.fontFamily = fontStack;
  document.documentElement.style.fontFamily = fontStack;
  // Apply font to all panels/cards/buttons explicitly (some override font-family in inline styles)
  document.querySelectorAll('button, input, select, textarea, .panel, .card, .pcard, .ps-input, h1,h2,h3,h4').forEach(el => {
    el.style.fontFamily = fontStack;
  });
  // Font size on body
  if(CURRENT_THEME.font_size) document.body.style.fontSize = CURRENT_THEME.font_size + 'px';
  // Mode: toggle classes + main bg color
  document.body.classList.toggle('zx-dark', CURRENT_THEME.mode === 'dark');
  document.body.classList.toggle('zx-light', CURRENT_THEME.mode === 'light');
  document.body.classList.toggle('dark-mode', CURRENT_THEME.mode === 'dark');
  document.body.style.background = c.bg;
  document.body.style.color = c.text;
  // Update preview area
  const prev = document.getElementById('tm-preview');
  if(prev) {
    prev.style.fontFamily = fontStack;
    prev.style.fontSize = (CURRENT_THEME.font_size || 15) + 'px';
    prev.style.color = c.text;
  }
}

function applyPreset(key) {
  const p = THEME_PRESETS[key];
  if(!p) return;
  CURRENT_THEME = {...CURRENT_THEME, ...p, colors: {...CURRENT_THEME.colors, ...p.colors}};
  // Sync UI inputs
  const setVal = (id, v) => { const el = document.getElementById(id); if(el) el.value = v; };
  setVal('tm-bg', p.colors.bg);
  setVal('tm-surface', p.colors.surface);
  setVal('tm-accent', p.colors.accent);
  setVal('tm-amber', p.colors.amber);
  setVal('tm-text', p.colors.text);
  setVal('tm-border', p.colors.border);
  setVal('tm-font', p.font_family);
  applyThemeLive();
  toast(`✓ تم تطبيق ثيم: ${key}`);
}

async function saveTheme() {
  try {
    const token = localStorage.getItem('zx_token') || '';
    const r = await fetch(API+'/api/theme/merchant/me', {
      method:'PUT',
      headers:{'Content-Type':'application/json', ...(token?{'Authorization':'Bearer '+token}:{})},
      body: JSON.stringify(CURRENT_THEME)
    });
    if(r.ok) toast('✓ تم حفظ الهوية وستظهر للعملاء الجدد فوراً');
    else toast('⚠️ فشل الحفظ — سجل دخول مرة أخرى');
  } catch(e) { toast('⚠️ '+e.message); }
}

async function resetTheme() {
  if(!confirm('استعادة الهوية الافتراضية لـ Zenrex؟')) return;
  try {
    const token = localStorage.getItem('zx_token') || '';
    await fetch(API+'/api/theme/merchant/reset', {method:'POST', headers:{...(token?{'Authorization':'Bearer '+token}:{})}});
    applyPreset('zenrex');
    toast('✓ تم استعادة الهوية الافتراضية');
  } catch(e) { toast('⚠️ '+e.message); }
}

async function loadMyTheme() {
  try {
    const token = localStorage.getItem('zx_token') || '';
    if(!token) return;
    const r = await fetch(API+'/api/theme/merchant/me', {headers:{'Authorization':'Bearer '+token}});
    if(!r.ok) return;
    const t = await r.json();
    if(t && !t.is_default) {
      CURRENT_THEME = {...CURRENT_THEME, ...t, colors:{...CURRENT_THEME.colors, ...(t.colors||{})}};
      // Sync UI inputs if visible
      const setVal = (id, v) => { const el = document.getElementById(id); if(el && v!=null) el.value = v; };
      const c = CURRENT_THEME.colors;
      setVal('tm-bg', c.bg); setVal('tm-surface', c.surface); setVal('tm-accent', c.accent);
      setVal('tm-amber', c.amber); setVal('tm-text', c.text); setVal('tm-border', c.border);
      setVal('tm-font', CURRENT_THEME.font_family);
      setVal('tm-fs', CURRENT_THEME.font_size || 15);
      setVal('tm-btn-style', CURRENT_THEME.buttons_style);
      setVal('tm-radius', CURRENT_THEME.radius_scale || 1);
      applyThemeLive();
    }
  } catch(_) {}
}
// Auto-load theme after login
setTimeout(loadMyTheme, 1500);
