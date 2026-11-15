// Cenas de história: personagens ilustrados (Open Peeps, CC0) que conversam, mudam de expressão,
// trocam mensagens no celular e mostram telas de compra. Cada fala chega com o tempo exato de cada palavra,
// então o balão "escreve" junto com a voz.
import React from "react";
import Peep from "react-peeps";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, SAFE, SAFE_W } from "./theme";
import type { Line, Scene, Word } from "./types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const OUT = Easing.bezier(0.16, 1, 0.3, 1);

// ---------- elenco ----------

type Look = { hair: string; body: string; accessory?: string; skin: string; shirt: string };
// As duas vozes (Dora natural e voz padrão) são femininas, então o elenco é de mulheres.
export const ELENCO: Record<string, Look> = {
  ana: { hair: "LongCurly", body: "Explaining", skin: "#F3C9A5", shirt: C.orange },
  bia: { hair: "Bun", body: "Device", skin: "#E0A982", shirt: "#3D6FD1" },
  carla: { hair: "MediumStraight", body: "Turtleneck", accessory: "GlassRound", skin: "#FBDCC4", shirt: "#2BB673" },
  duda: { hair: "Afro", body: "Sweater", skin: "#9C6644", shirt: "#E5533D" },
  lu: { hair: "LongBangs", body: "Coffee", skin: "#F1C27D", shirt: "#8E6CEF" },
  mari: { hair: "BunCurly", body: "PointingUp", accessory: "GlassButterfly", skin: "#C68642", shirt: "#F2B705" },
};

const FACE: Record<string, [string, string]> = {
  // emoção: [rosto parado, boca aberta falando]
  neutra: ["Calm", "Explaining"],
  feliz: ["SmileBig", "SmileTeeth"],
  animada: ["SmileLol", "SmileTeeth"],
  desconfiada: ["Suspicious", "Explaining"],
  pensativa: ["Solemn", "Explaining"],
  brava: ["Angry", "Rage"],
  furiosa: ["VeryAngry", "Rage"],
  chocada: ["Awe", "Awe"],
  assustada: ["ConcernedFear", "Fear"],
  triste: ["Concerned", "Concerned"],
  cansada: ["Tired", "Explaining"],
  apaixonada: ["LoveGrin", "LoveGrinTeeth"],
  aliviada: ["Smile", "SmileTeeth"],
};
export const EMOCOES = Object.keys(FACE);

export const lookOf = (id?: string) => ELENCO[(id ?? "").toLowerCase()] ?? ELENCO.ana;
const cap = (s: string) => s.replace(/^./, (c) => c.toUpperCase());

