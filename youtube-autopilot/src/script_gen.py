"""Membuat naskah video dengan Claude (butuh ANTHROPIC_API_KEY)."""
import json
import os

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")


def _prompt(cfg, history, top_titles):
    ch, v = cfg["channel"], cfg["video"]
    shorts = v["format"] == "shorts"
    words = int(v["target_seconds"] * 2.3)
    scenes = "5 sampai 8" if shorts else "12 sampai 20"
    past = "\n".join(f"- {h.get('topic', h.get('title', ''))}" for h in history[-60:]) or "(belum ada)"
    best = "\n".join(f"- {t}" for t in top_titles) or "(belum ada data)"
    jenis = "Shorts vertikal" if shorts else "panjang (horizontal)"
    return f"""Kamu penulis naskah video YouTube untuk channel dengan niche: {ch['niche']}.
Bahasa: {ch['language']}. Audiens: {ch['audience']}. Gaya: {ch['tone']}.
{ch.get('extra_rules', '')}

Buat SATU naskah video {jenis} dengan total narasi sekitar {words} kata.

Aturan:
- Topik harus BARU dan tidak mirip topik yang sudah pernah dibuat:
{past}
- Video yang paling berhasil di channel ini (pelajari pola topik/gayanya, jangan disalin):
{best}
- Hanya fakta yang bisa diverifikasi. Jika ragu, jangan dimasukkan. Tanpa klaim medis, keuangan, atau politik yang menyesatkan.
- Tulis dengan kata-katamu sendiri dan beri nilai tambah (penjelasan, sudut pandang, konteks), bukan sekadar daftar fakta.
- Kalimat pertama adalah hook yang kuat. Akhiri dengan pertanyaan ke penonton agar mereka berkomentar.
- {scenes} adegan. Tiap adegan: "narration" (1-2 kalimat pendek) dan "query" (kata kunci pencarian video stok dalam BAHASA INGGRIS, 2-4 kata, visual yang konkret).
- Judul maksimal 70 karakter, menarik, tidak menipu.

Balas HANYA dengan JSON valid berbentuk:
{{"topic": "...", "title": "...", "description": "2-3 kalimat, tambahkan rujukan jika ada", "tags": ["..."], "scenes": [{{"narration": "...", "query": "..."}}]}}"""


def _extract_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Balasan tidak berisi JSON")
    return json.loads(text[start : end + 1])


def _validate(d):
    for k in ("topic", "title", "description", "tags", "scenes"):
        if k not in d:
            raise ValueError(f"Kunci '{k}' hilang")
    if not d["scenes"]:
        raise ValueError("Tidak ada adegan")
    for s in d["scenes"]:
        if not s.get("narration") or not s.get("query"):
            raise ValueError("Adegan tidak lengkap")


def generate(cfg, history, top_titles):
    client = anthropic.Anthropic()
    prompt = _prompt(cfg, history, top_titles)
    last = None
    for attempt in range(3):
        try:
            msg = client.messages.create(
                model=MODEL,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )
            data = _extract_json(msg.content[0].text)
            _validate(data)
            return data
        except Exception as e:  # coba lagi jika JSON rusak
            last = e
            print(f"Naskah gagal (percobaan {attempt + 1}): {e}")
    raise RuntimeError(f"Gagal membuat naskah: {last}")
