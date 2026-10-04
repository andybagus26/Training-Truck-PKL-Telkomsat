# Backend API (FastAPI)

Lapisan API di depan Frigate. Frigate menyimpan hasil deteksi, backend ini mengambil dan merapikannya,
lalu menyajikannya lewat endpoint sendiri. Dashboard atau sistem lain cukup memanggil backend ini dan
tidak perlu tahu cara kerja Frigate.

```
Frigate NVR  ──►  Backend FastAPI  ──►  dashboard / sistem lain
(deteksi)         (rapikan & sajikan)    (konsumen data)
```

Selain meneruskan data deteksi, backend mengikuti keadaan objek dari waktu ke waktu dan
menyimpulkan **aktivitas** darinya: *loading* (truk sedang dimuat excavator), *dumping* (truk
menumpahkan muatan), dan *idle* (truk berhenti tanpa dilayani).

## Menjalankan

Butuh Python 3.10 ke atas. Semua perintah dijalankan dari akar repositori; Frigate harus sudah
berjalan (default `http://localhost:8971`).

```bash
# Mac / Linux
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8000 --reload
```

```powershell
# Windows (PowerShell)
python -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt
backend\.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000 --reload
```

Dokumentasi interaktif otomatis tersedia di **http://localhost:8000/docs**, lengkap dengan tombol
"Try it out" untuk mencoba tiap endpoint. Tampilan pemantauan ada di
**http://localhost:8000/dashboard/**.

Alamat Frigate dan timeout bisa diubah lewat environment variable. Cara mengisinya berbeda di tiap
sistem operasi:

```bash
# Mac / Linux: ditulis di depan perintah
FRIGATE_URL=http://192.168.1.10:8971 FRIGATE_TIMEOUT=15 backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8000
```

```powershell
# Windows (PowerShell): diisi dulu, baru perintahnya dijalankan
$env:FRIGATE_URL = "http://localhost:5000"
backend\.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000
```

Bila Frigate dijalankan dengan `frigate/docker-compose.yml`, port yang dibuka adalah 5000, jadi
`FRIGATE_URL` harus diisi `http://localhost:5000`. Tanpa itu backend mencari Frigate di port 8971 dan
`/health` melaporkan Frigate tidak terjangkau.

### MQTT (diperlukan untuk deteksi aktivitas)

Posisi objek terkini hanya tersedia lewat MQTT. Kotak yang dikembalikan `/api/events` adalah posisi
saat snapshot terbaik objek diambil, bukan posisi sekarang, sehingga tidak bisa dipakai menilai
"excavator berdekatan dengan truk" atau "truk berhenti". Karena itu Frigate perlu disambungkan ke
sebuah broker.

Broker dijalankan berdampingan dengan Frigate. Susunan siap pakainya ada di
`frigate/docker-compose.yml` (layanan `mosquitto`, dengan `frigate/mosquitto.conf`):

```yaml
  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
```

lalu dinyalakan di konfigurasi Frigate:

```yaml
mqtt:
  enabled: true
  host: mosquitto
  port: 1883
```

**`host` diisi nama layanan broker, bukan `localhost`.** Frigate berjalan di dalam container, dan di
sana `localhost` berarti container itu sendiri. Bila salah, Frigate tidak pernah tersambung ke broker
sementara backend tetap tersambung — tidak ada error yang muncul, hanya saja tidak ada satu pun kabar
yang masuk.

Backend menyambung ke `localhost:1883`; bisa diubah lewat `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`,
`MQTT_PASSWORD`. Sambungannya dicek di `GET /poller`: `mqtt.messages` menunjukkan jumlah kabar yang
sudah diterima. Bila broker tersambung tetapi tidak ada kabar selama `MQTT_SILENT_AFTER` detik padahal
Frigate sedang melacak objek, `mqtt.receiving` menjadi `false` dan `warning` berisi penjelasannya.

Tanpa broker, backend tetap jalan dengan membaca `/api/events` — daftar deteksi tetap lengkap, tapi
deteksi aktivitas tidak bisa diandalkan karena alasan di atas. Field `source` pada `/poller`
menunjukkan sumber yang sedang dipakai.

## Endpoint

