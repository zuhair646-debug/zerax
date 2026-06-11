/* Zenrex Business Templates — pre-built category + sample-product packs.
 * Merchants can pick a template during onboarding to seed their catalog instantly.
 * Each template ships with: emoji, name (ar+en), description, categories array, and sample products.
 */

window.ZENREX_BUSINESS_TEMPLATES = [
  {
    id: 'barber',
    emoji: '💈',
    name_ar: 'حلاقة وعناية رجالية',
    name_en: 'Barber & Men Grooming',
    desc_ar: 'صالونات الحلاقة، اللحى، تقليم الشعر، وعناية الرجال.',
    categories: [
      { id: 'haircut', name_ar: 'قصات الشعر', emoji: '✂️' },
      { id: 'beard',   name_ar: 'حلاقة وتنظيف اللحية', emoji: '🧔' },
      { id: 'shave',   name_ar: 'حلاقة كلاسيكية', emoji: '🪒' },
      { id: 'kids',    name_ar: 'قصات الأطفال', emoji: '👦' },
      { id: 'spa',     name_ar: 'سبا وجه ومساج', emoji: '💆' },
      { id: 'products', name_ar: 'منتجات العناية', emoji: '🧴' },
    ],
    sample_products: [
      { name: 'قصة شعر كلاسيكية', price: 50, category: 'haircut' },
      { name: 'قصة + تشكيل لحية', price: 80, category: 'haircut' },
      { name: 'حلاقة لحية كاملة', price: 40, category: 'beard' },
      { name: 'شامبو + مساج فروة', price: 35, category: 'spa' },
      { name: 'قصة شعر للأطفال', price: 30, category: 'kids' },
      { name: 'كريم لحية فاخر', price: 75, category: 'products' },
    ]
  },
  {
    id: 'stationery',
    emoji: '✏️',
    name_ar: 'قرطاسية ومستلزمات مدرسية',
    name_en: 'Stationery & School Supplies',
    desc_ar: 'دفاتر، أقلام، حقائب، أدوات هندسية، مستلزمات مدرسية.',
    categories: [
      { id: 'pens',     name_ar: 'أقلام وأقلام تلوين', emoji: '🖊️' },
      { id: 'notebooks', name_ar: 'دفاتر وكشاكيل', emoji: '📓' },
      { id: 'bags',     name_ar: 'حقائب وشنط', emoji: '🎒' },
      { id: 'art',      name_ar: 'أدوات فنون وتلوين', emoji: '🎨' },
      { id: 'office',   name_ar: 'مستلزمات مكتبية', emoji: '📎' },
      { id: 'books',    name_ar: 'كتب ومراجع', emoji: '📚' },
    ],
    sample_products: [
      { name: 'دفتر A4 ١٠٠ ورقة', price: 12, category: 'notebooks' },
      { name: 'باكيت أقلام جاف ١٠ ألوان', price: 25, category: 'pens' },
      { name: 'حقيبة ظهر مدرسية', price: 95, category: 'bags' },
      { name: 'علبة ألوان خشبية ٢٤', price: 35, category: 'art' },
      { name: 'دباسة + علبة دبابيس', price: 18, category: 'office' },
      { name: 'مسطرة هندسية ٣٠سم', price: 8, category: 'office' },
    ]
  },
  {
    id: 'restaurant',
    emoji: '🍔',
    name_ar: 'مطعم / وجبات سريعة',
    name_en: 'Restaurant / Fast Food',
    desc_ar: 'مطاعم وجبات سريعة، شاورما، برجر، بيتزا، مقبلات.',
    categories: [
      { id: 'burgers',  name_ar: 'برجر', emoji: '🍔' },
      { id: 'shawarma', name_ar: 'شاورما وساندويش', emoji: '🌯' },
      { id: 'pizza',    name_ar: 'بيتزا', emoji: '🍕' },
      { id: 'sides',    name_ar: 'مقبلات', emoji: '🍟' },
      { id: 'drinks',   name_ar: 'مشروبات', emoji: '🥤' },
      { id: 'desserts', name_ar: 'حلويات', emoji: '🍰' },
    ],
    sample_products: [
      { name: 'شاورما عربي', price: 18, category: 'shawarma' },
      { name: 'برجر دجاج', price: 25, category: 'burgers' },
      { name: 'بيتزا مارجريتا متوسطة', price: 45, category: 'pizza' },
      { name: 'بطاطس مقلية كبير', price: 12, category: 'sides' },
      { name: 'بيبسي ٣٣٠مل', price: 5, category: 'drinks' },
      { name: 'تشيز كيك', price: 22, category: 'desserts' },
    ]
  },
  {
    id: 'pharmacy',
    emoji: '💊',
    name_ar: 'صيدلية',
    name_en: 'Pharmacy',
    desc_ar: 'أدوية، فيتامينات، مستلزمات طبية، مستحضرات تجميل.',
    categories: [
      { id: 'medicine', name_ar: 'أدوية', emoji: '💊' },
      { id: 'vitamins', name_ar: 'فيتامينات ومكملات', emoji: '🌿' },
      { id: 'skin',     name_ar: 'العناية بالبشرة', emoji: '🧴' },
      { id: 'baby',     name_ar: 'منتجات أطفال', emoji: '👶' },
      { id: 'medical',  name_ar: 'أجهزة ومستلزمات طبية', emoji: '🩺' },
      { id: 'first_aid', name_ar: 'إسعاف أولي', emoji: '🩹' },
    ],
    sample_products: [
      { name: 'بنادول إكسترا', price: 18, category: 'medicine' },
      { name: 'فيتامين C ١٠٠٠', price: 65, category: 'vitamins' },
      { name: 'كريم ترطيب وجه', price: 85, category: 'skin' },
      { name: 'حفاضات أطفال M', price: 95, category: 'baby' },
      { name: 'جهاز قياس ضغط', price: 245, category: 'medical' },
      { name: 'بلاستر طبي - علبة', price: 12, category: 'first_aid' },
    ]
  },
  {
    id: 'cafe',
    emoji: '☕',
    name_ar: 'كافيه ومشروبات',
    name_en: 'Café & Beverages',
    desc_ar: 'قهوة مختصة، كابتشينو، شاي، مشروبات باردة، حلويات.',
    categories: [
      { id: 'hot',   name_ar: 'مشروبات ساخنة', emoji: '☕' },
      { id: 'cold',  name_ar: 'مشروبات باردة', emoji: '🧊' },
      { id: 'specialty', name_ar: 'قهوة مختصة', emoji: '🫘' },
      { id: 'tea',   name_ar: 'شاي وأعشاب', emoji: '🍵' },
      { id: 'sweets', name_ar: 'حلويات ومعجنات', emoji: '🥐' },
      { id: 'breakfast', name_ar: 'فطور', emoji: '🍳' },
    ],
    sample_products: [
      { name: 'إسبريسو سنغل', price: 12, category: 'hot' },
      { name: 'كابتشينو وسط', price: 18, category: 'hot' },
      { name: 'في 60 برد', price: 22, category: 'specialty' },
      { name: 'آيس لاتيه', price: 20, category: 'cold' },
      { name: 'كرواسون شوكولاتة', price: 16, category: 'sweets' },
      { name: 'بيض بنديكت', price: 38, category: 'breakfast' },
    ]
  },
  {
    id: 'salon',
    emoji: '💅',
    name_ar: 'صالون نسائي / مركز تجميل',
    name_en: 'Women Beauty Salon',
    desc_ar: 'تصفيف شعر، مكياج، أظافر، عناية بالبشرة للنساء.',
    categories: [
      { id: 'hair',    name_ar: 'تصفيف وصبغ شعر', emoji: '💇' },
      { id: 'makeup',  name_ar: 'مكياج وعروس', emoji: '💄' },
      { id: 'nails',   name_ar: 'أظافر ومناكير', emoji: '💅' },
      { id: 'skin',    name_ar: 'عناية بالبشرة', emoji: '✨' },
      { id: 'henna',   name_ar: 'حناء ورسم', emoji: '🤚' },
      { id: 'spa',     name_ar: 'سبا وجلسات استرخاء', emoji: '🌺' },
    ],
    sample_products: [
      { name: 'تصفيف شعر مناسبات', price: 150, category: 'hair' },
      { name: 'صبغة شعر كاملة', price: 280, category: 'hair' },
      { name: 'مكياج كاجوال', price: 200, category: 'makeup' },
      { name: 'مكياج عروس', price: 950, category: 'makeup' },
      { name: 'مناكير + بديكير', price: 130, category: 'nails' },
      { name: 'حناء يدين', price: 80, category: 'henna' },
    ]
  },
  {
    id: 'electronics',
    emoji: '📱',
    name_ar: 'إلكترونيات وجوالات',
    name_en: 'Electronics & Mobiles',
    desc_ar: 'جوالات، إكسسوارات، كمبيوترات، سماعات، شواحن.',
    categories: [
      { id: 'phones',   name_ar: 'جوالات', emoji: '📱' },
      { id: 'accessories', name_ar: 'إكسسوارات', emoji: '🎧' },
      { id: 'laptops',  name_ar: 'كمبيوترات', emoji: '💻' },
      { id: 'audio',    name_ar: 'صوتيات وسماعات', emoji: '🔊' },
      { id: 'wearables', name_ar: 'ساعات ذكية', emoji: '⌚' },
      { id: 'cables',   name_ar: 'كيبلات وشواحن', emoji: '🔌' },
    ],
    sample_products: [
      { name: 'iPhone 15 — 256GB', price: 3899, category: 'phones' },
      { name: 'كفر سيلكون شفاف', price: 35, category: 'accessories' },
      { name: 'سماعة AirPods Pro', price: 949, category: 'audio' },
      { name: 'Apple Watch SE', price: 1099, category: 'wearables' },
      { name: 'شاحن سريع 20W', price: 89, category: 'cables' },
      { name: 'لاب توب HP i5', price: 2799, category: 'laptops' },
    ]
  },
  {
    id: 'fashion',
    emoji: '👗',
    name_ar: 'أزياء وملابس',
    name_en: 'Fashion & Clothing',
    desc_ar: 'ملابس رجالية، نسائية، أطفال، عبايات، أحذية.',
    categories: [
      { id: 'men',     name_ar: 'رجالي', emoji: '👔' },
      { id: 'women',   name_ar: 'نسائي', emoji: '👗' },
      { id: 'abaya',   name_ar: 'عبايات', emoji: '🧕' },
      { id: 'kids',    name_ar: 'أطفال', emoji: '🧒' },
      { id: 'shoes',   name_ar: 'أحذية', emoji: '👟' },
      { id: 'bags',    name_ar: 'حقائب', emoji: '👜' },
    ],
    sample_products: [
      { name: 'قميص رجالي قطن', price: 95, category: 'men' },
      { name: 'فستان كاجوال', price: 185, category: 'women' },
      { name: 'عباية كلاسيك أسود', price: 280, category: 'abaya' },
      { name: 'بدلة أطفال', price: 65, category: 'kids' },
      { name: 'حذاء رياضي', price: 220, category: 'shoes' },
      { name: 'حقيبة كتف', price: 145, category: 'bags' },
    ]
  },
];

