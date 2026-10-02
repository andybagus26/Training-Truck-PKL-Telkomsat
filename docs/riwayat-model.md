# Riwayat model v1 → v6

Daftar sumber data tiap versi beserta link ada di [`sumber-dataset.md`](sumber-dataset.md).

Catatan perkembangan model: apa yang ditambahkan di tiap versi, alasannya, dan hasil pengujiannya.
Semua versi memakai arsitektur yang sama (YOLOv9-t, input 320×320). Jumlah class bertambah seiring
bertambahnya tugas: tiga di v1–v4 (`truck`, `full_load`, `empty_load`), `excavator` di v5, dan
`bed_raised` di v6.

## Ringkasan

### Perkembangan tiap versi

| | v1 | v2 | v3 | v4 | v5 | v6 |
|---|---|---|---|---|---|---|
| Gambar unik | 430 | 3.085 | 3.283 | 3.375 | 3.375 | 3.578 |
| Jumlah class | 3 | 3 | 3 | 3 | 4 | 5 |
| Class baru | — | — | — | — | `excavator` | `bed_raised` |
| Bobot awal | COCO | v1 | v2 | v3 | model excavator sementara | v5 |
| Yang ditambahkan | dataset site | data publik & contoh negatif | adegan loading | kondisi malam | label excavator di seluruh data | rekaman dumping |
| Masalah yang dijawab | — | kotak seukuran frame penuh | truk tak terdeteksi saat dimuat | gagal total di malam hari | excavator dikira truk | dumping tak bisa dibedakan dari berhenti |

Semua versi memakai transfer learning. Titik awalnya bobot YOLOv9-t hasil latihan di COCO, lalu tiap
versi melanjutkan bobot versi sebelumnya — bukan mengulang dari nol. Tanpa itu, dataset sebesar ini
jauh dari cukup untuk melatih detektor, apalagi `bed_raised` yang hanya punya 203 frame asli.

### Kemampuan v1–v6

Empat ukuran di bawah ini memakai bahan uji yang sama sejak v1, jadi angkanya bisa dibandingkan lurus
antar versi.

| | v1 | v2 | v3 | v4 | v5 | v6 |
|---|---|---|---|---|---|---|
| Test site asli, mAP50 | 0.995 | 0.995 | 0.995 | 0.995 | 0.995 | **0.995** |
| Test site asli versi malam, mAP50 | — | — | 0.786 | 0.995 | 0.995 | **0.995** |
| Video loading quarry: frame dengan truk | 20/24 | 5/24 | 22/24 | 24/24 | 24/24 | **24/24** |
| Video malam: frame dengan truk | — | — | 1/24 | 24/24 | 24/24 | **23/24** |

Tiga hal yang perlu dibaca bersama tabel itu:

**Angka v1 pada video quarry menipu.** Truk memang terdeteksi di 20 frame, tetapi disertai 26 kotak
salah seukuran frame penuh. Pada v6, kotak raksasa semacam itu tidak ada sama sekali di kedua video.

**Selisih satu frame pada baris terakhir bukan penurunan.** Saat diukur ulang bersama v6, model v5
juga menghasilkan 23/24 pada video yang sama — bukan 24/24 seperti tercatat dulu. Selisihnya berasal
dari cara frame diambil dari video, bukan dari kemampuan modelnya.

**Angka v5 ke bawah tidak bisa dihitung ulang.** Set ujinya disusun dari dataset v2 dan v3 yang sudah
dihapus saat pembersihan. Kolom v6 diisi dengan mengukur ulang memakai bahan yang masih ada: set site
asli 43 gambar, versi malam sintetisnya, dan dua video uji di folder media Frigate.

### Kemampuan di tambang lain (set rf100)

Ukuran ini **tidak masuk tabel di atas**, karena set rf100 yang lama ikut terhapus dan set yang ada
sekarang isinya berbeda. Membandingkan angkanya dengan kolom v1–v5 akan menyesatkan.

Pada set rf100 yang ada sekarang (144 gambar di test set v6), diukur untuk kedua model sekaligus:

| | v5 | v6 |
|---|---|---|
| `truck` mAP50 | 0.871 | 0.856 |
| `excavator` mAP50 | 0.851 | 0.851 |

Sebagai gambaran kasar, pada set rf100 yang lama angka `truck` adalah 0.207 di v1 lalu naik ke 0.840
di v2, dan turun perlahan menjadi 0.805 di v4 dan v5. Arahnya sama dengan yang terlihat sekarang:
penambahan data yang sangat spesifik untuk site tujuan memang menggeser model menjauh sedikit dari
tambang lain.

### v5 dibanding v6

Diukur pada test set yang sama persis (187 gambar). Rinciannya ada di
[`hasil-training.md`](hasil-training.md).

