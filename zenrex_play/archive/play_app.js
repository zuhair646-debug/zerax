// Zenrex Play — Clean Build (v1)
'use strict';

const API = '/api/freebuild-chat';
const $ = (s, ctx = document) => ctx.querySelector(s);
const $$ = (s, ctx = document) => Array.from(ctx.querySelectorAll(s));
const STATE = {
  role: localStorage.getItem('zp_role') || '',
  email: localStorage.getItem('zp_email') || '',
  name: localStorage.getItem('zp_name') || '',
  token: localStorage.getItem('zp_token') || '',
  category: 'all',
  videos: [],
  categories: [],
  parentTasks: [],
  dhikrList: []
};
const headers = () => STATE.token ? { Authorization: 'Bearer ' + STATE.token } : {};

// ════════ AUTH ════════
async function loadKidsForLogin() {
  try {
    const r = await fetch(API + '/kids/accounts/public');
    const d = await r.json();
    const sel = $('#ai-kid-pick');
    sel.innerHTML = '<option value="">-- اختر طفل --</option>';
    (d.items || []).forEach(k => {
      const o = document.createElement('option');
      o.value = k.email; o.textContent = k.name;
      sel.appendChild(o);
    });
  } catch (e) { console.warn('kids list', e); }
}
$$('.auth-tab').forEach(t => t.onclick = () => {
  $$('.auth-tab').forEach(x => x.classList.toggle('on', x === t));
  $('#auth-child').style.display = t.dataset.role === 'child' ? '' : 'none';
  $('#auth-parent').style.display = t.dataset.role === 'parent' ? '' : 'none';
});
$('#ai-login').onclick = async () => {
  const role = $('.auth-tab.on').dataset.role;
  $('#ai-err').textContent = '';
  try {
    if (role === 'child') {
      const email = $('#ai-kid-pick').value;
      const pin = $('#ai-kid-pin').value;
      if (!email || !pin) { $('#ai-err').textContent = 'اختر طفل + رقم سري'; return; }
      const fd = new FormData(); fd.append('email', email); fd.append('pin', pin);
      const r = await fetch(API + '/kids/login', { method: 'POST', body: fd });
      const d = await r.json();
      if (!r.ok || !d.ok) { $('#ai-err').textContent = d.detail || 'فشل الدخول'; return; }
      STATE.role = 'child'; STATE.email = d.email; STATE.name = d.name; STATE.token = '';
    } else {
      const email = $('#ai-p-email').value.trim();
      const pwd = $('#ai-p-pwd').value;
      if (!email || !pwd) { $('#ai-err').textContent = 'املأ كل الحقول'; return; }
      const r = await fetch('/api/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password: pwd })
      });
      const d = await r.json();
      if (!r.ok || !d.token) { $('#ai-err').textContent = d.detail || 'فشل الدخول'; return; }
      STATE.role = 'parent'; STATE.email = email; STATE.name = d.user?.name || 'ولي الأمر'; STATE.token = d.token;
    }
    localStorage.setItem('zp_role', STATE.role);
    localStorage.setItem('zp_email', STATE.email);
    localStorage.setItem('zp_name', STATE.name);
    localStorage.setItem('zp_token', STATE.token);
    enterApp();
  } catch (e) { $('#ai-err').textContent = 'خطأ: ' + e.message; }
};
$('#logout-fab').onclick = () => {
  if (!confirm('تسجيل الخروج؟')) return;
  ['zp_role','zp_email','zp_name','zp_token'].forEach(k => localStorage.removeItem(k));
  location.reload();
};

// ════════ ENTER APP ════════
async function enterApp() {
  $('#auth-screen').classList.add('hide');
  $('#app').classList.add('on');
  document.body.dataset.role = STATE.role;
  if (STATE.role === 'parent') {
    // Show parent screen directly
    showScreen('parent');
    buildParentDashboard('videos');
    $('#nav').style.display = 'none';
    $('.cat-fab').style.display = 'none';
  } else {
    // Child: load feed
    await loadCategories();
    await loadVideos();
    await loadDhikr();
    await loadParentTasks();
    showScreen('home');
  }
}

// ════════ NAV ════════
$$('.nav-btn').forEach(b => b.onclick = () => {
  $$('.nav-btn').forEach(x => x.classList.toggle('on', x === b));
  showScreen(b.dataset.nav);
});
function showScreen(name) {
  $('#feed').style.display = name === 'home' ? '' : 'none';
  $('.top-bar').style.display = (name === 'home' && STATE.role === 'child') ? 'flex' : 'none';
  $$('.screen').forEach(s => s.classList.remove('on'));
  if (name === 'home') {
    isolateAudio();
    eagerPrefetch();
  } else if (name === 'religion') {
    $('#religion-screen').classList.add('on');
    renderReligionScreen();
  } else if (name === 'quran') {
    $('#quran-home-screen').classList.add('on');
    renderQuranHome();
  } else if (name === 'tasks') {
    $('#tasks-screen').classList.add('on');
    renderTasksScreen();
  } else if (name === 'profile') {
    $('#profile-screen').classList.add('on');
    renderProfileScreen();
  } else if (name === 'parent') {
    $('#parent-screen').classList.add('on');
  }
}