/** Personagem: corpo e cabeça separados, para a cabeça balançar enquanto fala. */
const Person: React.FC<{ id: string; emotion: string; talking: boolean; size: number; flip?: boolean; dim?: boolean; at?: number; side?: -1 | 1 }> = ({ id, emotion, talking, size, flip, dim, at = 0, side = -1 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const look = lookOf(id);
  const [still, open] = FACE[emotion] ?? FACE.neutra;
  const face = talking && Math.floor(frame / 4) % 2 === 0 ? open : still;
  const enter = spring({ frame: frame - at, fps, config: { damping: 14, stiffness: 120, mass: 0.8 } });
  const breathe = Math.sin(frame / 14) * 0.012;
  const nod = talking ? Math.sin(frame / 3.2) * 3.2 : Math.sin(frame / 22) * 1.2;
  const lean = talking ? 1.05 : 1;
  const layer: React.CSSProperties = { position: "absolute", inset: 0, width: "100%", height: "100%" };
  return (
    <div style={{ width: size, height: size * 1.412, position: "relative", translate: `${(1 - enter) * side * 700}px 0`, scale: `${(flip ? -1 : 1) * lean} ${lean * (1 + breathe)}`, transformOrigin: "50% 100%", opacity: dim ? 0.8 : 1 }}>
      <Peep style={layer} strokeColor="#14213A" backgroundColor={look.shirt} body={look.body as never} />
      <div style={{ ...layer, rotate: `${nod}deg`, transformOrigin: "50% 47%" }}>
        <Peep style={layer} strokeColor="#14213A" backgroundColor={look.skin} hair={look.hair as never} face={face as never} accessory={(look.accessory ?? "None") as never} />
      </div>
    </div>
  );
};

/** Sinais de quadrinho em cima da cabeça, conforme a emoção. */
const Emote: React.FC<{ emotion: string; at: number; right: boolean }> = ({ emotion, at, right }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < at) return null;
  const p = spring({ frame: frame - at, fps, config: { damping: 9, stiffness: 200 } });
  const wob = Math.sin((frame - at) / 4) * 6;
  const s: React.CSSProperties = { position: "absolute", top: 10, [right ? "left" : "right"]: 10, scale: String(Math.max(0, p)), rotate: `${wob}deg`, fontWeight: 700, lineHeight: 1 };
  if (emotion === "desconfiada" || emotion === "pensativa") return <div style={{ ...s, fontSize: 140, color: C.peach }}>?</div>;
  if (emotion === "chocada" || emotion === "assustada") return <div style={{ ...s, fontSize: 150, color: C.orange }}>!</div>;
  if (emotion === "brava" || emotion === "furiosa")
    return <svg style={s} width="120" height="120" viewBox="0 0 24 24"><path d="M8 3v5H3M16 3v5h5M8 21v-5H3M16 21v-5h5" fill="none" stroke={C.red} strokeWidth="2.6" strokeLinecap="round" /></svg>;
  if (emotion === "apaixonada" || emotion === "feliz" || emotion === "animada" || emotion === "aliviada")
    return <svg style={{ ...s, translate: `0 ${-Math.min(40, (frame - at) * 1.5)}px` }} width="110" height="110" viewBox="0 0 24 24"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.1 0 3.6 1.2 4.3 2.6.7-1.4 2.2-2.6 4.3-2.6 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z" fill={C.red} /></svg>;
  if (emotion === "triste" || emotion === "cansada")
    return <svg style={{ ...s, top: 140, translate: `0 ${((frame - at) % 30) * 2}px` }} width="60" height="84" viewBox="0 0 20 28"><path d="M10 2C7 8 3 12 3 18a7 7 0 0014 0c0-6-4-10-7-16z" fill="#7FB4FF" /></svg>;
  return null;
};

