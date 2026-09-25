# Label dataset v5 (tanpa gambar)

Folder ini berisi seluruh anotasi yang dipakai untuk melatih model v5, dalam format YOLO
(`class cx cy w h`, nilai relatif 0–1), beserta `data.yaml` dan `manifest.csv`.

**Gambarnya sengaja tidak disertakan.** Sebagian berasal dari frame video publik yang hak ciptanya
dipegang pemilik kanal masing-masing, sehingga tidak layak didistribusikan ulang di sini. Gambar dari
Roboflow (CC BY 4.0) juga tidak disertakan agar repositori tetap ringan — lebih baik diambil langsung
dari sumbernya.

## Isi

| | |
|---|---|
| Label | 5.307 file `.txt` (train 4.648, valid 472, test 187) |
| Class | `truck`, `full_load`, `empty_load`, `excavator` |
| `manifest.csv` | Daftar tiap label: split, sumber, asal, apakah versi malam sintetis, salinan ke berapa, dan jumlah kotak |

## Arti nama file

| Pola nama | Asal | Cara mendapatkan gambarnya |
|---|---|---|
| `rf100_<nama>.txt` | [roboflow-100/excavators](https://universe.roboflow.com/roboflow-100/excavators-czvg9) versi 2 | Unduh dataset, gambar bernama `<nama>.jpg` |
| `yt_<id_video>_<detik>.txt` | Frame video YouTube | Ambil frame pada detik tersebut dari video dengan id itu |
| lainnya | [minitruck/mining-truck-v1.4](https://universe.roboflow.com/minitruck/mining-truck-v1.4) | Unduh dataset, gambar dengan nama sama |
| akhiran `_night` | Versi malam sintetis | Hasil `scripts/night_aug.py` dari gambar aslinya |
| akhiran `_dup2`, `_r1`, … | Salinan untuk oversampling | Gambar yang sama, hanya digandakan saat training |

Daftar video lengkap beserta link ada di [`../docs/sumber-dataset.md`](../docs/sumber-dataset.md).

## Membangun ulang dataset

1. Unduh dua dataset Roboflow di atas dalam format YOLOv9 (lihat notebook dan
   `scripts/build_dataset_v2.py`).
2. Ambil frame video dengan `scripts/autolabel_yt.py`. Nama file label sudah memuat id video dan detik
   pengambilan, jadi frame yang sama bisa diambil ulang persis.
3. Buat versi malam dengan `scripts/night_aug.py`, lalu gandakan gambar site dan frame video sesuai
   kolom `salinan` di `manifest.csv`.
4. Letakkan gambar di `train/images`, `valid/images`, `test/images` di samping folder label, lalu
   sesuaikan baris `path` di `data.yaml`.

Label di sini adalah hasil akhir setelah seluruh pemeriksaan manual, jadi tidak perlu mengulang proses
review.
