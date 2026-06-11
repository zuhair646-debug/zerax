const API = window.location.origin;

// ═══════════════════════ ZENREX CREDITS + ADMIN MODE + IMAGE OVERRIDES ═══════════════════════
let ZENREX_CREDITS=parseInt(localStorage.getItem('zx_credits')||'50',10);
let ADMIN_MODE=localStorage.getItem('zx_admin')==='1';
let STUDIO_TARGET=null;
let GEN_RESULT=null;
const IMG_OVERRIDES=JSON.parse(localStorage.getItem('zx_img_overrides')||'{}');

const STUDIO_LIBRARY={
  main_banner:[
    'https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1600&q=85',
    'https://images.unsplash.com/photo-1607083206869-4c7672e72a8a?w=1600&q=85',
    'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=1600&q=85',
    'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=1600&q=85',
    'https://images.unsplash.com/photo-1611243705797-7b65fefdc111?w=1600&q=85',
    'https://images.unsplash.com/photo-1607083206325-caf1edba7a83?w=1600&q=85',
  ],
  cat_banner:[
    'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=1600&q=85',
    'https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=1600&q=85',
    'https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=1600&q=85',
    'https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=1600&q=85',
    'https://images.unsplash.com/photo-1618220179428-22790b461013?w=1600&q=85',
    'https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=1600&q=85',
  ],
  product:[
    'https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=800&q=85',
    'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&q=85',
    'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&q=85',
    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&q=85',
    'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=85',
    'https://images.unsplash.com/photo-1556228720-195a672e8a03?w=800&q=85',
  ],
};

const STUDIO_SUGGESTIONS={
  ar:{
    main_banner:['عرض تخفيضات الجمعة البيضاء بإضاءة سينمائية','بنر فاخر للأزياء الراقية مع ذهب','بنر ربيعي مشرق بألوان زاهية','منتجات تقنية حديثة بإضاءة نيون'],
    cat_banner:['خلفية مكياج فاخر بإضاءة وردية','عرض إلكترونيات بإضاءة نيون','عرض أزياء بمنظر استوديو','مأكولات شهية مضاءة فنياً'],
    product:['منتج باحترافية على خلفية بيضاء','منتج بإضاءة دراماتيكية','منتج على رخام فاخر'],
  },
  en:{
    main_banner:['Black Friday sale banner cinematic light','Luxury fashion banner with gold','Bright vivid spring banner','Modern tech products neon'],
    cat_banner:['Luxury makeup background rose lighting','Electronics neon display','Fashion runway studio shot','Gourmet food artistic lighting'],
    product:['Pro product shot white background','Product dramatic lighting','Product on luxury marble'],
  }
};

const RATES = {SAR:1,AED:0.98,KWD:0.082,QAR:0.97,BHD:0.10,OMR:0.103,IQD:350,SYP:3400,JOD:0.19,LBP:24000,EGP:13,IRR:11200,YER:67,ILS:1,CNY:1.93,JPY:40,KRW:360,INR:22,USD:0.267,GBP:0.21,EUR:0.25,CHF:0.24,SEK:2.8,RUB:24,TRY:9.1,MAD:2.7,DZD:36,TND:0.83,LYD:1.3,SDG:160,PKR:75,BDT:32,IDR:4200,MYR:1.25,THB:9.5,PHP:15.3,VND:6500,CAD:0.36,MXN:5.4,BRL:1.6,ARS:270,ZAR:5.0,NGN:430,KES:34,AUD:0.41};

// ═══════════════════════ BRANCHES (Multi-branch eCommerce) ═══════════════════════
// Each branch has location + which products it stocks (out_of_stock list = products it's missing)
const BRANCHES=[
  {id:'b1',ar:'فرع الرياض - العليا',en:'Riyadh - Olaya Branch',addrAr:'شارع العليا، الرياض',addrEn:'Olaya St, Riyadh',lat:24.6877,lng:46.6857,out_of_stock:['p34','p40'],ship_modifier:1.0,phone:'+966112345678'},
  {id:'b2',ar:'فرع الرياض - الملز',en:'Riyadh - Malaz Branch',addrAr:'حي الملز، الرياض',addrEn:'Malaz District, Riyadh',lat:24.6745,lng:46.7335,out_of_stock:['p12','p35'],ship_modifier:1.0,phone:'+966112345679'},
  {id:'b3',ar:'فرع جدة - التحلية',en:'Jeddah - Tahlia Branch',addrAr:'شارع التحلية، جدة',addrEn:'Tahlia St, Jeddah',lat:21.5810,lng:39.1653,out_of_stock:['p11','p36','p37'],ship_modifier:1.15,phone:'+966122345678'},
  {id:'b4',ar:'فرع الدمام - الشاطئ',en:'Dammam - Corniche Branch',addrAr:'كورنيش الدمام',addrEn:'Dammam Corniche',lat:26.4366,lng:50.1040,out_of_stock:['p13','p38'],ship_modifier:1.25,phone:'+966132345678'},
];

// ═══════════════════════ SHIPPING METHODS ═══════════════════════
const SHIP_METHODS=[
  {id:'standard',ar:'توصيل عادي',en:'Standard Delivery',etaAr:'٢-٤ أيام',etaEn:'2-4 days',sar:15,ico:'🚚'},
  {id:'express',ar:'توصيل سريع',en:'Express Delivery',etaAr:'٢٤ ساعة',etaEn:'24 hours',sar:35,ico:'⚡'},
  {id:'sameday',ar:'توصيل نفس اليوم',en:'Same-day Delivery',etaAr:'خلال ٤ ساعات',etaEn:'Within 4 hours',sar:55,ico:'🏃'},
  {id:'pickup',ar:'استلام من الفرع',en:'Pickup from Branch',etaAr:'جاهز خلال ساعة',etaEn:'Ready in 1 hour',sar:0,ico:'🏪'},
];

// ═══════════════════════ SOCIAL MEDIA BY MARKET ═══════════════════════
// Country-specific defaults (China uses WeChat/Weibo, Russia uses VK/Telegram, Japan uses LINE, etc.)
const SOCIAL_PRESETS={
  // Gulf, MENA, EU, US, AU — global defaults
  default:[
    {id:'x',name:'X',icon:'fa-brands fa-x-twitter',color:'#000',url:'https://twitter.com'},
    {id:'snap',name:'Snapchat',icon:'fa-brands fa-snapchat',color:'#fffc00',url:'https://snapchat.com'},
    {id:'ig',name:'Instagram',icon:'fa-brands fa-instagram',color:'#e1306c',url:'https://instagram.com'},
    {id:'tt',name:'TikTok',icon:'fa-brands fa-tiktok',color:'#000',url:'https://tiktok.com'},
    {id:'yt',name:'YouTube',icon:'fa-brands fa-youtube',color:'#ff0000',url:'https://youtube.com'},
    {id:'wa',name:'WhatsApp',icon:'fa-brands fa-whatsapp',color:'#25d366',url:'https://wa.me/966512345678'},
  ],
  cn:[
    {id:'wechat',name:'WeChat',icon:'fa-brands fa-weixin',color:'#07c160',url:'https://wechat.com'},
    {id:'weibo',name:'Weibo',icon:'fa-brands fa-weibo',color:'#e6162d',url:'https://weibo.com'},
    {id:'douyin',name:'Douyin',icon:'fa-brands fa-tiktok',color:'#000',url:'https://douyin.com'},
    {id:'xhs',name:'Xiaohongshu',icon:'fa-solid fa-book-open',color:'#ff2442',url:'https://xiaohongshu.com'},
    {id:'qq',name:'QQ',icon:'fa-brands fa-qq',color:'#1296db',url:'https://qq.com'},
  ],
  jp:[
    {id:'line',name:'LINE',icon:'fa-brands fa-line',color:'#06c755',url:'https://line.me'},
    {id:'x',name:'X',icon:'fa-brands fa-x-twitter',color:'#000',url:'https://twitter.com'},
    {id:'ig',name:'Instagram',icon:'fa-brands fa-instagram',color:'#e1306c',url:'https://instagram.com'},
    {id:'yt',name:'YouTube',icon:'fa-brands fa-youtube',color:'#ff0000',url:'https://youtube.com'},
  ],
  kr:[
    {id:'kakao',name:'KakaoTalk',icon:'fa-solid fa-comment',color:'#fee500',url:'https://kakao.com'},
    {id:'naver',name:'Naver',icon:'fa-solid fa-n',color:'#03c75a',url:'https://naver.com'},
    {id:'ig',name:'Instagram',icon:'fa-brands fa-instagram',color:'#e1306c',url:'https://instagram.com'},
    {id:'yt',name:'YouTube',icon:'fa-brands fa-youtube',color:'#ff0000',url:'https://youtube.com'},
  ],
  ru:[
    {id:'vk',name:'VK',icon:'fa-brands fa-vk',color:'#0077ff',url:'https://vk.com'},
    {id:'tg',name:'Telegram',icon:'fa-brands fa-telegram',color:'#2aabee',url:'https://telegram.org'},
    {id:'ok',name:'Odnoklassniki',icon:'fa-solid fa-users',color:'#ee8208',url:'https://ok.ru'},
    {id:'yt',name:'YouTube',icon:'fa-brands fa-youtube',color:'#ff0000',url:'https://youtube.com'},
  ],
  ir:[
    {id:'tg',name:'Telegram',icon:'fa-brands fa-telegram',color:'#2aabee',url:'https://telegram.org'},
    {id:'ig',name:'Instagram',icon:'fa-brands fa-instagram',color:'#e1306c',url:'https://instagram.com'},
    {id:'aparat',name:'Aparat',icon:'fa-solid fa-play',color:'#ed145b',url:'https://aparat.com'},
  ],
  in:[
    {id:'wa',name:'WhatsApp',icon:'fa-brands fa-whatsapp',color:'#25d366',url:'https://wa.me/919999999999'},
    {id:'ig',name:'Instagram',icon:'fa-brands fa-instagram',color:'#e1306c',url:'https://instagram.com'},
    {id:'x',name:'X',icon:'fa-brands fa-x-twitter',color:'#000',url:'https://twitter.com'},
    {id:'yt',name:'YouTube',icon:'fa-brands fa-youtube',color:'#ff0000',url:'https://youtube.com'},
    {id:'fb',name:'Facebook',icon:'fa-brands fa-facebook',color:'#1877f2',url:'https://facebook.com'},
  ],
};

// 12 products with multi-language names (seed demos — augmented with merchant DB products at runtime)
let PRODUCTS = [
  // Electronics
  {id:'p1',cat:'electronics',ar:'سماعات لاسلكية فاخرة',en:'Premium Wireless Headphones',descAr:'صوت نقي · إلغاء ضوضاء · 30 ساعة',descEn:'Pure sound · ANC · 30hr battery',sar:599,img:'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500'},
  {id:'p2',cat:'electronics',ar:'ساعة ذكية رياضية',en:'Smart Sports Watch',descAr:'GPS · مقاومة للماء · شاشة AMOLED',descEn:'GPS · Water resistant · AMOLED',sar:1290,img:'https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=500'},
  {id:'p11',cat:'electronics',ar:'جوال آيفون 16 برو',en:'iPhone 16 Pro',descAr:'ذاكرة 256GB · 3 كاميرات · A18 Bionic',descEn:'256GB · Triple cam · A18 Bionic',sar:5499,img:'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=500'},
  {id:'p12',cat:'electronics',ar:'لابتوب ماك بوك إير',en:'MacBook Air M3',descAr:'13.6 إنش · M3 · 16GB رام · 512GB',descEn:'13.6" · M3 · 16GB RAM · 512GB',sar:6890,img:'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=500'},
  {id:'p13',cat:'electronics',ar:'سماعة AirPods Pro',en:'AirPods Pro 2',descAr:'إلغاء ضوضاء نشط · شحن لاسلكي MagSafe',descEn:'Active ANC · MagSafe wireless charging',sar:990,img:'https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?w=500'},
  {id:'p33',cat:'electronics',ar:'تابلت iPad Air',en:'iPad Air M2',descAr:'M2 · شاشة Liquid Retina · 256GB',descEn:'M2 · Liquid Retina · 256GB',sar:3290,img:'https://images.unsplash.com/photo-1561154464-82e9adf32764?w=500'},
  {id:'p34',cat:'electronics',ar:'كاميرا DSLR احترافية',en:'Pro DSLR Camera',descAr:'24MP · فيديو 4K · عدسة kit',descEn:'24MP · 4K video · kit lens',sar:4200,img:'https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=500'},
  {id:'p35',cat:'electronics',ar:'مكبر صوت بلوتوث',en:'Bluetooth Speaker',descAr:'مقاوم للماء · 24 ساعة · صوت 360°',descEn:'Waterproof · 24hr battery · 360° sound',sar:380,img:'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=500'},
  {id:'p36',cat:'electronics',ar:'شاشة Gaming 4K',en:'4K Gaming Monitor',descAr:'27 إنش · 144Hz · HDR400',descEn:'27" · 144Hz · HDR400',sar:2890,img:'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500'},
  // Fashion
  {id:'p3',cat:'fashion',ar:'قميص قطني فاخر',en:'Premium Cotton Shirt',descAr:'قطن مصري 100% · جميع المقاسات',descEn:'100% Egyptian cotton · All sizes',sar:185,img:'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500'},
  {id:'p4',cat:'fashion',ar:'حذاء رياضي مودرن',en:'Modern Sneakers',descAr:'مقاس 36-46 · 3 ألوان متوفرة',descEn:'Size 36-46 · 3 colors available',sar:399,img:'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500'},
  {id:'p5',cat:'fashion',ar:'ساعة كلاسيكية',en:'Classic Watch',descAr:'حركة سويسرية · ضمان سنتين',descEn:'Swiss movement · 2-year warranty',sar:890,img:'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500'},
  {id:'p14',cat:'fashion',ar:'جاكيت جلد طبيعي',en:'Genuine Leather Jacket',descAr:'جلد بقر فاخر · بطانة دافئة · صناعة يدوية',descEn:'Premium cowhide · Warm lining · Handmade',sar:1290,img:'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500'},
  {id:'p15',cat:'fashion',ar:'بنطلون جينز',en:'Slim Fit Jeans',descAr:'قطن مرن · قص حديث · أزرق غامق',descEn:'Stretch denim · Slim fit · Dark blue',sar:275,img:'https://images.unsplash.com/photo-1542272604-787c3835535d?w=500'},
  {id:'p16',cat:'fashion',ar:'حقيبة جلد للسيدات',en:'Leather Tote Bag',descAr:'جلد طبيعي · 3 جيوب داخلية · أنيقة',descEn:'Real leather · 3 inner pockets · Elegant',sar:560,img:'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=500'},
  {id:'p37',cat:'fashion',ar:'فستان سهرة فاخر',en:'Evening Dress',descAr:'حرير طبيعي · تطريز يدوي · مقاسات S-XL',descEn:'Pure silk · Hand-embroidered · S-XL',sar:1450,img:'https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=500'},
  {id:'p38',cat:'fashion',ar:'نظارة شمسية فاخرة',en:'Luxury Sunglasses',descAr:'UV400 · إطار معدني · مع علبة جلدية',descEn:'UV400 · Metal frame · Leather case',sar:680,img:'https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=500'},
  {id:'p39',cat:'fashion',ar:'حزام جلد طبيعي',en:'Genuine Leather Belt',descAr:'جلد بقر · إبزيم مذهب · 3 مقاسات',descEn:'Cowhide · Gold buckle · 3 sizes',sar:295,img:'https://images.unsplash.com/photo-1624222247344-550fb60583dc?w=500'},
  {id:'p40',cat:'fashion',ar:'سلسلة ذهب 18 قيراط',en:'18k Gold Chain',descAr:'ذهب أصلي · شهادة ضمان · 18 قيراط',descEn:'Real gold · Certified · 18 karat',sar:2890,img:'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=500'},
  {id:'p41',cat:'home',ar:'مرتبة فاخرة Queen',en:'Queen Mattress Premium',descAr:'فوم بدرجات متعددة · ضمان 10 سنوات',descEn:'Multi-layer foam · 10-year warranty',sar:1890,img:'https://images.unsplash.com/photo-1631679706909-1844bbd07221?w=500'},
  // Beauty
  {id:'p6',cat:'beauty',ar:'سيروم فيتامين C',en:'Vitamin C Serum',descAr:'يضيء البشرة · 30مل · بدون مواد ضارة',descEn:'Brightens skin · 30ml · Clean formula',sar:245,img:'https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500'},
  {id:'p7',cat:'beauty',ar:'عطر شرقي فاخر',en:'Luxury Oriental Perfume',descAr:'عود · مسك · ثبات 12 ساعة',descEn:'Oud · Musk · 12hr longevity',sar:1450,img:'https://images.unsplash.com/photo-1541643600914-78b084683601?w=500'},
  {id:'p17',cat:'beauty',ar:'كريم مرطب يومي',en:'Daily Moisturizer',descAr:'هياليورونيك أسيد · يومي · لكل أنواع البشرة',descEn:'Hyaluronic acid · For all skin types',sar:180,img:'https://images.unsplash.com/photo-1570554886111-e80fcca6a029?w=500'},
  {id:'p18',cat:'beauty',ar:'باليت ميك آب احترافية',en:'Pro Makeup Palette',descAr:'24 لون · ثبات طويل · يلائم كل المناسبات',descEn:'24 shades · Long lasting · All occasions',sar:320,img:'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=500'},
  {id:'p19',cat:'beauty',ar:'مكواة شعر سيراميك',en:'Ceramic Hair Straightener',descAr:'حماية للشعر · يصلح للمزدوج · 230°',descEn:'Hair protection · Dual voltage · 230°',sar:450,img:'https://images.unsplash.com/photo-1522338242992-e1a54906a8da?w=500'},
  {id:'p23',cat:'beauty',ar:'أحمر شفاه مات',en:'Matte Lipstick Set',descAr:'12 لون · صيغة ماتية · ثبات 8 ساعات',descEn:'12 shades · Matte formula · 8hr lasting',sar:165,img:'https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=500'},
  {id:'p24',cat:'beauty',ar:'فرش ميك آب احترافية',en:'Pro Makeup Brushes',descAr:'10 فرش · شعر صناعي · حقيبة جلدية',descEn:'10 brushes · Synthetic · Leather case',sar:285,img:'https://images.unsplash.com/photo-1631214540242-0712e842de4d?w=500'},
  {id:'p25',cat:'beauty',ar:'مساج وجه كهربائي',en:'Electric Face Massager',descAr:'يدلك ويرطب · 5 سرعات · شحن USB',descEn:'Massage + moisturize · 5 speeds · USB',sar:380,img:'https://images.unsplash.com/photo-1631730486572-226d1f595b68?w=500'},
  {id:'p26',cat:'beauty',ar:'بخاخ شعر طبيعي',en:'Natural Hair Mist',descAr:'زيت أرغان · مغذي · 100مل',descEn:'Argan oil · Nourishing · 100ml',sar:135,img:'https://images.unsplash.com/photo-1526045478516-99145907023c?w=500'},
  {id:'p27',cat:'beauty',ar:'كريم العين',en:'Eye Contour Cream',descAr:'يخفف الهالات · فيتامين K · 15مل',descEn:'Reduces dark circles · Vitamin K · 15ml',sar:210,img:'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=500'},
  // Home
  {id:'p8',cat:'home',ar:'مكنسة لاسلكية',en:'Cordless Vacuum',descAr:'شفط قوي · بطارية 60 دقيقة',descEn:'Powerful suction · 60min battery',sar:1890,img:'https://images.unsplash.com/photo-1558317374-067fb5f30001?w=500'},
  {id:'p20',cat:'home',ar:'مصباح ليد ذكي',en:'Smart LED Lamp',descAr:'16 مليون لون · يعمل بالصوت · Alexa & Google',descEn:'16M colors · Voice controlled · Alexa & Google',sar:240,img:'https://images.unsplash.com/photo-1565814329452-e1efa11c5b89?w=500'},
  {id:'p21',cat:'home',ar:'مكينة قهوة إيطالية',en:'Italian Espresso Machine',descAr:'ضغط 15 بار · رغوة حليب · إيطالية الصنع',descEn:'15-bar pressure · Milk frother · Made in Italy',sar:2450,img:'https://images.unsplash.com/photo-1610632380989-680fe40816c6?w=500'},
  {id:'p22',cat:'home',ar:'وسادة طبية',en:'Memory Foam Pillow',descAr:'فوم طبي · يدعم الرقبة · غطاء قابل للغسيل',descEn:'Memory foam · Neck support · Washable cover',sar:165,img:'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=500'},
  {id:'p28',cat:'home',ar:'بطانية حرارية',en:'Heated Throw Blanket',descAr:'3 درجات حرارة · مقاسات كبيرة · قابلة للغسيل',descEn:'3 heat levels · King size · Machine washable',sar:295,img:'https://images.unsplash.com/photo-1631679706909-1844bbd07221?w=500'},
  {id:'p29',cat:'home',ar:'أرفف كتب خشبية',en:'Wooden Bookshelf',descAr:'5 أرفف · خشب صلب · يحمل 50 كجم',descEn:'5 shelves · Solid wood · 50kg capacity',sar:680,img:'https://images.unsplash.com/photo-1594620302200-9a762244a156?w=500'},
  {id:'p30',cat:'home',ar:'سلطانية فخار',en:'Ceramic Bowl Set',descAr:'6 قطع · صناعة يدوية · سيراميك ياباني',descEn:'6-piece · Handmade · Japanese ceramic',sar:215,img:'https://images.unsplash.com/photo-1610701596007-11502861dcfa?w=500'},
  {id:'p31',cat:'home',ar:'منشفة قطن مصرية',en:'Egyptian Cotton Towels',descAr:'4 قطع · قطن مصري 100% · امتصاص فائق',descEn:'4-piece · 100% Egyptian cotton · Super absorbent',sar:185,img:'https://images.unsplash.com/photo-1571902943202-507ec2618e8f?w=500'},
  {id:'p32',cat:'home',ar:'بخار كهربائي للملابس',en:'Electric Clothes Steamer',descAr:'1500 واط · خزان 240مل · جاهز في 30 ثانية',descEn:'1500W · 240ml tank · Ready in 30s',sar:295,img:'https://images.unsplash.com/photo-1521903062400-b80f2cb8cb9d?w=500'},
  // Sports & Fitness
  {id:'p50',cat:'sports',ar:'دراجة هوائية جبلية',en:'Mountain Bike',descAr:'21 سرعة · إطار ألومنيوم · قابل للطي',descEn:'21 speeds · Aluminum frame · Foldable',sar:1890,img:'https://images.unsplash.com/photo-1485965120184-e220f721d03e?w=500'},
  {id:'p51',cat:'sports',ar:'مجموعة دامبلز قابلة للتعديل',en:'Adjustable Dumbbell Set',descAr:'2.5-25 كجم · سهل التعديل · مع ستاند',descEn:'2.5-25 kg · Quick adjust · With stand',sar:1450,img:'https://images.unsplash.com/photo-1638536532686-d610adfc8e5c?w=500'},
  {id:'p52',cat:'sports',ar:'سجادة يوغا فاخرة',en:'Premium Yoga Mat',descAr:'6 مم · مضادة للانزلاق · صديقة للبيئة',descEn:'6mm · Non-slip · Eco-friendly',sar:165,img:'https://images.unsplash.com/photo-1592432678016-e910b452f9a2?w=500'},
  {id:'p53',cat:'sports',ar:'حذاء جري احترافي',en:'Pro Running Shoes',descAr:'تقنية ضد الصدمات · خفيف · مقاسات 38-46',descEn:'Shock absorbing · Lightweight · 38-46',sar:680,img:'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500'},
  {id:'p54',cat:'sports',ar:'ساعة جري GPS',en:'GPS Running Watch',descAr:'بطارية 14 يوم · GPS متقدم · مراقبة القلب',descEn:'14-day battery · Advanced GPS · HR monitor',sar:1290,img:'https://images.unsplash.com/photo-1576243345690-4e4b79b63288?w=500'},
  // Food & Grocery
  {id:'p60',cat:'food',ar:'قهوة عربية مختصة',en:'Specialty Arabic Coffee',descAr:'محمصة طازجة · 250 جرام · حبوب مختارة',descEn:'Freshly roasted · 250g · Select beans',sar:75,img:'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=500'},
  {id:'p61',cat:'food',ar:'عسل سدر طبيعي',en:'Natural Sidr Honey',descAr:'1 كجم · يمني أصلي · غير مبستر',descEn:'1kg · Authentic Yemeni · Raw',sar:485,img:'https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=500'},
  {id:'p62',cat:'food',ar:'تمر مجدول فاخر',en:'Premium Medjool Dates',descAr:'1 كجم · فاخر · من نخيل المدينة',descEn:'1kg · Premium · From Madinah',sar:165,img:'https://images.unsplash.com/photo-1581375074612-d1fd0e661aeb?w=500'},
  {id:'p63',cat:'food',ar:'زعفران إيراني فاخر',en:'Premium Iranian Saffron',descAr:'1 جرام · صنف نقي · علبة فاخرة',descEn:'1g · Pure grade · Luxury box',sar:120,img:'https://images.unsplash.com/photo-1599909533930-f2a1aab7e1e7?w=500'},
  {id:'p64',cat:'food',ar:'زيت زيتون بكر ممتاز',en:'Extra Virgin Olive Oil',descAr:'500 مل · سوري أصلي · معصور بارد',descEn:'500ml · Syrian · Cold-pressed',sar:95,img:'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=500'},
  // Kids & Toys
  {id:'p70',cat:'kids',ar:'دراجة أطفال 3 عجلات',en:'Kids 3-Wheel Bike',descAr:'للأعمار 3-7 سنوات · مقعد قابل للتعديل · آمنة',descEn:'Age 3-7 · Adjustable seat · Safe',sar:295,img:'https://images.unsplash.com/photo-1597740049577-d8f4c947be15?w=500'},
  {id:'p71',cat:'kids',ar:'مجموعة ليجو 1500 قطعة',en:'LEGO Set 1500 pcs',descAr:'إبداعية · للأعمار 6+ · صندوق منظم',descEn:'Creative · Age 6+ · Storage box',sar:485,img:'https://images.unsplash.com/photo-1558877385-8c1b8c4b4d28?w=500'},
  {id:'p72',cat:'kids',ar:'سيارة ريموت سباق',en:'RC Racing Car',descAr:'سرعة 40 كم/س · بطارية 60 دقيقة · 4WD',descEn:'40 km/h · 60min battery · 4WD',sar:450,img:'https://images.unsplash.com/photo-1558060370-d644479cb6f7?w=500'},
  {id:'p73',cat:'kids',ar:'دمية باربي سيت كامل',en:'Barbie Complete Set',descAr:'دمية + 5 ملابس + اكسسوارات · هدية رائعة',descEn:'Doll + 5 outfits + accessories · Great gift',sar:215,img:'https://images.unsplash.com/photo-1558877385-8c1b8c4b4d28?w=500'},
  // ═══ SMART AI SERVICES (Pay with Zenrex Credits) ═══
  {id:'ai1',cat:'ai_services',ar:'تحليل صورة منتج بالذكاء الاصطناعي',en:'AI Product Image Analysis',descAr:'حلل صورة وأنشئ وصف احترافي · 30 نقطة',descEn:'Analyze image + pro description · 30 credits',sar:30,img:'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=500',isAI:true,credits:30,svc:'image_analyze'},
  {id:'ai2',cat:'ai_services',ar:'توليد صور إعلانية احترافية',en:'Pro Ad Image Generator',descAr:'صورة إعلانية بجودة عالية · نموذج Nano Banana · 50 نقطة',descEn:'High-quality ad image · 50 credits',sar:50,img:'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=500',isAI:true,credits:50,svc:'image_gen'},
  {id:'ai3',cat:'ai_services',ar:'توليد فيديو إعلاني (Sora 2)',en:'AI Promo Video (Sora 2)',descAr:'فيديو إعلاني 10 ثواني بجودة سينمائية · 200 نقطة',descEn:'10-sec cinematic promo video · 200 credits',sar:200,img:'https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?w=500',isAI:true,credits:200,svc:'video_gen'},
  {id:'ai4',cat:'ai_services',ar:'كتابة حملة إعلانية كاملة',en:'Full Ad Campaign Writer',descAr:'محتوى إعلاني لمنصات متعددة · GPT-5.2 · 40 نقطة',descEn:'Multi-platform ad copy · GPT-5.2 · 40 credits',sar:40,img:'https://images.unsplash.com/photo-1432888622747-4eb9a8efeb07?w=500',isAI:true,credits:40,svc:'ad_writer'},
  {id:'ai5',cat:'ai_services',ar:'تحليل سوق ومنافسين',en:'Market & Competitor Analysis',descAr:'تقرير تحليلي شامل · بحث ويب · 80 نقطة',descEn:'Comprehensive report · Web research · 80 credits',sar:80,img:'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=500',isAI:true,credits:80,svc:'market_analysis'},
  {id:'ai6',cat:'ai_services',ar:'مساعد عملاء ذكي 24/7',en:'24/7 AI Customer Assistant',descAr:'شات بوت ذكي للرد على عملائك · شهر · 500 نقطة',descEn:'Smart chatbot for customers · Monthly · 500 credits',sar:500,img:'https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=500',isAI:true,credits:500,svc:'ai_chatbot'},
  {id:'ai7',cat:'ai_services',ar:'تصميم شعار احترافي',en:'Pro Logo Designer',descAr:'5 نماذج شعار بأسلوبك · ملفات SVG · 60 نقطة',descEn:'5 logo variations · SVG files · 60 credits',sar:60,img:'https://images.unsplash.com/photo-1626785774573-4b799315345d?w=500',isAI:true,credits:60,svc:'logo_design'},
  {id:'ai8',cat:'ai_services',ar:'ترجمة احترافية متعددة اللغات',en:'Pro Multi-language Translation',descAr:'ترجمة فاخرة لـ 12 لغة · 1000 كلمة · 25 نقطة',descEn:'Premium translation 12 languages · 25 credits',sar:25,img:'https://images.unsplash.com/photo-1546410531-bb4caa6b424d?w=500',isAI:true,credits:25,svc:'translation'},
];
const CATS=[
  {id:'all',ar:'الكل',en:'All',ico:'📦'},
  {id:'ai_services',ar:'🤖 خدمات AI',en:'🤖 AI Services',ico:'🤖'},
  {id:'electronics',ar:'إلكترونيات',en:'Electronics',ico:'📱'},
  {id:'fashion',ar:'أزياء',en:'Fashion',ico:'👗'},
  {id:'beauty',ar:'تجميل ومكياج',en:'Beauty & Makeup',ico:'💄'},
  {id:'home',ar:'منزل',en:'Home',ico:'🏠'},
  {id:'sports',ar:'رياضة',en:'Sports',ico:'⚽'},
  {id:'food',ar:'مأكولات',en:'Food',ico:'🍯'},
  {id:'kids',ar:'أطفال',en:'Kids',ico:'🧸'},
];
const REVIEWS=[
  {ar:'تجربة شراء ممتازة! المنتجات أصلية والتوصيل سريع جداً',en:'Amazing shopping experience! Authentic products and very fast delivery',name:'أحمد · Ahmed',stars:5},
  {ar:'خدمة العملاء راقية ومتميزة، أنصح بشدة بهذا المتجر',en:'Excellent customer service, highly recommended store',name:'سارة · Sarah',stars:5},
  {ar:'أسعار منافسة جداً وجودة عالية، تعاملي الثالث',en:'Very competitive prices and high quality, my third time',name:'محمد · Mohammed',stars:5},
];
const TRANS={
  ar:{lang_btn:'عربي',home:'الرئيسية',products:'المنتجات',contact:'تواصل معنا',book_now:'احجز موعد',cart:'السلة',search:'بحث',orders:'طلباتي',account:'حسابي',featured:'⭐ المنتجات المميّزة',see_all:'الكل ←',reviews_title:'آراء عملائنا',reviews_sub:'قالوا عنا...',cart_title:'🛒 السلة',subtotal:'المجموع',tax:'الضريبة',total:'الإجمالي',checkout:'إتمام الطلب',checkout_title:'💳 إتمام الطلب',checkout_sub:'اختر طريقة الدفع',select_payment:'اختر طريقة الدفع',order_success:'تم تأكيد طلبك!',order_success_sub:'سيتم التواصل معك قريباً',close:'إغلاق',reserve_title:'📅 احجز موعدك',reserve_sub:'سنتواصل معك للتأكيد',confirm_book:'تأكيد الحجز',name:'الاسم الكامل',phone:'رقم الجوال',address:'العنوان',notes:'ملاحظات',rights:'جميع الحقوق محفوظة',made_by:'صُنع بواسطة',quick_links:'روابط سريعة',payments:'طرق الدفع',shipping:'الشحن',cart_empty:'سلتك فارغة',cart_empty_sub:'أضف منتجات لتبدأ التسوق',search_ph:'ابحث عن منتج...',brand:'Zenrex',back:'رجوع',shop_now:'تسوّق الآن',my_orders:'📋 طلباتي',my_account:'👤 حسابي',hello:'مرحباً',guest:'زائر عزيز',acc_name:'الاسم',acc_phone:'رقم الجوال',acc_addr:'العنوان',acc_addr_ph:'مدينتك وحيك',acc_name_ph:'اكتب اسمك',save_data:'💾 حفظ البيانات',orders_count:'عدد الطلبات',loyalty_points:'نقاط الولاء',products_label:'المنتجات',follow_us:'تابعنا',exclusive_offers:'عروض حصرية',cart_empty_alert:'السلة فارغة',choose_payment_alert:'اختر طريقة الدفع',fill_name_alert:'املأ الاسم',saved_ok:'✓ تم حفظ بياناتك',booking_ok:'تم استلام حجزك! سنتواصل معك للتأكيد.',products_in:'منتج',items_label:'منتج',status_confirmed:'مؤكد',no_orders:'لا توجد طلبات بعد',no_orders_sub:'ابدأ التسوق وستظهر طلباتك هنا',pick_branch:'🏪 اختر فرع التسليم',pick_shipping:'🚚 طريقة الشحن',map_loading:'جاري تحميل الخريطة...',locate_me:'📍 حدد موقعي تلقائياً',nearest:'الأقرب',km_away:'كم',stock_warn_title:'⚠️ تنبيه: منتجات غير متوفرة بالفرع الأقرب',stock_warn_msg:'بعض المنتجات غير متوفرة في الفرع الأقرب. اختر:',ship_from_other:'🚛 شحن من فرع آخر',ship_from_other_sub:'رسوم توصيل إضافية',remove_item:'🗑️ احذف من السلة',shipping_fee:'رسوم الشحن',pickup_free:'مجاناً',choose_branch_alert:'اختر فرع التسليم أولاً',add_custom_social:'+ إضافة موقع تواصل مخصص',custom_social_title:'إضافة موقع تواصل اجتماعي',custom_social_name:'اسم الموقع (مثلاً: Threads)',custom_social_url:'الرابط المباشر',custom_social_upload:'📷 ارفع صورة/شعار الموقع',custom_social_save:'حفظ ونشر',admin_custom:'إدارة المواقع المخصصة',admin:'لوحة التحكم'},
  en:{lang_btn:'English',home:'Home',products:'Products',contact:'Contact',book_now:'Book Now',cart:'Cart',search:'Search',orders:'Orders',account:'Account',featured:'⭐ Featured Products',see_all:'See all →',reviews_title:'Customer Reviews',reviews_sub:'What they said about us...',cart_title:'🛒 Cart',subtotal:'Subtotal',tax:'Tax',total:'Total',checkout:'Checkout',checkout_title:'💳 Checkout',checkout_sub:'Choose payment method',select_payment:'Select payment method',order_success:'Order Confirmed!',order_success_sub:'We will contact you shortly',close:'Close',reserve_title:'📅 Book Appointment',reserve_sub:'We will confirm with you',confirm_book:'Confirm Booking',name:'Full Name',phone:'Phone Number',address:'Address',notes:'Notes (optional)',rights:'All rights reserved',made_by:'Made by',quick_links:'Quick Links',payments:'Payments',shipping:'Shipping',cart_empty:'Your cart is empty',cart_empty_sub:'Add products to start shopping',search_ph:'Search for products...',brand:'Zenrex',back:'Back',shop_now:'Shop Now',my_orders:'📋 My Orders',my_account:'👤 My Account',hello:'Hello',guest:'Dear guest',acc_name:'Name',acc_phone:'Phone',acc_addr:'Address',acc_addr_ph:'Your city & district',acc_name_ph:'Type your name',save_data:'💾 Save Info',orders_count:'Orders count',loyalty_points:'Loyalty points',products_label:'Products',follow_us:'Follow Us',exclusive_offers:'EXCLUSIVE OFFERS',cart_empty_alert:'Cart is empty',choose_payment_alert:'Choose a payment method',fill_name_alert:'Please fill in your name',saved_ok:'✓ Account saved',booking_ok:'Booking received! We will contact you to confirm.',products_in:'items',items_label:'items',status_confirmed:'Confirmed',no_orders:'No orders yet',no_orders_sub:'Start shopping and your orders will appear here',pick_branch:'🏪 Choose delivery branch',pick_shipping:'🚚 Shipping method',map_loading:'Loading map...',locate_me:'📍 Auto-detect my location',nearest:'NEAREST',km_away:'km',stock_warn_title:'⚠️ Heads up: items missing from nearest branch',stock_warn_msg:'Some items are out-of-stock in the closest branch. Choose:',ship_from_other:'🚛 Ship from another branch',ship_from_other_sub:'Extra delivery fee applies',remove_item:'🗑️ Remove from cart',shipping_fee:'Shipping fee',pickup_free:'FREE',choose_branch_alert:'Please choose a delivery branch first',add_custom_social:'+ Add custom social',custom_social_title:'Add custom social network',custom_social_name:'Network name (e.g. Threads)',custom_social_url:'Direct link',custom_social_upload:'📷 Upload logo/icon image',custom_social_save:'Save & publish',admin_custom:'Manage custom socials',admin:'Admin'}
};
// Currency symbol per language (so SAR displays as "SAR" in English instead of "ر.س")
const CURRENCY_SYMBOLS_EN={SAR:'SAR',AED:'AED',KWD:'KWD',QAR:'QAR',BHD:'BHD',OMR:'OMR',IQD:'IQD',SYP:'SYP',JOD:'JOD',LBP:'LBP',EGP:'EGP',IRR:'IRR',YER:'YER',ILS:'ILS',CNY:'¥',JPY:'¥',KRW:'₩',INR:'₹',USD:'$',GBP:'£',EUR:'€',CHF:'CHF',SEK:'kr',RUB:'₽',TRY:'₺',MAD:'MAD',DZD:'DZD',TND:'TND',LYD:'LYD',SDG:'SDG',PKR:'₨',BDT:'৳',IDR:'Rp',MYR:'RM',THB:'฿',PHP:'₱',VND:'₫',CAD:'CA$',MXN:'MX$',BRL:'R$',ARS:'AR$',ZAR:'R',NGN:'₦',KES:'KSh',AUD:'A$'};
function curSym(){return CURRENT_LANG==='en'?(CURRENCY_SYMBOLS_EN[CURRENT_MARKET.currency]||CURRENT_MARKET.currency):CURRENT_MARKET.symbol;}
function tx(k){return (TRANS[CURRENT_LANG]||TRANS.en)[k]||k;}
const BANNERS={
  ar:[{title:'عروض اليوم 🔥',sub:'خصم 30% على كل المنتجات',tag:'حصري'},{title:'شحن مجاني 🚚',sub:'لكل الطلبات فوق 200 ر.س',tag:'جديد'},{title:'وصلت الأحدث ✨',sub:'تشكيلة 2026 الآن متوفرة',tag:'حصري'}],
  en:[{title:'Today\'s Deals 🔥',sub:'30% off all products',tag:'EXCLUSIVE'},{title:'Free Shipping 🚚',sub:'On orders over 200 SAR',tag:'NEW'},{title:'New Arrivals ✨',sub:'2026 Collection available now',tag:'EXCLUSIVE'}]
};

