"""
Interactive per-ayah Quran player widget for FreeBuild v2.

Usage (architect AI side):
    Insert a placeholder:
        @@QURAN_PLAYER/{surah_number}@@
    or
        @@QURAN_PLAYER/{surah_number}/style={classic|modern|minimal|royal}@@

Server-side post-processor replaces it with a fully self-contained widget:
    • Reciter avatar strip (horizontal scroll, click to select)
    • Verse-by-verse text fetched from alquran.cloud at runtime
    • Click any verse → plays that ayah with the active reciter
    • Repeat-toggle (loop current ayah)
    • Highlight currently-playing ayah with amber glow
    • Continuous-play mode (next ayah auto-plays)

Real CDN used: everyayah.com
    Per-ayah URL pattern:
        https://everyayah.com/data/{RECITER_KEY}/{surah:03d}{ayah:03d}.mp3
    Verified working for all 14 reciter keys below.

The whole widget is self-contained (inline CSS + vanilla JS) so the architect's
HTML stays clean — no external scripts, no dependencies, works offline once
loaded except for the audio CDN fetches.
"""
from __future__ import annotations
import re
from typing import Dict, List


# ═════════════════════════════════════════════════════════════════════════
#  RECITERS WITH PER-AYAH AUDIO (everyayah.com)
# ═════════════════════════════════════════════════════════════════════════
# Mapping of display name → everyayah folder slug. All verified 2026-05.
AYAH_RECITERS: List[Dict[str, str]] = [
    {"id": "alafasy",     "name": "مشاري العفاسي",     "slug": "Alafasy_128kbps"},
    {"id": "sudais",      "name": "عبد الرحمن السديس",  "slug": "Abdurrahmaan_As-Sudais_192kbps"},
    {"id": "shuraim",     "name": "سعود الشريم",       "slug": "Saood_ash-Shuraym_128kbps"},
    {"id": "husary",      "name": "محمود الحصري",      "slug": "Husary_128kbps"},
    {"id": "minshawi",    "name": "محمد المنشاوي",     "slug": "Minshawi_Murattal_128kbps"},
    {"id": "abdulbasit",  "name": "عبد الباسط",        "slug": "Abdul_Basit_Murattal_192kbps"},
    {"id": "ghamdi",      "name": "سعد الغامدي",       "slug": "Ghamadi_40kbps"},
    {"id": "ajmi",        "name": "أحمد العجمي",       "slug": "ahmed_ibn_ali_al_ajamy_128kbps"},
    {"id": "dossary",     "name": "ياسر الدوسري",      "slug": "Yasser_Ad-Dussary_128kbps"},
    {"id": "shatri",      "name": "أبو بكر الشاطري",   "slug": "Abu_Bakr_Ash-Shaatree_128kbps"},
    {"id": "juhany",      "name": "عبد الله الجهني",   "slug": "abdullaah_3awwaad_al-juhaynee_128kbps"},
    {"id": "hthfi",       "name": "علي الحذيفي",       "slug": "Hudhaify_128kbps"},
    {"id": "ayyub",       "name": "محمد أيوب",         "slug": "Muhammad_Ayyoub_128kbps"},
    {"id": "maher",       "name": "ماهر المعيقلي",     "slug": "Maher_AlMuaiqly_64kbps"},
]


# ═════════════════════════════════════════════════════════════════════════
#  WIDGET STYLE VARIANTS (4 visual flavors)
# ═════════════════════════════════════════════════════════════════════════
_STYLE_PRESETS: Dict[str, Dict[str, str]] = {
    "classic": {
        "bg": "linear-gradient(180deg,#1a1208 0%,#0a0a14 100%)",
        "border": "#d4af37",
        "accent": "#d4af37",
        "text": "#f5e6c8",
        "ayah_bg": "rgba(212,175,55,0.04)",
        "ayah_hover": "rgba(212,175,55,0.12)",
        "font_family": "'Amiri Quran','Amiri',serif",
    },
    "modern": {
        "bg": "linear-gradient(135deg,#0f172a 0%,#1e293b 100%)",
        "border": "#06b6d4",
        "accent": "#22d3ee",
        "text": "#e0f2fe",
        "ayah_bg": "rgba(34,211,238,0.04)",
        "ayah_hover": "rgba(34,211,238,0.12)",
        "font_family": "'Scheherazade New','Amiri',serif",
    },
    "minimal": {
        "bg": "#fafaf9",
        "border": "#171717",
        "accent": "#171717",
        "text": "#0c0a09",
        "ayah_bg": "rgba(0,0,0,0.03)",
        "ayah_hover": "rgba(0,0,0,0.08)",
        "font_family": "'Noto Naskh Arabic',serif",
    },
    "royal": {
        "bg": "linear-gradient(180deg,#1e1b4b 0%,#0c0a2c 100%)",
        "border": "#a78bfa",
        "accent": "#c4b5fd",
        "text": "#ede9fe",
        "ayah_bg": "rgba(167,139,250,0.05)",
        "ayah_hover": "rgba(167,139,250,0.15)",
        "font_family": "'Amiri Quran',serif",
    },
}


