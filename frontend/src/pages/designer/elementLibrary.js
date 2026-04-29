// Element library — stays in sync with backend `_element_svg()`
// Each entry: { type, name, icon, category, defaultWidth, defaultHeight, variants, hasColor }

export const ELEMENT_LIBRARY = [
  { type: 'castle', name: 'قلعة', icon: '🏰', category: 'buildings', w: 180, h: 160, variants: 1 },
  { type: 'house', name: 'بيت', icon: '🏠', category: 'buildings', w: 110, h: 100, variants: 4 },
  { type: 'farm', name: 'مزرعة', icon: '🚜', category: 'buildings', w: 130, h: 90, variants: 1 },
  { type: 'mine', name: 'منجم', icon: '⛏️', category: 'buildings', w: 120, h: 100, variants: 1 },

  { type: 'wheat_field', name: 'حقل قمح', icon: '🌾', category: 'fields', w: 130, h: 90, variants: 1 },
  { type: 'clay_field', name: 'حقل طين', icon: '🏺', category: 'fields', w: 130, h: 90, variants: 1 },
  { type: 'pond', name: 'بحيرة', icon: '💧', category: 'fields', w: 140, h: 90, variants: 1 },

  { type: 'tree', name: 'شجرة', icon: '🌲', category: 'nature', w: 70, h: 95, variants: 4 },
  { type: 'bush', name: 'شجيرة', icon: '🌿', category: 'nature', w: 50, h: 35, variants: 1 },
  { type: 'flower', name: 'زهرة', icon: '🌸', category: 'nature', w: 30, h: 40, variants: 5, hasColor: true },
  { type: 'rock', name: 'صخرة', icon: '🪨', category: 'nature', w: 50, h: 40, variants: 1 },
  { type: 'cloud', name: 'غيمة', icon: '☁️', category: 'nature', w: 140, h: 55, variants: 1 },

  { type: 'soldier', name: 'جندي', icon: '⚔️', category: 'units', w: 45, h: 70, variants: 1 },

  { type: 'circle', name: 'دائرة', icon: '⭕', category: 'shapes', w: 80, h: 80, variants: 1, hasColor: true },
  { type: 'rect', name: 'مربع', icon: '⬛', category: 'shapes', w: 100, h: 100, variants: 1, hasColor: true },
  { type: 'star', name: 'نجمة', icon: '⭐', category: 'shapes', w: 60, h: 60, variants: 1 },
  { type: 'text', name: 'نص', icon: 'T', category: 'shapes', w: 160, h: 40, variants: 1, hasColor: true, hasText: true },
];

export const CATEGORIES = [
  { id: 'buildings', name: 'مباني', icon: '🏛️' },
  { id: 'fields', name: 'حقول', icon: '🌾' },
  { id: 'nature', name: 'طبيعة', icon: '🌳' },
  { id: 'units', name: 'وحدات', icon: '⚔️' },
  { id: 'shapes', name: 'أشكال', icon: '⭕' },
];