let CURRENT_LANG='ar';
let CURRENT_MARKET=null;
let CART=JSON.parse(localStorage.getItem('zx_cart')||'[]');
let PAYMENT_CHOSEN=null;
let SELECTED_BRANCH=null;
let SELECTED_SHIPPING='standard';
let USER_LOCATION=null; // {lat,lng}
let CHECKOUT_MAP=null;
let CUSTOM_SOCIALS=JSON.parse(localStorage.getItem('zx_custom_socials')||'[]');

// ═══════════════════════ INIT ═══════════════════════
async function init(){
  // detect market
  let mid='sa';
  try{const r=await fetch(API+'/api/ready-sites/detect-market');const d=await r.json();mid=d.market_id||'sa';}catch(_){}
  await loadMarket(mid);
  buildMarketList();
  applyAllOverrides();
  ensureDefaultGalleries();
  renderUI();
  renderProducts();
  renderCategories();
  startBannerSlider();
  startReviewSlider();
  updateCart();
  updateWishBadge();
  updateAuthUi();
  loadMerchantProducts();
  applyAdminModeOnInit();
  document.body.addEventListener('click',()=>{document.getElementById('market-popover').classList.remove('open')});
}

async function loadMarket(mid){
  const r=await fetch(API+'/api/ready-sites/market/'+mid);
  CURRENT_MARKET=await r.json();
  // default lang = market language (or 'en' if not supported)
  CURRENT_LANG=CURRENT_MARKET.supported_languages?.includes(CURRENT_LANG)?CURRENT_LANG:CURRENT_MARKET.language;
  if(!['ar','en'].includes(CURRENT_LANG))CURRENT_LANG='en'; // fallback for now since we only have ar/en translations
  applyLocale();
}

function applyLocale(){
  document.documentElement.style.setProperty('--font',`'${CURRENT_MARKET.font}',sans-serif`);
  document.documentElement.style.setProperty('--dir',CURRENT_MARKET.direction);
  document.documentElement.dir=CURRENT_LANG==='ar'?'rtl':(CURRENT_MARKET.direction);
  document.documentElement.lang=CURRENT_LANG;
  const mlbl=document.getElementById('market-label');
  if(mlbl)mlbl.textContent=(CURRENT_LANG==='en'?(CURRENT_MARKET.name_en||CURRENT_MARKET.name_ar):(CURRENT_MARKET.name_ar||CURRENT_MARKET.name_en));
  // Update ALL lang-flag / lang-label elements (popover + account page both have them)
  document.querySelectorAll('#lang-flag,[data-id="lang-flag"]').forEach(el=>{el.textContent=CURRENT_LANG==='ar'?'🇸🇦':'🇬🇧';});
  document.querySelectorAll('#lang-label,[data-id="lang-label"]').forEach(el=>{el.textContent=CURRENT_LANG==='ar'?'العربية':'English';});
  const s=document.getElementById('search');
  if(s)s.placeholder=TRANS[CURRENT_LANG]?.search_ph||TRANS.en.search_ph;
  const mn=document.getElementById('acc-market-name');
  if(mn&&CURRENT_MARKET)mn.textContent=CURRENT_LANG==='ar'?CURRENT_MARKET.name_ar:CURRENT_MARKET.name_en;
}

// ═══════════════════════ LANGUAGE TOGGLE ═══════════════════════
function toggleLang(){
  CURRENT_LANG=CURRENT_LANG==='ar'?'en':'ar';
  applyLocale();
  renderUI();
  renderProducts();
  renderCategories();
  renderBanner();
  renderReviews();
  updateCart();
  // Re-render currently active view (category/orders/account) so dynamic text updates
  if(document.getElementById('view-category').style.display==='block' && activeCat && activeCat!=='all'){renderCategoryPage(activeCat);}
  if(document.getElementById('view-orders').style.display==='block'){renderOrders();}
  if(document.getElementById('view-account').style.display==='block'){renderAccount();}
}

function renderUI(){
  const t=TRANS[CURRENT_LANG]||TRANS.en;
  document.querySelectorAll('[data-key]').forEach(el=>{
    const k=el.getAttribute('data-key');
    if(t[k])el.textContent=t[k];
  });
  document.querySelectorAll('[data-key-ph]').forEach(el=>{
    const k=el.getAttribute('data-key-ph');
    if(t[k])el.placeholder=t[k];
  });
  // contact info update
  const b=CURRENT_MARKET;
  document.getElementById('phone-link').innerHTML='📞 +966 500 000 000';
  document.getElementById('whatsapp-link').innerHTML='💬 '+(b.chat_apps?.[0]?.name||'WhatsApp');
  // payments & shipping in footer
  const pf=document.getElementById('payments-footer');
  pf.innerHTML='<h4 data-key="payments">'+t.payments+'</h4>'+(b.payment_gateways||[]).slice(0,5).map(g=>`<a>${g.name}</a>`).join('');
  const sf=document.getElementById('shipping-footer');
  sf.innerHTML='<h4 data-key="shipping">'+t.shipping+'</h4>'+(b.shipping_carriers||[]).slice(0,4).map(s=>`<a>${s.name}</a>`).join('');
  // Render socials based on market
  renderSocialIcons();
}

// ═══════════════════════ SOCIAL ICONS (market-aware + custom) ═══════════════════════
function renderSocialIcons(){
  const mid=CURRENT_MARKET?.id||'sa';
  const preset=SOCIAL_PRESETS[mid]||SOCIAL_PRESETS.default;
  const host=document.getElementById('social-icons');
  if(!host)return;
  const builtin=preset.map(s=>`<a href="${s.url}" target="_blank" aria-label="${s.name}" title="${s.name}" style="background:#1e293b" onmouseover="this.style.background='${s.color}';this.style.color='#fff'" onmouseout="this.style.background='#1e293b';this.style.color='#cbd5e1'"><i class="${s.icon}"></i></a>`).join('');
  const custom=CUSTOM_SOCIALS.map(s=>`<a class="custom" href="${s.url}" target="_blank" aria-label="${s.name}" title="${s.name}"><img src="${s.image}" alt="${s.name}" loading="lazy" decoding="async"></a>`).join('');
  host.innerHTML=builtin+custom;
}

// ═══════════════════════ CUSTOM SOCIAL ADMIN ═══════════════════════
let _pendingSocialImage=null;
function openSocialModal(){
  document.getElementById('social-modal').classList.add('open');
  document.getElementById('cs-name').value='';
  document.getElementById('cs-url').value='';
  document.getElementById('cs-upload-zone').classList.remove('has-preview');
  document.getElementById('cs-upload-zone').innerHTML='<div style="font-size:32px;margin-bottom:6px">📷</div><b style="font-size:13px;color:#0a0a0a" data-key="custom_social_upload">'+tx('custom_social_upload')+'</b><p style="font-size:11px;color:#6b7280;margin-top:4px">PNG · JPG · SVG (max 512KB)</p>';
  _pendingSocialImage=null;
  renderCustomSocialList();
}
function closeSocialModal(){document.getElementById('social-modal').classList.remove('open');}
function onCustomSocialImage(e){
  const file=e.target.files?.[0];if(!file)return;
  if(file.size>512*1024){alert(CURRENT_LANG==='ar'?'الصورة كبيرة جداً (الحد الأقصى ٥١٢ كيلوبايت)':'Image too large (max 512KB)');return;}
  const reader=new FileReader();
  reader.onload=ev=>{
    _pendingSocialImage=ev.target.result;
    const zone=document.getElementById('cs-upload-zone');
    zone.classList.add('has-preview');
    zone.innerHTML=`<img src="${_pendingSocialImage}" alt="preview" loading="lazy" decoding="async"><p style="font-size:11px;color:#22c55e;margin-top:6px;font-weight:900">✓ ${CURRENT_LANG==='ar'?'تم رفع الصورة':'Image uploaded'}</p>`;
  };
  reader.readAsDataURL(file);
}
function saveCustomSocial(){
  const name=document.getElementById('cs-name').value.trim();
  const url=document.getElementById('cs-url').value.trim();
  if(!name||!url){alert(CURRENT_LANG==='ar'?'املأ اسم الموقع والرابط':'Fill name and URL');return;}
  if(!_pendingSocialImage){alert(CURRENT_LANG==='ar'?'ارفع صورة/شعار للموقع':'Upload an icon/logo');return;}
  CUSTOM_SOCIALS.push({id:'c'+Date.now(),name,url:url.startsWith('http')?url:'https://'+url,image:_pendingSocialImage});
  localStorage.setItem('zx_custom_socials',JSON.stringify(CUSTOM_SOCIALS));
  _pendingSocialImage=null;
  document.getElementById('cs-name').value='';
  document.getElementById('cs-url').value='';
  document.getElementById('cs-upload-zone').classList.remove('has-preview');
  document.getElementById('cs-upload-zone').innerHTML='<div style="font-size:32px;margin-bottom:6px">📷</div><b style="font-size:13px;color:#0a0a0a">'+tx('custom_social_upload')+'</b><p style="font-size:11px;color:#6b7280;margin-top:4px">PNG · JPG · SVG (max 512KB)</p>';
  renderCustomSocialList();
  renderSocialIcons();
}
function deleteCustomSocial(id){
  CUSTOM_SOCIALS=CUSTOM_SOCIALS.filter(s=>s.id!==id);
  localStorage.setItem('zx_custom_socials',JSON.stringify(CUSTOM_SOCIALS));
  renderCustomSocialList();
  renderSocialIcons();
}
function renderCustomSocialList(){
  const host=document.getElementById('cs-list');
  if(!host)return;
  if(!CUSTOM_SOCIALS.length){host.innerHTML='<p style="font-size:11px;color:#9ca3af;text-align:center;padding:10px">'+(CURRENT_LANG==='ar'?'لا توجد مواقع مخصصة بعد':'No custom socials yet')+'</p>';return;}
  host.innerHTML=CUSTOM_SOCIALS.map(s=>`<div class="custom-social-row"><img src="${s.image}" alt="${s.name}" loading="lazy" decoding="async"><div class="info"><b>${s.name}</b><small>${s.url}</small></div><button class="del" onclick="deleteCustomSocial('${s.id}')">✕</button></div>`).join('');
}

// ═══════════════════════ MARKET ═══════════════════════
async function buildMarketList(){
  const r=await fetch(API+'/api/ready-sites/markets');
  const d=await r.json();
  const list=document.getElementById('market-list');
  list.innerHTML=d.markets.map(m=>`<div class="market-item ${m.id===CURRENT_MARKET.id?'active':''}" onclick="switchMarket('${m.id}')"><span class="flag">${m.flag}</span><span>${m.name_ar}</span><small>${m.currency}</small></div>`).join('');
}
function toggleMarketPopover(e){
  e.stopPropagation();
  document.getElementById('market-popover').classList.toggle('open');
}
async function switchMarket(id){
  await loadMarket(id);
  document.getElementById('market-popover').classList.remove('open');
  buildMarketList();
  renderUI();
  renderProducts();
  renderCategories();
  renderBanner();
  renderReviews();
  updateCart();
  if(document.getElementById('view-category').style.display==='block' && activeCat && activeCat!=='all'){renderCategoryPage(activeCat);}
  if(document.getElementById('view-orders').style.display==='block'){renderOrders();}
  if(document.getElementById('view-account').style.display==='block'){renderAccount();}
}

// ═══════════════════════ RENDER ═══════════════════════
function formatPrice(sar){
  const rate=RATES[CURRENT_MARKET.currency]||1;
  const v=sar*rate;
  const noDecimal=['IQD','SYP','LBP','IRR','KRW','JPY','VND','IDR','UZS'];
  return noDecimal.includes(CURRENT_MARKET.currency)?Math.round(v).toLocaleString():v.toFixed(2);
}

let activeCat='all';
function renderProducts(){
  const filtered = activeCat==='all'?PRODUCTS:PRODUCTS.filter(p=>p.cat===activeCat);
  const t=TRANS[CURRENT_LANG]||TRANS.en;
  const grid=document.getElementById('products');
  if(!filtered.length){
    grid.innerHTML=`<div style="grid-column:1/-1;text-align:center;padding:40px 20px;color:#9ca3af"><div style="font-size:48px;margin-bottom:10px">📭</div><b>${CURRENT_LANG==='ar'?'لا توجد منتجات في هذا القسم':'No products in this category'}</b></div>`;
    return;
  }
  grid.innerHTML=filtered.map(pCardHtml).join('');
}

function renderCategories(){
  document.getElementById('cats').innerHTML=CATS.map(c=>{
    const overrideKey='cat_icon:'+c.id;
    const overrideObj=IMG_OVERRIDES[overrideKey];
    const overrideUrl=overrideObj?(typeof overrideObj==='string'?overrideObj:overrideObj.url):null;
    const fallbackImg=CAT_IMAGES[c.id]||CAT_IMAGES.fashion;
    const bgUrl=overrideUrl||fallbackImg;
    return `<div class="q-cat editable-img-host ${c.id===activeCat?'active-cat':''}" onclick="filterCat('${c.id}')">
      <div class="q-cat-bg" style="background-image:url('${bgUrl}')"></div>
      <button class="img-edit-btn" onclick="event.stopPropagation();openStudio('cat_icon:${c.id}')" title="تحرير">✨</button>
      <span>${CURRENT_LANG==='ar'?c.ar:c.en}</span>
    </div>`;
  }).join('');
}
function filterCat(id){activeCat=id;if(id==='all'){showView('home');renderCategories();renderProducts();window.scrollTo({top:document.getElementById('products').offsetTop-100,behavior:'smooth'});}else{showView('category',id);}}

// ═══════════════════════ VIEW ROUTER (Home / Category / Search / Orders / Account) ═══════════════════════
function showView(view, param){
  // Update active state on bottom nav
  document.querySelectorAll('.bnav a').forEach(a=>{
    a.classList.toggle('active', a.getAttribute('data-view')===view);
  });
  // Hide all dedicated view sections first
  document.querySelectorAll('[data-view-section]').forEach(el=>el.style.display='none');
  // Home content elements (everything between header and footer that's part of the home view)
  const homeSel='.banner,.quick-cats,.sec-head,#products,.reviews,#cats,.zx-footer';
  const homeBlocks=document.querySelectorAll(homeSel);
  if(view==='home' || view==='search'){
    homeBlocks.forEach(el=>el.style.display='');
    if(view==='search'){
      document.getElementById('search').focus();
    }
    window.scrollTo({top:0,behavior:'smooth'});
    return;
  }
  // For non-home views: hide ALL home content (incl. footer)
  homeBlocks.forEach(el=>el.style.display='none');
  if(view==='category'){renderCategoryPage(param);document.getElementById('view-category').style.display='block';}
  if(view==='orders'){renderOrders();document.getElementById('view-orders').style.display='block';}
  if(view==='account'){renderAccount();document.getElementById('view-account').style.display='block';}
  if(view==='wishlist'){renderWishlist();document.getElementById('view-wishlist').style.display='block';}
  if(view==='product'){document.getElementById('view-product').style.display='block';}
  // Footer only on home
  const footer=document.getElementById('powered-footer');
  if(footer)footer.style.display=view==='home'?'block':'none';
  window.scrollTo({top:0,behavior:'smooth'});
}

// ═══════════════════════ CATEGORY PAGE ═══════════════════════
const CAT_THEMES={
  food:{grad:'linear-gradient(135deg,#f59e0b,#dc2626)',emoji:'🍔',tagAr:'لذيذ وسريع',tagEn:'Hot & fresh',titleAr:'مأكولات',titleEn:'Food'},
  kids:{grad:'linear-gradient(135deg,#06b6d4,#3b82f6)',emoji:'🧸',tagAr:'لأحلى الصغار',tagEn:'For the little ones',titleAr:'أطفال',titleEn:'Kids'},
  sport:{grad:'linear-gradient(135deg,#10b981,#059669)',emoji:'⚽',tagAr:'حماس وتحدّي',tagEn:'Performance gear',titleAr:'رياضة',titleEn:'Sports'},
  home:{grad:'linear-gradient(135deg,#8b5cf6,#ec4899)',emoji:'🏠',tagAr:'بيت أحلى',tagEn:'A better home',titleAr:'منزل',titleEn:'Home'},
  beauty:{grad:'linear-gradient(135deg,#ec4899,#f43f5e)',emoji:'💄',tagAr:'لمسة جمال ساحرة',tagEn:'Glow & glam',titleAr:'تجميل ومكياج',titleEn:'Beauty & Makeup'},
  fashion:{grad:'linear-gradient(135deg,#6366f1,#8b5cf6)',emoji:'👗',tagAr:'موضة عصرية',tagEn:'Modern fashion',titleAr:'أزياء',titleEn:'Fashion'},
  electronics:{grad:'linear-gradient(135deg,#0f172a,#7c3aed)',emoji:'📱',tagAr:'تكنولوجيا حديثة',tagEn:'Latest tech',titleAr:'إلكترونيات',titleEn:'Electronics'},
};
// English translations for runtime strings (Arabic is the default)
const I18N={ar:{back:'رجوع',shop_now:'تسوّق الآن',my_orders:'طلباتي',my_account:'حسابي',sar:'ر.س'},
en:{back:'Back',shop_now:'Shop now',my_orders:'My Orders',my_account:'My Account',sar:'SAR'}};
function tr(k){return (I18N[CURRENT_LANG]||I18N.en)[k]||k;}
// Category background videos (free CDN looping clips)
const CAT_VIDEOS={
  food:'https://cdn.pixabay.com/video/2017/06/14/9839-222603517_large.mp4',
  fashion:'https://cdn.pixabay.com/video/2020/03/29/35169-403291317_large.mp4',
  beauty:'https://cdn.pixabay.com/video/2021/04/29/72237-543437352_large.mp4',
  makeup:'https://cdn.pixabay.com/video/2021/04/29/72237-543437352_large.mp4',
  electronics:'https://cdn.pixabay.com/video/2019/02/10/21307-317538144_large.mp4',
  home:'https://cdn.pixabay.com/video/2024/04/24/209019_large.mp4',
  sport:'https://cdn.pixabay.com/video/2022/02/23/108708-682773715_large.mp4',
  kids:'https://cdn.pixabay.com/video/2019/01/02/20305-309901537_large.mp4',
};

// Category banner images (HIGH-QUALITY, dramatic, full-bleed cinematic shots)
const CAT_IMAGES={
  food:'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=1600&q=90&auto=format&fit=crop',
  fashion:'https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=1600&q=90&auto=format&fit=crop',
  beauty:'https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=1600&q=90&auto=format&fit=crop',
  makeup:'https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=1600&q=90&auto=format&fit=crop',
  electronics:'https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=1600&q=90&auto=format&fit=crop',
  home:'https://images.unsplash.com/photo-1618220179428-22790b461013?w=1600&q=90&auto=format&fit=crop',
  sports:'https://images.unsplash.com/photo-1517649763962-0c623066013b?w=1600&q=90&auto=format&fit=crop',
  sport:'https://images.unsplash.com/photo-1517649763962-0c623066013b?w=1600&q=90&auto=format&fit=crop',
  kids:'https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=1600&q=90&auto=format&fit=crop',
  ai_services:'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1600&q=90&auto=format&fit=crop',
};

// Mini icons for the Quick Categories (top of home) — vivid emoji-style category vibes
const CAT_ICONS={
  electronics:'https://images.unsplash.com/photo-1468495244123-6c6c332eeece?w=200&q=80&fit=crop',
  fashion:'https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=200&q=80&fit=crop',
  beauty:'https://images.unsplash.com/photo-1522335789203-aaa2f8be5419?w=200&q=80&fit=crop',
  home:'https://images.unsplash.com/photo-1618220179428-22790b461013?w=200&q=80&fit=crop',
};

function renderCategoryPage(catId){
  const cat=CATS.find(c=>c.id===catId);
  if(!cat)return;
  const theme=CAT_THEMES[catId]||{tagAr:'عروض حصرية',tagEn:'Exclusive deals'};
  document.getElementById('cat-banner-tag').textContent=CURRENT_LANG==='ar'?theme.tagAr:theme.tagEn;
  document.getElementById('cat-banner-title').textContent=CURRENT_LANG==='ar'?cat.ar:cat.en;
  const filtered=PRODUCTS.filter(p=>p.cat===catId);
  document.getElementById('cat-banner-sub').textContent=CURRENT_LANG==='ar'?'اكتشف '+filtered.length+' منتج مختار بعناية':'Discover '+filtered.length+' carefully curated items';
  const ctaEl=document.getElementById('cat-banner-cta');
  if(ctaEl)ctaEl.textContent=tx('shop_now');
  // Full-bleed background image (always loads) — use override if set
  const img=document.getElementById('cat-banner-img');
  const overrideKey='cat_banner:'+catId;
  img.src=IMG_OVERRIDES[overrideKey]||CAT_IMAGES[catId]||CAT_IMAGES.fashion;
  // Optional video on top (fades in when ready)
  const vid=document.getElementById('cat-banner-video');
  vid.style.opacity='0';
  if(CAT_VIDEOS[catId]){
    vid.src=CAT_VIDEOS[catId];
    vid.load();
    vid.oncanplay=()=>{vid.play().then(()=>{vid.style.opacity='1'}).catch(()=>{})};
  }
  document.getElementById('cat-count-title').textContent=(CURRENT_LANG==='ar'?'المنتجات':'Products')+' ('+filtered.length+')';
  const grid=document.getElementById('cat-products');
  if(!filtered.length){
    grid.innerHTML=`<div style="grid-column:1/-1;text-align:center;padding:40px 20px;color:#9ca3af"><div style="font-size:48px;margin-bottom:10px">📭</div><b>${CURRENT_LANG==='ar'?'لا توجد منتجات حالياً':'No products yet'}</b></div><div class="add-product-card" onclick="startAddProduct('${catId}')"><div class="plus">+</div><b>${CURRENT_LANG==='ar'?'إضافة منتج جديد':'Add new product'}</b><small>${CURRENT_LANG==='ar'?'يفتح استوديو الصور للتوليد':'Opens Image Studio'}</small></div>`;
    return;
  }
  grid.innerHTML=filtered.map(pCardHtml).join('')+`<div class="add-product-card" onclick="startAddProduct('${catId}')"><div class="plus">+</div><b>${CURRENT_LANG==='ar'?'إضافة منتج جديد':'Add new product'}</b><small>${CURRENT_LANG==='ar'?'يفتح استوديو الصور لتوليد منتج بصورة احترافية':'Opens Image Studio to generate a product'}</small></div>`;
}

