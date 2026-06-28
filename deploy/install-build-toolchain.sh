#!/usr/bin/env bash
# install-build-toolchain.sh — Prepare the Zenrex VPS to actually build mobile
# apps in its OWN sandbox (no reliance on EAS/Codemagic external services).
#
# Run this ONCE on the production VPS:
#   bash /app/deploy/install-build-toolchain.sh
# It downloads Android SDK + Flutter + Node + Xcode CLI tools surrogates (not
# real Xcode — iOS .ipa still needs a Mac, but Android/RN/Flutter Android
# builds can run fully on Linux).
#
# Idempotent — re-running just upgrades versions and skips already-installed.
set -e

BUILD_ROOT="/opt/zerax/build-images"
mkdir -p "$BUILD_ROOT"
cd "$BUILD_ROOT"

echo "🛠  Zenrex Build Toolchain Installer"
echo "    Target: $BUILD_ROOT"
echo ""

# ─── 1. Java 17 (required by Android SDK + Gradle) ──────────────────────
if ! java -version 2>&1 | grep -q "17\."; then
  echo "📦 Installing OpenJDK 17..."
  apt-get update -qq
  apt-get install -y -qq openjdk-17-jdk-headless unzip wget curl
else
  echo "✓ Java 17 already installed"
fi

# ─── 2. Android command-line tools + SDK ────────────────────────────────
ANDROID_HOME="$BUILD_ROOT/android-sdk"
export ANDROID_HOME
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

if [ ! -d "$ANDROID_HOME/cmdline-tools/latest" ]; then
  echo "📦 Downloading Android command-line tools..."
  mkdir -p "$ANDROID_HOME/cmdline-tools"
  cd "$ANDROID_HOME/cmdline-tools"
  wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O tools.zip
  unzip -q tools.zip
  mv cmdline-tools latest
  rm tools.zip
  echo "✓ Android command-line tools installed"
else
  echo "✓ Android cmdline-tools present"
fi

# Accept licenses + install platform-tools + Android API 34 + build-tools
if [ ! -d "$ANDROID_HOME/platforms/android-34" ]; then
  echo "📦 Installing Android API 34 + build-tools 34.0.0..."
  yes | sdkmanager --licenses > /dev/null 2>&1 || true
  sdkmanager --install "platform-tools" "platforms;android-34" "build-tools;34.0.0" > /dev/null
  echo "✓ Android SDK 34 ready"
else
  echo "✓ Android SDK 34 already installed"
fi

# ─── 3. Flutter SDK ─────────────────────────────────────────────────────
FLUTTER_HOME="$BUILD_ROOT/flutter"
export FLUTTER_HOME
export PATH="$FLUTTER_HOME/bin:$PATH"

if [ ! -d "$FLUTTER_HOME" ]; then
  echo "📦 Downloading Flutter stable..."
  cd "$BUILD_ROOT"
  wget -q https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.24.5-stable.tar.xz -O flutter.tar.xz
  tar xf flutter.tar.xz
  rm flutter.tar.xz
  flutter precache --android --no-ios --no-linux --no-web --no-windows --no-macos > /dev/null 2>&1 || true
  echo "✓ Flutter installed"
else
  echo "✓ Flutter already installed"
fi

# ─── 4. Node 20 (for React Native / Expo / Capacitor) ───────────────────
if ! node --version 2>/dev/null | grep -qE "^v(20|21|22)\."; then
  echo "📦 Installing Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
  apt-get install -y -qq nodejs
  npm install -g yarn eas-cli@latest > /dev/null 2>&1
  echo "✓ Node 20 + yarn + eas-cli installed"
else
  echo "✓ Node already installed: $(node --version)"
fi

# ─── 5. Persist toolchain paths for the AI sandbox runner ───────────────
cat > "$BUILD_ROOT/env.sh" <<EOF
# Sourced by the Zenrex AI sandbox runner before invoking build commands.
export JAVA_HOME=\$(dirname \$(dirname \$(readlink -f \$(which java))))
export ANDROID_HOME="$ANDROID_HOME"
export ANDROID_SDK_ROOT="\$ANDROID_HOME"
export FLUTTER_HOME="$FLUTTER_HOME"
export PATH="\$FLUTTER_HOME/bin:\$ANDROID_HOME/cmdline-tools/latest/bin:\$ANDROID_HOME/platform-tools:\$PATH"
EOF
echo "✓ Toolchain env vars persisted to $BUILD_ROOT/env.sh"

# ─── 6. Smoke checks ────────────────────────────────────────────────────
echo ""
echo "🩺 Smoke checks:"
source "$BUILD_ROOT/env.sh"
echo "   java         : $(java -version 2>&1 | head -1)"
echo "   sdkmanager   : $(sdkmanager --version 2>&1 | head -1)"
echo "   adb          : $(adb --version 2>&1 | head -1)"
echo "   flutter      : $(flutter --version 2>&1 | head -1)"
echo "   node/yarn    : $(node --version) / $(yarn --version)"
echo "   eas-cli      : $(eas --version 2>&1 | head -1)"
echo ""
echo "✅ Toolchain ready at $BUILD_ROOT"
echo "   The AI sandbox runner now auto-sources $BUILD_ROOT/env.sh before"
echo "   running any build command, so 'flutter build apk', 'gradlew assembleRelease',"
echo "   'expo prebuild', etc. work locally without external CI."