// Returns SVG markup given the element spec — must match backend output
export function elementSvg(type, props = {}) {
  const v = props.variant || 0;
  const color = props.color;

  if (type === 'castle') return `<svg viewBox="0 0 120 110" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="cg${Math.random().toString(36).slice(2,7)}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#A08060"/><stop offset="100%" stop-color="#7A6040"/></linearGradient></defs><rect x="25" y="45" width="70" height="55" fill="#8B7050" rx="3"/><rect x="10" y="28" width="18" height="72" fill="#8B7355"/><rect x="92" y="28" width="18" height="72" fill="#8B7355"/><rect x="48" y="22" width="24" height="78" fill="#9B8465"/><polygon points="10,28 19,10 28,28" fill="#C41E3A"/><polygon points="92,28 101,10 110,28" fill="#C41E3A"/><polygon points="48,22 60,5 72,22" fill="#C41E3A"/><rect x="50" y="62" width="20" height="38" fill="#4A3322" rx="10"/><rect x="30" y="52" width="12" height="12" fill="#87CEEB" rx="2"/><rect x="78" y="52" width="12" height="12" fill="#87CEEB" rx="2"/><polygon points="54,8 63,0 72,8" fill="#FFD700"/></svg>`;

  if (type === 'house') {
    const cs = [['#D4A574','#8B4513'], ['#C49464','#7A3A12'], ['#B88454','#6B3010'], ['#DDB584','#9B5523']];
    const [c, r] = cs[v % 4];
    return `<svg viewBox="0 0 80 70" xmlns="http://www.w3.org/2000/svg"><rect x="10" y="35" width="60" height="35" fill="${c}" rx="2"/><polygon points="5,35 40,12 75,35" fill="${r}"/><rect x="30" y="45" width="14" height="25" fill="#4A3322" rx="5"/><rect x="13" y="40" width="11" height="10" fill="#87CEEB" rx="1"/><rect x="56" y="40" width="11" height="10" fill="#87CEEB" rx="1"/><rect x="62" y="16" width="6" height="19" fill="#8B7355"/></svg>`;
  }

  if (type === 'tree') {
    const gs = ['#2D8B2D', '#1E7A1E', '#3AA63A', '#228B22'];
    const g1 = color || gs[v % 4]; const g2 = gs[(v + 1) % 4];
    return `<svg viewBox="0 0 60 80" xmlns="http://www.w3.org/2000/svg"><rect x="25" y="52" width="10" height="23" fill="#6B4226" rx="3"/><ellipse cx="30" cy="35" rx="24" ry="26" fill="${g1}"/><ellipse cx="22" cy="30" rx="14" ry="16" fill="${g2}" opacity="0.9"/><ellipse cx="38" cy="32" rx="13" ry="15" fill="${g1}" opacity="0.85"/></svg>`;
  }

  if (type === 'wheat_field') return `<svg viewBox="0 0 90 60" xmlns="http://www.w3.org/2000/svg"><rect x="5" y="15" width="80" height="40" fill="#8B6914" rx="4"/><line x1="5" y1="25" x2="85" y2="25" stroke="#6B4F12" stroke-width="1"/><line x1="5" y1="35" x2="85" y2="35" stroke="#6B4F12" stroke-width="1"/><line x1="5" y1="45" x2="85" y2="45" stroke="#6B4F12" stroke-width="1"/><rect x="12" y="18" width="3" height="12" fill="#228B22"/><rect x="22" y="18" width="3" height="14" fill="#228B22"/><rect x="32" y="18" width="3" height="11" fill="#228B22"/><rect x="42" y="18" width="3" height="13" fill="#228B22"/><rect x="52" y="18" width="3" height="12" fill="#228B22"/><rect x="62" y="18" width="3" height="14" fill="#228B22"/><rect x="72" y="18" width="3" height="11" fill="#228B22"/><circle cx="22" cy="16" r="4" fill="#FFD700"/><circle cx="42" cy="16" r="4" fill="#FFD700"/><circle cx="62" cy="16" r="4" fill="#FFD700"/></svg>`;

  if (type === 'clay_field') return `<svg viewBox="0 0 90 60" xmlns="http://www.w3.org/2000/svg"><rect x="5" y="15" width="80" height="40" fill="#C08060" rx="4"/><ellipse cx="20" cy="35" rx="10" ry="6" fill="#A56040" opacity=".6"/><ellipse cx="55" cy="40" rx="12" ry="7" fill="#9F5030" opacity=".55"/><ellipse cx="72" cy="28" rx="8" ry="5" fill="#B87858" opacity=".5"/><circle cx="30" cy="28" r="3" fill="#6D4025"/><circle cx="62" cy="50" r="3" fill="#6D4025"/><circle cx="15" cy="48" r="2.5" fill="#6D4025"/></svg>`;

  if (type === 'farm') return elementSvg('wheat_field', props);

  if (type === 'soldier') return `<svg viewBox="0 0 40 60" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="12" r="8" fill="#FDBCB4"/><rect x="12" y="20" width="16" height="20" fill="#C41E3A" rx="3"/><rect x="7" y="22" width="7" height="14" fill="#A01030" rx="2"/><rect x="26" y="22" width="7" height="14" fill="#A01030" rx="2"/><rect x="14" y="40" width="5" height="14" fill="#4A3728" rx="2"/><rect x="21" y="40" width="5" height="14" fill="#4A3728" rx="2"/><ellipse cx="20" cy="5" rx="10" ry="4" fill="#808080"/><circle cx="16" cy="10" r="1.5" fill="#333"/><circle cx="24" cy="10" r="1.5" fill="#333"/></svg>`;

  if (type === 'mine') return `<svg viewBox="0 0 80 60" xmlns="http://www.w3.org/2000/svg"><polygon points="20,55 40,15 60,55" fill="#696969"/><polygon points="10,55 25,25 40,55" fill="#808080"/><polygon points="45,55 60,20 75,55" fill="#A9A9A9"/><rect x="35" y="30" width="5" height="20" fill="#6B4226"/><polygon points="32,30 40,18 48,30" fill="#555"/><circle cx="28" cy="42" r="4" fill="#FFD700"/><circle cx="55" cy="48" r="3" fill="#FFD700"/></svg>`;

  if (type === 'rock') return `<svg viewBox="0 0 40 30" xmlns="http://www.w3.org/2000/svg"><polygon points="8,28 20,8 35,28" fill="#808080"/><polygon points="2,28 12,15 22,28" fill="#696969"/></svg>`;

  if (type === 'flower') {
    const cs = ['#FF6B6B', '#FFD700', '#FF69B4', '#9370DB', '#FF8C00'];
    const cl = color || cs[v % 5];
    return `<svg viewBox="0 0 20 25" xmlns="http://www.w3.org/2000/svg"><rect x="9" y="12" width="2" height="13" fill="#228B22"/><circle cx="10" cy="9" r="5" fill="${cl}"/><circle cx="10" cy="9" r="2.5" fill="#FFD700"/></svg>`;
  }

  if (type === 'bush') return `<svg viewBox="0 0 40 25" xmlns="http://www.w3.org/2000/svg"><ellipse cx="20" cy="15" rx="18" ry="10" fill="#2D8B2D"/><ellipse cx="12" cy="13" rx="10" ry="8" fill="#3AA63A"/><ellipse cx="28" cy="14" rx="9" ry="7" fill="#248F24"/></svg>`;

  if (type === 'cloud') return `<svg viewBox="0 0 120 45" xmlns="http://www.w3.org/2000/svg"><ellipse cx="60" cy="28" rx="50" ry="16" fill="white" opacity=".9"/><ellipse cx="35" cy="22" rx="30" ry="14" fill="white" opacity=".92"/><ellipse cx="85" cy="24" rx="28" ry="12" fill="white" opacity=".88"/></svg>`;

  if (type === 'pond') return `<svg viewBox="0 0 80 50" xmlns="http://www.w3.org/2000/svg"><ellipse cx="40" cy="25" rx="38" ry="22" fill="#4DA6FF"/><ellipse cx="40" cy="22" rx="32" ry="17" fill="#87CEEB" opacity=".6"/><circle cx="25" cy="18" r="2" fill="white" opacity=".8"/></svg>`;

  if (type === 'circle') {
    const cl = color || '#FFD700';
    return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="48" fill="${cl}"/></svg>`;
  }

  if (type === 'rect') {
    const cl = color || '#4a3aff';
    return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="100" height="100" fill="${cl}" rx="8"/></svg>`;
  }

  if (type === 'star') return `<svg viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg"><polygon points="25,3 31,18 48,19 35,30 39,47 25,38 11,47 15,30 2,19 19,18" fill="#FFD700" stroke="#B8860B" stroke-width="1.5"/></svg>`;

  if (type === 'text') {
    const txt = (props.text || 'نص').replace(/</g, '&lt;').slice(0, 40);
    const cl = color || '#FFD700';
    const sz = props.font_size || 24;
    return `<svg viewBox="0 0 200 40" xmlns="http://www.w3.org/2000/svg"><text x="100" y="26" text-anchor="middle" font-family="Tajawal,sans-serif" font-size="${sz}" fill="${cl}" font-weight="900">${txt}</text></svg>`;
  }

  return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100" fill="#888"/></svg>`;
}

export function svgToDataUrl(svg) {
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}
