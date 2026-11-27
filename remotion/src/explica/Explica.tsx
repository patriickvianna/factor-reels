// Reels explicativo 3D (GUT #112): cena 3D em tela cheia + legenda embaixo + rótulo da peça em foco.
// Legenda: padrão de rede social e YouTube (decisão do PTK), embaixo, dentro da área segura;
// a palavra dita fica destacada no instante em que é falada.
import React from "react";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, SAFE, SAFE_W, loadBrandFonts } from "../theme";
import type { Line, Word } from "../types";
import { AirFryer3D, ramp } from "./AirFryer3D";
import type { ExplicaProps } from "./types";

loadBrandFonts();

// tons naturais, sem a paleta da Factor
const N = { text: "#F2EDE4", dim: "rgba(242,237,228,.42)", hi: "#E6D2AC", hiText: "#1E1B17", chip: "rgba(24,22,19,.62)" };

const chunk = (words: Word[], max = 34): Word[][] => {
  const out: Word[][] = [];
  let cur: Word[] = [];
  let len = 0;
  for (const w of words) {
    if (cur.length && len + w.text.length + 1 > max) {
      out.push(cur);
      cur = [];
      len = 0;
    }
    cur.push(w);
    len += w.text.length + 1;
  }
  if (cur.length) out.push(cur);
  return out;
};

const Captions: React.FC<{ lines: Line[] }> = ({ lines }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const ln = lines.find((l) => t >= l.start - 0.05 && t < l.end + 0.3);
  if (!ln?.words?.length) return null;
  const blocks = chunk(ln.words);
  const block = blocks.find((b) => t < b[b.length - 1].end + 0.2) ?? blocks[blocks.length - 1];
  const appear = ramp(t, block[0].start - 0.08, 0.16);
  return (
    <div style={{ position: "absolute", left: SAFE.left, width: SAFE_W + 120, top: 1235, fontFamily: FONT, fontWeight: 700, fontSize: 58,
      lineHeight: 1.3, letterSpacing: "-0.01em", opacity: appear, textShadow: "0 2px 14px rgba(0,0,0,.55)" }}>
      {block.map((w, i) => {
        const now = t >= w.start && t < w.end + 0.04;
        const said = t >= w.start;
        return (
          <span key={i} style={{ color: now ? N.hiText : said ? N.text : N.dim, background: now ? N.hi : "transparent",
            borderRadius: 8, padding: "0 8px", marginLeft: -8, marginRight: 6, textShadow: now ? "none" : undefined }}>
            {w.text}
          </span>
        );
      })}
    </div>
  );
};

const LABELS: [string, string][] = [
  ["coil", "Resistência · até 200 °C"],
  ["fan", "Ventilador"],
  ["down", "Ar quente circulando"],
  ["holes", "Cesto furado"],
  ["brown", "Casca dourada"],
  ["crowd", "Cesto lotado"],
];

const Chip: React.FC<{ cues: Record<string, number> }> = ({ cues }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const active = [...LABELS].reverse().find(([k]) => t >= (cues[k] ?? 999) && t < (cues.end ?? 999));
  if (!active) return null;
  const k = ramp(t, cues[active[0]], 0.35);
  return (
    <div style={{ position: "absolute", left: SAFE.left, top: 270, fontFamily: FONT, fontWeight: 500, fontSize: 34, color: N.text,
      background: N.chip, padding: "10px 20px", borderRadius: 12, opacity: k, translate: `0 ${(1 - k) * 10}px` }}>
      {active[1]}
    </div>
  );
};

const Title: React.FC<{ titulo: string; cues: Record<string, number>; handle: string }> = ({ titulo, cues, handle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const out = ramp(t, (cues.corte ?? 3) - 0.2, 0.5);
  const inn = ramp(t, 0.05, 0.5);
  const end = ramp(t, cues.end ?? 999, 0.6);
  return (
    <>
      <div style={{ position: "absolute", left: SAFE.left, top: 270, width: SAFE_W, fontFamily: FONT, fontWeight: 700, fontSize: 76,
        lineHeight: 1.05, color: N.text, opacity: inn * (1 - out), textShadow: "0 2px 18px rgba(0,0,0,.5)" }}>
        {titulo.split(" a ").length === 2 ? <>{titulo.split(" a ")[0]}<br />a {titulo.split(" a ")[1]}</> : titulo}
      </div>
      <div style={{ position: "absolute", left: SAFE.left, top: 280, fontFamily: FONT, fontWeight: 500, fontSize: 40, color: N.text, opacity: end }}>
        {handle}
      </div>
    </>
  );
};

export const Explica: React.FC<ExplicaProps> = (p) => {
  const { width, height } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: "#1d1b18" }}>
      <ThreeCanvas width={width} height={height} camera={{ fov: 34, near: 0.1, far: 60 }}
        gl={{ antialias: true }} onCreated={({ gl }) => { gl.localClippingEnabled = true; }}>
        {p.tema === "airfryer" ? <AirFryer3D cues={p.cues} /> : null}
      </ThreeCanvas>
      {/* escurece de leve o pé da tela, para a legenda ler bem sobre qualquer fundo */}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0) 58%, rgba(0,0,0,.5) 72%, rgba(0,0,0,.5) 100%)" }} />
      <Title titulo={p.titulo} cues={p.cues} handle={p.handle} />
      <Chip cues={p.cues} />
      <Captions lines={p.lines} />
      {p.audio ? <Audio src={staticFile(p.audio)} /> : null}
    </AbsoluteFill>
  );
};
