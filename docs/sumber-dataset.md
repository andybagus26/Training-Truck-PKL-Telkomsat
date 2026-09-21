# Sumber dataset

Rincian asal seluruh data yang dipakai pada model v1 sampai v4, beserta jumlah gambar yang benar-benar
masuk ke dataset akhir (setelah pemeriksaan manual).

## Ringkasan

| Versi | Sumber baru | Gambar | Total kumulatif |
|---|---|---|---|
| v1 | Roboflow — Mining truck V1.4 | 430 | 430 |
| v2 | Roboflow 100 — excavators | 2.655 | 3.085 |
| v3 | 6 video publik (adegan loading) | 198 | 3.283 |
| v4 | 5 video publik (malam & hauling) | 92 | 3.375 |

Selain itu, v4 memakai 854 gambar malam sintetis yang dibuat dari gambar di atas
(`scripts/night_aug.py`), jadi bukan data baru.

## v1 — dataset site

| Dataset | Gambar | Lisensi |
|---|---|---|
| [minitruck/mining-truck-v1.4](https://universe.roboflow.com/minitruck/mining-truck-v1.4) | 430 | CC BY 4.0 |

Diunduh melalui Roboflow SDK dalam format YOLOv9. Dataset ini juga tersedia sebagai salinan di
workspace lain ([ai-rice-quality/mining-truck-v1.4-yypbr](https://universe.roboflow.com/ai-rice-quality/mining-truck-v1.4-yypbr)),
dengan isi gambar yang sama.

Versi 3 dan 5 dari dataset tersebut memuat 1.031 gambar, tetapi tambahannya adalah hasil augmentasi
Roboflow dari 430 gambar yang sama, sehingga yang dipakai adalah gambar aslinya saja.

## v2 — dataset publik untuk variasi dan contoh negatif

| Dataset | Gambar | Lisensi |
|---|---|---|
| [roboflow-100/excavators](https://universe.roboflow.com/roboflow-100/excavators-czvg9) (versi 2) | 2.655 | CC BY 4.0 |

Class `dump truck` dipetakan menjadi `truck`. Class `EXCAVATORS` dan `wheel loader` sengaja tidak
dilabeli, sehingga 1.619 gambar di antaranya berfungsi sebagai contoh negatif.

Beberapa dataset lain sempat diunduh untuk dipertimbangkan, tetapi tidak dipakai:
[ryf09681065-gmail-com/mining-truck](https://universe.roboflow.com/ryf09681065-gmail-com/mining-truck)
(objek terlalu kecil, sudut drone),
[1-xhyzh/raven-dump-truck](https://universe.roboflow.com/1-xhyzh/raven-dump-truck-5gtxn) (foto katalog,
bukan truk tambang), dan
[excavator-sampling/heavy-equipment](https://universe.roboflow.com/excavator-sampling/heavy-equipment)
(berisi truk yang tidak dilabeli, berisiko mengajarkan hal yang keliru).

## v3 — video adegan loading

Frame diambil tiap 1,5 detik, dilabeli otomatis, lalu seluruh crop truk diperiksa manual.

| Video | Kanal | Frame terpakai |
|---|---|---|
| [Hitachi EX2500-6 Excavator Loading a Caterpillar 777D](https://www.youtube.com/watch?v=bYZW7DvZvY8) | Alf188188 | 55 |
| [Caterpillar 990 loading Caterpillar 777D](https://www.youtube.com/watch?v=VVDvgY-H1Ck) | Liebherr960 | 48 |
| [Excavator PC 2000 & Caterpillar 6030 loading truck Cat 777](https://www.youtube.com/watch?v=_N5oR7H-qRI) | Mr_Dompit | 42 |
| [Cat 775 Hauling Shot Rock To The Primary Crusher](https://www.youtube.com/watch?v=K6zCCLLKbKk) | Eat Sleep Dig Repeat | 31 |
| [Caterpillar 992K Wheel Loader Loading Caterpillar 777F Dumpers](https://www.youtube.com/watch?v=E9Twh20nseo) | Mega Machines Channel | 19 |
| [Time lapse fill cat 777](https://www.youtube.com/watch?v=92din2kUd4Y) | scott b | 3 |

Dua video lain ikut diunduh tetapi tidak ada frame yang lolos pemeriksaan
([PC 2000 Chargement 100T Cat 777](https://www.youtube.com/watch?v=SmdUCpNw5nI) dan
[Loading The Caterpillar 777C Dumper](https://www.youtube.com/watch?v=EHgJg4Z7fHg)) — kotak truk dari
pelabel otomatis tercampur dengan excavator atau trailer.

Catatan untuk video Cat 775: detik 0–31 dipakai sebagai video uji dan **dikecualikan** saat pengambilan
frame; hanya bagian lain video tersebut yang masuk data training.

## v4 — video malam dan jalan hauling

| Video | Kanal | Frame terpakai |
|---|---|---|
| [Komatsu HD785, CAT 777D & 777E Dump Trucks Working On A Busy Coal Mine](https://www.youtube.com/watch?v=iECoOj9_qCk) | Coal Mine Operations | 29 |
| [Shovel Liebherr 996 double loading Komatsu 830E](https://www.youtube.com/watch?v=yMpLwUKBt5w) | Giant Machine | 28 |
| [INSANE Night Mining Action! Komatsu PC2000 at Full Power](https://www.youtube.com/watch?v=stn_naWb_l4) | Fortysix Channel | 17 |
| [Mining night operation. Caterpillar 797B](https://www.youtube.com/watch?v=fRP15YVjR6A) | Quarry Works | 16 |
| [LIEBHERR 996 Loading night shift](https://www.youtube.com/watch?v=RSNn6em4WNA) | Giant Machine | 2 |

Frame dari video publik dipakai untuk prototipe dan penggunaan internal. Hak cipta video tetap pada
kanal masing-masing, dan frame-nya tidak disertakan di repositori ini.

## Video untuk pengujian (tidak dipakai training)

| Video | Sumber | Dipakai untuk |
|---|---|---|
| Cat 775 detik 0–31 | kanal Eat Sleep Dig Repeat (lihat di atas) | Uji adegan loading |
| Rigid haul truck Perlini | [Pexels 20712739](https://www.pexels.com/video/truck-fotage-20712739/) (Pexels License) | Uji truk bermuatan di jalan |
| Truk melintas di jalan hauling & operasi malam | preview video stok (watermark) | Uji generalisasi di tambang lain |

Seluruh video di tabel ini tidak pernah masuk data training, sehingga angka pengujian pada
[`riwayat-model.md`](riwayat-model.md) bisa dibaca apa adanya.