// ═══════════════════════ ORDERS ═══════════════════════
function getOrders(){return JSON.parse(localStorage.getItem('zx_orders')||'[]');}
function saveOrder(order){const o=getOrders();o.unshift(order);localStorage.setItem('zx_orders',JSON.stringify(o.slice(0,50)));}
function renderOrders(){
  const orders=getOrders();const list=document.getElementById('orders-list');
  if(!orders.length){list.innerHTML=`<div style="background:#fff;border-radius:14px;padding:60px 20px;text-align:center;color:#9ca3af"><div style="font-size:60px;margin-bottom:14px">📭</div><b style="font-size:16px;color:#0a0a0a">${tx('no_orders')}</b><p style="margin-top:8px;font-size:13px">${tx('no_orders_sub')}</p><button onclick="showView('home')" style="margin-top:16px;padding:12px 22px;background:#7c3aed;color:#fff;border:none;border-radius:10px;font-family:inherit;font-weight:900;font-size:13px;cursor:pointer">${tx('shop_now')}</button></div>`;return;}
  const returns=getReturns();
  list.innerHTML=orders.map(o=>{
    const date=new Date(o.date).toLocaleDateString(CURRENT_LANG==='ar'?'ar-SA':'en-US');
    const canReorder=Array.isArray(o.cartItems)&&o.cartItems.length>0;
    const existingReturn=returns.find(r=>r.orderId===o.id);
    const statusMap={confirmed:{ar:'مؤكد',en:'Confirmed',col:'#10b981'},shipped:{ar:'تم الشحن',en:'Shipped',col:'#3b82f6'},delivered:{ar:'تم التسليم',en:'Delivered',col:'#10b981'},cancelled:{ar:'ملغي',en:'Cancelled',col:'#ef4444'}};
    const st=statusMap[o.status]||statusMap.confirmed;
    return `<div style="background:var(--zx-card,#fff);border-radius:14px;padding:14px;margin-bottom:12px;box-shadow:0 2px 12px rgba(0,0,0,.05)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><b style="font-size:13px;color:var(--zx-text)">#${o.id}</b><span style="background:${st.col}20;color:${st.col};padding:3px 10px;border-radius:99px;font-size:11px;font-weight:900">${CURRENT_LANG==='ar'?st.ar:st.en}</span></div>
      <p style="color:#6b7280;font-size:12px;margin-bottom:8px">${date} · ${o.items} ${tx('items_label')}</p>
      ${o.credit_used>0?`<div style="background:#fef3c7;color:#92400e;padding:5px 10px;border-radius:8px;font-size:10px;font-weight:700;margin-bottom:8px;display:inline-block">💳 خصم ${o.currency} ${o.credit_used.toFixed(2)} من المحفظة</div>`:''}
      <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-top:1px solid #f3f4f6;border-bottom:1px solid #f3f4f6;margin-bottom:10px"><span style="font-size:12px;color:#6b7280">الإجمالي</span><b style="color:var(--zx-accent);font-size:15px">${o.currency} ${o.total}</b></div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        ${canReorder?`<button onclick="reorderOrder('${o.id}')" data-testid="reorder-${o.id}" style="flex:1;min-width:120px;padding:9px;background:linear-gradient(135deg,var(--zx-accent),var(--zx-accent2));color:#fff;border:none;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">🔁 اطلب مرة ثانية</button>`:''}
        ${existingReturn?`<button disabled style="flex:1;min-width:120px;padding:9px;background:#fef3c7;color:#92400e;border:1px solid #fde68a;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:not-allowed">🔁 طلب إرجاع #${existingReturn.id} · ${existingReturn.status}</button>`:`<button onclick="openReturnRequest('${o.id}')" data-testid="return-${o.id}" style="flex:1;min-width:120px;padding:9px;background:var(--zx-card,#fff);color:#dc2626;border:1.5px solid #fecaca;border-radius:8px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">↩️ طلب إرجاع</button>`}
      </div>
    </div>`;
  }).join('');
}

// ═══════════════════════ REORDER ═══════════════════════
function reorderOrder(orderId){
  const o=getOrders().find(x=>x.id===orderId);
  if(!o||!Array.isArray(o.cartItems)){alert('لا يمكن إعادة هذا الطلب');return;}
  // Validate products still exist
  const valid=o.cartItems.filter(ci=>PRODUCTS.find(p=>p.id===ci.id));
  const missing=o.cartItems.length-valid.length;
  if(!valid.length){alert('للأسف، المنتجات في هذا الطلب لم تعد متوفرة');return;}
  if(!confirm(`سيتم إضافة ${valid.length} منتج للسلة${missing?` (${missing} منتج غير متوفر حالياً)`:''}. متابعة؟`))return;
  valid.forEach(ci=>{
    const ex=CART.find(c=>c.id===ci.id);
    if(ex)ex.qty+=ci.qty;else CART.push({id:ci.id,qty:ci.qty});
  });
  saveCart();
  toast(`✓ تم إضافة ${valid.length} منتج للسلة`);
  setTimeout(()=>openCart(),400);
}

// ═══════════════════════ STORE CREDIT (محفظة المتجر) ═══════════════════════
function getStoreCredit(){return parseFloat(localStorage.getItem('zx_store_credit')||'0');}
function setStoreCredit(v){localStorage.setItem('zx_store_credit',String(Math.max(0,v)));}
function getCreditHistory(){return JSON.parse(localStorage.getItem('zx_credit_history')||'[]');}
function addStoreCredit(amount,reason){
  const v=getStoreCredit()+amount;
  setStoreCredit(v);
  const h=getCreditHistory();
  h.unshift({date:new Date().toISOString(),amount,reason,balance:v,type:'credit'});
  localStorage.setItem('zx_credit_history',JSON.stringify(h.slice(0,50)));
  return v;
}
function deductStoreCredit(amount,reason){
  const v=Math.max(0,getStoreCredit()-amount);
  setStoreCredit(v);
  const h=getCreditHistory();
  h.unshift({date:new Date().toISOString(),amount:-amount,reason,balance:v,type:'debit'});
  localStorage.setItem('zx_credit_history',JSON.stringify(h.slice(0,50)));
  return v;
}

// ═══════════════════════ RETURNS REQUEST ═══════════════════════
function getReturns(){return JSON.parse(localStorage.getItem('zx_returns')||'[]');}
function openReturnRequest(orderId){
  const o=getOrders().find(x=>x.id===orderId);if(!o){alert('الطلب غير موجود');return;}
  document.getElementById('return-order-id').value=orderId;
  document.getElementById('return-order-info').textContent=`الطلب #${o.id} · ${o.currency} ${o.total}`;
  document.getElementById('return-reason').value='';
  document.getElementById('return-notes').value='';
  document.getElementById('return-modal').classList.add('open');
}
function closeReturnRequest(){document.getElementById('return-modal').classList.remove('open');}
function submitReturnRequest(){
  const orderId=document.getElementById('return-order-id').value;
  const reason=document.getElementById('return-reason').value;
  const notes=document.getElementById('return-notes').value.trim();
  if(!reason){alert('اختر سبب الإرجاع');return;}
  const o=getOrders().find(x=>x.id===orderId);
  const ret={id:'RET-'+Date.now().toString(36).toUpperCase(),orderId,reason,notes,date:new Date().toISOString(),status:'بانتظار الاستلام',order_total:o?.total_raw||0,order_currency:o?.currency||curSym()};
  const arr=getReturns();arr.unshift(ret);localStorage.setItem('zx_returns',JSON.stringify(arr));
  // Refund: instantly add to wallet (simulated; in production this happens after merchant verifies)
  if(o&&o.total_raw){
    addStoreCredit(o.total_raw,`استرداد طلب #${o.id}`);
  }
  closeReturnRequest();
  alert(`✓ تم استلام طلب الإرجاع ${ret.id}\n\nسيتواصل معك التاجر خلال 24 ساعة لجدولة استلام المنتج.\n\n💰 المبلغ المسترد سيُضاف إلى محفظتك تلقائياً بعد التحقق.`);
  renderOrders();renderAccount();
}

// ═══════════════════════ REFERRAL PROGRAM ═══════════════════════
function copyRefCode(){
  const code=document.getElementById('ref-code').textContent;
  navigator.clipboard?.writeText(code).then(()=>toast('✓ تم نسخ الكود · شاركه مع أصدقاءك')).catch(()=>{
    const ta=document.createElement('textarea');ta.value=code;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();
    toast('✓ تم نسخ الكود');
  });
}
function shareRefWhatsapp(){
  const code=document.getElementById('ref-code').textContent;
  const msg=`🎉 جربت متجر Zenrex — تجربة رائعة! استخدم كود الإحالة ${code} عند التسجيل واحصل على 25 ر.س هدية ترحيب 🎁\n\n👇 التطبيق:\n${location.origin}/mockups/app_mode_full.html?ref=${code}`;
  window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`,'_blank');
}
// On page load, check if URL has ?ref= and credit the referrer (mock)
(function checkReferralOnLoad(){
  try{
    const params=new URLSearchParams(location.search);
    const ref=params.get('ref');
    if(ref&&!localStorage.getItem('zx_referred_by')){
      localStorage.setItem('zx_referred_by',ref);
      // Give new user 25 SAR welcome bonus
      const bal=parseFloat(localStorage.getItem('zx_store_credit')||'0')+25;
      localStorage.setItem('zx_store_credit',String(bal));
      const h=JSON.parse(localStorage.getItem('zx_credit_history')||'[]');
      h.unshift({date:new Date().toISOString(),amount:25,reason:`🎁 هدية ترحيب من إحالة ${ref}`,balance:bal,type:'credit'});
      localStorage.setItem('zx_credit_history',JSON.stringify(h));
      setTimeout(()=>alert(`🎉 مرحباً بك من ${ref}!\n\n💰 تم إضافة 25 ر.س هدية لمحفظتك.`),800);
    }
  }catch(_){}
})();

// ═══════════════════════ SAVED PAYMENT CARDS ═══════════════════════
function addSavedCard(){
  const num=prompt('رقم البطاقة (16 رقم):');if(!num||num.replace(/\D/g,'').length<13){if(num)alert('رقم البطاقة غير صحيح');return;}
  const exp=prompt('تاريخ الانتهاء (MM/YY):');if(!exp||!/^\d{1,2}\/\d{2}$/.test(exp.trim())){if(exp)alert('تنسيق التاريخ خاطئ');return;}
  const name=prompt('اسم صاحب البطاقة:')||'العميل';
  const cleanNum=num.replace(/\D/g,'');
  const first=cleanNum.charAt(0);
  const brand=first==='4'?'visa':first==='5'?'mastercard':first==='3'?'amex':'mada';
  const cards=JSON.parse(localStorage.getItem('zx_saved_cards')||'[]');
  if(!cards.length)cards.push({last4:cleanNum.slice(-4),exp:exp.trim(),brand,name,default:true});
  else cards.push({last4:cleanNum.slice(-4),exp:exp.trim(),brand,name,default:false});
  localStorage.setItem('zx_saved_cards',JSON.stringify(cards));
  renderAccount();
  toast('✓ تم حفظ البطاقة بأمان');
}
function removeSavedCard(i){
  if(!confirm('حذف البطاقة؟'))return;
  const cards=JSON.parse(localStorage.getItem('zx_saved_cards')||'[]');
  cards.splice(i,1);
  if(cards.length&&!cards.some(c=>c.default))cards[0].default=true;
  localStorage.setItem('zx_saved_cards',JSON.stringify(cards));
  renderAccount();
}

// ═══════════════════════ SUBSCRIPTIONS (طلب متكرر) ═══════════════════════
function subscribeToProduct(productId){
  if(!getUser()){requireLogin('يلزم تسجيل الدخول للاشتراك المتكرر');return;}
  const p=PRODUCTS.find(x=>x.id===productId);if(!p)return;
  const opts=['weekly','biweekly','monthly','quarterly'];
  const labels={weekly:'كل أسبوع (-5%)',biweekly:'كل أسبوعين (-10%)',monthly:'كل شهر (-15% الأفضل)',quarterly:'كل 3 أشهر (-8%)'};
  // Build a quick choice prompt
  const choice=prompt(`⏰ كم مرة تريد استلام "${p.ar}"؟\n\n1- أسبوعياً (خصم 5%)\n2- كل أسبوعين (خصم 10%)\n3- شهرياً (خصم 15% — الأكثر شيوعاً)\n4- كل 3 أشهر (خصم 8%)\n\nاكتب الرقم:`);
  if(!choice||!['1','2','3','4'].includes(choice.trim()))return;
  const freq=opts[parseInt(choice)-1];
  const days={weekly:7,biweekly:14,monthly:30,quarterly:90}[freq];
  const sub={
    id:'SUB-'+Date.now().toString(36).toUpperCase(),
    productId,
    frequency:freq,
    nextDelivery:new Date(Date.now()+days*86400000).toISOString(),
    paused:false,
    createdAt:new Date().toISOString()
  };
  const arr=JSON.parse(localStorage.getItem('zx_subscriptions')||'[]');
  arr.push(sub);
  localStorage.setItem('zx_subscriptions',JSON.stringify(arr));
  toast(`✓ تم تفعيل الاشتراك · ${labels[freq]}`);
  setTimeout(()=>{showView('account');renderAccount();document.getElementById('acc-subscriptions-section')?.scrollIntoView({block:'center'});},800);
}
function pauseSubscription(i){
  const arr=JSON.parse(localStorage.getItem('zx_subscriptions')||'[]');
  if(!arr[i])return;
  arr[i].paused=!arr[i].paused;
  localStorage.setItem('zx_subscriptions',JSON.stringify(arr));
  renderAccount();
  toast(arr[i].paused?'⏸ تم إيقاف الاشتراك مؤقتاً':'▶️ تم استئناف الاشتراك');
}
function skipNextDelivery(i){
  const arr=JSON.parse(localStorage.getItem('zx_subscriptions')||'[]');
  if(!arr[i])return;
  const days={weekly:7,biweekly:14,monthly:30,quarterly:90}[arr[i].frequency]||30;
  arr[i].nextDelivery=new Date(new Date(arr[i].nextDelivery).getTime()+days*86400000).toISOString();
  localStorage.setItem('zx_subscriptions',JSON.stringify(arr));
  renderAccount();
  toast('⏭️ تم تخطي التوصيلة القادمة');
}
function cancelSubscription(i){
  if(!confirm('هل تريد إلغاء هذا الاشتراك نهائياً؟'))return;
  const arr=JSON.parse(localStorage.getItem('zx_subscriptions')||'[]');
  arr.splice(i,1);
  localStorage.setItem('zx_subscriptions',JSON.stringify(arr));
  renderAccount();
  toast('✓ تم إلغاء الاشتراك');
}

// ═══════════════════════ ACCOUNT ═══════════════════════
function getAccount(){return JSON.parse(localStorage.getItem('zx_account')||'{}');}
function renderAccount(){
  const a=getAccount();
  const u=getUser();
  const nameVal=(u&&u.name)||a.name||'';
  document.getElementById('acc-name').value=nameVal;
  document.getElementById('acc-phone').value=(u&&u.phone)||a.phone||'';
  document.getElementById('acc-addr').value=a.address||'';
  const emailEl=document.getElementById('acc-email');if(emailEl)emailEl.value=a.email||'';
  const bdayEl=document.getElementById('acc-bday');if(bdayEl)bdayEl.value=a.bday||'';
  document.getElementById('acc-greet').textContent=nameVal||tx('guest');
  // Avatar (image or letter)
  const avEl=document.getElementById('acc-avatar');
  if(avEl){
    if(a.avatar){avEl.innerHTML=`<img src="${a.avatar}" alt="avatar" loading="lazy" decoding="async">`;}
    else{avEl.textContent=nameVal?nameVal.charAt(0).toUpperCase():'👤';}
  }
  const orders=getOrders();
  document.getElementById('acc-orders-count').textContent=orders.length;
  document.getElementById('acc-points').textContent=orders.length*10;
  const wcEl=document.getElementById('acc-wish-count');if(wcEl)wcEl.textContent=(typeof WISHLIST!=='undefined'?WISHLIST.length:0);
  // Membership tier
  const memEl=document.getElementById('acc-membership');
  if(memEl){
    const tier=orders.length>=20?{ico:'💎',name:'بلاتيني',col:'#06b6d4'}:orders.length>=10?{ico:'🥇',name:'ذهبي',col:'#eab308'}:orders.length>=3?{ico:'🥈',name:'فضي',col:'#94a3b8'}:{ico:'🥉',name:'برونزي',col:'#a16207'};
    memEl.innerHTML=`${tier.ico} عضو ${tier.name}`;
    memEl.style.color=tier.col;
  }
  // Orders list (last 3)
  const ol=document.getElementById('acc-orders-list');
  if(ol){
    if(!orders.length){ol.innerHTML='<div style="text-align:center;color:#9ca3af;padding:18px;font-size:12px">لا توجد طلبات بعد</div>';}
    else{
      ol.innerHTML=orders.slice(0,3).map((o,i)=>`<div class="acc-order-row"><div><b class="num">#${o.id||(1000+i)}</b><div style="font-size:10px;color:#9ca3af;margin-top:2px">${o.date||'—'} · ${(o.items||[]).length} منتج</div></div><div style="text-align:left"><b style="color:var(--zx-accent)">${curSym()} ${formatPrice(o.total||0)}</b><div style="font-size:10px;color:#10b981">✓ ${o.status||'مؤكد'}</div></div></div>`).join('');
    }
  }
  // Addresses
  const al=document.getElementById('acc-addresses-list');
  const addrs=JSON.parse(localStorage.getItem('zx_addresses')||'[]');
  if(al){
    if(!addrs.length){al.innerHTML='<div style="text-align:center;color:#9ca3af;padding:14px;font-size:12px">لم تضف عناوين بعد</div>';}
    else{al.innerHTML=addrs.map((ad,i)=>`<div class="acc-order-row"><div><b>${ad.label||'العنوان '+(i+1)}</b><div style="font-size:10px;color:#9ca3af;margin-top:2px">${ad.full}</div></div><button onclick="deleteAddress(${i})" style="background:#fef2f2;color:#ef4444;border:1px solid #fecaca;padding:6px 10px;border-radius:8px;font-family:inherit;font-size:10px;cursor:pointer">حذف</button></div>`).join('');}
  }
  // Sync dark mode toggle visual
  const dt=document.getElementById('set-dark-toggle');
  if(dt)dt.classList.toggle('on',document.body.classList.contains('dark'));
  // Sync preferences
  const prefs=JSON.parse(localStorage.getItem('zx_prefs')||'{"notif_orders":true,"notif_offers":true,"notif_new":false,"notif_email":true}');
  document.querySelectorAll('[data-pref]').forEach(b=>{b.classList.toggle('on',!!prefs[b.dataset.pref]);});
  // Store Credit balance
  const bal=getStoreCredit();
  const balEl=document.getElementById('acc-credit-balance');
  if(balEl)balEl.textContent=bal.toFixed(2);
  // Credit history
  const hist=getCreditHistory();
  const histEl=document.getElementById('acc-credit-history');
  if(histEl){
    histEl.innerHTML=hist.length?hist.map(h=>`<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f3f4f6;font-size:12px"><div><b style="color:var(--zx-text)">${h.reason}</b><div style="font-size:10px;color:#9ca3af;margin-top:2px">${new Date(h.date).toLocaleDateString('ar-SA')}</div></div><b style="color:${h.amount>=0?'#10b981':'#ef4444'}">${h.amount>=0?'+':''}${h.amount.toFixed(2)} ر.س</b></div>`).join(''):'<div style="text-align:center;color:#9ca3af;padding:12px;font-size:12px">لا توجد حركات بعد</div>';
  }
  // Returns history
  const returns=getReturns();
  const retSection=document.getElementById('acc-returns');
  const retList=document.getElementById('acc-returns-list');
  if(retSection&&retList){
    if(returns.length){retSection.style.display='block';retList.innerHTML=returns.slice(0,5).map(r=>{
      const stCol=r.status==='بانتظار الاستلام'?'#f59e0b':r.status==='تم الاسترداد'?'#10b981':'#3b82f6';
      return `<div style="background:var(--zx-bg);border-radius:10px;padding:10px;margin-bottom:6px"><div style="display:flex;justify-content:space-between;align-items:center"><b style="font-size:11px;color:var(--zx-accent)">#${r.id}</b><span style="background:${stCol}20;color:${stCol};padding:2px 8px;border-radius:99px;font-size:10px;font-weight:900">${r.status}</span></div><div style="font-size:10px;color:#6b7280;margin-top:4px">طلب #${r.orderId} · ${r.reason}</div></div>`;
    }).join('');}
    else{retSection.style.display='none';}
  }
  // Referral code
  let refCode=localStorage.getItem('zx_ref_code');
  if(!refCode){refCode='ZRX-'+Math.random().toString(36).slice(2,7).toUpperCase();localStorage.setItem('zx_ref_code',refCode);}
  const refCodeEl=document.getElementById('ref-code');if(refCodeEl)refCodeEl.textContent=refCode;
  const refStats=JSON.parse(localStorage.getItem('zx_ref_stats')||'{"invited":0,"earned":0}');
  const refI=document.getElementById('ref-invited');if(refI)refI.textContent=refStats.invited;
  const refE=document.getElementById('ref-earned');if(refE)refE.textContent=refStats.earned;
  // Saved cards
  const cards=JSON.parse(localStorage.getItem('zx_saved_cards')||'[]');
  const cardsList=document.getElementById('acc-cards-list');
  if(cardsList){
    cardsList.innerHTML=cards.length?cards.map((c,i)=>{
      const brandIco={visa:'💳',mastercard:'💳',mada:'🇸🇦',amex:'💎'}[c.brand]||'💳';
      const brandCol={visa:'#1a1f71',mastercard:'#eb001b',mada:'#84BD00',amex:'#016fd0'}[c.brand]||'#7c3aed';
      return `<div style="background:linear-gradient(135deg,${brandCol},${brandCol}dd);color:#fff;border-radius:12px;padding:14px;margin-bottom:8px;position:relative">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><span style="font-size:20px">${brandIco}</span>${c.default?'<span style="background:rgba(255,255,255,.25);font-size:9px;padding:3px 8px;border-radius:99px;font-weight:900">افتراضية</span>':''}</div>
        <div style="font-family:monospace;font-size:15px;letter-spacing:3px;direction:ltr">•••• •••• •••• ${c.last4}</div>
        <div style="display:flex;justify-content:space-between;align-items:end;margin-top:10px"><div><div style="font-size:9px;opacity:.7">صاحب البطاقة</div><b style="font-size:11px">${c.name||'العميل'}</b></div><div style="text-align:left"><div style="font-size:9px;opacity:.7">انتهاء</div><b style="font-size:11px">${c.exp}</b></div><button onclick="removeSavedCard(${i})" style="background:rgba(0,0,0,.25);color:#fff;border:none;width:24px;height:24px;border-radius:50%;cursor:pointer;font-size:11px">🗑️</button></div>
      </div>`;
    }).join(''):'<div style="text-align:center;color:#9ca3af;padding:14px;font-size:12px">لا توجد بطاقات محفوظة</div>';
  }
  // Subscriptions
  const subs=JSON.parse(localStorage.getItem('zx_subscriptions')||'[]');
  const subSec=document.getElementById('acc-subscriptions-section');
  const subList=document.getElementById('acc-subscriptions-list');
  if(subSec&&subList){
    if(subs.length){
      subSec.style.display='block';
      subList.innerHTML=subs.map((s,i)=>{
        const p=PRODUCTS.find(x=>x.id===s.productId);
        const name=p?(CURRENT_LANG==='ar'?p.ar:p.en):'منتج محذوف';
        const nextDate=new Date(s.nextDelivery).toLocaleDateString('ar-SA');
        const freqMap={weekly:'أسبوعياً',biweekly:'كل أسبوعين',monthly:'شهرياً',quarterly:'كل 3 أشهر'};
        return `<div style="background:linear-gradient(135deg,#faf5ff,#fdf2f8);border:1.5px solid #e9d5ff;border-radius:12px;padding:12px;margin-bottom:8px">
          <div style="display:flex;align-items:center;gap:10px"><img src="${p?.img||''}" style="width:48px;height:48px;border-radius:8px;object-fit:cover" loading="lazy" decoding="async"><div style="flex:1;min-width:0"><b style="font-size:12px;color:var(--zx-text)">${name}</b><div style="font-size:10px;color:#6b7280;margin-top:2px">⏰ ${freqMap[s.frequency]||s.frequency} · 📅 التالي: <b>${nextDate}</b></div></div><b style="color:var(--zx-accent);font-size:13px">${curSym()} ${formatPrice(p?.sar||0)}</b></div>
          <div style="display:flex;gap:6px;margin-top:10px"><button onclick="pauseSubscription(${i})" style="flex:1;padding:7px;background:var(--zx-card,#fff);border:1px solid #e5e7eb;border-radius:7px;font-family:inherit;font-size:10px;cursor:pointer;font-weight:700">${s.paused?'▶️ استئناف':'⏸️ إيقاف مؤقت'}</button><button onclick="skipNextDelivery(${i})" style="flex:1;padding:7px;background:var(--zx-card,#fff);border:1px solid #e5e7eb;border-radius:7px;font-family:inherit;font-size:10px;cursor:pointer;font-weight:700">⏭️ تخطي مرة</button><button onclick="cancelSubscription(${i})" style="flex:1;padding:7px;background:#fef2f2;color:#dc2626;border:1px solid #fecaca;border-radius:7px;font-family:inherit;font-size:10px;cursor:pointer;font-weight:700">❌ إلغاء</button></div>
        </div>`;
      }).join('');
    } else {subSec.style.display='none';}
  }
  // Market name
  const mn=document.getElementById('acc-market-name');
  if(mn&&CURRENT_MARKET)mn.textContent=CURRENT_LANG==='ar'?CURRENT_MARKET.name_ar:CURRENT_MARKET.name_en;
  const ab=document.getElementById('acc-auth-block');
  if(u){
    ab.innerHTML=`<div style="background:linear-gradient(135deg,#10b98115,#7c3aed15);border:1px solid #10b98140;border-radius:14px;padding:14px;display:flex;align-items:center;justify-content:space-between">
      <div><div style="font-size:11px;color:#10b981;font-weight:900">✓ مسجّل دخول</div><div style="font-size:13px;color:var(--zx-text);margin-top:2px;direction:ltr">${u.phone}</div></div>
      <button data-testid="logout-btn" onclick="logout()" style="padding:10px 16px;background:var(--zx-card);border:1px solid #ef4444;color:#ef4444;border-radius:10px;font-family:inherit;font-weight:900;font-size:12px;cursor:pointer">🚪 خروج</button>
    </div>`;
  } else {
    ab.innerHTML=`<button data-testid="account-login-btn" onclick="openLogin()" style="width:100%;padding:14px;background:linear-gradient(135deg,var(--zx-accent),var(--zx-accent2));color:#fff;border:none;border-radius:12px;font-family:inherit;font-weight:900;font-size:14px;cursor:pointer">🔐 تسجيل دخول / اشتراك</button>`;
  }
}
function saveAccount(){
  const a={
    name:document.getElementById('acc-name').value.trim(),
    phone:document.getElementById('acc-phone').value.trim(),
    address:document.getElementById('acc-addr').value.trim(),
    email:(document.getElementById('acc-email')||{}).value?.trim()||'',
    bday:(document.getElementById('acc-bday')||{}).value||'',
    avatar:(getAccount().avatar)||''
  };
  localStorage.setItem('zx_account',JSON.stringify(a));
  renderAccount();
  toast(tx('saved_ok'));
}
function onAvatarUpload(e){
  const file=e.target.files?.[0];if(!file)return;
  if(file.size>2*1024*1024){alert('الصورة كبيرة (الحد الأقصى 2MB)');return;}
  const r=new FileReader();
  r.onload=ev=>{
    const a=getAccount();a.avatar=ev.target.result;
    localStorage.setItem('zx_account',JSON.stringify(a));
    renderAccount();
    toast('✓ تم تحديث الصورة');
  };
  r.readAsDataURL(file);
}
function pickAccent(el){
  document.querySelectorAll('#set-accent-row .acc-swatch').forEach(s=>s.classList.remove('active'));
  el.classList.add('active');
  const c1=el.dataset.c1,c2=el.dataset.c2,name=el.dataset.name;
  document.documentElement.style.setProperty('--zx-accent',c1);
  document.documentElement.style.setProperty('--zx-accent2',c2);
  document.getElementById('set-accent-name').textContent=name;
  localStorage.setItem('zx_theme_accent',JSON.stringify({c1,c2,name}));
  toast('✓ تم تطبيق اللون');
}
function pickTextColor(el){
  document.querySelectorAll('#set-text-row .acc-swatch').forEach(s=>s.classList.remove('active'));
  el.classList.add('active');
  const tc=el.dataset.tc;
  if(tc){document.documentElement.style.setProperty('--zx-text',tc);}
  else{document.documentElement.style.removeProperty('--zx-text');}
  document.getElementById('set-textcolor-name').textContent=el.dataset.name;
  localStorage.setItem('zx_text_color',tc||'');
}
function pickFontSize(btn){
  document.querySelectorAll('.acc-font-pick button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const fs=btn.dataset.fs;
  document.documentElement.style.setProperty('--zx-font-scale',fs);
  document.getElementById('set-fontsize-name').textContent=btn.textContent;
  localStorage.setItem('zx_font_scale',fs);
}
function togglePref(btn){
  btn.classList.toggle('on');
  const prefs=JSON.parse(localStorage.getItem('zx_prefs')||'{}');
  prefs[btn.dataset.pref]=btn.classList.contains('on');
  localStorage.setItem('zx_prefs',JSON.stringify(prefs));
}
function toggleCreditHistory(){
  const h=document.getElementById('acc-credit-history');
  if(!h)return;
  h.style.display=h.style.display==='none'?'block':'none';
}
function addAddress(){
  const label=prompt('اسم العنوان (مثال: المنزل، الشغل):');if(!label)return;
  const full=prompt('العنوان الكامل:');if(!full)return;
  const addrs=JSON.parse(localStorage.getItem('zx_addresses')||'[]');
  addrs.push({label,full});
  localStorage.setItem('zx_addresses',JSON.stringify(addrs));
  renderAccount();toast('✓ تمت إضافة العنوان');
}
function deleteAddress(i){
  const addrs=JSON.parse(localStorage.getItem('zx_addresses')||'[]');
  addrs.splice(i,1);
  localStorage.setItem('zx_addresses',JSON.stringify(addrs));
  renderAccount();
}
function downloadMyData(){
  const data={account:getAccount(),orders:getOrders(),addresses:JSON.parse(localStorage.getItem('zx_addresses')||'[]'),wishlist:typeof WISHLIST!=='undefined'?WISHLIST:[],preferences:JSON.parse(localStorage.getItem('zx_prefs')||'{}')};
  const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download='my-zenrex-data.json';a.click();
  URL.revokeObjectURL(url);
  toast('✓ تم تنزيل بياناتك');
}
function confirmDeleteAccount(){
  if(!confirm('⚠️ هل أنت متأكد من حذف حسابك؟ كل البيانات ستفقد نهائياً.'))return;
  if(!confirm('تأكيد أخير: لن نستطيع استرجاع بياناتك. متأكد؟'))return;
  ['zx_account','zx_orders','zx_addresses','zx_user','zx_cust_token','zx_prefs','zx_theme_accent','zx_text_color','zx_font_scale','zx_dark'].forEach(k=>localStorage.removeItem(k));
  alert('تم حذف حسابك. ستتم إعادة تحميل الصفحة.');
  location.reload();
}
// Apply saved theme settings on load
(function applySavedTheme(){
  try{
    const t=JSON.parse(localStorage.getItem('zx_theme_accent')||'null');
    if(t){document.documentElement.style.setProperty('--zx-accent',t.c1);document.documentElement.style.setProperty('--zx-accent2',t.c2);}
    const tc=localStorage.getItem('zx_text_color');if(tc)document.documentElement.style.setProperty('--zx-text',tc);
    const fs=localStorage.getItem('zx_font_scale');if(fs)document.documentElement.style.setProperty('--zx-font-scale',fs);
  }catch(_){}
})();

// Seed demo orders + wallet credit for first-time visitors (for testing the new P0 features)
(function seedDemoOrdersAndCredit(){
  try{
    if(localStorage.getItem('zx_seeded_p0')==='1')return;
    const existing=JSON.parse(localStorage.getItem('zx_orders')||'[]');
    if(existing.length>0){localStorage.setItem('zx_seeded_p0','1');return;}
    const demoOrders=[
      {id:'A1B2C3',date:new Date(Date.now()-86400000*3).toISOString(),items:3,cartItems:[{id:'p1',qty:1},{id:'p3',qty:2}],total:'983.00',total_raw:983,currency:'ر.س',payment:'mada',branch:'الفرع الرئيسي',shipping:'standard',status:'delivered'},
      {id:'D4E5F6',date:new Date(Date.now()-86400000*7).toISOString(),items:2,cartItems:[{id:'p7',qty:1},{id:'p17',qty:1}],total:'1630.00',total_raw:1630,currency:'ر.س',payment:'visa',branch:'الفرع الرئيسي',shipping:'express',status:'delivered'},
      {id:'G7H8I9',date:new Date(Date.now()-86400000*14).toISOString(),items:1,cartItems:[{id:'p11',qty:1}],total:'5499.00',total_raw:5499,currency:'ر.س',payment:'tabby',branch:'الفرع الرئيسي',shipping:'standard',status:'delivered'},
    ];
    localStorage.setItem('zx_orders',JSON.stringify(demoOrders));
    // Seed wallet with 50 SAR welcome bonus
    localStorage.setItem('zx_store_credit','50');
    localStorage.setItem('zx_credit_history',JSON.stringify([
      {date:new Date().toISOString(),amount:50,reason:'🎁 هدية ترحيب — مرحباً بك!',balance:50,type:'credit'}
    ]));
    localStorage.setItem('zx_seeded_p0','1');
  }catch(_){}
})();

// ═══════════════════════ AUTH (OTP via real backend) ═══════════════════════
const API_BASE_CUST = window.location.origin;

// ═══════════ PRODUCT REVIEWS + TRANSLATION ═══════════
async function loadProductReviews(pid){
  const wrap = document.getElementById('pd-reviews');
  if (!wrap) return;
  wrap.innerHTML = '<div style="color:#9ca3af;font-size:12px;text-align:center;padding:20px">جاري تحميل التعليقات...</div>';
  try {
    const r = await fetch(window.location.origin + '/api/store/reviews/' + pid);
    const d = await r.json();
    const items = d.items || [];
    const langOptions = [['ar','العربية'],['en','English'],['zh','中文'],['hi','हिन्दी'],['ur','اردو'],['fr','Français'],['es','Español'],['tr','Türkçe']];
    wrap.innerHTML = `
      <div style="border-top:1px solid #e5e7eb;padding-top:18px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
          <h3 style="font-size:16px;font-weight:900;color:#0f172a;margin:0">⭐ تعليقات العملاء (${d.count})</h3>
          ${d.count ? `<div style="color:#f59e0b;font-weight:900">${d.avg}★</div>` : ''}
        </div>
        ${items.length ? items.map(rv => `
          <div style="background:#fff;border:1px solid #e5e7eb;border-radius:13px;padding:14px;margin-bottom:8px" data-testid="review-${rv.id}">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <div>
                <b style="font-size:13px;color:#0f172a">${rv.name}</b>
                ${rv.verified_purchase ? '<span style="display:inline-block;margin-right:6px;padding:2px 8px;background:rgba(16,185,129,.12);color:#059669;border-radius:99px;font-size:10px;font-weight:900">✓ شراء مؤكد</span>' : ''}
              </div>
              <div style="color:#f59e0b;font-weight:900;font-size:13px">${'★'.repeat(rv.stars)}${'☆'.repeat(5-rv.stars)}</div>
            </div>
            <div style="color:#374151;font-size:13px;line-height:1.7" id="rt-${rv.id}">${rv.text}</div>
            <div style="display:flex;gap:6px;align-items:center;margin-top:8px;flex-wrap:wrap">
              <div style="color:#9ca3af;font-size:10px">${new Date(rv.created_at).toLocaleDateString('ar-SA')}</div>
              <select onchange="translateReview('${rv.id}', this.value)" data-testid="trans-${rv.id}" style="margin-right:auto;padding:3px 8px;background:#f3f4f6;border:1px solid #e5e7eb;border-radius:7px;font-family:inherit;font-size:10px;cursor:pointer;color:#0f172a">
                <option value="">🌐 ترجمة...</option>
                ${langOptions.map(([c,n]) => `<option value="${c}">${n}</option>`).join('')}
              </select>
            </div>
          </div>
        `).join('') : '<div style="text-align:center;color:#9ca3af;padding:30px;background:#f9fafb;border-radius:12px">لا توجد تعليقات بعد · كن أول من يعلق!</div>'}
        <button onclick="openReviewModal('${pid}')" data-testid="add-review-btn" style="margin-top:10px;width:100%;padding:11px;background:linear-gradient(135deg,#7c3aed,#06b6d4);color:#fff;border:none;border-radius:11px;font-family:inherit;font-weight:900;cursor:pointer">✍️ أضف تعليقك</button>
      </div>`;
  } catch(e){ wrap.innerHTML = '<div style="color:#ef4444;text-align:center;padding:20px">تعذر تحميل التعليقات</div>'; }
}

window.translateReview = async function(revId, lang){
  if (!lang) return;
  const el = document.getElementById('rt-' + revId);
  if (!el) return;
  const original = el.dataset.original || el.textContent;
  el.dataset.original = original;
  el.innerHTML = '<span style="color:#9ca3af;font-size:11px">🌐 جاري الترجمة...</span>';
  try {
    const r = await fetch(window.location.origin + '/api/store/reviews/translate', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({text: original, target_lang: lang})
    });
    const d = await r.json();
    const esc = original.replace(/'/g,"\\'");
    el.innerHTML = `${d.translated || original}<br><a href="#" onclick="event.preventDefault();document.getElementById('rt-${revId}').textContent='${esc}'" style="color:#7c3aed;font-size:11px;font-weight:700;text-decoration:none">↩ النص الأصلي</a>`;
  } catch(e){ el.textContent = original; }
};

window.openReviewModal = function(pid){
  const html = `<div id="rev-mod" style="position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;z-index:9700;padding:14px" onclick="if(event.target===this)document.getElementById('rev-mod').remove()"><div style="background:#fff;border-radius:20px;max-width:420px;width:100%;padding:24px"><h3 style="font-size:18px;font-weight:900;color:#0f172a;margin-bottom:6px">✍️ اكتب تعليقك</h3><p style="font-size:12px;color:#64748b;margin-bottom:14px">قيّم المنتج بصدق — تجربتك تساعد العملاء</p><div style="text-align:center;margin-bottom:14px" id="rev-stars">${[1,2,3,4,5].map(n=>`<span data-n="${n}" data-testid="rev-star-${n}" onclick="setRevStars(${n})" style="font-size:36px;color:#fbbf24;cursor:pointer;margin:0 3px">★</span>`).join('')}</div><textarea id="rev-text" data-testid="rev-text" placeholder="شارك تجربتك (إيجابية أو سلبية)..." style="width:100%;padding:11px;border:1.5px solid #e5e7eb;border-radius:11px;font-family:inherit;font-size:13px;margin-bottom:12px;resize:vertical;min-height:80px"></textarea><div style="display:flex;gap:8px"><button onclick="document.getElementById('rev-mod').remove()" style="flex:1;padding:11px;background:#fff;border:1px solid #e5e7eb;color:#64748b;border-radius:11px;font-family:inherit;font-weight:700;cursor:pointer">إلغاء</button><button onclick="submitReview('${pid}')" data-testid="submit-review" style="flex:2;padding:11px;background:linear-gradient(135deg,#7c3aed,#06b6d4);color:#fff;border:none;border-radius:11px;font-family:inherit;font-weight:900;cursor:pointer">نشر التعليق</button></div></div></div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  window._revStars = 5;
};
window.setRevStars = function(n){ window._revStars = n; document.querySelectorAll('#rev-stars span').forEach(s => s.style.color = parseInt(s.dataset.n) <= n ? '#fbbf24' : '#cbd5e1'); };
window.submitReview = async function(pid){
  const text = document.getElementById('rev-text').value.trim();
  if (text.length < 3){ alert('اكتب تعليقاً (3 أحرف على الأقل)'); return; }
  const tok = localStorage.getItem('zx_cust_token') || localStorage.getItem('cust_token') || localStorage.getItem('customer_token') || '';
  if (!tok){ alert('سجّل دخولك أولاً'); return; }
  try {
    const r = await fetch(window.location.origin + '/api/store/reviews', {
      method:'POST', headers:{'Content-Type':'application/json', 'Authorization':'Bearer ' + tok},
      body: JSON.stringify({product_id: pid, stars: window._revStars || 5, text})
    });
    if (!r.ok) throw new Error('fail');
    document.getElementById('rev-mod').remove();
    alert('✓ شكراً! نُشر تعليقك');
    loadProductReviews(pid);
  } catch(e){ alert('فشل النشر'); }
};
function getUser(){try{return JSON.parse(localStorage.getItem('zx_user')||'null');}catch(_){return null;}}
function setUser(u){if(u)localStorage.setItem('zx_user',JSON.stringify(u));else localStorage.removeItem('zx_user');updateAuthUi();}
function getCustToken(){return localStorage.getItem('zx_cust_token')||'';}
function openLogin(){document.getElementById('login-modal').classList.add('open');document.getElementById('login-step-1').style.display='block';document.getElementById('login-step-2').style.display='none';setTimeout(()=>document.getElementById('login-phone').focus(),100);}
function closeLogin(){document.getElementById('login-modal').classList.remove('open');}
let _pendingLoginPhone=null;
async function requestOtp(){
  const phone=document.getElementById('login-phone').value.trim();
  if(phone.replace(/\D/g,'').length<7){alert('رقم الجوال غير صحيح');return;}
  try{
    const r=await fetch(API_BASE_CUST+'/api/store/customer/request-otp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone})});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||'فشل إرسال الرمز');
    _pendingLoginPhone=phone;
    document.getElementById('login-phone-echo').textContent=phone;
    document.getElementById('login-step-1').style.display='none';
    document.getElementById('login-step-2').style.display='block';
    setTimeout(()=>document.getElementById('login-otp').focus(),100);
  }catch(e){alert(e.message);}
}
function loginBackToPhone(){
  document.getElementById('login-step-2').style.display='none';
  document.getElementById('login-step-1').style.display='block';
}
async function verifyOtp(){
  const code=document.getElementById('login-otp').value.trim();
  if(!code){alert('أدخل الرمز');return;}
  try{
    const acc=getAccount();
    const r=await fetch(API_BASE_CUST+'/api/store/customer/verify-otp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone:_pendingLoginPhone,code,name:acc.name||''})});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||'الكود غير صحيح');
    localStorage.setItem('zx_cust_token',d.token);
    setUser({phone:_pendingLoginPhone,name:d.user.name||'',id:d.user.id});
    document.getElementById('login-otp').value='';
    document.getElementById('login-phone').value='';
    closeLogin();
    toast('✓ تم تسجيل الدخول');
    // Sync wishlist from server
    syncWishlistFromServer();
    renderAccount();
  }catch(e){alert(e.message);}
}
function logout(){
  localStorage.removeItem('zx_cust_token');
  setUser(null);
  toast('تم تسجيل الخروج');
  renderAccount();
}
function requireLogin(reason){
  if(getUser())return true;
  if(confirm((reason||'يلزم تسجيل الدخول')+'. تسجيل دخول الآن؟'))openLogin();
  return false;
}
function updateAuthUi(){
  const u=getUser();
  const btn=document.getElementById('header-login-btn');
  if(btn)btn.innerHTML=u?'<span style="color:#10b981">✓</span>':'👤';
}
async function syncWishlistFromServer(){
  if(!getCustToken())return;
  try{
    const r=await fetch(API_BASE_CUST+'/api/store/wishlist',{headers:{'Authorization':'Bearer '+getCustToken()}});
    if(!r.ok)return;
    const d=await r.json();
    WISHLIST=d.items||[];
    saveWishlist();renderProducts();
  }catch(_){}
}
// Load real products from merchant database and prepend them
async function loadMerchantProducts(){
  try{
    const params=new URLSearchParams(window.location.search);
    const merchantId=params.get('m');
    const qs=merchantId?('?merchant_id='+encodeURIComponent(merchantId)):'';
    const r=await fetch(API_BASE_CUST+'/api/store/products'+qs);
    if(!r.ok)return;
    const d=await r.json();
    if(!d.items||!d.items.length)return;
    const adapted=d.items.map(b=>({
      id:b.id,cat:b.cat||'other',
      ar:b.name,en:b.name,
      descAr:b.desc||'',descEn:b.desc||'',
      sar:b.price,img:b.img||'https://images.unsplash.com/photo-1586765501019-cbf6c0b6d7a4?w=500',
      stock:b.stock,sku:b.sku,_fromApi:true,_merchantId:b.merchant_id
    }));
    if(merchantId){
      PRODUCTS=adapted;
      _showMerchantBanner(merchantId,adapted.length);
      // Show AI assistant only on per-merchant page (assume enabled by default — merchant can toggle off in admin)
      const aiFab=document.getElementById('ai-assistant-fab');
      const merchantSettings=JSON.parse(localStorage.getItem('zx_merchant_'+merchantId+'_settings')||'{"ai_assistant":true}');
    if(aiFab)aiFab.style.display='none'; /* AI FAB disabled on customer storefront (it's a merchant control panel feature) */
    }else{
      const existingIds=new Set(PRODUCTS.map(p=>p.id));
      const newOnes=adapted.filter(p=>!existingIds.has(p.id));
      PRODUCTS=[...newOnes,...PRODUCTS];
    }
    renderProducts();
    renderCategories();
    console.log(`[storefront] loaded ${adapted.length} merchant products (merchant=${merchantId||'all'})`);
  }catch(e){console.warn('loadMerchantProducts failed',e);}
}
// ───── HEADER SETTINGS POPOVER + DARK MODE ─────
function toggleHeaderSettings(e){
  e?.stopPropagation();
  const p=document.getElementById('header-settings-popover');
  if(!p)return;
  p.style.display=p.style.display==='none'?'block':'none';
  if(p.style.display==='block'){
    setTimeout(()=>{
      document.addEventListener('click',function _h(ev){
        if(!p.contains(ev.target)){p.style.display='none';document.removeEventListener('click',_h);}
      });
    },100);
  }
}
function toggleDarkMode(){
  document.body.classList.toggle('dark');
  const isDark=document.body.classList.contains('dark');
  localStorage.setItem('zx_dark',isDark?'1':'0');
  const btn=document.getElementById('dark-mode-btn');
  if(btn)btn.innerHTML=isDark?'☀️ الوضع النهاري':'🌙 الوضع الليلي';
  // Sync new account toggle
  const t=document.getElementById('set-dark-toggle');
  if(t)t.classList.toggle('on',isDark);
  toast(isDark?'🌙 تم تفعيل الوضع الليلي':'☀️ تم تفعيل الوضع النهاري');
}
// Restore dark mode on load
if(localStorage.getItem('zx_dark')==='1'){
  document.body.classList.add('dark');
  setTimeout(()=>{const b=document.getElementById('dark-mode-btn');if(b)b.innerHTML='☀️ الوضع النهاري';},200);
}

// ───── AI CUSTOMER ASSISTANT ─────
let _aiQuestionsCount=0;
let _aiBusy=false;
function openAiAssistant(){document.getElementById('ai-modal').classList.add('open');setTimeout(()=>document.getElementById('ai-input').focus(),100);}
function closeAiAssistant(){document.getElementById('ai-modal').classList.remove('open');}
async function aiAskCustomer(q){
  if(!q||!q.trim()||_aiBusy)return;
  _aiBusy=true;
  const log=document.getElementById('ai-chat-log');
  // First question free, then merchant points (1 point per question)
  const isFree=_aiQuestionsCount===0;
  _aiQuestionsCount++;
  document.getElementById('ai-questions-count').textContent=_aiQuestionsCount;
  // Render user message
  const userMsg=document.createElement('div');
  userMsg.style.cssText='background:#7c3aed;color:#fff;padding:10px 12px;border-radius:14px 14px 4px 14px;margin:6px 0 6px auto;max-width:80%;font-size:12px;line-height:1.6;width:fit-content;float:right;clear:both';
  userMsg.textContent=q;
  log.appendChild(userMsg);
  // Render "typing" indicator
  const typing=document.createElement('div');
  typing.style.cssText='background:#f3f4f6;color:#6b7280;padding:10px 14px;border-radius:14px 14px 14px 4px;margin:6px auto 6px 0;max-width:80%;font-size:12px;width:fit-content;float:left;clear:both';
  typing.innerHTML='<b style="color:#7c3aed">✨ Zenrex AI</b> · يكتب...';
  log.appendChild(typing);
  log.scrollTop=log.scrollHeight;
  document.getElementById('ai-input').value='';
  // Simulate AI thinking (~1s)
  await new Promise(r=>setTimeout(r,900));
  // Generate response based on keywords
  const responses={
    'تجربة':'⭐ بناءً على ١٢ تقييم: متوسط ٤.٧/٥<br>✅ <b>الإيجابيات:</b> جودة عالية · تغليف ممتاز · شحن سريع<br>⚠️ <b>الملاحظات:</b> السعر مرتفع نسبياً مقارنة بالمنافسين',
    'قارن':'📊 <b>مقارنة سريعة:</b><br>• <b>هذا المنتج:</b> 5,499 ر.س · شاشة 6.9″ · بطارية 24 ساعة<br>• <b>المنتج البديل:</b> 4,899 ر.س · شاشة 6.7″ · بطارية 22 ساعة<br>💡 <b>توصيتي:</b> لو الشاشة الأكبر مهمة، الأول أفضل',
    'اقترح':'🎁 منتجات تكمل اختيارك:<br>1. كفر حماية بريميوم — 199 ر.س<br>2. شاحن لاسلكي 30W — 349 ر.س<br>3. واقي شاشة زجاجي — 89 ر.س<br><br>💰 العرض: خصم ١٥٪ لو اشتريت ٣ معاً',
    'أفضل':'🎯 بحسب اهتمامك بالجوالات الذكية، أنصحك بـ <b>iPhone 17 Pro Max</b> — يجمع بين الجودة الممتازة والميزات الكاملة. تقييمه ٤.٨/٥ وفي مخزون ٢٤ قطعة.',
    'سعر':'💰 السعر الحالي ٥,٤٩٩ ر.س. لو تحب نخصصلك خصم على كميات، تواصل مع التاجر مباشرة عبر زر واتساب في صفحة المنتج.',
    'شحن':'🚚 الشحن متاح لكل أنحاء السعودية:<br>• الرياض/جدة: ١-٢ يوم<br>• باقي المدن: ٢-٥ أيام<br>• الشحن مجاني فوق ٢٠٠ ر.س',
    'دفع':'💳 طرق الدفع المتاحة:<br>• مدى · Visa/Mastercard<br>• STC Pay · Apple Pay<br>• Tabby (قسّط على ٤ دفعات)<br>• Tamara (ادفع بعد ٣٠ يوم)<br>• الدفع عند الاستلام',
    'default':'سؤال ممتاز! ✨ بناءً على بيانات المتجر، أنصحك:<br>1. راجع قسم "آراء العملاء" تحت كل منتج<br>2. تواصل مع التاجر عبر زر الواتساب لاستفسار محدد<br>3. اسألني بشكل أوضح ⬇️ مثل: "وش الفرق بين المنتجين؟"'
  };
  let resp=responses.default;
  for(const k in responses){if(q.includes(k)){resp=responses[k];break;}}
  // Replace typing with actual response
  typing.innerHTML=`<b style="color:#7c3aed">✨ Zenrex AI:</b><br>${resp}`;
  typing.style.color='#1f2937';
  // Append cost indicator
  if(!isFree){
    const costNote=document.createElement('div');
    costNote.style.cssText='font-size:9px;color:#9ca3af;text-align:center;margin:2px 0 6px;clear:both';
    costNote.innerHTML='💎 تكلفة هذا السؤال: <b>0.10 ر.س</b> · يخصم من رصيد التاجر';
    log.appendChild(costNote);
  } else {
    const freeNote=document.createElement('div');
    freeNote.style.cssText='font-size:9px;color:#10b981;text-align:center;margin:2px 0 6px;font-weight:900;clear:both';
    freeNote.textContent='🎁 سؤالك الأول مجاناً';
    log.appendChild(freeNote);
  }
  log.scrollTop=log.scrollHeight;
  // After 3rd question, show paywall hint
  if(_aiQuestionsCount===3){
    const hint=document.createElement('div');
    hint.style.cssText='background:linear-gradient(135deg,#fffbeb,#fef3c7);border:1px dashed #f59e0b;border-radius:10px;padding:10px;font-size:11px;color:#92400e;text-align:center;margin:8px 0;clear:both;line-height:1.7';
    hint.innerHTML='✨ مساعد AI رائع وتلقائي · التاجر يوفّر لك هذي الخدمة مجاناً (يدفع عنك)';
    log.appendChild(hint);
  }
  _aiBusy=false;
}
function _showMerchantBanner(merchantId,count){
  const existing=document.getElementById('merchant-banner');if(existing)existing.remove();
  const banner=document.createElement('div');
  banner.id='merchant-banner';
  banner.style.cssText='background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;padding:14px 16px;margin:0 0 12px;text-align:center;font-weight:900;font-size:13px;box-shadow:0 4px 14px rgba(124,58,237,.3);position:sticky;top:60px;z-index:50';
  banner.innerHTML=`🏪 أنت في متجر تاجر مخصص — ${count} منتج معروض`;
  const main=document.querySelector('main')||document.body;
  const firstSection=document.querySelector('[data-view-section]')||main.firstChild;
  main.insertBefore(banner,firstSection);
}

// ═══════════════════════ WISHLIST ═══════════════════════
let WISHLIST=JSON.parse(localStorage.getItem('zx_wishlist')||'[]');
function saveWishlist(){localStorage.setItem('zx_wishlist',JSON.stringify(WISHLIST));updateWishBadge();}
function inWish(pid){return WISHLIST.includes(pid);}
function toggleWish(pid){
  if(inWish(pid))WISHLIST=WISHLIST.filter(x=>x!==pid);
  else{WISHLIST.push(pid);toast('❤ تمت الإضافة للمفضلة');}
  saveWishlist();
  renderProducts();
  if(document.getElementById('view-wishlist').style.display!=='none')renderWishlist();
  // Sync to server in background if logged in
  if(getCustToken()){
    fetch(API_BASE_CUST+'/api/store/wishlist',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+getCustToken()},body:JSON.stringify({product_id:pid})}).catch(()=>{});
  }
}
function updateWishBadge(){
  const n=WISHLIST.length;
  const bnavWish=document.getElementById('bnav-wish-badge');
  if(bnavWish){bnavWish.textContent=n;bnavWish.style.display=n>0?'flex':'none';}
}
function renderWishlist(){
  const grid=document.getElementById('wishlist-grid');
  const empty=document.getElementById('wishlist-empty');
  const shareBtn=document.getElementById('share-wishlist-btn');
  const items=WISHLIST.map(id=>PRODUCTS.find(p=>p.id===id)).filter(Boolean);
  if(!items.length){grid.innerHTML='';grid.style.display='none';empty.style.display='block';if(shareBtn)shareBtn.style.display='none';return;}
  grid.style.display='';empty.style.display='none';
  if(shareBtn)shareBtn.style.display='inline-flex';
  grid.innerHTML=items.map(pCardHtml).join('');
}
function shareWishlist(){
  if(!WISHLIST.length){alert('قائمتك فارغة');return;}
  // Build shareable URL
  const baseUrl=window.location.origin+window.location.pathname;
  const shareUrl=`${baseUrl}?wl=${WISHLIST.join(',')}`;
  const items=WISHLIST.map(id=>PRODUCTS.find(p=>p.id===id)).filter(Boolean);
  const itemsList=items.slice(0,5).map(p=>`• ${CURRENT_LANG==='ar'?p.ar:p.en} — ${curSym()} ${formatPrice(p.sar)}`).join('\n');
  const msg=`❤ شوف منتجاتي المفضلة من سوقي:\n\n${itemsList}${items.length>5?`\n... و ${items.length-5} منتج إضافي`:''}\n\n🔗 ${shareUrl}`;
  // Try native share first
  if(navigator.share){
    navigator.share({title:'قائمة مفضلتي',text:msg,url:shareUrl}).then(()=>toast('✓ تمت المشاركة')).catch(()=>{});
    return;
  }
  // Fallback: WhatsApp + copy options
  if(confirm(msg+'\n\nاضغط OK للفتح في واتساب · أو Cancel للنسخ')){
    window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`,'_blank');
  } else {
    navigator.clipboard?.writeText(shareUrl).then(()=>toast('📋 تم نسخ اللينك'));
  }
}
// Read ?wl=p1,p5,... from URL to auto-import shared wishlist
(function _maybeImportSharedWishlist(){
  const params=new URLSearchParams(window.location.search);
  const wl=params.get('wl');
  if(!wl)return;
  const ids=wl.split(',').filter(Boolean);
  if(!ids.length)return;
  setTimeout(()=>{
    if(confirm(`صديقك أرسل لك ${ids.length} منتج من مفضلته — تبي تضيفهم لقائمتك؟`)){
      ids.forEach(id=>{if(!WISHLIST.includes(id))WISHLIST.push(id);});
      saveWishlist();
      toast(`❤ تمت إضافة ${ids.length} منتج للمفضلة`);
      if(typeof showView==='function')showView('wishlist');
    }
  },1500);
})();

