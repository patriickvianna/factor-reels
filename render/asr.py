"""Conferência da fala: o robô "ouve" a voz gerada (faster-whisper, MIT) e compara com o roteiro.

Se a voz engolir ou trocar palavras demais, o vídeo é barrado. Números são convertidos para
palavras dos dois lados antes de comparar ("R$ 349" e "trezentos e quarenta e nove reais" contam igual).
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

import script as scripts

MAX_WER = float(os.environ.get("REELS_MAX_WER", "0.30"))
_model = None


def _norm(text: str) -> list[str]:
    t = scripts.speakable(text).lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return [w for w in t.split() if w not in {"e", "a", "o", "de"}]


def wer(ref: list[str], hyp: list[str]) -> float:
    if not ref:
        return 0.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1] / len(ref)


def check(voice_wav: Path, script: dict) -> dict:
    global _model
    from faster_whisper import WhisperModel
    if _model is None:
        _model = WhisperModel(os.environ.get("REELS_ASR_MODEL", "small"), device="cpu", compute_type="int8")
    import subprocess
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(voice_wav), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    samples = np.frombuffer(pcm, dtype=np.float32)
    segs, _ = _model.transcribe(samples, language="pt", beam_size=3, vad_filter=False, condition_on_previous_text=False)
    heard = " ".join(s.text.strip() for s in segs)
    ref = " ".join(ln["say"] for sc in script["scenes"] for ln in sc["lines"])
    score = round(wer(_norm(ref), _norm(heard)), 3)
    return {"wer": score, "ouvido": heard[:600], "ok": score <= MAX_WER}