def _render_widget(surah: int, style_key: str = "classic", instance_id: str = "q1") -> str:
    """Render a full self-contained Quran player widget."""
    style = _STYLE_PRESETS.get(style_key, _STYLE_PRESETS["classic"])
    reciter_json = (
        "[" + ",".join(
            '{"id":"%s","name":"%s","slug":"%s"}' % (r["id"], r["name"], r["slug"])
            for r in AYAH_RECITERS
        ) + "]"
    )

    return f"""
<div class="zerax-qp" data-instance="{instance_id}" data-surah="{surah}" style="
  background:{style['bg']};
  border:2px solid {style['border']};
  border-radius:1.5rem;
  padding:2rem;
  margin:2rem 0;
  font-family:{style['font_family']};
  color:{style['text']};
  max-width:900px;
  margin-inline:auto;
  box-shadow:0 20px 60px rgba(0,0,0,0.4);">

  <!-- Reciter strip -->
  <div class="zqp-reciters" style="
    display:flex;
    gap:.75rem;
    overflow-x:auto;
    padding-bottom:1rem;
    margin-bottom:1.5rem;
    border-bottom:1px solid {style['border']}55;
    scroll-snap-type:x proximity;">
  </div>

  <!-- Surah heading -->
  <div style="text-align:center;margin-bottom:1.5rem;">
    <div class="zqp-surah-name" style="
      font-size:2rem;
      font-weight:900;
      color:{style['accent']};
      letter-spacing:.05em;"></div>
    <div class="zqp-surah-meta" style="
      font-size:.85rem;
      opacity:.7;
      margin-top:.35rem;"></div>
  </div>

  <!-- Controls -->
  <div style="
    display:flex;
    gap:.5rem;
    flex-wrap:wrap;
    justify-content:center;
    margin-bottom:1.5rem;
    font-size:.85rem;">
    <button class="zqp-btn zqp-btn-repeat" data-active="0" style="
      padding:.5rem 1rem;
      background:transparent;
      color:{style['accent']};
      border:1px solid {style['accent']}88;
      border-radius:2rem;
      cursor:pointer;
      font-family:inherit;">🔁 تكرار الآية</button>
    <button class="zqp-btn zqp-btn-auto" data-active="1" style="
      padding:.5rem 1rem;
      background:{style['accent']}22;
      color:{style['accent']};
      border:1px solid {style['accent']};
      border-radius:2rem;
      cursor:pointer;
      font-family:inherit;">▶ تشغيل متصل</button>
    <button class="zqp-btn zqp-btn-prev" style="
      padding:.5rem 1rem;
      background:transparent;
      color:{style['accent']};
      border:1px solid {style['accent']}88;
      border-radius:2rem;
      cursor:pointer;
      font-family:inherit;">⏮ سابقة</button>
    <button class="zqp-btn zqp-btn-next" style="
      padding:.5rem 1rem;
      background:transparent;
      color:{style['accent']};
      border:1px solid {style['accent']}88;
      border-radius:2rem;
      cursor:pointer;
      font-family:inherit;">⏭ التالية</button>
  </div>

  <!-- Now playing indicator -->
  <div class="zqp-now-playing" style="
    text-align:center;
    font-size:.85rem;
    opacity:0;
    color:{style['accent']};
    margin-bottom:1rem;
    transition:opacity .3s;
    min-height:1.25rem;">
  </div>

  <!-- Verses grid -->
  <div class="zqp-verses" style="
    display:flex;
    flex-direction:column;
    gap:.5rem;
    max-height:60vh;
    overflow-y:auto;
    padding:.5rem;">
    <div class="zqp-loading" style="text-align:center;padding:3rem;opacity:.6">
      جاري تحميل السورة…
    </div>
  </div>

  <!-- Hidden audio element -->
  <audio class="zqp-audio" preload="none" crossorigin="anonymous"></audio>
</div>

<script>
(function(){{
  var root = document.querySelector('.zqp-{instance_id}') ||
             document.querySelector('.zerax-qp[data-instance="{instance_id}"]');
  if(!root || root.dataset.zqpInit === '1') return;
  root.dataset.zqpInit = '1';

  var RECITERS = {reciter_json};
  var SURAH = parseInt(root.dataset.surah || '1', 10);
  var state = {{
    reciter: RECITERS[0],
    currentAyah: 1,
    totalAyahs: 0,
    repeat: false,
    autoplay: true,
    surahNameAr: '',
  }};

  var recitersBar = root.querySelector('.zqp-reciters');
  var versesBox   = root.querySelector('.zqp-verses');
  var audio       = root.querySelector('.zqp-audio');
  var nowPlaying  = root.querySelector('.zqp-now-playing');
  var nameDiv     = root.querySelector('.zqp-surah-name');
  var metaDiv     = root.querySelector('.zqp-surah-meta');
  var btnRepeat   = root.querySelector('.zqp-btn-repeat');
  var btnAuto     = root.querySelector('.zqp-btn-auto');
  var btnPrev     = root.querySelector('.zqp-btn-prev');
  var btnNext     = root.querySelector('.zqp-btn-next');

  var accent = '{style['accent']}';
  var ayahHover = '{style['ayah_hover']}';
  var ayahBg = '{style['ayah_bg']}';

  function pad3(n){{ return (''+n).padStart(3,'0'); }}

  function ayahUrl(surah, ayah){{
    return 'https://everyayah.com/data/'+state.reciter.slug+'/'+pad3(surah)+pad3(ayah)+'.mp3';
  }}

  function buildReciterChip(r, idx){{
    var initials = r.name.split(' ').map(function(w){{return w.charAt(0);}}).join('').slice(0,2);
    var chip = document.createElement('button');
    chip.className = 'zqp-rchip';
    chip.dataset.reciterId = r.id;
    chip.style.cssText =
      'flex:0 0 auto;display:flex;flex-direction:column;align-items:center;gap:.4rem;'+
      'padding:.6rem .75rem;background:transparent;border:1.5px solid transparent;'+
      'border-radius:1rem;cursor:pointer;color:inherit;font-family:inherit;'+
      'transition:all .2s;scroll-snap-align:start';
    var av = document.createElement('div');
    av.style.cssText =
      'width:48px;height:48px;border-radius:50%;background:'+accent+'26;'+
      'display:flex;align-items:center;justify-content:center;font-weight:900;'+
      'color:'+accent+';font-size:1rem;border:2px solid '+accent+'55';
    av.textContent = initials;
    var lbl = document.createElement('div');
    lbl.style.cssText = 'font-size:.7rem;max-width:90px;text-align:center;line-height:1.2';
    lbl.textContent = r.name;
    chip.appendChild(av);
    chip.appendChild(lbl);
    chip.onclick = function(){{ selectReciter(r.id); }};
    return chip;
  }}

  function renderReciters(){{
    recitersBar.innerHTML = '';
    RECITERS.forEach(function(r,i){{
      recitersBar.appendChild(buildReciterChip(r,i));
    }});
    highlightReciter();
  }}

  function highlightReciter(){{
    Array.prototype.forEach.call(recitersBar.querySelectorAll('.zqp-rchip'), function(chip){{
      var active = chip.dataset.reciterId === state.reciter.id;
      chip.style.borderColor = active ? accent : 'transparent';
      chip.style.background  = active ? accent+'15' : 'transparent';
    }});
  }}

  function selectReciter(id){{
    var r = RECITERS.find(function(x){{return x.id === id;}});
    if(!r) return;
    state.reciter = r;
    highlightReciter();
    // If something is currently playing, swap to new reciter for same ayah
    if(!audio.paused){{ playAyah(state.currentAyah); }}
  }}

  function setAyahStyle(el, playing){{
    el.style.background  = playing ? accent+'22' : ayahBg;
    el.style.borderColor = playing ? accent : 'transparent';
    el.style.boxShadow   = playing ? '0 0 24px '+accent+'55' : 'none';
  }}

  function loadSurah(){{
    fetch('https://api.alquran.cloud/v1/surah/'+SURAH+'/ar.alafasy')
      .then(function(r){{ return r.json(); }})
      .then(function(d){{
        if(!d || d.code !== 200){{ throw new Error('api failed'); }}
        var s = d.data;
        state.totalAyahs = s.numberOfAyahs;
        state.surahNameAr = s.name;
        nameDiv.textContent = s.name + ' (' + s.englishName + ')';
        metaDiv.textContent = s.revelationType + ' • ' + s.numberOfAyahs + ' آية';

        versesBox.innerHTML = '';
        s.ayahs.forEach(function(a){{
          var row = document.createElement('div');
          row.className = 'zqp-ayah-row';
          row.dataset.ayah = a.numberInSurah;
          row.style.cssText =
            'padding:.9rem 1.1rem;background:'+ayahBg+';border:2px solid transparent;'+
            'border-radius:.75rem;cursor:pointer;transition:all .3s;line-height:2.4;'+
            'font-size:1.35rem;text-align:right;direction:rtl';
          row.addEventListener('mouseenter', function(){{
            if(row.style.borderColor !== accent){{ row.style.background = ayahHover; }}
          }});
          row.addEventListener('mouseleave', function(){{
            if(row.style.borderColor !== accent){{ row.style.background = ayahBg; }}
          }});
          var badge = document.createElement('span');
          badge.style.cssText =
            'display:inline-block;min-width:2.2rem;height:2.2rem;line-height:2.2rem;'+
            'text-align:center;border-radius:50%;background:'+accent+'22;color:'+accent+';'+
            'font-size:.9rem;font-weight:700;margin-left:.75rem;font-family:system-ui';
          badge.textContent = a.numberInSurah;
          var text = document.createElement('span');
          text.textContent = a.text;
          row.appendChild(badge);
          row.appendChild(text);
          row.onclick = function(){{ playAyah(parseInt(row.dataset.ayah,10)); }};
          versesBox.appendChild(row);
        }});
      }})
      .catch(function(e){{
        versesBox.innerHTML = '<div style="padding:2rem;text-align:center;opacity:.7">'+
          'تعذّر تحميل السورة. تحقق من الاتصال.</div>';
      }});
  }}

  function playAyah(n){{
    if(n < 1 || n > state.totalAyahs) return;
    state.currentAyah = n;
    // Reset previous highlights
    Array.prototype.forEach.call(versesBox.querySelectorAll('.zqp-ayah-row'), function(r){{
      setAyahStyle(r, false);
    }});
    var row = versesBox.querySelector('.zqp-ayah-row[data-ayah="'+n+'"]');
    if(row){{
      setAyahStyle(row, true);
      row.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}
    nowPlaying.style.opacity = '1';
    nowPlaying.textContent = 'يتلو الآن: ' + state.reciter.name + ' — الآية ' + n;
    audio.src = ayahUrl(SURAH, n);
    audio.play().catch(function(e){{
      nowPlaying.textContent = 'اضغط على أي آية للاستماع — '+state.reciter.name;
    }});
  }}

  audio.addEventListener('ended', function(){{
    if(state.repeat){{
      playAyah(state.currentAyah);
      return;
    }}
    if(state.autoplay && state.currentAyah < state.totalAyahs){{
      playAyah(state.currentAyah + 1);
    }}else{{
      nowPlaying.textContent = 'انتهت السورة';
      setTimeout(function(){{ nowPlaying.style.opacity='0'; }}, 2000);
    }}
  }});

  btnRepeat.onclick = function(){{
    state.repeat = !state.repeat;
    btnRepeat.style.background = state.repeat ? accent+'22' : 'transparent';
    btnRepeat.textContent = state.repeat ? '🔁 التكرار فعّال' : '🔁 تكرار الآية';
  }};
  btnAuto.onclick = function(){{
    state.autoplay = !state.autoplay;
    btnAuto.style.background = state.autoplay ? accent+'22' : 'transparent';
    btnAuto.textContent = state.autoplay ? '▶ تشغيل متصل' : '⏸ متصل معطّل';
  }};
  btnPrev.onclick = function(){{ playAyah(Math.max(1, state.currentAyah - 1)); }};
  btnNext.onclick = function(){{ playAyah(Math.min(state.totalAyahs, state.currentAyah + 1)); }};

  renderReciters();
  loadSurah();
}})();
</script>
""".strip()