// ═══════════════════════ PRODUCT REVIEWS (per-product) ═══════════════════════
function getReviews(pid){try{return JSON.parse(localStorage.getItem('zx_reviews_'+pid)||'[]');}catch(_){return[];}}
function saveReviewsFor(pid,arr){localStorage.setItem('zx_reviews_'+pid,JSON.stringify(arr));}
let _pdReviewStars=5;
function pickReviewStars(n){_pdReviewStars=n;document.querySelectorAll('.pd-rev-star').forEach((el,i)=>{el.textContent=i<n?'★':'☆';el.style.color=i<n?'#f59e0b':'#d1d5db';});}
function renderProductReviews(pid){
  // Fetch from server in background and merge with local cache
  (async()=>{
    try{
      const r=await fetch(API_BASE_CUST+'/api/store/reviews/'+encodeURIComponent(pid));
      if(!r.ok)return;
      const d=await r.json();
      if(d.items&&d.items.length){
        const local=getReviews(pid);
        const localIds=new Set(local.map(x=>x.id));
        const merged=[...local,...d.items.filter(x=>!localIds.has(x.id)).map(x=>({id:x.id,name:x.name,stars:x.stars,text:x.text,date:Date.parse(x.created_at)||Date.now()}))];
        saveReviewsFor(pid,merged);
        _renderReviewsHTML(pid);
      }
    }catch(_){}
  })();
  _renderReviewsHTML(pid);
}
function _renderReviewsHTML(pid){
  const list=getReviews(pid);
  const avg=list.length?(list.reduce((s,r)=>s+r.stars,0)/list.length).toFixed(1):'—';
  const u=getUser();
  let html=`<div style="background:#fff;border-radius:14px;padding:16px;box-shadow:0 2px 12px rgba(0,0,0,.05)">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
      <h3 style="font-size:16px;font-weight:900">⭐ تقييمات المنتج</h3>
      <div style="font-size:13px;color:#6b7280"><b style="color:#f59e0b">${avg}</b> · ${list.length} تقييم</div>
    </div>`;
  if(list.length){
    html+=`<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:14px">`+list.slice().reverse().map(r=>`
      <div style="background:#fafafa;border-radius:10px;padding:12px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <b style="font-size:13px">${(r.name||'عميل').slice(0,30)}</b>
          <span style="color:#f59e0b;font-size:13px">${'★'.repeat(r.stars)}${'☆'.repeat(5-r.stars)}</span>
        </div>
        <p style="font-size:12px;color:#374151;line-height:1.6;margin:0">${(r.text||'').replace(/[<>]/g,'')}</p>
        <small style="color:#9ca3af;font-size:10px">${new Date(r.date).toLocaleDateString('ar-SA')}</small>
      </div>`).join('')+`</div>`;
  } else {
    html+=`<p style="text-align:center;color:#9ca3af;font-size:13px;padding:18px 0">لا توجد تقييمات بعد · كن أول من يقيّم</p>`;
  }
  html+=`<div style="border-top:1px dashed #e5e7eb;padding-top:14px">
    <h4 style="font-size:13px;font-weight:900;margin-bottom:10px">✍️ اكتب تقييمك</h4>
    <div style="display:flex;gap:4px;margin-bottom:10px" id="pd-rev-stars">
      ${[1,2,3,4,5].map(n=>`<button class="pd-rev-star" data-testid="rev-star-${n}" onclick="pickReviewStars(${n})" style="background:none;border:none;font-size:24px;cursor:pointer;color:#f59e0b">★</button>`).join('')}
    </div>
    <textarea id="pd-rev-text" data-testid="pd-rev-text" placeholder="${u?'شاركنا تجربتك...':'سجّل دخولك للكتابة'}" ${u?'':'disabled'} style="width:100%;min-height:60px;padding:10px;border:1px solid #e5e7eb;border-radius:10px;font-family:inherit;font-size:13px;outline:none;resize:vertical;margin-bottom:10px"></textarea>
    <button data-testid="submit-review-btn" onclick="submitReview('${pid}')" style="width:100%;padding:12px;background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;border:none;border-radius:10px;font-family:inherit;font-weight:900;font-size:13px;cursor:pointer">${u?'📨 نشر التقييم':'🔐 سجّل دخول للنشر'}</button>
  </div></div>`;
  document.getElementById('pd-reviews').innerHTML=html;
  _pdReviewStars=5;
}
async function submitReview(pid){
  if(!requireLogin('يلزم تسجيل الدخول لنشر التقييم'))return;
  const text=document.getElementById('pd-rev-text').value.trim();
  if(!text){alert('اكتب نص التقييم أولاً');return;}
  try{
    const r=await fetch(API_BASE_CUST+'/api/store/reviews',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+getCustToken()},body:JSON.stringify({product_id:pid,stars:_pdReviewStars,text})});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||'فشل النشر');
    // Append locally too (so it appears immediately)
    const list=getReviews(pid);
    list.push({name:d.name,stars:d.stars,text:d.text,date:Date.now()});
    saveReviewsFor(pid,list);
    toast('✓ تم نشر تقييمك');
    renderProductReviews(pid);
  }catch(e){alert(e.message);}
}

// ═══════════════════════ COUPONS ═══════════════════════
const COUPONS={'WELCOME10':{code:'WELCOME10',type:'percent',value:10,label:'خصم 10% للترحيب'},'SAVE50':{code:'SAVE50',type:'flat',value:50,label:'خصم 50 ر.س'},'FREESHIP':{code:'FREESHIP',type:'flat',value:25,label:'شحن مجاني (يخصم 25)'}};
let ACTIVE_COUPON=JSON.parse(localStorage.getItem('zx_coupon')||'null');
function applyCoupon(){
  const code=(document.getElementById('coupon-input').value||'').trim().toUpperCase();
  if(!code){ACTIVE_COUPON=null;localStorage.removeItem('zx_coupon');updateCart();toast('تم إلغاء الكود');return;}
  const c=COUPONS[code];
  if(!c){alert('الكود غير صحيح أو منتهي');return;}
  ACTIVE_COUPON=c;localStorage.setItem('zx_coupon',JSON.stringify(c));
  updateCart();
  toast('🎟️ '+c.label);
}

let bannerIdx=0;
function renderBanner(){
  const ar=BANNERS[CURRENT_LANG]||BANNERS.en;
  const banner=document.getElementById('banner');
  // Keep video + overlay layers, only replace slide content
  const existing=banner.querySelectorAll('.banner-slide,.dots');
  existing.forEach(e=>e.remove());
  const slidesHtml=ar.map((b,i)=>`<div class="banner-slide ${i===0?'active':''}"><div><small>${b.tag}</small><h2>${b.title}</h2><p>${b.sub}</p></div></div>`).join('')+`<div class="dots">${ar.map((_,i)=>`<div class="dot ${i===0?'active':''}" onclick="goBanner(${i})"></div>`).join('')}</div>`;
  banner.insertAdjacentHTML('beforeend',slidesHtml);
  bannerIdx=0;
  // Fade video in once ready
  const vid=document.getElementById('banner-video');
  if(vid){vid.oncanplay=()=>{vid.style.opacity='1';vid.play().catch(()=>{})};if(vid.readyState>=3){vid.style.opacity='1'}}
}
function goBanner(i){
  const slides=document.querySelectorAll('.banner-slide');const dots=document.querySelectorAll('.dot');
  if(!slides.length)return;
  slides[bannerIdx]?.classList.remove('active');dots[bannerIdx]?.classList.remove('active');
  bannerIdx=i%slides.length;
  slides[bannerIdx]?.classList.add('active');dots[bannerIdx]?.classList.add('active');
}
function startBannerSlider(){renderBanner();setInterval(()=>goBanner(bannerIdx+1),5000);}

let revIdx=0;
function renderReviews(){
  document.getElementById('r-stage').innerHTML=REVIEWS.map((r,i)=>`<div class="r-slide ${i===0?'active':''}"><div class="r-stars">${'★'.repeat(r.stars)}</div><div class="r-text">"${CURRENT_LANG==='ar'?r.ar:r.en}"</div><div class="r-name">— ${r.name}</div></div>`).join('');
  document.getElementById('r-dots').innerHTML=REVIEWS.map((_,i)=>`<button class="r-dot ${i===0?'active':''}" onclick="goReview(${i})"></button>`).join('');
  revIdx=0;
}
function goReview(i){
  const sl=document.querySelectorAll('.r-slide');const dt=document.querySelectorAll('.r-dot');
  if(!sl.length)return;
  sl[revIdx]?.classList.remove('active');dt[revIdx]?.classList.remove('active');
  revIdx=i%sl.length;
  sl[revIdx]?.classList.add('active');dt[revIdx]?.classList.add('active');
}
function startReviewSlider(){renderReviews();setInterval(()=>goReview(revIdx+1),5000);}

// ═══════════════════════ CART ═══════════════════════
function addToCart(pid){
  const p=PRODUCTS.find(x=>x.id===pid);
  // Branch stock check
  const currentBranch=BRANCHES.find(b=>b.id===SELECTED_BRANCH);
  if(p&&currentBranch&&currentBranch.out_of_stock?.includes(pid)){
    const withStock=BRANCHES.filter(b=>!b.out_of_stock?.includes(pid));
    if(withStock.length&&USER_LOCATION){
      const sorted=withStock.map(b=>({...b,d:haversineKm(USER_LOCATION.lat,USER_LOCATION.lng,b.lat,b.lng)})).sort((a,b)=>a.d-b.d);
      const alt=sorted[0];
      if(confirm(`⚠️ "${p.ar}" غير متوفر في ${currentBranch.ar}.\n\n✓ متوفر في ${alt.ar} (${alt.d.toFixed(1)} كم)\n\nهل تريد التحويل للفرع الآخر وإضافة المنتج؟`)){
        selectBranchAndClose(alt.id);
        setTimeout(()=>{const ex=CART.find(c=>c.id===pid);if(ex)ex.qty++;else CART.push({id:pid,qty:1});saveCart();},400);
      }
    }else{toast('⚠️ هذا المنتج غير متوفر حالياً');}
    return;
  }
  // Smart AI Service — pay with Zenrex credits instantly, no cart
  if(p&&(p.isAI||p.cat==='ai_services')){
    if(!getUser()){requireLogin('يلزم تسجيل الدخول لشراء خدمات الذكاء الاصطناعي');return;}
    const cost=p.credits||p.sar;
    if(ZENREX_CREDITS<cost){
      toast('⚠️ رصيدك غير كافي · لديك '+ZENREX_CREDITS+' نقطة · السعر '+cost);
      const tb=document.getElementById('topup-banner');if(tb)tb.style.display='flex';
      return;
    }
    if(!confirm(`شراء خدمة "${CURRENT_LANG==='ar'?p.ar:p.en}" مقابل ${cost} نقطة؟`))return;
    ZENREX_CREDITS-=cost;
    localStorage.setItem('zx_credits',String(ZENREX_CREDITS));
    const el=document.getElementById('zenrex-credits');if(el)el.textContent=ZENREX_CREDITS;
    const orders=getOrders();
    orders.unshift({id:Date.now(),date:new Date().toLocaleDateString('ar'),items:[{id:p.id,qty:1,name:p.ar}],total:cost,status:'مفعّل · خدمة AI',isAI:true});
    localStorage.setItem('zx_orders',JSON.stringify(orders));
    toast('✓ تم تفعيل الخدمة · سيتواصل معك فريقنا');
    return;
  }
  const ex=CART.find(c=>c.id===pid);
  if(ex)ex.qty++;else CART.push({id:pid,qty:1});
  saveCart();
}
function changeQty(pid,d){
  const it=CART.find(c=>c.id===pid);if(!it)return;
  it.qty+=d;if(it.qty<=0)CART=CART.filter(c=>c.id!==pid);
  saveCart();
}
function saveCart(){localStorage.setItem('zx_cart',JSON.stringify(CART));updateCart();}
function updateCart(){
  const t=TRANS[CURRENT_LANG]||TRANS.en;
  const body=document.getElementById('cart-body');
  const foot=document.getElementById('cart-foot');
  const total=CART.reduce((s,c)=>s+c.qty,0);
  document.getElementById('cart-badge')?.style?.setProperty('display','flex');
  const cb=document.getElementById('cart-badge');if(cb)cb.textContent=total;
  const bnavCart=document.getElementById('bnav-cart-badge');
  if(bnavCart){bnavCart.textContent=total;bnavCart.style.display=total>0?'flex':'none';}
  if(!CART.length){body.innerHTML=`<div class="empty-cart"><div class="ico">🛒</div><b>${t.cart_empty}</b><p style="margin-top:6px;font-size:13px">${t.cart_empty_sub}</p></div>`;foot.style.display='none';return;}
  body.innerHTML=CART.map(c=>{const p=PRODUCTS.find(x=>x.id===c.id);if(!p)return'';const n=CURRENT_LANG==='ar'?p.ar:p.en;return `<div class="cart-item"><img src="${p.img}" loading="lazy" decoding="async"><div class="cart-item-info"><div class="n">${n}</div><div class="p">${curSym()} ${formatPrice(p.sar*c.qty)}</div><div class="qty-row"><button class="qty-btn" onclick="changeQty('${p.id}',-1)">−</button><span class="qty-num">${c.qty}</span><button class="qty-btn" onclick="changeQty('${p.id}',1)">+</button></div></div></div>`;}).join('');
  const sub=CART.reduce((s,c)=>{const p=PRODUCTS.find(x=>x.id===c.id);return s+(p?p.sar*c.qty:0);},0);
  const taxRate=typeof CURRENT_MARKET.tax?.rate==='number'?CURRENT_MARKET.tax.rate:0;
  const coup=ACTIVE_COUPON;
  let discount=0;
  if(coup){discount=coup.type==='percent'?sub*(coup.value/100):Math.min(coup.value,sub);}
  const taxBase=Math.max(0,sub-discount);
  const tax=taxBase*(taxRate/100);
  document.getElementById('subtotal').textContent=`${curSym()} ${formatPrice(sub)}`;
  document.getElementById('tax-line').textContent=`${curSym()} ${formatPrice(tax)}`;
  const dRow=document.getElementById('discount-row');
  if(coup){dRow.style.display='flex';document.getElementById('coupon-label').textContent=coup.code;document.getElementById('discount-line').textContent=`- ${curSym()} ${formatPrice(discount)}`;}
  else{dRow.style.display='none';}
  document.getElementById('total').textContent=`${curSym()} ${formatPrice(taxBase+tax)}`;
  foot.style.display='block';
}
function openCart(){document.getElementById('cart-drawer').classList.add('open')}
function closeCart(){document.getElementById('cart-drawer').classList.remove('open')}

// ═══════════════════════ CHECKOUT ═══════════════════════
function openCheckout(){
  if(!CART.length){alert(tx('cart_empty_alert'));return;}
  document.getElementById('checkout-modal').classList.add('open');
  document.getElementById('checkout-form').style.display='block';
  document.getElementById('checkout-success').style.display='none';
  // Render payment options from market
  const pays=CURRENT_MARKET.payment_gateways||[];
  const icons={card:'💳',wallet:'📱',bnpl:'🕐',cash:'💵',transfer:'🏦',qr:'📲',gateway:'🔌'};
  document.getElementById('pay-list').innerHTML=pays.map(g=>`<div class="pay-option" onclick="choosePay('${g.id}',this)"><div class="icon">${icons[g.type]||'💳'}</div><div class="info"><b>${g.name}</b><small>${g.tagline||''}</small></div>${g.popular?'<div class="pay-tag tag-pop">★</div>':''}</div>`).join('');
  // Render shipping methods
  renderShippingOptions();
  // Render branches (no user location yet → sort alphabetically)
  renderBranches();
  // Init map after modal animation
  setTimeout(initCheckoutMap,300);
  // Initialize delivery time picker
  initDeliveryTime();
  // Update BNPL split amount (cart total / 4)
  try {
    const total = (typeof CART !== 'undefined') ? CART.reduce((s,it) => s + (it.price * it.qty), 0) : 0;
    const el = document.getElementById('bnpl-split-amt');
    if (el) el.textContent = (total/4).toFixed(0) + ' ر.س/شهر';
  } catch(e){}
}

// ═══════════════════════════════════════════════════════════════════
// DELIVERY TIME (now / scheduled) — per-cart scheduling
// ═══════════════════════════════════════════════════════════════════
window.CK_SCHED = {mode:'now', date:'', time:'', eta_window:''};
async function initDeliveryTime(){
  // Reset
  window.CK_SCHED = {mode:'now', date:'', time:'', eta_window:''};
  // Show is-open banner
  try {
    const r = await fetch(API_BASE_CUST + '/api/delivery/schedule/is-open?merchant_id=demo');
    const d = await r.json();
    const banner = document.getElementById('ck-open-status');
    if (d.is_open || d.is_24_7){
      banner.style.background = '#dcfce7'; banner.style.color = '#15803d';
      banner.innerHTML = `🟢 المتجر مفتوح الآن ${d.is_24_7 ? '· 24/7' : ''}`;
    } else {
      banner.style.background = '#fee2e2'; banner.style.color = '#b91c1c';
      banner.innerHTML = `🔴 مغلق · يفتح ${d.next_open_label || ''}`;
    }
  } catch(e){}
  // Bind buttons
  const nowBtn = document.getElementById('ck-when-now');
  const schBtn = document.getElementById('ck-when-sched');
  const picker = document.getElementById('ck-sched-picker');
  nowBtn.onclick = () => {
    window.CK_SCHED = {mode:'now', date:'', time:'', eta_window:''};
    nowBtn.style.background = 'linear-gradient(135deg,#7c3aed,#06b6d4)'; nowBtn.style.color = '#fff'; nowBtn.style.border = 'none';
    schBtn.style.background = '#fff'; schBtn.style.color = '#6b7280'; schBtn.style.border = '1.5px solid #e5e7eb';
    picker.style.display = 'none';
  };
  schBtn.onclick = async () => {
    window.CK_SCHED.mode = 'schedule';
    schBtn.style.background = 'linear-gradient(135deg,#7c3aed,#06b6d4)'; schBtn.style.color = '#fff'; schBtn.style.border = 'none';
    nowBtn.style.background = '#fff'; nowBtn.style.color = '#6b7280'; nowBtn.style.border = '1.5px solid #e5e7eb';
    picker.style.display = 'block';
    // Populate dates (next 7 days)
    const sel = document.getElementById('ck-sched-date');
    sel.innerHTML = '';
    const today = new Date();
    const dayNamesAr = ['الأحد','الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت'];
    for (let i=0; i<7; i++){
      const d = new Date(today); d.setDate(today.getDate() + i);
      const iso = d.toISOString().slice(0,10);
      const lbl = (i===0?'اليوم':(i===1?'بكرة':dayNamesAr[d.getDay()])) + ' · ' + iso;
      const opt = document.createElement('option'); opt.value = iso; opt.textContent = lbl;
      sel.appendChild(opt);
    }
    sel.onchange = () => loadCkSlots(sel.value);
    await loadCkSlots(sel.value);
  };
}
async function loadCkSlots(date){
  const r = await fetch(API_BASE_CUST + `/api/delivery/schedule/slots?merchant_id=demo&date=${date}`);
  const d = await r.json();
  const ts = document.getElementById('ck-sched-time');
  ts.innerHTML = '<option value="">-- اختر الوقت --</option>';
  (d.slots || []).forEach(s => {
    const o = document.createElement('option');
    o.value = s.value;
    o.dataset.eta = s.eta_window || '';
    o.textContent = s.label + (s.eta_window ? '  (الوصول: ' + s.eta_window + ')' : '');
    ts.appendChild(o);
  });
  if ((d.slots || []).length === 0){
    ts.innerHTML = '<option value="">لا توجد فترات متاحة</option>';
  }
  ts.onchange = () => {
    window.CK_SCHED.date = date;
    window.CK_SCHED.time = ts.value;
    window.CK_SCHED.eta_window = ts.selectedOptions[0]?.dataset.eta || '';
    const info = document.getElementById('ck-eta-info');
    if (window.CK_SCHED.time){
      info.style.display = 'block';
      info.innerHTML = `📦 السائق يستلم قبل الموعد بـ <b>30 دقيقة</b> · بيوصلك بين <b>${window.CK_SCHED.eta_window}</b>`;
    } else {
      info.style.display = 'none';
    }
  };
}

function closeCheckout(){document.getElementById('checkout-modal').classList.remove('open');CHECKOUT_MAP=null;}
function choosePay(id,el){
  PAYMENT_CHOSEN=id;
  document.querySelectorAll('.pay-option').forEach(e=>e.style.borderColor='#e5e7eb');
  // For custom BNPL cards, also reset border
  document.querySelectorAll('[data-testid^="pay-zenrex-"]').forEach(e=>e.style.border='2px solid transparent');
  if (el) { el.style.borderColor='#7c3aed'; el.style.background = el.style.background || '#faf5ff'; }
  // If scheduled mode requires a time, block submission and prompt user.
  if (window.CK_SCHED && window.CK_SCHED.mode === 'schedule' && !window.CK_SCHED.time){
    alert('اختر وقت التوصيل من قائمة "حجز موعد" أولاً');
    return;
  }
  // Validate required customer info before POST
  const nm = (document.getElementById('ck-name')||{}).value || '';
  const ph = (document.getElementById('ck-phone')||{}).value || '';
  const ad = (document.getElementById('ck-address')||{}).value || '';
  if (!nm.trim() || !ph.trim()) { alert('الرجاء تعبئة الاسم ورقم الجوال قبل إتمام الطلب'); return; }
  // POST order to backend (persist + show in admin/driver) — fire & forget, but await response for ID
  const cartTotal = (typeof CART !== 'undefined') ? CART.reduce((s,it)=>s+(it.price*it.qty),0) : 0;
  const payload = {
    customer_name: nm.trim(),
    customer_phone: ph.trim(),
    address: ad.trim() || 'غير محدد',
    items: (CART||[]).map(it=>({name:it.name||'منتج', qty:it.qty||1, sar:it.price||0})),
    total_sar: cartTotal,
    payment_method: id || 'cod',
    notes: ((document.getElementById('ck-notes')||{}).value || '') + (window.CK_SCHED && window.CK_SCHED.mode==='schedule' ? ` | موعد التوصيل: ${window.CK_SCHED.date} ${window.CK_SCHED.time}` : ''),
    zone: 'central',
  };
  let orderIdReal = null;
  fetch((window.location.origin) + '/api/delivery/orders', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  }).then(r=>r.json()).then(d=>{
    orderIdReal = d && d.id ? d.id : null;
    if (orderIdReal){
      // Save order id in localStorage for "طلباتي" view
      try { const arr=JSON.parse(localStorage.getItem('my_orders')||'[]'); arr.unshift({id:orderIdReal,total:cartTotal,at:Date.now(),items:payload.items.length}); localStorage.setItem('my_orders',JSON.stringify(arr.slice(0,50))); } catch(e){}
      // Inject order id into success modal if visible
      const sub = document.querySelector('#checkout-success p');
      if (sub && !sub.innerHTML.includes(orderIdReal)) sub.innerHTML = (sub.innerHTML||'') + `<br><span style="opacity:.7;font-size:11px">رقم الطلب: <b style="color:#7c3aed">${orderIdReal}</b></span>`;
    }
  }).catch(e=>console.warn('order POST failed', e));
  setTimeout(()=>{
    document.getElementById('checkout-form').style.display='none';
    document.getElementById('checkout-success').style.display='block';
    const subEl = document.querySelector('#checkout-success p');
    let extra = '';
    if (id === 'zenrex_split'){
      const total = (typeof CART !== 'undefined') ? CART.reduce((s,it) => s + (it.price * it.qty), 0) : 0;
      extra = `<br>💳 سيتم تقسيمها على <b>4 دفعات</b> = <b>${(total/4).toFixed(0)} ر.س/شهر</b>`;
    } else if (id === 'zenrex_later'){
      extra = `<br>🕐 ستُسدّد خلال <b>30 يوماً</b> بدون فوائد`;
    }
    if (window.CK_SCHED && window.CK_SCHED.mode === 'schedule' && window.CK_SCHED.time){
      subEl.innerHTML = `✅ موعد التوصيل: <b>${window.CK_SCHED.date} الساعة ${window.CK_SCHED.time}</b><br>📦 السائق يصلك بين <b>${window.CK_SCHED.eta_window}</b>${extra}`;
    } else {
      subEl.innerHTML = 'سيتم التواصل معك للتوصيل قريباً' + extra;
    }
    // Show "Rate Your Delivery" button after a few seconds
    setTimeout(() => {
      if (document.getElementById('rate-btn-inject')) return;
      const successEl = document.getElementById('checkout-success');
      if (!successEl) return;
      const rateBtn = document.createElement('button');
      rateBtn.id = 'rate-btn-inject';
      rateBtn.dataset.testid = 'rate-delivery-btn';
      rateBtn.onclick = () => openRateModal();
      rateBtn.style.cssText = 'margin-top:14px;width:100%;padding:12px;background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#fff;border:none;border-radius:11px;font-weight:900;font-size:14px;cursor:pointer;font-family:inherit';
      rateBtn.innerHTML = '⭐ قيّم تجربة التوصيل';
      successEl.appendChild(rateBtn);
    }, 2000);
    if (typeof CART !== 'undefined'){ CART.length = 0; if (typeof updateCart === 'function') updateCart(); }
  }, 400);
}