/** Texto que acende palavra por palavra, no tempo da voz. */
const SpokenText: React.FC<{ line: Line; sceneStart: number; size: number; color?: string; dimColor?: string }> = ({ line, sceneStart, size, color = C.navy, dimColor = "rgba(14,28,51,.25)" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps + sceneStart;
  const words: Word[] = line.words?.length ? line.words : line.text.split(/\s+/).map((w, i, a) => {
    const d = (line.end - line.start) / a.length;
    return { text: w, start: line.start + i * d, end: line.start + (i + 1) * d };
  });
  return (
    <div style={{ fontSize: size, fontWeight: 700, lineHeight: 1.14, letterSpacing: "-0.01em" }}>
      {words.map((w, i) => {
        const p = interpolate(t, [w.start - 0.04, w.start + 0.08], [0, 1], clamp);
        return (
          <span key={i} style={{ display: "inline-block", marginRight: "0.26em", color: p > 0.5 ? color : dimColor, translate: `0 ${(1 - p) * 6}px` }}>{w.text}</span>
        );
      })}
    </div>
  );
};

const activeLine = (lines: Line[], t: number) => {
  let k = -1;
  lines.forEach((ln, i) => { if (t >= ln.start - 0.05) k = i; });
  return k;
};

// ---------- cenários ----------

const Lugar: React.FC<{ lugar?: string }> = ({ lugar }) => {
  const frame = useCurrentFrame();
  const floor = <div style={{ position: "absolute", left: 0, right: 0, top: 1330, bottom: 0, background: "linear-gradient(#1A3157, #0E1C33)", borderTop: "4px solid rgba(255,255,255,.08)" }} />;
  if (lugar === "loja")
    return (
      <AbsoluteFill style={{ opacity: 0.5 }}>
        {[0, 1, 2].map((r) => (
          <div key={r} style={{ position: "absolute", left: 40, right: 40, top: 760 + r * 190, height: 14, background: "#2A4A7A", borderRadius: 8 }}>
            {[0, 1, 2, 3, 4, 5].map((b) => <div key={b} style={{ position: "absolute", bottom: 14, left: 30 + b * 165, width: 110, height: 70 + ((b + r) % 3) * 30, borderRadius: 12, background: [C.orange, "#3D6FD1", C.peach, C.green][(b + r) % 4], opacity: 0.8 }} />)}
          </div>
        ))}
        {floor}
      </AbsoluteFill>
    );
  if (lugar === "rua")
    return (
      <AbsoluteFill style={{ opacity: 0.5 }}>
        {[0, 1, 2, 3, 4, 5].map((b) => <div key={b} style={{ position: "absolute", bottom: 590, left: -240 + b * 240 + (frame * 0.6) % 240, width: 190, height: 260 + (b % 3) * 120, background: "#22406C", borderRadius: "16px 16px 0 0" }} />)}
        {floor}
      </AbsoluteFill>
    );
  if (lugar === "casa")
    return (
      <AbsoluteFill style={{ opacity: 0.6 }}>
        <div style={{ position: "absolute", left: 620, top: 600, width: 300, height: 360, borderRadius: 24, border: "12px solid #2A4A7A", background: "linear-gradient(#3D6FD1, #1B3560)" }}>
          <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 12, background: "#2A4A7A" }} />
          <div style={{ position: "absolute", right: 40, top: 40, width: 60, height: 60, borderRadius: 60, background: C.peach, opacity: 0.8 }} />
        </div>
        <div style={{ position: "absolute", left: 120, top: 660, width: 10, height: 380, background: "#2A4A7A" }} />
        <div style={{ position: "absolute", left: 60, top: 600, width: 130, height: 90, borderRadius: "70px 70px 10px 10px", background: C.orange, opacity: 0.6 + Math.sin(frame / 20) * 0.05 }} />
        {floor}
      </AbsoluteFill>
    );
  return floor;
};

// ---------- história (diálogo) ----------

type HistoriaScene = Extract<Scene, { type: "historia" }>;

