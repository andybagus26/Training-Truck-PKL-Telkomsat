# Anotasi rekaman dumping (class `bed_raised`)

Kotak saja, tanpa gambar — hak cipta videonya tetap pada pemiliknya. Daftar sumber videonya ada di
[`docs/sumber-dataset.md`](../docs/sumber-dataset.md).

| Berkas | Isi |
|---|---|
| `bed_raised.json` | Kotak bak truk yang sedang terangkat, 203 frame pada 5 rekaman |
| `truck.json` | Kotak truk untuk 2 rekaman yang model v5-nya gagal mengenali truk berbak terangkat |

Bentuknya `{ "<id video youtube>": { "<nomor frame>": [x1, y1, x2, y2] } }`, dengan koordinat relatif
0–1 terhadap ukuran frame. Nomor frame mengacu pada pengambilan 2 frame per detik dari video aslinya:

```bash
ffmpeg -i <video>.mp4 -vf "fps=2,scale=640:-2" "<id>_%04d.jpg"
```

Cara anotasi ini dibuat — satu kotak manual per adegan lalu dilacak dan ditinjau — dijelaskan di
[`riwayat-model.md`](../docs/riwayat-model.md), bersama dua cara otomatis yang sudah dicoba dan gagal.