// ═════════ RATE DRIVER MODAL ═════════
window.openRateModal = function(){
  let stars = 5;
  const html = `
    <div id="rate-mod" style="position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;z-index:9700;padding:14px" onclick="if(event.target===this)closeRateMod()">
      <div style="background:#fff;border-radius:20px;max-width:380px;width:100%;padding:24px">
        <h3 style="font-size:18px;font-weight:900;margin-bottom:6px;color:#0f172a">قيّم سائقك</h3>
        <p style="font-size:12px;color:#64748b;margin-bottom:18px">رأيك يساعد التجار والعملاء الآخرين</p>
        <div style="text-align:center;margin-bottom:14px">
          <div style="width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#06b6d4);display:inline-flex;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:24px;margin-bottom:8px">س</div>
          <div style="font-weight:900;font-size:14px;color:#0f172a">السائق</div>
        </div>
        <div style="text-align:center;margin-bottom:14px" id="rt-stars">
          ${[1,2,3,4,5].map(n => `<span data-n="${n}" data-testid="star-${n}" onclick="setStars(${n})" style="font-size:36px;color:#fbbf24;cursor:pointer;margin:0 4px">★</span>`).join('')}
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;justify-content:center">
          ${['سريع','مهذب','نظيف','ودود','محترف','دقيق'].map(t => `<button class="rt-tag" data-tag="${t}" data-testid="tag-${t}" onclick="toggleTag('${t}',this)" style="padding:5px 12px;border:1.5px solid #e5e7eb;background:#fff;border-radius:99px;font-family:inherit;font-size:11px;font-weight:700;cursor:pointer;color:#0f172a">${t}</button>`).join('')}
        </div>
        <textarea id="rt-comment" data-testid="rate-comment" placeholder="اكتب تعليق (اختياري)..." style="width:100%;padding:11px;border:1.5px solid #e5e7eb;border-radius:11px;font-family:inherit;font-size:13px;margin-bottom:12px;resize:vertical;min-height:60px"></textarea>
        <div style="display:flex;gap:8px">
          <button onclick="closeRateMod()" style="flex:1;padding:11px;background:#fff;border:1px solid #e5e7eb;color:#64748b;border-radius:11px;font-family:inherit;font-weight:700;cursor:pointer">لاحقاً</button>
          <button onclick="submitRating()" data-testid="submit-rating" style="flex:2;padding:11px;background:linear-gradient(135deg,#7c3aed,#06b6d4);color:#fff;border:none;border-radius:11px;font-family:inherit;font-weight:900;cursor:pointer">إرسال التقييم</button>
        </div>
      </div>
    </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  window._rateStars = 5; window._rateTags = [];
};
window.setStars = function(n){
  window._rateStars = n;
  document.querySelectorAll('#rt-stars span').forEach(s => {
    s.style.color = parseInt(s.dataset.n) <= n ? '#fbbf24' : '#cbd5e1';
  });
};
window.toggleTag = function(t, el){
  window._rateTags = window._rateTags || [];
  const i = window._rateTags.indexOf(t);
  if (i >= 0){
    window._rateTags.splice(i, 1);
    el.style.background = '#fff'; el.style.color = '#0f172a'; el.style.borderColor = '#e5e7eb';
  } else {
    window._rateTags.push(t);
    el.style.background = 'linear-gradient(135deg,#7c3aed,#06b6d4)'; el.style.color = '#fff'; el.style.borderColor = 'transparent';
  }
};
window.closeRateMod = function(){ document.getElementById('rate-mod')?.remove(); };
window.submitRating = async function(){
  const comment = document.getElementById('rt-comment').value.trim();
  try {
    const r = await fetch(window.location.origin + '/api/delivery/ratings', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        driver_id: '0552222222',
        driver_name: 'السائق التجريبي',
        customer_name: document.getElementById('cust-name')?.value || 'عميل',
        customer_phone: document.getElementById('cust-phone')?.value || '',
        stars: window._rateStars || 5,
        comment, tags: window._rateTags || [],
      })
    });
    if (!r.ok) throw new Error('fail');
    closeRateMod();
    alert('✓ شكراً! تم إرسال تقييمك');
  } catch(e){
    alert('فشل الإرسال — حاول مرة ثانية');
  }
};

// ═══════════════════════ MAP + BRANCHES + STOCK LOGIC ═══════════════════════
function haversineKm(lat1,lng1,lat2,lng2){
  const R=6371,toRad=d=>d*Math.PI/180;
  const dLat=toRad(lat2-lat1),dLng=toRad(lng2-lng1);
  const a=Math.sin(dLat/2)**2+Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLng/2)**2;
  return R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));
}
function initCheckoutMap(){
  if(typeof L==='undefined'){setTimeout(initCheckoutMap,400);return;}
  const el=document.getElementById('ck-map');
  if(!el)return;
  el.innerHTML='';
  CHECKOUT_MAP=L.map(el,{zoomControl:false,attributionControl:false}).setView([24.7136,46.6753],10);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18}).addTo(CHECKOUT_MAP);
  L.control.zoom({position:'topright'}).addTo(CHECKOUT_MAP);
  // Plot all branches
  BRANCHES.forEach(b=>{
    const icon=L.divIcon({className:'',html:`<div style="background:#7c3aed;color:#fff;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.35);font-weight:900">🏪</div>`,iconSize:[28,28],iconAnchor:[14,14]});
    L.marker([b.lat,b.lng],{icon}).addTo(CHECKOUT_MAP).bindPopup(`<b>${CURRENT_LANG==='ar'?b.ar:b.en}</b><br><small>${CURRENT_LANG==='ar'?b.addrAr:b.addrEn}</small>`);
  });
  // Fit to bounds
  const bounds=L.latLngBounds(BRANCHES.map(b=>[b.lat,b.lng]));
  CHECKOUT_MAP.fitBounds(bounds,{padding:[24,24]});
}
function locateMe(){
  if(!navigator.geolocation){alert('Geolocation not supported');return;}
  navigator.geolocation.getCurrentPosition(pos=>{
    USER_LOCATION={lat:pos.coords.latitude,lng:pos.coords.longitude};
    addUserMarker();
    renderBranches();
  },err=>{
    // Fallback: demo location (Riyadh)
    USER_LOCATION={lat:24.71+Math.random()*0.05,lng:46.67+Math.random()*0.05};
    addUserMarker();
    renderBranches();
  },{timeout:8000});
}
function addUserMarker(){
  if(!CHECKOUT_MAP||!USER_LOCATION)return;
  const icon=L.divIcon({className:'',html:`<div style="background:#ef4444;color:#fff;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;border:3px solid #fff;box-shadow:0 0 0 4px rgba(239,68,68,.3);font-weight:900">📍</div>`,iconSize:[24,24],iconAnchor:[12,12]});
  L.marker([USER_LOCATION.lat,USER_LOCATION.lng],{icon}).addTo(CHECKOUT_MAP);
  // Draw line to nearest branch
  const sorted=BRANCHES.slice().sort((a,b)=>haversineKm(USER_LOCATION.lat,USER_LOCATION.lng,a.lat,a.lng)-haversineKm(USER_LOCATION.lat,USER_LOCATION.lng,b.lat,b.lng));
  const nearest=sorted[0];
  L.polyline([[USER_LOCATION.lat,USER_LOCATION.lng],[nearest.lat,nearest.lng]],{color:'#7c3aed',weight:3,dashArray:'6,8'}).addTo(CHECKOUT_MAP);
  CHECKOUT_MAP.fitBounds(L.latLngBounds([[USER_LOCATION.lat,USER_LOCATION.lng],[nearest.lat,nearest.lng]]),{padding:[40,40]});
}
function renderBranches(){
  // Compute distances and order
  const withDist=BRANCHES.map(b=>({...b,dist:USER_LOCATION?haversineKm(USER_LOCATION.lat,USER_LOCATION.lng,b.lat,b.lng):null}));
  withDist.sort((a,b)=>(a.dist??999)-(b.dist??999));
  // Default select nearest
  if(!SELECTED_BRANCH || !withDist.find(b=>b.id===SELECTED_BRANCH)){SELECTED_BRANCH=withDist[0].id;}
  const host=document.getElementById('branch-list');
  host.innerHTML=withDist.map((b,i)=>{
    const cartIds=CART.map(c=>c.id);
    const missing=cartIds.filter(id=>b.out_of_stock.includes(id));
    const isSel=b.id===SELECTED_BRANCH;
    const distLabel=b.dist!=null?`${b.dist.toFixed(1)} ${tx('km_away')}`:'';
    const nearestTag=i===0&&b.dist!=null?` <span style="background:#10b981;color:#fff;padding:2px 7px;border-radius:99px;font-size:9px;font-weight:900;margin-${CURRENT_LANG==='ar'?'right':'left'}:4px">${tx('nearest')}</span>`:'';
    return `<div class="branch-card ${isSel?'selected':''}" onclick="selectBranch('${b.id}')">
      <div class="b-ico">🏪</div>
      <div class="b-info"><b>${CURRENT_LANG==='ar'?b.ar:b.en}${nearestTag}</b><small>${CURRENT_LANG==='ar'?b.addrAr:b.addrEn}${missing.length?` · ⚠️ ${missing.length} ${tx('items_label')} ${CURRENT_LANG==='ar'?'غير متوفر':'unavailable'}`:''}</small></div>
      <div class="b-dist">${distLabel}</div>
    </div>`;
  }).join('');
  renderStockAlert(withDist[0]);
}
function selectBranch(id){SELECTED_BRANCH=id;renderBranches();updateBranchBar();}

// ═══════════════════════ PERSISTENT BRANCH BAR + LOCATION FLOW ═══════════════════════
function updateBranchBar(){
  const bar=document.getElementById('branch-bar');if(!bar)return;
  const b=BRANCHES.find(x=>x.id===SELECTED_BRANCH);
  const nameEl=document.getElementById('branch-bar-name');
  const distEl=document.getElementById('branch-bar-dist');
  if(b){
    nameEl.textContent=CURRENT_LANG==='ar'?b.ar:b.en;
    if(USER_LOCATION){
      const dist=haversineKm(USER_LOCATION.lat,USER_LOCATION.lng,b.lat,b.lng);
      distEl.innerHTML=`📍 ${dist.toFixed(1)} كم`;
    }else{distEl.textContent='';}
  }else{
    nameEl.textContent='— اختر فرعك —';distEl.textContent='';
  }
}
function openLocationModal(){document.getElementById('location-modal').classList.add('open');}
function closeLocationModal(){document.getElementById('location-modal').classList.remove('open');localStorage.setItem('zx_location_asked','1');}
function pickBranchManually(){closeLocationModal();openBranchPicker();}
function requestLocationPermission(){
  if(!navigator.geolocation){alert('متصفحك لا يدعم تحديد الموقع');return;}
  toast('⏳ جاري تحديد موقعك...');
  navigator.geolocation.getCurrentPosition(pos=>{
    USER_LOCATION={lat:pos.coords.latitude,lng:pos.coords.longitude};
    localStorage.setItem('zx_user_location',JSON.stringify(USER_LOCATION));
    autoSelectNearestBranch();
    closeLocationModal();
    closeBranchPicker();
    toast('✓ تم تحديد موقعك · اخترنا الفرع الأقرب لك');
  },err=>{
    // Fallback to manual
    closeLocationModal();
    openBranchPicker();
    toast('⚠️ لم نتمكن من تحديد موقعك · اختر يدوياً');
  },{timeout:10000,enableHighAccuracy:true});
}
function autoSelectNearestBranch(){
  if(!USER_LOCATION)return;
  const sorted=BRANCHES.slice().sort((a,b)=>haversineKm(USER_LOCATION.lat,USER_LOCATION.lng,a.lat,a.lng)-haversineKm(USER_LOCATION.lat,USER_LOCATION.lng,b.lat,b.lng));
  SELECTED_BRANCH=sorted[0].id;
  localStorage.setItem('zx_selected_branch',SELECTED_BRANCH);
  updateBranchBar();
  renderProducts();
}
function openBranchPicker(){
  document.getElementById('branch-picker-modal').classList.add('open');
  renderBranchPickerList();
}
function closeBranchPicker(){document.getElementById('branch-picker-modal').classList.remove('open');}
function renderBranchPickerList(){
  const host=document.getElementById('branch-picker-list');
  const withDist=BRANCHES.map(b=>({...b,dist:USER_LOCATION?haversineKm(USER_LOCATION.lat,USER_LOCATION.lng,b.lat,b.lng):null}));
  withDist.sort((a,b)=>(a.dist??999)-(b.dist??999));
  host.innerHTML=withDist.map((b,i)=>{
    const isSel=b.id===SELECTED_BRANCH;
    const distLabel=b.dist!=null?`${b.dist.toFixed(1)} كم`:'—';
    const nearestTag=i===0&&b.dist!=null?'<span style="background:#10b981;color:#fff;padding:2px 7px;border-radius:99px;font-size:9px;font-weight:900;margin-right:6px">الأقرب ✓</span>':'';
    const shipPct=b.ship_modifier?Math.round((b.ship_modifier-1)*100):0;
    const shipBadge=shipPct===0?'<span style="color:#10b981;font-size:9px;font-weight:700">رسوم شحن قياسية</span>':`<span style="color:#f59e0b;font-size:9px;font-weight:700">+${shipPct}% رسوم شحن</span>`;
    return `<div onclick="selectBranchAndClose('${b.id}')" data-testid="branch-option-${b.id}" style="border:2px solid ${isSel?'var(--zx-accent,#7c3aed)':'#e5e7eb'};background:${isSel?'linear-gradient(135deg,#faf5ff,#fdf2f8)':'#fff'};border-radius:12px;padding:12px;cursor:pointer;margin-bottom:8px;transition:all .15s">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;display:flex;align-items:center;justify-content:center;font-size:18px">🏪</div>
        <div style="flex:1;min-width:0"><b style="font-size:13px">${CURRENT_LANG==='ar'?b.ar:b.en}${nearestTag}</b><div style="font-size:11px;color:#6b7280;margin-top:2px">${CURRENT_LANG==='ar'?b.addrAr:b.addrEn}</div><div style="margin-top:4px;display:flex;gap:8px;align-items:center">${shipBadge}<span style="color:#6b7280;font-size:9px">📞 ${b.phone}</span></div></div>
        <div style="text-align:left"><b style="color:var(--zx-accent,#7c3aed);font-size:14px">${distLabel}</b>${isSel?'<div style="font-size:9px;color:var(--zx-accent,#7c3aed);font-weight:900;margin-top:2px">✓ المختار</div>':''}</div>
      </div>
    </div>`;
  }).join('');
}
function selectBranchAndClose(id){
  const prev=SELECTED_BRANCH;
  SELECTED_BRANCH=id;
  localStorage.setItem('zx_selected_branch',id);
  closeBranchPicker();
  updateBranchBar();
  renderProducts(); // re-render products to update availability
  const b=BRANCHES.find(x=>x.id===id);
  toast(`✓ تم التحويل لـ ${CURRENT_LANG==='ar'?b.ar:b.en}`);
  // If cart has out-of-stock items in new branch, warn
  if(prev!==id&&CART.length){
    const missing=CART.filter(c=>b.out_of_stock.includes(c.id));
    if(missing.length){
      setTimeout(()=>toast(`⚠️ ${missing.length} منتج من سلتك غير متوفر بالفرع الجديد`),1200);
    }
  }
}

// Initialize branch system on page load
(function initBranchSystem(){
  try{
    const savedLoc=localStorage.getItem('zx_user_location');
    if(savedLoc){USER_LOCATION=JSON.parse(savedLoc);}
    const savedBranch=localStorage.getItem('zx_selected_branch');
    if(savedBranch){SELECTED_BRANCH=savedBranch;}
    else if(USER_LOCATION){autoSelectNearestBranch();}
    setTimeout(updateBranchBar,400);
    // Prompt for location on first visit only
    if(!localStorage.getItem('zx_location_asked')&&!savedLoc){
      setTimeout(openLocationModal,2000);
    }
  }catch(_){}
})();
function renderStockAlert(nearestBranch){
  const host=document.getElementById('stock-alert-host');
  if(!nearestBranch){host.innerHTML='';return;}
  const cartIds=CART.map(c=>c.id);
  const missingIds=cartIds.filter(id=>nearestBranch.out_of_stock.includes(id));
  if(!missingIds.length || SELECTED_BRANCH!==nearestBranch.id){host.innerHTML='';return;}
  const names=missingIds.map(id=>{const p=PRODUCTS.find(x=>x.id===id);return p?(CURRENT_LANG==='ar'?p.ar:p.en):id;}).join('، ');
  host.innerHTML=`<div class="stock-alert">
    <h5>${tx('stock_warn_title')}</h5>
    <p>${tx('stock_warn_msg')}<br><b>${names}</b></p>
    <div class="actions">
      <button class="btn-ship-other" onclick="shipFromOtherBranch()">${tx('ship_from_other')}<br><small style="font-weight:400;opacity:.85">${tx('ship_from_other_sub')}</small></button>
      <button class="btn-remove-item" onclick="removeMissingItems(${JSON.stringify(missingIds).replace(/"/g,'&quot;')})">${tx('remove_item')}</button>
    </div>
  </div>`;
}
function shipFromOtherBranch(){
  // Auto-pick a branch that has all the items
  const cartIds=CART.map(c=>c.id);
  const alt=BRANCHES.find(b=>!cartIds.some(id=>b.out_of_stock.includes(id)));
  if(alt){SELECTED_BRANCH=alt.id;SELECTED_SHIPPING='express';renderBranches();renderShippingOptions();}
  else{alert(CURRENT_LANG==='ar'?'لا يوجد فرع متوفر فيه كل المنتجات حالياً':'No branch has all items in stock currently');}
}
function removeMissingItems(ids){
  CART=CART.filter(c=>!ids.includes(c.id));
  saveCart();
  renderBranches();
}
function renderShippingOptions(){
  const host=document.getElementById('ship-list');
  const branch=BRANCHES.find(b=>b.id===SELECTED_BRANCH);
  const mod=branch?.ship_modifier||1;
  host.innerHTML=SHIP_METHODS.map(s=>{
    const isSel=s.id===SELECTED_SHIPPING;
    const adjFee=Math.round(s.sar*mod);
    const fee=s.sar===0?`<span class="ship-opt-fee ship-free">${tx('pickup_free')}</span>`:`<span class="ship-opt-fee">${curSym()} ${formatPrice(adjFee)}${mod>1?` <small style="opacity:.7">(+${Math.round((mod-1)*100)}%)</small>`:''}</span>`;
    return `<div class="ship-opt ${isSel?'selected':''}" onclick="selectShipping('${s.id}')">
      <div class="ship-opt-left"><div class="ico">${s.ico}</div><div><b>${CURRENT_LANG==='ar'?s.ar:s.en}</b><small>${CURRENT_LANG==='ar'?s.etaAr:s.etaEn}</small></div></div>
      ${fee}
    </div>`;
  }).join('')+
    `<div id="checkout-credit-block" style="margin-top:12px"></div>`+
    `<button class="checkout-btn" onclick="completeOrder()" style="margin-top:14px">${tx('checkout')}</button>`;
  renderCheckoutCredit();
}
function renderCheckoutCredit(){
  const host=document.getElementById('checkout-credit-block');
  if(!host)return;
  const bal=getStoreCredit();
  if(bal<=0){host.innerHTML='';return;}
  host.innerHTML=`<label style="display:flex;align-items:center;gap:10px;padding:12px 14px;background:linear-gradient(135deg,#faf5ff,#fdf2f8);border:1.5px solid #ddd6fe;border-radius:10px;cursor:pointer">
    <input type="checkbox" id="use-store-credit" checked style="width:18px;height:18px;accent-color:#7c3aed">
    <div style="flex:1"><b style="font-size:13px;color:#7c3aed">💳 استخدم محفظتي</b><div style="font-size:11px;color:#6b7280;margin-top:2px">رصيدك: <b style="color:#7c3aed">${bal.toFixed(2)} ر.س</b> · سيُخصم تلقائياً من الإجمالي</div></div>
  </label>`;
}
function selectShipping(id){SELECTED_SHIPPING=id;renderShippingOptions();}

function completeOrder(){
  if(!PAYMENT_CHOSEN){alert(tx('choose_payment_alert'));return;}
  if(!SELECTED_BRANCH){alert(tx('choose_branch_alert'));return;}
  const items=CART.reduce((s,c)=>s+c.qty,0);
  const subtotal=CART.reduce((s,c)=>{const p=PRODUCTS.find(x=>x.id===c.id);return s+(p?p.sar*c.qty:0)},0);
  const taxRate=typeof CURRENT_MARKET.tax?.rate==='number'?CURRENT_MARKET.tax.rate:0;
  const shipFee=(SHIP_METHODS.find(s=>s.id===SELECTED_SHIPPING)||{sar:0}).sar*((BRANCHES.find(b=>b.id===SELECTED_BRANCH)?.ship_modifier)||1);
  // Apply Store Credit if customer chose to use it
  const useCredit=document.getElementById('use-store-credit')?.checked;
  const availableCredit=getStoreCredit();
  const gross=subtotal*(1+taxRate/100)+shipFee;
  const creditUsed=useCredit?Math.min(availableCredit,gross):0;
  const total=gross-creditUsed;
  const branch=BRANCHES.find(b=>b.id===SELECTED_BRANCH);
  if(creditUsed>0)deductStoreCredit(creditUsed,'استخدام في طلب جديد');
  saveOrder({
    id:Math.random().toString(36).slice(2,8).toUpperCase(),
    date:new Date().toISOString(),
    items:items,
    cartItems:[...CART], // for reorder
    total:formatPrice(total),
    total_raw:total,
    credit_used:creditUsed,
    currency:curSym(),
    payment:PAYMENT_CHOSEN,
    branch:branch?(CURRENT_LANG==='ar'?branch.ar:branch.en):'',
    shipping:SELECTED_SHIPPING,
    status:'confirmed'
  });
  document.getElementById('checkout-form').style.display='none';
  document.getElementById('checkout-success').style.display='block';
  CART=[];saveCart();
}

// ═══════════════════════ RESERVATION ═══════════════════════
function openReservation(){document.getElementById('resv-modal').classList.add('open')}
function closeReservation(){document.getElementById('resv-modal').classList.remove('open')}
function submitReservation(){
  if(!document.getElementById('rs-name').value){alert(tx('fill_name_alert'));return;}
  alert(tx('booking_ok'));
  closeReservation();
}

function scrollContact(){document.getElementById('contact-section').scrollIntoView({behavior:'smooth'})}

// ═══════════════════════ SEARCH ═══════════════════════
let searchQuery='';
document.getElementById('search').addEventListener('input',e=>{
  searchQuery=e.target.value.trim().toLowerCase();
  if(!searchQuery){renderProducts();return;}
  const matched=PRODUCTS.filter(p=>p.ar.toLowerCase().includes(searchQuery)||p.en.toLowerCase().includes(searchQuery));
  const t=TRANS[CURRENT_LANG]||TRANS.en;
  const grid=document.getElementById('products');
  if(!matched.length){grid.innerHTML=`<div style="grid-column:1/-1;text-align:center;padding:40px 20px;color:#9ca3af"><div style="font-size:48px;margin-bottom:10px">🔍</div><b>${CURRENT_LANG==='ar'?'لا توجد نتائج':'No results found'}</b></div>`;return;}
  grid.innerHTML=matched.map(pCardHtml).join('');
});

// ═══════════════════════ ADMIN MODE + IMAGE STUDIO ═══════════════════════
let STUDIO_MODE='image'; // 'image' | 'video'
let STUDIO_COUNT=1;
let STUDIO_STYLE='white'; // 'white' | 'lifestyle' | 'creative' | 'package'
let STUDIO_ANGLES=new Set(['front','back']);
let STUDIO_LOGO=null;
let STUDIO_BG='white';
let STUDIO_PERSON=false;
let GEN_MULTI=[];
let GEN_VIDEO=null;
const PRODUCT_GALLERIES=JSON.parse(localStorage.getItem('zx_galleries')||'{}');
let LB_CURRENT_PRODUCT=null;
let LB_GALLERY=[];
let LB_INDEX=0;
let _lbAutoAdvance=null;

const VIDEO_SAMPLES=['https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/720/Big_Buck_Bunny_720_10s_1MB.mp4'];

// Style-specific image pools (overrides theme pool when style matches)
// Each style has curated Unsplash photos with the right aesthetic
const STYLE_POOLS={
  white:{
    phone:['https://images.unsplash.com/photo-1511707171634-5f897ff02aa9','https://images.unsplash.com/photo-1592750475338-74b7b21085ab','https://images.unsplash.com/photo-1605236453806-6ff36851218e','https://images.unsplash.com/photo-1574944985070-8f3ebc6b79d2','https://images.unsplash.com/photo-1565849904461-04a58ad377e0','https://images.unsplash.com/photo-1580910051074-3eb694886505'],
    laptop:['https://images.unsplash.com/photo-1496181133206-80ce9b88a853','https://images.unsplash.com/photo-1517336714731-489689fd1ca8','https://images.unsplash.com/photo-1541807084-5c52b6b3adef'],
    watch:['https://images.unsplash.com/photo-1524805444758-089113d48a6d','https://images.unsplash.com/photo-1523275335684-37898b6baf30','https://images.unsplash.com/photo-1495856458515-0637185db551'],
    headphone:['https://images.unsplash.com/photo-1583394838336-acd977736f90','https://images.unsplash.com/photo-1505740420928-5e560c06d30e','https://images.unsplash.com/photo-1546435770-a3e426bf472b','https://images.unsplash.com/photo-1484704849700-f032a568e944','https://images.unsplash.com/photo-1487215078519-e21cc028cb29','https://images.unsplash.com/photo-1599669454699-248893623440'],
    default:['https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da','https://images.unsplash.com/photo-1556909114-f6e7ad7d3136'],
  },
  lifestyle:{
    phone:['https://images.unsplash.com/photo-1573739022854-abceaeb585dc','https://images.unsplash.com/photo-1551316679-9c6ae9dec224','https://images.unsplash.com/photo-1601784551446-20c9e07cdbdb','https://images.unsplash.com/photo-1592934067776-1d8f4a3a2d39','https://images.unsplash.com/photo-1556656793-08538906a9f8'],
    laptop:['https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89','https://images.unsplash.com/photo-1531297484001-80022131f5a1','https://images.unsplash.com/photo-1588872657578-7efd1f1555ed'],
    watch:['https://images.unsplash.com/photo-1547996160-81dfa63595aa','https://images.unsplash.com/photo-1622434641406-a158123450f9','https://images.unsplash.com/photo-1606293459214-69c69d6acaa3'],
    headphone:['https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1','https://images.unsplash.com/photo-1572536147248-ac59a8abfa4b','https://images.unsplash.com/photo-1612444530582-fc66183b16f7','https://images.unsplash.com/photo-1558756520-22cfe5d382ca'],
    default:['https://images.unsplash.com/photo-1483985988355-763728e1935b'],
  },
  creative:{
    phone:['https://images.unsplash.com/photo-1512054502232-10a0a035d672','https://images.unsplash.com/photo-1567581935884-3349723552ca'],
    laptop:['https://images.unsplash.com/photo-1611186871348-b1ce696e52c9'],
    watch:['https://images.unsplash.com/photo-1508057198894-247b23fe5ade','https://images.unsplash.com/photo-1622434641406-a158123450f9'],
    headphone:['https://images.unsplash.com/photo-1546435770-a3e426bf472b','https://images.unsplash.com/photo-1545127398-14699f92334b'],
    default:['https://images.unsplash.com/photo-1611243705797-7b65fefdc111','https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f'],
  },
  package:{
    phone:['https://images.unsplash.com/photo-1605236453806-6ff36851218e','https://images.unsplash.com/photo-1574944985070-8f3ebc6b79d2'],
    headphone:['https://images.unsplash.com/photo-1583394838336-acd977736f90','https://images.unsplash.com/photo-1546435770-a3e426bf472b'],
    watch:['https://images.unsplash.com/photo-1524805444758-089113d48a6d'],
    laptop:['https://images.unsplash.com/photo-1496181133206-80ce9b88a853'],
    default:['https://images.unsplash.com/photo-1607083206325-caf1edba7a83','https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da'],
  },
};

const THEMES=[
  {keys:['ايفون','آيفون','جوال','هاتف','موبايل','iphone','phone','smartphone','mobile'],id:'phone'},
  {keys:['لابتوب','حاسوب','كمبيوتر','laptop','macbook','computer','notebook'],id:'laptop'},
  {keys:['ساعة','watch','clock','timepiece'],id:'watch'},
  {keys:['سماعه','سماعة','سماعات','headphone','earphone','airpods','headset','earbuds'],id:'headphone'},
  {keys:['مكياج','تجميل','makeup','cosmetics','beauty','lipstick'],id:'default'},
  {keys:['أزياء','فستان','ملابس','fashion','dress','clothes','outfit'],id:'default'},
  {keys:['طعام','مأكولات','أكل','food','meal','restaurant'],id:'default'},
  {keys:['ذهب','فاخر','luxury','gold','مجوهرات','jewelry'],id:'default'},
  {keys:['منزل','بيت','تصميم','home','interior','furniture','أثاث'],id:'default'},
];
const MIXED_KEYS=['الكل','all','تشكيلة','collection','mixed','منوعات','متنوع','جميع'];

function setStyle(s){
  STUDIO_STYLE=s;
  document.querySelectorAll('.style-btn').forEach(b=>b.classList.toggle('active',b.dataset.style===s));
  // Auto-set person toggle for lifestyle
  STUDIO_PERSON=(s==='lifestyle');
  document.getElementById('person-toggle').classList.toggle('on',STUDIO_PERSON);
  updateAutoPrompt();
}
function setBg(color){
  STUDIO_BG=color;
  document.querySelectorAll('.bg-swatch').forEach(s=>s.classList.toggle('active',s.dataset.bg===color));
  updateAutoPrompt();
}
function togglePerson(){
  STUDIO_PERSON=!STUDIO_PERSON;
  document.getElementById('person-toggle').classList.toggle('on',STUDIO_PERSON);
  // If person is ON and style is white, auto-switch to lifestyle
  if(STUDIO_PERSON && STUDIO_STYLE==='white')setStyle('lifestyle');
  if(!STUDIO_PERSON && STUDIO_STYLE==='lifestyle')setStyle('white');
  updateAutoPrompt();
}

// Clarification rules: vague brands need a model picker
const CLARIFY_RULES=[
  {test:t=>/iphone|آيفون|ايفون/i.test(t)&&!/(16|17|15|14|pro|max|plus|mini)/i.test(t),title:'أي موديل iPhone؟',titleEn:'Which iPhone model?',options:['iPhone 17 Pro Max','iPhone 17 Pro','iPhone 17','iPhone 16 Pro','iPhone 16','iPhone 15']},
  {test:t=>/galaxy|سامسونج|samsung/i.test(t)&&!/(s24|s25|note|fold|flip|ultra)/i.test(t),title:'أي موديل Samsung؟',titleEn:'Which Samsung model?',options:['Galaxy S25 Ultra','Galaxy S25','Galaxy Z Fold 6','Galaxy Z Flip 6','Galaxy Note Ultra']},
  {test:t=>/^(فستان|dress)$/i.test(t.trim())||(/(فستان|dress)/i.test(t)&&!/(زفاف|سهرة|كاجوال|wedding|evening|casual|maxi|mini)/i.test(t)),title:'أي نوع فستان؟',titleEn:'Which type of dress?',options:['فستان سهرة','فستان زفاف','فستان كاجوال','فستان طويل (Maxi)','فستان قصير (Mini)','فستان عمل']},
  {test:t=>/(لابتوب|laptop|macbook)/i.test(t)&&!/(pro|air|m1|m2|m3|m4|13|14|15|16)/i.test(t),title:'أي موديل لابتوب؟',titleEn:'Which laptop model?',options:['MacBook Pro 16" M4','MacBook Pro 14" M4','MacBook Air 13" M3','Dell XPS 15','Lenovo ThinkPad','ASUS ROG']},
  {test:t=>/(ساعة|watch)/i.test(t)&&!/(apple|rolex|garmin|fitbit|samsung|smart|كلاسيك|رياضية)/i.test(t),title:'أي نوع ساعة؟',titleEn:'Which watch type?',options:['Apple Watch Ultra','Rolex كلاسيكية','ساعة ذكية رياضية','ساعة جلد فاخرة','ساعة معدنية']},
];

let _pendingPrompt=null;
function maybeClarify(prompt){
  const rule=CLARIFY_RULES.find(r=>r.test(prompt));
  if(!rule)return false;
  document.getElementById('clarify-title').textContent=CURRENT_LANG==='ar'?rule.title:(rule.titleEn||rule.title);
  document.getElementById('clarify-question').textContent=CURRENT_LANG==='ar'?'الذكاء الاصطناعي بيشتغل أحسن لو حدّدت بالضبط — اختر:':'AI works best with specifics — pick one:';
  const opts=document.getElementById('clarify-options');
  opts.innerHTML=rule.options.map(o=>`<button class="clarify-opt" onclick="applyClarify('${o.replace(/'/g,"&#39;")}')">${o}</button>`).join('');
  document.getElementById('clarify-overlay').classList.add('open');
  _pendingPrompt=prompt;
  return true;
}
function applyClarify(model){
  const newPrompt=(_pendingPrompt||'')+' — '+model;
  document.getElementById('ai-prompt').value=newPrompt;
  document.getElementById('ai-prompt').dataset.autoFilled='';
  document.getElementById('clarify-overlay').classList.remove('open');
  _pendingPrompt=null;
  // Show a small toast that the AI is "researching"
  toast(CURRENT_LANG==='ar'?'🔍 الذكاء يبحث عن '+model+' …':'🔍 AI is researching '+model+' …');
  // Auto-trigger generation
  setTimeout(()=>runGeneration(),700);
}
function dismissClarify(){
  document.getElementById('clarify-overlay').classList.remove('open');
  if(_pendingPrompt){runGeneration();_pendingPrompt=null;}
}
function toggleAngle(a){
  if(STUDIO_ANGLES.has(a))STUDIO_ANGLES.delete(a);else STUDIO_ANGLES.add(a);
  document.querySelectorAll('.angle-chip').forEach(c=>c.classList.toggle('active',STUDIO_ANGLES.has(c.dataset.a)));
  // sync count with angle selection
  if(STUDIO_ANGLES.size>0 && STUDIO_TARGET.startsWith('product:'))setStudioCount(STUDIO_ANGLES.size);
  updateAutoPrompt();
}
function setStudioMode(m){
  STUDIO_MODE=m;
  document.querySelectorAll('.studio-mode').forEach(el=>el.classList.toggle('active',el.dataset.mode===m));
  document.getElementById('count-row').style.display=m==='image'?'block':'none';
  updateGenButtonLabel();
}
function setStudioCount(n){
  STUDIO_COUNT=n;
  document.querySelectorAll('.count-btn').forEach(b=>b.classList.toggle('active',parseInt(b.dataset.c,10)===n));
  document.getElementById('count-cost').textContent=(n*5)+' '+(CURRENT_LANG==='ar'?'نقاط':'cr');
  updateGenButtonLabel();
}
function updateGenButtonLabel(){
  const label=document.getElementById('gen-btn-label');if(!label)return;
  if(STUDIO_MODE==='video')label.textContent=(CURRENT_LANG==='ar'?'توليد فيديو':'Generate video')+' (15 '+(CURRENT_LANG==='ar'?'نقطة':'cr')+')';
  else{
    const cost=STUDIO_COUNT*5;
    const word=STUDIO_COUNT===1?(CURRENT_LANG==='ar'?'الصورة':'image'):(CURRENT_LANG==='ar'?'صور':'images');
    label.textContent=(CURRENT_LANG==='ar'?`توليد ${STUDIO_COUNT} ${word}`:`Generate ${STUDIO_COUNT} ${word}`)+` (${cost} ${CURRENT_LANG==='ar'?'نقطة':'cr'})`;
  }
}
function updateAutoPrompt(){
  // Smart auto-prompt based on context (target + style + angles + product name)
  const promptEl=document.getElementById('ai-prompt');
  if(!promptEl||promptEl.value.trim()&&promptEl.value!==promptEl.dataset.autoFilled)return;
  let parts=[];
  const styleText={ar:{white:'خلفية بيضاء',lifestyle:'لايف ستايل طبيعي',creative:'إبداعي بإضاءة دراماتيكية',package:'صورة الكرتون'},en:{white:'white background',lifestyle:'lifestyle natural',creative:'creative dramatic lighting',package:'package box'}};
  const angleText={ar:{front:'من الأمام',back:'من الخلف',left:'من اليسار',right:'من اليمين',top:'من فوق',package:'الكرتون',held:'يد تمسكه'},en:{front:'front',back:'back',left:'left side',right:'right side',top:'top',package:'package',held:'held by hand'}};
  if(STUDIO_TARGET.startsWith('product:')){
    const pid=STUDIO_TARGET.split(':')[1];
    const p=PRODUCTS.find(x=>x.id===pid);
    const name=p?(CURRENT_LANG==='ar'?p.ar:p.en):'المنتج';
    parts.push(name);
    if(STUDIO_ANGLES.size&&STUDIO_ANGLES.size<=6){
      const angles=[...STUDIO_ANGLES].map(a=>(angleText[CURRENT_LANG]||angleText.en)[a]).join('، ');
      parts.push(angles);
    }
    parts.push((styleText[CURRENT_LANG]||styleText.en)[STUDIO_STYLE]);
    parts.push(CURRENT_LANG==='ar'?'بإضاءة استوديو احترافية':'professional studio lighting');
  } else if(STUDIO_TARGET.startsWith('cat_icon:')||STUDIO_TARGET.startsWith('cat_banner:')){
    const catId=STUDIO_TARGET.split(':')[1];
    const cat=CATS.find(c=>c.id===catId);
    if(cat)parts.push(CURRENT_LANG==='ar'?cat.ar:cat.en);
    parts.push((styleText[CURRENT_LANG]||styleText.en)[STUDIO_STYLE]);
  } else {
    parts.push((styleText[CURRENT_LANG]||styleText.en)[STUDIO_STYLE]);
  }
  const auto=parts.join(' · ');
  promptEl.value=auto;
  promptEl.dataset.autoFilled=auto;
}
function toggleAdminMode(){
  ADMIN_MODE=!ADMIN_MODE;
  localStorage.setItem('zx_admin',ADMIN_MODE?'1':'0');
  document.body.classList.toggle('admin-mode',ADMIN_MODE);
  const btn=document.getElementById('admin-btn');
  const acpBtn=document.getElementById('acp-open-btn');
  if(btn)btn.style.opacity=ADMIN_MODE?'1':'0.7';
  if(acpBtn)acpBtn.style.display=ADMIN_MODE?'inline-flex':'none';
  toast(ADMIN_MODE?(CURRENT_LANG==='ar'?'♛ وضع التحكم مُفعّل':'♛ Admin mode ON'):(CURRENT_LANG==='ar'?'تم الخروج من التحكم':'Admin mode OFF'));
  renderCategories();
  // Auto-open the admin control panel when enabling admin mode
  if(ADMIN_MODE)setTimeout(openAcp,250);
}
function applyAdminModeOnInit(){
  document.body.classList.toggle('admin-mode',ADMIN_MODE);
  const btn=document.getElementById('admin-btn');
  const acpBtn=document.getElementById('acp-open-btn');
  if(acpBtn)acpBtn.style.display=ADMIN_MODE?'inline-flex':'none';
  if(btn)btn.style.opacity=ADMIN_MODE?'1':'0.7';
}
function onStudioLogoUpload(e){
  const file=e.target.files?.[0];if(!file)return;
  if(file.size>256*1024){alert(CURRENT_LANG==='ar'?'حجم اللوغو كبير':'Logo too big');return;}
  const reader=new FileReader();
  reader.onload=ev=>{
    STUDIO_LOGO=ev.target.result;
    document.getElementById('studio-logo-preview').innerHTML=`<img src="${STUDIO_LOGO}" alt="logo" loading="lazy" decoding="async">`;
    document.getElementById('studio-logo-status').textContent=CURRENT_LANG==='ar'?'✓ سيُضاف اللوغو':'✓ Logo will be added';
  };
  reader.readAsDataURL(file);
}
function openStudio(target){
  STUDIO_TARGET=target;
  GEN_RESULT=null;GEN_MULTI=[];GEN_VIDEO=null;STUDIO_LOGO=null;
  STUDIO_COUNT=1;STUDIO_ANGLES=new Set(['front','back']);
  STUDIO_BG='white';STUDIO_PERSON=false;
  document.getElementById('clarify-overlay')?.classList.remove('open');
  document.getElementById('studio-modal').classList.add('open');
  document.getElementById('zenrex-credits').textContent=ZENREX_CREDITS;
  document.getElementById('ai-prompt').value='';
  document.getElementById('ai-prompt').dataset.autoFilled='';
  document.getElementById('gen-preview').classList.remove('show');
  document.getElementById('gen-loading').classList.remove('show');
  document.getElementById('topup-banner').style.display=ZENREX_CREDITS<5?'flex':'none';
  document.getElementById('studio-logo-preview').innerHTML='🏷️';
  document.getElementById('studio-logo-status').textContent=CURRENT_LANG==='ar'?'يطبع على زاوية الصورة المولّدة':'Will be stamped';
  // Context detection: figure out where the user is editing
  const ctx=document.getElementById('context-text');
  let ctxMsg='';
  let smartStyle='white',smartCount=1,showAngles=false;
  if(target.startsWith('product:')){
    const pid=target.split(':')[1];
    const p=PRODUCTS.find(x=>x.id===pid);
    if(p){
      const catName=CATS.find(c=>c.id===p.cat);
      ctxMsg=(CURRENT_LANG==='ar'?`فهمت السياق: منتج "${p.ar}" في قسم ${catName?catName.ar:''} — موصى به: خلفية بيضاء + ٤ زوايا`:`Context detected: "${p.en}" in ${catName?catName.en:''} — recommended: white BG + 4 angles`);
      smartStyle='white';smartCount=4;showAngles=true;
      STUDIO_ANGLES=new Set(['front','back','right','package']);
    }
  } else if(target==='main_banner'){
    ctxMsg=CURRENT_LANG==='ar'?'فهمت السياق: البنر الرئيسي — موصى به: لايف ستايل + صورة وحدة عريضة':'Context: main banner — lifestyle + 1 wide image';
    smartStyle='lifestyle';smartCount=1;
  } else if(target.startsWith('cat_banner:')){
    const catId=target.split(':')[1];
    const cat=CATS.find(c=>c.id===catId);
    ctxMsg=CURRENT_LANG==='ar'?`فهمت السياق: بنر قسم "${cat?cat.ar:''}" — موصى به: إبداعي`:`Context: category banner "${cat?cat.en:''}" — creative`;
    smartStyle='creative';smartCount=1;
  } else if(target.startsWith('cat_icon:')){
    const catId=target.split(':')[1];
    const cat=CATS.find(c=>c.id===catId);
    ctxMsg=CURRENT_LANG==='ar'?`فهمت السياق: أيقونة قسم "${cat?cat.ar:''}" — موصى به: خلفية بيضاء مربعة`:`Context: category icon — white square`;
    smartStyle='white';smartCount=1;
  }
  ctx.textContent=ctxMsg;
  document.getElementById('angles-section').style.display=showAngles?'block':'none';
  // Apply suggestions
  setStyle(smartStyle);
  setStudioCount(smartCount);
  // Reset bg + person UI
  STUDIO_BG='white';
  document.querySelectorAll('.bg-swatch').forEach(s=>s.classList.toggle('active',s.dataset.bg==='white'));
  document.getElementById('person-toggle').classList.toggle('on',STUDIO_PERSON);
  // sync angle chips
  document.querySelectorAll('.angle-chip').forEach(c=>c.classList.toggle('active',STUDIO_ANGLES.has(c.dataset.a)));
  // Build library tab
  const libKey=target.startsWith('product:')||target.startsWith('cat_icon:')?'product':(target.startsWith('cat_banner:')?'cat_banner':target);
  const lib=STUDIO_LIBRARY[libKey]||STUDIO_LIBRARY.cat_banner;
  document.getElementById('lib-grid').innerHTML=lib.map(u=>`<img src="${u}" onclick="pickFromLibrary('${u}')" alt="library" loading="lazy" decoding="async">`).join('');
  // Show video mode only for banners
  const videoModeEl=document.querySelector('.studio-mode[data-mode="video"]');
  if(videoModeEl)videoModeEl.style.display=(target==='main_banner'||target.startsWith('cat_banner:'))?'block':'none';
  // (Product Info AI panel was moved to Admin Control Panel — see openAcp())
  setStudioMode('image');
  // Generate auto-prompt
  updateAutoPrompt();
  switchStudioTab('ai');
}
function closeStudio(){document.getElementById('studio-modal').classList.remove('open');}
function switchStudioTab(tab){
  document.querySelectorAll('.studio-tab').forEach(t=>t.classList.toggle('active',t.dataset.tab===tab));
  document.querySelectorAll('.studio-section').forEach(s=>s.classList.toggle('active',s.dataset.section===tab));
}
function getTargetSize(target){
  if(target==='main_banner')return{w:1600,h:700,fit:'crop'};
  if(target.startsWith('cat_banner:'))return{w:1600,h:900,fit:'crop'};
  if(target.startsWith('cat_icon:'))return{w:400,h:400,fit:'crop'};
  if(target.startsWith('product:'))return{w:800,h:800,fit:'crop'};
  return{w:1200,h:800,fit:'crop'};
}
function unsplashTransform(baseUrl,size){
  const clean=baseUrl.split('?')[0];
  return `${clean}?w=${size.w}&h=${size.h}&fit=${size.fit}&q=90&auto=format`;
}
// Detect ALL theme IDs in prompt, then pull from STYLE_POOLS[style][themeId]
function detectThemeIds(prompt){
  const lower=prompt.toLowerCase();
  const ids=[];
  THEMES.forEach(t=>{if(t.keys.some(k=>lower.includes(k.toLowerCase())))ids.push(t.id);});
  if(MIXED_KEYS.some(k=>lower.includes(k.toLowerCase()))&&ids.length<2){return['phone','laptop','watch','default'];}
  return ids.length?[...new Set(ids)]:[];
}
function pickVariety(pools,count,seed){
  const out=[];
  if(!pools.length)return out;
  const indices=pools.map(()=>0);
  let p=0,attempts=0;
  while(out.length<count && attempts<count*pools.length*3){
    const pool=pools[p%pools.length];
    if(pool&&pool.length){
      const idx=(seed+indices[p%pools.length])%pool.length;
      const url=pool[idx];
      indices[p%pools.length]++;
      if(!out.includes(url))out.push(url);
    }
    p++;attempts++;
  }
  while(out.length<count && pools[0]&&pools[0].length){
    out.push(pools[0][(seed+out.length)%pools[0].length]);
  }
  return out;
}

