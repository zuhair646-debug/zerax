/**
 * Avatar3D v2 — Production-grade VRM renderer with real VRMA animations.
 *
 * Uses @pixiv/three-vrm + @pixiv/three-vrm-animation to play real
 * motion-capture animation files (.vrma) instead of manually rotating bones.
 *
 * Animation library auto-loaded from /public/animations/*.vrma :
 *   Idle / Wave (Goodbye) / Thinking / Clapping / Jump / LookAround /
 *   Relax / Surprised / Blush / Sad / Sleepy
 *
 * Cycles through idle variants every ~6-8 seconds for natural "alive" feel.
 */
import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three-stdlib';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import {
  VRMAnimationLoaderPlugin,
  createVRMAnimationClip,
} from '@pixiv/three-vrm-animation';

// Animation catalog — files must exist in /public/animations/
const ANIM_LIBRARY = {
  idle:       '/animations/Relax.vrma',        // calm standing baseline
  thinking:   '/animations/Thinking.vrma',
  wave:       '/animations/Goodbye.vrma',      // waving motion
  clap:       '/animations/Clapping.vrma',
  jump:       '/animations/Jump.vrma',
  look:       '/animations/LookAround.vrma',
  surprised:  '/animations/Surprised.vrma',
  blush:      '/animations/Blush.vrma',
  sad:        '/animations/Sad.vrma',
  sleepy:     '/animations/Sleepy.vrma',
  angry:      '/animations/Angry.vrma',
};

// Idle cycle — rotate through these when nothing specific is happening
const IDLE_CYCLE = ['idle', 'look', 'thinking', 'blush'];
// Fallback if one clip doesn't exist
const DEFAULT_ANIM = 'idle';

// Shared animation cache (avoid re-downloading per avatar)
const animationCache = new Map(); // url → gltf

async function loadVRMAGltf(url) {
  if (animationCache.has(url)) return animationCache.get(url);
  const loader = new GLTFLoader();
  loader.register((parser) => new VRMAnimationLoaderPlugin(parser));
  return new Promise((resolve, reject) => {
    loader.load(
      url,
      (gltf) => { animationCache.set(url, gltf); resolve(gltf); },
      undefined,
      (err) => reject(err),
    );
  });
}

