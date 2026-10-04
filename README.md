# Deteksi Truk Tambang dengan YOLOv9 + Frigate NVR

Model deteksi objek untuk memantau aktivitas tambang dari kamera CCTV: mendeteksi truk beserta status
muatannya (bermuatan / kosong), excavator, dan bak truk yang sedang terangkat saat menumpahkan muatan,
lalu dijalankan di [Frigate NVR](https://frigate.video) sebagai custom detector.

Di atasnya ada backend yang menyimpulkan apa yang sedang dilakukan tiap truk — sedang dimuat,
menumpahkan muatan, menganggur, atau bergerak — beserta lama tiap keadaan.

Model dilatih di Mac (Apple Silicon, MPS) dan dijalankan dengan ONNX Runtime + CoreML.

## Spesifikasi model

| | |
|---|---|
| Arsitektur | YOLOv9-t (Ultralytics 8.4), ~2 juta parameter |
| Input | 320×320, NCHW, RGB, nilai 0–1 |
| Output | `[1, 9, 2100]` — `cx, cy, w, h` (piksel) + 5 skor class, tanpa NMS |
| Class | `truck`, `full_load`, `empty_load`, `excavator`, `bed_raised` |
| Kecepatan | ~2 ms/gambar (CoreML, M1 Pro); ~14 ms per permintaan lewat Frigate |

Model siap pakai ada di `models/`.

## Hasil

Model v6, test set gabungan (187 gambar: 43 dari site asli + 144 dari tambang lain). Test set ini
tidak memuat adegan dumping, jadi `bed_raised` tidak muncul di tabel:

| Class | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|
| truck | 0.980 | 0.766 | 0.903 | 0.750 |
| full_load | 1.000 | 0.844 | 0.936 | 0.751 |
| empty_load | 0.902 | 0.857 | 0.855 | 0.728 |
| excavator | 0.887 | 0.824 | 0.850 | 0.697 |

Jumlah kotak terdeteksi pada video yang tidak dipakai saat training (24 frame per video, ambang 0.4):

| Video | truck | excavator | muatan |
|---|---|---|---|
| Loading di quarry (kamera statis) | 24 | 20 | 23 |
| Operasi malam hari | 25 | 27 | 0 |
| Truk melintas di jalan hauling | 35 | 0 | 0 |

Pada rekaman dumping, v6 mengenali truk di 91–100% frame dan bak terangkat di 100% frame, sementara
v5 sempat gagal total di salah satu rekaman. Rinciannya di
[`docs/hasil-training.md`](docs/hasil-training.md).

## Struktur

```
scripts/          Script training, pembuatan dataset, pelabelan, dan evaluasi
notebooks/        Notebook langkah demi langkah (setup, dataset, training, export ONNX) — model v1
models/           Model siap pakai (ONNX untuk Frigate + bobot PyTorch)
frigate/          Konfigurasi Frigate (Mac dan Windows), docker-compose, broker MQTT, dan patch Apple Silicon detector
docs/             Riwayat model, sumber dataset, dan grafik hasil training
dataset-v5-labels/   Anotasi dataset v5 (tanpa gambar) + panduan membangun ulang
dataset-dump-labels/ Anotasi rekaman dumping untuk class bed_raised (tanpa gambar)
backend/          API FastAPI yang menyajikan data deteksi dan menyimpulkan aktivitas truk
Dashboard/        Tampilan pemantauan berbasis web
```

- [`docs/riwayat-model.md`](docs/riwayat-model.md) — perkembangan v1 sampai v6 beserta alasan tiap penambahan data
- [`docs/sumber-dataset.md`](docs/sumber-dataset.md) — daftar lengkap sumber data tiap versi, dengan link
- [`docs/hasil-training.md`](docs/hasil-training.md) — grafik training, confusion matrix, dan contoh prediksi
- [`backend/README.md`](backend/README.md) — daftar endpoint API dan cara menjalankannya
- [`Dashboard/README.md`](Dashboard/README.md) — isi halaman pemantauan dan cara membukanya

Folder `datasets/`, `runs/`, `weights/`, dan `export/` tidak ikut di-commit karena besar,
dan bisa dibuat ulang dengan script di bawah. Anotasinya sendiri tersedia lengkap di
[`dataset-v5-labels/`](dataset-v5-labels/) dan, untuk class `bed_raised` pada v6, di
[`dataset-dump-labels/`](dataset-dump-labels/) — gambarnya tidak disertakan karena sebagian berasal dari
video publik yang hak ciptanya dipegang pemiliknya.

## Menjalankan

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
echo "ROBOFLOW_API_KEY=<api-key-anda>" > .env
```

Di Windows, letak program di dalam `.venv` berbeda: `.venv\Scripts\pip` dan `.venv\Scripts\python`,
bukan `.venv/bin/...`. Perintah lain di bawah tinggal menyesuaikan.

Dataset dasar diunduh dari Roboflow (lihat notebook), lalu:

```bash
# Training v6: fine-tune dari v5 dengan dataset yang sudah ditambah frame dumping
.venv/bin/python scripts/train.py --data datasets/mining-truck-v6/data.yaml \
    --weights models/mining_truck_yolov9t_320_v5.pt --epochs 50 --lr0 0.001

# Evaluasi beberapa versi model sekaligus
.venv/bin/python scripts/eval_models.py

# Video hasil deteksi (untuk pengecekan visual)
.venv/bin/python scripts/annotate_video.py input.mp4 output.mp4
```

Script pendukung:

| Script | Fungsi |
|---|---|
| `build_dataset_v2.py` | Gabungkan dataset site dengan dataset publik + label muatan hasil prediksi model |
| `autolabel_yt.py` | Ambil frame dari video dan buat label awal secara otomatis |
| `crop_review.py`, `review_grid.py` | Susun lembar pemeriksaan label untuk diperiksa manual |
| `apply_review.py` | Terapkan hasil pemeriksaan manual menjadi dataset bersih |
| `night_aug.py` | Buat versi malam sintetis dari gambar siang |
| `propose_excavator.py` | Usulkan kotak excavator untuk gambar di luar rf100, lalu susun lembar pemeriksaannya |
| `build_dataset_v5.py` | Bangun dataset 4 class (tambah `excavator`) |
| `track_box.py` | Lacak satu kotak anotasi dari frame acuan ke frame-frame sekitarnya |
| `review_boxes.py` | Gambar kotak hasil pelacakan ke lembar tinjauan, supaya kesalahan kelihatan sebelum dipakai |
| `build_dump_seed.py` | Susun dataset benih untuk class `bed_raised` dari kotak hasil pelacakan |
| `build_dataset_v6.py` | Susun dataset v6: dataset v5 ditambah class `bed_raised` dari rekaman dumping |

## Integrasi Frigate

Salin isi `models/` ke folder model Frigate, lalu pakai konfigurasi di `frigate/config.yml`:

```yaml
model:
  model_type: yolo-generic
  width: 320
  height: 320
  input_tensor: nchw
  input_dtype: float
  path: /models/mining_truck_yolov9t_320_v6.onnx
  labelmap_path: /models/labelmap_v6.txt

objects:
  track: [truck, full_load, empty_load, excavator, bed_raised]
```

Untuk Mac, deteksi dijalankan di host dengan
[apple-silicon-detector](https://github.com/frigate-nvr/apple-silicon-detector) karena Neural Engine
tidak bisa diakses dari dalam container:

```yaml
detectors:
  apple-silicon:
    type: zmq
    endpoint: tcp://host.docker.internal:5555
```

**Terapkan `frigate/apple-silicon-detector-nms-fix.patch` terlebih dahulu.** NMS bawaan detektor tersebut
bersifat class-agnostic dan menggunakan format kotak yang keliru, sehingga kotak muatan yang berada di
dalam kotak truk ikut terhapus.

Konfigurasi di `frigate/config.yml` juga berisi contoh zone dengan `loitering_time`, untuk menandai truk
yang berada terlalu lama di area loading.

### Windows, atau mesin tanpa Apple Silicon

Folder `frigate/` juga berisi susunan siap jalan lewat Docker: `docker-compose.yml` menyalakan Frigate
bersama broker MQTT, dengan konfigurasi `config.windows.yml`. Model diambil langsung dari `models/`, jadi
tidak perlu disalin.

```bash
cd frigate
docker compose up -d      # Frigate di http://localhost:5000
```

Video uji diletakkan di folder `frigate/` dengan nama yang tertulis di `docker-compose.yml`.

Di sini deteksi memakai detektor `onnx` bawaan Frigate yang berjalan di CPU, karena tidak ada Neural
Engine. Bebannya jauh lebih berat: pada pengujian 6 kamera di mesin 10 inti, detektor memakai hampir
seluruh inti dan sebagian frame terlewat, sedangkan lewat Neural Engine pemakaian CPU sekitar 11%. Untuk
mesin tanpa GPU, kurangi jumlah kamera atau turunkan `detect.fps`.

**`mqtt.host` harus berisi nama layanan broker (`mosquitto`), bukan `localhost`.** Di dalam container,
`localhost` berarti container Frigate sendiri, sehingga Frigate tidak pernah tersambung ke broker.
Akibatnya backend tidak menerima posisi objek: kotak keadaan di dashboard tidak muncul dan aktivitas
tidak tercatat, sementara Frigate-nya sendiri terlihat normal.

Susunan ini sudah dicoba dengan Frigate 0.17.1 dan 0.18.0. Versi bawaannya 0.17.1; untuk memakai image
lain, isi `FRIGATE_IMAGE` di file `frigate/.env`.

### Membaca warna kotak di Frigate

Kotak pada tampilan Frigate menunjukkan jenis objek sekaligus keadaannya:

| Tampilan | Artinya |
|---|---|
| Kotak tebal berwarna label | Objek terdeteksi pada frame ini dan sedang bergerak |
| Kotak tipis putih/abu-abu | Objek dianggap diam (stationary); warnanya tidak lagi mengikuti label |
| Kotak tipis biru | Objek tidak terdeteksi pada frame ini, tetapi posisinya masih dipertahankan pelacak |

Warna tiap label pada model v6:

| Label | Warna |
|---|---|
| `truck` | pink |
| `full_load` | biru tua |
| `empty_load` | biru muda |
| `excavator` | hijau |
| `bed_raised` | oranye kecokelatan |

Warna diberikan Frigate berdasarkan labelmap, jadi bisa berubah bila model atau labelmap diganti; pada v5
misalnya, excavator tidak berwarna hijau. Kotak tipis biru mudah tertukar dengan `full_load` dan
`empty_load`, jadi bedakan dari ketebalan garis dan tulisan labelnya.

Kotak yang berkedip atau berganti warna antar frame umumnya wajar: skor dan status diam dihitung ulang
tiap frame. Yang perlu diperhatikan adalah objek yang hilang lalu muncul sebagai objek baru, karena itu
memecah satu kejadian menjadi beberapa event.

## API untuk sistem lain

Folder [`backend/`](backend/) berisi API FastAPI yang mengambil data deteksi dari Frigate dan
menyajikannya kembali dalam bentuk yang lebih rapi, sehingga dashboard atau sistem lain tidak perlu
berhubungan langsung dengan Frigate.

```bash
# Mac / Linux
backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8000

# Windows (PowerShell)
backend\.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000

# dokumentasi interaktif: http://localhost:8000/docs
```

Cara memasang `backend/.venv` ada di [`backend/README.md`](backend/README.md). Alamat Frigate diatur
lewat `FRIGATE_URL` (default `http://localhost:8971`). Bila Frigate dijalankan
dengan `frigate/docker-compose.yml`, alamatnya `http://localhost:5000`; cara mengisinya di tiap sistem
operasi ada di [`backend/README.md`](backend/README.md).

Endpoint data deteksi: `/detections` (dengan penyaringan kamera, label, waktu, dan skor), `/summary`,
`/cameras`, `/stats`, serta endpoint gambar `/detections/{id}/snapshot` dan `/cameras/{camera}/latest`.

Endpoint penyimpulan aktivitas: `/activities` (loading, dumping, idle), `/trucks/live` (keadaan tiap
truk saat ini), `/cameras/{camera}/objects` (objek yang sedang terlihat beserta keadaan truknya),
`/utilization` (lama tiap keadaan per truk), dan `/operations` (rekap per kamera, termasuk bagian waktu
yang terbuang). Status backend dan sambungan MQTT ada di `/health` dan `/poller`.

### Dashboard

Backend juga menyajikan tampilan pemantauan dari folder [`Dashboard/`](Dashboard/) di
**http://localhost:8000/dashboard/** (alamat `http://localhost:8000/` otomatis diarahkan ke sana).
Isinya gambar tiap kamera dengan kotak keadaan truk, daftar deteksi, aktivitas truk, grafik, serta
pemakaian CPU dan RAM mesin Frigate. Dashboard hanya berupa HTML, CSS, dan JavaScript, jadi tidak ada
yang perlu di-install dan tampil sama di Windows maupun Mac.

## Catatan penerapan

- Beberapa pengaturan di `frigate/config.yml` khusus untuk kamera uji berupa video (`lightning_threshold`,
  `max_disappeared`, `stationary.threshold`). Untuk CCTV sungguhan, pakai nilai default.
- Frigate tidak membuat event untuk objek yang tidak pernah berpindah posisi, jadi truk yang sudah
  terparkir sejak awal rekaman tidak menghasilkan event meski terdeteksi.
- `stationary.threshold` harus lebih besar dari `loitering_time × fps` agar alert loitering muncul.

## Keterbatasan

- Data utama berasal dari satu site (armada CAT 777D). Untuk site baru, hasil terbaik didapat dengan
  fine-tune memakai beberapa ratus frame dari kamera site tersebut.
- Status muatan paling andal bila bak terlihat dari atas atau samping-atas. Dari sudut rendah, atau untuk
  material dengan tampilan sangat berbeda, sering tidak terdeteksi.
- Class `empty_load` paling lemah karena contohnya paling sedikit (244 kotak, dibanding 4.303 untuk
  `truck`).
- Wheel loader tidak dilabeli sebagai class tersendiri; mesin ini sengaja dijadikan contoh negatif agar
  tidak terdeteksi sebagai truk maupun excavator.
- Class `bed_raised` baru mengenal lima sudut kamera. Dari enam rekaman dumping yang tidak dilatih,
  hanya satu yang terdeteksi baik; rekaman berdebu tebal atau truk yang tertutup sebagian masih gagal.

## Dataset

3.578 gambar unik (label excavator memakai anotasi bawaan rf100 ditambah hasil review manual):

| Sumber | Gambar | Lisensi |
|---|---|---|
| [Mining truck V1.4](https://universe.roboflow.com/minitruck/mining-truck-v1.4) (site asli) | 430 | CC BY 4.0 |
| [Roboflow 100 – excavators](https://universe.roboflow.com/roboflow-100/excavators-czvg9) | 2.655 | CC BY 4.0 |
| Frame video publik (loading, hauling, malam), dilabeli dan diperiksa manual | 290 | hak cipta pemilik masing-masing |
| Frame video publik (adegan dumping), dilabeli setengah manual lalu ditinjau | 203 | hak cipta pemilik masing-masing |

Dataset publik dipakai untuk menambah variasi truk, sekaligus sebagai contoh negatif (excavator dan wheel
loader) agar tidak ikut terdeteksi sebagai truk. Karena sebagian data berasal dari video publik, model ini
ditujukan untuk prototipe dan penggunaan internal.

Daftar sumber per versi, lengkap dengan link dan jumlah gambar yang terpakai, ada di
[`docs/sumber-dataset.md`](docs/sumber-dataset.md).