function generateAI(){
  const prompt=document.getElementById('ai-prompt').value.trim();
  if(!prompt){alert(CURRENT_LANG==='ar'?'اكتب وصف الصورة':'Describe first');return;}
  if(maybeClarify(prompt))return;
  runGeneration();
}
async function runGeneration(){
  const prompt=document.getElementById('ai-prompt').value.trim();
  const cost=STUDIO_MODE==='video'?15:(STUDIO_COUNT*5);
  if(ZENREX_CREDITS<cost){document.getElementById('topup-banner').style.display='flex';return;}
  document.getElementById('gen-btn').disabled=true;
  document.getElementById('gen-loading').classList.add('show');
  document.getElementById('gen-preview').classList.remove('show');
  document.getElementById('gen-preview-img').style.display='none';
  document.getElementById('gen-preview-video').style.display='none';
  document.getElementById('gen-multi-grid').style.display='none';
  document.getElementById('gen-multi-grid').innerHTML='';
  const size=getTargetSize(STUDIO_TARGET);

  if(STUDIO_MODE==='video'){
    // Video generation still uses sample (no Gemini video API yet)
    setTimeout(()=>{
      document.getElementById('gen-loading').classList.remove('show');
      document.getElementById('gen-preview').classList.add('show');
      GEN_VIDEO=VIDEO_SAMPLES[0];
      const v=document.getElementById('gen-preview-video');
      v.src=GEN_VIDEO;v.style.display='block';v.load();v.play().catch(()=>{});
      document.getElementById('gen-btn').disabled=false;
      ZENREX_CREDITS-=cost;
      localStorage.setItem('zx_credits',String(ZENREX_CREDITS));
      document.getElementById('zenrex-credits').textContent=ZENREX_CREDITS;
    },1500);
    return;
  }

  // ═══ REAL AI: call /api/image-studio/generate (Gemini Nano Banana) ═══
  try {
    const angles=[...STUDIO_ANGLES];
    const res=await fetch(API+'/api/image-studio/generate',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        prompt,
        width:size.w,
        height:size.h,
        count:STUDIO_COUNT,
        style:STUDIO_STYLE,
        bg_color:STUDIO_BG,
        person_holding:STUDIO_PERSON,
        angles:angles.length?angles:undefined,
      })
    });
    if(!res.ok){
      const err=await res.json().catch(()=>({detail:'Network error'}));
      throw new Error(err.detail||'Generation failed');
    }
    const data=await res.json();
    let urls=data.images||[];
    if(STUDIO_LOGO)urls=await Promise.all(urls.map(u=>stampLogo(u,STUDIO_LOGO)));
    GEN_MULTI=urls;GEN_RESULT=urls[0];
    document.getElementById('gen-loading').classList.remove('show');
    document.getElementById('gen-preview').classList.add('show');
    if(STUDIO_COUNT===1){
      const img=document.getElementById('gen-preview-img');
      img.src=urls[0];img.style.display='block';
    } else {
      const grid=document.getElementById('gen-multi-grid');
      grid.style.display='grid';
      grid.innerHTML=urls.map((u,i)=>`<img src="${u}" data-i="${i}" onclick="pickMultiVariant(${i},this)" alt="variant ${i+1}" class="${i===0?'picked':''}" loading="lazy" decoding="async">`).join('');
    }
    ZENREX_CREDITS-=(data.cost||cost);
    localStorage.setItem('zx_credits',String(ZENREX_CREDITS));
    document.getElementById('zenrex-credits').textContent=ZENREX_CREDITS;
  } catch(e) {
    document.getElementById('gen-loading').classList.remove('show');
    alert((CURRENT_LANG==='ar'?'فشل التوليد: ':'Generation failed: ')+e.message);
  } finally {
    document.getElementById('gen-btn').disabled=false;
  }
}
// Apply colored background tint to a white-bg image
function applyBgColor(imgUrl,bgKey){
  const colors={white:'#ffffff',gray:'#e5e7eb',black:'#1a1a1a',beige:'#f5e6d3',gold:'#fbbf24',navy:'#1e3a8a'};
  const bg=colors[bgKey]||'#ffffff';
  return new Promise(resolve=>{
    const img=new Image();img.crossOrigin='anonymous';
    img.onload=()=>{
      const c=document.createElement('canvas');c.width=img.naturalWidth;c.height=img.naturalHeight;
      const ctx=c.getContext('2d');
      // Fill with target color, then draw image with multiply/screen blend for effect
      ctx.fillStyle=bg;ctx.fillRect(0,0,c.width,c.height);
      ctx.globalCompositeOperation='multiply';
      ctx.drawImage(img,0,0);
      ctx.globalCompositeOperation='source-over';
      // Slight overlay for dark bg
      if(bgKey==='black'||bgKey==='navy'){
        ctx.fillStyle='rgba(255,255,255,.1)';ctx.fillRect(0,0,c.width,c.height);
      }
      try{resolve(c.toDataURL('image/jpeg',0.9));}catch(_){resolve(imgUrl);}
    };
    img.onerror=()=>resolve(imgUrl);
    img.src=imgUrl;
  });
}

// ═══════ EXPANDED THEME POOLS (8-12 distinct images per theme for real variety) ═══════
function pickMultiVariant(i,el){
  GEN_RESULT=GEN_MULTI[i];
  document.querySelectorAll('#gen-multi-grid img').forEach(im=>im.classList.remove('picked'));
  el.classList.add('picked');
}
// Stamp company logo on top-right of generated image using canvas
function stampLogo(imgUrl,logoDataUrl){
  return new Promise(resolve=>{
    const img=new Image();img.crossOrigin='anonymous';
    img.onload=()=>{
      const c=document.createElement('canvas');c.width=img.naturalWidth;c.height=img.naturalHeight;
      const ctx=c.getContext('2d');ctx.drawImage(img,0,0);
      const logo=new Image();logo.crossOrigin='anonymous';
      logo.onload=()=>{
        const lw=img.naturalWidth*0.14,lh=lw*(logo.height/logo.width);
        const m=img.naturalWidth*0.03;
        const bx=img.naturalWidth-lw-m,by=m;
        ctx.fillStyle='rgba(255,255,255,.92)';
        const r=12;
        ctx.beginPath();ctx.moveTo(bx+r,by);ctx.lineTo(bx+lw-r,by);ctx.quadraticCurveTo(bx+lw,by,bx+lw,by+r);ctx.lineTo(bx+lw,by+lh-r);ctx.quadraticCurveTo(bx+lw,by+lh,bx+lw-r,by+lh);ctx.lineTo(bx+r,by+lh);ctx.quadraticCurveTo(bx,by+lh,bx,by+lh-r);ctx.lineTo(bx,by+r);ctx.quadraticCurveTo(bx,by,bx+r,by);ctx.fill();
        ctx.drawImage(logo,bx+8,by+4,lw-16,lh-8);
        try{resolve(c.toDataURL('image/jpeg',0.9));}catch(_){resolve(imgUrl);}
      };
      logo.onerror=()=>resolve(imgUrl);
      logo.src=logoDataUrl;
    };
    img.onerror=()=>resolve(imgUrl);
    img.src=imgUrl;
  });
}
function applyGenerated(){
  if(STUDIO_MODE==='video'&&GEN_VIDEO){applyImageOverride(STUDIO_TARGET,GEN_VIDEO,'video');closeStudio();return;}
  if(!GEN_RESULT){alert(CURRENT_LANG==='ar'?'اختر صورة':'Pick an image');return;}
  // If multiple images & product target → add all to gallery; apply selected as main
  if(STUDIO_COUNT>1 && STUDIO_TARGET.startsWith('product:')){
    const pid=STUDIO_TARGET.split(':')[1];
    if(!PRODUCT_GALLERIES[pid])PRODUCT_GALLERIES[pid]=[];
    GEN_MULTI.forEach(u=>{if(u!==GEN_RESULT)PRODUCT_GALLERIES[pid].push({type:'image',url:u});});
    localStorage.setItem('zx_galleries',JSON.stringify(PRODUCT_GALLERIES));
    toast(CURRENT_LANG==='ar'?`✨ تم تطبيق المختارة وإضافة ${GEN_MULTI.length-1} للمعرض`:`✨ Applied + ${GEN_MULTI.length-1} saved to gallery`);
  }
  applyImageOverride(STUDIO_TARGET,GEN_RESULT);
  closeStudio();
}
function onStudioUpload(e){
  const file=e.target.files?.[0];if(!file)return;
  if(file.size>2*1024*1024){alert(CURRENT_LANG==='ar'?'الصورة كبيرة (٢ ميجابايت)':'Image too big (2MB)');return;}
  const reader=new FileReader();
  reader.onload=ev=>{applyImageOverride(STUDIO_TARGET,ev.target.result);closeStudio();};
  reader.readAsDataURL(file);
}
function pickFromLibrary(url){applyImageOverride(STUDIO_TARGET,url);closeStudio();}
function topupCredits(){
  ZENREX_CREDITS+=100;
  localStorage.setItem('zx_credits',String(ZENREX_CREDITS));
  document.getElementById('zenrex-credits').textContent=ZENREX_CREDITS;
  document.getElementById('topup-banner').style.display='none';
  alert(CURRENT_LANG==='ar'?'✓ تم شحن ١٠٠ نقطة (محاكاة - في الإنتاج عبر Stripe)':'✓ +100 credits (mocked Stripe)');
}
function applyImageOverride(target,url,type){
  IMG_OVERRIDES[target]={url,type:type||'image'};
  localStorage.setItem('zx_img_overrides',JSON.stringify(IMG_OVERRIDES));
  if(target==='main_banner'){
    const stack=document.getElementById('banner-img-stack');
    if(stack){
      if(type==='video'){stack.innerHTML='';const v=document.getElementById('banner-video');v.src=url;v.style.opacity='1';v.load();v.play().catch(()=>{});}
      else{stack.innerHTML=`<img src="${url}" alt="banner" style="opacity:1;animation:bnr-fade 18s linear infinite" loading="lazy" decoding="async">`;}
    }
  } else if(target.startsWith('cat_banner:')){
    document.getElementById('cat-banner-img').src=url;
  } else if(target.startsWith('cat_icon:')){
    renderCategories();
  } else if(target.startsWith('product:')){
    const id=target.split(':')[1];
    const p=PRODUCTS.find(x=>x.id===id);if(p)p.img=url;
    // Also add as first gallery entry
    if(!PRODUCT_GALLERIES[id])PRODUCT_GALLERIES[id]=[];
    PRODUCT_GALLERIES[id].unshift({type:type||'image',url});
    localStorage.setItem('zx_galleries',JSON.stringify(PRODUCT_GALLERIES));
    renderProducts();
    if(document.getElementById('view-category').style.display==='block')renderCategoryPage(activeCat);
  }
  toast(CURRENT_LANG==='ar'?'✨ تم تطبيق الصورة الجديدة':'✨ Image applied');
}
// Build product card HTML (with hover-rotate gallery)
function pCardHtml(p){
  const name=CURRENT_LANG==='ar'?p.ar:p.en;
  const desc=CURRENT_LANG==='ar'?(p.descAr||''):(p.descEn||'');
  const gallery=(PRODUCT_GALLERIES[p.id]||[{type:'image',url:p.img}]).filter(g=>g.type==='image').slice(0,5);
  const imgs=gallery.length?gallery:[{url:p.img}];
  const FALLBACK_IMG='https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600';
  const stack=imgs.map((g,i)=>`<img src="${g.url||FALLBACK_IMG}" alt="${name} ${i+1}" class="${i===0?'active':''}" data-i="${i}" onerror="this.onerror=null;this.src='${FALLBACK_IMG}'" loading="lazy" decoding="async">`).join('');
  const dots=imgs.length>1?`<div class="p-card-dots">${imgs.map((_,i)=>`<span class="${i===0?'active':''}"></span>`).join('')}</div>`:'';
  const navs=imgs.length>1?`<button class="p-card-nav p-card-prev" onclick="event.stopPropagation();pCardNav(this,-1)" aria-label="prev">‹</button><button class="p-card-nav p-card-next" onclick="event.stopPropagation();pCardNav(this,1)" aria-label="next">›</button>`:'';
  const isAI=p.isAI||p.cat==='ai_services';
  const aiBadge=isAI?`<div class="ai-badge">✨ AI · ${p.credits||p.sar} نقطة</div>`:'';
  const priceLabel=isAI?`⭐ ${p.credits||p.sar} <small style="font-size:9px;opacity:.85">نقطة</small>`:`${curSym()} ${formatPrice(p.sar)}`;
  // Branch stock check
  const currentBranch=BRANCHES.find(b=>b.id===SELECTED_BRANCH);
  const isOOS=currentBranch&&currentBranch.out_of_stock?.includes(p.id);
  // Find nearest branch with stock if OOS
  let altBranch=null,altDist=null;
  if(isOOS){
    const withStock=BRANCHES.filter(b=>!b.out_of_stock?.includes(p.id));
    if(withStock.length&&USER_LOCATION){
      const sorted=withStock.map(b=>({...b,d:haversineKm(USER_LOCATION.lat,USER_LOCATION.lng,b.lat,b.lng)})).sort((a,b)=>a.d-b.d);
      altBranch=sorted[0];altDist=sorted[0].d;
    }else if(withStock.length){altBranch=withStock[0];}
  }
  const oosBadge=isOOS?`<div style="position:absolute;top:8px;${CURRENT_LANG==='ar'?'left':'right'}:8px;background:rgba(220,38,38,.95);color:#fff;padding:3px 8px;border-radius:99px;font-size:9px;font-weight:900;z-index:7;backdrop-filter:blur(4px)">⚠️ نافد بفرعك</div>`:'';
  const oosFooter=isOOS&&altBranch?`<div onclick="event.stopPropagation();selectBranchAndClose('${altBranch.id}')" style="background:linear-gradient(135deg,#fef3c7,#fde68a);color:#92400e;padding:6px 8px;font-size:10px;font-weight:700;text-align:center;cursor:pointer;border-top:1px solid #fde68a">📍 متوفر بـ <b>${CURRENT_LANG==='ar'?altBranch.ar:altBranch.en}</b>${altDist?` · ${altDist.toFixed(1)} كم`:''} · انقر للتبديل ←</div>`:'';
  return `<div class="p-card ${isAI?'ai-service':''}" onmouseenter="pCardHover(this,true)" onmouseleave="pCardHover(this,false)" onclick="if(!event.target.closest('.add-btn,.p-card-nav,.wish-heart,img'))showProductDetail('${p.id}')">
    <div class="editable-img-host">${aiBadge}${oosBadge}<div class="p-card-stack" data-pid="${p.id}">${stack}</div>${dots}${navs}<button class="wish-heart ${inWish(p.id)?'active':''}" data-testid="wish-toggle-${p.id}" onclick="event.stopPropagation();toggleWish('${p.id}')" title="المفضلة">${inWish(p.id)?'❤':'🤍'}</button></div>
    <div class="p-info" onclick="event.stopPropagation();showProductDetail('${p.id}')" style="cursor:pointer"><div class="name">${name}</div><div class="desc">${desc}</div><div class="p-row"><div class="p-price">${priceLabel}</div><button class="add-btn" onclick="event.stopPropagation();addToCart('${p.id}')" title="${isAI?'اشترِ بالنقاط':isOOS?'غير متوفر':'أضف للسلة'}" ${isOOS?'style="background:#9ca3af;cursor:not-allowed"':''}>${isAI?'⭐':isOOS?'✕':'+'}</button></div></div>
    ${oosFooter}
  </div>`;
}
// Hover auto-rotate logic
const _pCardTimers=new WeakMap();
function pCardHover(card,enter){
  const stack=card.querySelector('.p-card-stack');
  if(!stack)return;
  const imgs=stack.querySelectorAll('img');
  if(imgs.length<2)return;
  if(enter){
    if(_pCardTimers.get(card))return;
    let i=0;
    const t=setInterval(()=>{
      i=(i+1)%imgs.length;
      imgs.forEach((im,k)=>im.classList.toggle('active',k===i));
      card.querySelectorAll('.p-card-dots span').forEach((d,k)=>d.classList.toggle('active',k===i));
    },1200);
    _pCardTimers.set(card,t);
  } else {
    const t=_pCardTimers.get(card);if(t){clearInterval(t);_pCardTimers.delete(card);}
    imgs.forEach((im,k)=>im.classList.toggle('active',k===0));
    card.querySelectorAll('.p-card-dots span').forEach((d,k)=>d.classList.toggle('active',k===0));
  }
}
function pCardNav(btn,dir){
  const card=btn.closest('.p-card');
  const imgs=card.querySelectorAll('.p-card-stack img');
  let cur=Array.from(imgs).findIndex(im=>im.classList.contains('active'));
  if(cur<0)cur=0;
  cur=(cur+dir+imgs.length)%imgs.length;
  imgs.forEach((im,k)=>im.classList.toggle('active',k===cur));
  card.querySelectorAll('.p-card-dots span').forEach((d,k)=>d.classList.toggle('active',k===cur));
}

// ═══════════════════════ PRODUCT DETAIL PAGE ═══════════════════════
let _pdIndex=0;
function showProductDetail(pid){
  const p=PRODUCTS.find(x=>x.id===pid);
  if(!p)return;
  const name=CURRENT_LANG==='ar'?p.ar:p.en;
  const desc=CURRENT_LANG==='ar'?(p.descAr||''):(p.descEn||'');
  const gallery=(PRODUCT_GALLERIES[pid]||[{type:'image',url:p.img}]).filter(g=>g.type==='image');
  _pdIndex=0;
  const heroImg=document.getElementById('pd-hero-img');
  heroImg.src=gallery[0].url;
  heroImg.onclick=()=>openLightbox(gallery[0].url,pid);
  document.getElementById('pd-thumbs').innerHTML=gallery.map((g,i)=>`<img src="${g.url}" class="${i===0?'active':''}" onclick="pdJump(${i},'${pid}')" alt="" loading="lazy" decoding="async">`).join('');
  document.getElementById('pd-title').textContent=name;
  document.getElementById('pd-tagline').textContent=desc;
  document.getElementById('pd-price').textContent=curSym()+' '+formatPrice(p.sar);
  document.getElementById('pd-add-btn').onclick=()=>{addToCart(pid);toast(CURRENT_LANG==='ar'?'✓ تمت الإضافة للسلة':'✓ Added');};
  const subBtn=document.getElementById('pd-subscribe-btn');
  if(subBtn){
    // Only show subscribe for non-AI physical products
    if(p.isAI||p.cat==='ai_services'){subBtn.style.display='none';}
    else{subBtn.style.display='';subBtn.onclick=()=>{subscribeToProduct(pid);};}
  }
  document.getElementById('pd-edit-btn').onclick=(e)=>{e.stopPropagation();openStudio('product:'+pid);};
  // Load product reviews
  loadProductReviews(pid);
  const info=PRODUCT_INFO[pid];
  // Use rich builder if any of the new deep fields exist; fallback to legacy html
  const hasRichFields = info && (
    (info.features && info.features.length) ||
    (info.benefits && info.benefits.length) ||
    (info.usage_instructions && info.usage_instructions.length) ||
    (info.whats_new && info.whats_new.length) ||
    (info.side_effects && info.side_effects.length) ||
    (info.comparison && (info.comparison.previous_model || (info.comparison.key_differences||[]).length)) ||
    (info.specs && Object.keys(info.specs).length)
  );
  const html = hasRichFields ? buildRichAnalysisClientHTML(info) : info?.html;
  // Render variants (colors / sizes / warranty)
  const vWrap=document.getElementById('pd-variants');
  if(info && (info.colors?.length || info.sizes?.length || info.warranty?.duration_text)){
    let html2='';
    if(info.colors?.length){
      const labelColor=CURRENT_LANG==='ar'?'اللون':'Color';
      html2+=`<div class="pdp-var-row"><b>${labelColor}: <span id="pd-color-label" style="font-weight:400;color:#6b7280">${info.colors[0].name||''}</span></b><div class="pdp-colors">`+
        info.colors.map((c,i)=>`<div class="pdp-color ${i===0?'active':''}" style="background:${c.hex||'#888'}" data-name="${c.name||''}" onclick="pdPickColor(this)" title="${c.name||''}"></div>`).join('')+'</div></div>';
    }
    if(info.sizes?.length){
      const labelSize=CURRENT_LANG==='ar'?'المقاس / السعة':'Size / Capacity';
      html2+=`<div class="pdp-var-row"><b>${labelSize}:</b><div class="pdp-sizes">`+
        info.sizes.map((s,i)=>`<button class="pdp-size ${i===0?'active':''}" onclick="pdPickSize(this)">${s}</button>`).join('')+'</div></div>';
    }
    if(info.warranty?.duration_text){
      const labelW=CURRENT_LANG==='ar'?'🛡️ الضمان':'🛡️ Warranty';
      html2+=`<div class="pdp-var-row"><b>${labelW}:</b><div class="pdp-warranty">${info.warranty.duration_text}${info.warranty.url?` · <a href="${info.warranty.url}" target="_blank">${CURRENT_LANG==='ar'?'تفاصيل الضمان الرسمي ↗':'Official warranty ↗'}</a>`:''}</div></div>`;
    }
    vWrap.innerHTML=html2;
    vWrap.style.display='block';
  } else { vWrap.style.display='none'; }
  document.getElementById('pd-info').innerHTML=html||`<div class="pd-empty">${CURRENT_LANG==='ar'?'ℹ️ التاجر لم يضف تفاصيل تفصيلية لهذا المنتج بعد.':'ℹ️ The merchant has not added detailed info for this product yet.'}</div>`;
  // Add "Ask Zenrex AI" CTA in product detail
  const askCta=document.createElement('div');
  askCta.style.cssText='background:linear-gradient(135deg,#faf5ff,#fdf2f8);border:2px dashed #7c3aed;border-radius:14px;padding:16px;margin:14px 0;text-align:center;cursor:pointer;transition:transform .2s';
  askCta.onmouseenter=()=>askCta.style.transform='scale(1.02)';
  askCta.onmouseleave=()=>askCta.style.transform='scale(1)';
  askCta.onclick=()=>{openAiAssistant();setTimeout(()=>{document.getElementById('ai-input').value='قارن هذا المنتج مع منتجات مشابهة';aiAskCustomer('قارن هذا المنتج مع منتجات مشابهة');},300);};
  askCta.innerHTML='<div style="font-size:24px;margin-bottom:6px">✨</div><b style="font-size:14px;color:#7c3aed">تردد في الشراء؟ اسأل Zenrex AI</b><div style="font-size:11px;color:#6b7280;margin-top:4px;line-height:1.6">قارن مع منتجات مشابهة · اطّلع على تجارب العملاء · احصل على توصية فورية</div><div style="margin-top:8px;background:#7c3aed;color:#fff;padding:8px 16px;border-radius:99px;font-size:11px;font-weight:900;display:inline-block">💬 اسأل الآن (مجاناً أول مرة)</div>';
  document.getElementById('pd-info').appendChild(askCta);
  renderProductReviews(pid);
  showView('product');
  window.scrollTo({top:0,behavior:'smooth'});
}
function buildRichAnalysisClientHTML(d){
  if(!d)return '';
  const L=CURRENT_LANG==='ar';
  let html='';
  if(d.target_audience){html+=`<div class="pdai-audience">👥 <b>${L?'الفئة المستهدفة:':'For:'}</b> ${d.target_audience}</div>`;}
  if(d.whats_new&&d.whats_new.length){html+=`<div class="pdai-card"><h3><span class="ic" style="background:#fef2f2;color:#f43f5e">🆕</span> ${L?'الجديد في هذا الإصدار':"What's new"}</h3><div class="pdai-list-rose">${d.whats_new.map(w=>`<div class="it">⚡ ${w}</div>`).join('')}</div></div>`;}
  if(d.comparison&&(d.comparison.previous_model||(d.comparison.key_differences&&d.comparison.key_differences.length))){html+=`<div class="pdai-card"><h3><span class="ic" style="background:#fdf4ff;color:#a855f7">⚖️</span> ${L?'المقارنة مع':'Compared to'} ${d.comparison.previous_model||(L?'السابق':'previous')}</h3><div class="pdai-comp">${(d.comparison.key_differences||[]).map(k=>`<div class="diff">▸ ${k}</div>`).join('')}${(d.comparison.upgrades||[]).length?`<div class="upgrades"><b>🚀 ${L?'ترقيات أساسية':'Key upgrades'}</b>${d.comparison.upgrades.map(u=>`<div class="up">✓ ${u}</div>`).join('')}</div>`:''}</div></div>`;}
  if(d.features&&d.features.length){html+=`<div class="pdai-card"><h3><span class="ic" style="background:#faf5ff;color:#7c3aed">✦</span> ${L?'المميزات الرئيسية':'Key features'} (${d.features.length})</h3><div class="pdai-features">${d.features.map(f=>`<span class="chip">✦ ${f}</span>`).join('')}</div></div>`;}
  if(d.benefits&&d.benefits.length){html+=`<div class="pdai-card"><h3><span class="ic" style="background:#f0fdf4;color:#10b981">💚</span> ${L?'الفوائد':'Benefits'}</h3><div class="pdai-list-green">${d.benefits.map(b=>`<div class="it">💚 ${b}</div>`).join('')}</div></div>`;}
  if(d.usage_instructions&&d.usage_instructions.length){html+=`<div class="pdai-card"><h3><span class="ic" style="background:#ecfeff;color:#06b6d4">📋</span> ${L?'طريقة الاستخدام':'How to use'}</h3><div class="pdai-steps">${d.usage_instructions.map((u,i)=>`<div class="step"><span class="num">${i+1}</span><span>${u}</span></div>`).join('')}</div></div>`;}
  if(d.side_effects&&d.side_effects.length){html+=`<div class="pdai-card"><h3><span class="ic" style="background:#fffbeb;color:#f59e0b">⚠️</span> ${L?'تحذيرات وآثار جانبية':'Warnings & side effects'}</h3><div class="pdai-list-amber">${d.side_effects.map(s=>`<div class="it">⚠ ${s}</div>`).join('')}</div></div>`;}
  if(d.specs&&Object.keys(d.specs).length){html+=`<div class="pdai-card"><h3><span class="ic" style="background:#f3f4f6;color:#374151">🔧</span> ${L?'المواصفات التقنية':'Technical specs'}</h3><div class="pdai-specs">${Object.entries(d.specs).map(([k,v])=>`<div class="pdai-spec"><b>${k}</b><span>${v}</span></div>`).join('')}</div></div>`;}
  if(d.official_url){const u=d.official_url.startsWith('http')?d.official_url:'https://'+d.official_url;html+=`<div class="pdai-card"><h3><span class="ic" style="background:#faf5ff;color:#7c3aed">🌐</span> ${L?'الموقع الرسمي':'Official site'}</h3><a class="pdai-link" href="${u}" target="_blank">${d.official_url} ↗</a></div>`;}
  return html;
}
function pdJump(i,pid){
  _pdIndex=i;
  const gallery=(PRODUCT_GALLERIES[pid]||[]).filter(g=>g.type==='image');
  if(!gallery[i])return;
  const heroImg=document.getElementById('pd-hero-img');
  heroImg.src=gallery[i].url;
  heroImg.onclick=()=>openLightbox(gallery[i].url,pid);
  document.querySelectorAll('#pd-thumbs img').forEach((im,k)=>im.classList.toggle('active',k===i));
}
function pdPickColor(el){
  document.querySelectorAll('.pdp-color').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('pd-color-label').textContent=el.dataset.name||'';
  // Cycle through gallery image to suggest variant change (visual feedback)
  const idx=Array.from(el.parentNode.children).indexOf(el);
  const gallery=document.querySelectorAll('#pd-thumbs img');
  if(gallery[idx])gallery[idx].click();
}
function pdPickSize(el){
  document.querySelectorAll('.pdp-size').forEach(s=>s.classList.remove('active'));
  el.classList.add('active');
}



// ═══════════════════════ AI PRODUCT INFO (research + fill) ═══════════════════════
const PRODUCT_INFO=JSON.parse(localStorage.getItem('zx_product_info')||'{}');
async function aiFillProductInfo(){
  if(!STUDIO_TARGET.startsWith('product:'))return;
  const pid=STUDIO_TARGET.split(':')[1];
  const p=PRODUCTS.find(x=>x.id===pid);
  const name=document.getElementById('info-name').value.trim()||(p?(CURRENT_LANG==='ar'?p.ar:p.en):'');
  const url=document.getElementById('info-url').value.trim();
  if(!name){alert(CURRENT_LANG==='ar'?'اكتب اسم المنتج':'Enter product name');return;}
  if(ZENREX_CREDITS<10){document.getElementById('topup-banner').style.display='flex';return;}
  const btn=document.getElementById('info-fill-btn');btn.disabled=true;btn.innerHTML='⏳ '+(CURRENT_LANG==='ar'?'الذكاء يبحث في الإنترنت…':'AI researching…');
  const result=document.getElementById('info-result');result.classList.remove('show');
  try{
    const res=await fetch(API+'/api/image-studio/product-info',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name,official_url:url||undefined,image_base64:p?.img&&p.img.startsWith('data:')?p.img:undefined,lang:CURRENT_LANG})
    });
    if(!res.ok){const e=await res.json().catch(()=>({detail:'Network error'}));throw new Error(e.detail||'Failed');}
    const data=await res.json();
    // Save to product info store + update product fields
    PRODUCT_INFO[pid]=data;
    try{localStorage.setItem('zx_product_info',JSON.stringify(PRODUCT_INFO));}catch(_){}
    if(p){
      if(CURRENT_LANG==='ar'){p.ar=data.title;p.descAr=data.description;}else{p.en=data.title;p.descEn=data.description;}
    }
    // Render result preview
    result.innerHTML=`<h5>${data.title}</h5><div class="desc">${data.description}</div>`+(data.features.length?`<b style="font-size:11px;color:#7c3aed">المميزات:</b><ul>${data.features.map(f=>`<li>${f}</li>`).join('')}</ul>`:'')+(Object.keys(data.specs).length?`<b style="font-size:11px;color:#7c3aed">المواصفات:</b><div class="specs">${Object.entries(data.specs).map(([k,v])=>`<div><b>${k}</b>${v}</div>`).join('')}</div>`:'');
    result.classList.add('show');
    ZENREX_CREDITS-=(data.cost||10);
    localStorage.setItem('zx_credits',String(ZENREX_CREDITS));
    document.getElementById('zenrex-credits').textContent=ZENREX_CREDITS;
    renderProducts();
    if(document.getElementById('view-category').style.display==='block')renderCategoryPage(activeCat);
    toast(CURRENT_LANG==='ar'?'✓ تم تعبئة المعلومات تلقائياً':'✓ Info filled');
  }catch(e){
    alert((CURRENT_LANG==='ar'?'فشل البحث: ':'Failed: ')+e.message);
  }finally{
    btn.disabled=false;btn.innerHTML='🤖 '+(CURRENT_LANG==='ar'?'ابحث وعبّي المعلومات تلقائياً':'Research & auto-fill');
  }
}