// Apply selected template — seeds categories + sample products via API.
window.applyBusinessTemplate = async function(templateId, opts){
  opts = opts || {};
  const t = (window.ZENREX_BUSINESS_TEMPLATES||[]).find(x=>x.id===templateId);
  if (!t){ alert('قالب غير معروف'); return; }
  if (!confirm(`سيتم إضافة ${t.categories.length} قسم و ${t.sample_products.length} منتج نموذجي للقالب «${t.name_ar}». استمر؟`)) return;
  try {
    const base = (window.API || window.location.origin);
    let added = 0;
    // Create each sample product
    for (const p of t.sample_products){
      try {
        const r = await fetch(base + '/api/store/products', {
          method:'POST',
          headers:{'Content-Type':'application/json', 'Authorization':'Bearer ' + (localStorage.getItem('zx_token')||'')},
          body: JSON.stringify({
            name: p.name,
            price: p.price,
            description: `منتج نموذجي من قالب ${t.name_ar}`,
            category: p.category,
            stock: 50,
            image: '',
            template_id: t.id
          })
        });
        if (r.ok) added++;
      } catch(e){ console.warn('product failed', e); }
    }
    // Persist template selection
    try { localStorage.setItem('zx_business_template', JSON.stringify({id:t.id, name:t.name_ar, applied_at: Date.now()})); } catch(e){}
    if (typeof toast === 'function') toast(`✅ تم تطبيق قالب «${t.name_ar}» — ${added}/${t.sample_products.length} منتج`);
    else alert(`✅ تم تطبيق قالب «${t.name_ar}» — ${added}/${t.sample_products.length} منتج`);
    if (typeof renderProducts === 'function') renderProducts();
    if (typeof goPage === 'function') goPage('products');
  } catch(err){
    console.error(err);
    alert('فشل تطبيق القالب: ' + (err.message||''));
  }
};

