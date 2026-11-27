// Cena 3D "Como funciona a air fryer" (GUT #112). Tudo é desenhado em código (sem modelo baixado):
// corpo, gaveta, cesto furado, batatas, resistência em espiral, ventilador e o ar quente circulando.
// Tons naturais (plástico preto fosco, inox, batata) e luz suave, sem a paleta da Factor.
// Cada movimento começa no instante da palavra que o dispara (props.cues).
import React, { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";

// ---------- tempo ----------
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const ease = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
export const ramp = (t: number, at: number, dur = 0.7) => ease(clamp01((t - at) / dur));
const mix = (a: number, b: number, k: number) => a + (b - a) * k;

// gerador fixo: o mesmo vídeo sai igual em qualquer máquina (render em partes)
const rng = (seed: number) => () => {
  seed = (seed * 1664525 + 1013904223) % 4294967296;
  return seed / 4294967296;
};

// ---------- medidas (1 unidade ≈ 15 cm) ----------
const BODY_R = 1.08;
const BODY_H = 2.3;
const POT_R = 0.86;
const POT_Y0 = 0.16;
const POT_Y1 = 1.32;
const BASKET_R = 0.68;
const BASKET_Y0 = 0.32;
const BASKET_Y1 = 1.24;
const COIL_Y = 1.56;
const FAN_Y = 1.86;
const GAP_R = (BASKET_R + POT_R) / 2;

// ---------- texturas feitas em canvas ----------
function holesTexture(cols: number, rows: number) {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 512;
  const g = c.getContext("2d")!;
  g.fillStyle = "#fff";
  g.fillRect(0, 0, 512, 512);
  g.fillStyle = "#000";
  const dx = 512 / cols;
  const dy = 512 / rows;
  for (let y = 0; y < rows; y++)
    for (let x = 0; x < cols; x++) {
      g.beginPath();
      g.arc((x + 0.5 + (y % 2) * 0.5) * dx, (y + 0.5) * dy, Math.min(dx, dy) * 0.28, 0, Math.PI * 2);
      g.fill();
    }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

function shadowTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const g = c.getContext("2d")!;
  const grd = g.createRadialGradient(128, 128, 10, 128, 128, 128);
  grd.addColorStop(0, "rgba(0,0,0,0.55)");
  grd.addColorStop(0.6, "rgba(0,0,0,0.25)");
  grd.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = grd;
  g.fillRect(0, 0, 256, 256);
  return new THREE.CanvasTexture(c);
}

// ---------- caminho do ar (u de 0 a 1 = uma volta) ----------
// 0–0,14: sai do ventilador para a borda · 0,14–0,44: desce pela lateral · 0,44–0,58: corre no fundo para o centro
// 0,58–0,9: sobe por dentro do cesto, girando · 0,9–1: volta ao ventilador
export const AIR = { push: 0.14, down: 0.44, bottom: 0.58, up: 0.9 };
function airPoint(u: number, ang: number, swirl: number, out: THREE.Vector3) {
  let r: number;
  let y: number;
  let a = ang;
  if (u < AIR.push) {
    const k = u / AIR.push;
    r = mix(0.15, GAP_R, k);
    y = mix(FAN_Y - 0.12, COIL_Y - 0.05, k);
  } else if (u < AIR.down) {
    const k = (u - AIR.push) / (AIR.down - AIR.push);
    r = GAP_R;
    y = mix(COIL_Y - 0.05, POT_Y0 + 0.08, k);
  } else if (u < AIR.bottom) {
    const k = (u - AIR.down) / (AIR.bottom - AIR.down);
    r = mix(GAP_R, 0.22, k);
    y = POT_Y0 + 0.08 + Math.sin(k * Math.PI) * 0.03;
  } else if (u < AIR.up) {
    const k = (u - AIR.bottom) / (AIR.up - AIR.bottom);
    r = 0.22 + Math.sin(k * Math.PI) * 0.28;
    y = mix(POT_Y0 + 0.1, BASKET_Y1 + 0.18, k);
    a += k * 2.4 * swirl;
  } else {
    const k = (u - AIR.up) / (1 - AIR.up);
    r = mix(0.22, 0.12, k);
    y = mix(BASKET_Y1 + 0.18, FAN_Y - 0.12, k);
    a += 2.4 * swirl;
  }
  out.set(Math.cos(a) * r, y, Math.sin(a) * r);
  return out;
}

// ---------- câmera ----------
type Cam = { az: number; el: number; dist: number; ty: number };
function cameraAt(t: number, cue: (k: string) => number): Cam {
  // pontos de vista, na ordem em que a fala chega neles
  const shots: [string, Cam][] = [
    ["corte", { az: 0.22, el: 0.2, dist: 7.6, ty: 1.15 }],
    ["coil", { az: 0.12, el: 0.62, dist: 6.0, ty: 1.4 }],
    ["fan", { az: -0.1, el: 0.48, dist: 6.0, ty: 1.5 }],
    ["down", { az: -0.28, el: 0.2, dist: 7.2, ty: 1.1 }],
    ["holes", { az: -0.05, el: 0.4, dist: 6.3, ty: 0.85 }],
    ["brown", { az: 0.15, el: 0.66, dist: 5.6, ty: 0.7 }],
    ["crowd", { az: 0.3, el: 0.34, dist: 6.2, ty: 0.95 }],
    ["end", { az: 0.62, el: 0.18, dist: 8.4, ty: 1.15 }],
  ];
  let c: Cam = { az: 0.75, el: 0.16, dist: 8.6, ty: 1.15 };
  for (const [k, s] of shots) {
    const p = ramp(t, cue(k) - 0.15, 1.3);
    c = { az: mix(c.az, s.az, p), el: mix(c.el, s.el, p), dist: mix(c.dist, s.dist, p), ty: mix(c.ty, s.ty, p) };
  }
  // respiração lenta, para a imagem nunca ficar parada
  c.az += Math.sin(t * 0.35) * 0.05;
  c.el += Math.sin(t * 0.27 + 1) * 0.015;
  return c;
}

const CameraRig: React.FC<{ cam: Cam }> = ({ cam }) => {
  const { camera } = useThree();
  const x = Math.sin(cam.az) * Math.cos(cam.el) * cam.dist;
  const z = Math.cos(cam.az) * Math.cos(cam.el) * cam.dist;
  const y = cam.ty + Math.sin(cam.el) * cam.dist;
  camera.position.set(x, y, z);
  // olha um pouco abaixo do centro: a air fryer sobe na tela e o terço de baixo fica livre para a legenda
  camera.lookAt(0, cam.ty - cam.dist * 0.055, 0);
  camera.updateProjectionMatrix();
  return null;
};

// ---------- cena ----------
export const AirFryer3D: React.FC<{ cues: Record<string, number> }> = ({ cues }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const cue = (k: string) => cues[k] ?? 999;

  // corte: tira a metade da frente para mostrar o lado de dentro
  const cut = ramp(t, cue("corte"), 1.2);
  const plane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, 0, -1), 3), []);
  plane.constant = mix(3, 0.0, cut);
  const clip = useMemo(() => [plane], [plane]);

  const heat = ramp(t, cue("coil"), 0.9) * (0.55 + 0.45 * ramp(t, cue("hot"), 0.8));
  const fanOn = ramp(t, cue("fan"), 0.8);
  const blocked = ramp(t, cue("block"), 0.8);
  const brown = ramp(t, cue("brown"), 2.2);
  const soggy = ramp(t, cue("soggy"), 1.0);
  const holesGlow = ramp(t, cue("holes"), 0.6) * (1 - ramp(t, cue("holes") + 2.4, 0.8));

  // quanto do caminho do ar já aparece
  const reveal = Math.max(
    mix(0, AIR.push, ramp(t, cue("push"), 0.9)),
    mix(AIR.push, AIR.down, ramp(t, cue("down"), 1.2)),
    mix(AIR.down, AIR.bottom, ramp(t, cue("bottom"), 0.8)),
    mix(AIR.bottom, 1, ramp(t, cue("up"), 1.2)),
    ramp(t, cue("hook_air"), 0.5) * (1 - ramp(t, cue("hook_air") + 2.0, 0.6)) * 1.0,
  );
  const airOpacity = reveal > 0 ? 1 : 0;
  // no gancho o ar aparece um instante, antes de o ventilador "ligar" na explicação
  const hookFlash = ramp(t, cue("hook_air"), 0.5) * (1 - ramp(t, cue("hook_air") + 2.0, 0.6));
  const airVis = Math.max(fanOn, hookFlash);

  const tex = useMemo(() => {
    const wall = holesTexture(28, 14);
    wall.repeat.set(3, 2);
    const floor = holesTexture(16, 16);
    return { wall, floor, shadow: shadowTexture() };
  }, []);

  // giro do ventilador: ângulo acumulado (integral da velocidade), igual em qualquer pedaço do render
  const fanSpeed = (s: number) => 18 * ramp(s, cue("fan"), 0.8) * (1 - 0.65 * ramp(s, cue("block"), 0.8));
  let fanAngle = 0;
  for (let f = 0; f <= frame; f++) fanAngle += fanSpeed(f / fps) / fps;

  // ar: posição de cada partícula pela "distância percorrida" (também integral da velocidade)
  const airSpeed = (s: number) => 0.24 * (1 - 0.6 * ramp(s, cue("block"), 0.8));
  let travel = 0;
  for (let f = 0; f <= frame; f++) travel += airSpeed(f / fps) / fps;

  const N = 300;
  const parts = useMemo(() => {
    const r = rng(7);
    return Array.from({ length: N }, () => ({ ang: r() * Math.PI * 2, phase: r(), size: 0.011 + r() * 0.012, swirl: 0.6 + r() * 0.8 }));
  }, []);
  const tmp = useMemo(() => new THREE.Vector3(), []);

  // batatas (as do cesto cheio entram em "lote")
  const fries = useMemo(() => {
    const r = rng(42);
    const make = (n: number, yMax: number) =>
      Array.from({ length: n }, () => {
        const a = r() * Math.PI * 2;
        const rad = Math.sqrt(r()) * (BASKET_R - 0.12);
        return {
          p: [Math.cos(a) * rad, BASKET_Y0 + 0.06 + r() * yMax, Math.sin(a) * rad] as [number, number, number],
          rot: [r() * Math.PI, r() * Math.PI, (r() - 0.5) * 1.2] as [number, number, number],
          len: 0.34 + r() * 0.16,
        };
      });
    return { base: make(34, 0.32), extra: make(90, 0.78) };
  }, []);
  const raw = new THREE.Color("#E6D5A2");
  const golden = new THREE.Color("#A47546");
  const pale = new THREE.Color("#D9C58E");
  const friesColor = raw.clone().lerp(golden, brown);
  const extraColor = raw.clone().lerp(pale, soggy);
  const baseColorCrowded = friesColor.clone().lerp(pale, soggy * 0.8);

  const coilCurve = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= 240; i++) {
      const k = i / 240;
      const a = k * Math.PI * 2 * 3.5;
      const rr = 0.14 + k * 0.52;
      pts.push(new THREE.Vector3(Math.cos(a) * rr, COIL_Y, Math.sin(a) * rr));
    }
    return new THREE.CatmullRomCurve3(pts);
  }, []);

  const bodyProfile = useMemo(() => {
    const pts: THREE.Vector2[] = [];
    const R = BODY_R;
    pts.push(new THREE.Vector2(0, 0));
    pts.push(new THREE.Vector2(R - 0.12, 0));
    for (let i = 0; i <= 6; i++) {
      const a = -Math.PI / 2 + (i / 6) * (Math.PI / 2);
      pts.push(new THREE.Vector2(R - 0.12 + Math.cos(a) * 0.12, 0.12 + Math.sin(a) * 0.12));
    }
    pts.push(new THREE.Vector2(R + 0.02, BODY_H * 0.55));
    pts.push(new THREE.Vector2(R - 0.04, BODY_H - 0.22));
    for (let i = 0; i <= 8; i++) {
      const a = (i / 8) * (Math.PI / 2);
      pts.push(new THREE.Vector2(R - 0.3 + Math.cos(a) * 0.26, BODY_H - 0.22 + Math.sin(a) * 0.22));
    }
    pts.push(new THREE.Vector2(0, BODY_H));
    return pts;
  }, []);

  const cam = cameraAt(t, cue);
  const coilColor = new THREE.Color("#5a5752").lerp(new THREE.Color("#d9773f"), heat);
  const coilEmissive = new THREE.Color("#c4501c").multiplyScalar(heat * 1.15);

  return (
    <>
      <CameraRig cam={cam} />
      <color attach="background" args={["#23201c"]} />
      {/* luz de contorno por trás: separa a air fryer preta do fundo escuro */}
      <directionalLight position={[-2, 4, -6]} intensity={1.3} color="#dfe6ee" />
      <hemisphereLight args={["#f4efe6", "#2a2622", 0.9]} />
      <directionalLight position={[4, 6, 5]} intensity={1.6} color="#fff4e6" />
      <directionalLight position={[-5, 3, -2]} intensity={0.55} color="#c9d6e6" />
      <pointLight position={[0, COIL_Y - 0.1, 0]} intensity={heat * 2.2} distance={2.2} decay={2} color="#ff8a3d" />

      {/* sombra no balcão */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.012, 0]}>
        <planeGeometry args={[4.4, 4.4]} />
        <meshBasicMaterial map={tex.shadow} transparent depthWrite={false} />
      </mesh>
      {/* balcão */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <circleGeometry args={[9, 64]} />
        <meshStandardMaterial color="#4a443c" roughness={0.85} />
      </mesh>

      {/* corpo: preto fosco por fora, cinza claro no corte */}
      <mesh>
        <latheGeometry args={[bodyProfile, 96]} />
        <meshStandardMaterial color="#2c2a27" roughness={0.5} metalness={0.05} clippingPlanes={clip} side={THREE.FrontSide} />
      </mesh>
      <mesh>
        <latheGeometry args={[bodyProfile, 96]} />
        <meshStandardMaterial color="#6f6a62" roughness={0.8} clippingPlanes={clip} side={THREE.BackSide} />
      </mesh>
      {/* painel do topo */}
      <mesh position={[0, BODY_H - 0.005, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.55, 64]} />
        <meshStandardMaterial color="#1a1917" roughness={0.25} clippingPlanes={clip} />
      </mesh>
      {/* emenda entre a cabeça e a gaveta */}
      <mesh position={[0, 1.42, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[BODY_R + 0.015, 0.012, 8, 128]} />
        <meshStandardMaterial color="#121110" roughness={0.6} clippingPlanes={clip} />
      </mesh>
      {/* frente da gaveta e alça (somem no corte) */}
      <mesh position={[0, 0.78, BODY_R - 0.02]} >
        <boxGeometry args={[1.1, 1.0, 0.06]} />
        <meshStandardMaterial color="#252321" roughness={0.45} clippingPlanes={clip} />
      </mesh>
      <mesh position={[0, 0.72, BODY_R + 0.16]}>
        <boxGeometry args={[0.34, 0.5, 0.22]} />
        <meshStandardMaterial color="#1c1b19" roughness={0.4} clippingPlanes={clip} />
      </mesh>

      {/* gaveta (panela de inox escuro) */}
      <mesh position={[0, (POT_Y0 + POT_Y1) / 2, 0]}>
        <cylinderGeometry args={[POT_R, POT_R - 0.02, POT_Y1 - POT_Y0, 96, 1, true]} />
        <meshStandardMaterial color="#4a4845" metalness={0.55} roughness={0.42} side={THREE.DoubleSide} clippingPlanes={clip} />
      </mesh>
      <mesh position={[0, POT_Y0, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[POT_R - 0.02, 96]} />
        <meshStandardMaterial color="#3e3c39" metalness={0.5} roughness={0.5} side={THREE.DoubleSide} clippingPlanes={clip} />
      </mesh>

      {/* cesto furado */}
      <mesh position={[0, (BASKET_Y0 + BASKET_Y1) / 2, 0]}>
        <cylinderGeometry args={[BASKET_R, BASKET_R - 0.03, BASKET_Y1 - BASKET_Y0, 96, 1, true]} />
        <meshStandardMaterial
          color={new THREE.Color("#9a9893").lerp(new THREE.Color("#e8c48a"), holesGlow * 0.6)}
          metalness={0.7} roughness={0.32} alphaMap={tex.wall} alphaTest={0.5} transparent side={THREE.DoubleSide} clippingPlanes={clip}
        />
      </mesh>
      <mesh position={[0, BASKET_Y0, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[BASKET_R - 0.03, 96]} />
        <meshStandardMaterial color="#8f8d88" metalness={0.7} roughness={0.35} alphaMap={tex.floor} alphaTest={0.5} transparent side={THREE.DoubleSide} />
      </mesh>
      {/* aro do cesto */}
      <mesh position={[0, BASKET_Y1, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[BASKET_R, 0.022, 12, 96]} />
        <meshStandardMaterial color="#b3b1ab" metalness={0.8} roughness={0.25} clippingPlanes={clip} />
      </mesh>

      {/* batatas */}
      {fries.base.map((f, i) => (
        <mesh key={`b${i}`} position={f.p} rotation={f.rot}>
          <boxGeometry args={[0.075, f.len, 0.075]} />
          <meshStandardMaterial color={baseColorCrowded} roughness={0.75} />
        </mesh>
      ))}
      {fries.extra.map((f, i) => {
        const k = ramp(t, cue("crowd") + i * 0.012, 0.35);
        if (k <= 0) return null;
        return (
          <mesh key={`e${i}`} position={[f.p[0], f.p[1] + (1 - k) * 1.2, f.p[2]]} rotation={f.rot} scale={k}>
            <boxGeometry args={[0.075, f.len, 0.075]} />
            <meshStandardMaterial color={extraColor} roughness={0.75} />
          </mesh>
        );
      })}

      {/* resistência */}
      <mesh>
        <tubeGeometry args={[coilCurve, 400, 0.026, 10, false]} />
        <meshStandardMaterial color={coilColor} emissive={coilEmissive} roughness={0.4} metalness={0.6} />
      </mesh>

      {/* ventilador */}
      <group position={[0, FAN_Y, 0]} rotation={[0, fanAngle, 0]}>
        <mesh>
          <cylinderGeometry args={[0.12, 0.12, 0.1, 32]} />
          <meshStandardMaterial color="#8d8a84" metalness={0.7} roughness={0.3} />
        </mesh>
        {Array.from({ length: 7 }, (_, i) => (
          <group key={i} rotation={[0, (i / 7) * Math.PI * 2, 0]}>
            <mesh position={[0.38, 0, 0]} rotation={[0.45, 0, 0]}>
              <boxGeometry args={[0.52, 0.012, 0.16]} />
              <meshStandardMaterial color="#a19e97" metalness={0.75} roughness={0.28} />
            </mesh>
          </group>
        ))}
      </group>
      {/* tampa interna sobre o ventilador */}
      <mesh position={[0, FAN_Y + 0.14, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <circleGeometry args={[BODY_R - 0.12, 96]} />
        <meshStandardMaterial color="#57534d" roughness={0.7} side={THREE.DoubleSide} clippingPlanes={clip} />
      </mesh>

      {/* ar quente */}
      {airOpacity > 0 &&
        parts.map((p, i) => {
          const u = (p.phase + travel) % 1;
          if (u > reveal) return null;
          // as que entram no cesto cheio ficam presas e somem
          let o = 0.62;
          if (u > AIR.bottom) o *= 1 - 0.8 * blocked;
          const edge = clamp01((reveal - u) / 0.05);
          airPoint(u, p.ang + t * 0.15, p.swirl, tmp);
          // quente perto da resistência, mais claro no caminho
          const warm = new THREE.Color("#ffb066").lerp(new THREE.Color("#f3dcc0"), clamp01((u - AIR.push) / 0.6));
          return (
            <mesh key={i} position={[tmp.x, tmp.y, tmp.z]}>
              <sphereGeometry args={[p.size, 8, 8]} />
              <meshBasicMaterial color={warm} transparent opacity={o * edge * airVis} depthWrite={false} />
            </mesh>
          );
        })}
    </>
  );
};
