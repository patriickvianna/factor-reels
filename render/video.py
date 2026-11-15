"""Imagem dos Reels: desenha cada quadro da cena (scene.html) no Chromium e monta o MP4 com o FFmpeg.

Mesma técnica do HyperFrames (HTML + quadro a quadro + FFmpeg), sem dependências extras:
a página só muda quando chamamos seek(t), então o resultado é sempre o mesmo.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
W, H, FPS = 1080, 1920, 30


def _page_html(script: dict, timeline: dict) -> str:
    html = (HERE / "scene.html").read_text(encoding="utf-8")
    data = json.dumps({"script": script, "timeline": timeline}, ensure_ascii=False).replace("</", "<\\/")
    return html.replace("<script>\nconst D = window.DATA;", f"<script>window.DATA = {data};</script>\n<script>\nconst D = window.DATA;", 1)


def render(script: dict, timeline: dict, audio: Path, out_mp4: Path, cover_jpg: Path, work: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    page_file = HERE / f".scene-{out_mp4.stem}.html"   # ao lado de fonts/ para achar as fontes
    page_file.write_text(_page_html(script, timeline), encoding="utf-8")
    duration = float(timeline["duration"])
    frames = int(round(duration * FPS))
    enc = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
        "-i", str(audio),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
        "-r", str(FPS), "-g", str(FPS * 2),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(out_mp4)], stdin=subprocess.PIPE)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--disable-web-security", "--allow-file-access-from-files", "--font-render-hinting=none"])
            page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            page.goto(page_file.as_uri(), wait_until="load", timeout=60000)
            info = page.evaluate("() => window.ready")
            if info.get("bad"):
                raise RuntimeError("imagem do produto não carregou: " + ", ".join(info["bad"])[:300])
            cover_t = min(1.6, duration / 3)
            for i in range(frames):
                t = i / FPS
                page.evaluate("t => window.seek(t)", t)
                buf = page.screenshot(type="jpeg", quality=94, full_page=False)
                enc.stdin.write(buf)
                if abs(t - cover_t) < 0.5 / FPS:
                    cover_jpg.write_bytes(buf)
            browser.close()
    finally:
        enc.stdin.close()
        code = enc.wait()
        page_file.unlink(missing_ok=True)
    if code != 0:
        raise RuntimeError("ffmpeg não conseguiu montar o vídeo")
    return probe(out_mp4)


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,sample_rate:format=duration,size",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    return {"width": v["width"], "height": v["height"], "fps": v["r_frame_rate"], "has_audio": a is not None,
            "audio_rate": a and a.get("sample_rate"), "duration": float(j["format"]["duration"]), "bytes": int(j["format"]["size"])}


def check(info: dict, expected: float) -> None:
    from audio import QualityError
    problems = []
    if (info["width"], info["height"]) != (W, H):
        problems.append(f"resolução {info['width']}x{info['height']}")
    if not info["has_audio"]:
        problems.append("vídeo sem áudio")
    if abs(info["duration"] - expected) > 0.25:
        problems.append(f"duração {info['duration']:.2f}s (esperado {expected:.2f}s)")
    if not (6 <= info["duration"] <= 90):
        problems.append(f"duração fora do limite: {info['duration']:.1f}s")
    if info["bytes"] > 60 * 1024 * 1024:
        problems.append("arquivo grande demais")
    if problems:
        raise QualityError("vídeo: " + "; ".join(problems))