| Endpoint | Fungsi |
|---|---|
| `GET /` | Diarahkan ke `/dashboard/` |
| `GET /health` | Status backend, apakah Frigate terjangkau, versi Frigate, daftar class model |
| `GET /labels` | Daftar class: `truck`, `full_load`, `empty_load`, `excavator`, `bed_raised` |
| `GET /cameras` | Daftar kamera: status aktif, fps deteksi, resolusi, zone, class yang dilacak |
| `GET /cameras/{camera}/latest` | Frame terbaru sebuah kamera (JPEG). Parameter: `bbox`, `height` |
| `GET /cameras/{camera}/objects` | Objek yang sedang terlihat di sebuah kamera beserta keadaan truknya, kotak relatif 0-1 |
| `GET /detections` | Daftar deteksi yang sudah dirapikan |
| `GET /detections/{id}` | Detail satu deteksi |
| `GET /detections/{id}/snapshot` | Gambar saat objek terdeteksi (JPEG). Parameter: `bbox` |
| `GET /summary` | Rekap jumlah deteksi per label dan per kamera dalam rentang waktu |
| `GET /stats` | Performa detektor dan kamera, serta pemakaian CPU/RAM mesin Frigate (`system`) dan tiap kamera |
| `GET /activities` | Aktivitas yang tersimpul: `loading`, `dumping`, `idle`. Parameter: `type`, `camera`, `since_minutes`, `ongoing_only`, `limit` |
| `GET /activities/{id}` | Detail satu aktivitas |
| `GET /trucks/live` | Keadaan tiap truk yang sedang terlihat: `moving`/`loading`/`dumping`/`idle`, status muatan, excavator terdekat |
| `GET /utilization` | Per truk: lama tiap keadaan dan bagian waktu yang terbuang. Parameter: `camera`, `since_minutes` |
| `GET /operations` | Per kamera: truk terlihat, total waktu tiap keadaan, jumlah dan rata-rata durasi aktivitas |
| `GET /poller` | Status pengambilan sampel dan sambungan MQTT, termasuk peringatan bila tidak ada kabar dari Frigate |

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

## Keadaan truk dan aktivitas

Aktivitas disimpulkan dari sampel keadaan yang diambil tiap detik, bukan dari satu frame saja. Pada
setiap titik waktu, sebuah truk berada di salah satu dari empat keadaan:

| Keadaan | Syarat |
|---|---|
| `moving` | titik tengah kotaknya bergeser lebih dari `MOVE_TOLERANCE` dalam `STILL_WINDOW` detik terakhir |
| `dumping` | truk berhenti dan ada kotak `bed_raised` di dalam kotak truk |
| `loading` | truk berhenti dan ada excavator berdekatan — jarak antar kotak di bawah `NEAR_GAP` (0 berarti bertumpuk) |
| `idle` | truk berhenti, tidak sedang dimuat maupun menumpah |

Urutan penilaiannya dumping, lalu loading, lalu idle, sehingga satu truk tidak pernah terhitung dua
kali. Sebuah keadaan baru dicatat sebagai aktivitas bila bertahan melewati lama minimalnya, dan
ditutup bila syaratnya hilang selama `END_GRACE` detik. Status muatan sebelum dan sesudah diambil dari
kotak `full_load`/`empty_load` yang berada di dalam kotak truk.

| Variable | Default | Arti |
|---|---|---|
| `POLL_INTERVAL` | `1` | Detik antar pengambilan sampel |
| `MOVE_TOLERANCE` | `0.03` | Batas pergeseran titik tengah (relatif terhadap ukuran frame) |
| `STILL_WINDOW` | `6` | Jendela penilaian "berhenti", detik |
| `NEAR_GAP` | `0.12` | Jarak maksimal truk-excavator (relatif) |
| `MIN_DURATION` | `8` | Lama minimal sebelum diakui sebagai loading, detik |
| `MIN_DUMP` | `5` | Lama minimal sebelum diakui sebagai dumping, detik |
| `MIN_IDLE` | `30` | Lama minimal sebelum diakui sebagai idle, detik |
| `END_GRACE` | `15` | Lama syarat boleh hilang sebelum aktivitas ditutup, detik |
| `RETENTION_HOURS` | `6` | Masa simpan sampel mentah (aktivitas tidak ikut terhapus) |
| `MQTT_STALE_AFTER` | `120` | Objek yang tidak dikabarkan selama ini dianggap sudah hilang, detik |
| `MQTT_SILENT_AFTER` | `180` | Lama tanpa kabar MQTT sebelum `/poller` memberi peringatan, detik |
| `DB_PATH` | `backend/data/activity.db` | Letak penyimpanan sampel dan aktivitas |

Ambang idle sengaja lebih panjang: berhenti sebentar untuk manuver atau memberi jalan bukan
pemborosan, yang dicari adalah berhenti yang benar-benar menunggu.

