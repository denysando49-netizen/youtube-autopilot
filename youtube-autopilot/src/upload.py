"""Upload video ke YouTube lewat YouTube Data API v3."""
import time

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


def _clean_tags(tags):
    out, total = [], 0
    for t in tags:
        t = str(t).lstrip("#").strip()
        if not t:
            continue
        if total + len(t) + 1 > 450:
            break
        out.append(t)
        total += len(t) + 1
    return out[:15]


def upload(path, data, cfg, yt):
    up = cfg["upload"]
    shorts = cfg["video"]["format"] == "shorts"

    hashtags = list(up.get("default_hashtags", []))
    if shorts:
        hashtags.append("#Shorts")
    description = (data["description"].strip() + "\n\n" + " ".join(hashtags))[:4900]

    lang = up.get("language_code", "id")
    body = {
        "snippet": {
            "title": data["title"][:100],
            "description": description,
            "tags": _clean_tags(data.get("tags", [])),
            "categoryId": str(up.get("category_id", "27")),
            "defaultLanguage": lang,
            "defaultAudioLanguage": lang,
        },
        "status": {
            "privacyStatus": up.get("privacy", "private"),
            "selfDeclaredMadeForKids": bool(up.get("made_for_kids", False)),
            "containsSyntheticMedia": bool(up.get("contains_synthetic_media", False)),
        },
    }

    media = MediaFileUpload(str(path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response, tries = None, 0
    while response is None:
        try:
            _, response = request.next_chunk()
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and tries < 5:
                tries += 1
                time.sleep(2**tries)
                continue
            raise
    return response["id"]
