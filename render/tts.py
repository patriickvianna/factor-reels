"""Voz dos Reels: Kokoro-82M (Apache 2.0) rodando em CPU via ONNX.

Cada fala é gerada separadamente; assim sabemos o início e o fim exatos de cada uma
(as legendas e as animações seguem esses tempos, sem adivinhação).
Vozes em português do Brasil: pf_dora (feminina), pm_alex e pm_santa (masculinas).
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000
MODEL_DIR = Path(os.environ.get("KOKORO_DIR", Path(__file__).resolve().parent.parent / "models"))
GAP_LINE = 0.14   # respiro entre falas da mesma cena
GAP_SCENE = 0.30  # respiro entre cenas
SPEED = {"pf_dora": 1.06, "pm_alex": 1.06, "pm_santa": 1.04}

_kokoro = None


def _engine():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
    return _kokoro


def _espeak(text: str) -> np.ndarray:
    """Só para testes locais sem o modelo (TTS_ENGINE=espeak). Nunca usado em produção."""
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        subprocess.run(["espeak-ng", "-v", "pt-br", "-s", "165", "-w", f.name, text], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f.name, "-ar", str(SR), "-ac", "1", f.name + ".r.wav"], check=True)
        data, _ = sf.read(f.name + ".r.wav", dtype="float32")
        os.unlink(f.name + ".r.wav")
    return data


def _trim(x: np.ndarray, thr_db: float = -45.0, pad: float = 0.03) -> np.ndarray:
    """Corta silêncio do começo e do fim, deixando 30 ms de folga."""
    if x.size == 0:
        return x
    thr = 10 ** (thr_db / 20)
    idx = np.where(np.abs(x) > thr)[0]
    if idx.size == 0:
        return x[:0]
    p = int(pad * SR)
    return x[max(0, idx[0] - p): min(x.size, idx[-1] + p)]


def synth(text: str, voice: str) -> np.ndarray:
    if os.environ.get("TTS_ENGINE") == "espeak":
        audio = _espeak(text)
    else:
        samples, sr = _engine().create(text, voice=voice, speed=SPEED.get(voice, 1.05), lang="pt-br")
        audio = np.asarray(samples, dtype="float32")
        if sr != SR:
            raise RuntimeError(f"taxa inesperada da voz: {sr}")
    audio = _trim(audio)
    if audio.size < SR * 0.15:
        raise RuntimeError(f"voz vazia ou curta demais para: {text!r}")
    if not np.isfinite(audio).all():
        raise RuntimeError("voz com valores inválidos")
    return audio


def narrate(script: dict, voice: str, out_wav: Path, lead_in: float = 0.25, tail: float = 0.6) -> dict:
    """Gera a narração inteira e devolve os tempos de cada cena e de cada fala (em segundos)."""
    chunks: list[np.ndarray] = [np.zeros(int(lead_in * SR), dtype="float32")]
    t = lead_in
    timeline = []
    for si, scene in enumerate(script["scenes"]):
        s_start = t if si else 0.0
        lines = []
        for li, ln in enumerate(scene["lines"]):
            a = synth(ln["say"], voice)
            dur = a.size / SR
            lines.append({"text": ln["text"], "start": round(t, 3), "end": round(t + dur, 3)})
            chunks.append(a)
            t += dur
            gap = GAP_LINE if li < len(scene["lines"]) - 1 else (GAP_SCENE if si < len(script["scenes"]) - 1 else tail)
            chunks.append(np.zeros(int(gap * SR), dtype="float32"))
            t += gap
        timeline.append({"start": round(s_start, 3), "end": round(t, 3), "lines": lines})
    audio = np.concatenate(chunks)
    sf.write(out_wav, audio, SR, subtype="PCM_16")
    return {"scenes": timeline, "duration": round(audio.size / SR, 3)}
