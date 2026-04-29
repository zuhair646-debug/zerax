import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

const API = process.env.REACT_APP_BACKEND_URL;

export default function PublicSite() {
  const { slug } = useParams();
  const [html, setHtml] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!slug) return;
    document.title = `${slug} | Zitex`;
    fetch(`${API}/api/websites/public/${slug}`)
      .then(async (r) => {
        if (!r.ok) throw new Error('not_found');
        const text = await r.text();
        setHtml(text);
      })
      .catch(() => setErr('الموقع غير موجود أو لم يُعتمد بعد'));
  }, [slug]);

  if (err) {
    return (
      <div style={{minHeight:'100vh',display:'flex',alignItems:'center',justifyContent:'center',background:'#0b0f1f',color:'#fff',fontFamily:'Tajawal,sans-serif'}} dir="rtl">
        <div style={{textAlign:'center',padding:40}}>
          <div style={{fontSize:64}}>🔍</div>
          <h1 style={{color:'#FFD700'}}>{err}</h1>
          <a href="/" style={{color:'#FFD700',textDecoration:'underline'}}>العودة لـ Zitex</a>
        </div>
      </div>
    );
  }

  if (!html) {
    return (
      <div style={{minHeight:'100vh',display:'flex',alignItems:'center',justifyContent:'center',background:'#0b0f1f',color:'#fff'}}>
        <div>⏳ جاري التحميل...</div>
      </div>
    );
  }

  // Use an iframe with srcDoc so the site's CSS can't affect Zitex header routes
  return (
    <iframe
      srcDoc={html}
      sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
      title={slug}
      style={{width:'100vw',height:'100vh',border:0,display:'block'}}
    />
  );
}
