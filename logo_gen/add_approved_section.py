"""Add 'Approved Videos' section to Parent Dashboard so user can see all 26 videos."""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

SLUG = "zenrex-kids-pro"

# Marker — the closing of the existing pending block
PENDING_BLOCK_OLD = '''      <div class="bc-pending">
        <div class="bc-pending-title">⏳ بانتظار مراجعتك</div>
        <div class="bc-pgrid" id="bc-pending-grid">
          <div class="bc-list-empty" style="grid-column: span 2">لا توجد فيديوهات بانتظار المراجعة</div>
        </div>
      </div>'''

# Replacement — original + new approved section right after
PENDING_BLOCK_NEW = '''      <div class="bc-pending">
        <div class="bc-pending-title">⏳ بانتظار مراجعتك</div>
        <div class="bc-pgrid" id="bc-pending-grid">
          <div class="bc-list-empty" style="grid-column: span 2">لا توجد فيديوهات بانتظار المراجعة</div>
        </div>
      </div>

      <!-- NEW: Approved Videos Library -->
      <div class="bc-pending" style="margin-top: 20px;" data-approved-section="1">
        <div class="bc-pending-title">
          ✅ مكتبة الفيديوهات المعتمدة
          <span id="bc-approved-count" style="font-size: 12px; opacity: 0.7; font-weight: 500; margin-inline-start: 8px;"></span>
        </div>
        <div class="bc-pgrid" id="bc-approved-grid">
          <div class="bc-list-empty" style="grid-column: span 2">جاري التحميل...</div>
        </div>
      </div>'''

# Marker — the existing buildWidget call section that does loadPending + setInterval
LOAD_PENDING_OLD = '''    wireEvents();
    loadConfig();
    loadPending();
    setInterval(loadPending, 5000);
  }'''

LOAD_PENDING_NEW = '''    wireEvents();
    loadConfig();
    loadPending();
    loadApproved();
    setInterval(loadPending, 5000);
    setInterval(loadApproved, 10000);
  }

  // NEW: Load and display approved videos in parent dashboard
  async function loadApproved(){
    if (localStorage.getItem('zk_role') !== 'parent') return;
    const grid = document.getElementById('bc-approved-grid');
    const cnt = document.getElementById('bc-approved-count');
    if (!grid) return;
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/kids/bot/approved`, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const d = await r.json();
      const items = d.items || [];
      if (cnt) cnt.textContent = `(${items.length})`;
      if (items.length === 0) {
        grid.innerHTML = '<div class="bc-list-empty" style="grid-column: span 2">لم تعتمد أي فيديو بعد</div>';
        return;
      }
      grid.innerHTML = '';
      items.forEach(it => {
        const c = document.createElement('div');
        c.className = 'bc-pcard2';
        const videoUrl = it.url || it.file_url || '';
        const fullUrl = videoUrl.startsWith('http') ? videoUrl : (window.location.origin + videoUrl);
        const title = (it.title || it.prompt || 'فيديو معتمد').slice(0, 60);
        const date = it.created_at ? new Date(it.created_at).toLocaleDateString('ar-SA') : '';
        c.innerHTML = `
          <video src="${fullUrl}" preload="metadata" muted playsinline style="width:100%;border-radius:8px;background:#000;aspect-ratio:9/16;object-fit:cover;cursor:pointer" onclick="this.paused?this.play():this.pause()"></video>
          <div class="pt">${title}</div>
          <div style="font-size:10px;opacity:0.6;margin:4px 0;">${date}</div>
          <div class="pb">
            <button class="ok" style="background:rgba(56,189,248,0.15);color:#38bdf8" onclick="window.open('${fullUrl}','_blank')">👁 معاينة</button>
            <button class="no">🗑 حذف</button>
          </div>
        `;
        c.querySelector('.no').onclick = async () => {
          if (!confirm('حذف هذا الفيديو نهائياً من المكتبة؟')) return;
          await fetch(`${API}/kids/bot/reject/${it.id}`, { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token }});
          loadApproved();
        };
        grid.appendChild(c);
      });
    } catch(e) { console.warn('approved load:', e); }
  }
'''


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = c[os.environ["DB_NAME"]]
    doc = await d.freebuild_published_sites.find_one({"slug": SLUG})
    html = doc["current_html"]
    original_len = len(html)

    if 'data-approved-section="1"' in html:
        print("Already patched — skipping HTML block insertion")
    elif PENDING_BLOCK_OLD in html:
        html = html.replace(PENDING_BLOCK_OLD, PENDING_BLOCK_NEW, 1)
        print("✅ Inserted approved section HTML block")
    else:
        print("❌ Could not find pending block marker — abort")
        return

    if 'async function loadApproved(' in html:
        print("loadApproved() already present — skipping JS insertion")
    elif LOAD_PENDING_OLD in html:
        html = html.replace(LOAD_PENDING_OLD, LOAD_PENDING_NEW, 1)
        print("✅ Inserted loadApproved() JS")
    else:
        print("❌ Could not find loadPending init marker — abort")
        return

    await d.freebuild_published_sites.update_one(
        {"slug": SLUG}, {"$set": {"current_html": html}}
    )
    print(f"Saved. {original_len} -> {len(html)} bytes (delta {len(html)-original_len:+d})")
    c.close()


if __name__ == "__main__":
    asyncio.run(main())
