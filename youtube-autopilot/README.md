# YouTube Autopilot

Sistem yang berjalan di GitHub Actions: membuat naskah (Claude), suara (edge-tts), video (klip stok Pexels + teks), mengunggahnya ke YouTube sesuai jadwal, lalu melacak progres monetisasi tiap minggu.

```
Jadwal harian ─► naskah (Claude) ─► suara + klip + teks (ffmpeg) ─► upload YouTube
Jadwal mingguan ─► YouTube Analytics ─► STATUS.md (progres) + video terbaik ─► topik berikutnya
```

## Setup (sekali saja, sekitar 30 menit)

### 1. GitHub
Buat repo baru (public = menit Actions gratis tanpa batas), lalu unggah semua isi folder ini.

### 2. Kunci API gratis/murah
- **Claude API key**: dari Claude Console (dipakai untuk menulis naskah; biaya kecil per video).
- **Pexels API key**: gratis di pexels.com/api (klip video stok).

### 3. Google Cloud (akses YouTube)
1. Buka console.cloud.google.com, buat project baru.
2. Aktifkan **YouTube Data API v3** dan **YouTube Analytics API**.
3. OAuth consent screen: pilih External, isi nama app dan emailmu, tambahkan emailmu sebagai test user.
4. **Penting:** setelah selesai, klik **Publish app** (status *In production*). Kalau dibiarkan *Testing*, token login kadaluarsa tiap 7 hari dan upload otomatis berhenti.
5. Credentials → Create credentials → OAuth client ID → tipe **Desktop app** → unduh JSON, simpan sebagai `client_secret.json` di folder proyek (jangan di-commit).
6. Di komputermu: `pip install google-auth-oauthlib` lalu `python scripts/get_refresh_token.py`. Login dengan akun yang memiliki channel YouTube. Skrip menampilkan 3 nilai.

### 4. GitHub Secrets
Repo → Settings → Secrets and variables → Actions → New repository secret. Buat 5 secret:
`ANTHROPIC_API_KEY`, `PEXELS_API_KEY`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

### 5. Atur channel
Edit `config.yaml`: niche, gaya, suara, format (`shorts` atau `long`), dan jam upload di `.github/workflows/upload.yml` (cron memakai UTC; WIB = UTC+7).

### 6. Uji coba
Actions → *Upload video otomatis* → Run workflow → centang **dry_run**. Video hasilnya bisa diunduh dari bagian Artifacts. Tonton dulu, perbaiki `config.yaml` jika perlu.

### 7. Jalan sungguhan
Biarkan jadwal berjalan. `privacy` default-nya `private`: cek video di YouTube Studio selama beberapa hari, dan kalau kualitasnya sudah bagus ubah jadi `public`.

## Melacak target monetisasi
Workflow *Laporan progres monetisasi* berjalan tiap Senin dan memperbarui `STATUS.md` (progres subscriber, jam tayang, views Shorts) serta `data/performance.json` (video terbaik). Naskah berikutnya otomatis dibuat dengan mengacu pola video yang performanya paling bagus.

Syarat YouTube Partner Program (cek ulang di YouTube Studio, angkanya bisa berubah; ubah di `config.yaml`):

| Tier | Subscriber | Jam tayang (365 hari) | atau Views Shorts (90 hari) |
|---|---|---|---|
| Awal (fan funding) | 500 | 3.000 | 3 juta |
| Iklan, sekarang | 1.000 | 4.000 | 10 juta |
| Iklan, pelamar baru mulai 1 Feb 2027 | 1.000 | 8.000 | 20 juta |

Catatan: jam tayang hanya dihitung dari video panjang, bukan Shorts. Kalau targetmu jam tayang, ubah `video.format` ke `long`.

## Agar monetisasi tidak ditolak
- Konten harus orisinal dan bernilai tambah. Video massal yang berulang atau seperti template bisa ditolak atau dicabut monetisasinya.
- Jangan mengejar jumlah. 1 video per hari dengan kualitas bagus lebih aman daripada 5 video asal-asalan.
- Tinjau hasilnya tiap minggu, dan hapus video yang jelek.
- Isi `contains_synthetic_media: true` jika visual atau suaranya meniru orang atau peristiwa nyata secara realistis.
- Klip Pexels boleh dipakai gratis. Naskah dan fakta tetap perlu kamu cek sesekali.

## Batasan yang perlu diketahui
- Upload lewat API memakai kuota YouTube. Jika video yang diunggah ternyata terkunci *private* di Studio padahal `privacy: public`, proyek API-mu perlu diverifikasi lewat formulir audit Google.
- edge-tts kadang diblokir dari server GitHub. Jika gagal, sistem otomatis memakai gTTS (suara kurang natural).
- Jika tidak ada klip yang cocok, adegan memakai latar warna polos.
