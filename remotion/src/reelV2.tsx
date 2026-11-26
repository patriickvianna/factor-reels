// Modelo v2 dos Reels (26/11/2026, GUT #96). Regras do IA Reels Maker adaptadas às cenas feitas em código:
// - legenda em FAIXA: a frase inteira alinhada à esquerda; a palavra dita ganha a faixa pêssego, as próximas ficam apagadas;
//   sem contorno, sem sombra, sem brilho;
// - movimento calmo: entrada suave (14 quadros, desaceleração), saída rápida (9 quadros); sem desfoque, zoom ou tranco;
// - barra de progresso fina no alto (segura a atenção até o fim);
// - fundo limpo (sem manchas de luz) e marca em caixa-alta espaçada.
import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { SceneView } from "./scenes";
import { OWN_CAPTION } from "./story";
import { C, SAFE, SAFE_W } from "./theme";
import type { Line, Scene, Word } from "./types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const OUT = Easing.out(Easing.cubic);

export const BackgroundV2: React.FC = () => (
  <AbsoluteFill style={{ background: `linear-gradient(180deg, #142A4C 0%, ${C.navy} 45%, #0B172B 100%)` }}>
    <AbsoluteFill style={{ backgroundImage: "radial-gradient(rgba(255,255,255,.045) 2px, transparent 2px)", backgroundSize: "48px 48px" }} />
  </AbsoluteFill>
);

export const BrandV2: React.FC = () => (
  <div style={{ position: "absolute", left: SAFE.left, top: 190, display: "flex", alignItems: "center", gap: 16 }}>
    <span style={{ width: 8, height: 34, borderRadius: 4, background: C.orange }} />
    <span style={{ fontWeight: 700, fontSize: 26, letterSpacing: "0.2em", color: C.peach }}>FACTOR OFERTAS</span>
  </div>
);

export const ProgressV2: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = Math.min(1, frame / Math.max(1, durationInFrames - 1));
  return (
    <div style={{ position: "absolute", left: SAFE.left, top: 248, width: SAFE_W, height: 6, borderRadius: 3, background: "rgba(255,255,255,.14)" }}>
      <div style={{ width: `${p * 100}%`, height: "100%", borderRadius: 3, background: C.orange }} />
    </div>
  );
};

/** Divide as palavras de uma fala em blocos de até ~2 linhas (cerca de 48 caracteres). */
const chunk = (words: Word[], max = 48): Word[][] => {
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

/** Sem as palavras ouvidas, distribui o tempo da fala entre as palavras do texto. */
const wordsOf = (ln: Line): Word[] => {
  if (ln.words?.length) return ln.words;
  const parts = ln.text.split(/\s+/).filter(Boolean);
  const step = (ln.end - ln.start) / Math.max(1, parts.length);
  return parts.map((text, i) => ({ text, start: ln.start + i * step, end: ln.start + (i + 1) * step }));
};

export const CaptionsV2: React.FC<{ scenes: Scene[] }> = ({ scenes }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const sc = scenes.find((x) => t >= x.start && t < x.end);
  if (!sc || OWN_CAPTION.has(sc.type)) return null; // nas histórias e conversas, o balão já é a legenda
  // a fala atual (segura 0,25 s depois de terminar, para não piscar entre frases)
  const ln = sc.lines.find((l) => t >= l.start - 0.05 && t < l.end + 0.25);
  if (!ln) return null;
  const blocks = chunk(wordsOf(ln), 38);
  const block = blocks.find((b) => t < b[b.length - 1].end + 0.25) ?? blocks[blocks.length - 1];
  const appear = interpolate(t, [block[0].start - 0.05, block[0].start + 0.12], [0, 1], { ...clamp, easing: OUT });
  // Faixa contínua: as palavras já ditas vão num único trecho com fundo pêssego (quebra de linha clona a faixa);
  // a palavra do momento fica em laranja colada ao fim da faixa; as próximas aparecem apagadas.
  const said = block.filter((w) => t >= w.start);
  const cur = said.length && t < said[said.length - 1].end ? said[said.length - 1] : null;
  const done = cur ? said.slice(0, -1) : said;
  const rest = block.slice(said.length);
  const bar = { padding: "4px 12px", borderRadius: 6, boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone" } as const;
  return (
    <div style={{ position: "absolute", left: SAFE.left - 12, width: SAFE_W + 12, top: 1240, fontSize: 56, fontWeight: 700, lineHeight: 1.42, letterSpacing: "-0.01em", opacity: appear, translate: `0 ${(1 - appear) * 12}px` }}>
      {done.length ? <span style={{ ...bar, background: C.peach, color: C.navy, borderRadius: cur ? "6px 0 0 6px" : 6, paddingRight: cur ? 0 : 12 }}>{done.map((w) => w.text).join(" ")}{cur ? " " : ""}</span> : null}
      {cur ? <span style={{ ...bar, background: C.orange, color: C.white, borderRadius: done.length ? "0 6px 6px 0" : 6 }}>{cur.text}</span> : null}
      {rest.length ? <span style={{ color: "rgba(255,255,255,.4)", paddingLeft: 12 }}>{rest.map((w) => w.text).join(" ")}</span> : null}
    </div>
  );
};

export const SceneShellV2: React.FC<{ scene: Scene; last: boolean }> = ({ scene, last }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = Math.round((scene.end - scene.start) * fps);
  const inP = interpolate(frame, [0, 14], [0, 1], { ...clamp, easing: OUT });
  const outP = last ? 0 : interpolate(frame, [dur - 9, dur], [0, 1], { ...clamp, easing: Easing.in(Easing.cubic) });
  return (
    <AbsoluteFill style={{ opacity: Math.min(inP, 1 - outP), translate: `0 ${(1 - inP) * 36 - outP * 24}px` }}>
      <SceneView scene={scene} />
    </AbsoluteFill>
  );
};
