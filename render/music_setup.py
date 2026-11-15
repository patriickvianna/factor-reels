"""Monta a biblioteca de música dos Reels (roda uma vez no GitHub Actions, quando music/sources.json muda).

Fonte: FreePD.com, músicas em domínio público (CC0 1.0): uso comercial liberado, sem crédito obrigatório.
Para cada categoria, baixa as primeiras faixas que passam no filtro (duração e volume), etiqueta com o clima
e guarda os MP3 como anexos do Release "musica" deste repositório (fora do git, para o repositório não crescer).
O arquivo music/manifest.json lista o que existe; o robô escolhe a faixa pelo clima de cada formato.
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
UA = {"User-Agent": "Mozilla/5.0 (factor-reels music setup)"}


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def probe(path: Path) -> tuple[float, float]:
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, check=True).stdout.strip())
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    i = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])
    return d, i


def main() -> int:
    cfg = json.loads((ROOT / "music" / "sources.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    home = cfg.get("home", "https://freepd.com/")
    home_html = get(home).decode("utf-8", "ignore")
    pages = sorted({urllib.parse.urljoin(home, h) for h in re.findall(r"""href=["']([^"'#?]+)["']""", home_html)
                    if urllib.parse.urljoin(home, h).startswith(home) and not h.lower().endswith(".mp3")})
    print("páginas no site:", ", ".join(x.replace(home, "/") for x in pages)[:1500])
    for cat in cfg["categories"]:
        page = next((x for x in pages if cat["keyword"] in x.rsplit("/", 1)[-1].lower()), None)
        if not page:
            print(cat["mood"], ": nenhuma página com", cat["keyword"])
            continue
        cat["page"] = page
        html = get(page).decode("utf-8", "ignore")
        links = []
        for m in re.findall(r"""(?:href|src)=["']([^"']+\.mp3)["']""", html, re.I):
            u = urllib.parse.urljoin(cat["page"], m)
            if u not in links:
                links.append(u)
        print(cat["mood"], "->", len(links), "faixas na página")
        skip = {s.lower() for s in cat.get("skip", [])}
        got = 0
        for u in links:
            if got >= cat["take"]:
                break
            title = urllib.parse.unquote(u.rsplit("/", 1)[-1])[:-4]
            if title.lower() in skip:
                continue
            fname = f"{cat['mood']}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}.mp3"
            dst = OUT / fname
            try:
                dst.write_bytes(get(u))
                dur, lufs = probe(dst)
            except Exception as e:  # faixa quebrada: pula
                print("  pulei", title, e)
                dst.unlink(missing_ok=True)
                continue
            if dur < cfg.get("min_seconds", 50) or lufs < -32:
                print(f"  pulei {title}: {dur:.0f}s, {lufs} LUFS")
                dst.unlink(missing_ok=True)
                continue
            manifest.append({"file": fname, "title": title, "mood": cat["mood"], "duration": round(dur, 1), "lufs": lufs,
                             "source": u, "license": "CC0 1.0 (FreePD.com)"})
            got += 1
            print(f"  ok {title}: {dur:.0f}s, {lufs} LUFS")
    if len(manifest) < 4:
        print("poucas faixas encontradas; biblioteca não foi trocada")
        return 1
    (ROOT / "music" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print(len(manifest), "faixas na biblioteca")
    return 0


if __name__ == "__main__":
    sys.exit(main())
