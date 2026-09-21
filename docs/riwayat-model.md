# Riwayat model v1 → v4

Daftar sumber data tiap versi beserta link ada di [`sumber-dataset.md`](sumber-dataset.md).

Catatan perkembangan model: apa yang ditambahkan di tiap versi, alasannya, dan hasil pengujiannya.
Semua versi memakai arsitektur yang sama (YOLOv9-t, input 320×320, 3 class: `truck`, `full_load`, `empty_load`).

## Ringkasan

| | v1 | v2 | v3 | v4 |
|---|---|---|---|---|
| Gambar unik | 430 | 3.085 | 3.283 | 3.375 |
| Test site asli, mAP50 | 0.995 | 0.995 | 0.995 | 0.995 |
| Test tambang lain (rf100), `truck` mAP50 | 0.207 | 0.840 | 0.822 | 0.805 |
| Test site asli versi malam, mAP50 | — | — | 0.786 | 0.995 |
| Video loading quarry: frame dengan truk | 20/24* | 5/24 | 22/24 | 24/24 |
| Video malam: frame dengan truk | — | — | 1/24 | 24/24 |

\* v1 mendeteksi truk di 20 frame, tetapi disertai 26 kotak salah seukuran frame penuh.

---

## v1 — dataset site saja

**Data:** [Mining truck V1.4](https://universe.roboflow.com/minitruck/mining-truck-v1.4) dari Roboflow, 430 gambar.

Dataset aslinya punya 27 class. Sebagian besar adalah karakter nomor lambung (`0`–`9`, `A`, `G`, `H`, …)
berukuran 3–15 px pada input 320 — terlalu kecil untuk dideteksi, dan memang ditujukan untuk OCR, bukan
deteksi truk. Class yang dipakai disederhanakan menjadi tiga:

- `mining_truck` dan `dumping_soil` digabung menjadi `truck`. Keduanya ternyata menandai objek yang sama;
  setiap gambar hanya punya salah satunya, tidak pernah keduanya.
- `full_load` dan `empty_load` tetap.

Label aslinya campuran poligon dan kotak dalam satu file, yang membuat sebagian kotak salah terbaca,
sehingga semua dikonversi ke format kotak standar. Pembagian train/valid/test juga disusun ulang 70/20/10
secara stratified, karena pembagian bawaannya timpang (`empty_load` hanya 2 objek di test).

**Training:** 150 epoch, AdamW, lr 0.001 (cosine), batch 16. Hasil terbaik di epoch 133.

**Hasil:** sangat baik di site-nya sendiri (test mAP50 0.995) tetapi tidak bisa dipakai di luar itu:

- Sering menghasilkan kotak `truck` seukuran frame penuh. Penyebabnya, seluruh gambar training adalah
  hasil crop dekat yang truknya memenuhi frame, sehingga model belajar "area besar bertekstur tambang = truk".
- Hopper/trailer di site sendiri ikut terdeteksi sebagai truk.
- Di tambang lain hampir tidak berfungsi (rf100 `truck` mAP50 0.207).

---

## v2 — menambah variasi dan contoh negatif

**Tambahan data:** [Roboflow 100 – excavators](https://universe.roboflow.com/roboflow-100/excavators-czvg9),
2.655 gambar. Class `dump truck` dipetakan menjadi `truck`; excavator dan wheel loader sengaja
**tidak dilabeli**, sehingga 1.619 gambar berfungsi sebagai contoh negatif.

Label muatan pada dataset ini dibuat otomatis: tiap kotak truk di-crop, lalu model v1 dijalankan pada crop
tersebut (mirip distribusi data training v1), dan hanya prediksi dengan skor ≥ 0.7 yang dipakai.
Gambar site asli digandakan 3× agar tidak tenggelam oleh data baru, dan augmentasi zoom diperkuat
(`scale=0.9`) supaya model terbiasa melihat truk berukuran kecil.

**Training:** 80 epoch dari bobot COCO.

**Hasil:** kotak seukuran frame penuh hilang (26 → 0) dan kemampuan di tambang lain melonjak
(rf100 `truck` mAP50 0.207 → 0.840). Namun model menjadi terlalu berhati-hati pada adegan yang tidak
dikenalnya: di video truk sedang dimuat excavator, truk hanya terdeteksi di 5 dari 24 frame.

---

## v3 — adegan loading

**Tambahan data:** 198 frame dari 6 video publik berisi excavator/loader memuat haul truck.

Alur pelabelannya:

1. Frame diambil tiap 1,5 detik, frame yang nyaris sama dilewati (`scripts/autolabel_yt.py`).
2. Kotak truk dibuat otomatis oleh detektor COCO (YOLOv9-e), kotak muatan diusulkan model v1 pada crop truk.
3. Seluruh 635 crop truk **diperiksa manual** lewat lembar bernomor (`scripts/crop_review.py`).
   Kotak yang sebenarnya excavator, wheel loader, dozer, atau trailer dihapus; frame dengan kotak yang
   menggabungkan dua kendaraan dibuang seluruhnya (`scripts/apply_review.py`).

Hasil akhirnya 207 kotak `truck` dan 99 `full_load`, ditambah 93 area excavator/loader yang dibiarkan tanpa
label sebagai contoh negatif — persis kasus yang sebelumnya salah terdeteksi.

**Training:** fine-tune dari v2, 40 epoch, lr 0.0005.

**Hasil:** di video loading, truk terdeteksi di 22 dari 24 frame (v2: 5) dan muatan di 19 frame (v2: 1),
tanpa kotak salah. Akurasi posisi kotak di site asli juga naik (`truck` mAP50-95 0.918 → 0.954).

---

## v4 — kondisi malam

**Masalah:** pada video operasi malam hari, v3 hanya mendeteksi truk di 1 dari 24 frame. Hampir seluruh data
training diambil siang hari.

**Tambahan data:**

- 92 frame dari 5 video publik (operasi malam dan truk bermuatan di jalan hauling), melalui proses
  pemeriksaan manual yang sama: 469 crop diperiksa, menghasilkan 98 kotak `truck` dan 7 `full_load`.
- 854 gambar malam sintetis (`scripts/night_aug.py`): gambar siang digelapkan secara non-linear, saturasi
  diturunkan, ditambah noise sensor, pergeseran warna lampu, dan sumber cahaya buatan. Labelnya tidak berubah.

**Training:** fine-tune dari v3, berhenti otomatis di epoch 31 (hasil terbaik epoch 16).

**Hasil:**

| Pengujian | v3 | v4 |
|---|---|---|
| Video malam: frame dengan truk | 1/24 | 24/24 |
| Test site asli versi malam, mAP50 | 0.786 | 0.995 |
| Video loading quarry: truk / muatan | 22 / 19 dari 24 | 24 / 22 dari 24 |
| Test tambang lain (rf100), `truck` mAP50 | 0.822 | 0.805 |

---

## Yang masih belum selesai

- **Muatan dari sudut rendah.** Pada video truk melintas di jalan hauling, truk terdeteksi (22/24 frame)
  tetapi muatannya tidak sama sekali, bahkan pada ambang 0.05. Material yang dibawa (bijih abu-abu gelap)
  sangat berbeda dari seluruh contoh muatan di data training, dan hanya 7 contoh `full_load` baru yang
  lolos pemeriksaan di v4 — terlalu sedikit untuk mengubah perilaku model.
- **`empty_load`** tetap class terlemah: hanya 102 kotak di seluruh dataset.
- **Truk yang sedang menumpahkan muatan** (bak terangkat) jarang terdeteksi; adegan ini tidak ada di data training.
- **Kemampuan di tambang lain** turun tipis sejak v2 (rf100 `truck` 0.840 → 0.805), efek samping dari
  penambahan data yang sangat spesifik pada v3 dan v4.

Perbaikan paling efektif untuk semua poin di atas adalah beberapa ratus frame berlabel dari kamera site
yang dituju, bukan penambahan data publik.

## Catatan kebersihan data

- Video yang dipakai untuk menguji tidak pernah masuk data training. Untuk video Cat 775, segmen demo
  (detik 0–31) dikecualikan saat pengambilan frame, sementara bagian lain video tersebut ikut dilatih —
  ini setara dengan alur "ambil sedikit frame dari site tujuan, lalu fine-tune".
- Test set site asli (43 gambar) tidak berubah sejak v1, sehingga angkanya bisa dibandingkan antarversi.
- Label muatan pada dataset rf100 berasal dari prediksi model v1, bukan pemeriksaan manual, sehingga
  angka `full_load`/`empty_load` pada test rf100 perlu dibaca dengan hati-hati.