export const Historia: React.FC<{ s: HistoriaScene }> = ({ s }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps + s.start;
  const k = activeLine(s.lines, t);
  const cur = k >= 0 ? s.lines[k] : undefined;
  const meta = s.falas ?? [];
  const who = k >= 0 ? meta[k]?.quem : undefined;
  const cast = s.personagens.slice(0, 2);
  const two = cast.length === 2;
  const lineFrame = (j: number) => Math.round((s.lines[j].start - s.start) * fps);
  /** Emoção atual do personagem e o frame em que ela mudou. */
  const moodOf = (id: string): [string, number] => {
    let e = s.inicio?.[id] ?? "neutra";
    let at = 0;
    for (let j = 0; j <= k; j++) {
      const m = meta[j];
      if (!m) continue;
      if (m.quem === id && m.emocao) { e = m.emocao; at = lineFrame(j); }
      else if (m.quem !== id && m.reacao) { e = m.reacao; at = lineFrame(j); }
    }
    return [e, at];
  };
  const lineAt = cur ? lineFrame(k) : 0;
  const bubbleIn = spring({ frame: frame - lineAt, fps, config: { damping: 12, stiffness: 220, mass: 0.6 } });
  const speakerIdx = who ? cast.indexOf(who) : -1;
  const narr = !!cur && speakerIdx < 0;
  const size = two ? 470 : 580;
  const talkingNow = (id: string) => !!cur && who === id && t < cur.end && (cur.words?.length ? cur.words.some((w) => t >= w.start && t < w.end + 0.05) : true);
  // câmera: chega perto de quem fala
  const camX = two && speakerIdx >= 0 ? (speakerIdx === 0 ? 50 : -50) : 0;
  const cam = interpolate(frame, [lineAt, lineAt + 12], [0, 1], { ...clamp, easing: OUT });
  const bubbleSize = cur ? (cur.text.length > 80 ? 50 : cur.text.length > 45 ? 58 : 68) : 60;
  return (
    <AbsoluteFill>
      <Lugar lugar={s.lugar} />
      <AbsoluteFill style={{ translate: `${camX * cam}px 0`, scale: String(1.0 + 0.035 * cam + frame * 0.0003), transformOrigin: "50% 85%" }}>
        {cast.map((id, i) => {
          const x = two ? (i === 0 ? SAFE.left - 50 : SAFE.right - size + 70) : (1080 - size) / 2 - 80;
          const [e, at] = moodOf(id);
          return (
            <div key={id} style={{ position: "absolute", left: x, top: 1440 - size * 1.412 + 130, width: size, height: size * 1.412 }}>
              <div style={{ position: "absolute", left: "5%", right: "5%", top: "8%", height: "60%", borderRadius: 999, background: `radial-gradient(closest-side, ${lookOf(id).shirt}55, transparent)`, opacity: speakerIdx === i ? 1 : 0.55 }} />
              <Person id={id} emotion={e} talking={talkingNow(id)} size={size} flip={two && i === 1} dim={two && speakerIdx >= 0 && speakerIdx !== i} at={i * 6} side={i === 0 ? -1 : 1} />
              <Emote key={`${e}-${at}`} emotion={e} at={at} right={two && i === 1} />
              <div style={{ position: "absolute", left: "50%", translate: "-50% 0", bottom: 140, background: C.navy, border: `4px solid ${lookOf(id).shirt}`, color: C.white, fontWeight: 700, fontSize: 36, borderRadius: 999, padding: "6px 26px", whiteSpace: "nowrap" }}>{s.nomes?.[id] ?? cap(id)}</div>
            </div>
          );
        })}
      </AbsoluteFill>
      {cur ? (
        narr ? (
          <div style={{ position: "absolute", left: SAFE.left, width: SAFE_W, top: SAFE.top + 30, background: C.orange, borderRadius: 30, padding: "30px 36px", boxShadow: "0 24px 60px rgba(0,0,0,.35)", scale: String(0.85 + 0.15 * bubbleIn), opacity: Math.min(1, bubbleIn * 2), transformOrigin: "50% 0%" }}>
            <SpokenText line={cur} sceneStart={s.start} size={bubbleSize - 6} color={C.white} dimColor="rgba(255,255,255,.4)" />
          </div>
        ) : (
          <div style={{ position: "absolute", left: SAFE.left, width: SAFE_W, top: SAFE.top + 30, scale: String(0.6 + 0.4 * bubbleIn), opacity: Math.min(1, bubbleIn * 2), transformOrigin: speakerIdx === 1 ? "80% 100%" : "20% 100%" }}>
            <div style={{ background: C.white, borderRadius: 38, padding: "32px 38px", boxShadow: "0 24px 60px rgba(0,0,0,.35)", position: "relative" }}>
              <SpokenText line={cur} sceneStart={s.start} size={bubbleSize} />
              <svg width="80" height="70" viewBox="0 0 80 70" style={{ position: "absolute", bottom: -60, left: speakerIdx === 1 ? undefined : 110, right: speakerIdx === 1 ? 110 : undefined, scale: speakerIdx === 1 ? "-1 1" : undefined }}>
                <path d="M0 0 H70 L14 70 Z" fill={C.white} />
              </svg>
            </div>
          </div>
        )
      ) : null}
    </AbsoluteFill>
  );
};

// ---------- conversa no celular ----------

type ChatScene = Extract<Scene, { type: "chat" }>;

const Phone: React.FC<{ children: React.ReactNode; top?: number; height?: number }> = ({ children, top = SAFE.top, height = 1150 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame, fps, config: { damping: 15, stiffness: 120 } });
  const float = Math.sin(frame / 25) * 6;
  return (
    <div style={{ position: "absolute", left: SAFE.left + 20, width: SAFE_W - 40, top, height, borderRadius: 64, background: "#0B0F17", padding: 16, boxShadow: "0 50px 120px rgba(0,0,0,.55)", translate: `0 ${(1 - p) * 1000 + float}px`, rotate: `${(1 - p) * -8}deg` }}>
      <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: 50, overflow: "hidden", background: "#ECE5DD" }}>
        <div style={{ position: "absolute", top: 14, left: "50%", translate: "-50% 0", width: 150, height: 34, borderRadius: 20, background: "#0B0F17", zIndex: 5 }} />
        {children}
      </div>
    </div>
  );
};

