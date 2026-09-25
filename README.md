# Deteksi Truk Tambang dengan YOLOv9 + Frigate NVR

Model deteksi objek untuk memantau aktivitas tambang dari kamera CCTV: mendeteksi truk beserta status
muatannya (bermuatan / kosong) dan excavator, lalu dijalankan di [Frigate NVR](https://frigate.video)
sebagai custom detector.

Model dilatih di Mac (Apple Silicon, MPS) dan dijalankan dengan ONNX Runtime + CoreML.

## Spesifikasi model

| | |
|---|---|
| Arsitektur | YOLOv9-t (Ultralytics 8.4), ~2 juta parameter |
| Input | 320×320, NCHW, RGB, nilai 0–1 |
| Output | `[1, 8, 2100]` — `cx, cy, w, h` (piksel) + 4 skor class, tanpa NMS |
| Class | `truck`, `full_load`, `empty_load`, `excavator` |
| Kecepatan | ~2 ms/gambar (CoreML, M1 Pro); ~14 ms per permintaan lewat Frigate |

Model siap pakai ada di `models/`.

## Hasil

Test set gabungan (187 gambar: 43 dari site asli + 144 dari tambang lain):

| Class | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|
| truck | 0.976 | 0.720 | 0.915 | 0.741 |
| full_load | 0.993 | 0.891 | 0.942 | 0.745 |
| empty_load | 0.957 | 0.857 | 0.855 | 0.721 |
| excavator | 0.906 | 0.789 | 0.851 | 0.659 |

Pengujian pada video yang tidak dipakai saat training (24 frame per video):

| Video | truck | excavator | muatan |
|---|---|---|---|
| Loading di quarry (kamera statis) | 24 | 18 | 23 |
| Operasi malam hari | 26 | 24 | — |
| Truk melintas di jalan hauling | 31 | — | 0 |

## Struktur

```
scripts/          Script training, pembuatan dataset, pelabelan, dan evaluasi
notebooks/        Notebook langkah demi langkah (setup, dataset, training, export ONNX) — model v1
models/           Model siap pakai (ONNX untuk Frigate + bobot PyTorch)
frigate/          Konfigurasi Frigate dan patch untuk Apple Silicon detector
docs/             Riwayat model, sumber dataset, dan grafik hasil training
dataset-v5-labels/  Anotasi lengkap dataset v5 (tanpa gambar) + panduan membangun ulang
backend/          API FastAPI yang menyajikan data deteksi Frigate ke sistem lain
```

- [`docs/riwayat-model.md`](docs/riwayat-model.md) — perkembangan v1 sampai v5 beserta alasan tiap penambahan data
- [`docs/sumber-dataset.md`](docs/sumber-dataset.md) — daftar lengkap sumber data tiap versi, dengan link
- [`docs/hasil-training.md`](docs/hasil-training.md) — grafik training, confusion matrix, dan contoh prediksi
- [`backend/README.md`](backend/README.md) — daftar endpoint API dan cara menjalankannya

Folder `datasets/`, `runs/`, `weights/`, dan `export/` tidak ikut di-commit karena besar,
dan bisa dibuat ulang dengan script di bawah. Anotasinya sendiri tersedia lengkap di
[`dataset-v5-labels/`](dataset-v5-labels/) — gambarnya tidak disertakan karena sebagian berasal dari
video publik yang hak ciptanya dipegang pemiliknya.

## Menjalankan

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
echo "ROBOFLOW_API_KEY=<api-key-anda>" > .env
```

Dataset dasar diunduh dari Roboflow (lihat notebook), lalu:

```bash
# Training
.venv/bin/python scripts/train.py --data datasets/mining-truck-v4/data.yaml --epochs 40 --batch 32

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

## Integrasi Frigate

Salin isi `models/` ke folder model Frigate, lalu pakai konfigurasi di `frigate/config.yml`:

```yaml
model:
  model_type: yolo-generic
  width: 320
  height: 320
  input_tensor: nchw
  input_dtype: float
  path: /models/mining_truck_yolov9t_320_v5.onnx
  labelmap_path: /models/labelmap_v5.txt

objects:
  track: [truck, full_load, empty_load, excavator]
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

## API untuk sistem lain

Folder [`backend/`](backend/) berisi API FastAPI yang mengambil data deteksi dari Frigate dan
menyajikannya kembali dalam bentuk yang lebih rapi, sehingga dashboard atau sistem lain tidak perlu
berhubungan langsung dengan Frigate.

```bash
.venv/bin/uvicorn backend.app.main:app --port 8000
# dokumentasi interaktif: http://localhost:8000/docs
```

Endpoint utama: `/detections` (dengan penyaringan kamera, label, waktu, dan skor), `/summary`,
`/cameras`, `/stats`, serta endpoint gambar `/detections/{id}/snapshot` dan
`/cameras/{camera}/latest`.

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
- Class `empty_load` paling lemah karena contohnya paling sedikit (102 kotak).
- Wheel loader tidak dilabeli sebagai class tersendiri; mesin ini sengaja dijadikan contoh negatif agar
  tidak terdeteksi sebagai truk maupun excavator.
- Truk yang sedang menumpahkan muatan (bak terangkat) belum terdeteksi dengan baik.

## Dataset

3.375 gambar unik (label excavator memakai anotasi bawaan rf100 ditambah hasil review manual):

| Sumber | Gambar | Lisensi |
|---|---|---|
| [Mining truck V1.4](https://universe.roboflow.com/minitruck/mining-truck-v1.4) (site asli) | 430 | CC BY 4.0 |
| [Roboflow 100 – excavators](https://universe.roboflow.com/roboflow-100/excavators-czvg9) | 2.655 | CC BY 4.0 |
| Frame video publik (loading, hauling, malam), dilabeli dan diperiksa manual | 290 | hak cipta pemilik masing-masing |

Dataset publik dipakai untuk menambah variasi truk, sekaligus sebagai contoh negatif (excavator dan wheel
loader) agar tidak ikut terdeteksi sebagai truk. Karena sebagian data berasal dari video publik, model ini
ditujukan untuk prototipe dan penggunaan internal.

Daftar sumber per versi, lengkap dengan link dan jumlah gambar yang terpakai, ada di
[`docs/sumber-dataset.md`](docs/sumber-dataset.md).