Angka default lainnya diambil dari pengukuran pada rekaman uji: truk yang benar-benar dimuat
menghasilkan rentang 21-30 detik, sedangkan truk yang sekadar melintas dekat excavator hanya 0-2
detik. Pada pengujian 6 menit, 10 aktivitas loading terbentuk dengan 93-100% waktunya benar-benar
memenuhi syarat, dan 42 truk yang lewat di kamera tanpa excavator tidak menghasilkan aktivitas palsu.
Nilainya bergantung sudut kamera, jadi perlu disetel ulang untuk lokasi lain.

### Melihat hasilnya secara visual

Tampilan pemantauan ada di folder [`Dashboard/`](../Dashboard/) pada akar repositori.

Endpoint `GET /cameras/{camera}/objects` menyediakan bahan untuk menggambar lapisan di atas gambar
kamera: tiap objek yang sedang terlihat beserta kotaknya, dan untuk truk ditambah keadaannya
(`moving`, `loading`, `dumping`, `idle`) serta sudah berapa lama. Koordinatnya relatif 0-1, jadi bisa
langsung dikalikan dengan ukuran gambar berapa pun.

Perlu dibedakan saat menampilkannya: `excavator`, `bed_raised`, `full_load`, dan `empty_load` adalah
hasil deteksi langsung model, sedangkan keadaan truk bukan hasil deteksi melainkan kesimpulan dari
gerak truk dan objek di sekitarnya.

### Menghitung waktu terbuang

`GET /utilization` merinci per truk, `GET /operations` merekap per kamera: berapa lama truk berada di
tiap keadaan, berapa kali dimuat atau menumpah, dan berapa rata-rata durasinya. Keduanya dihitung
ulang dari sampel, bukan dari tabel aktivitas, sehingga keadaan yang terlalu singkat untuk diakui
sebagai aktivitas pun tetap terhitung — jumlah seluruh keadaan sama dengan lama truk itu terlihat.
`idle_share` adalah bagian waktu truk berhenti tanpa dilayani.

### Yang tidak bisa dijawab dari kamera

Ini perlu diketahui sebelum angkanya dipakai mengambil keputusan:

- **Mesin hidup atau mati tidak terlihat.** `idle` di sini berarti "berhenti dan tidak sedang
  dilayani". Truk yang parkir selesai giliran terlihat sama persis dengan truk yang menunggu
  excavator; yang membedakan hanya lama berhentinya dan di zone mana, jadi ambangnya harus mengikuti
  aturan lapangan.
- **Tonase tidak terukur** — yang diketahui hanya penuh atau kosong.
- **Siklus penuh per truk belum bisa dirangkai.** Id objek Frigate berlaku per kamera dan per
  kemunculan, jadi truk yang keluar-masuk frame dihitung sebagai objek baru. Untuk menghitung ritase
  dan waktu siklus, truknya harus dikenali satuan, misalnya lewat nomor lambung.
- **Gerak mendekati atau menjauhi kamera sulit terbaca.** "Berhenti" dinilai dari pergeseran titik
  tengah kotak, sedangkan truk yang mundur lurus ke arah kamera hampir tidak bergeser — hanya
  kotaknya yang membesar. Frigate pun menganggapnya diam dan berhenti mengabarkan posisinya, sehingga
  truk itu terbaca `idle` padahal masih bergerak. Sudut kamera yang menyamping lebih aman.

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
- **Penamaan class** mengikuti model yang aktif (v6). Pada model versi pertama truk bernama
  `mining_truck`, sejak itu digabung menjadi `truck`; `excavator` ditambahkan pada v5 dan
  `bed_raised` pada v6.
- **Penanganan error**: Frigate mati atau tidak terjangkau menghasilkan `503`, terlalu lama merespons
  `504`, dan error dari Frigate diteruskan sebagai `502`. Jadi pemanggil bisa membedakan masalah
  jaringan dari data yang memang tidak ada (`404`).
- **Deteksi dumping bergantung pada class `bed_raised`** dari model v6. Class itu baru mengenal lima
  sudut kamera, jadi di sudut yang jauh berbeda dumping bisa terlewat — truknya tetap terbaca, hanya
  keadaannya jatuh ke `idle` karena baknya tidak dikenali terangkat.
- **Daftar kamera dibaca saat backend tersambung.** Ukuran frame tiap kamera diambil sekali, jadi
  kamera yang ditambahkan ke Frigate setelah itu terbaca `unknown` sampai backend dinyalakan ulang.
  Urutan menyalakan tidak masalah: backend yang hidup lebih dulu akan tersambung sendiri begitu
  Frigate dan broker siap.
- CORS dibuka untuk semua origin agar mudah dipakai dashboard saat pengembangan. Batasi sebelum
  dipakai di jaringan yang lebih luas.
