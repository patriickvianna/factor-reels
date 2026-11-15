"""Som dos Reels: tratamento da voz, música que abaixa sob a voz, volume no padrão e conferência.

Padrão de entrega (o mesmo das plataformas de vídeo curto):
  - volume integrado de -14 LUFS (tolerância de 1 LU)
  - pico verdadeiro no máximo -1 dBTP
  - 48 kHz, AAC 192 kbps
Se o resultado sair fora disso, o vídeo é barrado (QualityError) e não chega ao painel.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

TARGET_I = -14.0
TARGET_TP = -1.0
TARGET_LRA = 11.0
SR_OUT = 48000


class QualityError(RuntimeError):
    pass


def _run(args: list[str]) -> str:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-y", *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg falhou: " + p.stderr[-1500:])
    return p.stderr


def _loudnorm_measure(src: Path, pre: str = "") -> dict:
    chain = (pre + "," if pre else "") + f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json"
    err = _run(["-i", str(src), "-af", chain, "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)
    if not m:
        raise RuntimeError("não consegui medir o volume")
    return json.loads(m.group(0))


def normalize(src: Path, dst: Path, pre: str = "") -> None:
    """Normalização em duas passadas (linear): volume exato sem 'bombear'."""
    m = _loudnorm_measure(src, pre)
    chain = (pre + "," if pre else "") + (
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
        f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
        f"alimiter=limit={10 ** ((TARGET_TP - 0.3) / 20):.4f}:level=disabled:attack=5:release=50"
    )
    _run(["-i", str(src), "-af", chain, "-ar", str(SR_OUT), "-ac", "2", "-c:a", "pcm_s16le", str(dst)])


VOICE_CHAIN = (
    "highpass=f=85,lowpass=f=13500,"
    "equalizer=f=250:t=q:w=1.2:g=-2,"          # tira o 'abafado'
    "equalizer=f=3200:t=q:w=1.0:g=2,"          # presença e clareza
    "deesser=i=0.35:m=0.5:f=0.5,"              # suaviza os 's' chiados
    "acompressor=threshold=-22dB:ratio=3:attack=4:release=90:makeup=3,"
    "aresample=48000"
)


def master(voice_wav: Path, music: Path | None, duration: float, work: Path) -> dict:
    """Gera final.wav (voz + música) e voice.wav (só voz), ambos já no padrão."""
    work.mkdir(parents=True, exist_ok=True)
    v = work / "voice_proc.wav"
    _run(["-i", str(voice_wav), "-af", VOICE_CHAIN + f",apad=whole_dur={duration:.3f}", "-ac", "2", "-c:a", "pcm_s16le", str(v)])

    voice_only = work / "voice_only.wav"
    normalize(v, voice_only, f"afade=t=out:st={max(0.1, duration - 0.35):.3f}:d=0.35")

    final = work / "final.wav"
    if music is None:
        normalize(v, final, f"afade=t=out:st={max(0.1, duration - 0.35):.3f}:d=0.35")
    else:
        fade_out = 1.6
        graph = (
            # música: corta no tamanho, deixa uns 14 dB abaixo da voz e entra/sai suave
            f"[1:a]aresample=48000,atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,"
            f"loudnorm=I=-28:TP=-6:LRA=11,"
            f"afade=t=in:st=0:d=0.6,afade=t=out:st={max(0.1, duration - fade_out):.3f}:d={fade_out}[m];"
            # a voz controla a música: quando ela fala, a música abaixa mais um pouco
            "[0:a]asplit=2[vk][vm];"
            "[m][vk]sidechaincompress=threshold=0.02:ratio=4:attack=20:release=380:makeup=1[duck];"
            "[vm][duck]amix=inputs=2:normalize=0:duration=first[mix]"
        )
        pre_mix = work / "mix.wav"
        _run(["-i", str(v), "-stream_loop", "-1", "-i", str(music), "-filter_complex", graph, "-map", "[mix]",
              "-t", f"{duration:.3f}", "-ac", "2", "-c:a", "pcm_s16le", str(pre_mix)])
        normalize(pre_mix, final)
    return {"final": final, "voice_only": voice_only}


def measure(path: Path) -> dict:
    """Mede o volume (EBU R128), o pico verdadeiro e os silêncios do arquivo final."""
    err = _run(["-i", str(path), "-af", "ebur128=peak=true,silencedetect=n=-50dB:d=1.4", "-f", "null", "-"])
    summary = err[err.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    lra = float(re.search(r"LRA:\s+(-?[\d.]+) LU", summary).group(1))
    tp_m = re.search(r"True peak:\s+Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    tp = float(tp_m.group(1)) if tp_m and tp_m.group(1) != "-inf" else -99.0
    silences = [(float(a), float(b)) for a, b in re.findall(r"silence_start: (-?[\d.]+)[\s\S]*?silence_end: ([\d.]+)", err)]
    return {"lufs": round(i, 2), "true_peak": round(tp, 2), "lra": round(lra, 2), "silences": silences}


def check(path: Path, duration: float, label: str) -> dict:
    m = measure(path)
    problems = []
    if abs(m["lufs"] - TARGET_I) > 1.0:
        problems.append(f"volume {m['lufs']} LUFS (alvo {TARGET_I})")
    if m["true_peak"] > TARGET_TP + 0.15:
        problems.append(f"pico {m['true_peak']} dBTP (máximo {TARGET_TP})")
    inner = [s for s in m["silences"] if s[0] > 0.6 and s[1] < duration - 0.8]
    if inner:
        problems.append(f"silêncio no meio do áudio em {inner[0][0]:.1f}s")
    if problems:
        raise QualityError(f"{label}: " + "; ".join(problems))
    return {k: m[k] for k in ("lufs", "true_peak", "lra")}
