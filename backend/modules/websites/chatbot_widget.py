"""Floating AI chatbot widget — injected when chatbot_config.enabled = True.

Includes:
• Floating bubble + chat modal (RTL Arabic)
• Live multi-turn conversation with /api/websites/public/{slug}/chatbot
• Automatic [HANDOFF] detection — shows a "تواصل مع موظف" form that creates a ticket
• Suggested-question chips for first-time users
"""


def chatbot_widget(slug: str, project: dict) -> str:
    cfg = project.get("chatbot_config") or {}
    if not cfg.get("enabled"):
        return ""
    if not slug:
        return ""

    api = "/api/websites"
    welcome = (
        cfg.get("welcome_message")
        or f"مرحباً! أنا المساعد الذكي لـ {project.get('name','المتجر')}. كيف أساعدك؟"
    ).replace('"', '\\"').replace('\n', '\\n')

    return f"""<!-- ZX-AI-ASSISTANT -->
<button id="zxai-fab" data-hl="extra-aibot" title="مساعد ذكي">💬</button>
<div id="zxai-modal" style="display:none">
  <div id="zxai-box">
    <div id="zxai-head">
      <div><b>🤖 المساعد الذكي</b><div style="font-size:10px;opacity:.65">يجيب فوراً على استفساراتك</div></div>
      <button id="zxai-close" style="background:rgba(255,255,255,.1);border:0;color:#fff;width:30px;height:30px;border-radius:50%;cursor:pointer">×</button>
    </div>
    <div id="zxai-log"></div>
    <div id="zxai-handoff-bar" style="display:none">
      <div style="padding:10px 12px;background:rgba(234,179,8,.08);border-top:1px solid rgba(234,179,8,.25);font-size:12px">
        <div style="margin-bottom:6px">📞 <b>تواصل مع موظف</b> — اترك بياناتك ونرد عليك سريعاً</div>
        <input id="zxai-h-name" placeholder="اسمك" style="width:100%;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.15);color:#fff;padding:7px 10px;border-radius:8px;font-size:13px;font-family:inherit;margin-bottom:5px" />
        <input id="zxai-h-contact" placeholder="جوالك أو بريدك" style="width:100%;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.15);color:#fff;padding:7px 10px;border-radius:8px;font-size:13px;font-family:inherit;margin-bottom:5px" />
        <textarea id="zxai-h-note" placeholder="ملاحظتك (اختياري)" rows="2" style="width:100%;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.15);color:#fff;padding:7px 10px;border-radius:8px;font-size:13px;font-family:inherit;resize:vertical;margin-bottom:6px"></textarea>
        <div style="display:flex;gap:6px">
          <button id="zxai-h-cancel" style="flex:1;padding:7px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);color:#fff;border-radius:8px;font-size:12px;cursor:pointer">إلغاء</button>
          <button id="zxai-h-submit" style="flex:2;padding:7px;background:linear-gradient(135deg,#eab308,#f59e0b);border:0;color:#000;border-radius:8px;font-size:12px;font-weight:900;cursor:pointer">إرسال للموظف</button>
        </div>
      </div>
    </div>
    <div id="zxai-input-bar">
      <input id="zxai-input" type="text" placeholder="اكتب سؤالك..." />
      <button id="zxai-send">📤</button>
    </div>
    <div style="font-size:9px;text-align:center;opacity:.4;padding:4px">مدعوم بـ Zitex AI</div>
  </div>
</div>
<style>
#zxai-fab{{position:fixed;bottom:16px;left:16px;z-index:96;width:54px;height:54px;border-radius:50%;background:linear-gradient(135deg,#10b981,#06b6d4);color:#fff;border:0;cursor:pointer;font-size:24px;box-shadow:0 10px 28px rgba(16,185,129,.45);animation:zxai-pulse 2s infinite}}
@keyframes zxai-pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.07)}}}}
#zxai-modal{{position:fixed;inset:0;z-index:999;background:rgba(0,0,0,.55);backdrop-filter:blur(6px);display:flex;align-items:flex-end;justify-content:center;padding:16px}}
@media(min-width:768px){{#zxai-modal{{align-items:center}}}}
#zxai-box{{background:#0e1128;color:#fff;border-radius:20px;width:min(440px,100%);max-height:85vh;display:flex;flex-direction:column;overflow:hidden;border:1px solid rgba(16,185,129,.3);font-family:Tajawal,Cairo,sans-serif;direction:rtl}}
#zxai-head{{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;background:linear-gradient(90deg,rgba(16,185,129,.18),rgba(6,182,212,.1));border-bottom:1px solid rgba(255,255,255,.06)}}
#zxai-log{{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;min-height:280px;max-height:55vh;scroll-behavior:smooth}}
.zxai-msg{{padding:9px 13px;border-radius:14px;font-size:13.5px;line-height:1.55;max-width:85%;white-space:pre-wrap;word-wrap:break-word;animation:zxai-in .25s ease-out}}
@keyframes zxai-in{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
.zxai-u{{align-self:flex-start;background:rgba(234,179,8,.15);border:1px solid rgba(234,179,8,.3);border-bottom-right-radius:4px}}
.zxai-a{{align-self:flex-end;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.25);border-bottom-left-radius:4px}}
.zxai-sys{{align-self:center;background:rgba(245,158,11,.1);border:1px dashed rgba(245,158,11,.4);font-size:11px;color:#fbbf24;border-radius:10px;padding:6px 12px;max-width:95%;text-align:center}}
.zxai-typing{{align-self:flex-end;display:flex;gap:4px;padding:10px 14px;background:rgba(16,185,129,.1);border-radius:14px}}
.zxai-typing span{{width:6px;height:6px;background:#10b981;border-radius:50%;animation:zxai-bounce 1.4s infinite}}
.zxai-typing span:nth-child(2){{animation-delay:.2s}}
.zxai-typing span:nth-child(3){{animation-delay:.4s}}
@keyframes zxai-bounce{{0%,80%,100%{{transform:translateY(0);opacity:.5}}40%{{transform:translateY(-4px);opacity:1}}}}
#zxai-input-bar{{display:flex;gap:6px;padding:10px;border-top:1px solid rgba(255,255,255,.08)}}
#zxai-input{{flex:1;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.15);color:#fff;padding:10px 12px;border-radius:12px;font-size:14px;font-family:inherit}}
#zxai-input:focus{{outline:none;border-color:rgba(16,185,129,.5)}}
#zxai-send{{padding:10px 14px;background:linear-gradient(135deg,#10b981,#06b6d4);color:#fff;border:0;border-radius:12px;font-weight:900;cursor:pointer;font-size:16px}}
#zxai-send:disabled{{opacity:.5;cursor:not-allowed}}
.zxai-suggest{{display:flex;flex-wrap:wrap;gap:6px;padding:0 14px 8px}}
.zxai-suggest button{{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);color:#fff;padding:6px 10px;border-radius:99px;font-size:11px;cursor:pointer;font-family:inherit}}
.zxai-suggest button:hover{{background:rgba(16,185,129,.15);border-color:rgba(16,185,129,.3)}}
.zxai-handoff-btn{{margin-top:6px;background:linear-gradient(135deg,#eab308,#f59e0b);color:#000;border:0;padding:7px 12px;border-radius:8px;font-weight:900;font-size:12px;cursor:pointer;display:inline-flex;align-items:center;gap:5px;font-family:inherit}}
.zxai-handoff-btn:hover{{filter:brightness(1.1)}}
</style>
<script>
(function(){{
  var SLUG="{slug}",API="{api}";
  var fab=document.getElementById("zxai-fab"),mod=document.getElementById("zxai-modal"),
      cls=document.getElementById("zxai-close"),log=document.getElementById("zxai-log"),
      inp=document.getElementById("zxai-input"),snd=document.getElementById("zxai-send"),
      hbar=document.getElementById("zxai-handoff-bar"),
      hN=document.getElementById("zxai-h-name"),hC=document.getElementById("zxai-h-contact"),
      hM=document.getElementById("zxai-h-note"),
      hCancel=document.getElementById("zxai-h-cancel"),hSubmit=document.getElementById("zxai-h-submit");
  var sid="zxai_"+Math.random().toString(36).slice(2,10);
  var greeted=false;
  var transcript=[]; // [{{role, text}}]
  var suggestions=["⏰ ساعات العمل","📦 ما هي المنتجات؟","🚚 طرق الشحن","💰 أسعاركم","📞 تواصل مع موظف"];

  function bubble(role,text){{
    var d=document.createElement("div");
    d.className="zxai-msg zxai-"+(role==="user"?"u":role==="system"?"sys":"a");
    d.textContent=text;log.appendChild(d);log.scrollTop=log.scrollHeight;
    if(role!=="system") transcript.push({{role:role==="user"?"user":"assistant",text:text}});
  }}
  function typing(on){{
    var ex=document.getElementById("zxai-typing");
    if(on&&!ex){{var t=document.createElement("div");t.id="zxai-typing";t.className="zxai-typing";t.innerHTML="<span></span><span></span><span></span>";log.appendChild(t);log.scrollTop=log.scrollHeight;}}
    if(!on&&ex)ex.remove();
  }}
  function showSuggest(){{
    var s=document.createElement("div");s.className="zxai-suggest";s.id="zxai-sug";
    suggestions.forEach(function(q){{
      var b=document.createElement("button");b.textContent=q;
      b.onclick=function(){{
        s.remove();
        if(q.indexOf("تواصل مع موظف")>=0){{ openHandoff(); }}
        else {{ ask(q.replace(/^[^ ]+\s/,"")); }}
      }};
      s.appendChild(b);
    }});
    log.appendChild(s);
  }}
  function openHandoff(){{
    hbar.style.display="block";
    bubble("system","💼 جارٍ تحويلك لموظف بشري — يرجى تعبئة بياناتك أدناه");
    setTimeout(function(){{ hN.focus(); }},80);
  }}
  function offerHandoffBtn(){{
    var wrap=document.createElement("div");
    wrap.style.alignSelf="flex-end";
    wrap.style.maxWidth="85%";
    var b=document.createElement("button");
    b.className="zxai-handoff-btn";
    b.textContent="📞 تواصل مع موظف بشري";
    b.onclick=openHandoff;
    wrap.appendChild(b);
    log.appendChild(wrap);
    log.scrollTop=log.scrollHeight;
  }}
  async function ask(text){{
    bubble("user",text);typing(true);snd.disabled=true;inp.disabled=true;
    try{{
      var r=await fetch(API+"/public/"+SLUG+"/chatbot",{{
        method:"POST",headers:{{"Content-Type":"application/json"}},
        body:JSON.stringify({{message:text,session_id:sid}})
      }});
      var d=await r.json();typing(false);
      if(!r.ok)throw new Error(d.detail||"تعذّر الرد");
      bubble("assistant",d.reply||"عذراً، لم أفهم.");
      if(d.handoff){{ offerHandoffBtn(); }}
    }}catch(e){{
      typing(false);
      bubble("assistant","⚠️ "+(e.message||"خطأ في الاتصال"));
      offerHandoffBtn();
    }}
    snd.disabled=false;inp.disabled=false;inp.focus();
  }}
  hCancel.onclick=function(){{
    hbar.style.display="none";hN.value="";hC.value="";hM.value="";
  }};
  hSubmit.onclick=async function(){{
    var name=(hN.value||"").trim(), contact=(hC.value||"").trim(), note=(hM.value||"").trim();
    if(!name && !contact){{ alert("الرجاء كتابة الاسم أو وسيلة التواصل"); return; }}
    hSubmit.disabled=true; hSubmit.textContent="...";
    try{{
      var r=await fetch(API+"/public/"+SLUG+"/chatbot/handoff",{{
        method:"POST",headers:{{"Content-Type":"application/json"}},
        body:JSON.stringify({{session_id:sid,name:name,contact:contact,message:note,transcript:transcript.slice(-30)}})
      }});
      var d=await r.json();
      if(!r.ok)throw new Error(d.detail||"فشل");
      hbar.style.display="none";hN.value="";hC.value="";hM.value="";
      bubble("system","✅ تم إرسال طلبك للموظف. سنتواصل معك قريباً (تذكرة #"+(d.ticket_id||"").slice(0,8)+")");
    }}catch(e){{
      alert("⚠️ "+(e.message||"تعذّر الإرسال"));
    }}
    hSubmit.disabled=false; hSubmit.textContent="إرسال للموظف";
  }};

  fab.onclick=function(){{
    mod.style.display="flex";
    if(!greeted){{greeted=true;bubble("assistant","{welcome}");showSuggest();}}
    setTimeout(function(){{inp.focus();}},100);
  }};
  cls.onclick=function(){{mod.style.display="none";}};
  mod.onclick=function(e){{if(e.target===mod)mod.style.display="none";}};
  snd.onclick=function(){{var t=inp.value.trim();if(!t)return;inp.value="";ask(t);}};
  inp.onkeydown=function(e){{if(e.key==="Enter"){{e.preventDefault();snd.click();}}}};
}})();
</script>"""
