"""Stories Bar + Animated Banner widget — injected into every storefront homepage.

Renders:
  • Top hero banner (image/video bg, Ken-Burns / parallax / fade animation, overlay + CTA)
  • Stories ribbon below the banner (Instagram-style circular thumbnails)
  • Fullscreen story viewer with auto-progress + tap nav

The data is read on storefront load via `/api/websites/public/{slug}/stories`.
"""


def stories_widget(slug: str) -> str:
    """Returns the HTML/CSS/JS block injected near the top of <body>."""
    if not slug:
        return ""
    api = "/api/websites"
    return f"""<!-- ZX-STORIES-BANNER -->
<div id="zxsb-host" data-hl="extra-stories"></div>
<style>
#zxsb-host{{position:relative;z-index:5}}
.zxsb-banner{{position:relative;width:100%;height:clamp(220px,38vw,520px);overflow:hidden;background:#000;direction:rtl;border-bottom:1px solid rgba(255,255,255,.08)}}
.zxsb-banner-media{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.zxsb-banner-media.kenburns{{animation:zxsb-kenburns 18s ease-in-out infinite alternate}}
@keyframes zxsb-kenburns{{from{{transform:scale(1) translate(0,0)}}to{{transform:scale(1.12) translate(-3%,2%)}}}}
.zxsb-banner-media.parallax{{transition:transform 50ms linear;will-change:transform}}
.zxsb-banner-media.fade{{animation:zxsb-fadein 1.4s ease-out}}
@keyframes zxsb-fadein{{from{{opacity:.0}}to{{opacity:1}}}}
.zxsb-banner-overlay{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.0) 0%,rgba(0,0,0,.65) 100%);pointer-events:none}}
.zxsb-banner-content{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:flex-end;align-items:flex-start;padding:clamp(16px,3vw,42px);gap:8px;color:#fff}}
.zxsb-banner-title{{font-size:clamp(22px,3.6vw,46px);font-weight:900;line-height:1.15;text-shadow:0 6px 28px rgba(0,0,0,.6);max-width:80%;animation:zxsb-rise .9s cubic-bezier(.2,.8,.2,1) both}}
.zxsb-banner-subtitle{{font-size:clamp(13px,1.4vw,18px);opacity:.9;text-shadow:0 4px 18px rgba(0,0,0,.5);max-width:70%;animation:zxsb-rise .9s .12s cubic-bezier(.2,.8,.2,1) both}}
@keyframes zxsb-rise{{from{{opacity:0;transform:translateY(18px)}}to{{opacity:1;transform:none}}}}
.zxsb-banner-cta{{margin-top:8px;display:inline-flex;align-items:center;gap:7px;padding:10px 22px;background:linear-gradient(135deg,#FFD700,#FF6B35);color:#0b0f1f;border-radius:99px;font-weight:900;font-size:14px;text-decoration:none;box-shadow:0 12px 32px rgba(255,107,53,.4);transition:transform .2s ease;animation:zxsb-rise .9s .24s cubic-bezier(.2,.8,.2,1) both}}
.zxsb-banner-cta:hover{{transform:translateY(-2px) scale(1.03)}}

.zxsb-stories{{display:flex;gap:12px;padding:14px clamp(12px,3vw,24px);overflow-x:auto;scrollbar-width:none;background:linear-gradient(180deg,rgba(0,0,0,.4),rgba(0,0,0,.0));direction:rtl;scroll-snap-type:x proximity}}
.zxsb-stories::-webkit-scrollbar{{display:none}}
.zxsb-story{{flex-shrink:0;width:74px;text-align:center;cursor:pointer;scroll-snap-align:start;font-family:inherit}}
.zxsb-story-ring{{width:74px;height:74px;border-radius:50%;padding:3px;background:conic-gradient(from 180deg,#FFD700,#FF6B35,#10b981,#06b6d4,#FFD700);position:relative;transition:transform .25s ease}}
.zxsb-story:hover .zxsb-story-ring{{transform:scale(1.06)}}
.zxsb-story-ring.seen{{background:rgba(255,255,255,.2)}}
.zxsb-story-img{{width:100%;height:100%;border-radius:50%;object-fit:cover;background:#000;border:2px solid #0e1128}}
.zxsb-story-vbadge{{position:absolute;bottom:2px;left:2px;background:#FF6B35;color:#fff;font-size:11px;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center}}
.zxsb-story-cap{{font-size:11px;margin-top:5px;color:rgba(255,255,255,.85);text-overflow:ellipsis;overflow:hidden;white-space:nowrap;direction:rtl}}

.zxsb-viewer{{position:fixed;inset:0;z-index:998;background:rgba(0,0,0,.96);display:none;align-items:center;justify-content:center;animation:zxsb-fadein .25s ease-out}}
.zxsb-viewer.open{{display:flex}}
.zxsb-viewer-shell{{position:relative;width:min(420px,100%);height:min(80vh,720px);max-height:96vh;background:#000;border-radius:14px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.7)}}
.zxsb-viewer-media{{width:100%;height:100%;object-fit:cover;background:#000}}
.zxsb-viewer-progress{{position:absolute;top:8px;left:8px;right:8px;display:flex;gap:4px;z-index:3}}
.zxsb-viewer-pbar{{flex:1;height:2.5px;background:rgba(255,255,255,.25);border-radius:99px;overflow:hidden}}
.zxsb-viewer-pfill{{height:100%;background:#fff;width:0%;transition:width 80ms linear}}
.zxsb-viewer-pfill.full{{width:100%}}
.zxsb-viewer-cap{{position:absolute;left:0;right:0;bottom:0;padding:12px 18px;color:#fff;font-size:14px;background:linear-gradient(0deg,rgba(0,0,0,.85),transparent);direction:rtl;font-family:inherit}}
.zxsb-viewer-cap a{{display:inline-block;margin-top:8px;padding:8px 18px;background:linear-gradient(135deg,#FFD700,#FF6B35);color:#0b0f1f;border-radius:99px;font-weight:900;font-size:13px;text-decoration:none}}
.zxsb-viewer-close{{position:absolute;top:14px;right:14px;width:34px;height:34px;border-radius:50%;background:rgba(0,0,0,.6);color:#fff;border:0;font-size:20px;cursor:pointer;z-index:4}}
.zxsb-tap{{position:absolute;top:0;bottom:0;width:50%;cursor:pointer;z-index:2}}
.zxsb-tap.left{{left:0}}.zxsb-tap.right{{right:0}}
</style>
<script>
(function(){{
  var SLUG="{slug}",API="{api}";
  var host=document.getElementById("zxsb-host");
  var viewer=null,viewerIdx=0,viewerStories=[],viewerTimer=null;
  var SEEN_KEY="zxsb_seen_"+SLUG;
  var seen=(function(){{try{{return JSON.parse(localStorage.getItem(SEEN_KEY)||"[]");}}catch(_){{return[];}}}})();
  function markSeen(id){{if(seen.indexOf(id)<0){{seen.push(id);try{{localStorage.setItem(SEEN_KEY,JSON.stringify(seen.slice(-100)));}}catch(_){{}}}}}}

  function el(tag,attrs,children){{
    var n=document.createElement(tag);
    if(attrs)Object.keys(attrs).forEach(function(k){{
      if(k==="style"&&typeof attrs[k]==="object")Object.assign(n.style,attrs[k]);
      else if(k==="text")n.textContent=attrs[k];
      else if(k==="html")n.innerHTML=attrs[k];
      else n.setAttribute(k,attrs[k]);
    }});
    (children||[]).forEach(function(c){{if(c)n.appendChild(c);}});
    return n;
  }}

  function renderBanner(b){{
    if(!b||!b.enabled||!b.media_url)return null;
    var media,anim=b.animation||"kenburns";
    if(b.type==="video"){{
      media=el("video",{{class:"zxsb-banner-media "+anim,src:b.media_url,autoplay:"",muted:"",loop:"",playsinline:""}});
    }}else{{
      media=el("img",{{class:"zxsb-banner-media "+anim,src:b.media_url,alt:""}});
    }}
    var box=el("section",{{class:"zxsb-banner"}},[media,el("div",{{class:"zxsb-banner-overlay"}})]);
    var content=el("div",{{class:"zxsb-banner-content"}});
    if(b.title)content.appendChild(el("div",{{class:"zxsb-banner-title",text:b.title}}));
    if(b.subtitle)content.appendChild(el("div",{{class:"zxsb-banner-subtitle",text:b.subtitle}}));
    if(b.cta_text){{var a=el("a",{{class:"zxsb-banner-cta",href:b.cta_link||"#",text:b.cta_text+" ←"}});content.appendChild(a);}}
    box.appendChild(content);
    if(anim==="parallax"){{
      window.addEventListener("scroll",function(){{
        var y=Math.max(0,Math.min(120,window.scrollY*.25));
        media.style.transform="translateY("+y+"px) scale(1.08)";
      }},{{passive:true}});
    }}
    return box;
  }}

  function renderStoriesRibbon(stories){{
    if(!stories||!stories.length)return null;
    var wrap=el("div",{{class:"zxsb-stories"}});
    stories.forEach(function(s,i){{
      var ring=el("div",{{class:"zxsb-story-ring"+(seen.indexOf(s.id)>=0?" seen":"")}});
      var img=el("img",{{class:"zxsb-story-img",src:(s.poster_url||(s.type==="video"?"":s.media_url))||"data:image/svg+xml;utf8,<svg xmlns=\\"http://www.w3.org/2000/svg\\" width=\\"60\\" height=\\"60\\"><rect width=\\"60\\" height=\\"60\\" fill=\\"%23222\\"/></svg>",alt:s.caption||""}});
      ring.appendChild(img);
      if(s.type==="video")ring.appendChild(el("div",{{class:"zxsb-story-vbadge",text:"▶"}}));
      var node=el("div",{{class:"zxsb-story"}},[ring]);
      if(s.caption)node.appendChild(el("div",{{class:"zxsb-story-cap",text:s.caption}}));
      node.onclick=function(){{ openViewer(stories,i); }};
      wrap.appendChild(node);
    }});
    return wrap;
  }}

  function openViewer(stories,startIdx){{
    viewerStories=stories;viewerIdx=startIdx;
    if(!viewer){{
      viewer=el("div",{{class:"zxsb-viewer"}});
      var shell=el("div",{{class:"zxsb-viewer-shell",id:"zxsb-vshell"}});
      shell.appendChild(el("div",{{class:"zxsb-viewer-progress",id:"zxsb-vprog"}}));
      shell.appendChild(el("button",{{class:"zxsb-viewer-close",text:"×",id:"zxsb-vclose"}}));
      var media=el("div",{{id:"zxsb-vmedia",style:{{width:"100%",height:"100%"}}}});
      shell.appendChild(media);
      shell.appendChild(el("div",{{class:"zxsb-viewer-cap",id:"zxsb-vcap"}}));
      shell.appendChild(el("div",{{class:"zxsb-tap left",id:"zxsb-tleft"}}));
      shell.appendChild(el("div",{{class:"zxsb-tap right",id:"zxsb-tright"}}));
      viewer.appendChild(shell);
      document.body.appendChild(viewer);
      viewer.addEventListener("click",function(e){{ if(e.target===viewer)closeViewer(); }});
      document.getElementById("zxsb-vclose").onclick=closeViewer;
      document.getElementById("zxsb-tleft").onclick=function(){{ stepRTL(+1); }};
      document.getElementById("zxsb-tright").onclick=function(){{ stepRTL(-1); }};
      document.addEventListener("keydown",function(e){{
        if(!viewer.classList.contains("open"))return;
        if(e.key==="Escape")closeViewer();
        if(e.key==="ArrowLeft")stepRTL(+1);
        if(e.key==="ArrowRight")stepRTL(-1);
      }});
    }}
    viewer.classList.add("open");
    showStory();
  }}
  function closeViewer(){{
    if(!viewer)return;
    viewer.classList.remove("open");
    if(viewerTimer){{clearInterval(viewerTimer);viewerTimer=null;}}
    var v=document.querySelector("#zxsb-vmedia video");if(v)try{{v.pause();}}catch(_){{}}
  }}
  function stepRTL(delta){{ // RTL: tap-left = NEXT, tap-right = PREV
    var nidx=viewerIdx+delta;
    if(nidx<0||nidx>=viewerStories.length){{closeViewer();return;}}
    viewerIdx=nidx;showStory();
  }}
  function showStory(){{
    var s=viewerStories[viewerIdx];if(!s)return;
    markSeen(s.id);
    var media=document.getElementById("zxsb-vmedia");media.innerHTML="";
    var prog=document.getElementById("zxsb-vprog");prog.innerHTML="";
    viewerStories.forEach(function(_,i){{
      var bar=el("div",{{class:"zxsb-viewer-pbar"}});
      var fill=el("div",{{class:"zxsb-viewer-pfill"+(i<viewerIdx?" full":"")}});
      bar.appendChild(fill);prog.appendChild(bar);
    }});
    var cap=document.getElementById("zxsb-vcap");cap.innerHTML="";
    if(s.caption){{cap.appendChild(el("div",{{text:s.caption}}));}}
    if(s.link){{cap.appendChild(el("a",{{href:s.link,target:"_blank",rel:"noopener",text:"اعرف أكثر ←"}}));}}
    var dur=Math.max(2,Math.min(20,s.duration_sec||6))*1000;
    if(s.type==="video"){{
      var v=el("video",{{class:"zxsb-viewer-media",src:s.media_url,autoplay:"",playsinline:"",controls:""}});
      media.appendChild(v);
      v.addEventListener("loadedmetadata",function(){{ if(v.duration&&v.duration>0)dur=Math.min(20,v.duration)*1000; startProgress(dur); }});
      v.addEventListener("ended",function(){{ stepRTL(+1); }});
    }}else{{
      var img=el("img",{{class:"zxsb-viewer-media",src:s.media_url,alt:""}});
      media.appendChild(img);
      startProgress(dur);
    }}
  }}
  function startProgress(durMs){{
    if(viewerTimer){{clearInterval(viewerTimer);}}
    var start=Date.now();
    var prog=document.getElementById("zxsb-vprog");
    var fill=prog && prog.children[viewerIdx] && prog.children[viewerIdx].firstChild;
    viewerTimer=setInterval(function(){{
      var pct=Math.min(100,((Date.now()-start)/durMs)*100);
      if(fill)fill.style.width=pct+"%";
      if(pct>=100){{clearInterval(viewerTimer);viewerTimer=null;stepRTL(+1);}}
    }},80);
  }}

  fetch(API+"/public/"+SLUG+"/stories").then(function(r){{return r.json();}}).then(function(d){{
    var stories=(d.stories||[]).filter(function(s){{return s.media_url;}});
    var b=renderBanner(d.banner);
    if(b)host.appendChild(b);
    var ribbon=renderStoriesRibbon(stories);
    if(ribbon)host.appendChild(ribbon);
  }}).catch(function(){{}});
}})();
</script>"""
