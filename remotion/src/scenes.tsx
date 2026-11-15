// Cenas dos Reels. Cada cena começa no frame 0 da sua <Sequence> e sabe quando cada fala começa,
// para os elementos entrarem junto com a voz.
import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Confetti } from "./remocn/confetti";
import { C, SAFE, SAFE_W } from "./theme";
import type { Scene } from "./types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const OUT = Easing.bezier(0.16, 1, 0.3, 1);

/** Frame (relativo à cena) em que a fala i começa. */
export const useLineAt = (scene: Scene) => {
  const { fps } = useVideoConfig();
  return (i: number, fallback = 0) => {
    const ln = scene.lines[i];
    return Math.max(0, Math.round(((ln ? ln.start : scene.start + fallback) - scene.start) * fps));
  };
};

const usePop = (at: number, damping = 13) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - at, fps, config: { damping, stiffness: 170, mass: 0.7 } });
};

const useRise = (at: number, dur = 14) => {
  const frame = useCurrentFrame();
  return interpolate(frame, [at, at + dur], [0, 1], { ...clamp, easing: OUT });
};

/** Texto que entra palavra por palavra, subindo, e quebra linha normalmente. */
export const RiseText: React.FC<{ text: string; at: number; size: number; color?: string; weight?: number; stagger?: number; mark?: string; align?: "left" | "center" }> = ({ text, at, size, color = C.white, weight = 700, stagger = 2, mark, align = "left" }) => {
  const frame = useCurrentFrame();
  const words = text.split(/\s+/).filter(Boolean);
  const markWords = new Set((mark ?? "").toLowerCase().split(/\s+/).filter(Boolean));
  return (
    <div style={{ fontSize: size, fontWeight: weight, color, lineHeight: 1.06, letterSpacing: "-0.02em", textAlign: align }}>
      {words.map((w, i) => {
        const p = interpolate(frame, [at + i * stagger, at + i * stagger + 12], [0, 1], { ...clamp, easing: OUT });
        const hl = markWords.has(w.toLowerCase().replace(/[^\p{L}\p{N}%$]/gu, ""));
        return (
          <span key={i} style={{ display: "inline-block", opacity: p, translate: `0 ${(1 - p) * size * 0.45}px`, marginRight: "0.24em", color: hl ? C.orange : undefined }}>
            {w}
          </span>
        );
      })}
    </div>
  );
};

const Kicker: React.FC<{ text: string; at?: number }> = ({ text, at = 0 }) => {
  const p = usePop(at, 12);
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 14, background: C.orange, color: C.white, fontWeight: 700, fontSize: 38, letterSpacing: "0.06em", padding: "14px 28px", borderRadius: 999, scale: String(0.6 + 0.4 * p), opacity: Math.min(1, p * 2), transformOrigin: "left center", boxShadow: "0 12px 40px rgba(240,90,26,.45)", textTransform: "uppercase" }}>
      <span style={{ width: 16, height: 16, borderRadius: 99, background: C.white }} />
      {text}
    </div>
  );
};

/** Bloco de conteúdo. Sem "top", fica centralizado na vertical entre a marca e a legenda. */
const Box: React.FC<{ top?: number; children: React.ReactNode; gap?: number; center?: boolean }> = ({ top, children, gap = 36, center }) => (
  <div style={{ position: "absolute", left: SAFE.left, width: SAFE_W, top: top ?? SAFE.top + 10, height: top === undefined ? SAFE.bottom - 200 - (SAFE.top + 10) : undefined, display: "flex", flexDirection: "column", justifyContent: top === undefined ? "center" : "flex-start", gap, alignItems: center ? "center" : "flex-start" }}>{children}</div>
);

const Card: React.FC<{ src: string; size: number; at?: number; zoom?: boolean }> = ({ src, size, at = 0, zoom = true }) => {
  const frame = useCurrentFrame();
  const p = usePop(at, 15);
  return (
    <div style={{ width: size, height: size, background: C.white, borderRadius: 44, overflow: "hidden", boxShadow: "0 40px 90px rgba(0,0,0,.45)", scale: String(0.85 + 0.15 * p + (zoom ? Math.max(0, frame - at) * 0.0007 : 0)), opacity: Math.min(1, p * 2) }}>
      <Img src={src} style={{ width: "100%", height: "100%", objectFit: "contain", padding: size * 0.07 }} />
    </div>
  );
};

