"""Amostra do Reels explicativo 3D (GUT #112): gera a narração, o instante de cada palavra e os cues dos movimentos.

Uso local: python render/explica_amostra.py airfryer out/explica   →  out/explica/props.json + voz.wav

Voz (EXPLICA_VOZ):
  - cb_dora (padrão, decisão do PTK em 27/11): Chatterbox com o timbre da Dora; o instante de cada palavra
    vem do Whisper (asr.py), que ouve a fala gerada. Roda no GitHub (modelos em cache).
  - pm_alex/pf_dora: Kokoro (reserva, sotaque de estrangeiro). Cada trecho entre vírgulas/pontos é falado
    separado e, dentro do trecho, o tempo é dividido pelo nº de fonemas de cada palavra.
Música: trilha "curiosidade" gerada em código (trilha_explica.py), uns 12 dB abaixo da voz e abaixando
mais quando o locutor fala. Volume final de -12 LUFS (o PTK achou -14 baixo).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import audio  # noqa: E402
import trilha_explica  # noqa: E402

SR = 24000
MODEL = os.environ.get("KOKORO_DIR", "/home/claude/models")
VOICE = os.environ.get("EXPLICA_VOZ", "cb_dora")
LUFS = -12.0
SPEED = 1.06

# (legenda, fala). A fala só muda a pronúncia; precisa ter o mesmo nº de palavras da legenda.
# cues: palavra da legenda (sem pontuação, minúscula) → nome do movimento que ela dispara.
TEMAS = {
    "airfryer": {
        "titulo": "Como funciona a air fryer",
        "linhas": [
            ("A air fryer não frita nada. Ela assa com vento quente.", "A ér fráier não frita nada. Ela assa com vento quente.", {"vento": "hook_air"}),
            ("Em cima fica uma resistência, igual à de um forno, que esquenta até 200 graus.",
             "Em cima fica uma resistência, igual à de um forno, que esquenta até duzentos graus.",
             {"em": "corte", "resistência": "coil", "esquenta": "hot"}),
            ("Logo acima, um ventilador gira rápido e empurra o calor para baixo.", None, {"ventilador": "fan", "empurra": "push"}),
            ("O ar desce pelas laterais, bate no fundo e sobe por dentro do cesto.", None, {"desce": "down", "fundo": "bottom", "sobe": "up"}),
            ("Como o cesto é furado, o vento quente passa por todos os lados da comida.", None, {"furado": "holes", "todos": "around"}),
            ("Aí a casca seca e doura, como na fritura, com pouco ou nenhum óleo.", None, {"doura": "brown", "óleo": "oil"}),
            ("Por isso não lote o cesto: sem espaço, o ar não circula e a batata sai murcha.", None,
             {"lote": "crowd", "circula": "block", "murcha": "soggy"}),
            ("Salva para lembrar e segue a Factor para entender as coisas da sua casa.", None, {"salva": "end"}),
        ],
    },
}

PAUSE_COMMA = 0.14
PAUSE_STOP = 0.30
PAUSE_LINE = 0.34
LEAD_IN = 0.45
TAIL = 1.4


def _kokoro():
    from kokoro_onnx import Kokoro
    from kokoro_onnx.tokenizer import Tokenizer
    return Kokoro(f"{MODEL}/kokoro-v1.0.onnx", f"{MODEL}/voices-v1.0.bin"), Tokenizer()


def _trim(a: np.ndarray, thr: float = 0.012) -> np.ndarray:
    idx = np.where(np.abs(a) > thr)[0]
    if not len(idx):
        return a
    s = max(0, idx[0] - int(0.015 * SR))
    e = min(len(a), idx[-1] + int(0.03 * SR))
    return a[s:e]


def _pieces(text: str) -> list[tuple[str, str]]:
    """Divide em trechos que terminam em vírgula, ponto ou dois-pontos. Devolve (trecho, pontuação final)."""
    out = []
    for m in re.finditer(r"[^,.:;!?]+[,.:;!?]?", text):
        s = m.group(0).strip()
        if s:
            out.append((s, s[-1] if s[-1] in ",.:;!?" else ""))
    return out


def _norm(w: str) -> str:
    return re.sub(r"[^\wà-úÀ-Ú]", "", w.lower())


def _voz_kokoro(cfg: dict, outdir: Path) -> tuple[Path, list, float]:
    tts, tok = _kokoro()
    chunks: list[np.ndarray] = [np.zeros(int(LEAD_IN * SR), dtype=np.float32)]
    t = LEAD_IN
    lines = []
    for cap, say, _cues in cfg["linhas"]:
        say = say or cap
        cap_pieces, say_pieces = _pieces(cap), _pieces(say)
        assert len(cap_pieces) == len(say_pieces), (cap, say)
        line_words = []
        line_start = t
        for (cp, punct), (sp, _) in zip(cap_pieces, say_pieces):
            cw, sw = cp.split(), sp.split()
            assert len(cw) == len(sw), (cp, sp)
            wav, _ = tts.create(sp, voice=VOICE, speed=SPEED, lang="pt-br")
            wav = _trim(np.asarray(wav, dtype=np.float32))
            dur = len(wav) / SR
            weights = [len(tok.phonemize(_norm(w) or w, lang="pt-br")) + 1.5 for w in sw]
            tot = sum(weights)
            acc = t
            for w, wt in zip(cw, weights):
                d = dur * wt / tot
                line_words.append({"text": w, "start": round(acc, 3), "end": round(acc + d, 3)})
                acc += d
            chunks.append(wav)
            t += dur
            gap = PAUSE_STOP if punct in ".:;!?" else PAUSE_COMMA if punct == "," else 0.05
            chunks.append(np.zeros(int(gap * SR), dtype=np.float32))
            t += gap
        lines.append({"text": cap, "start": round(line_start, 3), "end": line_words[-1]["end"], "words": line_words})
        chunks.append(np.zeros(int(PAUSE_LINE * SR), dtype=np.float32))
        t += PAUSE_LINE
    chunks.append(np.zeros(int(TAIL * SR), dtype=np.float32))
    raw = outdir / "voz_bruta.wav"
    sf.write(raw, np.concatenate(chunks), SR)
    return raw, lines, round(t + TAIL - PAUSE_LINE, 2)


def _voz_chatterbox(cfg: dict, outdir: Path) -> tuple[Path, list, float]:
    import tts
    script = {"scenes": [{"lines": [{"text": cap, "say": say or cap}]} for cap, say, _ in cfg["linhas"]]}
    raw = outdir / "voz_bruta.wav"
    tl = tts.narrate(script, VOICE, raw, lead_in=LEAD_IN, tail=TAIL)
    lines = [ln for sc in tl["scenes"] for ln in sc["lines"]]
    falta = [ln["text"] for ln in lines if not ln.get("words")]
    if falta:
        raise RuntimeError(f"sem o tempo das palavras (Whisper) em: {falta[0]!r}")
    return raw, lines, tl["duration"]


def _mix(raw: Path, duration: float, outdir: Path) -> Path:
    """Voz tratada + trilha baixa que abaixa mais quando o locutor fala; volume final em LUFS."""
    trilha = outdir / "trilha.wav"
    y = trilha_explica.build(duration + 0.5)
    sf.write(trilha, np.stack([y, y], 1), trilha_explica.SR)
    graph = (f"[0:a]{audio.VOICE_CHAIN},apad=whole_dur={duration:.3f}[v];"
             f"[1:a]aresample=48000,loudnorm=I=-26:TP=-8:LRA=7,afade=t=in:st=0:d=1.0,"
             f"afade=t=out:st={max(0.1, duration - 2):.3f}:d=2[m];"
             "[v]asplit=2[vk][vm];"
             "[m][vk]sidechaincompress=threshold=0.03:ratio=3:attack=30:release=450:makeup=1[duck];"
             "[vm][duck]amix=inputs=2:normalize=0:duration=first[mix]")
    pre = outdir / "mix_pre.wav"
    audio._run(["-i", str(raw), "-i", str(trilha), "-filter_complex", graph, "-map", "[mix]", "-t", f"{duration:.3f}",
                "-ac", "2", "-c:a", "pcm_s16le", str(pre)])
    audio.TARGET_I = LUFS
    final = outdir / "voz.wav"
    audio.normalize(pre, final)
    m = audio.measure(final)
    if abs(m["lufs"] - LUFS) > 1.0 or m["true_peak"] > -0.85:
        raise audio.QualityError(f"som fora do padrão: {m['lufs']} LUFS, pico {m['true_peak']} dBTP")
    return final


def build(tema: str, outdir: Path) -> dict:
    cfg = TEMAS[tema]
    outdir.mkdir(parents=True, exist_ok=True)
    raw, lines, duration = (_voz_chatterbox if VOICE.startswith("cb_") else _voz_kokoro)(cfg, outdir)
    cues = {}
    for ln, (_, _, cue_words) in zip(lines, cfg["linhas"]):
        for w in ln["words"]:
            k = _norm(w["text"])
            if k in cue_words and cue_words[k] not in cues:
                cues[cue_words[k]] = w["start"]
    missing = sorted({v for _, _, c in cfg["linhas"] for v in c.values()} - set(cues))
    assert not missing, f"cues sem palavra: {missing}"
    final = _mix(raw, duration, outdir)
    props = {"tema": tema, "titulo": cfg["titulo"], "lines": lines, "cues": cues, "audio_file": str(final.resolve()),
             "audio": "", "duration": duration, "handle": "@factorofertas", "voz": VOICE}
    (outdir / "props.json").write_text(json.dumps(props, ensure_ascii=False, indent=1))
    return props


if __name__ == "__main__":
    p = build(sys.argv[1] if len(sys.argv) > 1 else "airfryer", Path(sys.argv[2] if len(sys.argv) > 2 else "out/explica"))
    print(json.dumps({"duration": p["duration"], "cues": p["cues"], "palavras": sum(len(l["words"]) for l in p["lines"])}, ensure_ascii=False))
