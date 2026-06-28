"""Generates animated HTML "tutorial videos" for every continuation provider.

Each generated file is a self-contained HTML page that plays a 3-step
CSS-keyframe animation:
  1) Login to the official provider site
  2) Navigate to the token / app-password / SSH-keys page
  3) Select the required permissions / scopes

Bilingual labels (AR top, EN below). A non-obstructive Zenrex watermark
sits in the top-right corner. The page auto-loops indefinitely and is
embedded into the onboarding wizard via an <iframe>.

Run:
    python /app/backend/static/tutorials/_build_tutorials.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path("/app/static/tutorials")
PROVIDERS_FILE = Path("/app/backend/data/continuation_providers.json")


PROVIDER_STEPS = {
    "github": {
        "brand": "GitHub", "color": "#24292e", "accent": "#2ea44f", "icon": "🐙",
        "url": "github.com/settings/tokens",
        "steps": [
            ("سجّل الدخول لـ GitHub", "Sign in to GitHub", "github.com → Sign in"),
            ("افتح Settings → Developer settings", "Open Settings → Developer settings", "Profile menu → Settings"),
            ("Personal access tokens → Generate new (classic)", "Personal access tokens → Generate new (classic)", "Scopes: repo, workflow, read:org"),
        ],
    },
    "gitlab": {
        "brand": "GitLab", "color": "#FC6D26", "accent": "#E24329", "icon": "🦊",
        "url": "gitlab.com/-/profile/personal_access_tokens",
        "steps": [
            ("سجّل الدخول لـ GitLab", "Sign in to GitLab", "gitlab.com → Sign in"),
            ("Avatar → Edit profile → Access Tokens", "Avatar → Edit profile → Access Tokens", "Top-right avatar menu"),
            ("Add new token + اختر api, read_repository, write_repository", "Add token + select api, read_repository, write_repository", "Set expiry: 6 months"),
        ],
    },
    "bitbucket": {
        "brand": "Bitbucket", "color": "#0052CC", "accent": "#2684FF", "icon": "🪣",
        "url": "bitbucket.org/account/settings/app-passwords/",
        "steps": [
            ("سجّل الدخول لـ Bitbucket", "Sign in to Bitbucket", "bitbucket.org → Sign in"),
            ("Personal settings → App passwords", "Personal settings → App passwords", "Avatar menu"),
            ("Create app password — Repositories: Read+Write", "Create app password — Repositories: Read+Write", "Label it 'Zenrex'"),
        ],
    },
    "azure_devops": {
        "brand": "Azure DevOps", "color": "#0078D4", "accent": "#005A9E", "icon": "🔷",
        "url": "dev.azure.com/_usersSettings/tokens",
        "steps": [
            ("سجّل دخول لـ Azure DevOps", "Sign in to Azure DevOps", "dev.azure.com → Sign in"),
            ("User Settings → Personal access tokens", "User Settings → Personal access tokens", "Top-right user icon"),
            ("New Token — Code: Read & Write", "New Token — Code: Read & Write", "Custom defined → Code R/W"),
        ],
    },
    "gitea": {
        "brand": "Gitea", "color": "#609926", "accent": "#34495E", "icon": "🍵",
        "url": "your-gitea.com/user/settings/applications",
        "steps": [
            ("سجّل دخول لـ Gitea الخاص فيك", "Sign in to your Gitea", "your-gitea.com → Sign in"),
            ("Settings → Applications", "Settings → Applications", "User profile menu"),
            ("Manage Access Tokens → Generate", "Manage Access Tokens → Generate", "Scope: repo (read+write)"),
        ],
    },
    "other_git": {
        "brand": "Git Server", "color": "#F05032", "accent": "#86B04D", "icon": "🌐",
        "url": "your-git-server/settings/tokens",
        "steps": [
            ("سجّل دخول لسيرفر Git", "Sign in to your Git server", "Your private Git URL"),
            ("افتح إعدادات الـ Token الشخصي", "Open Personal Access Token settings", "Usually under Profile → Settings"),
            ("أنشئ Token مع صلاحيات Read+Write للريبو", "Generate token with Read+Write repo scopes", "Save & copy immediately"),
        ],
    },
    "vercel": {
        "brand": "Vercel", "color": "#000000", "accent": "#FFFFFF", "icon": "▲",
        "url": "vercel.com/account/tokens",
        "steps": [
            ("سجّل دخول لـ Vercel", "Sign in to Vercel", "vercel.com → Sign in"),
            ("Account → Tokens", "Account → Tokens", "Top-right avatar"),
            ("Create Token — Scope: Full Account, Expiry: 1 year", "Create Token — Scope: Full Account, Expiry: 1 year", "Name: zenrex-deploy"),
        ],
    },
    "netlify": {
        "brand": "Netlify", "color": "#00C7B7", "accent": "#011627", "icon": "🌊",
        "url": "app.netlify.com/user/applications#personal-access-tokens",
        "steps": [
            ("سجّل دخول لـ Netlify", "Sign in to Netlify", "app.netlify.com"),
            ("User settings → Applications", "User settings → Applications", "Avatar menu"),
            ("Personal access tokens → New token", "Personal access tokens → New token", "Description: 'Zenrex Continuation'"),
        ],
    },
    "cloudflare_pages": {
        "brand": "Cloudflare Pages", "color": "#F38020", "accent": "#FBAD41", "icon": "☁️",
        "url": "dash.cloudflare.com/profile/api-tokens",
        "steps": [
            ("سجّل دخول لـ Cloudflare", "Sign in to Cloudflare", "dash.cloudflare.com"),
            ("My Profile → API Tokens", "My Profile → API Tokens", "Right side menu"),
            ("Create Token → Custom: Account.Pages = Edit", "Create Token → Custom: Account.Pages = Edit", "Zone: include all"),
        ],
    },
    "hetzner": {
        "brand": "Hetzner VPS", "color": "#D50C2D", "accent": "#262626", "icon": "🖥️",
        "url": "console.hetzner.cloud",
        "steps": [
            ("افتح Hetzner Console", "Open Hetzner Console", "console.hetzner.cloud"),
            ("Security → API Tokens", "Security → API Tokens", "Project left sidebar"),
            ("Generate API Token — Read & Write", "Generate API Token — Read & Write", "Copy immediately - shown once"),
        ],
    },
    "digitalocean": {
        "brand": "DigitalOcean", "color": "#0080FF", "accent": "#00BFFF", "icon": "🌊",
        "url": "cloud.digitalocean.com/account/api/tokens",
        "steps": [
            ("سجّل دخول لـ DigitalOcean", "Sign in to DigitalOcean", "cloud.digitalocean.com"),
            ("API → Tokens / Keys", "API → Tokens / Keys", "Left sidebar"),
            ("Generate New Token — Full Access, Expiry: 1y", "Generate New Token — Full Access, Expiry: 1y", "Name: zenrex"),
        ],
    },
    "aws_ec2": {
        "brand": "AWS EC2", "color": "#FF9900", "accent": "#232F3E", "icon": "🟧",
        "url": "console.aws.amazon.com/iam/home#/users",
        "steps": [
            ("افتح AWS Console", "Open AWS Console", "console.aws.amazon.com"),
            ("IAM → Users → Add user", "IAM → Users → Add user", "Programmatic access"),
            ("Permissions: EC2 + S3 Full → Get Access Key", "Permissions: EC2 + S3 Full → Get Access Key", "Save .csv securely"),
        ],
    },
    "hostinger": {
        "brand": "Hostinger", "color": "#673DE6", "accent": "#FFFFFF", "icon": "🟣",
        "url": "hpanel.hostinger.com",
        "steps": [
            ("سجّل دخول لـ Hostinger", "Sign in to Hostinger", "hpanel.hostinger.com"),
            ("Hosting → FTP Accounts", "Hosting → FTP Accounts", "Left side menu"),
            ("Create FTP user أو استخدم الافتراضي", "Create FTP user or use default", "Note: host + user + pass"),
        ],
    },
    "godaddy": {
        "brand": "GoDaddy", "color": "#1BDBDB", "accent": "#000000", "icon": "🟢",
        "url": "developer.godaddy.com/keys",
        "steps": [
            ("سجّل دخول لـ GoDaddy", "Sign in to GoDaddy", "godaddy.com → Sign in"),
            ("My Products → Web Hosting → cPanel → FTP", "My Products → Web Hosting → cPanel → FTP", "Or use API at developer.godaddy.com"),
            ("Note host + username + password", "Note host + username + password", "Production API only"),
        ],
    },
    "bluehost": {
        "brand": "Bluehost", "color": "#0768A3", "accent": "#7AC142", "icon": "🔵",
        "url": "my.bluehost.com",
        "steps": [
            ("سجّل دخول لـ Bluehost", "Sign in to Bluehost", "my.bluehost.com"),
            ("Hosting → Advanced → FTP Accounts", "Hosting → Advanced → FTP Accounts", "Or cPanel → FTP Manager"),
            ("اعمل FTP user جديد — Document Root كامل", "Create FTP user — Document Root access", "Save credentials"),
        ],
    },
    "wordpress_com": {
        "brand": "WordPress.com", "color": "#21759B", "accent": "#D54E21", "icon": "Ⓦ",
        "url": "wordpress.com/me/security/two-step",
        "steps": [
            ("سجّل دخول لـ WordPress.com", "Sign in to WordPress.com", "wordpress.com"),
            ("Profile → Security → Application Passwords", "Profile → Security → Application Passwords", "Two-step section"),
            ("اكتب 'Zenrex' → Generate Password", "Type 'Zenrex' → Generate Password", "Copy the 24-char password"),
        ],
    },
    "render": {
        "brand": "Render", "color": "#46E3B7", "accent": "#000000", "icon": "🟩",
        "url": "dashboard.render.com/u/settings#api-keys",
        "steps": [
            ("سجّل دخول لـ Render", "Sign in to Render", "dashboard.render.com"),
            ("Account Settings → API Keys", "Account Settings → API Keys", "Top-right user menu"),
            ("Create API Key — Full account access", "Create API Key — Full account access", "Description: zenrex"),
        ],
    },
    "railway": {
        "brand": "Railway", "color": "#9966FF", "accent": "#FFFFFF", "icon": "🚂",
        "url": "railway.app/account/tokens",
        "steps": [
            ("سجّل دخول لـ Railway", "Sign in to Railway", "railway.app"),
            ("Account Settings → Tokens", "Account Settings → Tokens", "Right side avatar"),
            ("Create Token → Team scope", "Create Token → Team scope", "Note: copy once"),
        ],
    },
    "firebase": {
        "brand": "Firebase", "color": "#FFCA28", "accent": "#FF6F00", "icon": "🔥",
        "url": "console.firebase.google.com",
        "steps": [
            ("افتح Firebase Console", "Open Firebase Console", "console.firebase.google.com"),
            ("Project → Settings → Service accounts", "Project → Settings → Service accounts", "Gear icon"),
            ("Generate new private key → JSON file", "Generate new private key → JSON file", "Download — keep secret"),
        ],
    },
    "other_hosting": {
        "brand": "Hosting Generic", "color": "#6B7280", "accent": "#9CA3AF", "icon": "🌍",
        "url": "your hosting cPanel",
        "steps": [
            ("سجّل دخول لـ cPanel/Plesk الخاص فيك", "Sign in to your cPanel/Plesk", "Usually example.com/cpanel"),
            ("Files → FTP Accounts", "Files → FTP Accounts", "Or SSH Access"),
            ("اعمل user مع وصول كامل", "Create user with full access", "Save host + user + pass"),
        ],
    },
}


TEMPLATE = r"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>{brand} — Zenrex Tutorial</title>
<style>
:root {{
  --brand: {color};
  --accent: {accent};
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; }}
body {{
  font-family: -apple-system, "Segoe UI", "Cairo", "Tajawal", sans-serif;
  background: radial-gradient(circle at 30% 20%, #1a0b1a, #06030a);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  position: relative;
}}
/* Watermark — top-left, non-intrusive */
.wm {{
  position: absolute; top: 12px; left: 14px;
  font-size: 11px; font-weight: 800; color: rgba(255,255,255,0.5);
  letter-spacing: 1px; user-select: none; pointer-events: none;
  z-index: 50;
}}
.wm::before {{
  content: '⚡'; margin-inline-end: 4px;
  color: #f0abfc;
}}
/* Brand badge — top-right */
.brand-badge {{
  position: absolute; top: 10px; right: 14px;
  display: flex; align-items: center; gap: 6px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 999px; padding: 4px 12px;
  font-size: 11px; font-weight: 700;
  backdrop-filter: blur(8px);
}}
.brand-badge .ico {{ font-size: 16px; }}
/* Stage */
.stage {{
  width: 92%; max-width: 720px;
  aspect-ratio: 16 / 9;
  position: relative;
  display: flex; align-items: center; justify-content: center;
}}
.slide {{
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  text-align: center;
  opacity: 0;
  animation: cycle 18s infinite;
}}
.slide:nth-child(1) {{ animation-delay: 0s; }}
.slide:nth-child(2) {{ animation-delay: 6s; }}
.slide:nth-child(3) {{ animation-delay: 12s; }}
@keyframes cycle {{
  0%, 1%   {{ opacity: 0; transform: translateY(12px) scale(0.98); }}
  4%, 30%  {{ opacity: 1; transform: translateY(0) scale(1); }}
  33%, 100%{{ opacity: 0; transform: translateY(-12px) scale(1.02); }}
}}
.step-num {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 56px; height: 56px; border-radius: 50%;
  background: var(--brand);
  color: var(--accent);
  font-size: 28px; font-weight: 900;
  border: 3px solid rgba(255,255,255,0.2);
  margin-bottom: 18px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}}
.step-ar {{
  font-size: 24px; font-weight: 900; color: #fff;
  margin-bottom: 8px; padding: 0 16px;
  line-height: 1.4;
}}
.step-en {{
  font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.65);
  direction: ltr; font-family: -apple-system, "Segoe UI", sans-serif;
  margin-bottom: 16px; padding: 0 16px;
}}
.step-detail {{
  display: inline-block;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  padding: 8px 18px; border-radius: 8px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 12px; color: #f0abfc;
  direction: ltr;
}}
/* Progress dots */
.dots {{
  position: absolute; bottom: 14px; left: 50%;
  transform: translateX(-50%);
  display: flex; gap: 8px;
  z-index: 30;
}}
.dot {{
  width: 8px; height: 8px; border-radius: 50%;
  background: rgba(255,255,255,0.2);
  transition: background 0.3s;
}}
.dot.active {{ background: #f0abfc; }}
.dot:nth-child(1) {{ animation: dot1 18s infinite; }}
.dot:nth-child(2) {{ animation: dot2 18s infinite; }}
.dot:nth-child(3) {{ animation: dot3 18s infinite; }}
@keyframes dot1 {{ 0%, 33% {{ background: #f0abfc; }} 34%, 100% {{ background: rgba(255,255,255,0.2); }} }}
@keyframes dot2 {{ 0%, 33% {{ background: rgba(255,255,255,0.2); }} 34%, 66% {{ background: #f0abfc; }} 67%, 100% {{ background: rgba(255,255,255,0.2); }} }}
@keyframes dot3 {{ 0%, 66% {{ background: rgba(255,255,255,0.2); }} 67%, 100% {{ background: #f0abfc; }} }}
/* Animated browser-window mockup behind each slide */
.browser {{
  position: absolute; top: 12%; left: 8%; right: 8%; bottom: 30%;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  pointer-events: none;
  z-index: 1;
}}
.browser::before {{
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 22px;
  background: rgba(255,255,255,0.04);
  border-top-left-radius: 12px; border-top-right-radius: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}}
.browser::after {{
  content: '○ ○ ○';
  position: absolute; top: 4px; left: 8px;
  font-size: 9px; color: rgba(255,255,255,0.3); letter-spacing: 4px;
}}
.url-bar {{
  position: absolute; top: 4px; left: 60px; right: 12px;
  height: 14px;
  background: rgba(0,0,0,0.3);
  border-radius: 7px;
  font-size: 9px; color: rgba(255,255,255,0.5);
  font-family: ui-monospace, monospace;
  display: flex; align-items: center; padding: 0 8px;
  direction: ltr;
}}
.slide > * {{ position: relative; z-index: 2; }}
</style>
</head>
<body>
<div class="wm">ZENREX</div>
<div class="brand-badge">
  <span class="ico">{icon}</span>
  <span>{brand}</span>
</div>

<div class="stage">
  <div class="browser">
    <div class="url-bar">{url}</div>
  </div>

  <div class="slide">
    <div class="step-num">1</div>
    <div class="step-ar">{s1_ar}</div>
    <div class="step-en">{s1_en}</div>
    <div class="step-detail">{s1_detail}</div>
  </div>

  <div class="slide">
    <div class="step-num">2</div>
    <div class="step-ar">{s2_ar}</div>
    <div class="step-en">{s2_en}</div>
    <div class="step-detail">{s2_detail}</div>
  </div>

  <div class="slide">
    <div class="step-num">3</div>
    <div class="step-ar">{s3_ar}</div>
    <div class="step-en">{s3_en}</div>
    <div class="step-detail">{s3_detail}</div>
  </div>

  <div class="dots">
    <div class="dot"></div>
    <div class="dot"></div>
    <div class="dot"></div>
  </div>
</div>
</body>
</html>
"""