// ═══════════════════════ SAVED IMAGES LIBRARY ═══════════════════════
const SAVED_IMAGES=JSON.parse(localStorage.getItem('zx_saved_images')||'[]');
function saveCurrentImage(){
  if(!GEN_RESULT){alert(CURRENT_LANG==='ar'?'ولّد صورة أولاً':'Generate first');return;}
  const item={id:'s_'+Date.now(),url:GEN_RESULT,prompt:document.getElementById('ai-prompt').value.trim().slice(0,80),target:STUDIO_TARGET,savedAt:Date.now()};
  if(STUDIO_COUNT>1 && GEN_MULTI.length){
    GEN_MULTI.forEach((u,i)=>{
      if(u===GEN_RESULT){SAVED_IMAGES.unshift({...item,url:u});return;}
      SAVED_IMAGES.unshift({...item,id:'s_'+Date.now()+'_'+i,url:u});
    });
  } else SAVED_IMAGES.unshift(item);
  while(SAVED_IMAGES.length>30)SAVED_IMAGES.pop();
  try{localStorage.setItem('zx_saved_images',JSON.stringify(SAVED_IMAGES));}catch(_){toast(CURRENT_LANG==='ar'?'مساحة التخزين ممتلئة':'Storage full');return;}
  toast(CURRENT_LANG==='ar'?'💾 تم حفظ الصورة في مكتبتك':'💾 Image saved to library');
}
function renderSavedImages(){
  const host=document.getElementById('saved-grid');
  const empty=document.getElementById('saved-empty');
  if(!host)return;
  if(!SAVED_IMAGES.length){host.innerHTML='';if(empty)empty.style.display='block';return;}
  if(empty)empty.style.display='none';
  host.innerHTML=SAVED_IMAGES.map(s=>`<div class="saved-card" onclick="applySavedImage('${s.id}')"><img src="${s.url}" alt="" loading="lazy" decoding="async"><button class="del" onclick="event.stopPropagation();deleteSavedImage('${s.id}')">✕</button><div class="meta">${(s.prompt||'').slice(0,40)}</div></div>`).join('');
}
function applySavedImage(id){
  const item=SAVED_IMAGES.find(s=>s.id===id);
  if(!item)return;
  applyImageOverride(STUDIO_TARGET,item.url);
  closeStudio();
}
function deleteSavedImage(id){
  const idx=SAVED_IMAGES.findIndex(s=>s.id===id);
  if(idx>=0){SAVED_IMAGES.splice(idx,1);localStorage.setItem('zx_saved_images',JSON.stringify(SAVED_IMAGES));renderSavedImages();}
}

// ═══════════════════════ ADD-PRODUCT (now routes through Admin Control Panel) ═══════════════════════
function startAddProduct(catId){
  // Open the Admin Control Panel pre-filled to add a new product in this category.
  openAcp();
  switchAcpTab('products');
  acpResetForm();
  // pre-select category
  const sel=document.getElementById('acp-pcat');
  if(sel&&[...sel.options].some(o=>o.value===catId))sel.value=catId;
  document.getElementById('acp-product-form').style.display='block';
  ACP_EDITING_PID=null;
}

// ═══════════════════════ DEFAULT MULTI-IMAGE GALLERIES ═══════════════════════
function ensureDefaultGalleries(){
  const variantPool={
    electronics:['https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=800&q=85','https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=800&q=85','https://images.unsplash.com/photo-1574944985070-8f3ebc6b79d2?w=800&q=85'],
    fashion:['https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800&q=85','https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=800&q=85','https://images.unsplash.com/photo-1551232864-3f0890e580d9?w=800&q=85'],
    beauty:['https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=800&q=85','https://images.unsplash.com/photo-1522335789203-aaa2f8be5419?w=800&q=85','https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=800&q=85'],
    home:['https://images.unsplash.com/photo-1618220179428-22790b461013?w=800&q=85','https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&q=85','https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800&q=85'],
  };
  PRODUCTS.forEach(p=>{
    if(PRODUCT_GALLERIES[p.id]&&PRODUCT_GALLERIES[p.id].length>1)return;
    const pool=variantPool[p.cat]||variantPool.home;
    PRODUCT_GALLERIES[p.id]=[{type:'image',url:p.img}].concat(pool.slice(0,3).map(u=>({type:'image',url:u})));
  });
  try{localStorage.setItem('zx_galleries',JSON.stringify(PRODUCT_GALLERIES));}catch(_){}
}


// ═══════════════════════ ADMIN CONTROL PANEL (ACP) ═══════════════════════
let ACP_EDITING_PID=null;
let ACP_AI_DATA=null;
function openAcp(){
  document.getElementById('acp-modal').classList.add('open');
  syncCreditsDisplay();
  acpRenderProductGrid();
  vsPopulateProductSelect();
}
function closeAcp(){document.getElementById('acp-modal').classList.remove('open');}
function switchAcpTab(tab){
  document.querySelectorAll('.acp-tab').forEach(t=>t.classList.toggle('active',t.dataset.tab===tab));
  document.querySelectorAll('.acp-section').forEach(s=>s.classList.toggle('active',s.dataset.section===tab));
  if(tab==='delivery')dlvLoadAll();
  if(tab==='payroll')prInit();
  if(tab==='gateways')gwInit();
}
function syncCreditsDisplay(){
  const el=document.getElementById('acp-credits-value');if(el)el.textContent=ZENREX_CREDITS;
  const e2=document.getElementById('zenrex-credits');if(e2)e2.textContent=ZENREX_CREDITS;
}
function acpRenderProductGrid(){
  const grid=document.getElementById('acp-product-grid');
  if(!grid)return;
  const recent=PRODUCTS.slice(0,7);
  grid.innerHTML=`<div class="acp-pcard adding" onclick="acpStartNewProduct()"><div class="plus">＋</div><b style="font-size:11px">منتج جديد</b></div>`+
    recent.map(p=>`<div class="acp-pcard" onclick="acpEditProduct('${p.id}')"><img src="${p.img}" alt="" loading="lazy" decoding="async"><div class="nm">${(CURRENT_LANG==='ar'?p.ar:p.en).slice(0,30)}</div></div>`).join('');
}
function acpStartNewProduct(){
  acpResetForm();
  ACP_EDITING_PID=null;
  document.getElementById('acp-product-form').style.display='block';
}
function acpEditProduct(pid){
  const p=PRODUCTS.find(x=>x.id===pid);
  if(!p)return;
  ACP_EDITING_PID=pid;
  document.getElementById('acp-pname').value=CURRENT_LANG==='ar'?p.ar:p.en;
  document.getElementById('acp-pprice').value=p.sar||'';
  document.getElementById('acp-pcat').value=p.cat||'electronics';
  document.getElementById('acp-pdesc').value=CURRENT_LANG==='ar'?(p.descAr||''):(p.descEn||'');
  document.getElementById('acp-purl').value='';
  document.getElementById('acp-ai-result').classList.remove('show');
  document.getElementById('acp-product-form').style.display='block';
}
function acpResetForm(){
  ['acp-pname','acp-pprice','acp-purl','acp-pdesc'].forEach(id=>{const el=document.getElementById(id);if(el)el.value='';});
  ACP_EDITING_PID=null;ACP_AI_DATA=null;
  const r=document.getElementById('acp-ai-result');if(r)r.classList.remove('show');
  document.getElementById('acp-product-form').style.display='none';
}
function acpOpenImagesForCurrent(){
  // Ensure product exists (create on-the-fly if new), then open image studio for it.
  let pid=ACP_EDITING_PID;
  if(!pid){
    const name=document.getElementById('acp-pname').value.trim();
    if(!name){alert(CURRENT_LANG==='ar'?'اكتب اسم المنتج أولاً':'Enter product name first');return;}
    pid=acpCommitProduct();
  } else {
    acpCommitProduct();
  }
  openStudio('product:'+pid);
}
function acpCommitProduct(){
  const name=document.getElementById('acp-pname').value.trim()||'منتج جديد';
  const price=parseFloat(document.getElementById('acp-pprice').value||'0')||0;
  const cat=document.getElementById('acp-pcat').value||'electronics';
  const desc=document.getElementById('acp-pdesc').value.trim();
  if(ACP_EDITING_PID){
    const p=PRODUCTS.find(x=>x.id===ACP_EDITING_PID);
    if(p){
      if(CURRENT_LANG==='ar'){p.ar=name;p.descAr=desc;}else{p.en=name;p.descEn=desc;}
      p.sar=price;p.cat=cat;
    }
    return ACP_EDITING_PID;
  }
  const newId='custom_'+Date.now();
  PRODUCTS.unshift({id:newId,cat:cat,ar:name,en:name,descAr:desc,descEn:desc,sar:price,img:'https://via.placeholder.com/800x800/ede9fe/7c3aed?text=%E2%9C%A8'});
  ACP_EDITING_PID=newId;
  return newId;
}
function acpSaveProduct(){
  if(!document.getElementById('acp-pname').value.trim()){alert(CURRENT_LANG==='ar'?'اكتب اسم المنتج':'Enter product name');return;}
  const pid=acpCommitProduct();
  renderProducts();
  const catView=document.getElementById('view-category');
  if(catView&&catView.style.display==='block')renderCategoryPage(activeCat);
  acpRenderProductGrid();
  toast(CURRENT_LANG==='ar'?'✓ تم حفظ المنتج':'✓ Product saved');
}
async function acpAiFillProduct(){
  const name=document.getElementById('acp-pname').value.trim();
  if(!name){alert(CURRENT_LANG==='ar'?'اكتب اسم المنتج أولاً':'Enter product name first');return;}
  if(ZENREX_CREDITS<10){openRecharge();return;}
  const btn=document.getElementById('acp-ai-btn');
  btn.disabled=true;
  const originalHTML=btn.innerHTML;
  btn.innerHTML='⏳ <span>الذكاء يبحث في الإنترنت…</span>';
  try{
    const res=await fetch(API+'/api/image-studio/product-info',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name,official_url:document.getElementById('acp-purl').value.trim()||undefined,lang:CURRENT_LANG})
    });
    if(!res.ok)throw new Error((await res.json().catch(()=>({}))).detail||'AI failed');
    const data=await res.json();
    ACP_AI_DATA=data;
    // Auto-fill form fields
    document.getElementById('acp-pname').value=data.title||name;
    document.getElementById('acp-pdesc').value=data.description||'';
    // Render rich preview
    const r=document.getElementById('acp-ai-result');
    r.innerHTML=`<h5>${data.title}</h5><div class="desc">${data.description||''}</div>`+
      (data.features?.length?`<b style="font-size:11px;color:#7c3aed">المميزات:</b><ul>${data.features.map(f=>`<li>${f}</li>`).join('')}</ul>`:'')+
      (data.colors?.length?`<b style="font-size:11px;color:#7c3aed">الألوان المتاحة:</b><div style="display:flex;gap:6px;flex-wrap:wrap;margin:5px 0 10px">${data.colors.map(c=>`<span style="display:inline-flex;align-items:center;gap:4px;font-size:11px;background:#fff;padding:3px 8px;border-radius:99px;border:1px solid #e5e7eb"><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${c.hex||'#888'};border:1px solid #d1d5db"></span>${c.name_ar||c.name||c.name_en||''}</span>`).join('')}</div>`:'')+
      (data.warranty?.url?`<b style="font-size:11px;color:#7c3aed">الضمان:</b><br><a href="${data.warranty.url}" target="_blank" style="font-size:11px;color:#7c3aed;text-decoration:underline">${data.warranty.duration_text||'الموقع الرسمي'}</a>`:'');
    r.classList.add('show');
    // Persist AI data on product
    PRODUCT_INFO[ACP_EDITING_PID||'_pending']=data;
    try{localStorage.setItem('zx_product_info',JSON.stringify(PRODUCT_INFO));}catch(_){}
    // Auto-commit to product (so PDP variants show)
    if(ACP_EDITING_PID){
      const p=PRODUCTS.find(x=>x.id===ACP_EDITING_PID);
      if(p){
        if(CURRENT_LANG==='ar'){p.ar=data.title;p.descAr=data.description;}else{p.en=data.title;p.descEn=data.description;}
      }
      PRODUCT_INFO[ACP_EDITING_PID]=data;
      try{localStorage.setItem('zx_product_info',JSON.stringify(PRODUCT_INFO));}catch(_){}
    }
    ZENREX_CREDITS-=(data.cost||10);
    localStorage.setItem('zx_credits',String(ZENREX_CREDITS));
    syncCreditsDisplay();
    toast(CURRENT_LANG==='ar'?'✓ تم توليد المعلومات':'✓ Info generated');
  }catch(e){
    alert((CURRENT_LANG==='ar'?'فشل التوليد: ':'Failed: ')+e.message);
  }finally{
    btn.disabled=false;btn.innerHTML=originalHTML;
  }
}

// ═══════════════════════ VIDEO STUDIO ═══════════════════════
let VS_DURATION=30, VS_TONE='energetic', VS_VOICE='zenrex_male_deep';
let VS_STORYBOARD=null, VS_PRODUCT_ID=null, VS_LAST_VIDEO=null;
function vsSetDuration(d){VS_DURATION=d;document.querySelectorAll('#vs-duration-row .vs-pill').forEach(p=>p.classList.toggle('active',+p.dataset.d===d));vsUpdateRenderCost();}
function vsSetTone(t){VS_TONE=t;document.querySelectorAll('#vs-tone-row .vs-pill').forEach(p=>p.classList.toggle('active',p.dataset.t===t));}
function vsSetVoice(v){VS_VOICE=v;document.querySelectorAll('#vs-voice-row .vs-pill').forEach(p=>p.classList.toggle('active',p.dataset.v===v));}
function vsUpdateRenderCost(){const c=Math.floor(VS_DURATION/5)*5;const el=document.getElementById('vs-render-cost');if(el)el.textContent=c+' نقطة';}
function vsPopulateProductSelect(){
  const sel=document.getElementById('vs-product');if(!sel)return;
  sel.innerHTML=PRODUCTS.slice(0,30).map(p=>`<option value="${p.id}">${(CURRENT_LANG==='ar'?p.ar:p.en).slice(0,45)}</option>`).join('');
}
async function vsGenerateStoryboard(){
  const sel=document.getElementById('vs-product');
  const pid=sel?.value;
  if(!pid){alert('اختر منتج');return;}
  if(ZENREX_CREDITS<5){openRecharge();return;}
  VS_PRODUCT_ID=pid;
  const p=PRODUCTS.find(x=>x.id===pid);
  const cta=document.getElementById('vs-cta').value.trim()||'اطلب الآن';
  document.getElementById('vs-story-loader').classList.add('show');
  document.getElementById('vs-storyboard-preview').style.display='none';
  document.getElementById('vs-video-result').classList.remove('show');
  try{
    const res=await fetch(API+'/api/promo-video/storyboard',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        product_name:CURRENT_LANG==='ar'?p.ar:p.en,
        product_description:(CURRENT_LANG==='ar'?p.descAr:p.descEn)||'',
        duration_seconds:VS_DURATION, tone:VS_TONE, lang:CURRENT_LANG, cta:cta
      })
    });
    if(!res.ok)throw new Error((await res.json().catch(()=>({}))).detail||'storyboard failed');
    const data=await res.json();
    VS_STORYBOARD=data;
    document.getElementById('vs-title-preview').textContent=data.title;
    document.getElementById('vs-scenes-list').innerHTML=data.scenes.map(s=>
      `<div class="vs-scene"><div class="seq">${s.seq}</div><div class="narr">${s.narration}<small>🎨 ${s.visual_prompt.slice(0,70)}</small></div></div>`
    ).join('');
    document.getElementById('vs-storyboard-preview').style.display='block';
    ZENREX_CREDITS-=(data.cost||5);
    localStorage.setItem('zx_credits',String(ZENREX_CREDITS));
    syncCreditsDisplay();
    toast('✓ تم توليد القصة');
  }catch(e){alert('فشل التوليد: '+e.message);}
  finally{document.getElementById('vs-story-loader').classList.remove('show');}
}
async function vsRenderVideo(){
  if(!VS_STORYBOARD){alert('ولّد القصة أولاً');return;}
  const cost=Math.floor(VS_DURATION/5)*5;
  if(ZENREX_CREDITS<cost){openRecharge();return;}
  const p=PRODUCTS.find(x=>x.id===VS_PRODUCT_ID);
  // Build scenes with product gallery images (fallback to p.img)
  const gallery=PRODUCT_GALLERIES?.[VS_PRODUCT_ID]||[{type:'image',url:p?.img}];
  const imgUrls=gallery.filter(g=>g.type==='image'||!g.type).map(g=>g.url);
  const scenes=VS_STORYBOARD.scenes.map((s,i)=>({
    narration:s.narration,
    text_overlay:s.text_overlay||null,
    image_url: imgUrls[i % imgUrls.length] || p?.img
  }));
  document.getElementById('vs-render-loader').classList.add('show');
  document.getElementById('vs-video-result').classList.remove('show');
  try{
    const res=await fetch(API+'/api/promo-video/generate',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        title:VS_STORYBOARD.title, scenes, duration_seconds:VS_DURATION, voice:VS_VOICE,
        full_narration:VS_STORYBOARD.full_narration, cta:VS_STORYBOARD.cta, lang:CURRENT_LANG
      })
    });
    if(!res.ok)throw new Error((await res.json().catch(()=>({}))).detail||'render failed');
    const data=await res.json();
    VS_LAST_VIDEO=data;
    const vid=document.getElementById('vs-video-player');
    vid.src=API+data.video_url;
    document.getElementById('vs-video-meta').innerHTML=
      `<div style="margin-top:8px"><span class="vs-info-pill">⏱ ${data.duration_seconds}s</span><span class="vs-info-pill">🎬 ${data.scenes_count} مشاهد</span><span class="vs-info-pill">🎙 ${data.voice_used}</span><span class="vs-info-pill">⚡ -${data.cost} نقطة</span></div>`;
    document.getElementById('vs-video-result').classList.add('show');
    ZENREX_CREDITS-=(data.cost||cost);
    localStorage.setItem('zx_credits',String(ZENREX_CREDITS));
    syncCreditsDisplay();
    toast('✓ تم توليد الفيديو');
  }catch(e){alert('فشل التوليد: '+e.message);}
  finally{document.getElementById('vs-render-loader').classList.remove('show');}
}
function vsDownloadVideo(){
  if(!VS_LAST_VIDEO)return;
  const a=document.createElement('a');
  a.href=API+VS_LAST_VIDEO.video_url;
  a.download='zenrex-promo.mp4';
  document.body.appendChild(a);a.click();a.remove();
}

// ═══════════════════════ RECHARGE (Inline Zenrex wallet top-up) ═══════════════════════
let RCH_PKG='pro', RCH_METHOD='mada', RCH_PACKAGES=[];
async function openRecharge(){
  document.getElementById('rch-modal').classList.add('open');
  document.getElementById('rch-body-main').style.display='block';
  document.getElementById('rch-success').classList.remove('show');
  // Render fallback packages instantly to avoid flash of empty modal
  if(!RCH_PACKAGES.length){
    RCH_PACKAGES=[
      {id:'starter',credits:500,price_sar:49,label_ar:'البداية'},
      {id:'pro',credits:2500,price_sar:199,label_ar:'المحترف'},
      {id:'agency',credits:6000,price_sar:449,label_ar:'الوكالة'},
      {id:'enterprise',credits:15000,price_sar:999,label_ar:'المؤسسي'}
    ];
  }
  rchRenderPackages();
  rchUpdateButton();
  // Refresh from API in background (in case prices/tiers change)
  try{
    const res=await fetch(API+'/api/promo-video/packages');
    const data=await res.json();
    if(data.packages?.length){RCH_PACKAGES=data.packages;rchRenderPackages();rchUpdateButton();}
  }catch(_){}
}
function closeRecharge(){document.getElementById('rch-modal').classList.remove('open');}
function rchRenderPackages(){
  const grid=document.getElementById('rch-pkg-grid');
  grid.innerHTML=RCH_PACKAGES.map(p=>{
    const popular=p.id==='pro'?'popular':'';
    const active=p.id===RCH_PKG?'active':'';
    const perPt=(p.price_sar/p.credits*100).toFixed(1);
    return `<div class="rch-pkg ${active} ${popular}" data-pkg="${p.id}" onclick="rchSetPkg('${p.id}')">
      <span class="badge">الأكثر طلباً</span>
      <div class="credits">${p.credits.toLocaleString()}</div>
      <div class="label">${p.label_ar||p.id}</div>
      <div class="price">${p.price_sar} ر.س</div>
      <div class="perpoint">${perPt} هللة/نقطة</div>
    </div>`;
  }).join('');
}
function rchSetPkg(id){RCH_PKG=id;rchRenderPackages();rchUpdateButton();}
function rchSetPay(m){RCH_METHOD=m;document.querySelectorAll('.rch-pay').forEach(p=>p.classList.toggle('active',p.dataset.m===m));}
function rchUpdateButton(){
  const pkg=RCH_PACKAGES.find(p=>p.id===RCH_PKG);
  if(!pkg)return;
  document.getElementById('rch-confirm-label').textContent=`ادفع ${pkg.price_sar} ر.س — استلم ${pkg.credits.toLocaleString()} نقطة`;
}
async function rchConfirm(){
  const btn=document.getElementById('rch-confirm');
  btn.disabled=true;
  const old=btn.innerHTML;btn.innerHTML='⏳ جاري الاتصال بالبوابة الآمنة…';
  try{
    const res=await fetch(API+'/api/promo-video/recharge',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({package_id:RCH_PKG, payment_method:RCH_METHOD})
    });
    if(!res.ok)throw new Error('payment failed');
    const data=await res.json();
    ZENREX_CREDITS+=data.credits_added;
    localStorage.setItem('zx_credits',String(ZENREX_CREDITS));
    syncCreditsDisplay();
    // Show success screen
    document.getElementById('rch-body-main').style.display='none';
    document.getElementById('rch-credits-added').innerHTML=`+ <b style="color:#10b981;font-size:22px">${data.credits_added.toLocaleString()}</b> نقطة Zenrex أُضيفت لرصيدك`;
    document.getElementById('rch-receipt').innerHTML=`رقم العملية: ${data.transaction_id}<br>الإيصال: ${data.receipt_number}<br>طريقة الدفع: ${data.payment_method.toUpperCase()}`;
    document.getElementById('rch-success').classList.add('show');
  }catch(e){alert('فشل الدفع: '+e.message);}
  finally{btn.disabled=false;btn.innerHTML=old;}
}


// ═══════════════════════ DELIVERY MANAGEMENT (in ACP) ═══════════════════════
let DLV_ORDER_FILTER='all', DLV_SUB='orders', DLV_ASSIGN_ORDER_ID=null;
let DLV_DRIVERS_CACHE=[], DLV_SETTINGS_CACHE=null;
async function dlvLoadAll(){
  try{
    const [statsR,ordR,drvR,setR]=await Promise.all([
      fetch(API+'/api/delivery/stats').then(r=>r.json()),
      fetch(API+'/api/delivery/orders?limit=80').then(r=>r.json()),
      fetch(API+'/api/delivery/drivers').then(r=>r.json()),
      fetch(API+'/api/delivery/settings').then(r=>r.json()),
    ]);
    DLV_DRIVERS_CACHE=drvR.drivers||[];
    DLV_SETTINGS_CACHE=setR;
    dlvRenderStats(statsR);
    dlvRenderOrders(ordR.orders||[]);
    dlvRenderDrivers(DLV_DRIVERS_CACHE);
    dlvRenderSettings(setR);
    dlvPopulateAreaSelect();
  }catch(e){console.warn('delivery load failed',e);}
}
function dlvRenderStats(s){
  const items=[
    {v:s.by_status?.pending||0,l:'بانتظار'},
    {v:(s.by_status?.assigned||0)+(s.by_status?.delivering||0),l:'نشطة'},
    {v:s.active_drivers||0,l:'سائق متاح'},
    {v:s.revenue_today_sar||0,l:'إيراد اليوم'},
  ];
  document.getElementById('dlv-stats').innerHTML=items.map(i=>`<div class="dlv-stat-box"><div class="v">${i.v}</div><div class="l">${i.l}</div></div>`).join('');
}
function dlvSwitchSub(s){
  DLV_SUB=s;
  ['orders','drivers','branches','payouts','zones'].forEach(k=>{
    const el=document.getElementById('dlv-'+k);if(el)el.style.display=k===s?'block':'none';
    const btn=document.getElementById('dlv-sub-'+k);if(btn)btn.classList.toggle('active',k===s);
  });
  if(s==='branches')dlvLoadBranches();
  if(s==='payouts')dlvLoadPayouts();
}
function dlvFilterOrders(f){
  DLV_ORDER_FILTER=f;
  document.querySelectorAll('#dlv-orders .vs-pill[data-flt]').forEach(p=>p.classList.toggle('active',p.dataset.flt===f));
  dlvLoadOrdersOnly();
}
async function dlvLoadOrdersOnly(){
  const u=DLV_ORDER_FILTER==='all'?'/api/delivery/orders':'/api/delivery/orders?status='+DLV_ORDER_FILTER;
  try{const r=await fetch(API+u);const d=await r.json();dlvRenderOrders(d.orders||[]);}catch(_){}
}
function dlvRenderOrders(orders){
  const list=document.getElementById('dlv-orders-list');
  if(!orders.length){list.innerHTML='<div style="text-align:center;padding:30px 12px;color:#6b7280;font-size:12px">لا توجد طلبات</div>';return;}
  const statusLbl=s=>({pending:'بانتظار',assigned:'مُسندة',picked_up:'تم الاستلام',delivering:'في طريقها',delivered:'منجزة',cancelled:'ملغاة'})[s]||s;
  list.innerHTML=orders.map(o=>{
    const drv=DLV_DRIVERS_CACHE.find(d=>d.id===o.driver_id);
    const drvHtml=drv?`<span class="drv">🧑‍✈️ ${drv.name}</span>`:`<span class="drv no-drv">⚠️ لم يُسند</span>`;
    const showAssign=!o.driver_id&&['pending'].includes(o.status);
    const actHtml=showAssign?`<div class="actions"><button class="primary" onclick="openDlvAssign('${o.id}')">إسناد لسائق</button><button class="secondary" onclick="dlvCancelOrder('${o.id}')">إلغاء</button></div>`:'';
    return `<div class="dlv-order">
      <div class="top"><div><div class="cust">${o.customer_name}</div><div class="ph">${o.customer_phone}</div></div><span class="badge ${o.status}">${statusLbl(o.status)}</span></div>
      <div class="addr">📍 ${o.address}</div>
      <div class="meta"><span class="total">${o.total_sar} ر.س</span>${drvHtml}<span style="color:#6b7280">${o.payment_method==='cash'?'💵':'💳'}</span></div>
      ${actHtml}
    </div>`;
  }).join('');
}
function openDlvAssign(orderId){
  DLV_ASSIGN_ORDER_ID=orderId;
  const o=Object.values(document.querySelectorAll('.dlv-order'));
  document.getElementById('dlv-assign-order-info').textContent='طلب #'+orderId.replace('ord_','');
  const available=DLV_DRIVERS_CACHE.filter(d=>d.status!=='offline');
  document.getElementById('dlv-assign-list').innerHTML=available.length?available.map(d=>`
    <div class="dlv-assign-driver-row" onclick="dlvAssignTo('${d.id}')">
      <div class="avt">${d.name.charAt(0)}</div>
      <div style="flex:1;min-width:0"><div style="font-size:13px;font-weight:900">${d.name}</div><div style="font-size:10px;color:#6b7280">⭐ ${d.rating||5} · ${d.deliveries_today||0} توصيل اليوم · ${dlvAreaLabel(d.area)}</div></div>
      <span class="status-pill ${d.status}" style="padding:3px 8px;border-radius:99px;font-size:9px;font-weight:900;background:${d.status==='online'?'#d1fae5':'#fce7f3'};color:${d.status==='online'?'#065f46':'#9d174d'}">${d.status==='online'?'متاح':'في توصيل'}</span>
    </div>`).join(''):'<div style="text-align:center;padding:20px;color:#dc2626;font-weight:900">⚠️ لا يوجد سائقين متاحين حالياً</div>';
  document.getElementById('dlv-assign-modal').classList.add('open');
}
function closeDlvAssign(){document.getElementById('dlv-assign-modal').classList.remove('open');}
async function dlvAssignTo(driverId){
  try{
    const r=await fetch(API+'/api/delivery/orders/'+DLV_ASSIGN_ORDER_ID+'/assign',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({driver_id:driverId})});
    if(!r.ok)throw new Error();
    closeDlvAssign();dlvLoadAll();
    toast('✓ تم إسناد الطلب');
  }catch(e){alert('فشل الإسناد');}
}
async function dlvCancelOrder(orderId){
  if(!confirm('إلغاء هذا الطلب؟'))return;
  try{
    await fetch(API+'/api/delivery/orders/'+orderId+'/status',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'cancelled'})});
    dlvLoadAll();toast('✓ تم الإلغاء');
  }catch(_){alert('فشل');}
}
function dlvAreaLabel(id){const m={north_riyadh:'شمال الرياض',south_riyadh:'جنوب الرياض',east_riyadh:'شرق الرياض',west_riyadh:'غرب الرياض',central:'وسط الرياض'};return m[id]||id;}
let DLV_EMP_TYPE='commission', DLV_COUNTRIES=[], DLV_PAY_METHODS=[];
function dlvSetEmpType(t){
  DLV_EMP_TYPE=t;
  document.getElementById('dlv-emp-commission').classList.toggle('active',t==='commission');
  document.getElementById('dlv-emp-salaried').classList.toggle('active',t==='salaried');
  document.getElementById('dlv-emp-commission-fields').style.display=t==='commission'?'block':'none';
  document.getElementById('dlv-emp-salaried-fields').style.display=t==='salaried'?'block':'none';
}
function dlvPopulateAreaSelect(){
  if(!DLV_SETTINGS_CACHE)return;
  const sel=document.getElementById('dlv-d-area');if(!sel)return;
  sel.innerHTML=DLV_SETTINGS_CACHE.zones.map(z=>`<option value="${z.id}">${z.name_ar}</option>`).join('');
}
async function dlvDeleteDriver(id,name){
  if(!confirm('حذف السائق "'+name+'"؟'))return;
  try{await fetch(API+'/api/delivery/drivers/'+id,{method:'DELETE'});dlvLoadAll();toast('✓ تم الحذف');}catch(e){alert('فشل');}
}
async function dlvLoadCountries(){
  if(DLV_COUNTRIES.length)return;
  try{const r=await fetch(API+'/api/delivery/countries');const d=await r.json();DLV_COUNTRIES=d.countries||[];
    const sel=document.getElementById('dlv-d-country');
    if(sel){sel.innerHTML=DLV_COUNTRIES.map(c=>`<option value="${c.code}">${c.flag} ${c.name_ar}</option>`).join('');sel.value='SA';}
  }catch(_){}
}
async function dlvLoadPayoutMethods(){
  const country=document.getElementById('dlv-d-country')?.value||'SA';
  try{
    const r=await fetch(API+'/api/delivery/payout-methods?country='+country);
    const d=await r.json();
    DLV_PAY_METHODS=d.methods||[];
    const sel=document.getElementById('dlv-d-paymethod');
    if(sel){
      sel.innerHTML=DLV_PAY_METHODS.map(m=>`<option value="${m.id}" data-field="${m.field}">${m.icon} ${m.name_ar}</option>`).join('');
      dlvUpdateAccountLabel();
    }
  }catch(_){}
}
function dlvUpdateAccountLabel(){
  const sel=document.getElementById('dlv-d-paymethod');if(!sel)return;
  const opt=sel.selectedOptions[0];
  const f=opt?.dataset?.field;
  const lbl=document.getElementById('dlv-d-account-label');
  if(f==='iban')lbl.textContent='IBAN — رقم الحساب الدولي';
  else if(f==='note')lbl.textContent='ملاحظة (تحويل يدوي/كاش)';
  else lbl.textContent='رقم الجوال للتحويل';
}
document.addEventListener('change',(e)=>{if(e.target&&e.target.id==='dlv-d-paymethod')dlvUpdateAccountLabel();});

async function dlvSaveDriver(){
  const name=document.getElementById('dlv-d-name').value.trim();
  const phone=document.getElementById('dlv-d-phone').value.trim();
  if(!name||!/^05\d{8}$/.test(phone)){alert('أدخل الاسم ورقم جوال صحيح يبدأ بـ 05');return;}
  const payload={
    name, phone,
    vehicle:document.getElementById('dlv-d-vehicle').value,
    area:document.getElementById('dlv-d-area').value,
    status:'online',
    employment_type:DLV_EMP_TYPE,
    share_per_delivery_sar:+document.getElementById('dlv-d-share').value||8,
    monthly_salary_sar:+document.getElementById('dlv-d-salary').value||0,
    country:document.getElementById('dlv-d-country').value||'SA',
    payout_method:document.getElementById('dlv-d-paymethod').value||'stc_pay',
    payout_account:document.getElementById('dlv-d-account').value.trim()||phone,
  };
  try{
    const r=await fetch(API+'/api/delivery/drivers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!r.ok)throw new Error();
    ['dlv-d-name','dlv-d-phone','dlv-d-account'].forEach(id=>document.getElementById(id).value='');
    document.getElementById('dlv-add-driver-form').style.display='none';
    dlvLoadAll();toast('✓ تم حفظ السائق');
  }catch(e){alert('فشل الحفظ');}
}
function dlvShowAddDriver(){
  const f=document.getElementById('dlv-add-driver-form');
  f.style.display=f.style.display==='none'?'block':'none';
  if(f.style.display==='block'){
    dlvPopulateAreaSelect();
    dlvLoadCountries().then(dlvLoadPayoutMethods);
  }
}

// Update drivers render to show employment type
function dlvRenderDrivers(drivers){
  const list=document.getElementById('dlv-drivers-list');
  if(!drivers.length){list.innerHTML='<div style="text-align:center;padding:30px;color:#6b7280;font-size:12px">لا يوجد سائقين</div>';return;}
  list.innerHTML=drivers.map(d=>{
    const empBadge=d.employment_type==='salaried'?`<span style="background:#dbeafe;color:#1e40af;padding:2px 6px;border-radius:99px;font-size:9px;font-weight:900">📅 راتب ${d.monthly_salary_sar||0} ر.س</span>`:`<span style="background:#fce7f3;color:#9d174d;padding:2px 6px;border-radius:99px;font-size:9px;font-weight:900">💸 ${d.share_per_delivery_sar||0} ر.س/طلب</span>`;
    return `<div class="dlv-driver">
      <div class="avt">${d.name.charAt(0)}</div>
      <div style="flex:1;min-width:0">
        <div class="nm">${d.name} ${empBadge}</div>
        <div class="ph">${d.phone}</div>
        <div class="stat-row">⭐ <b>${(d.rating||5).toFixed(1)}</b> · ${d.deliveries_today||0} توصيل · معلّق <b>${d.balance_pending_sar||0}</b> ر.س · ${dlvAreaLabel(d.area)}</div>
      </div>
      <span class="status-pill ${d.status}">${d.status==='online'?'متاح':d.status==='delivering'?'في توصيل':'غير متاح'}</span>
      <button onclick="dlvDeleteDriver('${d.id}','${d.name.replace(/'/g,'')}')" style="background:none;border:none;color:#dc2626;cursor:pointer;font-size:16px;padding:4px">🗑️</button>
    </div>`;
  }).join('');
}

// ── BRANCHES ──
async function dlvLoadBranches(){
  try{
    const r=await fetch(API+'/api/delivery/branches');
    const d=await r.json();
    document.getElementById('dlv-branches-list').innerHTML=(d.branches||[]).map(b=>`
      <div class="dlv-driver" style="padding:12px">
        <div class="avt" style="background:linear-gradient(135deg,#10b981,#059669)">🏪</div>
        <div style="flex:1;min-width:0">
          <div class="nm">${b.name_ar} ${b.is_main?'<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:99px;font-size:9px;font-weight:900;margin-right:5px">⭐ رئيسي</span>':''}</div>
          <div style="font-size:10px;color:#6b7280;font-family:monospace;direction:ltr;text-align:right;margin-top:3px">${b.lat}, ${b.lng}</div>
          <div style="font-size:11px;color:#6b7280;margin-top:3px">📞 ${b.phone||'—'}</div>
        </div>
        <a href="https://maps.google.com/?q=${b.lat},${b.lng}" target="_blank" style="background:#10b981;color:#fff;padding:6px 12px;border-radius:99px;font-size:11px;font-weight:900;text-decoration:none;flex-shrink:0">📍 خريطة</a>
      </div>`).join('');
  }catch(_){}
}
async function dlvSaveBranch(){
  const name=document.getElementById('dlv-b-name').value.trim();
  const lat=+document.getElementById('dlv-b-lat').value;
  const lng=+document.getElementById('dlv-b-lng').value;
  if(!name||isNaN(lat)||isNaN(lng)){alert('أدخل الاسم والإحداثيات');return;}
  try{
    const r=await fetch(API+'/api/delivery/branches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      name_ar:name,lat,lng,
      phone:document.getElementById('dlv-b-phone').value.trim(),
      is_main:document.getElementById('dlv-b-main').checked
    })});
    if(!r.ok)throw new Error();
    ['dlv-b-name','dlv-b-phone'].forEach(id=>document.getElementById(id).value='');
    document.getElementById('dlv-add-branch-form').style.display='none';
    dlvLoadBranches();toast('✓ تم حفظ الفرع');
  }catch(e){alert('فشل');}
}