// Render template picker grid (called from admin onboarding or dedicated page).
window.renderBusinessTemplates = function(containerSel){
  const root = document.querySelector(containerSel) || document.getElementById('biz-templates-root');
  if (!root) return;
  const cards = (window.ZENREX_BUSINESS_TEMPLATES||[]).map(t=>`
    <div data-testid="biz-template-${t.id}" style="background:#fff;border:1.5px solid #e5e7eb;border-radius:14px;padding:18px;cursor:pointer;transition:all .2s;font-family:inherit" onmouseover="this.style.borderColor='#7c3aed';this.style.boxShadow='0 10px 28px rgba(124,58,237,.15)';this.style.transform='translateY(-2px)'" onmouseout="this.style.borderColor='#e5e7eb';this.style.boxShadow='none';this.style.transform='translateY(0)'" onclick="applyBusinessTemplate('${t.id}')">
      <div style="font-size:42px;margin-bottom:8px">${t.emoji}</div>
      <h3 style="font-size:15px;font-weight:900;color:#0f172a;margin-bottom:4px">${t.name_ar}</h3>
      <p style="font-size:11px;color:#64748b;margin-bottom:12px;line-height:1.6">${t.desc_ar}</p>
      <div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px">
        ${t.categories.slice(0,4).map(c=>`<span style="background:#faf5ff;color:#7c3aed;padding:3px 8px;border-radius:10px;font-size:10px;font-weight:700">${c.emoji} ${c.name_ar}</span>`).join('')}
        ${t.categories.length>4?`<span style="color:#94a3b8;font-size:10px;padding:3px 4px">+${t.categories.length-4} أكثر</span>`:''}
      </div>
      <button style="width:100%;padding:9px;background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;border:none;border-radius:9px;font-weight:900;font-size:12px;cursor:pointer;font-family:inherit">⚡ طبّق هذا القالب</button>
    </div>
  `).join('');
  root.innerHTML = `
    <div style="background:linear-gradient(135deg,#faf5ff,#fff);border:1px solid #e5e7eb;border-radius:16px;padding:20px;margin-bottom:20px">
      <h2 style="font-size:18px;font-weight:900;color:#0f172a;margin-bottom:4px">🎯 اختر نوع نشاطك</h2>
      <p style="font-size:12px;color:#64748b">القالب يضيف لك الأقسام + منتجات نموذجية فوراً — توفّر عليك ساعات إعداد!</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px">${cards}</div>
  `;
};
