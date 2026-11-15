"""Robô de Reels da Factor Ofertas (roda no GitHub Actions).

1. Entra no porteiro do Supabase com o token do próprio GitHub (sem senha guardada).
2. Pega até 2 Reels da fila, monta roteiro, voz, som e imagem, confere a qualidade.
3. Publica o MP4 (com música e só com voz) e a capa como Release deste repositório.
4. Avisa o Supabase (pronto ou falha). Uma falha volta para a fila; na 3ª vira item em Prioridades.
5. Apaga os vídeos com mais de 14 dias.

Teste local sem fila: python main.py --local alerta   (usa test/jobs.json)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import asr  # noqa: E402
import audio  # noqa: E402
import script as scripts  # noqa: E402
import tts  # noqa: E402
import video  # noqa: E402

FN_URL = os.environ.get("FN_URL", "https://fojvvrtctfowdhdgmske.supabase.co/functions/v1/reels-runner")
REPO = os.environ.get("GITHUB_REPOSITORY", "patriickvianna/factor-reels")
MUSIC_DIR = ROOT / "music" / "files"


def oidc_token() -> str:
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + "&audience=factor-reels"
    req = urllib.request.Request(url, headers={"Authorization": "bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["value"]


def api(action: str, **body) -> dict:
    data = json.dumps({"action": action, **body}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(FN_URL, data=data, method="POST", headers={
                "Content-Type": "application/json", "Authorization": "Bearer " + oidc_token()})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    return {}


def pick_music(mood: str, seed: int) -> tuple[Path | None, dict | None]:
    manifest = ROOT / "music" / "manifest.json"
    if not manifest.exists():
        return None, None
    tracks = [t for t in json.loads(manifest.read_text()) if (MUSIC_DIR / t["file"]).exists()]
    if not tracks:
        return None, None
    same = [t for t in tracks if t["mood"] == mood] or tracks
    t = same[seed % len(same)]
    return MUSIC_DIR / t["file"], t


def sh(*args: str) -> str:
    p = subprocess.run(list(args), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{args[0]} falhou: {p.stderr[-800:]}")
    return p.stdout


def remux_voice_only(video_mp4: Path, voice_wav: Path, out: Path) -> None:
    sh("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_mp4), "-i", str(voice_wav),
       "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
       "-movflags", "+faststart", "-shortest", str(out))


def produce(job: dict, work: Path) -> dict:
    """Roteiro -> voz -> som -> imagem -> conferência. Devolve os arquivos e as medidas."""
    rid = int(job["id"])
    s = scripts.build(job)
    tl = tts.narrate(s, job.get("voice") or "pf_dora", work / "voice.wav")
    dur = tl["duration"]
    fala = asr.check(work / "voice.wav", s) if os.environ.get("REELS_ASR", "1") == "1" else None
    if fala and not fala["ok"] and os.environ.get("REELS_ASR_ENFORCE", "0") == "1":
        raise audio.QualityError(f"a voz não ficou clara (erro de {fala['wer']:.0%}): ouvi “{fala['ouvido'][:160]}”")
    music, track = pick_music(s["mood"], rid) if job.get("with_music", True) else (None, None)
    m = audio.master(work / "voice.wav", music, dur, work / "audio")
    a_final = audio.check(m["final"], dur, "som com música")
    a_voice = audio.check(m["voice_only"], dur, "som só com voz")
    mp4 = work / f"reel-{rid}.mp4"
    cover = work / f"reel-{rid}-capa.jpg"
    info = video.render(s, tl, m["final"], mp4, cover, work / "frames")
    video.check(info, dur)
    mp4_voice = work / f"reel-{rid}-so-voz.mp4"
    remux_voice_only(mp4, m["voice_only"], mp4_voice)
    video.check(video.probe(mp4_voice), dur)
    if not cover.exists():
        raise audio.QualityError("capa não foi gerada")
    s["timeline"] = tl
    s["music"] = track
    return {"script": s, "files": [mp4, mp4_voice, cover], "duration": dur,
            "audio": {"com_musica": a_final, "so_voz": a_voice, "musica": track and track["title"], "fala": fala}, "video": info}


def publish(rid: int, attempt: int, files: list[Path], title: str) -> tuple[str, dict]:
    tag = f"reel-{rid}-{attempt}-{int(time.time())}"
    sh("gh", "release", "create", tag, *map(str, files), "--repo", REPO, "--title", f"Reels #{rid}: {title}"[:120],
       "--notes", "Gerado pelo robô da Factor Ofertas. Apagado automaticamente 14 dias depois.", "--latest=false")
    # Refazer: apaga a versão anterior deste mesmo Reels (não deixa vídeo velho ocupando espaço)
    try:
        old = [ln.split("\t")[2] for ln in sh("gh", "release", "list", "--repo", REPO, "--limit", "200").splitlines() if "\t" in ln]
        for t in old:
            if t.startswith(f"reel-{rid}-") and t != tag:
                sh("gh", "release", "delete", t, "--repo", REPO, "--yes", "--cleanup-tag")
    except RuntimeError as e:
        print("não consegui apagar a versão anterior:", e)
    base = f"https://github.com/{REPO}/releases/download/{tag}/"
    return tag, {"video_url": base + files[0].name, "voice_url": base + files[1].name, "cover_url": base + files[2].name}


def cleanup() -> None:
    items = api("cleanup").get("items") or []
    done = []
    for it in items:
        try:
            sh("gh", "release", "delete", it["tag"], "--repo", REPO, "--yes", "--cleanup-tag")
            done.append(it["id"])
        except RuntimeError as e:
            if "release not found" in str(e).lower() or "not found" in str(e).lower():
                done.append(it["id"])
            else:
                print("limpeza falhou:", it, e)
    if done:
        print("removidos:", api("removed", ids=done))


def run_queue() -> int:
    cleanup()
    jobs = api("claim", limit=int(os.environ.get("REELS_LIMIT", "3"))).get("jobs") or []
    print(f"{len(jobs)} Reels na vez")
    failures = 0
    for job in jobs:
        rid = int(job["id"])
        started = datetime.now(timezone.utc).isoformat()
        t0 = time.time()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out = produce(job, Path(tmp))
                tag, urls = publish(rid, int(job.get("attempt", 1)), out["files"], out["script"]["title"])
            result = {"ok": True, "script": out["script"], "caption": out["script"]["caption"], "hashtags": out["script"]["hashtags"],
                      "duration_s": round(out["duration"], 2), "audio": {**out["audio"], "video": out["video"], "render_s": round(time.time() - t0)},
                      "release_tag": tag, **urls}
            print(f"Reels #{rid} pronto em {time.time() - t0:.0f}s:", urls["video_url"], out["audio"])
        except Exception as e:  # falha: volta para a fila (até 3 tentativas)
            failures += 1
            tb = traceback.format_exc()
            print(tb)
            kind = "qualidade" if isinstance(e, audio.QualityError) else "erro"
            result = {"ok": False, "error": f"[{kind}] {e}"[:600] + "\n" + tb[-280:]}
        print(api("done", id=rid, result=result, started_at=started))
    return 1 if failures and failures == len(jobs) else 0


def run_local(kind: str) -> int:
    job = json.loads((ROOT / "test" / "jobs.json").read_text())[kind]
    out_dir = ROOT / "out"
    out_dir.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp())
    out = produce(job, work)
    for f in out["files"]:
        f.replace(out_dir / f.name)
    (out_dir / f"reel-{job['id']}.json").write_text(json.dumps(out["script"], ensure_ascii=False, indent=1))
    print(json.dumps(out["audio"], ensure_ascii=False), out["video"])
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--local":
        sys.exit(run_local(sys.argv[2]))
    sys.exit(run_queue())
