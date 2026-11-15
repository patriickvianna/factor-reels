"""Teste de voz: Kokoro (atual). Gera um WAV por frase e um de referência (12 s) para o Chatterbox."""
import json, sys, time
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
frases = json.load(open("voz/textos.json"))["frases"]
for voz in ("pf_dora", "pm_alex"):
    t0 = time.time(); total = 0
    for f in frases:
        a, sr = k.create(f["texto"], voice=voz, speed=1.06, lang="pt-br")
        sf.write(out / f"kokoro-{voz}-{f['id']}.wav", a, sr); total += len(a) / sr
    print(f"kokoro {voz}: {total:.1f}s de áudio em {time.time()-t0:.1f}s")
# referência (frases 1, 2 e 5 juntas) para clonar o timbre no Chatterbox
ref = [k.create(frases[i]["texto"], voice="pf_dora", speed=1.0, lang="pt-br")[0] for i in (0, 1)]
sf.write(out / "ref-dora.wav", np.concatenate([np.concatenate([r, np.zeros(6000, dtype=r.dtype)]) for r in ref]), 24000)
