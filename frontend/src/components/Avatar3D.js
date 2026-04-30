/**
 * Avatar3D — VRM 3D avatar renderer using PURE Three.js (no R3F).
 *
 * Why not @react-three/fiber? R3F v9 has React 19 compatibility issues,
 * and downgrading to v8 fails because React 19 removed internals R3F v8 used.
 * Pure three.js via useRef + useEffect is the most stable path.
 */
import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three-stdlib';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';

export default function Avatar3D({
  url = '/avatars-3d/sample1.vrm',
  tint = null,
  talking = false,
  className = '',
  dataTestId,
  cameraPos = [0, 1.25, 2.5],
  fov = 22,
  onReady,
  sceneOffset = 0,
}) {
  const containerRef = useRef(null);
  const rendererRef = useRef(null);
  const vrmRef = useRef(null);
  const animRef = useRef(null);
  const talkingRef = useRef(talking);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => { talkingRef.current = talking; }, [talking]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    const width = container.clientWidth || 300;
    const height = container.clientHeight || 400;

    // Scene
    const scene = new THREE.Scene();
    // Lighting
    scene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const dir1 = new THREE.DirectionalLight(0xffffff, 1.1);
    dir1.position.set(2, 3, 2);
    scene.add(dir1);
    const dir2 = new THREE.DirectionalLight(0x9a7fff, 0.4);
    dir2.position.set(-2, 2, -1);
    scene.add(dir2);

    // Camera — frame upper body close-up
    const camera = new THREE.PerspectiveCamera(fov, width / height, 0.1, 100);
    camera.position.set(cameraPos[0], cameraPos[1], cameraPos[2]);
    camera.lookAt(0, 1.3, 0);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setSize(width, height);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Load VRM
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
              if (tint && m.color) m.color.lerp(new THREE.Color(tint), 0.08);
            });
          }
        });
        vrm.scene.rotation.y = 0; // VRM1 sample already faces +Z
        vrm.scene.position.set(0, 0, 0);
        scene.add(vrm.scene);

        vrmRef.current = vrm;
        setLoaded(true);
        if (onReady) onReady(vrm);
      },
      undefined,
      (err) => {
        console.warn('[Avatar3D] VRM load error', err);
        setFailed(true);
      },
    );

    // Animate
    const clock = new THREE.Clock();
    const tick = () => {
      if (cancelled) return;
      const delta = clock.getDelta();
      const t = clock.getElapsedTime();
      const vrm = vrmRef.current;
      if (vrm) {
        vrm.update(delta);

        // ===== Animation cycling: pick a new "scene" every 5 seconds =====
        // Scenes: 0=idle breathe, 1=wave, 2=head_tilt_curious, 3=hand_on_hip,
        //         4=look_around, 5=stretch, 6=think_pose, 7=happy_bounce
        const SCENE_DURATION = 5; // seconds
        const tEff = t + sceneOffset;
        const sceneIdx = Math.floor(tEff / SCENE_DURATION) % 8;
        const localT = tEff % SCENE_DURATION;       // 0..5
        const phase = localT / SCENE_DURATION;       // 0..1

        // Always-on subtle breathing
        const chest = vrm.humanoid?.getNormalizedBoneNode('chest') || vrm.humanoid?.getNormalizedBoneNode('upperChest');
        if (chest) {
          const s = 1 + Math.sin(t * 1.5) * 0.015;
          chest.scale.set(s, s, s);
        }

        const head = vrm.humanoid?.getNormalizedBoneNode('head');
        const leftArm = vrm.humanoid?.getNormalizedBoneNode('leftUpperArm');
        const rightArm = vrm.humanoid?.getNormalizedBoneNode('rightUpperArm');
        const leftLowerArm = vrm.humanoid?.getNormalizedBoneNode('leftLowerArm');
        const rightLowerArm = vrm.humanoid?.getNormalizedBoneNode('rightLowerArm');
        const spine = vrm.humanoid?.getNormalizedBoneNode('spine');
        const hips = vrm.humanoid?.getNormalizedBoneNode('hips');

        // Default rest pose (arms down by sides)
        let lArmZ = -1.25;
        let rArmZ = 1.25;
        let lArmX = 0, rArmX = 0;
        let lArmY = 0, rArmY = 0;
        let lLowerY = 0, rLowerY = 0;
        let headX = Math.sin(t * 0.7) * 0.05;
        let headY = Math.sin(t * 0.5) * 0.08;
        let spineY = 0;
        let hipsY = 0;

        // Smooth easing
        const ease = (x) => 0.5 - Math.cos(x * Math.PI) * 0.5; // 0..1

        if (sceneIdx === 0) {
          // Idle breathing — default
        } else if (sceneIdx === 1) {
          // Wave with right hand: arm goes up, hand sways
          const w = ease(Math.min(phase * 2, 1)); // ramp up first half
          const down = phase > 0.85 ? (phase - 0.85) / 0.15 : 0;
          rArmZ = 1.25 + w * (-2.4) - down * (-2.4); // raise arm
          rArmX = w * 0.3 - down * 0.3;
          rLowerY = Math.sin(t * 6) * 0.4 * (1 - down); // hand sway
          headY = w * -0.3; // turn slightly toward arm
        } else if (sceneIdx === 2) {
          // Curious head tilt
          headX = Math.sin(phase * Math.PI) * 0.25;
          headY = Math.sin(phase * Math.PI * 2) * 0.3;
        } else if (sceneIdx === 3) {
          // Hand on hip (left arm bent up)
          const e = ease(Math.min(phase * 2, 1));
          const release = phase > 0.85 ? (phase - 0.85) / 0.15 : 0;
          lArmZ = -1.25 + e * (-0.6) + release * 0.6;
          lLowerY = e * (-1.2) + release * 1.2;
          spineY = e * 0.1 - release * 0.1;
        } else if (sceneIdx === 4) {
          // Look around (left then right)
          headY = Math.sin(phase * Math.PI * 2) * 0.55;
          spineY = Math.sin(phase * Math.PI * 2) * 0.1;
        } else if (sceneIdx === 5) {
          // Stretch arms slightly upward
          const e = ease(Math.min(phase * 1.5, 1));
          const release = phase > 0.7 ? (phase - 0.7) / 0.3 : 0;
          lArmZ = -1.25 - e * 0.7 + release * 0.7;
          rArmZ = 1.25 + e * 0.7 - release * 0.7;
          headX = -e * 0.1 + release * 0.1;
        } else if (sceneIdx === 6) {
          // Think pose — hand near chin
          const e = ease(Math.min(phase * 2, 1));
          const release = phase > 0.85 ? (phase - 0.85) / 0.15 : 0;
          rArmZ = 1.25 + e * (-1.0) + release * 1.0;
          rArmX = e * 0.4 - release * 0.4;
          rLowerY = e * (-1.4) + release * 1.4;
          headX = e * 0.15 - release * 0.15;
        } else if (sceneIdx === 7) {
          // Happy bounce
          const bounce = Math.abs(Math.sin(phase * Math.PI * 4)) * 0.05;
          if (hips) hips.position.y = bounce;
          headX = Math.sin(phase * Math.PI * 4) * 0.1;
          lArmZ = -1.25 + Math.sin(t * 4) * 0.15;
          rArmZ = 1.25 - Math.sin(t * 4) * 0.15;
        }

        if (head) { head.rotation.x = headX; head.rotation.y = headY; }
        if (leftArm) {
          leftArm.rotation.set(lArmX, lArmY, lArmZ + Math.sin(t * 0.9) * 0.02);
        }
        if (rightArm) {
          rightArm.rotation.set(rArmX, rArmY, rArmZ + Math.sin(t * 0.9 + 0.5) * 0.02);
        }
        if (leftLowerArm) leftLowerArm.rotation.y = lLowerY;
        if (rightLowerArm) rightLowerArm.rotation.y = rLowerY;
        if (spine) spine.rotation.y = spineY;
        if (hips && sceneIdx !== 7) hips.position.y = hipsY;

        if (vrm.expressionManager) {
          // Blink every ~4s
          const blinkPhase = (t % 4) / 4;
          const blinkVal = blinkPhase > 0.95 ? Math.sin((blinkPhase - 0.95) / 0.05 * Math.PI) : 0;
          vrm.expressionManager.setValue('blink', blinkVal);
          // Lip-sync when talking
          if (talkingRef.current) {
            const mouth = 0.3 + Math.abs(Math.sin(t * 12)) * 0.4;
            vrm.expressionManager.setValue('aa', mouth);
          } else {
            vrm.expressionManager.setValue('aa', 0);
          }
          // Smile in happy_bounce scene
          vrm.expressionManager.setValue('happy', sceneIdx === 7 ? 0.6 : 0);
          vrm.expressionManager.update();
        }
      }
      renderer.render(scene, camera);
      animRef.current = requestAnimationFrame(tick);
    };
    tick();

    // Resize observer
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
      scene.clear();
    };
  }, [url, tint, cameraPos, fov, onReady, sceneOffset]);

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
