// Reels explicativo em 3D ("como funciona"), GUT #112.
// O robô entrega a fala com o instante de cada palavra e os "cues": o segundo em que cada movimento começa,
// tirado da palavra que o dispara (ex.: "resistência" acende a resistência).
import type { Line } from "../types";

export type ExplicaProps = {
  tema: "airfryer" | "coracao";
  titulo: string;
  lines: Line[];
  cues: Record<string, number>;
  audio: string;
  duration: number;
  handle: string;
};