def build_all() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    written = 0
    for pid, cfg in PROVIDER_STEPS.items():
        s1, s2, s3 = cfg["steps"]
        html = TEMPLATE.format(
            brand=cfg["brand"], color=cfg["color"], accent=cfg["accent"],
            icon=cfg["icon"], url=cfg["url"],
            s1_ar=s1[0], s1_en=s1[1], s1_detail=s1[2],
            s2_ar=s2[0], s2_en=s2[1], s2_detail=s2[2],
            s3_ar=s3[0], s3_en=s3[1], s3_detail=s3[2],
        )
        (ROOT / f"{pid}.html").write_text(html, encoding="utf-8")
        written += 1
    print(f"✓ wrote {written} tutorial HTML files to {ROOT}")

    # Patch continuation_providers.json — point tutorial_video_ar to the new HTMLs.
    with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    for section in ("git_providers", "hosting_providers"):
        for p in data.get(section, []):
            pid = p.get("id")
            if pid in PROVIDER_STEPS:
                p["tutorial_video_ar"] = f"/static/tutorials/{pid}.html"
                p["tutorial_video_en"] = f"/static/tutorials/{pid}.html"
    with open(PROVIDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ patched {PROVIDERS_FILE} with new tutorial URLs")


if __name__ == "__main__":
    build_all()