const Badge: React.FC<{ off: number; at: number; size?: number; style?: React.CSSProperties }> = ({ off, at, size = 230, style }) => {
  const frame = useCurrentFrame();
  const p = usePop(at, 10);
  return (
    <div style={{ position: "absolute", width: size, height: size, borderRadius: size, background: C.orange, border: "8px solid #fff", color: C.white, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontWeight: 700, boxShadow: "0 20px 60px rgba(240,90,26,.55)", scale: String(Math.max(0, p)), rotate: `${-10 + Math.sin(frame / 9) * 3}deg`, ...style }}>
      <span style={{ fontSize: size * 0.34, lineHeight: 0.9, letterSpacing: "-0.03em" }}>-{off}%</span>
      <span style={{ fontSize: size * 0.12, letterSpacing: "0.1em" }}>OFF</span>
    </div>
  );
};

const Check: React.FC<{ color?: string; size?: number }> = ({ color = C.green, size = 64 }) => (
  <span style={{ flex: `0 0 ${size}px`, width: size, height: size, borderRadius: size, background: color, display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
    <svg width={size * 0.56} height={size * 0.56} viewBox="0 0 24 24"><path d="M5 12.5l4.2 4.2L19 7" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
  </span>
);

const Xmark: React.FC<{ size?: number }> = ({ size = 64 }) => (
  <span style={{ flex: `0 0 ${size}px`, width: size, height: size, borderRadius: size, background: C.red, display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
    <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" /></svg>
  </span>
);

// ---------- conteúdo ----------

const Gancho: React.FC<{ s: Extract<Scene, { type: "gancho" }> }> = ({ s }) => {
  const frame = useCurrentFrame();
  const punch = interpolate(frame, [0, 6, 14], [1.12, 0.98, 1], clamp);
  return (
    <Box gap={44}>
      {s.kicker ? <Kicker text={s.kicker} /> : null}
      <div style={{ scale: String(punch), transformOrigin: "left top" }}>
        <RiseText text={s.titulo} at={2} size={s.titulo.length > 60 ? 100 : s.titulo.length > 38 ? 116 : 136} mark={s.destaque} stagger={2} />
      </div>
    </Box>
  );
};

const Numero: React.FC<{ s: Extract<Scene, { type: "numero" }> }> = ({ s }) => {
  const at = useLineAt(s);
  const p = usePop(at(0), 11);
  return (
    <Box gap={30}>
      {s.kicker ? <Kicker text={s.kicker} /> : null}
      <div style={{ fontSize: s.numero.length > 6 ? 200 : 280, fontWeight: 700, color: C.orange, letterSpacing: "-0.05em", lineHeight: 0.9, scale: String(0.5 + 0.5 * p), transformOrigin: "left center", textShadow: "0 20px 60px rgba(240,90,26,.35)" }}>{s.numero}</div>
      <RiseText text={s.rotulo} at={at(0) + 8} size={70} color={C.cream} />
    </Box>
  );
};

const Lista: React.FC<{ s: Extract<Scene, { type: "lista" }> }> = ({ s }) => {
  const at = useLineAt(s);
  const offset = s.lines.length > s.itens.length ? 1 : 0; // a 1ª fala pode ser o título
  return (
    <Box gap={40}>
      {s.kicker ? <Kicker text={s.kicker} /> : null}
      <RiseText text={s.titulo} at={0} size={s.titulo.length > 40 ? 76 : 90} />
      <div style={{ display: "flex", flexDirection: "column", gap: 26, marginTop: 8 }}>
        {s.itens.map((it, i) => <ListRow key={i} text={it} at={at(i + offset, 0.8 + i * 1.2)} />)}
      </div>
    </Box>
  );
};

const ListRow: React.FC<{ text: string; at: number; icon?: React.ReactNode; dim?: boolean }> = ({ text, at, icon, dim }) => {
  const p = useRise(at, 12);
  return (
    <div style={{ display: "flex", gap: 24, alignItems: "center", opacity: p, translate: `${(1 - p) * -60}px 0`, background: "rgba(255,255,255,.08)", border: "2px solid rgba(255,255,255,.14)", borderRadius: 28, padding: "22px 28px", fontSize: 50, fontWeight: 700, color: dim ? C.muted : C.white, lineHeight: 1.12 }}>
      {icon ?? <Check />}
      <span>{text}</span>
    </div>
  );
};

const MitoVerdade: React.FC<{ s: Extract<Scene, { type: "mito_verdade" }> }> = ({ s }) => {
  const at = useLineAt(s);
  const frame = useCurrentFrame();
  const v = at(1, 1.6);
  const strike = interpolate(frame, [v - 10, v], [0, 100], clamp);
  const pv = usePop(v, 12);
  return (
    <Box gap={40}>
      <Tag text="MITO" color={C.red} />
      <div style={{ position: "relative", alignSelf: "stretch" }}>
        <RiseText text={s.mito} at={2} size={84} color={frame > v ? C.muted : C.white} />
        <div style={{ position: "absolute", left: 0, top: "48%", height: 12, width: `${strike}%`, background: C.red, borderRadius: 6 }} />
      </div>
      <div style={{ opacity: pv, scale: String(0.8 + 0.2 * pv), transformOrigin: "left center", display: "flex", flexDirection: "column", gap: 28, marginTop: 24 }}>
        <Tag text="VERDADE" color={C.green} />
        <RiseText text={s.verdade} at={v + 4} size={84} />
      </div>
    </Box>
  );
};

const Tag: React.FC<{ text: string; color: string }> = ({ text, color }) => (
  <span style={{ alignSelf: "flex-start", background: color, color: C.white, fontWeight: 700, fontSize: 46, letterSpacing: "0.08em", padding: "10px 26px", borderRadius: 16 }}>{text}</span>
);

const Passos: React.FC<{ s: Extract<Scene, { type: "passos" }> }> = ({ s }) => {
  const at = useLineAt(s);
  const offset = s.lines.length > s.passos.length ? 1 : 0;
  return (
    <Box gap={34}>
      <RiseText text={s.titulo} at={0} size={s.titulo.length > 40 ? 84 : 100} />
      {s.passos.map((p, i) => <Step key={i} n={i + 1} text={p} at={at(i + offset, 0.8 + i * 1.2)} />)}
    </Box>
  );
};

const Step: React.FC<{ n: number; text: string; at: number }> = ({ n, text, at }) => {
  const p = usePop(at, 14);
  return (
    <div style={{ display: "flex", gap: 26, alignItems: "center", opacity: Math.min(1, p * 2), translate: `0 ${(1 - p) * 50}px` }}>
      <span style={{ flex: "0 0 104px", height: 104, borderRadius: 30, background: C.orange, color: C.white, fontSize: 64, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>{n}</span>
      <span style={{ fontSize: 56, fontWeight: 700, lineHeight: 1.12, color: C.cream }}>{text}</span>
    </div>
  );
};

const Comparacao: React.FC<{ s: Extract<Scene, { type: "comparacao" }> }> = ({ s }) => {
  const at = useLineAt(s);
  const col = (side: { titulo: string; itens: string[] }, good: boolean, start: number) => {
    const p = useRise(start, 14);
    return (
      <div style={{ flex: 1, opacity: p, translate: `0 ${(1 - p) * 60}px`, background: good ? "rgba(240,90,26,.16)" : "rgba(255,255,255,.07)", border: `3px solid ${good ? C.orange : "rgba(255,255,255,.18)"}`, borderRadius: 36, padding: 30, display: "flex", flexDirection: "column", gap: 22 }}>
        <div style={{ fontSize: 50, fontWeight: 700, color: good ? C.orange : C.muted }}>{side.titulo}</div>
        {side.itens.map((it, i) => (
          <div key={i} style={{ display: "flex", gap: 14, alignItems: "flex-start", fontSize: 40, fontWeight: 500, color: good ? C.white : C.muted, lineHeight: 1.15 }}>
            {good ? <Check size={44} /> : <Xmark size={44} />}<span>{it}</span>
          </div>
        ))}
      </div>
    );
  };
  return (
    <Box gap={36}>
      {s.titulo ? <RiseText text={s.titulo} at={0} size={80} /> : null}
      <div style={{ display: "flex", gap: 22, alignSelf: "stretch" }}>
        {col(s.esquerda, false, at(0, 0.3))}
        {col(s.direita, true, at(1, 1.6))}
      </div>
    </Box>
  );
};

const Pergunta: React.FC<{ s: Extract<Scene, { type: "pergunta" }> }> = ({ s }) => {
  const at = useLineAt(s);
  return (
    <Box gap={46}>
      <Kicker text="Comenta aí" />
      <RiseText text={s.pergunta} at={2} size={s.pergunta.length > 50 ? 84 : 100} />
      <div style={{ display: "flex", flexDirection: "column", gap: 24, alignSelf: "stretch" }}>
        {s.opcoes.slice(0, 3).map((o, i) => <Option key={i} letter={String.fromCharCode(65 + i)} text={o} at={at(1, 1.2) + i * 6} />)}
      </div>
    </Box>
  );
};

const Option: React.FC<{ letter: string; text: string; at: number }> = ({ letter, text, at }) => {
  const p = usePop(at, 14);
  return (
    <div style={{ display: "flex", gap: 22, alignItems: "center", background: C.white, color: C.navy, borderRadius: 999, padding: "18px 30px", fontSize: 48, fontWeight: 700, scale: String(0.8 + 0.2 * p), opacity: Math.min(1, p * 2), transformOrigin: "left center" }}>
      <span style={{ width: 70, height: 70, borderRadius: 70, background: C.orange, color: C.white, display: "inline-flex", alignItems: "center", justifyContent: "center" }}>{letter}</span>
      {text}
    </div>
  );
};

const Destaque: React.FC<{ s: Extract<Scene, { type: "destaque" }> }> = ({ s }) => {
  const at = useLineAt(s);
  const frame = useCurrentFrame();
  const m = interpolate(frame, [at(1, 0.9), at(1, 0.9) + 12], [0, 1], { ...clamp, easing: OUT });
  return (
    <Box gap={40}>
      {s.kicker ? <Kicker text={s.kicker} /> : null}
      <div style={{ fontSize: 96, fontWeight: 700, lineHeight: 1.1, letterSpacing: "-0.02em", color: C.white }}>
        {s.antes ? <RiseText text={s.antes} at={2} size={96} /> : null}
        <span style={{ position: "relative", display: "inline-block", marginTop: 10 }}>
          <span style={{ position: "absolute", inset: "4px -14px", background: C.orange, borderRadius: 18, transformOrigin: "left center", scale: `${m} 1` }} />
          <span style={{ position: "relative" }}><RiseText text={s.destaque} at={at(1, 0.9) - 4} size={96} /></span>
        </span>
        {s.depois ? <RiseText text={s.depois} at={at(2, 1.8)} size={96} /> : null}
      </div>
    </Box>
  );
};

// ---------- ofertas ----------

const Produto: React.FC<{ s: Extract<Scene, { type: "produto" }> }> = ({ s }) => {
  const at = useLineAt(s);
  return (
    <>
      <Box gap={40}>{s.kicker ? <Kicker text={s.kicker} /> : null}</Box>
      <div style={{ position: "absolute", left: SAFE.left + 20, top: SAFE.top + 140 }}><Card src={s.imagem} size={720} /></div>
      {s.desconto ? <Badge off={s.desconto} at={at(1, 1)} style={{ left: SAFE.right - 200, top: SAFE.top + 90 }} /> : null}
      <div style={{ position: "absolute", left: SAFE.left, width: SAFE_W, top: SAFE.top + 900 }}><RiseText text={s.nome} at={at(1, 1) + 4} size={70} color={C.cream} /></div>
    </>
  );
};

const Preco: React.FC<{ s: Extract<Scene, { type: "preco" }> }> = ({ s }) => {
  const at = useLineAt(s);
  const frame = useCurrentFrame();
  const n = s.de ? at(1, 1.4) : at(0, 0.2);
  const pn = usePop(n, 12);
  const strike = interpolate(frame, [at(0) + 14, at(0) + 26], [0, 100], clamp);
  const deP = useRise(at(0), 10);
  return (
    <>
      <div style={{ position: "absolute", left: SAFE.left, top: SAFE.top + 20 }}><Card src={s.imagem} size={480} /></div>
      {s.desconto ? <Badge off={s.desconto} at={n + 8} size={250} style={{ left: SAFE.left + 500, top: SAFE.top + 140 }} /> : null}
      <Box top={SAFE.top + 560} gap={18}>
        <RiseText text={s.nome} at={2} size={60} color={C.cream} />
        {s.de ? (
          <div style={{ position: "relative", fontSize: 60, color: C.muted, fontWeight: 500, opacity: deP }}>
            de {s.de}
            <span style={{ position: "absolute", left: 70, top: "52%", height: 8, width: `calc((100% - 70px) * ${strike / 100})`, background: C.orange, borderRadius: 4 }} />
          </div>
        ) : null}
        <div style={{ fontSize: 160, fontWeight: 700, letterSpacing: "-0.04em", lineHeight: 1, color: C.white, scale: String(0.6 + 0.4 * pn), opacity: Math.min(1, pn * 2), transformOrigin: "left center" }}>
          <span style={{ fontSize: 76, color: C.peach, marginRight: 14 }}>R$</span>{s.por.replace("R$ ", "")}
        </div>
        <div style={{ height: 14, borderRadius: 7, background: C.orange, width: `${interpolate(frame, [n + 8, n + 22], [0, 100], clamp) * 0.8}%` }} />
      </Box>
    </>
  );
};

const Prova: React.FC<{ s: Extract<Scene, { type: "prova" }> }> = ({ s }) => {
  const at = useLineAt(s);
  const span = Math.max(14, at(1, 2) - at(0));
  return (
    <>
      <div style={{ position: "absolute", left: SAFE.left, top: SAFE.top + 20 }}><Card src={s.imagem} size={380} /></div>
      <Box top={SAFE.top + 460} gap={26}>
        <RiseText text="Compra segura" at={2} size={84} />
        {s.selos.map((t, i) => <ListRow key={i} text={t} at={at(0) + (i * span) / Math.max(1, s.selos.length)} />)}
      </Box>
    </>
  );
};

const Produtos: React.FC<{ s: Extract<Scene, { type: "produtos" }> }> = ({ s }) => {
  const frame = useCurrentFrame();
  const at = useLineAt(s);
  const n = s.imagens.length;
  const subP = useRise(at(0) + 14);
  return (
    <>
      <Box gap={40}>{s.kicker ? <Kicker text={s.kicker} /> : null}</Box>
      {s.imagens.map((src, k) => {
        const p = spring({ frame: frame - 4 - k * 5, fps: 30, config: { damping: 13 } });
        const x = SAFE.left + 30 + k * ((SAFE_W - 360) / Math.max(1, n - 1));
        return (
          <div key={k} style={{ position: "absolute", left: x, top: SAFE.top + 160 + Math.abs(k - (n - 1) / 2) * 40, rotate: `${(k - (n - 1) / 2) * 8}deg`, scale: String(0.7 + 0.3 * p), opacity: Math.min(1, p * 2), zIndex: k === 1 ? 3 : 1 }}>
            <Card src={src} size={360} zoom={false} />
          </div>
        );
      })}
      <Box top={SAFE.top + 700} gap={24}>
        <RiseText text={s.titulo} at={at(0)} size={100} />
        {s.sub ? <span style={{ alignSelf: "flex-start", background: C.orange, borderRadius: 999, padding: "12px 34px", fontSize: 58, fontWeight: 700, opacity: subP }}>{s.sub}</span> : null}
      </Box>
    </>
  );
};

const Item: React.FC<{ s: Extract<Scene, { type: "item" }> }> = ({ s }) => {
  const at = useLineAt(s);
  const pn = usePop(at(1, 1.2), 12);
  return (
    <>
      <div style={{ position: "absolute", left: SAFE.left, top: SAFE.top + 10, display: "flex", alignItems: "baseline", gap: 12, fontWeight: 700 }}>
        <span style={{ fontSize: 150, color: C.orange, lineHeight: 0.8 }}>{s.indice}</span>
        <span style={{ fontSize: 52, color: C.muted }}>/{s.total}</span>
      </div>
      <div style={{ position: "absolute", left: SAFE.left + 150, top: SAFE.top + 60 }}><Card src={s.imagem} size={560} /></div>
      {s.desconto && s.desconto >= 10 ? <Badge off={s.desconto} at={at(1, 1.2) + 6} size={200} style={{ left: SAFE.right - 190, top: SAFE.top + 20 }} /> : null}
      <Box top={SAFE.top + 680} gap={14}>
        <RiseText text={s.nome} at={at(0) + 4} size={64} color={C.cream} />
        <div style={{ fontSize: 130, fontWeight: 700, letterSpacing: "-0.04em", scale: String(0.6 + 0.4 * pn), opacity: Math.min(1, pn * 2), transformOrigin: "left center" }}>
          <span style={{ fontSize: 66, color: C.peach, marginRight: 12 }}>R$</span>{s.por.replace("R$ ", "")}
        </div>
      </Box>
    </>
  );
};

// ---------- curte e segue ----------

const Cta: React.FC<{ s: Extract<Scene, { type: "cta" }> }> = ({ s }) => {
  const frame = useCurrentFrame();
  const at = useLineAt(s);
  const heart = usePop(at(0) + 2, 9);
  const follow = at(1, 1.2);
  const fp = usePop(follow, 13);
  const tapped = frame >= follow + 16;
  const tapScale = interpolate(frame, [follow + 12, follow + 16, follow + 22], [1, 0.9, 1], clamp);
  const tail = useRise(at(2, 2.4));
  const offers = s.ofertas?.length ? `ofertas ${s.ofertas.map((o) => "#" + o).join(" · ")}` : s.oferta ? `oferta #${s.oferta}` : null;
  return (
    <>
      <Confetti startFrame={at(0) + 2} originX={0.42} originY={0.3} particleCount={70} colors={[C.orange, C.peach, "#fff", "#FFB38A"]} seed={7} />
      <Box gap={42} center>
        <div style={{ scale: String(heart), position: "relative" }}>
          <svg width="230" height="230" viewBox="0 0 24 24"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.1 0 3.6 1.2 4.3 2.6.7-1.4 2.2-2.6 4.3-2.6 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z" fill={C.red} /></svg>
        </div>
        <div style={{ fontSize: 112, fontWeight: 700, lineHeight: 1, textAlign: "center", letterSpacing: "-0.03em" }}>
          <RiseText text="Curte e segue" at={at(0)} size={112} align="center" />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 22, background: "rgba(255,255,255,.1)", border: "2px solid rgba(255,255,255,.18)", borderRadius: 999, padding: "16px 18px 16px 28px", scale: String(Math.max(0, fp) * tapScale), opacity: Math.min(1, fp * 2) }}>
          <span style={{ fontSize: 50, fontWeight: 700 }}>{s.handle}</span>
          <span style={{ background: tapped ? "transparent" : C.orange, border: tapped ? "3px solid rgba(255,255,255,.6)" : "3px solid transparent", color: C.white, fontSize: 44, fontWeight: 700, borderRadius: 999, padding: "12px 34px" }}>{tapped ? "Seguindo" : "Seguir"}</span>
        </div>
        {offers ? <div style={{ opacity: tail, fontSize: 54, fontWeight: 700, color: C.peach, textAlign: "center" }}>Link na bio · {offers}</div> : null}
        {s.salvar ? <div style={{ opacity: tail, fontSize: 46, fontWeight: 500, color: C.peach }}>Salva pra ver depois</div> : null}
      </Box>
    </>
  );
};

export const SceneView: React.FC<{ scene: Scene }> = ({ scene }) => {
  switch (scene.type) {
    case "gancho": return <Gancho s={scene} />;
    case "numero": return <Numero s={scene} />;
    case "lista": return <Lista s={scene} />;
    case "mito_verdade": return <MitoVerdade s={scene} />;
    case "passos": return <Passos s={scene} />;
    case "comparacao": return <Comparacao s={scene} />;
    case "pergunta": return <Pergunta s={scene} />;
    case "destaque": return <Destaque s={scene} />;
    case "produto": return <Produto s={scene} />;
    case "preco": return <Preco s={scene} />;
    case "prova": return <Prova s={scene} />;
    case "produtos": return <Produtos s={scene} />;
    case "item": return <Item s={scene} />;
    case "cta": return <Cta s={scene} />;
    default: return <AbsoluteFill />;
  }
};

