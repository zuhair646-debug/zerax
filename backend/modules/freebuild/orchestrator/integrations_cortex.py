"""
🌐 Integrations Cortex — quick wiring for popular third-party services.

Just glue code generators. Each function returns a code snippet the AI
can paste into a project. Real integration playbooks live in:
  - emergent_integrations_manager (for Emergent LLM key)
  - integration_playbook_expert_v2 (for paid integrations)

This is just the "I know how to wire these in a snippet" layer.
"""
from __future__ import annotations

from typing import Any, Dict, List


def sentry_setup_js() -> Dict[str, str]:
    return {
        "type": "monitoring",
        "name": "Sentry Error Tracking",
        "install": "npm install @sentry/browser",
        "head_inject": '<script src="https://browser.sentry-cdn.com/8.0.0/bundle.min.js" crossorigin="anonymous"></script>',
        "init_snippet": """if (window.Sentry) {
  Sentry.init({
    dsn: 'YOUR_SENTRY_DSN_HERE',
    integrations: [new Sentry.BrowserTracing()],
    tracesSampleRate: 0.1,
    environment: 'production',
  });
}"""
    }


def posthog_setup_js() -> Dict[str, str]:
    return {
        "type": "analytics",
        "name": "PostHog Product Analytics",
        "head_inject": """<script>
!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
posthog.init('YOUR_POSTHOG_API_KEY',{api_host:'https://app.posthog.com'});
</script>"""
    }


def google_analytics_setup_js(measurement_id: str = "G-XXXXXXXXXX") -> Dict[str, str]:
    return {
        "type": "analytics",
        "name": "Google Analytics 4",
        "head_inject": f"""<script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{measurement_id}');
</script>"""
    }


def crisp_chat_setup_js(website_id: str = "YOUR_CRISP_ID") -> Dict[str, str]:
    return {
        "type": "support",
        "name": "Crisp Live Chat",
        "body_inject": f"""<script type="text/javascript">
window.$crisp=[];window.CRISP_WEBSITE_ID="{website_id}";
(function(){{d=document;s=d.createElement("script");s.src="https://client.crisp.chat/l.js";s.async=1;d.getElementsByTagName("head")[0].appendChild(s);}})();
</script>"""
    }


def s3_upload_node_snippet() -> Dict[str, str]:
    return {
        "type": "storage",
        "name": "S3-compatible upload (R2/Backblaze)",
        "install": "npm install @aws-sdk/client-s3 @aws-sdk/s3-request-presigner",
        "code": """import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

const s3 = new S3Client({
  endpoint: process.env.S3_ENDPOINT, // 'https://<accountid>.r2.cloudflarestorage.com'
  region: process.env.S3_REGION || 'auto',
  credentials: {
    accessKeyId: process.env.S3_ACCESS_KEY,
    secretAccessKey: process.env.S3_SECRET_KEY,
  },
});

export async function getUploadUrl(key, contentType = 'application/octet-stream') {
  const cmd = new PutObjectCommand({
    Bucket: process.env.S3_BUCKET,
    Key: key,
    ContentType: contentType,
  });
  return await getSignedUrl(s3, cmd, { expiresIn: 3600 });
}"""
    }


def list_all() -> List[Dict[str, str]]:
    """Return all available integration generators."""
    return [
        {"id": "sentry", "name": "Sentry Error Tracking", "type": "monitoring"},
        {"id": "posthog", "name": "PostHog Analytics", "type": "analytics"},
        {"id": "google_analytics", "name": "Google Analytics 4", "type": "analytics"},
        {"id": "crisp_chat", "name": "Crisp Live Chat", "type": "support"},
        {"id": "s3_upload", "name": "S3/R2 Upload", "type": "storage"},
    ]
