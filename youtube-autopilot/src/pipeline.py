"""Alur utama: naskah -> video -> upload -> catat riwayat."""
import copy
import datetime
import json
import os
import pathlib

import yaml

from . import auth, script_gen, upload, video

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    hist_path = ROOT / "data" / "history.json"
    history = _load(hist_path, [])
    perf = _load(ROOT / "data" / "performance.json", {})
    top_titles = [t["title"] for t in perf.get("top", [])][:5]

    dry = os.environ.get("DRY_RUN", "").strip().lower() in ("1", "true", "yes")
    shorts = cfg["video"]["format"] == "shorts"
    max_s = cfg["video"].get("max_shorts_seconds", 59)
    (ROOT / "output").mkdir(exist_ok=True)

    yt = None if dry else auth.youtube(auth.credentials())

    for n in range(int(cfg["video"].get("uploads_per_run", 1))):
        scale = 1.0
        for _attempt in range(3):
            c = copy.deepcopy(cfg)
            c["video"]["target_seconds"] = max(20, int(cfg["video"]["target_seconds"] * scale))
            data = script_gen.generate(c, history, top_titles)
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
            out = ROOT / "output" / f"video-{stamp}-{n}.mp4"
            secs = video.build(data, cfg, out)
            if not shorts or secs <= max_s:
                break
            print(f"Durasi {secs:.0f}s melebihi {max_s}s, ulangi dengan naskah lebih pendek")
            out.unlink(missing_ok=True)
            scale *= 0.75
        else:
            raise SystemExit("Gagal membuat Shorts di bawah batas durasi")

        if dry:
            print(f"Uji coba selesai ({secs:.0f}s): {out.name} | judul: {data['title']}")
            continue

        video_id = upload.upload(out, data, cfg, yt)
        print(f"Terupload: https://youtube.com/watch?v={video_id} ({cfg['upload'].get('privacy')})")
        history.append(
            {
                "date": datetime.date.today().isoformat(),
                "topic": data["topic"],
                "title": data["title"],
                "video_id": video_id,
            }
        )
        hist_path.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")
        out.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