// ════════ VIDEO FEED ════════
async function loadVideos() {
  try {
    const r = await fetch(API + '/kids/bot/approved?_=' + Date.now());
    const d = await r.json();
    const items = (d.items || []).filter(v => v.url);
    // Smart shuffle: every login = fresh order. Uses a Fisher-Yates with seeded
    // randomness based on session ID, then mixes old (>3 days) and new (<3 days)
    // alternately to keep variety.
    const now = Date.now();
    const fresh = [], old = [];
    items.forEach(v => {
      const created = new Date(v.created_at || 0).getTime();
      const ageDays = (now - created) / 86400000;
      if (ageDays <= 3) fresh.push(v); else old.push(v);
    });
    // Shuffle each group independently
    function shuf(a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
    shuf(fresh); shuf(old);
    // Interleave: 1 fresh, 1 old, 1 fresh, 1 old... (so user always sees variety)
    const merged = [];
    const max = Math.max(fresh.length, old.length);
    for (let i = 0; i < max; i++) {
      if (fresh[i]) merged.push(fresh[i]);
      if (old[i]) merged.push(old[i]);
    }
    STATE.videos = merged;
    renderFeed();
  } catch (e) { console.error('loadVideos', e); }
}
function renderFeed() {
  const feed = $('#feed');
  const filtered = STATE.category === 'all'
    ? STATE.videos
    : STATE.videos.filter(v => (v.category || '') === STATE.category);
  if (!filtered.length) {
    feed.innerHTML = '<div class="feed-empty"><div class="ic">📹</div><div>لا توجد فيديوهات في هذا التصنيف</div></div>';
    return;
  }
  feed.innerHTML = filtered.map((v, i) => `
    <div class="video-slide" data-idx="${i}" data-cat="${v.category || ''}">
      <video src="${v.url}" preload="${i < 3 ? 'auto' : 'metadata'}" playsinline loop muted></video>
      <div class="video-info">
        <div class="vt">${(v.title || 'فيديو').slice(0, 80)}</div>
        ${v.category ? `<span class="vc">${getCatIcon(v.category)} ${getCatTitle(v.category)}</span>` : ''}
      </div>
    </div>
  `).join('');
  setupFeedObserver();
  setupAudioUnlock();
}
let feedObserver = null;
function setupFeedObserver() {
  if (feedObserver) feedObserver.disconnect();
  feedObserver = new IntersectionObserver(entries => {
    entries.forEach(en => {
      const v = en.target.querySelector('video');
      if (!v) return;
      if (en.intersectionRatio >= 0.6) {
        // Play this — pause + mute others
        $$('#feed video').forEach(other => {
          if (other !== v) { try { other.pause(); other.muted = true; } catch(_){} }
        });
        v.muted = !document.body.classList.contains('audio-on');
        v.play().catch(() => {});
        prefetchAhead();
      } else {
        try { v.pause(); v.muted = true; } catch(_){}
      }
    });
  }, { root: $('#feed'), threshold: [0, 0.6, 1] });
  $$('#feed .video-slide').forEach(s => feedObserver.observe(s));
}
function setupAudioUnlock() {
  if (document.body._unlocked) return;
  document.body._unlocked = true;
  const unlock = () => {
    document.body.classList.add('audio-on');
    $$('#feed video').forEach(v => {
      // Only unmute the currently playing one
      const r = v.getBoundingClientRect();
      const inView = r.top < innerHeight * 0.5 && r.bottom > innerHeight * 0.5;
      if (inView) { v.muted = false; v.play().catch(() => {}); }
    });
  };
  document.body.addEventListener('touchstart', unlock, { once: true });
  document.body.addEventListener('click', unlock, { once: true });
}
function isolateAudio() {
  $$('#feed video').forEach((v, i) => {
    const r = v.parentElement.getBoundingClientRect();
    const inView = r.top < innerHeight * 0.5 && r.bottom > innerHeight * 0.5;
    if (!inView) { try { v.pause(); v.muted = true; } catch(_){} }
  });
}
const prefetched = new Set();
async function prefetchVideo(url) {
  if (!url || prefetched.has(url)) return;
  prefetched.add(url);
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 8000);
    await fetch(url, { cache: 'force-cache', priority: 'low', signal: ctrl.signal });
  } catch(_){}
}
async function eagerPrefetch() {
  for (let i = 0; i < Math.min(5, STATE.videos.length); i++) {
    prefetchVideo(STATE.videos[i].url);
  }
}
function prefetchAhead() {
  const slides = $$('#feed .video-slide');
  let idx = 0;
  slides.forEach((s, i) => {
    const r = s.getBoundingClientRect();
    if (r.top < innerHeight * 0.5 && r.bottom > innerHeight * 0.5) idx = i;
  });
  for (let i = 1; i <= 3; i++) {
    const next = slides[idx + i];
    const v = next?.querySelector('video');
    if (v?.src) prefetchVideo(v.src);
  }
}

// ════════ CATEGORIES ════════
async function loadCategories() {
  try {
    const r = await fetch(API + '/kids/categories');
    const d = await r.json();
    STATE.categories = d.items || [];
    renderCatDrawer();
  } catch (e) { console.warn(e); }
}
function getCatIcon(id) { return STATE.categories.find(c => c.id === id)?.icon || '🎬'; }
function getCatTitle(id) { return STATE.categories.find(c => c.id === id)?.title || id; }
function renderCatDrawer() {
  const g = $('#cat-grid');
  g.innerHTML = STATE.categories.map(c => `
    <div class="item ${c.id === STATE.category ? 'on' : ''}" data-cid="${c.id}">
      <span class="ic">${c.icon || '🎬'}</span>
      <span class="t">${c.title}</span>
    </div>
  `).join('');
  g.querySelectorAll('.item').forEach(it => it.onclick = () => {
    STATE.category = it.dataset.cid;
    $('#cat-fab-label').textContent = it.querySelector('.t').textContent;
    renderFeed();
    closeCatDrawer();
  });
}
function openCatDrawer() { $('#cat-drawer').classList.add('on'); $('#cat-bd').classList.add('on'); }
function closeCatDrawer() { $('#cat-drawer').classList.remove('on'); $('#cat-bd').classList.remove('on'); }
$('#cat-fab').onclick = openCatDrawer;
$('#cat-bd').onclick = closeCatDrawer;

// ════════ RELIGION SCREEN ════════
async function loadDhikr() {
  try {
    const r = await fetch(API + '/kids/dhikr');
    const d = await r.json();
    STATE.dhikrList = d.items || [];
  } catch (e) { console.warn(e); }
}
function renderReligionScreen() {
  // Prayers (static list)
  const prayers = [
    { id: 'fajr', icon: '🌅', name: 'الفجر' },
    { id: 'dhuhr', icon: '🌞', name: 'الظهر' },
    { id: 'asr', icon: '🌤️', name: 'العصر' },
    { id: 'maghrib', icon: '🌇', name: 'المغرب' },
    { id: 'isha', icon: '🌙', name: 'العشاء' },
  ];
  $('#prayer-list').innerHTML = prayers.map(p => `
    <div class="list-item" data-pray="${p.id}">
      <span class="ic">${p.icon}</span>
      <div class="tx"><div class="ttl">${p.name}</div><div class="meta">صلِّ + سجّل صوتك = +10 نقاط</div></div>
      <button class="btn-sm btn-go" data-act="prayer-rec" data-pid="${p.id}" data-pname="${p.name}">📹</button>
    </div>
  `).join('');
  $('#prayer-list').querySelectorAll('button').forEach(b => b.onclick = () => openCamera('prayer', b.dataset.pid, b.dataset.pname, 10));
  // Dhikr
  $('#dhikr-list').innerHTML = STATE.dhikrList.map(d => `
    <div class="list-item" data-dh="${d.id}">
      <span class="ic">${d.icon || '📿'}</span>
      <div class="tx"><div class="ttl">${d.title}</div><div class="meta">×${d.target} = <b>+${d.points} نقطة</b></div></div>
      <button class="btn-sm btn-go">▶</button>
    </div>
  `).join('');
  $('#dhikr-list').querySelectorAll('.list-item').forEach(it => {
    it.onclick = () => {
      const d = STATE.dhikrList.find(x => x.id === it.dataset.dh);
      if (d) openDhikr(d);
    };
  });
}

// ════════ DHIKR COUNTER ════════
function openDhikr(d) {
  const ov = $('#dh-overlay');
  let count = 0, awarded = false;
  $('#dh-ic').textContent = d.icon || '📿';
  $('#dh-title').textContent = d.title;
  $('#dh-meta').textContent = `الهدف: ${d.target} • المكافأة: +${d.points} نقطة`;
  $('#dh-ct').textContent = '0';
  $('#dh-fill').style.width = '0%';
  $('#dh-done').textContent = '';
  ov.classList.remove('done-state');
  ov.classList.add('on');
  $('#dh-tap').onclick = async () => {
    if (awarded) return;
    count++;
    $('#dh-ct').textContent = count;
    $('#dh-fill').style.width = Math.min(100, count / d.target * 100) + '%';
    if (navigator.vibrate) navigator.vibrate(30);
    if (count >= d.target && !awarded) {
      awarded = true;
      await awardPoints('dhikr', d.points, { dhikr_id: d.id, title: d.title });
      $('#dh-done').textContent = `✨ أحسنت! +${d.points} نقطة`;
      ov.classList.add('done-state');
      if (navigator.vibrate) navigator.vibrate([100, 50, 100, 50, 200]);
      setTimeout(() => ov.classList.remove('on'), 3000);
    }
  };
}

