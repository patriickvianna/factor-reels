"""Monta a biblioteca de música dos Reels (roda no GitHub Actions quando music/sources.json muda).

Busca no Openverse (catálogo aberto de mídia) só faixas de MÚSICA com licença CC0 (domínio público):
uso comercial liberado e sem crédito obrigatório. Cada faixa passa por filtro de duração e volume,
recebe a etiqueta de clima (urgente / animada) e vai para o Release "musica" deste repositório
(fora do git, para o repositório não crescer). O arquivo music/manifest.json lista o que existe.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "music" / "files"
UA = {"User-Agent": "factor-reels/1.0 (github.com/patriickvianna/factor-reels)"}
API = "https://api.openverse.org/v1/audio/"


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        return r.read()


def probe(path: Path) -> tuple[float, float]:
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, check=True).stdout.strip())
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    i = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])
    return d, i


def search(q: str, n: int) -> list[dict]:
    """Tenta do filtro mais estrito ao mais solto; sempre só domínio público (cc0 ou pdm)."""
    for extra in ({"category": "music"}, {}):
        params = {"q": q, "license": "cc0,pdm", "page_size": str(n), **extra}
        raw = get(API + "?" + urllib.parse.urlencode(params))
        data = json.loads(raw)
        res = data.get("results", [])
        print(f"   openverse {params} -> {data.get('result_count')} ({len(res)})" + ("" if res else f" {raw[:160]!r}"))
        if res:
            return res
    return []


def main() -> int:
    cfg = json.loads((ROOT / "music" / "sources.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    manifest, seen = [], set()
    for cat in cfg["categories"]:
        got = 0
        for q in cat["queries"]:
            if got >= cat["take"]:
                break
            try:
                results = search(q, 20)
            except Exception as e:
                print(f"busca '{q}' falhou: {e}")
                continue
            print(f"{cat['mood']} · '{q}': {len(results)} resultados")
            for r in results:
                if got >= cat["take"]:
                    break
                url, title = r.get("url"), (r.get("title") or "faixa").strip()
                if title in cfg.get("skip_titles", []):
                    continue
                if not url or r.get("license") not in ("cc0", "pdm") or url in seen:
                    continue
                if (r.get("duration") or 0) and r["duration"] < cfg.get("min_seconds", 50) * 1000:
                    continue
                seen.add(url)
                ext = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".mp3"
                slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "faixa"
                raw = OUT / f"tmp{ext}"
                fname = f"{cat['mood']}-{slug}.mp3"
                dst = OUT / fname
                try:
                    raw.write_bytes(get(url))
                    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw), "-ac", "2", "-ar", "48000",
                                    "-b:a", "192k", str(dst)], check=True)
                    raw.unlink(missing_ok=True)
                    dur, lufs = probe(dst)
                except Exception as e:
                    print("  pulei", title, e)
                    raw.unlink(missing_ok=True)
                    dst.unlink(missing_ok=True)
                    continue
                if dur < cfg.get("min_seconds", 50) or lufs < -30:
                    print(f"  pulei {title}: {dur:.0f}s, {lufs} LUFS")
                    dst.unlink(missing_ok=True)
                    continue
                manifest.append({"file": fname, "title": title, "mood": cat["mood"], "duration": round(dur, 1), "lufs": lufs,
                                 "creator": r.get("creator"), "source": r.get("foreign_landing_url") or url, "provider": r.get("source"),
                                 "license": "domínio público (" + str(r.get("license")).upper() + ")"})
                got += 1
                print(f"  ok {title} ({r.get('source')}): {dur:.0f}s, {lufs} LUFS")
    if len(manifest) < 4:
        print("poucas faixas encontradas; biblioteca não foi trocada")
        return 1
    (ROOT / "music" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print(len(manifest), "faixas na biblioteca")
    return 0


if __name__ == "__main__":
    sys.exit(main())
