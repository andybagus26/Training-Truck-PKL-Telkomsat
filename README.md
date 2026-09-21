# Deteksi Truk Tambang dengan YOLOv9 + Frigate NVR

Model deteksi objek untuk memantau truk tambang dari kamera CCTV: mendeteksi truk dan status muatannya
(bermuatan / kosong), lalu dijalankan di [Frigate NVR](https://frigate.video) sebagai custom detector.

Model dilatih di Mac (Apple Silicon, MPS) dan dijalankan dengan ONNX Runtime + CoreML.

## Spesifikasi model

| | |
|---|---|
| Arsitektur | YOLOv9-t (Ultralytics 8.4), ~2 juta parameter |
| Input | 320×320, NCHW, RGB, nilai 0–1 |
| Output | `[1, 7, 2100]` — `cx, cy, w, h` (piksel) + 3 skor class, tanpa NMS |
| Class | `truck`, `full_load`, `empty_load` |
| Kecepatan | ~2 ms/gambar (CoreML, M1 Pro); ~14 ms per permintaan lewat Frigate |

Model siap pakai ada di `models/`.

## Hasil

| Pengujian | mAP50 | mAP50-95 |
|---|---|---|
| Test set site asli (43 gambar) | 0.995 | 0.845 |
| Test set site asli versi malam (sintetis) | 0.995 | 0.817 |
| Test set tambang lain (rf100, class `truck`) | 0.805 | 0.606 |

Pengujian pada video yang tidak dipakai saat training:

| Video | Truk terdeteksi | Muatan terdeteksi |
|---|---|---|
| Loading di quarry (kamera statis) | 24/24 frame | 22/24 frame |
| Operasi malam hari | 24/24 frame | — |
| Truk melintas di jalan hauling | 22/24 frame | 0/24 frame |

## Struktur

```
scripts/          Script training, pembuatan dataset, pelabelan, dan evaluasi
notebooks/        Notebook langkah demi langkah (setup, dataset, training, export ONNX)
models/           Model siap pakai (ONNX untuk Frigate + bobot PyTorch)
frigate/          Konfigurasi Frigate dan patch untuk Apple Silicon detector
```

Folder `datasets/`, `runs/`, `weights/`, dan `export/` tidak ikut di-commit karena besar,
dan bisa dibuat ulang dengan script di bawah.

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
  path: /models/mining_truck_yolov9t_320_v4.onnx
  labelmap_path: /models/labelmap.txt

objects:
  track: [truck, full_load, empty_load]
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
- Truk yang sedang menumpahkan muatan (bak terangkat) belum terdeteksi dengan baik.

## Dataset

3.375 gambar unik:

| Sumber | Gambar | Lisensi |
|---|---|---|
| [Mining truck V1.4](https://universe.roboflow.com/minitruck/mining-truck-v1.4) (site asli) | 430 | CC BY 4.0 |
| [Roboflow 100 – excavators](https://universe.roboflow.com/roboflow-100/excavators-czvg9) | 2.655 | CC BY 4.0 |
| Frame video publik (loading, hauling, malam), dilabeli dan diperiksa manual | 290 | hak cipta pemilik masing-masing |

Dataset publik dipakai untuk menambah variasi truk, sekaligus sebagai contoh negatif (excavator dan wheel
loader) agar tidak ikut terdeteksi sebagai truk. Karena sebagian data berasal dari video publik, model ini
ditujukan untuk prototipe dan penggunaan internal.
