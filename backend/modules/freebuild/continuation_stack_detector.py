"""Universal Stack Detector for Continuation mode.

Given a sandbox directory containing a real codebase, this module inspects
manifest/lockfiles and tells the AI Engineer Manager:
  • What programming stacks/frameworks are present (one or more)
  • What package manager is used
  • Where the entry points / build artifacts live
  • Recommended build / test / install / lint commands
  • Special quirks (e.g. needs Xcode, needs Android SDK, needs Docker)

This is the FOUNDATION that lets a single set of generic AI tools support
EVERY programming language and app type — instead of hard-coding a separate
tool for React Native, Flutter, .NET, Go, Rust, etc.

Design rules:
  • Pure-Python, zero external deps (just stdlib + Path)
  • Read-only — never writes to the sandbox
  • Cheap — only inspects manifest/lock files, never traverses node_modules
  • Confidence-scored — multi-stack projects (e.g. Flutter app + Go backend)
    are returned as a list ordered by confidence
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


# ───────────────────────────────────────────────────────────────────
# Pattern → stack map. Each entry says: "if this manifest exists,
# emit this StackInfo with these build/test/install hints."
# Ordered roughly by specificity (more-specific first).
# ───────────────────────────────────────────────────────────────────


@dataclass
class StackInfo:
    id: str                       # canonical id, e.g. 'flutter', 'react_native'
    name: str                     # human label
    category: str                 # mobile | web | backend | desktop | game | cms | hybrid
    language: str                 # primary language
    package_manager: Optional[str] = None
    entry_files: List[str] = field(default_factory=list)
    build_command: Optional[str] = None
    test_command: Optional[str] = None
    install_command: Optional[str] = None
    lint_command: Optional[str] = None
    dev_command: Optional[str] = None
    artifact_paths: List[str] = field(default_factory=list)
    needs_cloud_build: bool = False        # e.g. iOS needs macOS / EAS
    needs_native_sdk: List[str] = field(default_factory=list)  # ['android', 'xcode', 'dotnet']
    confidence: float = 1.0
    notes_ar: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Each detector returns Optional[StackInfo] given the sandbox Path.
# Multiple detectors can match (e.g. Flutter for app + Go for backend).
def _read_text_safe(path: Path, max_bytes: int = 200_000) -> Optional[str]:
    try:
        if path.is_file() and path.stat().st_size <= max_bytes:
            return path.read_text("utf-8", errors="replace")
    except Exception:
        return None
    return None


def _read_json_safe(path: Path) -> Optional[Dict[str, Any]]:
    txt = _read_text_safe(path)
    if not txt:
        return None
    try:
        return json.loads(txt)
    except Exception:
        return None


# ─── Mobile / Cross-Platform ──────────────────────────────────────
def detect_flutter(root: Path) -> Optional[StackInfo]:
    pub = root / "pubspec.yaml"
    if not pub.is_file():
        return None
    return StackInfo(
        id="flutter", name="Flutter", category="mobile", language="Dart",
        package_manager="pub", entry_files=["lib/main.dart"],
        install_command="flutter pub get",
        build_command="flutter build apk --release",
        test_command="flutter test",
        lint_command="flutter analyze",
        dev_command="flutter run",
        artifact_paths=["build/app/outputs/flutter-apk/app-release.apk",
                        "build/ios/iphoneos/Runner.app"],
        needs_native_sdk=["android", "xcode"],
        notes_ar="Flutter متعدد المنصات. iOS يتطلب macOS أو EAS/Codemagic.",
    )


def detect_react_native(root: Path) -> Optional[StackInfo]:
    pkg = _read_json_safe(root / "package.json")
    if not pkg:
        return None
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    if "react-native" not in deps:
        return None
    is_expo = "expo" in deps
    return StackInfo(
        id="expo" if is_expo else "react_native",
        name="Expo (React Native)" if is_expo else "React Native (bare)",
        category="mobile", language="TypeScript/JavaScript",
        package_manager="yarn" if (root / "yarn.lock").is_file() else "npm",
        entry_files=["App.tsx", "App.js", "index.js"],
        install_command="yarn install" if (root / "yarn.lock").is_file() else "npm install",
        build_command=(
            "eas build --platform android --non-interactive"
            if is_expo else "cd android && ./gradlew assembleRelease"
        ),
        test_command="yarn jest" if (root / "jest.config.js").is_file() or "jest" in deps else None,
        lint_command="yarn lint" if "eslint" in deps else None,
        dev_command="expo start" if is_expo else "npx react-native start",
        artifact_paths=["android/app/build/outputs/apk/release/app-release.apk"],
        needs_cloud_build=is_expo,
        needs_native_sdk=["android", "xcode"],
        notes_ar=("Expo — البناء عبر EAS Cloud. iOS يحتاج EAS." if is_expo
                  else "React Native bare — يتطلب Android Studio محلياً + Xcode للـ iOS."),
    )


def detect_capacitor(root: Path) -> Optional[StackInfo]:
    pkg = _read_json_safe(root / "package.json")
    cap = root / "capacitor.config.ts"
    cap_json = root / "capacitor.config.json"
    if not pkg and not cap.is_file() and not cap_json.is_file():
        return None
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})} if pkg else {}
    if not any(k.startswith("@capacitor/") for k in deps) and not cap.is_file() and not cap_json.is_file():
        return None
    return StackInfo(
        id="capacitor", name="Ionic Capacitor", category="hybrid", language="TypeScript/JavaScript",
        package_manager="npm",
        install_command="npm install && npx cap sync",
        build_command="npm run build && npx cap copy && cd android && ./gradlew assembleRelease",
        test_command="npm test" if "jest" in deps or "vitest" in deps else None,
        dev_command="npm run dev",
        artifact_paths=["android/app/build/outputs/apk/release/app-release.apk"],
        needs_native_sdk=["android", "xcode"],
        notes_ar="Capacitor (PWA → APK/IPA). iOS يحتاج macOS.",
    )


def detect_ionic(root: Path) -> Optional[StackInfo]:
    cfg = root / "ionic.config.json"
    if cfg.is_file():
        return StackInfo(
            id="ionic", name="Ionic", category="hybrid", language="TypeScript",
            package_manager="npm", install_command="npm install",
            build_command="ionic build --prod",
            artifact_paths=["www/"],
            notes_ar="Ionic — عادة يستخدم Capacitor للـ build الأصلي.",
        )
    return None


def detect_cordova(root: Path) -> Optional[StackInfo]:
    if (root / "config.xml").is_file() and "<widget" in (_read_text_safe(root / "config.xml") or ""):
        return StackInfo(
            id="cordova", name="Apache Cordova", category="hybrid", language="JavaScript",
            package_manager="npm", install_command="npm install",
            build_command="cordova build android",
            artifact_paths=["platforms/android/app/build/outputs/apk/"],
            notes_ar="Cordova — قديم لكن مدعوم.",
        )
    return None


def detect_nativescript(root: Path) -> Optional[StackInfo]:
    if (root / "nativescript.config.ts").is_file() or (root / "nativescript.config.js").is_file():
        return StackInfo(
            id="nativescript", name="NativeScript", category="mobile", language="TypeScript",
            package_manager="npm", install_command="npm install",
            build_command="ns build android --release",
            notes_ar="NativeScript — بناء أصلي بدون WebView.",
        )
    return None


def detect_xamarin_maui(root: Path) -> Optional[StackInfo]:
    csprojs = list(root.glob("*.csproj")) + list(root.glob("**/*.csproj"))
    for f in csprojs[:5]:
        txt = _read_text_safe(f) or ""
        if "-android" in txt or "-ios" in txt or "Maui" in txt or "UseMaui" in txt:
            return StackInfo(
                id="dotnet_maui", name=".NET MAUI", category="mobile", language="C#",
                package_manager="dotnet", install_command="dotnet restore",
                build_command="dotnet build -c Release",
                test_command="dotnet test",
                needs_native_sdk=["dotnet", "android", "xcode"],
                notes_ar=".NET MAUI — يبني لـ iOS/Android/Windows/Mac. iOS يحتاج macOS.",
            )
    return None


# ─── Native Android ───────────────────────────────────────────────
def detect_android_native(root: Path) -> Optional[StackInfo]:
    if not ((root / "build.gradle").is_file() or (root / "build.gradle.kts").is_file()
            or (root / "settings.gradle").is_file() or (root / "settings.gradle.kts").is_file()):
        return None
    # Skip if it's a sub-folder of an RN/Flutter project (parent has pubspec/package.json)
    if (root.parent / "pubspec.yaml").is_file() or (root.parent / "package.json").is_file():
        return None
    is_kotlin = bool(list(root.rglob("*.kt"))[:1])
    return StackInfo(
        id="android_native",
        name="Android Native (Kotlin)" if is_kotlin else "Android Native (Java)",
        category="mobile", language="Kotlin" if is_kotlin else "Java",
        package_manager="gradle",
        install_command="./gradlew --refresh-dependencies",
        build_command="./gradlew assembleRelease",
        test_command="./gradlew test",
        lint_command="./gradlew lint",
        artifact_paths=["app/build/outputs/apk/release/app-release.apk",
                        "app/build/outputs/bundle/release/app-release.aab"],
        needs_native_sdk=["android"],
        notes_ar="Android أصلي. يتطلب Android SDK + JDK 17+.",
    )


# ─── Native iOS ───────────────────────────────────────────────────
def detect_ios_native(root: Path) -> Optional[StackInfo]:
    pods = root / "Podfile"
    xcodeproj = list(root.glob("*.xcodeproj"))[:1]
    pkg_swift = root / "Package.swift"
    if not (pods.is_file() or xcodeproj or pkg_swift.is_file()):
        return None
    has_swift = bool(list(root.rglob("*.swift"))[:1])
    return StackInfo(
        id="ios_native",
        name="iOS Native (Swift)" if has_swift else "iOS Native (Objective-C)",
        category="mobile", language="Swift" if has_swift else "Objective-C",
        package_manager="cocoapods" if pods.is_file() else "spm",
        install_command="pod install" if pods.is_file() else "swift package resolve",
        build_command="xcodebuild -workspace *.xcworkspace -scheme Release archive",
        test_command="xcodebuild test",
        needs_cloud_build=True,  # cannot build .ipa on Linux
        needs_native_sdk=["xcode"],
        notes_ar="iOS أصلي. لا يمكن البناء على Linux — يجب استخدام Codemagic أو EAS أو macOS محلي.",
    )


# ─── Desktop ──────────────────────────────────────────────────────
def detect_electron(root: Path) -> Optional[StackInfo]:
    pkg = _read_json_safe(root / "package.json")
    if not pkg:
        return None
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    if "electron" not in deps:
        return None
    return StackInfo(
        id="electron", name="Electron", category="desktop", language="JavaScript/TypeScript",
        package_manager="npm",
        install_command="npm install",
        build_command="npm run build && npx electron-builder",
        test_command="npm test" if "jest" in deps or "vitest" in deps else None,
        dev_command="npm start",
        artifact_paths=["dist/"],
        notes_ar="Electron — تطبيق سطح مكتب Windows/Mac/Linux.",
    )


def detect_tauri(root: Path) -> Optional[StackInfo]:
    if (root / "src-tauri" / "tauri.conf.json").is_file() or (root / "src-tauri" / "Cargo.toml").is_file():
        return StackInfo(
            id="tauri", name="Tauri", category="desktop", language="Rust + JS",
            package_manager="cargo",
            install_command="npm install && cd src-tauri && cargo fetch",
            build_command="npm run tauri build",
            artifact_paths=["src-tauri/target/release/"],
            needs_native_sdk=["rust"],
            notes_ar="Tauri — تطبيق سطح مكتب خفيف بـ Rust.",
        )
    return None


# ─── Backend ──────────────────────────────────────────────────────
def detect_nodejs_backend(root: Path) -> Optional[StackInfo]:
    pkg = _read_json_safe(root / "package.json")
    if not pkg:
        return None
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    # If react/vue/svelte present, it's frontend, not backend
    if any(k in deps for k in ("react", "vue", "svelte", "next", "nuxt", "react-native", "expo")):
        return None
    server_libs = {"express", "fastify", "koa", "hapi", "@nestjs/core", "hono", "elysia"}
    if not (server_libs & set(deps)):
        return None
    framework = next(iter(server_libs & set(deps)), "node")
    return StackInfo(
        id=f"node_{framework.replace('@nestjs/core', 'nestjs').replace('-', '_')}",
        name=f"Node.js ({framework})", category="backend", language="JavaScript/TypeScript",
        package_manager="yarn" if (root / "yarn.lock").is_file() else "npm",
        install_command="yarn install" if (root / "yarn.lock").is_file() else "npm install",
        build_command="npm run build" if "build" in (pkg.get("scripts") or {}) else None,
        test_command="npm test" if "test" in (pkg.get("scripts") or {}) else None,
        dev_command=(pkg.get("scripts") or {}).get("dev") or (pkg.get("scripts") or {}).get("start"),
        notes_ar=f"Node.js backend بإطار {framework}.",
    )


def detect_nextjs(root: Path) -> Optional[StackInfo]:
    pkg = _read_json_safe(root / "package.json")
    if not pkg:
        return None
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    if "next" not in deps:
        return None
    return StackInfo(
        id="nextjs", name="Next.js", category="web", language="TypeScript/JavaScript",
        package_manager="yarn" if (root / "yarn.lock").is_file() else "npm",
        install_command="yarn install" if (root / "yarn.lock").is_file() else "npm install",
        build_command="next build",
        test_command="npm test" if "jest" in deps or "vitest" in deps else None,
        dev_command="next dev",
        artifact_paths=[".next/"],
        notes_ar="Next.js — React SSR/SSG.",
    )


def detect_react(root: Path) -> Optional[StackInfo]:
    pkg = _read_json_safe(root / "package.json")
    if not pkg:
        return None
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    if "react" not in deps or "next" in deps or "react-native" in deps:
        return None
    is_vite = "vite" in deps
    return StackInfo(
        id="react_vite" if is_vite else "react_cra",
        name="React + Vite" if is_vite else "React (Create React App)",
        category="web", language="TypeScript/JavaScript",
        package_manager="yarn" if (root / "yarn.lock").is_file() else "npm",
        install_command="yarn install" if (root / "yarn.lock").is_file() else "npm install",
        build_command="vite build" if is_vite else "react-scripts build",
        test_command=(pkg.get("scripts") or {}).get("test"),
        dev_command="vite" if is_vite else "react-scripts start",
        artifact_paths=["build/", "dist/"],
        notes_ar="React SPA.",
    )


def detect_vue_nuxt(root: Path) -> Optional[StackInfo]:
    pkg = _read_json_safe(root / "package.json")
    if not pkg:
        return None
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    if "nuxt" in deps:
        return StackInfo(id="nuxt", name="Nuxt.js", category="web", language="TypeScript/JavaScript",
                         package_manager="npm", install_command="npm install",
                         build_command="nuxt build", dev_command="nuxt dev",
                         notes_ar="Nuxt.js — Vue SSR.")
    if "vue" in deps:
        return StackInfo(id="vue", name="Vue.js", category="web", language="TypeScript/JavaScript",
                         package_manager="npm", install_command="npm install",
                         build_command="vue-cli-service build", dev_command="vue-cli-service serve",
                         notes_ar="Vue.js SPA.")
    return None


def detect_python(root: Path) -> Optional[StackInfo]:
    has_req = (root / "requirements.txt").is_file()
    has_poetry = (root / "pyproject.toml").is_file() and "poetry" in (_read_text_safe(root / "pyproject.toml") or "").lower()
    has_pip = (root / "setup.py").is_file() or (root / "pyproject.toml").is_file()
    if not (has_req or has_poetry or has_pip):
        return None
    # Detect framework
    req_text = (_read_text_safe(root / "requirements.txt") or "") + (_read_text_safe(root / "pyproject.toml") or "")
    framework = "python"
    install = "pip install -r requirements.txt" if has_req else ("poetry install" if has_poetry else "pip install -e .")
    if "fastapi" in req_text.lower():
        framework, dev = "fastapi", "uvicorn main:app --reload"
    elif "django" in req_text.lower():
        framework, dev = "django", "python manage.py runserver"
    elif "flask" in req_text.lower():
        framework, dev = "flask", "flask run"
    else:
        dev = "python main.py"
    return StackInfo(
        id=f"python_{framework}", name=f"Python ({framework})", category="backend", language="Python",
        package_manager="poetry" if has_poetry else "pip",
        install_command=install,
        test_command="pytest" if "pytest" in req_text.lower() else None,
        lint_command="ruff check ." if "ruff" in req_text.lower() else "flake8" if "flake8" in req_text.lower() else None,
        dev_command=dev,
        notes_ar=f"Python {framework} backend.",
    )


def detect_go(root: Path) -> Optional[StackInfo]:
    if not (root / "go.mod").is_file():
        return None
    return StackInfo(
        id="go", name="Go", category="backend", language="Go",
        package_manager="go modules",
        install_command="go mod download",
        build_command="go build -o app ./...",
        test_command="go test ./...",
        lint_command="go vet ./...",
        dev_command="go run .",
        notes_ar="Go backend — يبني binary واحد.",
    )


def detect_rust(root: Path) -> Optional[StackInfo]:
    if not (root / "Cargo.toml").is_file():
        return None
    return StackInfo(
        id="rust", name="Rust", category="backend", language="Rust",
        package_manager="cargo",
        install_command="cargo fetch",
        build_command="cargo build --release",
        test_command="cargo test",
        lint_command="cargo clippy",
        dev_command="cargo run",
        notes_ar="Rust — أداء عالي.",
    )


def detect_java_spring(root: Path) -> Optional[StackInfo]:
    if (root / "pom.xml").is_file():
        txt = _read_text_safe(root / "pom.xml") or ""
        framework = "spring-boot" if "spring-boot" in txt else "java"
        return StackInfo(
            id=f"java_{framework.replace('-', '_')}",
            name=f"Java ({framework})", category="backend", language="Java",
            package_manager="maven",
            install_command="mvn dependency:resolve",
            build_command="mvn package -DskipTests",
            test_command="mvn test",
            dev_command="mvn spring-boot:run" if framework == "spring-boot" else "mvn exec:java",
            notes_ar=f"Java {framework} — Maven.",
        )
    if (root / "build.gradle").is_file() and (root / "src" / "main" / "java").is_dir():
        return StackInfo(
            id="java_gradle", name="Java (Gradle)", category="backend", language="Java",
            package_manager="gradle",
            install_command="./gradlew dependencies",
            build_command="./gradlew build",
            test_command="./gradlew test",
            notes_ar="Java + Gradle.",
        )
    return None


def detect_dotnet(root: Path) -> Optional[StackInfo]:
    csprojs = list(root.glob("*.csproj")) + list(root.glob("**/*.csproj"))
    if not csprojs:
        return None
    # MAUI detection already handles mobile-specific .NET
    return StackInfo(
        id="dotnet", name=".NET", category="backend", language="C#",
        package_manager="dotnet",
        install_command="dotnet restore",
        build_command="dotnet build -c Release",
        test_command="dotnet test",
        dev_command="dotnet run",
        notes_ar=".NET — ASP.NET Core أو console.",
    )


def detect_php_laravel(root: Path) -> Optional[StackInfo]:
    if not (root / "composer.json").is_file():
        return None
    composer = _read_json_safe(root / "composer.json") or {}
    req = composer.get("require") or {}
    is_laravel = "laravel/framework" in req
    is_symfony = "symfony/framework-bundle" in req
    name = "Laravel" if is_laravel else ("Symfony" if is_symfony else "PHP")
    return StackInfo(
        id=f"php_{name.lower()}", name=f"PHP ({name})", category="backend", language="PHP",
        package_manager="composer",
        install_command="composer install",
        build_command="composer dump-autoload --optimize",
        test_command="vendor/bin/phpunit" if "phpunit/phpunit" in (composer.get("require-dev") or {}) else None,
        dev_command="php artisan serve" if is_laravel else "php -S localhost:8000",
        notes_ar=f"PHP {name}.",
    )


def detect_ruby_rails(root: Path) -> Optional[StackInfo]:
    if not (root / "Gemfile").is_file():
        return None
    gemfile = _read_text_safe(root / "Gemfile") or ""
    is_rails = "rails" in gemfile.lower()
    return StackInfo(
        id="ruby_rails" if is_rails else "ruby",
        name="Ruby on Rails" if is_rails else "Ruby",
        category="backend", language="Ruby",
        package_manager="bundler",
        install_command="bundle install",
        build_command="bundle exec rails assets:precompile" if is_rails else None,
        test_command="bundle exec rspec" if "rspec" in gemfile.lower() else "bundle exec rake test",
        dev_command="bundle exec rails server" if is_rails else "ruby app.rb",
        notes_ar=f"Ruby {'on Rails' if is_rails else ''}.",
    )


# ─── Games ────────────────────────────────────────────────────────
def detect_unity(root: Path) -> Optional[StackInfo]:
    if (root / "Assets").is_dir() and (root / "ProjectSettings").is_dir():
        return StackInfo(
            id="unity", name="Unity", category="game", language="C#",
            package_manager="unity",
            build_command="Unity -batchmode -nographics -projectPath . -buildTarget Android -executeMethod BuildScript.Build",
            needs_native_sdk=["unity"],
            notes_ar="Unity — يتطلب Unity Hub + License محلياً للبناء.",
        )
    return None


def detect_unreal(root: Path) -> Optional[StackInfo]:
    if list(root.glob("*.uproject"))[:1]:
        return StackInfo(
            id="unreal", name="Unreal Engine", category="game", language="C++",
            needs_native_sdk=["unreal"],
            notes_ar="Unreal Engine — يتطلب UE Editor محلياً.",
        )
    return None


def detect_godot(root: Path) -> Optional[StackInfo]:
    if (root / "project.godot").is_file():
        return StackInfo(
            id="godot", name="Godot", category="game", language="GDScript",
            build_command="godot --headless --export-release Android out.apk",
            notes_ar="Godot — محرك ألعاب مفتوح المصدر.",
        )
    return None


# ─── CMS ──────────────────────────────────────────────────────────
def detect_wordpress(root: Path) -> Optional[StackInfo]:
    if (root / "wp-config.php").is_file() or (root / "wp-config-sample.php").is_file():
        return StackInfo(
            id="wordpress", name="WordPress", category="cms", language="PHP",
            install_command="composer install" if (root / "composer.json").is_file() else None,
            notes_ar="WordPress — تعديلات الـ themes/plugins فقط، الـ core ما يُلمس.",
        )
    return None


# ─── Master detector ──────────────────────────────────────────────
DETECTORS = [
    # Mobile / Cross-platform first (most specific)
    detect_flutter, detect_react_native, detect_capacitor, detect_ionic,
    detect_cordova, detect_nativescript, detect_xamarin_maui,
    # Native mobile
    detect_android_native, detect_ios_native,
    # Desktop
    detect_electron, detect_tauri,
    # Web frontend
    detect_nextjs, detect_vue_nuxt, detect_react,
    # Backend
    detect_nodejs_backend, detect_python, detect_go, detect_rust,
    detect_java_spring, detect_dotnet, detect_php_laravel, detect_ruby_rails,
    # Games
    detect_unity, detect_unreal, detect_godot,
    # CMS
    detect_wordpress,
]


def detect_stacks(sandbox_root: Path | str) -> List[StackInfo]:
    """Run every detector on the sandbox root + first-level subfolders.

    A monorepo like `myapp/{mobile/, backend/, web/}` will return 3 stacks.
    """
    root = Path(sandbox_root)
    if not root.exists() or not root.is_dir():
        return []
    candidates: List[Path] = [root]
    # Also probe immediate subdirs (cap at 8 to stay fast)
    for sub in list(root.iterdir())[:20]:
        if sub.is_dir() and not sub.name.startswith(".") and sub.name not in (
            "node_modules", "vendor", "__pycache__", "build", "dist", "target", ".gradle"
        ):
            candidates.append(sub)
            if len(candidates) >= 8:
                break

    results: List[StackInfo] = []
    seen_ids: set = set()
    for path in candidates:
        for det in DETECTORS:
            try:
                info = det(path)
            except Exception:
                info = None
            if info and info.id not in seen_ids:
                if path != root:
                    info.entry_files = [f"{path.name}/{p}" for p in info.entry_files] or [f"{path.name}/"]
                results.append(info)
                seen_ids.add(info.id)
    # Sort: mobile/desktop/game first, then web, then backend, then cms
    cat_order = {"mobile": 0, "hybrid": 0, "desktop": 1, "game": 1, "web": 2, "backend": 3, "cms": 4}
    results.sort(key=lambda s: cat_order.get(s.category, 9))
    return results


def summarize_stacks(stacks: List[StackInfo]) -> Dict[str, Any]:
    """High-level summary the AI engineer manager can include in its first
    diagnostic message to the customer."""
    if not stacks:
        return {"detected": False, "stacks": [], "message_ar": "ما لقيت ستاك معروف. اطلب من العميل وصف أكثر."}
    primary = stacks[0]
    needs_cloud = any(s.needs_cloud_build for s in stacks)
    needs_sdks = sorted({sdk for s in stacks for sdk in s.needs_native_sdk})
    return {
        "detected": True,
        "primary_stack": primary.to_dict(),
        "all_stacks": [s.to_dict() for s in stacks],
        "monorepo": len(stacks) > 1,
        "needs_cloud_build": needs_cloud,
        "needs_sdks": needs_sdks,
        "message_ar": (
            f"كشفت {len(stacks)} ستاك: "
            + "، ".join(s.name for s in stacks)
            + (". هذا monorepo." if len(stacks) > 1 else ".")
            + (" يحتاج cloud build (iOS)." if needs_cloud else "")
        ),
    }
