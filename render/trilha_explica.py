"""Trilha de fundo para os Reels explicativos (GUT #112), gerada em código: sem direito autoral de terceiros.

Clima de "documentário curioso": colchão de acordes suave, arpejo de marimba leve e baixo macio, 92 BPM,
volume constante do começo ao fim (não briga com o locutor). Mesma semente = mesma música.
Uso: python render/trilha_explica.py saida.wav [segundos]
"""
from __future__ import annotations

import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter

SR = 48000
BPM = 92
BEAT = 60 / BPM


def midi(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def pad(freqs: list[float], dur: float) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):  # leve desafinação: som mais "quente"
            ff = f * 2 ** (det / 12)
            out += np.sin(2 * np.pi * ff * t) + 0.18 * np.sin(2 * np.pi * 2 * ff * t)
    a = np.minimum(1, t / 0.9) * np.minimum(1, (dur - t) / 0.9)  # entra e sai devagar
    return out * np.clip(a, 0, 1) / (len(freqs) * 3)


def marimba(f: float, dur: float = 1.2) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    att = np.minimum(1, t / 0.004)
    return att * (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.35) + 0.25 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.06))


def bass(f: float, dur: float) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    return (np.sin(2 * np.pi * f * t) + 0.1 * np.sin(2 * np.pi * 2 * f * t)) * np.minimum(1, t / 0.02) * np.exp(-t / 0.9)


def reverb(x: np.ndarray, secs: float = 2.2, mix: float = 0.28, seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR / (secs / 5))
    ir /= np.sqrt((ir ** 2).sum())
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return (1 - mix) * x + mix * wet


def lowpass(x: np.ndarray, fc: float) -> np.ndarray:
    b, a = butter(2, fc / (SR / 2))
    return lfilter(b, a, x)


def build(seconds: float) -> np.ndarray:
    # D → Bm → G → A (com 7ª/9ª: tons claros e calmos), 2 compassos cada
    chords = [
        (50, [62, 66, 69, 73, 76]),  # Dmaj9
        (47, [59, 62, 66, 69, 73]),  # Bm9
        (43, [55, 59, 62, 66, 69]),  # Gmaj7
        (45, [57, 61, 64, 67, 71]),  # A7sus
    ]
    bar = 4 * BEAT
    total = int((seconds + 4) * SR)
    pads, keys, low = np.zeros(total), np.zeros(total), np.zeros(total)
    rng = np.random.default_rng(11)

    def put(buf: np.ndarray, s: int, x: np.ndarray) -> None:
        e = min(total, s + len(x))
        buf[s:e] += x[: e - s]

    t0, i = 0.0, 0
    while t0 < seconds + 1:
        root, notes = chords[i % 4]
        dur = 2 * bar
        s = int(t0 * SR)
        put(pads, s, pad([midi(n) for n in notes[:4]], dur + 0.8))
        put(low, s, bass(midi(root), dur))
        for k in range(16):  # arpejo em colcheias; às vezes pula uma nota (respira)
            if rng.random() < 0.22:
                continue
            note = notes[[0, 2, 4, 3, 1, 3, 2, 4][k % 8]] + (12 if k % 8 in (2, 6) else 0)
            put(keys, s + int(k * BEAT / 2 * SR), marimba(midi(note)) * (0.55 + 0.25 * rng.random()))
        t0 += dur
        i += 1
    mixd = 0.55 * lowpass(pads, 1800) + 0.32 * lowpass(reverb(keys, mix=0.35), 5000) + 0.35 * lowpass(low, 400)
    mixd = reverb(mixd, secs=1.6, mix=0.15, seed=5)[: int(seconds * SR)]
    fade = int(1.5 * SR)
    mixd[:fade] *= np.linspace(0, 1, fade)
    mixd[-fade:] *= np.linspace(1, 0, fade)
    return (mixd / (np.abs(mixd).max() + 1e-9) * 0.7).astype(np.float32)


if __name__ == "__main__":
    out = sys.argv[1]
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    y = build(secs)
    sf.write(out, np.stack([y, y], 1), SR)
    print(out, secs)
