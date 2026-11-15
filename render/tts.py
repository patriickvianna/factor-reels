"""Voz dos Reels.

Duas ferramentas gratuitas:
  - Chatterbox multilíngue (MIT, Resemble AI): voz natural, imita o timbre de uma gravação de referência.
      cb_ptk    -> voz do PTK (voz/ptk.wav)
      cb_dora   -> timbre da Dora (voz/ref-dora.wav)
      cb_padrao -> voz que vem com o modelo
  - Kokoro-82M (Apache 2.0): mais rápida e mais robótica. pf_dora, pm_alex, pm_santa.

Cada fala é gerada separadamente; assim sabemos o início e o fim exatos de cada uma.
Se o Chatterbox cortar uma fala (acontece às vezes), ela é gerada de novo.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000
ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = Path(os.environ.get("KOKORO_DIR", ROOT / "models"))
GAP_LINE = 0.16   # respiro entre falas da mesma cena
GAP_SCENE = 0.32  # respiro entre cenas
SPEED = {"pf_dora": 1.06, "pm_alex": 1.06, "pm_santa": 1.04}
CB_REF = {"cb_ptk": ROOT / "voz" / "ptk.wav", "cb_dora": ROOT / "voz" / "ref-dora.wav", "cb_padrao": None}

_cb = None


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


def _espeak(text: str) -> np.ndarray:
    """Só para testes locais sem os modelos (TTS_ENGINE=espeak). Nunca usado em produção."""
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["espeak-ng", "-v", "pt-br", "-s", "165", "-w", f"{d}/a.wav", text], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{d}/a.wav", "-ar", str(SR), "-ac", "1", f"{d}/b.wav"], check=True)
        data, _ = sf.read(f"{d}/b.wav", dtype="float32")
    return data


def _kokoro_batch(texts: list[str], voice: str) -> list[np.ndarray]:
    """Kokoro roda num ambiente Python separado (KOKORO_PY), porque usa outra versão do numpy."""
    py = os.environ.get("KOKORO_PY", sys.executable)
    with tempfile.TemporaryDirectory() as d:
        Path(d, "in.json").write_text(json.dumps({"texts": texts, "voice": voice, "speed": SPEED.get(voice, 1.05),
                                                  "model": str(MODEL_DIR)}, ensure_ascii=False))
        code = (
            "import json,sys,soundfile as sf;from kokoro_onnx import Kokoro;j=json.load(open(sys.argv[1]+'/in.json'));"
            "k=Kokoro(j['model']+'/kokoro-v1.0.onnx',j['model']+'/voices-v1.0.bin');"
            "[sf.write(f\"{sys.argv[1]}/{i}.wav\",k.create(t,voice=j['voice'],speed=j['speed'],lang='pt-br')[0],24000) for i,t in enumerate(j['texts'])]"
        )
        subprocess.run([py, "-c", code, d], check=True)
        return [sf.read(f"{d}/{i}.wav", dtype="float32")[0] for i in range(len(texts))]


def _chatterbox(text: str, voice: str, attempt: int) -> np.ndarray:
    global _cb
    import torch
    if _cb is None:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        torch.set_num_threads(max(1, os.cpu_count() or 4))
        _cb = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
        _cb._ref = None
    ref = CB_REF.get(voice)
    if voice == "cb_ptk" and (ref is None or not ref.exists()):
        raise RuntimeError("a gravação de referência da voz do PTK (voz/ptk.wav) ainda não está no repositório")
    if _cb._ref != (str(ref) if ref else None):  # prepara o timbre só quando muda
        if ref:
            _cb.prepare_conditionals(str(ref), exaggeration=0.55)
        else:
            _cb = None
            return _chatterbox(text, voice, attempt)
        _cb._ref = str(ref)
    torch.manual_seed(1234 + attempt)
    w = _cb.generate(text, language_id="pt", exaggeration=0.55, cfg_weight=0.5, temperature=0.7 if attempt == 0 else 0.6)
    return w.squeeze(0).numpy().astype("float32")


def _ok_length(audio: np.ndarray, text: str) -> bool:
    """Fala cortada ou arrastada: duração fora do esperado para o tamanho do texto."""
    dur = audio.size / SR
    n = len(text)
    return 0.035 * n <= dur <= 0.16 * n + 1.2


def synth_all(texts: list[str], voice: str) -> list[np.ndarray]:
    if os.environ.get("TTS_ENGINE") == "espeak":
        raw = [_espeak(t) for t in texts]
    elif voice.startswith("cb_"):
        raw = []
        for t in texts:
            a = _trim(_chatterbox(t, voice, 0))
            tries = 1
            while not _ok_length(a, t) and tries < 3:
                a = _trim(_chatterbox(t, voice, tries))
                tries += 1
            raw.append(a)
    else:
        import roteiro
        raw = _kokoro_batch([roteiro.respell(t) for t in texts], voice)
    out = []
    for t, a in zip(texts, raw):
        a = _trim(np.asarray(a, dtype="float32"))
        if a.size < SR * 0.15 or not np.isfinite(a).all():
            raise RuntimeError(f"voz vazia ou inválida para: {t!r}")
        out.append(a)
    return out


def narrate(script: dict, voice: str, out_wav: Path, lead_in: float = 0.25, tail: float = 0.7) -> dict:
    """Gera a narração inteira e devolve os tempos de cada cena e de cada fala (em segundos)."""
    flat = [ln["say"] for sc in script["scenes"] for ln in sc["lines"]]
    audios = iter(synth_all(flat, voice))
    chunks: list[np.ndarray] = [np.zeros(int(lead_in * SR), dtype="float32")]
    t = lead_in
    timeline = []
    for si, scene in enumerate(script["scenes"]):
        s_start = t if si else 0.0
        lines = []
        for li, ln in enumerate(scene["lines"]):
            a = next(audios)
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
