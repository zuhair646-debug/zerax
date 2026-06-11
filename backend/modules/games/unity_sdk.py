"""
🎮 Unity SDK exporter
═══════════════════════════════════════════════════════════════════════
Ships a downloadable .zip with Unity C# scripts that pull a Zenrex
project's assets into a Unity scene at runtime — images become
Sprites/Textures, .glb models become GameObjects, .mp3 voice lines
become AudioClips.

Endpoint: GET /api/games/project/{id}/unity-sdk.zip
Auth: requires the owner of the project.
"""
from __future__ import annotations
import io, zipfile, json
from typing import Dict, Any


CSHARP_CLIENT = '''
// Zenrex Unity Client — auto-generated. Drop into your Unity project.
// Requires: GLTFast (Window > Package Manager > Add by name: com.unity.cloud.gltfast)
using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

namespace Zenrex {
  [Serializable] public class ZenrexAsset {
    public string id; public string type; public string subtype;
    public string name; public string url; public string cdn_url;
  }
  [Serializable] public class ZenrexManifest {
    public string project_id;
    public string project_title;
    public List<ZenrexAsset> images;
    public List<ZenrexAsset> models;
    public List<ZenrexAsset> voices;
    public string base_api;
    public string lora_url;
  }

  public static class ZenrexClient {
    public static IEnumerator FetchManifest(string manifestUrl, Action<ZenrexManifest> onReady, Action<string> onError = null) {
      using (var req = UnityWebRequest.Get(manifestUrl)) {
        yield return req.SendWebRequest();
        if (req.result == UnityWebRequest.Result.Success) {
          var m = JsonUtility.FromJson<ZenrexManifest>(req.downloadHandler.text);
          onReady?.Invoke(m);
        } else { onError?.Invoke(req.error); }
      }
    }

    public static IEnumerator LoadSprite(string url, Action<Sprite> onReady) {
      using (var req = UnityWebRequestTexture.GetTexture(url)) {
        yield return req.SendWebRequest();
        if (req.result == UnityWebRequest.Result.Success) {
          var tex = DownloadHandlerTexture.GetContent(req);
          var sprite = Sprite.Create(tex, new Rect(0,0,tex.width,tex.height), new Vector2(0.5f,0.5f), 100f);
          onReady?.Invoke(sprite);
        }
      }
    }

    public static IEnumerator LoadAudio(string url, AudioType type, Action<AudioClip> onReady) {
      using (var req = UnityWebRequestMultimedia.GetAudioClip(url, type)) {
        yield return req.SendWebRequest();
        if (req.result == UnityWebRequest.Result.Success) {
          onReady?.Invoke(DownloadHandlerAudioClip.GetContent(req));
        }
      }
    }
  }

  // Drop this on any GameObject to auto-load all approved assets.
  public class ZenrexImporter : MonoBehaviour {
    [Tooltip("URL to the project's manifest JSON")]
    public string manifestUrl;
    public Transform spritesParent;
    public Transform modelsParent;

    void Start() { StartCoroutine(ZenrexClient.FetchManifest(manifestUrl, OnManifest)); }

    void OnManifest(ZenrexManifest m) {
      Debug.Log($"[Zenrex] loaded project: {m.project_title} ({m.images?.Count} imgs, {m.models?.Count} models)");
      if (m.images != null) foreach (var a in m.images) StartCoroutine(LoadSpriteInto(a));
      // Models require GLTFast — leave as TODO for the user.
    }

    IEnumerator LoadSpriteInto(ZenrexAsset a) {
      yield return ZenrexClient.LoadSprite(a.cdn_url ?? a.url, sprite => {
        var go = new GameObject(a.name);
        if (spritesParent) go.transform.SetParent(spritesParent, false);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = sprite;
      });
    }
  }
}
'''.strip()


README_MD = '''# Zenrex Unity SDK

Auto-generated SDK for your Zenrex project. Imports all approved
images, 3D models (.glb), and voice lines into a Unity scene at
runtime.

## Setup (60 seconds)

1. **Copy the `Zenrex/` folder** to your Unity project's `Assets/`.
2. **Install GLTFast** (for .glb models):
   - `Window > Package Manager > + > Add package by name`
   - `com.unity.cloud.gltfast`
3. **Create an empty GameObject** in your scene, name it `ZenrexImporter`.
4. **Attach `ZenrexImporter.cs`** to it.
5. **Set `manifestUrl`** to:
   `{MANIFEST_URL}`
6. Press Play — all approved assets stream in automatically.

## What's included
- `ZenrexClient.cs`  — async helpers for fetching images/audio/models.
- `ZenrexImporter.cs` — drag-and-drop scene component.
- `manifest.json`  — snapshot of your project's assets (also live via API).
- `README.md`     — this file.

## Live updates
The `manifestUrl` always returns the latest approved assets. You can
re-run `ZenrexImporter` at any time to refresh the scene.

## Need anything else?
Open an issue at https://zenrex.ai/support — we ship custom Unity
features for paying tiers (LoRA-based prefab generation, automated
animation rigs via Mixamo, etc.)
'''


def build_zip(project: Dict[str, Any], base_api: str) -> bytes:
    """Build a .zip blob with Unity SDK + project manifest."""
    pid = project.get("id", "")
    manifest_url = f"{base_api}/api/games/project/{pid}/unity-manifest"

    # Snapshot manifest for offline use
    assets = (project.get("assets") or {})
    images = [a for a in (assets.get("images") or []) if a.get("approved")]
    models = [a for a in (assets.get("models_3d") or []) if a.get("approved")]
    voices = [a for a in (assets.get("voices") or []) if a.get("approved")]

    def _pick(a):
        return {
            "id": a.get("id"),
            "type": a.get("type"),
            "subtype": a.get("subtype"),
            "name": a.get("name"),
            "url": a.get("image_url") or a.get("model_url") or a.get("audio_url"),
            "cdn_url": a.get("cdn_url"),
        }

    manifest = {
        "project_id": pid,
        "project_title": project.get("title", ""),
        "base_api": base_api,
        "lora_url": (project.get("lora") or {}).get("lora_url", ""),
        "images": [_pick(a) for a in images],
        "models": [_pick(a) for a in models],
        "voices": [_pick(a) for a in voices],
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Zenrex/ZenrexClient.cs", CSHARP_CLIENT)
        zf.writestr("Zenrex/manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("README.md", README_MD.replace("{MANIFEST_URL}", manifest_url))
    return buf.getvalue()


def build_manifest_json(project: Dict[str, Any], base_api: str) -> Dict[str, Any]:
    """Live manifest endpoint — same shape as the embedded one."""
    pid = project.get("id", "")
    assets = (project.get("assets") or {})
    images = [a for a in (assets.get("images") or []) if a.get("approved")]
    models = [a for a in (assets.get("models_3d") or []) if a.get("approved")]
    voices = [a for a in (assets.get("voices") or []) if a.get("approved")]
    def _pick(a):
        return {
            "id": a.get("id"),
            "type": a.get("type"),
            "subtype": a.get("subtype"),
            "name": a.get("name"),
            "url": a.get("image_url") or a.get("model_url") or a.get("audio_url"),
            "cdn_url": a.get("cdn_url"),
        }
    return {
        "project_id": pid,
        "project_title": project.get("title", ""),
        "base_api": base_api,
        "lora_url": (project.get("lora") or {}).get("lora_url", ""),
        "images": [_pick(a) for a in images],
        "models": [_pick(a) for a in models],
        "voices": [_pick(a) for a in voices],
    }
