# dinail AI — layanan cek foto ukuran kuku

Bagian AI dari capstone Asah 2026 (tim A26-CS222, UMKM dinail.co). Layanan ini menerima
foto tangan + koin patokan, memeriksa kualitas foto, mendeteksi koin, menghitung skala
piksel→mm, lalu menyarankan nomor ukuran memakai tabel konversi pemilik.

Status: **v0.1 jalan di `https://dinail.himanusia.com`** (InstaBox sandbox + Cloudflare Tunnel).

Ini **layanan backend (HTTP API)** plus satu halaman HTML tanpa build step untuk uji manual.
Tidak ada database, tidak ada framework frontend: halaman pemesanan, antrian admin, dan
dashboard pemilik tetap milik FS dan memanggil endpoint di sini.

## Struktur

| berkas | isi |
|---|---|
| `dinail_ai/coins.py` | tabel diameter koin rupiah + nominal yang ambigu (sumber + tahun) |
| `dinail_ai/quality.py` | metrik kualitas foto + `gate()` yang mengembalikan alasan tolak |
| `dinail_ai/detect.py` | Hough kasar → refine sub-piksel ke rim luar → skor kandidat |
| `dinail_ai/sizes.py` | pemetaan lebar mm ke nomor ukuran dari tabel pemilik (atau "belum diisi") |
| `dinail_ai/analyze.py` | orkestrasi satu foto: kualitas → deteksi → skala → saran |
| `dinail_ai/app.py` | FastAPI: `/v1/analyze`, `/health`, `/v1/size-table`, halaman `/` |
| `scripts/make_fixtures.py` | pembuat scene uji ber-ground-truth + crop foto koin |
| `tests/` | 42 uji: tabel koin, gerbang kualitas, deteksi & akurasi, tabel ukuran, orkestrasi, API |

## Apa yang sudah dikerjakan

| Bagian | Status | Catatan |
|---|---|---|
| Gerbang kualitas foto (buram, gelap, terlalu kecil, koin kecil/tidak ada) | jalan | tolak dengan alasan tertulis, bukan sekadar gagal |
| Deteksi koin patokan + skala px/mm | jalan | Hough + refine sub-piksel (rim luar), error skala 0,14–0,88% pada scene ground truth |
| Saran nomor ukuran | siap, menunggu data | butuh tabel konversi nomor ukuran dari pemilik (`size_table.json`) |
| Deteksi kuku otomatis (segmentasi) | belum | v0.1 memakai lebar kuku (px) yang dikirim UI/admin |
| Klasifikasi jenis koin dari gambar | belum | v0.1 memakai jenis koin yang dipilih di form (jalur cadangan di dokumen risiko) |
| Uji pada foto dinail.co | belum | butuh 32 foto (16 sesi) + 50–100 foto berlabel dari pemilik |

## Kontrak API (untuk FS)

`POST /v1/analyze` — `multipart/form-data`

| field | wajib | isi |
|---|---|---|
| `image` | ya | JPEG/PNG/WebP, maks 12 MB |
| `coin` | tidak | `50` \| `100` \| `200` \| `500` \| `1000` (jenis koin yang dipakai) |
| `nail_width_px` | tidak | lebar kuku dalam piksel dari alat ukur di UI/admin |
| `coin_diameter_px` | tidak | override kalau admin mengukur koin manual |

Respons:

```json
{
  "ok": true,
  "quality": {"pass": true, "reasons": [], "sharpness": 436.0, "sharpness_global": 201.2,
              "brightness": 211.05, "width": 1600, "height": 1200, "min_side": 1200},
  "coin": {"found": true, "center_px": [1120.3, 541.2], "radius_px": 121.2,
           "diameter_px": 242.4, "score": 0.843, "type": "500", "diameter_mm": 27.0},
  "scale_px_per_mm": 8.9785,
  "nail": {"width_px": 118.8, "width_mm": 13.23,
           "suggestion": {"size": "M", "range_mm": [12.6, 14.0], "margin_mm": 0.63,
                          "ambiguous": false, "needs_admin_check": true}},
  "warnings": [],
  "elapsed_ms": 707.1
}
```

