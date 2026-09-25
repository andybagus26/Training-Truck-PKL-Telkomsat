# Backend API (FastAPI)

Lapisan API di depan Frigate. Frigate menyimpan hasil deteksi, backend ini mengambil dan merapikannya,
lalu menyajikannya lewat endpoint sendiri. Dashboard atau sistem lain cukup memanggil backend ini dan
tidak perlu tahu cara kerja Frigate.

```
Frigate NVR  ──►  Backend FastAPI  ──►  dashboard / sistem lain
(deteksi)         (rapikan & sajikan)    (konsumen data)
```

## Menjalankan

```bash
# Frigate harus sudah berjalan (default http://localhost:8971)
.venv/bin/uvicorn backend.app.main:app --port 8000 --reload
```

Dokumentasi interaktif otomatis tersedia di **http://localhost:8000/docs**, lengkap dengan tombol
"Try it out" untuk mencoba tiap endpoint.

Alamat Frigate dan timeout bisa diubah lewat environment variable:

```bash
FRIGATE_URL=http://192.168.1.10:8971 FRIGATE_TIMEOUT=15 .venv/bin/uvicorn backend.app.main:app --port 8000
```

## Endpoint

| Endpoint | Fungsi |
|---|---|
| `GET /health` | Status backend, apakah Frigate terjangkau, versi Frigate, daftar class model |
| `GET /labels` | Daftar class: `truck`, `full_load`, `empty_load`, `excavator` |
| `GET /cameras` | Daftar kamera: status aktif, fps deteksi, resolusi, zone, class yang dilacak |
| `GET /cameras/{camera}/latest` | Frame terbaru sebuah kamera (JPEG). Parameter: `bbox`, `height` |
| `GET /detections` | Daftar deteksi yang sudah dirapikan |
| `GET /detections/{id}` | Detail satu deteksi |
| `GET /detections/{id}/snapshot` | Gambar saat objek terdeteksi (JPEG). Parameter: `bbox` |
| `GET /summary` | Rekap jumlah deteksi per label dan per kamera dalam rentang waktu |
| `GET /stats` | Performa detektor dan kamera |

### Penyaringan di `/detections`

| Parameter | Contoh | Keterangan |
|---|---|---|
| `camera` | `excavator_shovel` | Batasi ke satu kamera |
| `label` | `excavator` | Harus salah satu class model; selain itu ditolak dengan 422 |
| `zone` | `area_loading` | Hanya objek yang masuk zone tersebut |
| `since_minutes` | `30` | Deteksi dalam N menit terakhir |
| `after`, `before` | `2026-09-25T09:00:00Z` | Rentang waktu eksplisit (ISO 8601) |
| `min_score` | `0.7` | Skor minimum |
| `ongoing_only` | `true` | Hanya objek yang masih terlihat saat ini |
| `limit` | `100` | Maksimal 500 |

### Contoh

```bash
curl "http://localhost:8000/detections?label=excavator&min_score=0.7&limit=5"
curl "http://localhost:8000/detections?camera=cat775_full&since_minutes=30"
curl "http://localhost:8000/summary?since_minutes=60"
curl "http://localhost:8000/cameras/excavator_shovel/latest?height=480" -o frame.jpg
```

Contoh isi satu deteksi:

```json
{
  "id": "1790329169.623477-4sm1jp",
  "camera": "truck_lewat",
  "label": "truck",
  "score": 0.9013,
  "start_time": "2026-09-25T09:39:29.623477Z",
  "end_time": "2026-09-25T09:39:41.204000Z",
  "duration_seconds": 11.6,
  "ongoing": false,
  "zones": [],
  "box": { "x": 0.08, "y": 0.55, "w": 0.16, "h": 0.22 },
  "has_snapshot": true,
  "has_clip": true,
  "snapshot_url": "/detections/1790329169.623477-4sm1jp/snapshot"
}
```

Nilai `box` bersifat relatif (0–1) terhadap ukuran frame, jadi tetap benar pada resolusi tampilan
berapa pun.

## Catatan

- **Tanpa database.** Data selalu diambil langsung dari Frigate saat diminta, jadi selalu sinkron.
  Konsekuensinya, histori mengikuti masa simpan di Frigate (saat ini 3 hari).
- **Endpoint snapshot** memerlukan `snapshots.enabled: true` di konfigurasi Frigate. Bila sebuah
  deteksi tidak punya gambar, `has_snapshot` bernilai `false` dan `snapshot_url` kosong.
- **Penamaan class** mengikuti model yang aktif (v5). Pada model versi pertama, truk bernama
  `mining_truck`; sejak itu digabung menjadi `truck`, dan `excavator` ditambahkan pada v5.
- **Penanganan error**: Frigate mati atau tidak terjangkau menghasilkan `503`, terlalu lama merespons
  `504`, dan error dari Frigate diteruskan sebagai `502`. Jadi pemanggil bisa membedakan masalah
  jaringan dari data yang memang tidak ada (`404`).
- CORS dibuka untuk semua origin agar mudah dipakai dashboard saat pengembangan. Batasi sebelum
  dipakai di jaringan yang lebih luas.
