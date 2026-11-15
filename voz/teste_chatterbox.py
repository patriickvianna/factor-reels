"""Teste de voz: Chatterbox multilíngue (MIT), em português, na CPU do GitHub."""
import json, sys, time
from pathlib import Path
import torch, torchaudio
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
torch.set_num_threads(4)
out = Path(sys.argv[1])
refs = {"padrao": None, "ref-dora": str(out / "ref-dora.wav")}
for p in Path("voz").glob("ptk.*"):
    refs["ptk"] = str(p)
t0 = time.time(); m = ChatterboxMultilingualTTS.from_pretrained(device="cpu"); print(f"modelo carregado em {time.time()-t0:.0f}s")
frases = json.load(open("voz/textos.json"))["frases"]
for nome, ref in refs.items():
    for ex in (0.5,):
        t0 = time.time(); total = 0
        for f in frases:
            w = m.generate(f["texto"], language_id="pt", audio_prompt_path=ref, exaggeration=ex, cfg_weight=0.5, temperature=0.7)
            torchaudio.save(str(out / f"chatterbox-{nome}-{f['id']}.wav"), w, m.sr); total += w.shape[-1] / m.sr
        el = time.time() - t0
        print(f"chatterbox {nome}: {total:.1f}s de áudio em {el:.0f}s (x{el/total:.1f} do tempo real)")
