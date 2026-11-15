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


def _get_model():
    global _model
    from faster_whisper import WhisperModel
    if _model is None:
        _model = WhisperModel(os.environ.get("REELS_ASR_MODEL", "small"), device="cpu", compute_type="int8")
    return _model


def _to16k(audio_24k):
    import numpy as np
    a = np.asarray(audio_24k, dtype=np.float32)
    idx = np.round(np.arange(0, a.size, 24000 / 16000)).astype(int)
    return a[idx[idx < a.size]]


def hear_line(audio_24k, text: str) -> tuple[float, list[dict]]:
    """Ouve uma fala só: devolve o erro (para gerar de novo a frase embolada) e o instante de cada palavra ouvida."""
    segs, _ = _get_model().transcribe(_to16k(audio_24k), language="pt", beam_size=3, vad_filter=False,
                                      condition_on_previous_text=False, word_timestamps=True)
    words = [{"w": w.word.strip(), "start": float(w.start), "end": float(w.end)} for s in segs for w in (s.words or [])]
    heard = " ".join(w["w"] for w in words)
    return wer(_norm(text), _norm(heard)), words


def line_wer(audio_24k, text: str) -> float:
    return hear_line(audio_24k, text)[0]


def align(tokens: list[str], heard: list[dict], dur: float) -> list[dict]:
    """Dá a cada palavra da legenda o tempo em que ela foi dita.

    A legenda e a fala nem sempre têm as mesmas palavras ("R$ 169" vira "cento e sessenta e nove reais"),
    então as duas viram a forma falada e são casadas palavra a palavra. O que não casar é distribuído
    entre os vizinhos pelo tamanho."""
    import difflib
    ref, owner = [], []
    for i, t in enumerate(tokens):
        for w in _norm(t):
            ref.append(w); owner.append(i)
    hyp, hyp_t = [], []
    for h in heard:
        for w in _norm(h["w"]):
            hyp.append(w); hyp_t.append((h["start"], h["end"]))
    st: list = [None] * len(tokens)
    en: list = [None] * len(tokens)
    sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            i, (s0, e0) = owner[blk.a + k], hyp_t[blk.b + k]
            st[i] = s0 if st[i] is None else min(st[i], s0)
            en[i] = e0 if en[i] is None else max(en[i], e0)
    # mantém a ordem (tempo nunca volta) e preenche os buracos
    last = 0.0
    for i in range(len(tokens)):
        if st[i] is not None and st[i] < last:
            st[i] = en[i] = None
        elif st[i] is not None:
            last = st[i]
    weight = [max(1, len(re.sub(r"[^\wÀ-ú%$]", "", t))) + 2 for t in tokens]
    i = 0
    while i < len(tokens):
        if st[i] is not None:
            i += 1
            continue
        j = i
        while j < len(tokens) and st[j] is None:
            j += 1
        a = en[i - 1] if i > 0 else 0.0
        b = st[j] if j < len(tokens) else dur
        if b < a:
            b = a
        tot = sum(weight[i:j]); acc = 0
        for k in range(i, j):
            st[k] = a + acc / tot * (b - a); acc += weight[k]; en[k] = a + acc / tot * (b - a)
        i = j
    out = []
    for i, t in enumerate(tokens):
        s0 = max(0.0, min(st[i], dur)); e0 = max(s0 + 0.05, min(en[i], dur))
        out.append({"text": t, "start": round(s0, 3), "end": round(e0, 3)})
    return out
