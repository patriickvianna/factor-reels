"""Ouve cada amostra (faster-whisper) e mede quanto do texto foi dito certo (erro por palavra)."""
import json, sys
from pathlib import Path
sys.path.insert(0, "render")
import asr
from faster_whisper import WhisperModel
import numpy as np, subprocess
m = WhisperModel("small", device="cpu", compute_type="int8")
textos = {f["id"]: f["texto"] for f in json.load(open("voz/textos.json"))["frases"]}
out = Path(sys.argv[1]); res = {}
for f in sorted(out.glob("*.wav")):
    if f.name.startswith("ref-"):
        continue
    fid = next((k for k in textos if f.stem.endswith("-" + k)), None)
    if not fid:
        continue
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    segs, _ = m.transcribe(np.frombuffer(pcm, dtype=np.float32), language="pt", beam_size=3, condition_on_previous_text=False)
    heard = " ".join(s.text.strip() for s in segs)
    ref = textos["ingles"] if fid == "ingles_respelado" else textos[fid]
    w = asr.wer(asr._norm(ref), asr._norm(heard))
    voz = f.stem[: -(len(fid) + 1)]
    res.setdefault(voz, []).append(w)
    print(f"{f.stem}: erro {w:.0%} | ouvi: {heard}")
for v, ws in res.items():
    print(f"MÉDIA {v}: {sum(ws)/len(ws):.0%}")
