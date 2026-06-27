"""
📲 Capacitor Mobile Cortex — wraps a web app as a Capacitor native app.

Generates:
  - capacitor.config.ts
  - android/ + ios/ folder instructions
  - package.json with @capacitor/* deps
  - Build instructions (Arabic) for the user to run locally

HONEST LIMITATION: We CAN'T build the .apk/.ipa here (needs Android Studio /
Xcode). We give the user a ready project they can build on their machine.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List


def build_capacitor_config(app_id: str, app_name: str, web_dir: str = "dist") -> str:
    return f"""import {{ CapacitorConfig }} from '@capacitor/cli';

const config: CapacitorConfig = {{
  appId: '{app_id}',
  appName: '{app_name}',
  webDir: '{web_dir}',
  bundledWebRuntime: false,
  server: {{
    androidScheme: 'https',
    allowNavigation: ['*']
  }},
  plugins: {{
    SplashScreen: {{
      launchShowDuration: 2000,
      backgroundColor: '#0a0a0a',
      androidScaleType: 'CENTER_CROP'
    }},
    PushNotifications: {{
      presentationOptions: ['badge', 'sound', 'alert']
    }}
  }}
}};

export default config;"""


def capacitor_package_json(app_name: str = "zenrex-app", capacitor_version: str = "^6.0.0") -> str:
    return json.dumps({
        "name": app_name,
        "version": "1.0.0",
        "scripts": {
            "build": "echo 'build your web app to ./dist first'",
            "cap:sync": "cap sync",
            "cap:android": "cap open android",
            "cap:ios": "cap open ios",
            "android": "cap run android",
            "ios": "cap run ios"
        },
        "dependencies": {
            "@capacitor/core": capacitor_version,
            "@capacitor/android": capacitor_version,
            "@capacitor/ios": capacitor_version,
            "@capacitor/splash-screen": capacitor_version,
            "@capacitor/push-notifications": capacitor_version,
            "@capacitor/status-bar": capacitor_version,
            "@capacitor/preferences": capacitor_version,
            "@capacitor/network": capacitor_version
        },
        "devDependencies": {
            "@capacitor/cli": capacitor_version
        }
    }, indent=2)


def build_instructions_ar(app_name: str = "تطبيقك") -> str:
    return f"""# 📱 بناء {app_name} كتطبيق Android/iOS — Capacitor

## المتطلبات على جهازك (مش هنا في Zenrex):
- **Android:** Android Studio + JDK 17+
- **iOS:** macOS + Xcode 15+ + Apple Developer account (للنشر)
- Node.js 18+

## الخطوات:

```bash
# 1. ثبّت dependencies
npm install

# 2. ابني الـ web app (Vite/React/Next)
npm run build

# 3. أضف الـ platforms (مرة وحدة)
npx cap add android
npx cap add ios

# 4. زامن web → native
npx cap sync

# 5. افتح Android Studio أو Xcode
npx cap open android
# أو
npx cap open ios

# 6. من الـ IDE: ابني الـ APK/IPA
```

## نشر:
- **Android:** Google Play Console — `Generate Signed Bundle`
- **iOS:** App Store Connect — `Archive → Distribute App`

## ⚠️ ملاحظات:
- نحن ولّدنا لك الـ Capacitor wrapper كاملاً
- البناء الفعلي للـ APK/IPA يحتاج جهازك (Apple ما يسمح ببناء iOS على غير macOS)
- لو ودك CI/CD: استخدم GitHub Actions + EAS Build (Expo) أو Bitrise
"""


def push_native_snippet_js() -> str:
    """JS that wires Capacitor Push notifications."""
    return """import { PushNotifications } from '@capacitor/push-notifications';

export async function setupPushNotifications() {
  let permStatus = await PushNotifications.checkPermissions();
  if (permStatus.receive === 'prompt') {
    permStatus = await PushNotifications.requestPermissions();
  }
  if (permStatus.receive !== 'granted') return;
  await PushNotifications.register();

  PushNotifications.addListener('registration', (token) => {
    console.log('FCM token:', token.value);
    // Send token to your backend
    fetch('/api/push/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token.value, platform: 'capacitor' }),
    });
  });

  PushNotifications.addListener('pushNotificationReceived', (n) => {
    console.log('push received:', n);
  });

  PushNotifications.addListener('pushNotificationActionPerformed', (a) => {
    console.log('push tapped:', a);
    // route handling here
  });
}"""
