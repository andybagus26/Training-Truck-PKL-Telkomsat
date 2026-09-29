# Backend API (FastAPI)

Lapisan API di depan Frigate. Frigate menyimpan hasil deteksi, backend ini mengambil dan merapikannya,
lalu menyajikannya lewat endpoint sendiri. Dashboard atau sistem lain cukup memanggil backend ini dan
tidak perlu tahu cara kerja Frigate.

```
Frigate NVR  ──►  Backend FastAPI  ──►  dashboard / sistem lain
(deteksi)         (rapikan & sajikan)    (konsumen data)
```

Selain meneruskan data deteksi, backend mengikuti keadaan objek dari waktu ke waktu dan
menyimpulkan **aktivitas** darinya. Tahap saat ini menangani aktivitas *loading* (truk sedang
dimuat excavator).

## Menjalankan

```bash
pip install -r backend/requirements.txt

# Frigate harus sudah berjalan (default http://localhost:8971)
.venv/bin/uvicorn backend.app.main:app --port 8000 --reload
```

Dokumentasi interaktif otomatis tersedia di **http://localhost:8000/docs**, lengkap dengan tombol
"Try it out" untuk mencoba tiap endpoint.

Alamat Frigate dan timeout bisa diubah lewat environment variable:

```bash
FRIGATE_URL=http://192.168.1.10:8971 FRIGATE_TIMEOUT=15 .venv/bin/uvicorn backend.app.main:app --port 8000
```

### MQTT (diperlukan untuk deteksi aktivitas)

Posisi objek terkini hanya tersedia lewat MQTT. Kotak yang dikembalikan `/api/events` adalah posisi
saat snapshot terbaik objek diambil, bukan posisi sekarang, sehingga tidak bisa dipakai menilai
"excavator berdekatan dengan truk" atau "truk berhenti". Karena itu Frigate perlu disambungkan ke
sebuah broker.

Broker dijalankan berdampingan dengan Frigate (lihat `frigate/mosquitto.conf`):

```yaml
  mosquitto:
    container_name: mosquitto
    image: eclipse-mosquitto:2
    restart: always
    volumes:
      - ./mosquitto/config/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
      - ./mosquitto/data:/mosquitto/data
    ports:
      - "1883:1883"
```

lalu dinyalakan di `config.yml` Frigate:

```yaml
mqtt:
  enabled: true
  host: mosquitto
  port: 1883
```

Backend menyambung ke `localhost:1883`; bisa diubah lewat `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`,
`MQTT_PASSWORD`. Sambungannya dicek di `GET /poller`.

Tanpa broker, backend tetap jalan dengan membaca `/api/events` — daftar deteksi tetap lengkap, tapi
deteksi aktivitas tidak bisa diandalkan karena alasan di atas. Field `source` pada `/poller`
menunjukkan sumber yang sedang dipakai.

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
| `GET /activities` | Aktivitas yang tersimpul, mis. truk sedang dimuat. Parameter: `type`, `camera`, `since_minutes`, `ongoing_only`, `limit` |
| `GET /activities/{id}` | Detail satu aktivitas |
| `GET /trucks/live` | Keadaan tiap truk yang sedang terlihat: status muatan, berhenti/jalan, excavator terdekat, aktivitas berjalan |
| `GET /poller` | Status pengambilan sampel dan sambungan MQTT |

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

## Aktivitas *loading*

Aktivitas disimpulkan dari sampel keadaan yang diambil tiap detik, bukan dari satu frame saja.
Sebuah truk dianggap sedang dimuat bila:

1. titik tengah kotaknya **tidak bergeser** lebih dari `MOVE_TOLERANCE` selama `STILL_WINDOW` detik, dan
2. ada **excavator berdekatan** — jarak antar kotak di bawah `NEAR_GAP` (0 berarti bertumpuk), dan
3. keduanya bertahan minimal `MIN_DURATION` detik.

Aktivitas ditutup bila syaratnya hilang selama `END_GRACE` detik. Status muatan sebelum dan sesudah
diambil dari kotak `full_load`/`empty_load` yang berada di dalam kotak truk.

| Variable | Default | Arti |
|---|---|---|
| `POLL_INTERVAL` | `1` | Detik antar pengambilan sampel |
| `MOVE_TOLERANCE` | `0.03` | Batas pergeseran titik tengah (relatif terhadap ukuran frame) |
| `STILL_WINDOW` | `6` | Jendela penilaian "berhenti", detik |
| `NEAR_GAP` | `0.12` | Jarak maksimal truk-excavator (relatif) |
| `MIN_DURATION` | `8` | Lama minimal sebelum diakui sebagai loading, detik |
| `END_GRACE` | `15` | Lama syarat boleh hilang sebelum aktivitas ditutup, detik |
| `RETENTION_HOURS` | `72` | Masa simpan sampel |

Angka default diambil dari pengukuran pada rekaman uji: truk yang benar-benar dimuat menghasilkan
rentang 21-30 detik, sedangkan truk yang sekadar melintas dekat excavator hanya 0-2 detik. Pada
pengujian 6 menit, 10 aktivitas terbentuk dengan 93-100% waktunya benar-benar memenuhi syarat, dan
42 truk yang lewat di kamera tanpa excavator tidak menghasilkan aktivitas palsu. Nilainya bergantung
sudut kamera, jadi perlu disetel ulang untuk lokasi lain.

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

- **Data deteksi tidak disalin.** `/detections`, `/summary`, dan `/stats` mengambil langsung dari
  Frigate saat diminta, jadi selalu sinkron; historinya mengikuti masa simpan Frigate (3 hari).
- **Aktivitas perlu penyimpanan sendiri**, karena menilai "berapa lama truk berhenti didampingi
  excavator" butuh rekaman keadaan dari waktu ke waktu, sedangkan Frigate hanya menyimpan ringkasan
  per objek. Sampel dan aktivitas disimpan di SQLite (`backend/data/activity.db`, dibuat otomatis
  dan tidak ikut di-commit). Menghapus file itu hanya menghapus riwayat aktivitas.
- **Endpoint snapshot** memerlukan `snapshots.enabled: true` di konfigurasi Frigate. Bila sebuah
  deteksi tidak punya gambar, `has_snapshot` bernilai `false` dan `snapshot_url` kosong.
- **Penamaan class** mengikuti model yang aktif (v5). Pada model versi pertama, truk bernama
  `mining_truck`; sejak itu digabung menjadi `truck`, dan `excavator` ditambahkan pada v5.
- **Penanganan error**: Frigate mati atau tidak terjangkau menghasilkan `503`, terlalu lama merespons
  `504`, dan error dari Frigate diteruskan sebagai `502`. Jadi pemanggil bisa membedakan masalah
  jaringan dari data yang memang tidak ada (`404`).
- **Aktivitas selain loading** (dumping, idle) belum ditangani. Dumping menunggu penambahan class
  untuk bak yang terangkat pada model berikutnya; idle menunggu data lapangan.
- CORS dibuka untuk semua origin agar mudah dipakai dashboard saat pengembangan. Batasi sebelum
  dipakai di jaringan yang lebih luas.
