/**
 * Zitex Quran Primitives — exposed to AI-generated sites.
 *
 * The AI has full freedom to design the UI/UX from scratch, but uses these
 * verified data primitives so it never hallucinates Quran text or audio URLs.
 *
 * Available globals:
 *   ZitexQuran.RECITERS — array of 14 verified reciters with per-ayah audio
 *   ZitexQuran.SURAHS   — array of 114 surahs {n, name, transliteration, type, ayah_count}
 *   ZitexQuran.fetchSurah(n) → Promise<{ayahs: [{n, text}], audio_url(reciterId, ayahN)}>
 *   ZitexQuran.audioUrl(reciterId, surahN, ayahN) → string
 *   ZitexQuran.formatAyahNumber(n) → arabic-indic numerals
 */
(function (global) {
  'use strict';

  const RECITERS = [
    { id: 'alafasy',    name: 'مشاري العفاسي',     slug: 'Alafasy_128kbps' },
    { id: 'sudais',     name: 'عبد الرحمن السديس', slug: 'Abdurrahmaan_As-Sudais_192kbps' },
    { id: 'shuraim',    name: 'سعود الشريم',        slug: 'Saood_ash-Shuraym_128kbps' },
    { id: 'husary',     name: 'محمود الحصري',       slug: 'Husary_128kbps' },
    { id: 'minshawi',   name: 'محمد المنشاوي',     slug: 'Minshawi_Murattal_128kbps' },
    { id: 'abdulbasit', name: 'عبد الباسط',         slug: 'Abdul_Basit_Murattal_192kbps' },
    { id: 'ghamdi',     name: 'سعد الغامدي',        slug: 'Ghamadi_40kbps' },
    { id: 'ajmi',       name: 'أحمد العجمي',        slug: 'ahmed_ibn_ali_al_ajamy_128kbps' },
    { id: 'dossary',    name: 'ياسر الدوسري',       slug: 'Yasser_Ad-Dussary_128kbps' },
    { id: 'shatri',     name: 'أبو بكر الشاطري',    slug: 'Abu_Bakr_Ash-Shaatree_128kbps' },
    { id: 'juhany',     name: 'عبد الله الجهني',    slug: 'abdullaah_3awwaad_al-juhaynee_128kbps' },
    { id: 'hthfi',      name: 'علي الحذيفي',        slug: 'Hudhaify_128kbps' },
    { id: 'ayyub',      name: 'محمد أيوب',          slug: 'Muhammad_Ayyoub_128kbps' },
    { id: 'maher',      name: 'ماهر المعيقلي',      slug: 'Maher_AlMuaiqly_64kbps' },
  ];

  const SURAHS_AR = [
    'الفاتحة','البقرة','آل عمران','النساء','المائدة','الأنعام','الأعراف','الأنفال','التوبة','يونس',
    'هود','يوسف','الرعد','إبراهيم','الحجر','النحل','الإسراء','الكهف','مريم','طه',
    'الأنبياء','الحج','المؤمنون','النور','الفرقان','الشعراء','النمل','القصص','العنكبوت','الروم',
    'لقمان','السجدة','الأحزاب','سبأ','فاطر','يس','الصافات','ص','الزمر','غافر',
    'فصلت','الشورى','الزخرف','الدخان','الجاثية','الأحقاف','محمد','الفتح','الحجرات','ق',
    'الذاريات','الطور','النجم','القمر','الرحمن','الواقعة','الحديد','المجادلة','الحشر','الممتحنة',
    'الصف','الجمعة','المنافقون','التغابن','الطلاق','التحريم','الملك','القلم','الحاقة','المعارج',
    'نوح','الجن','المزمل','المدثر','القيامة','الإنسان','المرسلات','النبأ','النازعات','عبس',
    'التكوير','الانفطار','المطففين','الانشقاق','البروج','الطارق','الأعلى','الغاشية','الفجر','البلد',
    'الشمس','الليل','الضحى','الشرح','التين','العلق','القدر','البينة','الزلزلة','العاديات',
    'القارعة','التكاثر','العصر','الهمزة','الفيل','قريش','الماعون','الكوثر','الكافرون','النصر',
    'المسد','الإخلاص','الفلق','الناس'
  ];
  const SURAHS_EN = [
    'Al-Faatiha','Al-Baqara','Aal-Imran','An-Nisa','Al-Maaida','Al-Anaam','Al-Aaraf','Al-Anfal','At-Tawba','Yunus',
    'Hud','Yusuf','Ar-Raad','Ibrahim','Al-Hijr','An-Nahl','Al-Israa','Al-Kahf','Maryam','Taa-Haa',
    'Al-Anbiyaa','Al-Hajj','Al-Muminoon','An-Noor','Al-Furqan','Ash-Shuara','An-Naml','Al-Qasas','Al-Ankaboot','Ar-Room',
    'Luqman','As-Sajda','Al-Ahzaab','Saba','Faatir','Yaseen','As-Saaffaat','Saad','Az-Zumar','Al-Ghaafir',
    'Fussilat','Ash-Shooraa','Az-Zukhruf','Ad-Dukhaan','Al-Jaathiya','Al-Ahqaaf','Muhammad','Al-Fath','Al-Hujuraat','Qaaf',
    'Adh-Dhaariyat','At-Toor','An-Najm','Al-Qamar','Ar-Rahmaan','Al-Waaqia','Al-Hadeed','Al-Mujaadila','Al-Hashr','Al-Mumtahana',
    'As-Saff','Al-Jumua','Al-Munaafiqoon','At-Taghaabun','At-Talaaq','At-Tahreem','Al-Mulk','Al-Qalam','Al-Haaqqa','Al-Maaarij',
    'Nooh','Al-Jinn','Al-Muzzammil','Al-Muddaththir','Al-Qiyaama','Al-Insaan','Al-Mursalaat','An-Naba','An-Naaziaat','Abasa',
    'At-Takweer','Al-Infitaar','Al-Mutaffifeen','Al-Inshiqaaq','Al-Burooj','At-Taariq','Al-Aalaa','Al-Ghaashiya','Al-Fajr','Al-Balad',
    'Ash-Shams','Al-Layl','Ad-Dhuhaa','Ash-Sharh','At-Teen','Al-Alaq','Al-Qadr','Al-Bayyina','Az-Zalzala','Al-Aadiyaat',
    'Al-Qaariaa','At-Takaathur','Al-Asr','Al-Humaza','Al-Feel','Quraish','Al-Maaoon','Al-Kawthar','Al-Kaafiroon','An-Nasr',
    'Al-Masad','Al-Ikhlaas','Al-Falaq','An-Naas'
  ];
  const AYAH_COUNTS = [7,286,200,176,120,165,206,75,129,109,123,111,43,52,99,128,111,110,98,135,112,78,118,64,77,227,93,88,69,60,34,30,73,54,45,83,182,88,75,85,54,53,89,59,37,35,38,29,18,45,60,49,62,55,78,96,29,22,24,13,14,11,11,18,12,12,30,52,52,44,28,28,20,56,40,31,50,40,46,42,29,19,36,25,22,17,19,26,30,20,15,21,11,8,8,19,5,8,8,11,11,8,3,9,5,4,7,3,6,3,5,4,4,5,6];
  const TYPES = ['Meccan','Medinan','Medinan','Medinan','Medinan','Meccan','Meccan','Medinan','Medinan','Meccan','Meccan','Meccan','Medinan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Medinan','Meccan','Medinan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Medinan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Medinan','Medinan','Medinan','Meccan','Meccan','Meccan','Meccan','Meccan','Medinan','Meccan','Medinan','Medinan','Medinan','Medinan','Medinan','Medinan','Medinan','Medinan','Medinan','Medinan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Medinan','Medinan','Meccan','Medinan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Medinan','Medinan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Meccan','Medinan','Meccan','Meccan','Meccan','Meccan'];

  const SURAHS = SURAHS_AR.map((name, i) => ({
    n: i + 1,
    name: name,
    transliteration: SURAHS_EN[i] || '',
    type: TYPES[i] || 'Meccan',
    ayah_count: AYAH_COUNTS[i] || 0,
  }));

  function pad3(n) {
    return String(n).padStart(3, '0');
  }

  function audioUrl(reciterId, surahN, ayahN) {
    const r = RECITERS.find(x => x.id === reciterId) || RECITERS[0];
    return `https://everyayah.com/data/${r.slug}/${pad3(surahN)}${pad3(ayahN)}.mp3`;
  }

  // Cache to avoid refetching same surah
  const _cache = {};

  async function fetchSurah(n) {
    if (_cache[n]) return _cache[n];
    const url = `https://api.alquran.cloud/v1/surah/${n}/quran-uthmani`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('failed to fetch surah ' + n);
    const json = await res.json();
    const ayahs = (json.data?.ayahs || []).map(a => ({
      n: a.numberInSurah,
      text: a.text,
      juz: a.juz,
      page: a.page,
    }));
    const out = {
      n: n,
      name: SURAHS_AR[n - 1],
      transliteration: SURAHS_EN[n - 1],
      ayahs: ayahs,
      audio_url: (reciterId, ayahN) => audioUrl(reciterId, n, ayahN),
    };
    _cache[n] = out;
    return out;
  }

  function formatAyahNumber(n) {
    const map = ['٠','١','٢','٣','٤','٥','٦','٧','٨','٩'];
    return String(n).split('').map(d => /\d/.test(d) ? map[+d] : d).join('');
  }

  global.ZitexQuran = {
    RECITERS: RECITERS,
    SURAHS: SURAHS,
    fetchSurah: fetchSurah,
    audioUrl: audioUrl,
    formatAyahNumber: formatAyahNumber,
  };
})(window);
