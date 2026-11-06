"""Merakit video: suara (edge-tts), klip stok (Pexels), teks, lalu digabung dengan ffmpeg."""
import asyncio
import os
import pathlib
import random
import re
import shutil
import subprocess
import tempfile
import textwrap

import requests

PEXELS_URL = "https://api.pexels.com/videos/search"


def _run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Perintah gagal: {' '.join(cmd[:3])} ...\n{r.stderr[-1500:]}")
    return r.stdout


def _duration(path):
    out = _run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)]
    )
    return float(out.strip())


def _tts(text, voice, rate, dest, fallback_lang):
    try:
        import edge_tts

        asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(dest)))
        if dest.exists() and dest.stat().st_size > 1000:
            return
    except Exception as e:
        print("edge-tts gagal, pakai gTTS:", e)
    from gtts import gTTS

    gTTS(text=text, lang=fallback_lang).save(str(dest))


def _fetch_clip(query, orientation, dest, key):
    if not key:
        return False
    try:
        r = requests.get(
            PEXELS_URL,
            headers={"Authorization": key},
            params={"query": query, "orientation": orientation, "size": "medium", "per_page": 8},
            timeout=30,
        )
        r.raise_for_status()
        vids = r.json().get("videos", [])
        random.shuffle(vids)
        for v in vids:
            files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
            if not files:
                continue
            files.sort(key=lambda f: abs(min(f["width"], f["height"]) - 1080))
            with requests.get(files[0]["link"], stream=True, timeout=120) as d:
                d.raise_for_status()
                with open(dest, "wb") as fh:
                    for chunk in d.iter_content(1 << 20):
                        fh.write(chunk)
            return True
    except Exception as e:
        print(f"Pexels gagal untuk '{query}': {e}")
    return False


def _chunks(text, max_words):
    out, cur = [], []
    for w in text.split():
        cur.append(w)
        if len(cur) >= max_words or (re.search(r"[.!?,;:]$", w) and len(cur) >= 3):
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def build(data, cfg, out_path):
    """Membuat video dari naskah. Mengembalikan durasi (detik)."""
    v = cfg["video"]
    shorts = v["format"] == "shorts"
    W, H = (1080, 1920) if shorts else (1920, 1080)
    orientation = "portrait" if shorts else "landscape"
    fontsize = 64 if shorts else 54
    wrap = 22 if shorts else 42
    max_words = 6 if shorts else 10
    y_expr = "(h-text_h)*0.72" if shorts else "(h-text_h)*0.88"
    font = v.get("font_file", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    key = os.environ.get("PEXELS_API_KEY", "")

    work = pathlib.Path(tempfile.mkdtemp(prefix="yt_"))
    try:
        parts = []
        for i, sc in enumerate(data["scenes"]):
            audio = work / f"a{i}.mp3"
            _tts(sc["narration"], v["voice"], v.get("voice_rate", "+0%"), audio, v.get("tts_fallback_lang", "id"))
            dur = _duration(audio) + 0.25

            bg = work / f"bg{i}.mp4"
            have_bg = _fetch_clip(sc["query"], orientation, bg, key)

            cs = _chunks(sc["narration"], max_words)
            total = sum(len(c) for c in cs) or 1
            vf = [
                f"scale={W}:{H}:force_original_aspect_ratio=increase",
                f"crop={W}:{H}",
                "setsar=1",
                "fps=30",
            ]
            t = 0.0
            for j, c in enumerate(cs):
                seg = dur * len(c) / total
                tf = work / f"c{i}_{j}.txt"
                tf.write_text(textwrap.fill(c, wrap), encoding="utf-8")
                vf.append(
                    f"drawtext=fontfile={font}:textfile={tf.name}:fontsize={fontsize}:fontcolor=white"
                    f":borderw=6:bordercolor=black:line_spacing=12:x=(w-text_w)/2:y={y_expr}"
                    f":enable='between(t,{t:.2f},{t + seg:.2f})'"
                )
                t += seg

            if have_bg:
                inp = ["-stream_loop", "-1", "-i", bg.name]
            else:
                inp = ["-f", "lavfi", "-i", f"color=c=0x16213e:s={W}x{H}:r=30"]

            seg_out = work / f"s{i}.mp4"
            _run(
                [
                    "ffmpeg", "-y", *inp, "-i", audio.name,
                    "-t", f"{dur:.2f}",
                    "-vf", ",".join(vf),
                    "-map", "0:v:0", "-map", "1:a:0", "-af", "apad",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                    seg_out.name,
                ],
                cwd=work,
            )
            parts.append(seg_out.name)

        (work / "list.txt").write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
        final = work / "final.mp4"
        _run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy",
             "-movflags", "+faststart", final.name],
            cwd=work,
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(final, out_path)
        return _duration(out_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