export const Chat: React.FC<{ s: ChatScene }> = ({ s }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps + s.start;
  const meta = s.falas ?? [];
  const me = s.personagens?.[0];
  const other = s.personagens?.[1];
  const LEAD = 0.5; // o "digitando…" aparece meio segundo antes da mensagem
  const shown = s.lines.map((ln, i) => ({ ln, i, mine: (meta[i]?.quem ?? me) === me })).filter((m) => t >= m.ln.start);
  const typing = s.lines.findIndex((ln) => t >= ln.start - LEAD && t < ln.start);
  const typingMine = typing >= 0 && (meta[typing]?.quem ?? me) === me;
  const scroll = Math.max(0, shown.length - 4) * 175;
  const otherLook = lookOf(other);
  return (
    <AbsoluteFill>
      <Phone>
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 180, background: "#075E54", display: "flex", alignItems: "flex-end", gap: 18, padding: "0 26px 22px", zIndex: 4 }}>
          <div style={{ width: 88, height: 88, borderRadius: 88, overflow: "hidden", background: otherLook.shirt, position: "relative" }}>
            <Peep style={{ position: "absolute", width: 150, height: 212, left: -31, top: -8 }} strokeColor="#14213A" backgroundColor={otherLook.skin} hair={otherLook.hair as never} face={"Smile" as never} />
          </div>
          <div style={{ color: "#fff" }}>
            <div style={{ fontSize: 42, fontWeight: 700 }}>{s.contato ?? cap(other ?? "Amiga")}</div>
            <div style={{ fontSize: 28, opacity: 0.85 }}>{typing >= 0 && !typingMine ? "digitando…" : "online"}</div>
          </div>
        </div>
        <div style={{ position: "absolute", top: 200, left: 22, right: 22, display: "flex", flexDirection: "column", gap: 20, translate: `0 ${-scroll}px` }}>
          {shown.map(({ ln, i, mine }) => {
            const p = spring({ frame: frame - Math.round((ln.start - s.start) * fps), fps, config: { damping: 13, stiffness: 200, mass: 0.6 } });
            return (
              <div key={i} style={{ alignSelf: mine ? "flex-end" : "flex-start", maxWidth: "84%", background: mine ? "#DCF8C6" : "#fff", borderRadius: mine ? "28px 28px 6px 28px" : "28px 28px 28px 6px", padding: "20px 26px 12px", boxShadow: "0 3px 6px rgba(0,0,0,.12)", scale: String(0.7 + 0.3 * p), opacity: Math.min(1, p * 2), transformOrigin: mine ? "100% 100%" : "0% 100%" }}>
                <SpokenText line={ln} sceneStart={s.start} size={ln.text.length > 60 ? 46 : 52} color="#111B21" dimColor="rgba(17,27,33,.3)" />
                <div style={{ textAlign: "right", fontSize: 22, color: mine ? "#34B7F1" : "#667781", marginTop: 4 }}>{mine ? "✓✓" : " "}</div>
              </div>
            );
          })}
          {typing >= 0 ? (
            <div style={{ alignSelf: typingMine ? "flex-end" : "flex-start", background: typingMine ? "#DCF8C6" : "#fff", borderRadius: 28, padding: "24px 30px", display: "flex", gap: 10 }}>
              {[0, 1, 2].map((d) => <span key={d} style={{ width: 16, height: 16, borderRadius: 16, background: "#8696A0", translate: `0 ${Math.sin(frame / 3 + d) * 5}px` }} />)}
            </div>
          ) : null}
        </div>
      </Phone>
    </AbsoluteFill>
  );
};

// ---------- tela de compra no celular ----------

