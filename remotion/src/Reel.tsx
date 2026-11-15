// O Reels inteiro: fundo animado, marca, cenas na hora de cada fala, legenda e o áudio já mixado.
import React from "react";
import { AbsoluteFill, Audio, Easing, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { SceneView } from "./scenes";
import { C, FONT, loadBrandFonts, SAFE, SAFE_W } from "./theme";
import type { CaptionPage, ReelProps, Scene } from "./types";

loadBrandFonts();
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(120% 80% at 50% 0%, #1B3560 0%, ${C.navy} 60%, #0A1528 100%)` }}>
      <div style={{ position: "absolute", width: 820, height: 820, borderRadius: 999, background: C.orange, opacity: 0.26, filter: "blur(110px)", left: -220 + Math.sin(t * 0.35) * 170, top: -160 + Math.cos(t * 0.28) * 130 }} />
      <div style={{ position: "absolute", width: 660, height: 660, borderRadius: 999, background: "#3D6FD1", opacity: 0.22, filter: "blur(110px)", left: 520 + Math.cos(t * 0.3) * 150, top: 1180 + Math.sin(t * 0.33) * 150 }} />
      <AbsoluteFill style={{ backgroundImage: "radial-gradient(rgba(255,255,255,.07) 2px, transparent 2px)", backgroundSize: "54px 54px", backgroundPosition: `0 ${-(t * 12) % 54}px` }} />
    </AbsoluteFill>
  );
};

const Brand: React.FC = () => (
  <div style={{ position: "absolute", left: SAFE.left, top: 196, display: "flex", alignItems: "center", gap: 14, fontWeight: 700, fontSize: 28, letterSpacing: "0.14em", color: C.peach }}>
    <svg width="46" height="46" viewBox="0 0 1080 1080"><circle cx="540" cy="540" r="500" fill="#FFE1CC" /><g transform="translate(540 540) rotate(-12) translate(-320 -210)"><path d="M190 50 H560 V370 H190 L60 210 Z" fill="#F05A1A" stroke="#F05A1A" strokeWidth="60" strokeLinejoin="round" /><circle cx="156" cy="210" r="30" fill="#FFE1CC" /><path d="M330 120 H470 V170 H385 V200 H455 V248 H385 V310 H330 Z" fill="#FFFFFF" /></g></svg>
    FACTOR OFERTAS
  </div>
);

/** Legenda: uma linha por vez, palavra da vez em destaque; preço e "R$" nunca se separam. */
const Captions: React.FC<{ pages: CaptionPage[] }> = ({ pages }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const page = pages.find((p) => t >= p.start - 0.02 && t < p.end);
  if (!page) return null;
  const pop = interpolate(t, [page.start, page.start + 0.16], [0, 1], { ...clamp, easing: Easing.bezier(0.34, 1.56, 0.64, 1) });
  return (
    <div style={{ position: "absolute", left: SAFE.left - 20, width: SAFE_W + 40, top: SAFE.bottom - 170, height: 150, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ whiteSpace: "nowrap", fontSize: 62, fontWeight: 700, letterSpacing: "-0.01em", color: C.white, textShadow: "0 4px 0 rgba(0,0,0,.55), 0 0 26px rgba(0,0,0,.55)", scale: String(0.9 + 0.1 * pop), opacity: Math.min(1, pop * 1.5) }}>
        {page.words.map((w, i) => {
          const on = t >= w.start && t < w.end;
          const done = t >= w.end;
          return (
            <span key={i} style={{ display: "inline-block", padding: "0 10px", margin: "0 2px", borderRadius: 14, background: on ? C.orange : "transparent", color: on || done ? C.white : "rgba(255,255,255,.62)" }}>
              {w.text}
            </span>
          );
        })}
      </div>
    </div>
  );
};

const SceneShell: React.FC<{ scene: Scene; last: boolean }> = ({ scene, last }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = Math.round((scene.end - scene.start) * fps);
  const inP = interpolate(frame, [0, 9], [0, 1], { ...clamp, easing: Easing.bezier(0.16, 1, 0.3, 1) });
  const outP = last ? 0 : interpolate(frame, [dur - 7, dur], [0, 1], { ...clamp, easing: Easing.in(Easing.cubic) });
  return (
    <AbsoluteFill style={{ opacity: Math.min(inP, 1 - outP), translate: `0 ${(1 - inP) * 60 - outP * 40}px`, scale: String(1 - outP * 0.04) }}>
      <SceneView scene={scene} />
    </AbsoluteFill>
  );
};

export const Reel: React.FC<ReelProps> = ({ scenes, pages, audio }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ fontFamily: `${FONT}, sans-serif`, color: C.white, background: C.navy }}>
      <Background />
      <Brand />
      {scenes.map((s, i) => {
        const from = Math.round(s.start * fps);
        const to = Math.round(s.end * fps);
        return (
          <Sequence key={i} from={from} durationInFrames={Math.max(1, to - from)} layout="none">
            <SceneShell scene={s} last={i === scenes.length - 1} />
          </Sequence>
        );
      })}
      <Captions pages={pages} />
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};
