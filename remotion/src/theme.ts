import { loadFont } from "@remotion/fonts";
import { createContext, useContext } from "react";
import { staticFile } from "remotion";

// Modelo visual do Reels: "v1" (original) ou "v2" (26/11: legenda em faixa, movimento calmo, sem brilho).
export type Modelo = "v1" | "v2";
export const ModelCtx = createContext<Modelo>("v1");
export const useModelo = () => useContext(ModelCtx);

// Marca Factor Ofertas
export const C = {
  navy: "#0E1C33",
  navy2: "#172C4D",
  orange: "#F05A1A",
  orange2: "#FF7A3D",
  peach: "#FFE1CC",
  cream: "#FFF7F1",
  muted: "#9FB0C8",
  green: "#2BB673",
  red: "#E5533D",
  white: "#FFFFFF",
};

export const FONT = "SpaceGrotesk";

// Área segura do Reels (1080x1920): nada acima de 230, nada abaixo de 1440, 230 px livres à direita.
export const SAFE = { left: 72, right: 1080 - 230, top: 250, bottom: 1440 };
export const SAFE_W = SAFE.right - SAFE.left;

let loaded = false;
export const loadBrandFonts = () => {
  if (loaded) return;
  loaded = true;
  loadFont({ family: FONT, url: staticFile("fonts/space-grotesk-latin-500-normal.woff2"), weight: "500" });
  loadFont({ family: FONT, url: staticFile("fonts/space-grotesk-latin-700-normal.woff2"), weight: "700" });
};