type TelaScene = Extract<Scene, { type: "tela" }>;

export const Tela: React.FC<{ s: TelaScene }> = ({ s }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const offset = s.lines.length > s.itens.length ? 1 : 0; // a 1ª fala pode apresentar a tela
  const shownAt = (i: number) => Math.round(((s.lines[Math.min(i + offset, s.lines.length - 1)]?.start ?? s.start) - s.start) * fps);
  const lastItem = shownAt(s.itens.length - 1);
  const stampF = Math.round((s.lines[s.lines.length - 1].start - s.start) * fps) + 8;
  const stamp = spring({ frame: frame - stampF, fps, config: { damping: 8, stiffness: 160 } });
  const totalP = interpolate(frame, [lastItem + 10, lastItem + 20], [0, 1], clamp);
  const shake = frame >= stampF && frame < stampF + 10 ? Math.sin(frame * 2.3) * 8 : 0;
  return (
    <AbsoluteFill style={{ translate: `${shake}px 0` }}>
      <Phone top={SAFE.top + 10} height={1010}>
        <div style={{ position: "absolute", inset: 0, background: "#F5F6F8" }}>
          <div style={{ height: 180, background: "#FFE600", display: "flex", alignItems: "flex-end", padding: "0 34px 26px", fontSize: 44, fontWeight: 700, color: "#2D3277" }}>{s.titulo}</div>
          <div style={{ padding: "26px 28px", display: "flex", flexDirection: "column", gap: 18 }}>
            {s.itens.map((it, i) => {
              const at = shownAt(i);
              const p = spring({ frame: frame - at, fps, config: { damping: 14, stiffness: 180 } });
              const strike = it.riscado ? interpolate(frame, [at + 10, at + 22], [0, 100], clamp) : 0;
              const flash = it.alerta ? interpolate(frame, [at, at + 6, at + 18], [0, 1, 0.35], clamp) : 0;
              return (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 20, background: it.alerta ? `rgba(229,83,61,${0.06 + flash * 0.14})` : "#fff", borderRadius: 22, padding: "26px 28px", boxShadow: "0 4px 12px rgba(0,0,0,.06)", opacity: Math.min(1, p * 2), translate: `${(1 - p) * 300}px 0`, border: it.alerta ? `4px solid ${C.red}` : "4px solid transparent" }}>
                  <span style={{ fontSize: 38, color: "#333", fontWeight: 500 }}>{it.rotulo}</span>
                  <span style={{ position: "relative", fontSize: 42, fontWeight: 700, color: it.alerta ? C.red : "#111", whiteSpace: "nowrap" }}>
                    {it.valor}
                    {it.riscado ? <span style={{ position: "absolute", left: -4, top: "50%", height: 6, width: `${strike}%`, background: C.red, borderRadius: 4 }} /> : null}
                  </span>
                </div>
              );
            })}
            {s.total ? (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "20px 10px 0", borderTop: "3px dashed #ccc", opacity: totalP, scale: String(0.9 + 0.1 * totalP) }}>
                <span style={{ fontSize: 46, fontWeight: 700, color: "#111" }}>Total</span>
                <span style={{ fontSize: 54, fontWeight: 700, color: "#00A650" }}>{s.total}</span>
              </div>
            ) : null}
          </div>
        </div>
      </Phone>
      {s.carimbo && frame >= stampF ? (
        <div style={{ position: "absolute", left: 0, width: 1080 - 230 + 72, top: 1110, display: "flex", justifyContent: "center" }}>
          <div style={{ border: `10px solid ${C.red}`, color: C.red, background: "rgba(255,255,255,.94)", fontWeight: 700, fontSize: 80, letterSpacing: "0.04em", padding: "8px 34px", borderRadius: 20, rotate: "-10deg", scale: String(Math.max(0.01, 2.2 - 1.2 * stamp)), textTransform: "uppercase", whiteSpace: "nowrap" }}>{s.carimbo}</div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

/** Cenas em que o próprio texto na tela já é a legenda (balão, mensagem): a legenda de baixo some. */
export const OWN_CAPTION = new Set(["historia", "chat"]);