export default function Avatar3D({
  url = '/avatars-3d/zara.vrm',
  talking = false,
  className = '',
  dataTestId,
  cameraPos = [0, 1.3, 2.5],
  fov = 30,
  sceneOffset = 0,
  action = null,
  onReady,
}) {
  const containerRef = useRef(null);
  const rendererRef = useRef(null);
  const vrmRef = useRef(null);
  const wrapperRef = useRef(null);
  const mixerRef = useRef(null);
  const currentActionRef = useRef(null);
  const animRef = useRef(null);
  const talkingRef = useRef(talking);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => { talkingRef.current = talking; }, [talking]);

  // Switch to a named animation (one-shot or looping)
  const playAnimation = async (name, { loop = true } = {}) => {
    const vrm = vrmRef.current;
    const mixer = mixerRef.current;
    if (!vrm || !mixer) return;
    const url = ANIM_LIBRARY[name] || ANIM_LIBRARY[DEFAULT_ANIM];
    if (!url) return;

    try {
      const gltf = await loadVRMAGltf(url);
      const vrmAnim = gltf.userData.vrmAnimations?.[0];
      if (!vrmAnim) return;
      const clip = createVRMAnimationClip(vrmAnim, vrm);
      const next = mixer.clipAction(clip);
      next.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
      next.clampWhenFinished = !loop;
      // Crossfade from previous
      const prev = currentActionRef.current;
      if (prev && prev !== next) {
        next.reset().fadeIn(0.5).play();
        prev.fadeOut(0.5);
      } else {
        next.play();
      }
      currentActionRef.current = next;
    } catch (e) {
      console.warn(`[Avatar3D] anim "${name}" load failed`, e);
    }
  };

  // React to `action` prop changes (trigger one-shot)
  useEffect(() => {
    if (!action || !loaded) return;
    playAnimation(action, { loop: false });
    // After the one-shot, fall back to idle cycle
    const t = setTimeout(() => {
      playAnimation(DEFAULT_ANIM, { loop: true });
    }, 4000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [action, loaded]);

  // Idle cycle when no action is firing
  useEffect(() => {
    if (!loaded || action) return;
    // Rotate through IDLE_CYCLE every 7 seconds
    let i = Math.floor(sceneOffset) % IDLE_CYCLE.length;
    playAnimation(IDLE_CYCLE[i] || DEFAULT_ANIM, { loop: true });
    const handle = setInterval(() => {
      i = (i + 1) % IDLE_CYCLE.length;
      playAnimation(IDLE_CYCLE[i] || DEFAULT_ANIM, { loop: true });
    }, 7000 + sceneOffset * 1000);
    return () => clearInterval(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, action, sceneOffset]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    const width = container.clientWidth || 300;
    const height = container.clientHeight || 400;

    const scene = new THREE.Scene();
    scene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const dir1 = new THREE.DirectionalLight(0xffffff, 1.1);
    dir1.position.set(2, 3, 2);
    scene.add(dir1);
    const dir2 = new THREE.DirectionalLight(0x9a7fff, 0.4);
    dir2.position.set(-2, 2, -1);
    scene.add(dir2);

    const camera = new THREE.PerspectiveCamera(fov, width / height, 0.1, 100);
    // Apply character offset: we move character into view
    camera.position.set(cameraPos[0], cameraPos[1], cameraPos[2]);
    camera.lookAt(0, cameraPos[1] - 0.2, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setSize(width, height);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));
    loader.load(
      url,
      (gltf) => {
        if (cancelled) return;
        const vrm = gltf.userData.vrm;
        if (!vrm) { setFailed(true); return; }
        VRMUtils.removeUnnecessaryVertices(gltf.scene);
        VRMUtils.combineSkeletons(gltf.scene);
        vrm.scene.traverse((obj) => {
          obj.frustumCulled = false;
          if (obj.isMesh && obj.material) {
            const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
            mats.forEach((m) => {
              // Force double-sided so thin geometry (eyelashes, hair) renders from any angle
              m.side = THREE.DoubleSide;
              // Ensure visible
              m.transparent = m.transparent || false;
              m.depthWrite = true;
              m.needsUpdate = true;
            });
          }
        });

        // Add VRM directly - we'll handle rotation via a post-update fix
        scene.add(vrm.scene);

        vrmRef.current = vrm;
        // Create animation mixer bound to the VRM scene
        mixerRef.current = new THREE.AnimationMixer(vrm.scene);

        setLoaded(true);
        if (onReady) onReady(vrm);
      },
      undefined,
      (err) => {
        console.warn('[Avatar3D] VRM load error', err);
        setFailed(true);
      },
    );

    const clock = new THREE.Clock();
    const tick = () => {
      if (cancelled) return;
      const delta = clock.getDelta();
      const t = clock.getElapsedTime();
      const vrm = vrmRef.current;
      const mixer = mixerRef.current;
      if (mixer) mixer.update(delta);
      if (vrm) {
        vrm.update(delta);
        // Keep character facing camera — counter any root rotation applied by animations
        const hips = vrm.humanoid?.getNormalizedBoneNode('hips');
        if (hips) {
          // Neutralize Y-rotation to prevent animation from turning character away
          hips.rotation.y = 0;
        }
        vrm.scene.rotation.y = 0;
        if (vrm.expressionManager) {
          // Blink every ~4s
          const blinkPhase = ((t + sceneOffset) % 4) / 4;
          const blinkVal = blinkPhase > 0.95 ? Math.sin((blinkPhase - 0.95) / 0.05 * Math.PI) : 0;
          vrm.expressionManager.setValue('blink', blinkVal);
          // Lip-sync when talking
          if (talkingRef.current) {
            const mouth = 0.3 + Math.abs(Math.sin(t * 12)) * 0.4;
            vrm.expressionManager.setValue('aa', mouth);
          } else {
            vrm.expressionManager.setValue('aa', 0);
          }
          vrm.expressionManager.update();
        }
      }
      renderer.render(scene, camera);
      animRef.current = requestAnimationFrame(tick);
    };
    tick();

    const onResize = () => {
      if (!container) return;
      const w = container.clientWidth || 300;
      const h = container.clientHeight || 400;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    const ro = new ResizeObserver(onResize);
    ro.observe(container);

    return () => {
      cancelled = true;
      if (animRef.current) cancelAnimationFrame(animRef.current);
      ro.disconnect();
      try { renderer.dispose(); } catch (_) {}
      try { container.removeChild(renderer.domElement); } catch (_) {}
      if (vrmRef.current) {
        try { VRMUtils.deepDispose(vrmRef.current.scene); } catch (_) {}
      }
      if (mixerRef.current) {
        try { mixerRef.current.stopAllAction(); } catch (_) {}
      }
      scene.clear();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  if (failed) {
    return (
      <div className={className} data-testid={dataTestId}>
        <div className="w-full h-full flex items-center justify-center text-white/50 text-xs">
          3D تحميل فشل
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={className}
      data-testid={dataTestId}
      data-loaded={loaded ? '1' : '0'}
      style={{ position: 'relative' }}
    />
  );
}
