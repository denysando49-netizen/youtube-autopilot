"""Pelacak target monetisasi: ambil statistik channel, hitung progres, simpan video terbaik."""
import datetime
import json
import pathlib

import yaml

from . import auth

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _bar(pct, n=20):
    filled = int(min(pct, 100) / 100 * n)
    return "█" * filled + "░" * (n - filled)


def _pct(value, target):
    return min(100.0, value / target * 100) if target else 0.0


def _query(ya, **kw):
    try:
        return ya.reports().query(ids="channel==MINE", **kw).execute().get("rows") or []
    except Exception as e:
        print(f"Analytics gagal ({kw.get('dimensions', 'total')}): {e}")
        print("Pastikan YouTube Analytics API sudah diaktifkan di Google Cloud.")
        return []


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    creds = auth.credentials()
    yt, ya = auth.youtube(creds), auth.analytics(creds)

    end = datetime.date.today() - datetime.timedelta(days=1)
    d365 = (end - datetime.timedelta(days=365)).isoformat()
    d90 = (end - datetime.timedelta(days=90)).isoformat()
    end_s = end.isoformat()

    stats = yt.channels().list(part="statistics", mine=True).execute()["items"][0]["statistics"]
    subs = int(stats.get("subscriberCount", 0))

    # Jam tayang yang dihitung YPP hanya dari video panjang & livestream (bukan Shorts)
    rows = _query(ya, startDate=d365, endDate=end_s, dimensions="creatorContentType",
                  metrics="views,estimatedMinutesWatched")
    minutes = sum(r[2] for r in rows if r[0] in ("VIDEO_ON_DEMAND", "LIVE_STREAM"))
    hours = minutes / 60

    rows = _query(ya, startDate=d90, endDate=end_s, dimensions="creatorContentType", metrics="views")
    shorts_views = sum(r[1] for r in rows if r[0] == "SHORTS")

    # Video terbaik 90 hari terakhir -> dipakai untuk mengarahkan topik berikutnya
    rows = _query(ya, startDate=d90, endDate=end_s, dimensions="video", metrics="views",
                  sort="-views", maxResults=10)
    top = []
    if rows:
        ids = [r[0] for r in rows]
        items = yt.videos().list(part="snippet", id=",".join(ids)).execute().get("items", [])
        titles = {i["id"]: i["snippet"]["title"] for i in items}
        top = [{"video_id": r[0], "title": titles.get(r[0], r[0]), "views": r[1]} for r in rows]

    m = cfg["monetization"]
    tiers = [
        ("Tier awal (fan funding)", m["early_tier"]),
        ("Tier iklan (aturan sekarang)", m["full_tier_now"]),
        ("Tier iklan (pelamar baru mulai 1 Feb 2027)", m["full_tier_from_2027_02_01"]),
    ]

    lines = [
        f"# Progres monetisasi",
        f"Diperbarui: {datetime.date.today().isoformat()} (perkiraan dari YouTube Analytics; angka resmi ada di YouTube Studio)",
        "",
        f"- Subscriber: **{subs:,}**",
        f"- Jam tayang video panjang (365 hari): **{hours:,.0f} jam**",
        f"- Views Shorts (90 hari): **{shorts_views:,}**",
        "",
    ]
    result = {"date": datetime.date.today().isoformat(), "subscribers": subs, "watch_hours_365d": round(hours, 1),
              "shorts_views_90d": shorts_views, "tiers": {}}
    for name, t in tiers:
        ps, ph, pv = _pct(subs, t["subscribers"]), _pct(hours, t["watch_hours"]), _pct(shorts_views, t["shorts_views"])
        ok = ps >= 100 and (ph >= 100 or pv >= 100)
        result["tiers"][name] = {"subs_pct": round(ps, 1), "hours_pct": round(ph, 1),
                                 "shorts_pct": round(pv, 1), "eligible": ok}
        lines += [
            f"## {name}  {'✅ MEMENUHI SYARAT' if ok else ''}",
            f"- Subscriber {t['subscribers']:,}: `{_bar(ps)}` {ps:.1f}%",
            f"- Jam tayang {t['watch_hours']:,}: `{_bar(ph)}` {ph:.1f}%",
            f"- *atau* views Shorts {t['shorts_views']:,}: `{_bar(pv)}` {pv:.1f}%",
            "",
        ]

    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "status.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    (ROOT / "data" / "performance.json").write_text(
        json.dumps({"date": result["date"], "top": top}, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    (ROOT / "STATUS.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