// ════════ TASKS ════════
async function loadParentTasks() {
  try {
    const r = await fetch(API + '/kids/parent-tasks');
    const d = await r.json();
    STATE.parentTasks = d.items || [];
  } catch (e) { console.warn(e); }
}
function renderTasksScreen() {
  $('#tasks-list').innerHTML = STATE.parentTasks.map(t => `
    <div class="list-item" data-tk="${t.id}">
      <span class="ic">${t.icon || '✅'}</span>
      <div class="tx"><div class="ttl">${t.title}</div><div class="meta">${t.needs_before_after ? '📹📹 قبل + بعد ' : t.needs_camera ? '📹 ' : ''}<b>+${t.points} نقطة</b></div></div>
      <button class="btn-sm btn-go">${t.needs_before_after ? '📹📹 ابدأ' : t.needs_camera ? '📹 سجّل' : '✓ تم'}</button>
    </div>
  `).join('');
  $('#tasks-list').querySelectorAll('.list-item').forEach(it => {
    it.onclick = async () => {
      const t = STATE.parentTasks.find(x => x.id === it.dataset.tk);
      if (!t) return;
      if (t.needs_before_after) {
        // Two-step: before then after
        if (!confirm(`المهمة: "${t.title}"\n\nخطوة 1️⃣: صوّر الحالة قبل التنظيف/التنفيذ.\nاضغط موافق لفتح الكاميرا.`)) return;
        openCamera('task', t.id, t.title, Math.round(t.points / 2), 'before', () => {
          // After first upload done, prompt for "after"
          setTimeout(() => {
            if (confirm(`أحسنت! ✅\n\nخطوة 2️⃣: الحين نفذ المهمة (مثلاً نظّف). لما تخلص، اضغط موافق لتصوير الحالة بعد التنفيذ.`)) {
              openCamera('task', t.id, t.title, t.points - Math.round(t.points / 2), 'after');
            }
          }, 600);
        });
      } else if (t.needs_camera) openCamera('task', t.id, t.title, t.points, '');
      else {
        await awardPoints('task', t.points, { task_id: t.id, title: t.title });
        alert(`✅ +${t.points} نقطة!`);
      }
    };
  });
}