# ═════════════════════════════════════════════════════════════════════════
#  POST-PROCESSOR — replace @@QURAN_PLAYER/...@@ placeholders
# ═════════════════════════════════════════════════════════════════════════
_PH_RE = re.compile(
    r"@@QURAN_PLAYER/(\d{1,3})(?:/style=(\w+))?@@"
)


def inject_quran_players(html: str) -> str:
    """Replace every @@QURAN_PLAYER/N@@ or @@QURAN_PLAYER/N/style=X@@ placeholder
    with a fully-rendered self-contained widget. Each instance gets a unique id
    so multiple players on the same page don't interfere."""
    if not html or "@@QURAN_PLAYER/" not in html:
        return html
    counter = {"n": 0}

    def _rep(m):
        counter["n"] += 1
        inst = f"q{counter['n']}"
        surah = int(m.group(1) or 1)
        if surah < 1:
            surah = 1
        if surah > 114:
            surah = 114
        style = (m.group(2) or "classic").lower()
        if style not in _STYLE_PRESETS:
            style = "classic"
        widget = _render_widget(surah, style, inst)
        # The widget expects `.zqp-{instance_id}` OR the data-instance attribute
        # selector — we already set data-instance. To be safe also add a class.
        widget = widget.replace(
            f'<div class="zerax-qp" data-instance="{inst}"',
            f'<div class="zerax-qp zqp-{inst}" data-instance="{inst}"',
            1,
        )
        return widget

    return _PH_RE.sub(_rep, html)