| | v5 | v6 |
|---|---|---|
| Gabungan, mAP50 | 0.891 | 0.886 |
| `truck` mAP50 / recall | 0.915 / 0.720 | 0.903 / **0.766** |
| `excavator` mAP50 / recall | 0.851 / 0.789 | 0.850 / **0.824** |
| Site asli (43 gambar) | 0.995 | 0.995 |
| Site asli versi malam | 0.995 | 0.995 |
| Truk dikenali saat menumpah muatan | 0–100%, rata-rata rendah | **91–100%** |
| Bak terangkat salah dibaca `excavator` | sampai 37% frame | **0%** |

Penambahan class menurunkan mAP gabungan 0,005 — masih dalam rentang wajar — sementara recall naik
dan kesalahan pada adegan dumping hilang.

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

## v5 — menambah class excavator

**Kebutuhan baru:** model harus mendeteksi truk sekaligus excavator. Sampai v4, excavator justru sengaja
dibiarkan tanpa label sebagai contoh negatif, jadi label excavator harus ditambahkan ke seluruh dataset,
bukan sekadar menambah data baru.

**Langkahnya:**

1. Class `EXCAVATORS` pada dataset rf100 (1.475 kotak) yang selama ini dibuang, dihidupkan kembali.
2. Dilatih model sementara di data rf100 saja (20 epoch) sampai bisa mengenali excavator
   (mAP50 0.816), lalu dipakai untuk mengusulkan kotak pada 720 gambar site dan video
   (`scripts/propose_excavator.py`).
3. Dari 97 gambar berusulan, **48 diterima** setelah diperiksa manual. Sisanya ditolak karena kotaknya
   ikut menutupi truk, atau salah objek — misalnya bak truk yang sedang terangkat dikira excavator.
4. Kotak "bukan truk" dari pemeriksaan v3/v4 diperiksa ulang: dari 115 kotak, **55 ternyata excavator**;
   sisanya wheel loader yang memang tidak perlu label.
5. 32 gambar yang excavator-nya tidak bisa dikotaki dengan baik dikeluarkan dari training, agar model
   tidak belajar bahwa excavator adalah latar belakang.

Total 2.208 kotak excavator di data training (termasuk salinan dan versi malam).

**Training:** fine-tune dari model sementara, 40 epoch, lr 0.0008.

**Hasil (test set gabungan 187 gambar):**

| Class | v4 mAP50 | v5 mAP50 |
|---|---|---|
| truck | 0.867 | **0.915** |
| full_load | 0.930 | **0.942** |
| empty_load | 0.855 | 0.855 |
| excavator | — | **0.851** |

Deteksi truk justru naik karena excavator tidak lagi salah terdeteksi sebagai truk. Pada video malam,
excavator yang sebelumnya dihitung sebagai truk kini dikenali dengan benar (85–88% di Frigate).

## v6 — menambah class bed_raised

**Kebutuhan baru:** membedakan truk yang sedang menumpahkan muatan dari truk yang sekadar berhenti.
Sampai v5 tidak ada sinyal apa pun untuk itu. Diuji pada 205 frame dumping, model v5 tidak pernah
mengenali bak terangkat, dan pada satu rekaman malah membacanya sebagai `excavator` di 25 frame —
kelemahan yang sudah tercatat sejak v3 tapi belum pernah ditangani.

**Mencari datanya.** Dataset asli ternyata tidak membantu: class `dumping_soil` (260 gambar) bukan
adegan menumpahkan muatan, melainkan truk tampak samping dengan bak mendatar di satu pos yang sama,
hanya divariasi siang dan malam. Itu sebabnya dulu digabung menjadi `truck`. Rekaman uji yang ada pun
tidak punya satu pun adegan bak terangkat, termasuk `cat775_crusher_demo` yang ternyata adegan loading.

Dataset publik juga tidak menolong. ACID dan sejenisnya hanya mendeteksi *jenis* alat, bukan
keadaannya; dataset riset yang beranotasi aksi truk-excavator (UIUC, 479 video) tidak terbuka untuk
diunduh. Jadi datanya dikumpulkan sendiri dari video publik.

**Melabelinya.** Dari 15 video yang diperiksa, 5 adegan layak dipakai. Dua cara otomatis dicoba dan
gagal, keduanya dicatat di sini supaya tidak diulang:

1. Detektor open-vocabulary (YOLO-World, prompt "raised dump bed of a truck" dan sejenisnya) justru
   tidak menghasilkan usulan apa pun pada frame yang paling jelas.
2. Model benih satu class yang dilatih dari 115 frame di 3 adegan tidak bisa melabeli adegan lain:
   usulannya menempel di tumpukan batu, pipa, dan pagar.

Yang dipakai akhirnya setengah manual: satu kotak digambar manual per adegan, lalu dilacak maju dan
mundur dengan pencocokan template multi-skala (`scripts/track_box.py`), dan hasilnya ditinjau bergambar
(`scripts/review_boxes.py`). Peninjauan itu menangkap dua kesalahan yang akan merusak model bila lolos:
frame saat bak sebenarnya belum naik (itu muatan penuh, bukan dumping), dan frame saat kotak sudah
melenceng setelah bak turun.

