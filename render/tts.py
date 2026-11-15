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
_LAST_HEARD: list = []


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


def synth_all(texts: list[str], voice: str | list[str]) -> list[np.ndarray]:
    """Gera cada fala. `voice` pode ser uma voz só ou uma lista (uma voz por fala, para diálogos)."""
    voices = voice if isinstance(voice, list) else [voice] * len(texts)
    if len(set(voices)) > 1:
        out: list = [None] * len(texts)
        for v in dict.fromkeys(voices):
            idx = [i for i, x in enumerate(voices) if x == v]
            for i, a in zip(idx, synth_all([texts[i] for i in idx], v)):
                out[i] = a
        return out
    voice = voices[0] if voices else "cb_dora"
    if os.environ.get("TTS_ENGINE") == "espeak":
        raw = [_espeak(t) for t in texts]
    elif voice.startswith("cb_"):
        import asr
        raw = []
        for t in texts:
            # até 3 tentativas: fica a que a conferência (Whisper) ouviu mais certo
            best, best_w, best_heard = None, 9.0, None
            for tries in range(3):
                a = _trim(_chatterbox(t, voice, tries))
                if not _ok_length(a, t):
                    continue
                try:
                    w, heard = asr.hear_line(a, t)
                except Exception:
                    w, heard = 0.0, None
                if w < best_w:
                    best, best_w, best_heard = a, w, heard
                if w <= 0.25:
                    break
            if best is None:
                raise RuntimeError(f"a voz cortou a fala: {t!r}")
            raw.append(best)
            _LAST_HEARD.append(best_heard)
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


def _heard_words(audio: np.ndarray, text: str):
    """Palavras ouvidas pelo Whisper com o instante de cada uma (None se a conferência estiver desligada)."""
    if os.environ.get("REELS_ASR") == "0":
        return None
    try:
        import asr
        return asr.hear_line(audio, text)[1]
    except Exception as e:
        print(f"  aviso: tempo das palavras indisponível ({e})")
        return None


def narrate(script: dict, voice: str, out_wav: Path, lead_in: float = 0.25, tail: float = 0.7) -> dict:
    """Gera a narração inteira e devolve os tempos de cada cena, de cada fala e de cada palavra (em segundos).

    Numa história, a fala pode trazer "voz": "outra" para o segundo personagem falar com a outra voz."""
    import asr
    other = {"cb_dora": "cb_padrao", "cb_padrao": "cb_dora", "pf_dora": "pm_alex", "pm_alex": "pf_dora"}.get(voice, voice)
    flat = [ln for sc in script["scenes"] for ln in sc["lines"]]
    voices = [other if ln.get("voz") == "outra" else voice for ln in flat]
    _LAST_HEARD.clear()
    audios_l = synth_all([ln["say"] for ln in flat], voices if len(set(voices)) > 1 else voice)
    # o Chatterbox já foi ouvido ao escolher a melhor tentativa; as outras vozes são ouvidas agora
    heard_cache = {}
    if len(_LAST_HEARD) == len(flat) and not any(v != voice for v in voices):
        heard_cache = dict(enumerate(_LAST_HEARD))
    audios = iter(enumerate(audios_l))
    chunks: list[np.ndarray] = [np.zeros(int(lead_in * SR), dtype="float32")]
    t = lead_in
    timeline = []
    for si, scene in enumerate(script["scenes"]):
        s_start = t if si else 0.0
        lines = []
        for li, ln in enumerate(scene["lines"]):
            k, a = next(audios)
            dur = a.size / SR
            heard = heard_cache.get(k) if k in heard_cache else _heard_words(a, ln["say"])
            line = {"text": ln["text"], "start": round(t, 3), "end": round(t + dur, 3)}
            if ln.get("voz"):
                line["voz"] = ln["voz"]
            if heard:
                toks = caption_tokens(ln["text"])
                line["words"] = [{"text": w["text"], "start": round(t + w["start"], 3), "end": round(t + w["end"], 3)}
                                 for w in asr.align(toks, heard, dur)]
            lines.append(line)
            chunks.append(a)
            t += dur
            gap = GAP_LINE if li < len(scene["lines"]) - 1 else (GAP_SCENE if si < len(script["scenes"]) - 1 else tail)
            chunks.append(np.zeros(int(gap * SR), dtype="float32"))
            t += gap
        timeline.append({"start": round(s_start, 3), "end": round(t, 3), "lines": lines})
    audio = np.concatenate(chunks)
    sf.write(out_wav, audio, SR, subtype="PCM_16")
    return {"scenes": timeline, "duration": round(audio.size / SR, 3)}


def caption_tokens(text: str) -> list[str]:
    """Palavras da legenda, com "R$" colado no valor."""
    toks: list[str] = []
    for w in text.split():
        if toks and toks[-1] in ("R$", "US$"):
            toks[-1] = f"{toks[-1]} {w}"
        else:
            toks.append(w)
    return toks