// ════════ CAMERA ════════
let mediaRecorder = null, recChunks = [], recStream = null, recStartedAt = 0, recTimer = null, recCtx = null;
async function openCamera(recType, taskId, taskTitle, points, phase = '', onDone = null) {
  recCtx = { recType, taskId, taskTitle, points, phase, onDone };
  const m = $('#cam');
  m.classList.add('on');
  try {
    recStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 720 }, height: { ideal: 1280 } },
      audio: { echoCancellation: true, noiseSuppression: true }
    });
    $('#cam-vid').srcObject = recStream;
  } catch (e) {
    alert('فشل فتح الكاميرا: ' + (e.name || e.message) + '\n\nتأكد من السماح للكاميرا في الإعدادات.');
    m.classList.remove('on');
  }
}
$('#cam-x').onclick = closeCam;
function closeCam() {
  if (recStream) { recStream.getTracks().forEach(t => t.stop()); recStream = null; }
  if (recTimer) { clearInterval(recTimer); recTimer = null; }
  $('#cam').classList.remove('on', 'recording');
  recChunks = []; mediaRecorder = null;
}
$('#cam-rec').onclick = () => {
  if (!recStream) return;
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();
  } else {
    recChunks = [];
    const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp9') ? 'video/webm;codecs=vp9'
      : MediaRecorder.isTypeSupported('video/webm') ? 'video/webm' : '';
    mediaRecorder = new MediaRecorder(recStream, mime ? { mimeType: mime } : {});
    mediaRecorder.ondataavailable = e => { if (e.data.size) recChunks.push(e.data); };
    mediaRecorder.onstop = uploadRecording;
    mediaRecorder.start();
    recStartedAt = Date.now();
    $('#cam').classList.add('recording');
    $('#cam-rec').textContent = 'إيقاف';
    $('#cam-rec').classList.add('recording');
    recTimer = setInterval(() => {
      const s = Math.floor((Date.now() - recStartedAt) / 1000);
      $('#cam-timer').textContent = `⏺ ${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;
    }, 500);
  }
};
async function uploadRecording() {
  $('#cam-rec').textContent = 'جاري الرفع...';
  const blob = new Blob(recChunks, { type: 'video/webm' });
  const fd = new FormData();
  const phaseSuffix = recCtx.phase ? `_${recCtx.phase}` : '';
  fd.append('file', blob, `${recCtx.recType}${phaseSuffix}_${Date.now()}.webm`);
  fd.append('child_email', STATE.email);
  fd.append('child_name', STATE.name);
  fd.append('audio_track', `${recCtx.recType}: ${recCtx.taskTitle}${recCtx.phase ? ' (' + recCtx.phase + ')' : ''}`);
  fd.append('rec_type', recCtx.recType);
  fd.append('task_id', recCtx.taskId);
  fd.append('task_title', recCtx.taskTitle + (recCtx.phase ? ' (' + (recCtx.phase === 'before' ? 'قبل' : 'بعد') + ')' : ''));
  fd.append('points', String(recCtx.points));
  fd.append('duration_sec', String((Date.now() - recStartedAt) / 1000));
  if (recCtx.phase) fd.append('phase', recCtx.phase);
  try {
    const r = await fetch(API + '/kids/recordings/upload', { method: 'POST', body: fd });
    const d = await r.json();
    if (d.ok) {
      const cb = recCtx.onDone;
      alert(`✅ تم! +${d.points_awarded || recCtx.points} نقطة`);
      if (cb) cb();
    } else {
      alert('❌ ' + (d.detail || 'فشل الرفع'));
    }
  } catch (e) {
    alert('❌ ' + e.message);
  }
  closeCam();
}

// ════════ POINTS ════════
async function awardPoints(kind, value, meta) {
  if (!STATE.email) return;
  const fd = new FormData();
  fd.append('child_email', STATE.email);
  fd.append('kind', kind);
  fd.append('value', String(value));
  fd.append('meta_json', JSON.stringify(meta || {}));
  try {
    const r = await fetch(API + '/kids/points/award', { method: 'POST', body: fd });
    return await r.json();
  } catch (e) { return null; }
}

// ════════ PROFILE ════════
async function renderProfileScreen() {
  $('#profile-stats').innerHTML = '<div style="grid-column:1/-1;text-align:center;opacity:.5;font-size:12px">⏳</div>';
  try {
    const r = await fetch(API + '/kids/points/summary?child_email=' + encodeURIComponent(STATE.email));
    const d = await r.json();
    $('#profile-stats').innerHTML = `
      <div class="stat-cell"><div class="v">${d.total_points || 0}</div><div class="l">⭐ نقاط</div></div>
      <div class="stat-cell"><div class="v">${d.today_points || 0}</div><div class="l">📅 اليوم</div></div>
      <div class="stat-cell"><div class="v">${d.streak_days || 0}</div><div class="l">🔥 streak</div></div>
      <div class="stat-cell"><div class="v">${(d.monthly_sar || 0).toFixed(1)}</div><div class="l">💰 ر.س</div></div>
    `;
    $('#profile-recent').innerHTML = (d.recent || []).slice(0, 10).map(e => `
      <div class="list-item">
        <span class="ic">${e.kind === 'dhikr' ? '📿' : e.kind === 'task' ? '🎯' : e.kind === 'prayer' ? '🕌' : '⭐'}</span>
        <div class="tx"><div class="ttl">${e.kind} +${e.value}</div><div class="meta">${(e.created_at || '').slice(0, 16).replace('T', ' ')}</div></div>
      </div>
    `).join('') || '<div style="opacity:.5;text-align:center;padding:14px;font-size:12px">لا نشاطات بعد</div>';
  } catch (e) { $('#profile-stats').innerHTML = '<div style="opacity:.5">خطأ</div>'; }
}

// ════════ PARENT DASHBOARD ════════
$$('#p-tabs .p-tab').forEach(b => b.onclick = () => {
  $$('#p-tabs .p-tab').forEach(x => x.classList.toggle('on', x === b));
  buildParentDashboard(b.dataset.pt);
});
function buildParentDashboard(pt) {
  const c = $('#p-content');
  c.innerHTML = '⏳';
  if (pt === 'videos') return pdVideos(c);
  if (pt === 'cats') return pdCats(c);
  if (pt === 'tasks') return pdTasks(c);
  if (pt === 'dhikr') return pdDhikr(c);
  if (pt === 'kids') return pdKids(c);
  if (pt === 'stats') return pdStats(c);
  if (pt === 'recordings') return pdRecordings(c);
  if (pt === 'quran-review') return pdQuranReview(c);
}
async function pdVideos(c) {
  c.innerHTML = `
    <div class="card">
      <h3>📥 إضافة فيديو بالرابط</h3>
      <div class="hint">انسخ رابط TikTok / YouTube → سيتم استخراج العنوان تلقائياً ثم تنزيل + تصنيف بالـ AI.</div>
      <div class="form-row"><input id="v-url" placeholder="https://..." dir="ltr" style="flex:1 1 100%"></div>
      <div class="form-row"><button class="btn-add" id="v-prev">🔍 معاينة</button><button class="btn-add" id="v-dl" disabled>📥 تحميل + AI</button></div>
      <div id="v-prev-out"></div>
      <div class="status" id="v-dl-st"></div>
    </div>
    <div class="card">
      <h3>📋 الفيديوهات (<span id="v-cnt">…</span>)</h3>
      <button class="btn-add" id="v-recat">🤖 إعادة تصنيف الكل بالـ AI</button>
      <div class="status" id="v-recat-st"></div>
      <div id="v-list" style="margin-top:10px"></div>
    </div>`;
  let meta = null;
  $('#v-prev').onclick = async () => {
    const url = $('#v-url').value.trim();
    if (!url) return alert('ضع رابط');
    $('#v-prev-out').innerHTML = '<div class="status wait show">⏳ جاري جلب المعلومات...</div>';
    try {
      const fd = new FormData(); fd.append('url', url);
      const r = await fetch(API + '/kids/video-metadata', { method: 'POST', headers: headers(), body: fd });
      meta = await r.json();
      $('#v-prev-out').innerHTML = `
        <div style="display:flex;gap:10px;padding:10px;background:rgba(0,0,0,.3);border-radius:10px;margin-top:8px">
          ${meta.thumbnail ? `<img src="${meta.thumbnail}" style="width:80px;height:46px;object-fit:cover;border-radius:6px">` : ''}
          <div style="flex:1;min-width:0"><div style="font-size:12px;font-weight:800;line-height:1.4">${meta.title || '(بلا عنوان)'}</div><div style="font-size:10px;opacity:.6;margin-top:3px">${meta.uploader || ''} ${meta.duration ? '• ' + Math.floor(meta.duration/60) + ':' + String(meta.duration%60).padStart(2,'0') : ''}</div></div>
        </div>`;
      $('#v-dl').disabled = false;
    } catch (e) { $('#v-prev-out').innerHTML = `<div class="status err show">${e.message}</div>`; }
  };
  $('#v-dl').onclick = async () => {
    const url = $('#v-url').value.trim(); if (!url) return;
    $('#v-dl-st').className = 'status wait show';
    $('#v-dl-st').textContent = '⏳ تنزيل + تحويل + تصنيف AI... (30-60 ث)';
    try {
      const fd = new FormData(); fd.append('url', url); fd.append('title', meta?.title || '');
      const r = await fetch(API + '/kids/videos/import', { method: 'POST', headers: headers(), body: fd });
      const d = await r.json();
      if (!d.ok) throw new Error(d.detail || 'فشل');
      $('#v-dl-st').className = 'status ok show';
      $('#v-dl-st').textContent = `✅ تم — تصنيف: ${d.category || 'غير محدد'}`;
      $('#v-url').value = ''; $('#v-prev-out').innerHTML = ''; $('#v-dl').disabled = true;
      setTimeout(loadList, 1200);
    } catch (e) { $('#v-dl-st').className = 'status err show'; $('#v-dl-st').textContent = '❌ ' + e.message; }
  };
  $('#v-recat').onclick = async () => {
    $('#v-recat-st').className = 'status wait show';
    $('#v-recat-st').textContent = '⏳ Claude Haiku يصنّف...';
    try {
      const r = await fetch(API + '/kids/auto-categorize/all', { method: 'POST', headers: headers() });
      const d = await r.json();
      $('#v-recat-st').className = 'status ok show';
      $('#v-recat-st').textContent = `✅ تم تصنيف ${d.count} فيديو`;
      loadList();
    } catch (e) { $('#v-recat-st').className = 'status err show'; $('#v-recat-st').textContent = '❌'; }
  };
  async function loadList() {
    try {
      const r = await fetch(API + '/kids/bot/approved', { headers: headers() });
      const d = await r.json();
      const cats = await (await fetch(API + '/kids/categories')).json();
      const catMap = Object.fromEntries((cats.items || []).map(c => [c.id, c]));
      $('#v-cnt').textContent = (d.items || []).length;
      $('#v-list').innerHTML = (d.items || []).map(v => {
        const ct = catMap[v.category] || { icon: '❓', title: '(غير مصنّف)' };
        return `<div class="list-item"><span class="ic">${ct.icon}</span><div class="tx"><div class="ttl">${(v.title || 'بلا').slice(0, 50)}</div><div class="meta">${ct.title}</div></div><button class="btn-sm btn-del" data-vid="${v.id}">🗑</button></div>`;
      }).join('');
      $$('#v-list .btn-del').forEach(b => b.onclick = async () => {
        if (!confirm('حذف؟')) return;
        await fetch(API + '/kids/bot/reject/' + b.dataset.vid, { method: 'DELETE', headers: headers() });
        loadList();
      });
    } catch (e) { $('#v-list').innerHTML = '❌' + e.message; }
  }
  loadList();
}
async function pdCats(c) {
  c.innerHTML = `
    <div class="card">
      <h3>🏷️ التصنيفات</h3>
      <div class="hint">أضف تصنيفات (أخبار، رياضة، كرتون...). الفيديوهات الجديدة تتصنف تلقائياً بالـ AI.</div>
      <div class="form-row"><input class="icon" id="c-ic" placeholder="🏷️" maxlength="4"><input id="c-t" placeholder="اسم التصنيف"><button class="btn-add" id="c-add">+</button></div>
      <div id="c-l"></div>
    </div>`;
  async function refresh() {
    const r = await fetch(API + '/kids/categories');
    const d = await r.json();
    $('#c-l').innerHTML = (d.items || []).map(x => `
      <div class="list-item"><span class="ic">${x.icon}</span><div class="tx"><div class="ttl">${x.title}</div><div class="meta">${x.system ? 'نظامي' : ''}</div></div>${x.system ? '' : `<button class="btn-sm btn-del" data-id="${x.id}">🗑</button>`}</div>
    `).join('');
    $$('#c-l .btn-del').forEach(b => b.onclick = async () => {
      if (!confirm('حذف؟')) return;
      await fetch(API + '/kids/categories/' + encodeURIComponent(b.dataset.id), { method: 'DELETE', headers: headers() });
      refresh(); loadCategories();
    });
  }
  $('#c-add').onclick = async () => {
    const t = $('#c-t').value.trim(); if (!t) return alert('اسم؟');
    const fd = new FormData(); fd.append('title', t); fd.append('icon', $('#c-ic').value.trim() || '🏷️');
    const r = await fetch(API + '/kids/categories', { method: 'POST', headers: headers(), body: fd });
    if ((await r.json()).ok) { $('#c-t').value = ''; $('#c-ic').value = ''; refresh(); loadCategories(); }
  };
  refresh();
}
async function pdTasks(c) {
  c.innerHTML = `
    <div class="card">
      <h3>🎯 المهام اليومية</h3>
      <div class="hint">أضف مهام تظهر للطفل. المهام مع كاميرا تجبر الطفل يصوّر إثبات.</div>
      <div class="form-row"><input class="icon" id="t-ic" placeholder="🪥" maxlength="4"><input id="t-t" placeholder="عنوان المهمة"></div>
      <div class="form-row"><input class="pts" id="t-p" type="number" min="1" max="500" value="5"><select id="t-cam"><option value="0">بدون كاميرا</option><option value="1">📹 كاميرا واحد</option><option value="2">📹📹 قبل + بعد</option></select><button class="btn-add" id="t-add">+</button></div>
      <div id="t-l"></div>
    </div>`;
  async function refresh() {
    const r = await fetch(API + '/kids/parent-tasks'); const d = await r.json();
    $('#t-l').innerHTML = (d.items || []).map(x => `
      <div class="list-item"><span class="ic">${x.icon}</span><div class="tx"><div class="ttl">${x.title}</div><div class="meta">+${x.points} ${x.needs_before_after ? '📹📹 قبل+بعد' : x.needs_camera ? '📹' : ''}</div></div><button class="btn-sm btn-del" data-id="${x.id}">🗑</button></div>
    `).join('');
    $$('#t-l .btn-del').forEach(b => b.onclick = async () => {
      if (!confirm('حذف؟')) return;
      await fetch(API + '/kids/parent-tasks/' + b.dataset.id, { method: 'DELETE', headers: headers() });
      refresh();
    });
  }
  $('#t-add').onclick = async () => {
    const t = $('#t-t').value.trim(); if (!t) return alert('عنوان؟');
    const camVal = $('#t-cam').value;
    const fd = new FormData();
    fd.append('title', t); fd.append('icon', $('#t-ic').value.trim() || '✅');
    fd.append('points', $('#t-p').value || '5');
    fd.append('needs_camera', (camVal === '1' || camVal === '2') ? 'true' : 'false');
    fd.append('needs_before_after', camVal === '2' ? 'true' : 'false');
    const r = await fetch(API + '/kids/parent-tasks', { method: 'POST', headers: headers(), body: fd });
    if ((await r.json()).ok) { $('#t-t').value = ''; refresh(); }
  };
  refresh();
}
async function pdDhikr(c) {
  c.innerHTML = `
    <div class="card">
      <h3>📿 الأذكار</h3>
      <div class="hint">أضف ذكر بالعنوان والهدف (التكرارات) والنقاط.</div>
      <div class="form-row"><input class="icon" id="d-ic" placeholder="📿" maxlength="4"><input id="d-t" placeholder="عنوان الذكر"></div>
      <div class="form-row"><input class="pts" id="d-tar" type="number" min="1" max="9999" value="33" placeholder="الهدف"><input class="pts" id="d-p" type="number" min="1" max="500" value="5" placeholder="نقاط"><button class="btn-add" id="d-add">+</button></div>
      <div id="d-l"></div>
    </div>`;
  async function refresh() {
    const r = await fetch(API + '/kids/dhikr'); const d = await r.json();
    $('#d-l').innerHTML = (d.items || []).map(x => `
      <div class="list-item"><span class="ic">${x.icon}</span><div class="tx"><div class="ttl">${x.title}</div><div class="meta">×${x.target} • +${x.points}</div></div><button class="btn-sm btn-del" data-id="${x.id}">🗑</button></div>
    `).join('');
    $$('#d-l .btn-del').forEach(b => b.onclick = async () => {
      if (!confirm('حذف؟')) return;
      await fetch(API + '/kids/dhikr/' + b.dataset.id, { method: 'DELETE', headers: headers() });
      refresh();
    });
  }
  $('#d-add').onclick = async () => {
    const t = $('#d-t').value.trim(); if (!t) return alert('عنوان؟');
    const fd = new FormData();
    fd.append('title', t); fd.append('icon', $('#d-ic').value.trim() || '📿');
    fd.append('target', $('#d-tar').value || '33'); fd.append('points', $('#d-p').value || '5');
    const r = await fetch(API + '/kids/dhikr', { method: 'POST', headers: headers(), body: fd });
    if ((await r.json()).ok) { $('#d-t').value = ''; refresh(); }
  };
  refresh();
}
async function pdKids(c) {
  c.innerHTML = `
    <div class="card">
      <h3>👶 حسابات الأطفال</h3>
      <div class="form-row"><input id="k-n" placeholder="اسم"><input id="k-p" placeholder="PIN (4-12)"><button class="btn-add" id="k-add">+</button></div>
      <div id="k-l"></div>
    </div>`;
  async function refresh() {
    const r = await fetch(API + '/kids/accounts', { headers: headers() }); const d = await r.json();
    $('#k-l').innerHTML = (d.items || []).map(x => `
      <div class="list-item"><span class="ic">👦</span><div class="tx"><div class="ttl">${x.name}</div><div class="meta">PIN: <b>${x.pin}</b></div></div><button class="btn-sm btn-del" data-email="${x.email}">🗑</button></div>
    `).join('');
    $$('#k-l .btn-del').forEach(b => b.onclick = async () => {
      if (!confirm('حذف؟')) return;
      await fetch(API + '/kids/accounts/' + encodeURIComponent(b.dataset.email), { method: 'DELETE', headers: headers() });
      refresh();
    });
  }
  $('#k-add').onclick = async () => {
    const n = $('#k-n').value.trim(), p = $('#k-p').value.trim();
    if (!n || !p) return alert('اسم + PIN');
    const fd = new FormData(); fd.append('name', n); fd.append('pin', p);
    const r = await fetch(API + '/kids/accounts', { method: 'POST', headers: headers(), body: fd });
    if ((await r.json()).ok) { $('#k-n').value = ''; $('#k-p').value = ''; refresh(); }
  };
  refresh();
}
async function pdStats(c) {
  c.innerHTML = '<div class="card">⏳</div>';
  try {
    const r = await fetch(API + '/kids/parent-summary'); const d = await r.json();
    if (!d.children?.length) { c.innerHTML = '<div class="card">لا أطفال</div>'; return; }
    c.innerHTML = `<div class="card"><h3>📊 الإجمالي</h3><div class="stat-grid"><div class="stat-cell"><div class="v">${d.totals.points}</div><div class="l">⭐ نقاط</div></div><div class="stat-cell"><div class="v">${(d.totals.points * 0.1).toFixed(1)}</div><div class="l">💰 ر.س / شهر</div></div></div></div>` +
      d.children.map(k => `
        <div class="card">
          <h3>👦 ${k.name}</h3>
          <div class="stat-grid">
            <div class="stat-cell"><div class="v">${k.total_points}</div><div class="l">نقاط</div></div>
            <div class="stat-cell"><div class="v">${k.monthly_sar.toFixed(1)}</div><div class="l">ر.س</div></div>
            <div class="stat-cell"><div class="v">${k.prayer_recordings}</div><div class="l">🕌 صلوات</div></div>
            <div class="stat-cell"><div class="v">${k.task_recordings}</div><div class="l">📹 مهام</div></div>
          </div>
          <div style="font-size:12px;opacity:.7;margin:8px 0 4px">آخر النقاط:</div>
          ${(k.recent_points || []).slice(0, 5).map(e => `<div class="list-item"><span class="ic">${e.kind === 'dhikr' ? '📿' : e.kind === 'task' ? '🎯' : '⭐'}</span><div class="tx"><div class="ttl">${e.kind} +${e.value}</div><div class="meta">${(e.created_at || '').slice(0, 16).replace('T', ' ')}</div></div></div>`).join('') || '<div style="opacity:.5;font-size:11px;padding:8px">لا نشاطات</div>'}
        </div>
      `).join('');
  } catch (e) { c.innerHTML = `<div class="card status err show">${e.message}</div>`; }
}

// ════════ STARTUP ════════
async function pdRecordings(c) {
  c.innerHTML = '<div class="card">⏳</div>';
  try {
    const r = await fetch(API + '/kids/parent-recordings?limit=100');
    const d = await r.json();
    if (!d.items?.length) { c.innerHTML = '<div class="card"><div style="opacity:.6;text-align:center;padding:20px">لا توجد تسجيلات بعد</div></div>'; return; }
    c.innerHTML = '<div class="card"><h3>📹 تسجيلات الأطفال (' + d.items.length + ')</h3><div class="hint">شاهد فيديوهات الأطفال للمهام والصلوات.</div><div id="recs-list"></div></div>';
    const host = $('#recs-list');
    d.items.forEach(rec => {
      const icon = rec.rec_type === 'prayer' ? '🕌' : rec.rec_type === 'task' ? '🎯' : '📹';
      const phase = rec.phase ? (rec.phase === 'before' ? ' (قبل)' : ' (بعد)') : '';
      const dur = rec.duration_sec ? Math.round(rec.duration_sec) + 'ث' : '';
      const it = document.createElement('div');
      it.className = 'list-item';
      it.innerHTML = `
        <span class="ic">${icon}</span>
        <div class="tx">
          <div class="ttl">${rec.child_name}${phase}</div>
          <div class="meta">${rec.task_title || rec.audio_track || rec.rec_type} • ${(rec.created_at || '').slice(0, 16).replace('T', ' ')} • ${dur}</div>
        </div>
        <button class="btn-sm btn-go" data-vid="${rec.id}">▶</button>
      `;
      host.appendChild(it);
    });
    host.querySelectorAll('button[data-vid]').forEach(b => b.onclick = () => {
      const url = `${API}/kids/recordings/${b.dataset.vid}/stream`;
      const vid = document.getElementById('play-video');
      vid.src = url;
      vid.load();
      document.getElementById('play-modal').style.display = 'flex';
      vid.play().catch(() => {});
    });
  } catch (e) { c.innerHTML = '<div class="card status err show">' + e.message + '</div>'; }
}

// ════════ QURAN ════════
async function pdQuranReview(c) {
  c.innerHTML = '<div class="card">⏳ جاري التحميل...</div>';
  try {
    const r = await fetch(API + '/kids/quran/submissions?status=pending_parent&limit=50');
    const d = await r.json();
    const pending = d.items || [];
    const rApp = await fetch(API + '/kids/quran/submissions?status=approved&limit=20');
    const approved = (await rApp.json()).items || [];
    const rRej = await fetch(API + '/kids/quran/submissions?status=rejected&limit=20');
    const rejected = (await rRej.json()).items || [];
    const surahsMap = {};
    if (!quranSurahs.length) {
      try { const r2 = await fetch(API + '/kids/quran/surahs'); quranSurahs = (await r2.json()).items || []; } catch(e){}
    }
    quranSurahs.forEach(s => surahsMap[s.number] = s.name);
    const surahName = (n) => surahsMap[n] || `سورة ${n}`;
    c.innerHTML = `
      <div class="card">
        <h3>📋 خطط الحفظ</h3>
        <div class="hint">حدد خطة لكل طفل (سور مخصصة أو عشوائي).</div>
        <div id="q-plans"></div>
      </div>
      <div class="card">
        <h3>📖 مراجعة تسجيلات القرآن</h3>
        <div class="hint">استمع لتسجيلات الأطفال وقرر إن كانت القراءة صحيحة لتمنحهم النقاط.</div>
        <div style="margin-bottom:14px">
          <h3 style="margin-top:14px;color:#fcd34d">⏳ في انتظار المراجعة (${pending.length})</h3>
          <div id="q-pending"></div>
        </div>
        <div>
          <h3 style="margin-top:14px;color:#86efac">✅ تمت الموافقة (${approved.length})</h3>
          <div id="q-approved" style="opacity:.7"></div>
        </div>
        ${rejected.length ? `<div><h3 style="margin-top:14px;color:#fca5a5">❌ مرفوض (${rejected.length})</h3><div id="q-rejected" style="opacity:.6"></div></div>` : ''}
      </div>`;
    // Plans UI
    try {
      const rk = await fetch(API + '/kids/accounts/public');
      const kids = (await rk.json()).items || [];
      const plansHtml = await Promise.all(kids.map(async kid => {
        const rp = await fetch(API + '/kids/quran/plan?child_email=' + encodeURIComponent(kid.email));
        const plan = (await rp.json()).plan || {};
        const surahs = (plan.surahs || []).join(',');
        return `<div class="list-item" style="flex-direction:column;align-items:stretch;gap:6px;padding:12px">
          <div style="display:flex;align-items:center;gap:8px"><span class="ic">👦</span><div class="tx"><div class="ttl">${kid.name}</div><div class="meta">${plan.surahs?.length || 0} سورة في الخطة • ${plan.type || 'لا توجد خطة'}</div></div></div>
          <input id="plan-${kid.email}" placeholder="أرقام السور مفصولة بفاصلة (مثل: 1,112,113,114)" value="${surahs}" style="background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.1);color:#fff;padding:8px;border-radius:6px;font-size:12px">
          <div style="display:flex;gap:6px">
            <button class="btn-sm btn-go" data-act="save" data-email="${kid.email}">💾 حفظ</button>
            <button class="btn-sm" style="background:rgba(168,85,247,.15);color:#c4b5fd;border:1px solid rgba(168,85,247,.3)" data-act="random" data-email="${kid.email}">🎲 عشوائي 10</button>
            <button class="btn-sm btn-del" data-act="clear" data-email="${kid.email}">🗑 مسح</button>
          </div>
        </div>`;
      }));
      $('#q-plans').innerHTML = plansHtml.join('');
      $$('#q-plans button[data-act]').forEach(b => b.onclick = async () => {
        const email = b.dataset.email; const act = b.dataset.act;
        const fd = new FormData(); fd.append('child_email', email);
        if (act === 'save') {
          const v = document.getElementById('plan-' + email).value.split(',').map(s => parseInt(s.trim())).filter(n => n >= 1 && n <= 114);
          fd.append('surahs', JSON.stringify(v)); fd.append('plan_type', 'custom');
        } else if (act === 'random') {
          fd.append('plan_type', 'random'); fd.append('note', '10');
        } else if (act === 'clear') {
          fd.append('surahs', '[]'); fd.append('plan_type', 'none');
        }
        await fetch(API + '/kids/quran/plan', { method: 'POST', headers: headers(), body: fd });
        pdQuranReview(c);
      });
    } catch(e){ $('#q-plans').innerHTML = '<div style="opacity:.5">' + e.message + '</div>'; }
    function renderSub(s, withActions) {
      const audioUrl = `${API}/kids/quran/submissions/${s.id}/audio`;
      const stClass = s.status === 'approved' ? 'approved' : s.status === 'rejected' ? 'rejected' : 'pending';
      const stTxt = s.status === 'approved' ? '✅ موافق' : s.status === 'rejected' ? '❌ مرفوض' : '⏳ معلق';
      return `
        <div class="q-sub-card" data-id="${s.id}">
          <div class="h">
            <span>👦</span>
            <span class="nm">${s.child_name || s.child_email}</span>
            <span class="st ${stClass}">${stTxt}</span>
          </div>
          <div style="font-size:12px;opacity:.8;margin-bottom:6px">${surahName(s.surah_num)} • ${s.proposed_points} نقطة محتملة</div>
          <audio src="${audioUrl}" controls preload="none"></audio>
          ${withActions ? `<div class="acts"><button class="ok" data-act="ok">✅ موافقة + ${s.proposed_points} نقطة</button><button class="no" data-act="no">❌ رفض</button></div>` : ''}
        </div>`;
    }
    $('#q-pending').innerHTML = pending.map(s => renderSub(s, true)).join('') || '<div style="opacity:.5;text-align:center;padding:14px;font-size:12px">لا تسجيلات معلقة</div>';
    if ($('#q-approved')) $('#q-approved').innerHTML = approved.map(s => renderSub(s, false)).join('') || '<div style="opacity:.5;text-align:center;padding:8px;font-size:11px">-</div>';
    if ($('#q-rejected')) $('#q-rejected').innerHTML = rejected.map(s => renderSub(s, false)).join('') || '';
    $$('#q-pending [data-act]').forEach(b => b.onclick = async () => {
      const card = b.closest('.q-sub-card');
      const id = card.dataset.id;
      const act = b.dataset.act;
      if (act === 'ok') {
        await fetch(API + `/kids/quran/submissions/${id}/approve`, { method: 'POST', headers: headers(), body: new FormData() });
        alert('✅ تمت الموافقة + إضافة النقاط');
      } else {
        if (!confirm('رفض التسجيل؟')) return;
        await fetch(API + `/kids/quran/submissions/${id}/reject`, { method: 'POST', headers: headers(), body: new FormData() });
      }
      pdQuranReview(c);
    });
  } catch (e) { c.innerHTML = `<div class="card status err show">${e.message}</div>`; }
}
// ════════ QURAN HOME (5th tab) ════════
async function renderQuranHome() {
  if (!quranSurahs.length) {
    try { const r = await fetch(API + '/kids/quran/surahs'); quranSurahs = (await r.json()).items || []; } catch(e){}
  }
  let subs = [];
  try {
    const r = await fetch(API + '/kids/quran/submissions?child_email=' + encodeURIComponent(STATE.email) + '&limit=200');
    subs = (await r.json()).items || [];
  } catch(e){}
  const statusBySurah = {};
  subs.forEach(s => {
    const cur = statusBySurah[s.surah_num];
    const rank = { approved: 3, pending_parent: 2, rejected: 1 };
    if (!cur || (rank[s.status] || 0) > (rank[cur] || 0)) statusBySurah[s.surah_num] = s.status;
  });
  // Load plan
  try {
    const rp = await fetch(API + '/kids/quran/plan?child_email=' + encodeURIComponent(STATE.email));
    const dp = await rp.json();
    if (dp.ok && dp.plan && dp.plan.surahs?.length) {
      const plan = dp.plan;
      const total = plan.surahs.length;
      const done = plan.surahs.filter(n => statusBySurah[n] === 'approved').length;
      $('#quran-plan-card').style.display = 'block';
      $('#quran-plan-desc').textContent = plan.note || `حفظ ${total} سورة. ${done}/${total} مكتملة.`;
      $('#quran-plan-progress').innerHTML = `<div style="background:rgba(0,0,0,.3);height:10px;border-radius:100px;overflow:hidden;margin:8px 0"><div style="height:100%;background:linear-gradient(90deg,#22c55e,#86efac);width:${(done/total*100).toFixed(0)}%"></div></div><div style="display:grid;grid-template-columns:repeat(6,1fr);gap:4px;margin-top:8px">${plan.surahs.map(n => { const st = statusBySurah[n]; const col = st === 'approved' ? '#22c55e' : st === 'pending_parent' ? '#fbbf24' : '#444'; return `<div data-snum="${n}" style="aspect-ratio:1;background:${col};color:#fff;border-radius:6px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:12px;cursor:pointer">${n}</div>`; }).join('')}</div>`;
    } else { $('#quran-plan-card').style.display = 'none'; }
  } catch(e) { $('#quran-plan-card').style.display = 'none'; }
  let okCount = 0, pendCount = 0, emptyCount = 0;
  $('#quran-map').innerHTML = quranSurahs.map(s => {
    const st = statusBySurah[s.number];
    let col = '#2a2a2a'; emptyCount++;
    if (st === 'approved') { col = '#22c55e'; okCount++; emptyCount--; }
    else if (st === 'pending_parent') { col = '#fbbf24'; pendCount++; emptyCount--; }
    else if (st === 'rejected') { col = '#7f1d1d'; }
    return `<div data-snum="${s.number}" title="${s.name}" style="aspect-ratio:1;background:${col};color:#fff;border-radius:6px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:11px;cursor:pointer">${s.number}</div>`;
  }).join('');
  $('#qm-ok').textContent = okCount;
  $('#qm-pend').textContent = pendCount;
  $('#qm-empty').textContent = emptyCount;
  $$('#quran-map [data-snum]').forEach(c => c.onclick = () => openSurah(+c.dataset.snum));
  $$('#quran-plan-progress [data-snum]').forEach(c => c.onclick = () => openSurah(+c.dataset.snum));
}
$('#open-quran-from-tab').onclick = () => openQuranList();

// ════════ QURAN ════════
let quranSurahs = [];
let currentSurah = null;
let quranRecorder = null, quranChunks = [], quranStream = null, quranRecStart = 0;
async function openQuranList() {
  $('#religion-screen').classList.remove('on');
  $('#quran-surah-screen').classList.remove('on');
  $('#quran-list-screen').classList.add('on');
  if (!quranSurahs.length) {
    $('#quran-surahs-list').innerHTML = '<div style="text-align:center;opacity:.5;padding:20px">⏳</div>';
    try { const r = await fetch(API + '/kids/quran/surahs'); quranSurahs = (await r.json()).items || []; }
    catch (e) { $('#quran-surahs-list').innerHTML = '<div style="color:#fca5a5;text-align:center;padding:20px">' + e.message + '</div>'; return; }
  }
  renderSurahList();
}
function renderSurahList(q = '') {
  const filtered = q ? quranSurahs.filter(s => s.name.includes(q) || (s.name_en||'').toLowerCase().includes(q.toLowerCase()) || String(s.number) === q) : quranSurahs;
  $('#quran-surahs-list').innerHTML = filtered.map(s => `<div class="q-surah-card" data-num="${s.number}"><div class="num">${s.number}</div><div class="info"><div class="name">${s.name}</div><div class="meta">${s.name_en} • ${s.ayahs} آية • ${s.revelation}</div></div><div style="opacity:.5">▸</div></div>`).join('');
  $$('#quran-surahs-list .q-surah-card').forEach(c => c.onclick = () => openSurah(+c.dataset.num));
}
async function openSurah(num) {
  $('#quran-list-screen').classList.remove('on');
  $('#quran-surah-screen').classList.add('on');
  $('#quran-ayahs').innerHTML = '<div style="text-align:center;opacity:.5;padding:20px">⏳</div>';
  $('#quran-surah-title').textContent = 'جاري التحميل...';
  try {
    const r = await fetch(API + '/kids/quran/surah/' + num);
    const d = await r.json();
    currentSurah = d;
    $('#quran-surah-title').textContent = d.name;
    $('#quran-ayahs').innerHTML = d.ayahs.map(a => `<div class="q-ayah"><div class="txt"><span class="num">${a.number_in_surah}</span>${a.text}</div><div class="ctrls"><button data-aud="${a.audio}">▶ استمع</button><button data-rep="${a.audio}">🔁 كرر ×3</button></div></div>`).join('');
    $$('#quran-ayahs button[data-aud]').forEach(b => b.onclick = () => playAyahAudio(b.dataset.aud, b, 1));
    $$('#quran-ayahs button[data-rep]').forEach(b => b.onclick = () => playAyahAudio(b.dataset.rep, b, 3));
  } catch (e) { $('#quran-ayahs').innerHTML = '<div style="color:#fca5a5;padding:20px;text-align:center">' + e.message + '</div>'; }
}
let currentAudio = null;
function playAyahAudio(url, btn, repeats) {
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  let count = 0;
  function playOnce() {
    currentAudio = new Audio(url);
    currentAudio.onended = () => { count++; if (count < repeats) playOnce(); else if (btn) btn.textContent = btn.dataset.rep ? '🔁 كرر ×3' : '▶ استمع'; };
    currentAudio.play();
    if (btn) btn.textContent = repeats > 1 ? `⏸ ${count + 1}/${repeats}` : '⏸';
  }
  playOnce();
}
$('#open-quran').onclick = openQuranList;
$('#quran-back').onclick = () => { $('#quran-surah-screen').classList.remove('on'); openQuranList(); };
$('#quran-search').oninput = (e) => renderSurahList(e.target.value.trim());
$('#quran-rec-btn').onclick = async () => {
  if (!currentSurah) return;
  if (quranRecorder && quranRecorder.state === 'recording') { quranRecorder.stop(); return; }
  try {
    quranStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    quranChunks = [];
    quranRecorder = new MediaRecorder(quranStream, MediaRecorder.isTypeSupported('audio/webm') ? { mimeType: 'audio/webm' } : {});
    quranRecorder.ondataavailable = e => { if (e.data.size) quranChunks.push(e.data); };
    quranRecorder.onstop = async () => {
      quranStream.getTracks().forEach(t => t.stop());
      const blob = new Blob(quranChunks, { type: 'audio/webm' });
      const fd = new FormData();
      fd.append('file', blob, `quran_${Date.now()}.webm`);
      fd.append('child_email', STATE.email);
      fd.append('surah_num', currentSurah.number);
      fd.append('ayah_from', 1);
      fd.append('ayah_to', currentSurah.ayahs.length);
      fd.append('duration_sec', String((Date.now() - quranRecStart) / 1000));
      $('#quran-rec-btn').textContent = '⏳ جاري الرفع...';
      $('#quran-rec-btn').disabled = true;
      try {
        const r = await fetch(API + '/kids/quran/submit', { method: 'POST', body: fd });
        const d = await r.json();
        if (d.ok) alert(`✅ أُرسل التسجيل لولي أمرك.\nستحصل على ${d.proposed_points} نقطة عند الموافقة!`);
        else alert('❌ ' + (d.detail || 'فشل'));
      } catch (e) { alert('❌ ' + e.message); }
      $('#quran-rec-btn').textContent = '🎤 سجّل قراءتك للتحفيظ';
      $('#quran-rec-btn').disabled = false;
      $('#quran-rec-btn').classList.remove('recording');
    };
    quranRecorder.start();
    quranRecStart = Date.now();
    $('#quran-rec-btn').textContent = '⏹ إيقاف وحفظ';
    $('#quran-rec-btn').classList.add('recording');
  } catch (e) { alert('فشل فتح المايك: ' + e.message); }
};

// ════════ STARTUP ════════
async function startup() {
  if (STATE.role && STATE.email) {
    enterApp();
  } else {
    loadKidsForLogin();
  }
}
startup();