- `quality.pass = false` → tampilkan `quality.reasons` apa adanya ke customer.
- `suggestion.size = null` → tabel konversi pemilik belum diisi; jangan menebak.
- `needs_admin_check` selalu `true`: hasil AI adalah saran, admin tetap konfirmasi.
- Latensi terukur: 360–710 ms untuk foto 1600×1200 s.d. 3200×2400.

`GET /health` — status, versi, diameter koin yang dipakai, status tabel konversi.
`GET /v1/size-table` — isi tabel konversi yang sedang aktif.

## Diameter koin yang dipakai

Rp50 20 mm · Rp100 23 mm · Rp200 25 mm · Rp500 27 mm · Rp1000 24 mm
(sumber: Wikipedia "Uang koin rupiah", perlu dikonfirmasi ke pemilik).
Rp200 (25 mm) dan Rp1000 (24 mm) hanya beda 1 mm → API mengeluarkan `warnings`, dan
jenis koin harus dipilih di form, bukan ditebak dari ukuran.

## Ketajaman foto

`quality.sharpness` = persentil 99,5 gradien pada petak 128 px, diambil **petak terajam**.
Statistik global jatuh pada foto berlatar polos (scene uji 22–48) walau tepi koinnya tajam,
sedangkan per petak 380–510. Foto buram tetap rendah di semua petak (51–55), jadi ambang
150 memberi jarak pisah ~8×, bukan 1,7× seperti versi global.

## Tabel konversi ukuran

Salin `size_table.example.json` → `dinail_ai/size_table.json` setelah pemilik memberi
angka resmi, lalu restart container. Format: `{"sizes": [{"size": "S", "min_mm": 12.6,
"max_mm": 14.0}, ...]}`. Tanpa berkas ini API tetap jalan, tapi saran ukuran berhenti di
`size: null` + alasan.

## Jalankan lokal

```bash
/opt/homebrew/bin/python3.12 -m venv venv     # python 3.12; 3.9 sistem tidak punya wheel numpy>=2.1
./venv/bin/pip install -r requirements.txt
./venv/bin/python scripts/make_fixtures.py    # fixture uji (sekali, ~10 s)
./venv/bin/python -m pytest -q                # 42 uji, ~35 s
./venv/bin/uvicorn dinail_ai.app:app --port 8000
```

`fixtures/` berisi scene sintetis ber-ground-truth (koin digambar dengan radius pasti) dan
foto koin domain publik dari Wikimedia Commons. Error skala pada 4 scene yang lolos gerbang:
0,14–0,88%; error lebar kuku ≤ 0,35 mm. Dua scene sengaja ditolak karena koinnya terlalu
kecil di frame.

## Deploy (InstaBox sandbox + Cloudflare Tunnel)

```bash
instabox start box-6be75f                       # sandbox gratis 4 vCPU/8 GB
instabox push box-6be75f . /data/home/dinail-ai -p
instabox ssh box-6be75f -- 'cd /data/home/dinail-ai && docker build -t dinail-ai . && \
  docker rm -f dinail-ai; docker run -d --name dinail-ai --restart unless-stopped -p 8000:8000 dinail-ai'
# tunnel: dinail.himanusia.com -> localhost:8000 (token disimpan di Cloudflare, bukan di repo)
instabox ssh box-6be75f -- 'docker rm -f dinail-tunnel; docker run -d --name dinail-tunnel \
  --restart unless-stopped --network host cloudflare/cloudflared:latest tunnel --no-autoupdate run --token $TOKEN'
```

Batas sandbox gratis: auto-suspend setelah 30 menit idle, maksimum 480 menit per sesi, jadi
URL ini bukan hosting 24/7. Untuk demo/dosen cukup dihidupkan (`instabox start box-6be75f`),
untuk produksi pindahkan ke VPS `31.97.49.76` (Dokploy) di belakang Cloudflare yang sama.

## Langkah berikutnya

1. Terima 32 foto dinail.co + 50–100 foto berlabel + tabel konversi pemilik; ukur akurasi
   sesungguhnya (selisih mm vs penggaris, target selisih ≤ 1 nomor ukuran).
2. Segmentasi kuku otomatis (MediaPipe Hands / segmentasi) supaya `nail_width_px` tidak
   perlu diisi manual; siapkan split per customer agar tidak bocor.
3. Klasifikasi jenis koin dari gambar (6 jenis) sebagai pengganti pilihan di form, dengan
   laporan confusion matrix seperti yang diminta dokumen.
