"""Prévia rápida: tira fotos de alguns instantes da cena, sem montar o vídeo (uso em testes)."""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import video

def shots(script, timeline, times, out_dir: Path, prefix="f"):
    out_dir.mkdir(parents=True, exist_ok=True)
    page_file = video.HERE / ".scene-preview.html"
    page_file.write_text(video._page_html(script, timeline), encoding="utf-8")
    files = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(page_file.as_uri()); pg.evaluate("() => window.ready")
        for t in times:
            pg.evaluate("t => window.seek(t)", t)
            f = out_dir / f"{prefix}_{t:05.2f}.png"; pg.screenshot(path=str(f)); files.append(f)
        b.close()
    page_file.unlink(missing_ok=True)
    return files
