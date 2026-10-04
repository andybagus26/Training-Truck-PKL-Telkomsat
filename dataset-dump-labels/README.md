# Anotasi rekaman dumping (class `bed_raised`)

Kotak saja, tanpa gambar — hak cipta videonya tetap pada pemiliknya. Daftar sumber videonya ada di
[`docs/sumber-dataset.md`](../docs/sumber-dataset.md).

Anotasi ini adalah tambahan data untuk model v6: dataset v5 di
[`dataset-v5-labels/`](../dataset-v5-labels/) ditambah class kelima, `bed_raised`, yang disusun oleh
`scripts/build_dataset_v6.py`.

| Berkas | Isi |
|---|---|
| `bed_raised.json` | Kotak bak truk yang sedang terangkat, 221 frame pada 5 rekaman (43, 23, 49, 47, dan 59 frame) |
| `truck.json` | Kotak truk untuk 2 rekaman yang model v5-nya gagal mengenali truk berbak terangkat, 102 frame |

Frame yang benar-benar masuk dataset bisa lebih sedikit dari isi berkas ini, karena
`build_dataset_v6.py` melewati frame yang truknya tidak terkotaki.

Bentuknya `{ "<id video youtube>": { "<nomor frame>": [x1, y1, x2, y2] } }`, dengan koordinat relatif
0–1 terhadap ukuran frame. Nomor frame mengacu pada pengambilan 2 frame per detik dari video aslinya:

```bash
ffmpeg -i <video>.mp4 -vf "fps=2,scale=640:-2" "<id>_%04d.jpg"
```

## Memakainya untuk membangun dataset v6

`scripts/build_dataset_v6.py` membaca anotasi ini dari `datasets/dump-raw/` dengan nama yang berbeda,
jadi berkasnya perlu ditempatkan dulu:

| Berkas di sini | Ditempatkan sebagai |
|---|---|
| `bed_raised.json` | `datasets/dump-raw/boxes.json` |
| `truck.json` | `datasets/dump-raw/boxes_truck.json` |
| frame hasil `ffmpeg` di atas | `datasets/dump-raw/frames/<id>_<nomor>.jpg` |

Dataset v5 harus sudah ada di `datasets/mining-truck-v5` (lihat
[`dataset-v5-labels/`](../dataset-v5-labels/)); hasilnya ditulis ke `datasets/mining-truck-v6`.

Cara anotasi ini dibuat — satu kotak manual per adegan lalu dilacak dan ditinjau — dijelaskan di
[`riwayat-model.md`](../docs/riwayat-model.md), bersama dua cara otomatis yang sudah dicoba dan gagal.