Tiga rekaman dibuang setelah ditinjau. Satu karena truknya tertutup tepi timbunan sehingga yang
terlihat hanya debu, satu lagi karena kotak pelacakan berakhir menempel di awan debu dan tembok —
kalau dipakai, model akan belajar bahwa debu berarti bak terangkat, lalu memunculkan dumping palsu.

Hasilnya 203 frame dari 5 adegan. Label `truck` untuk dua rekaman ikut dilacak manual, karena di
situ v5 gagal total mengenali truknya (0% dan 5%); seluruh prediksi `excavator` pada frame dumping
dibuang karena memang salah.

**Training:** fine-tune dari v5, 50 epoch, lr 0.001, 320×320, 5.161 gambar latih (frame dumping
digandakan 3× agar tidak tenggelam). Selesai dalam 3,1 jam di M1 Pro.

**Hasil (test set gabungan 187 gambar):**

| Class | v5 mAP50 | v6 mAP50 |
|---|---|---|
| truck | 0.915 | 0.903 |
| full_load | 0.942 | 0.936 |
| empty_load | 0.855 | 0.855 |
| excavator | 0.851 | 0.850 |
| gabungan | 0.891 | 0.886 |

Turun tipis dan masih dalam rentang wajar. Sebagai gantinya recall naik: truck 0.720 → 0.766,
excavator 0.789 → 0.824.

**Pada rekaman dumping**, perubahannya besar:

| Rekaman | v5 kenali truk | v5 salah baca excavator | v6 kenali truk | v6 salah excavator | v6 bed_raised |
|---|---|---|---|---|---|
| Cat 793D waste dump | 0% | 37% | 100% | 0% | 100% |
| Nevada waste dump | 5% | 0% | 100% | 0% | 100% |
| Crusher feeder | 65% | 8% | 91% | 0% | 100% |
| Komatsu 930E | 100% | 4% | 100% | 0% | 100% |
| Tipper jalan raya | 79% | 4% | 100% | 0% | 100% |

**Positif palsu nol.** Pada 187 gambar test dan 126 frame rekaman demo Frigate, `bed_raised` tidak
pernah muncul pada truk berbak normal.

**Yang masih lemah:** generalisasi ke sudut kamera asing. Dari 6 rekaman dumping yang tidak dilatih,
hanya 1 yang terdeteksi baik; yang berdebu tebal, yang truknya tertutup, dan yang baknya hanya
terlihat sebagian semuanya gagal. Ini konsekuensi langsung dari hanya 5 adegan yang tersedia, dan
baru bisa diperbaiki dengan rekaman dari lokasi sebenarnya.

---

## Yang masih belum selesai

Diperbarui setelah v6.

- **`bed_raised` baru kenal lima sudut kamera.** Dari 6 rekaman dumping yang tidak dilatih, hanya 1
  yang terdeteksi baik; yang berdebu tebal, truknya tertutup tepi timbunan, atau baknya hanya
  terlihat sebagian masih gagal. Ini akibat langsung dari sedikitnya rekaman dumping yang bisa
  dicari — hanya 203 frame dari 5 adegan.
- **`empty_load` tetap class terlemah**, 244 kotak di seluruh dataset dibanding 4.303 untuk `truck`.
  Pada test set, mAP50-nya 0.855, terendah bersama `excavator`.
- **Muatan dari sudut rendah.** Pada video truk melintas di jalan hauling, truk terdeteksi tetapi
  muatannya tidak, bahkan pada ambang 0.05. Material yang dibawa sangat berbeda dari seluruh contoh
  muatan di data training. Catatan ini berasal dari pengujian v4 dan belum diukur ulang di v6.
- **Kemampuan di tambang lain** tidak membaik: pada set rf100, `truck` 0.871 di v5 menjadi 0.856 di
  v6. Penambahan data yang sangat spesifik memang cenderung menggeser model ke arah site tujuan.

Perbaikan paling efektif untuk semua poin di atas sama seperti sejak v3: beberapa ratus frame
berlabel dari kamera site yang dituju, bukan penambahan data publik.

## Catatan kebersihan data

- Video yang dipakai untuk menguji tidak pernah masuk data training. Untuk video Cat 775, segmen demo
  (detik 0–31) dikecualikan saat pengambilan frame, sementara bagian lain video tersebut ikut dilatih —
  ini setara dengan alur "ambil sedikit frame dari site tujuan, lalu fine-tune".
- Test set site asli (43 gambar) tidak berubah sejak v1, sehingga angkanya bisa dibandingkan antarversi.
- Label muatan pada dataset rf100 berasal dari prediksi model v1, bukan pemeriksaan manual, sehingga
  angka `full_load`/`empty_load` pada test rf100 perlu dibaca dengan hati-hati.

---