// ── PAYOUTS ──
async function dlvLoadPayouts(){
  try{
    const [drvR,payR]=await Promise.all([
      fetch(API+'/api/delivery/drivers').then(r=>r.json()),
      fetch(API+'/api/delivery/payouts').then(r=>r.json())
    ]);
    const drivers=drvR.drivers||[];
    const payouts=payR.payouts||[];
    // Summary
    const totalPending=drivers.reduce((s,d)=>s+(d.balance_pending_sar||0),0).toFixed(2);
    const totalPaid=payouts.reduce((s,p)=>s+(p.amount_sar||0),0).toFixed(2);
    const totalSalaries=drivers.filter(d=>d.employment_type==='salaried').reduce((s,d)=>s+(d.monthly_salary_sar||0),0).toFixed(0);
    document.getElementById('dlv-payout-summary').innerHTML=[
      {v:totalPending+' ر.س',l:'معلّق دفعه',c:'#dc2626'},
      {v:totalPaid+' ر.س',l:'مدفوع سابقاً',c:'#10b981'},
      {v:totalSalaries+' ر.س',l:'إجمالي الرواتب الشهرية',c:'#7c3aed'}
    ].map(i=>`<div class="dlv-stat-box"><div class="v" style="color:${i.c}">${i.v}</div><div class="l">${i.l}</div></div>`).join('');
    // Balances list (drivers with pending > 0 or salaried)
    const owed=drivers.filter(d=>(d.balance_pending_sar||0)>0||d.employment_type==='salaried');
    document.getElementById('dlv-balances-list').innerHTML=owed.length?owed.map(d=>{
      const amt=d.employment_type==='salaried'?(d.monthly_salary_sar||0):(d.balance_pending_sar||0);
      const lbl=d.employment_type==='salaried'?'راتب شهري':'عمولات معلّقة';
      return `<div class="dlv-driver">
        <div class="avt">${d.name.charAt(0)}</div>
        <div style="flex:1;min-width:0"><div class="nm">${d.name}</div><div style="font-size:10px;color:#6b7280">${lbl} · ${dlvPayMethodLabel(d.payout_method)} · <span style="direction:ltr">${d.payout_account||'—'}</span></div></div>
        <div style="font-weight:900;color:#dc2626;font-size:14px">${amt} ر.س</div>
        <button class="acp-save-btn" style="margin:0;padding:8px 14px;width:auto;font-size:11px" onclick="dlvDoPayout('${d.id}','${d.name.replace(/'/g,'')}',${amt})">💸 تحويل</button>
      </div>`;
    }).join(''):'<div style="text-align:center;padding:20px;color:#6b7280;font-size:12px">لا توجد أرصدة معلّقة</div>';
    // Payouts history
    document.getElementById('dlv-payouts-list').innerHTML=payouts.length?payouts.slice(0,10).map(p=>`
      <div class="dlv-order" style="padding:10px">
        <div class="top"><div><div class="cust">${p.driver_name}</div><div style="font-size:10px;color:#6b7280;font-family:monospace;direction:ltr;text-align:right">${p.reference}</div></div><span class="badge delivered">${p.amount_sar} ر.س</span></div>
        <div class="meta" style="font-size:11px">${dlvPayMethodLabel(p.method)} · <span style="direction:ltr">${p.account}</span> · ${new Date(p.created_at).toLocaleString('ar-SA')}</div>
      </div>`).join(''):'<div style="text-align:center;padding:20px;color:#6b7280;font-size:12px">لا توجد تحويلات سابقة</div>';
  }catch(_){}
}
function dlvPayMethodLabel(id){const m={stc_pay:'📱 STC Pay',mada:'🏦 مدى',urpay:'💳 urpay',alinma_pay:'💳 الإنماء',cash:'💵 كاش',payby:'📱 PayBy',e_and:'📱 e&',vodafone_cash:'📱 Vodafone Cash',instapay:'💳 InstaPay',fawry:'🏷️ Fawry',knet:'🏦 KNET',myfatoorah:'💳 MyFatoorah',benefit:'📱 Benefit',qpay:'📱 QPay',omanpay:'📱 OmanNet',zaincash:'📱 ZainCash',asia_hawala:'📱 AsiaHawala',bank:'🏦 بنكي',bank_ae:'🏦 بنكي UAE',bank_eg:'🏦 بنكي EG'};return m[id]||id;}
async function dlvDoPayout(driverId,name,amount){
  const amt=parseFloat(prompt('تأكيد المبلغ المراد تحويله للسائق '+name+' (ر.س):',amount.toString())||'0');
  if(!amt||amt<=0)return;
  try{
    const r=await fetch(API+'/api/delivery/payouts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({driver_id:driverId,amount_sar:amt,note:'تحويل يدوي من لوحة التاجر'})});
    if(!r.ok)throw new Error();
    const data=await r.json();
    toast('✓ تم التحويل · مرجع: '+data.reference);
    dlvLoadPayouts();
  }catch(e){alert('فشل التحويل');}
}

// ── FEE CALCULATOR ──
async function dlvCalcFee(){
  const lat=+document.getElementById('dlv-calc-lat').value;
  const lng=+document.getElementById('dlv-calc-lng').value;
  const total=+document.getElementById('dlv-calc-total').value||0;
  if(isNaN(lat)||isNaN(lng)){alert('أدخل الإحداثيات');return;}
  try{
    const r=await fetch(API+'/api/delivery/calculate-fee',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({customer_lat:lat,customer_lng:lng,total_sar:total})});
    const d=await r.json();
    document.getElementById('dlv-calc-result').innerHTML=d.is_free
      ?`<div style="background:#d1fae5;color:#065f46;padding:10px;border-radius:10px;font-weight:900">✅ توصيل مجاني! المسافة ${d.distance_km} كم — الطلب أكبر من ${d.free_threshold_sar} ر.س</div>`
      :`<div style="background:#fff;border:1.5px solid #e5e7eb;padding:10px;border-radius:10px;line-height:1.9">
          <div>📏 المسافة: <b>${d.distance_km} كم</b></div>
          <div>🧮 الحساب: ${d.base_fee_sar} + (${d.distance_km} × ${d.per_km_sar}) = <b>${(d.base_fee_sar + d.distance_km*d.per_km_sar).toFixed(2)}</b></div>
          <div>💰 الرسوم النهائية: <b style="color:#7c3aed;font-size:14px">${d.fee_sar} ر.س</b> (بعد min/max)</div>
          <div style="border-top:1px dashed #e5e7eb;margin-top:6px;padding-top:6px">🚗 حصة السائق (افتراضي): <b>${d.driver_share_sar} ر.س</b> · 🏪 المتجر: <b>${d.merchant_share_sar} ر.س</b></div>
        </div>`;
  }catch(e){alert('فشل الحساب');}
}

function dlvRenderSettings(s){
  document.getElementById('dlv-free-th').value=s.free_delivery_threshold_sar||0;
  document.getElementById('dlv-base-fee').value=s.base_fee_sar||0;
  document.getElementById('dlv-per-km').value=s.per_km_sar||0;
  document.getElementById('dlv-min-fee').value=s.min_fee_sar||0;
  document.getElementById('dlv-max-fee').value=s.max_fee_sar||0;
  document.getElementById('dlv-drv-pct').value=s.driver_share_default_pct||80;
  document.getElementById('dlv-mer-pct').value=100-(s.driver_share_default_pct||80);
  document.getElementById('dlv-auto').checked=!!s.auto_assign;
  document.getElementById('dlv-cod').checked=!!s.allow_cash_on_delivery;
  document.getElementById('dlv-distance-pricing').checked=!!s.use_distance_pricing;
  // auto-update merchant pct
  document.getElementById('dlv-drv-pct').oninput=e=>{document.getElementById('dlv-mer-pct').value=100-(+e.target.value||0);};
  document.getElementById('dlv-zones-list').innerHTML=(s.zones||[]).map(z=>
    `<div class="dlv-zone-row"><div><div class="nm">${z.name_ar}</div><div class="meta">~${z.eta_min} دقيقة</div></div><div>الرسوم: <b>${z.fee_sar}</b> ر.س</div></div>`
  ).join('');
}
async function dlvSaveSettings(){
  const drvPct=+document.getElementById('dlv-drv-pct').value||80;
  const payload={
    free_delivery_threshold_sar:+document.getElementById('dlv-free-th').value||0,
    base_fee_sar:+document.getElementById('dlv-base-fee').value||0,
    per_km_sar:+document.getElementById('dlv-per-km').value||0,
    min_fee_sar:+document.getElementById('dlv-min-fee').value||0,
    max_fee_sar:+document.getElementById('dlv-max-fee').value||0,
    driver_share_default_pct:drvPct,
    merchant_share_default_pct:100-drvPct,
    auto_assign:document.getElementById('dlv-auto').checked,
    allow_cash_on_delivery:document.getElementById('dlv-cod').checked,
    use_distance_pricing:document.getElementById('dlv-distance-pricing').checked,
  };
  try{
    const r=await fetch(API+'/api/delivery/settings',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!r.ok)throw new Error();
    DLV_SETTINGS_CACHE=await r.json();
    toast('✓ تم حفظ الإعدادات');
  }catch(e){alert('فشل');}
}


// ═══════════════════════ PAYROLL (auto-calc + bulk payout + statements) ═══════════════════════
const MONTHS_AR=['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'];
function prInit(){
  const mSel=document.getElementById('pr-month'),ySel=document.getElementById('pr-year');
  if(!mSel.options.length){
    mSel.innerHTML=MONTHS_AR.map((m,i)=>`<option value="${i+1}">${m}</option>`).join('');
    const now=new Date();mSel.value=now.getMonth()+1;
    const years=[2025,2026,2027];ySel.innerHTML=years.map(y=>`<option value="${y}">${y}</option>`).join('');
    ySel.value=now.getFullYear();
  }
  prCalculate();
}
async function prCalculate(){
  const m=document.getElementById('pr-month').value, y=document.getElementById('pr-year').value;
  try{
    const r=await fetch(API+`/api/payroll/calculate?month=${m}&year=${y}`);
    const d=await r.json();
    document.getElementById('pr-summary').innerHTML=`
      <div class="dlv-stat-box"><div class="v">${d.total_payable_sar}</div><div class="l">إجمالي المستحق (ر.س)</div></div>
      <div class="dlv-stat-box"><div class="v">${d.drivers_count}</div><div class="l">سائقين</div></div>
      <div class="dlv-stat-box"><div class="v" style="color:#1e40af">${d.salaried_total}</div><div class="l">رواتب موظفين</div></div>
      <div class="dlv-stat-box"><div class="v" style="color:#9d174d">${d.commission_total}</div><div class="l">عمولات</div></div>
    `;
    document.getElementById('pr-lines').innerHTML=`<h5 style="font-size:12px;font-weight:900;color:#0a0a0a;margin-bottom:8px">📋 تفاصيل ${d.label}</h5>`+
      d.lines.map(l=>{
        const empBadge=l.employment_type==='salaried'?`<span style="background:#dbeafe;color:#1e40af;padding:2px 6px;border-radius:99px;font-size:9px;font-weight:900">📅 راتب</span>`:`<span style="background:#fce7f3;color:#9d174d;padding:2px 6px;border-radius:99px;font-size:9px;font-weight:900">💸 عمولة</span>`;
        return `<div class="dlv-driver">
          <div class="avt">${l.driver_name.charAt(0)}</div>
          <div style="flex:1;min-width:0">
            <div class="nm">${l.driver_name} ${empBadge}</div>
            <div class="stat-row">${l.kind} · ${l.deliveries_this_month} توصيل · ${dlvPayMethodLabel(l.payout_method)}</div>
          </div>
          <div style="font-weight:900;color:${l.amount_sar>0?'#10b981':'#94a3b8'};font-size:14px">${l.amount_sar} ر.س</div>
          <button onclick="prOpenStatement('${l.driver_id}',${m},${y})" style="background:#0a0a14;color:#fbbf24;border:none;padding:7px 12px;border-radius:99px;font-family:inherit;font-weight:900;font-size:11px;cursor:pointer">📄 كشف</button>
        </div>`;
      }).join('');
    document.getElementById('pr-actions').style.display=d.total_payable_sar>0?'block':'none';
  }catch(e){alert('فشل الحساب');}
}
function prOpenStatement(driverId,m,y){
  window.open(API+`/api/payroll/statement/${driverId}?month=${m}&year=${y}`,'_blank');
}
async function prRun(){
  if(!confirm('سيتم تحويل دفعات لجميع السائقين الآن. هل أنت متأكد؟'))return;
  const m=document.getElementById('pr-month').value, y=document.getElementById('pr-year').value;
  try{
    const r=await fetch(API+'/api/payroll/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({month:+m,year:+y,notify_whatsapp:true})});
    const d=await r.json();
    document.getElementById('pr-results').innerHTML=`
      <div style="background:linear-gradient(135deg,#d1fae5,#a7f3d0);border:1.5px solid #10b981;border-radius:14px;padding:14px;margin-bottom:10px;text-align:center">
        <div style="font-size:32px;margin-bottom:6px">✅</div>
        <h4 style="font-size:14px;font-weight:900;color:#065f46;margin-bottom:4px">تم تنفيذ الدفعات!</h4>
        <p style="font-size:12px;color:#065f46">تم تحويل <b>${d.total_paid_sar} ر.س</b> على ${d.processed} سائق</p>
      </div>
      ${d.results.map(r=>{
        const status=r.status==='paid'?'<span style="color:#10b981">✓ مدفوع</span>':r.status==='skipped'?'<span style="color:#94a3b8">— تخطٍ</span>':'<span style="color:#dc2626">✕ فشل</span>';
        return `<div class="dlv-order" style="padding:10px"><div class="top"><div><div class="cust">${r.driver_name}</div><div style="font-size:10px;color:#6b7280">${r.amount_sar} ر.س · ${dlvPayMethodLabel(r.payout_method)} · ${r.reference||'—'}</div></div>${status}</div>${r.whatsapp_message?`<div style="font-size:10px;color:#7c3aed;background:#faf5ff;padding:6px;border-radius:6px;margin-top:6px;line-height:1.5;white-space:pre-line">📱 WA: ${r.whatsapp_message.slice(0,140)}…</div>`:''}</div>`;
      }).join('')}`;
    prCalculate();
  }catch(e){alert('فشل التحويل');}
}

// ═══════════════════════ GLOBAL PAYMENT GATEWAYS ═══════════════════════
let GW_COUNTRIES=[],GW_CURRENT_COUNTRY='SA',GW_ENABLED=[];
async function gwInit(){
  try{
    const [profR,enR]=await Promise.all([
      fetch(API+'/api/payments/countries').then(r=>r.json()),
      fetch(API+'/api/payments/enabled').then(r=>r.json())
    ]);
    GW_ENABLED=enR.enabled.map(g=>g.id);
    const sel=document.getElementById('gw-country');
    const codes=Object.keys(profR.profiles);
    sel.innerHTML=codes.map(c=>{
      const p=profR.profiles[c];
      const flag={SA:'🇸🇦',AE:'🇦🇪',EG:'🇪🇬',KW:'🇰🇼',BH:'🇧🇭',QA:'🇶🇦',US:'🇺🇸',GB:'🇬🇧',DE:'🇩🇪',FR:'🇫🇷',NL:'🇳🇱',CN:'🇨🇳',IN:'🇮🇳',SG:'🇸🇬'}[c]||'🌐';
      return `<option value="${c}">${flag} ${p.name_ar}</option>`;
    }).join('');
    sel.value=GW_CURRENT_COUNTRY;
    gwLoadCountry();
  }catch(_){}
}
async function gwLoadCountry(){
  const c=document.getElementById('gw-country').value;
  GW_CURRENT_COUNTRY=c;
  try{
    const r=await fetch(API+'/api/payments/by-country?country='+c);
    const d=await r.json();
    // profile panel
    const p=d.profile;
    document.getElementById('gw-country-profile').innerHTML=`
      <div style="background:linear-gradient(135deg,#faf5ff,#fff);border:1.5px solid #ddd6fe;border-radius:14px;padding:14px;margin-bottom:14px">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:12px;line-height:1.7">
          <div>🏛️ <b>الجهة المنظِّمة:</b> ${p.regulator}</div>
          <div>💱 <b>العملة:</b> ${p.currency}</div>
          <div>📊 <b>ضريبة:</b> ${p.vat_pct}%</div>
          <div>📑 <b>الفاتورة:</b> ${p.invoice_standard}</div>
          <div style="grid-column:1/-1">🚚 <b>الشحن:</b> ${(p.shipping_partners||[]).join(' · ')||'—'}</div>
        </div>
      </div>`;
    // gateways list
    const list=d.gateways;
    document.getElementById('gw-gateways-list').innerHTML=list.map(g=>{
      const enabled=GW_ENABLED.includes(g.id);
      const typeColor={card:'#1e40af',wallet:'#7c3aed',bnpl:'#ec4899',bank:'#059669',cod:'#10b981',qr:'#0891b2',crypto:'#f59e0b'}[g.type]||'#6b7280';
      const typeIco={card:'💳',wallet:'📱',bnpl:'💎',bank:'🏦',cod:'💵',qr:'📲',crypto:'₿'}[g.type]||'💰';
      const fees=g.real_fees||{};
      const universalBadge=g.is_universal?'<span style="background:#fef3c7;color:#92400e;padding:2px 6px;border-radius:99px;font-size:9px;font-weight:900;margin-right:4px">🌐 عالمي</span>':'';
      return `<div style="background:#fff;border:2px solid ${enabled?'#7c3aed':'#e5e7eb'};border-radius:12px;padding:10px;margin-bottom:8px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
          <div style="width:46px;height:46px;border-radius:10px;background:${g.badge.bg};color:${g.badge.fg};display:flex;align-items:center;justify-content:center;font-weight:900;font-size:11px;text-align:center;line-height:1.1;flex-shrink:0">${g.name_en.slice(0,7)}</div>
          <div style="flex:1;min-width:0">
            <div style="font-size:13px;font-weight:900">${g.name_ar} ${universalBadge}<span style="background:${typeColor}20;color:${typeColor};padding:2px 6px;border-radius:99px;font-size:9px;margin-right:4px">${typeIco} ${g.type.toUpperCase()}</span></div>
            <div style="font-size:10px;color:#6b7280;margin-top:2px">${g.badge.slogan_ar}</div>
            <div style="font-size:10px;color:#dc2626;margin-top:2px">💰 رسوم التاجر: ${fees.merchant||g.fees_hint||'—'} · تسوية ${fees.settlement_days||1} يوم</div>
          </div>
          <label style="display:flex;align-items:center;cursor:pointer">
            <input type="checkbox" ${enabled?'checked':''} onchange="gwToggle('${g.id}',this.checked)" style="width:36px;height:20px;appearance:none;background:${enabled?'#7c3aed':'#cbd5e1'};border-radius:99px;cursor:pointer">
          </label>
        </div>
        <div style="display:flex;gap:5px;flex-wrap:wrap">
          <a href="${g.merchant_signup_url||'#'}" target="_blank" style="background:#10b981;color:#fff;padding:5px 10px;border-radius:99px;font-size:10px;font-weight:900;text-decoration:none">🚀 تسجيل التاجر</a>
          <a href="${g.merchant_dashboard_url||'#'}" target="_blank" style="background:#0a0a14;color:#fbbf24;padding:5px 10px;border-radius:99px;font-size:10px;font-weight:900;text-decoration:none">🔐 لوحة التحكم</a>
          <a href="${g.developer_docs_url||'#'}" target="_blank" style="background:#7c3aed;color:#fff;padding:5px 10px;border-radius:99px;font-size:10px;font-weight:900;text-decoration:none">📚 API Docs</a>
          ${g.required_credentials&&g.required_credentials.length?`<button onclick="gwOpenConnect('${g.id}')" style="background:#fbbf24;color:#0a0a14;padding:5px 10px;border:none;border-radius:99px;font-size:10px;font-weight:900;cursor:pointer;font-family:inherit">🔌 اربط الآن</button>`:''}
          <button onclick="gwShowHelp('${g.id}')" style="background:#fff;color:#7c3aed;padding:5px 10px;border:1px solid #ddd6fe;border-radius:99px;font-size:10px;font-weight:900;cursor:pointer;font-family:inherit">🤖 مساعد AI</button>
        </div>
        <div id="gw-help-${g.id}" style="display:none;background:#faf5ff;border:1px solid #ddd6fe;border-radius:8px;padding:8px;margin-top:8px;font-size:11px;line-height:1.7;color:#5b21b6">${g.ai_helper_ar||''}</div>
        <div id="gw-connect-${g.id}" style="display:none;background:#fef3c7;border:1px dashed #f59e0b;border-radius:8px;padding:10px;margin-top:8px"></div>
      </div>`;
    }).join('');
    // preview selector
    const tsel=document.getElementById('gw-test-gateway');
    tsel.innerHTML=list.map(g=>`<option value="${g.id}">${g.name_ar}</option>`).join('');
  }catch(_){}
}
async function gwToggle(gid,enable){
  try{await fetch(API+'/api/payments/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({gateway_id:gid,enable})});if(enable&&!GW_ENABLED.includes(gid))GW_ENABLED.push(gid);if(!enable)GW_ENABLED=GW_ENABLED.filter(x=>x!==gid);toast(enable?'✓ تم تفعيل '+gid:'تم تعطيل '+gid);}catch(_){}
}
function gwShowHelp(gid){
  const el=document.getElementById('gw-help-'+gid);
  if(el)el.style.display=el.style.display==='none'?'block':'none';
}
async function gwOpenConnect(gid){
  const el=document.getElementById('gw-connect-'+gid);
  if(!el)return;
  if(el.style.display!=='none'){el.style.display='none';return;}
  try{
    const r=await fetch(API+'/api/payments/gateway/'+gid);
    const g=await r.json();
    const creds=g.required_credentials||[];
    const saved=JSON.parse(localStorage.getItem('zx_gw_creds_'+gid)||'{}');
    el.innerHTML=`
      <h5 style="font-size:12px;font-weight:900;color:#92400e;margin-bottom:8px">🔌 ربط ${g.name_ar} بمتجرك</h5>
      <p style="font-size:11px;color:#6b7280;margin-bottom:10px;line-height:1.6">سجّل في <a href="${g.merchant_signup_url}" target="_blank" style="color:#7c3aed;font-weight:900">بوابة ${g.name_ar} ↗</a> ثم انسخ المعلومات أدناه:</p>
      ${creds.map(c=>{
        const val=saved[c.name]||'';
        const optionsHtml=c.options?`<select id="cred-${gid}-${c.name}" style="width:100%;padding:8px;border:1.5px solid #fcd34d;border-radius:8px;font-family:inherit;font-size:12px;margin-bottom:4px">${c.options.map(o=>`<option value="${o}"${val===o?' selected':''}>${o}</option>`).join('')}</select>`:`<input id="cred-${gid}-${c.name}" type="${c.type==='password'?'password':'text'}" value="${val}" placeholder="${c.label_ar}" style="width:100%;padding:8px;border:1.5px solid #fcd34d;border-radius:8px;font-family:inherit;font-size:12px;margin-bottom:4px;direction:ltr;text-align:right">`;
        return `<div style="margin-bottom:8px"><label style="font-size:10px;font-weight:900;color:#92400e;display:block;margin-bottom:3px">${c.label_ar}</label>${optionsHtml}<small style="font-size:9px;color:#78350f;line-height:1.4;display:block">💡 ${c.where_ar||''}</small></div>`;
      }).join('')}
      ${creds.length===0?'<p style="font-size:11px;color:#92400e">لا تحتاج بيانات إضافية — البوابة جاهزة فور التفعيل.</p>':''}
      <button onclick="gwSaveCreds('${gid}')" style="background:#10b981;color:#fff;padding:8px 16px;border:none;border-radius:8px;font-family:inherit;font-weight:900;font-size:12px;cursor:pointer;margin-top:6px">💾 حفظ وربط البوابة</button>
    `;
    el.style.display='block';
  }catch(e){alert('فشل التحميل');}
}
function gwSaveCreds(gid){
  const creds={};
  document.querySelectorAll(`[id^="cred-${gid}-"]`).forEach(inp=>{
    const k=inp.id.replace(`cred-${gid}-`,'');
    creds[k]=inp.value;
  });
  localStorage.setItem('zx_gw_creds_'+gid,JSON.stringify(creds));
  gwToggle(gid,true);
  toast('✓ تم حفظ بيانات '+gid+' محلياً · جاهز للربط الفعلي');
  document.getElementById('gw-connect-'+gid).style.display='none';
}
async function gwPreview(){
  const amount=+document.getElementById('gw-test-amount').value||0;
  const gid=document.getElementById('gw-test-gateway').value;
  try{
    const r=await fetch(API+`/api/payments/checkout-preview?gateway_id=${gid}&amount=${amount}&currency=SAR`,{method:'POST'});
    const d=await r.json();
    if(!d.eligible){document.getElementById('gw-preview-result').innerHTML=`<div style="background:#fef2f2;color:#991b1b;padding:10px;border-radius:8px;font-size:12px">⚠️ ${d.reason}</div>`;return;}
    let html=`<div style="background:#fff;border:1.5px solid ${d.badge.bg};border-radius:12px;padding:14px;margin-top:10px;text-align:center">`;
    html+=`<div style="background:${d.badge.bg};color:${d.badge.fg};display:inline-block;padding:8px 18px;border-radius:99px;font-weight:900;font-size:13px;margin-bottom:8px">${d.name_ar}</div>`;
    html+=`<p style="font-size:11px;color:#6b7280;margin-bottom:10px">${d.badge.slogan_ar}</p>`;
    if(d.installments){
      html+='<div style="display:flex;flex-direction:column;gap:6px;text-align:right">';
      d.installments.forEach(p=>{html+=`<div style="background:#faf5ff;border:1px solid #ddd6fe;border-radius:8px;padding:8px;font-size:12px;display:flex;justify-content:space-between"><span>${p.label_ar}</span><b style="color:#7c3aed">${p.total_with_interest} ${d.currency}</b></div>`;});
      html+='</div>';
    }else{
      html+=`<div style="font-size:18px;font-weight:900;color:${d.badge.bg.startsWith('#0')?'#0a0a14':d.badge.bg}">${d.amount} ${d.currency}</div>`;
    }
    html+=`<div style="margin-top:10px;font-size:10px;color:#6b7280">${d.checkout.otp_required?'🔒 يتطلب OTP':''} ${d.checkout.kyc_required?'· 🆔 KYC':''} · 📲 ${d.checkout.flow}</div>`;
    html+='</div>';
    document.getElementById('gw-preview-result').innerHTML=html;
  }catch(e){alert('فشل');}
}


function toast(msg){
  const el=document.createElement('div');
  el.textContent=msg;
  el.style.cssText='position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:#0a0a0a;color:#fff;padding:12px 22px;border-radius:99px;font-weight:900;font-size:13px;z-index:600;box-shadow:0 8px 24px rgba(0,0,0,.3);animation:fadeOut 2.5s forwards';
  document.body.appendChild(el);
  setTimeout(()=>el.remove(),2500);
}
const _toastKf=document.createElement('style');_toastKf.textContent='@keyframes fadeOut{0%,70%{opacity:1}100%{opacity:0;transform:translate(-50%,20px)}}';document.head.appendChild(_toastKf);

// ═══════════════════════ LIGHTBOX (Pan + Zoom + Gallery + Auto-advance) ═══════════════════════
let _lbScale=1,_lbX=0,_lbY=0,_lbStartX=0,_lbStartY=0,_lbDragging=false;
function buildProductGallery(productId){
  const p=PRODUCTS.find(x=>x.id===productId);
  const stored=PRODUCT_GALLERIES[productId]||[];
  if(stored.length)return stored;
  // Default: include p.img only
  return p?[{type:'image',url:p.img}]:[];
}
function openLightbox(url,productId){
  LB_CURRENT_PRODUCT=productId||null;
  LB_GALLERY=productId?buildProductGallery(productId):[{type:'image',url}];
  LB_INDEX=Math.max(0,LB_GALLERY.findIndex(g=>g.url===url));
  if(LB_INDEX<0)LB_INDEX=0;
  _lbScale=1;_lbX=0;_lbY=0;
  document.getElementById('lightbox').classList.add('open');
  document.body.style.overflow='hidden';
  document.getElementById('lb-gallery-add').style.display=(ADMIN_MODE&&productId)?'flex':'none';
  showLbItem();
  startLbAutoAdvance();
}
function showLbItem(){
  const item=LB_GALLERY[LB_INDEX];if(!item)return;
  const img=document.getElementById('lb-img'),vid=document.getElementById('lb-video');
  if(item.type==='video'){
    img.style.display='none';vid.style.display='block';vid.src=item.url;vid.play().catch(()=>{});
  } else {
    vid.pause();vid.style.display='none';
    img.style.display='block';img.src=item.url.replace(/w=\d+/,'w=1600').replace(/q=\d+/,'q=90');
  }
  _lbScale=1;_lbX=0;_lbY=0;applyLbTransform();
  // Render thumbnails
  const thumbs=document.getElementById('lb-thumbs');
  if(LB_GALLERY.length>1){
    thumbs.style.display='flex';
    thumbs.innerHTML=LB_GALLERY.map((g,i)=>`<img src="${g.type==='video'?'https://cdn-icons-png.flaticon.com/512/727/727245.png':g.url}" class="${i===LB_INDEX?'active':''}" onclick="jumpLb(${i})" alt="" loading="lazy" decoding="async">`).join('');
  } else thumbs.style.display='none';
  // Show/hide nav buttons
  const showNav=LB_GALLERY.length>1;
  document.querySelector('.lb-prev').style.display=showNav?'flex':'none';
  document.querySelector('.lb-next').style.display=showNav?'flex':'none';
}
function jumpLb(i){LB_INDEX=i;showLbItem();}
function lbPrev(){LB_INDEX=(LB_INDEX-1+LB_GALLERY.length)%LB_GALLERY.length;showLbItem();}
function lbNext(){LB_INDEX=(LB_INDEX+1)%LB_GALLERY.length;showLbItem();}
function startLbAutoAdvance(){
  if(_lbAutoAdvance)clearInterval(_lbAutoAdvance);
  if(LB_GALLERY.length<2)return;
  _lbAutoAdvance=setInterval(()=>{if(_lbScale===1)lbNext();},5000);
}
function closeLightbox(){
  document.getElementById('lightbox').classList.remove('open');
  document.body.style.overflow='';
  if(_lbAutoAdvance)clearInterval(_lbAutoAdvance);
  document.getElementById('lb-video').pause();
}
function lbZoom(delta){_lbScale=Math.max(0.5,Math.min(5,_lbScale+delta));applyLbTransform();}
function lbReset(){_lbScale=1;_lbX=0;_lbY=0;applyLbTransform();}
function applyLbTransform(){
  const img=document.getElementById('lb-img');
  if(!img)return;
  img.style.transform=`translate(${_lbX}px,${_lbY}px) scale(${_lbScale})`;
  document.getElementById('lb-info').textContent=Math.round(_lbScale*100)+'%';
}
function addToProductGallery(e,kind){
  if(!LB_CURRENT_PRODUCT)return;
  const file=e.target.files?.[0];if(!file)return;
  const max=kind==='video'?20*1024*1024:5*1024*1024;
  if(file.size>max){alert(CURRENT_LANG==='ar'?'الملف كبير':'File too large');return;}
  const reader=new FileReader();
  reader.onload=ev=>{
    if(!PRODUCT_GALLERIES[LB_CURRENT_PRODUCT])PRODUCT_GALLERIES[LB_CURRENT_PRODUCT]=[];
    PRODUCT_GALLERIES[LB_CURRENT_PRODUCT].push({type:kind,url:ev.target.result});
    localStorage.setItem('zx_galleries',JSON.stringify(PRODUCT_GALLERIES));
    LB_GALLERY=buildProductGallery(LB_CURRENT_PRODUCT);
    LB_INDEX=LB_GALLERY.length-1;
    showLbItem();
    toast(CURRENT_LANG==='ar'?(kind==='video'?'🎬 تم إضافة فيديو':'📷 تم إضافة صورة'):(kind==='video'?'🎬 Video added':'📷 Image added'));
  };
  reader.readAsDataURL(file);
}
function openStudioFromLightbox(){
  if(!LB_CURRENT_PRODUCT)return;
  closeLightbox();
  openStudio('product:'+LB_CURRENT_PRODUCT);
}
(function setupLightboxDrag(){
  const stage=document.getElementById('lb-stage');
  if(!stage)return;
  const img=document.getElementById('lb-img');
  const start=e=>{const t=e.touches?e.touches[0]:e;_lbStartX=t.clientX-_lbX;_lbStartY=t.clientY-_lbY;_lbDragging=true;img.classList.add('dragging');};
  const move=e=>{if(!_lbDragging)return;const t=e.touches?e.touches[0]:e;_lbX=t.clientX-_lbStartX;_lbY=t.clientY-_lbStartY;applyLbTransform();};
  const end=()=>{_lbDragging=false;img.classList.remove('dragging');};
  stage.addEventListener('mousedown',start);stage.addEventListener('mousemove',move);window.addEventListener('mouseup',end);
  stage.addEventListener('touchstart',start,{passive:true});stage.addEventListener('touchmove',move,{passive:true});stage.addEventListener('touchend',end);
  stage.addEventListener('wheel',e=>{e.preventDefault();lbZoom(e.deltaY<0?0.15:-0.15);},{passive:false});
  let lastTap=0;
  stage.addEventListener('click',e=>{if(e.target.id==='lb-img'){const now=Date.now();if(now-lastTap<350){_lbScale===1?lbZoom(1):lbReset();}lastTap=now;}});
})();

// Hook product images to lightbox (delegated)
document.addEventListener('click',e=>{
  if(e.target.closest('.img-edit-btn,.add-btn,.qty-btn'))return;
  const img=e.target.closest('.p-card img');
  if(!img)return;
  const card=img.closest('.p-card');
  const addBtn=card?.querySelector('.add-btn');
  // Find product ID from add-btn onclick
  let pid=null;
  if(addBtn){const m=addBtn.getAttribute('onclick')?.match(/addToCart\('([^']+)'\)/);if(m)pid=m[1];}
  openLightbox(img.src,pid);
});

// Apply image overrides on initial render
function applyAllOverrides(){
  if(IMG_OVERRIDES.main_banner){
    const stack=document.getElementById('banner-img-stack');
    const ov=IMG_OVERRIDES.main_banner;
    const obj=typeof ov==='string'?{url:ov,type:'image'}:ov;
    if(stack){
      if(obj.type==='video'){stack.innerHTML='';const v=document.getElementById('banner-video');v.src=obj.url;v.style.opacity='1';v.load();}
      else{stack.innerHTML=`<img src="${obj.url}" alt="banner" style="opacity:1;animation:bnr-fade 18s linear infinite" loading="lazy" decoding="async">`;}
    }
  }
  Object.keys(IMG_OVERRIDES).forEach(k=>{
    if(k.startsWith('product:')){
      const id=k.split(':')[1];
      const p=PRODUCTS.find(x=>x.id===id);
      if(p){const v=IMG_OVERRIDES[k];p.img=typeof v==='string'?v:v.url;}
    }
  });
}

init();
