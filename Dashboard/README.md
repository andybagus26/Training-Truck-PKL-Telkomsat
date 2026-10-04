# Dashboard Deteksi Truk Tambang

Tampilan pemantauan berbasis web: gambar tiap kamera dengan keadaan truknya, daftar deteksi, aktivitas
truk, dan beban mesin. Seluruh datanya diambil dari backend FastAPI ([`backend/`](../backend/)), tidak
langsung dari Frigate.

```
Frigate NVR  ──►  Backend FastAPI  ──►  Dashboard
(deteksi)         (rapikan & simpulkan)  (halaman ini)
```

Dashboard hanya berupa HTML, CSS, dan JavaScript tanpa library dari internet, jadi tidak ada yang perlu
di-install dan tampil sama di Windows maupun Mac. Yang berbeda di tiap sistem operasi hanya cara
menjalankan backend dan Frigate.

| Berkas | Isi |
|---|---|
| `index.html` | Kerangka halaman |
| `style.css` | Tampilan; tema terang atau gelap mengikuti setelan perangkat |
| `app.js` | Pengambilan data dari backend dan pembaruan tampilan |

## Menjalankan

Frigate harus sudah berjalan. Backend otomatis menyajikan folder ini di `/dashboard/` bila foldernya
ada, jadi cukup jalankan backend dari akar repositori:

```bash
# Mac / Linux
FRIGATE_URL=http://localhost:8971 backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8000
```

```bash
# Windows (WSL)
FRIGATE_URL=http://localhost:5000 \
MQTT_HOST=localhost \
MQTT_PORT=1883 \
backend/.venv/bin/uvicorn backend.app.main:app --port 8000
```

Lalu buka **http://localhost:8000/dashboard/** (alamat `http://localhost:8000/` otomatis diarahkan ke
sana). `FRIGATE_URL` diisi alamat Frigate yang dipakai: `http://localhost:5000` bila Frigate dijalankan
dengan `frigate/docker-compose.yml`. Cara memasang `backend/.venv` ada di
[`backend/README.md`](../backend/README.md).

Keadaan truk (dimuat, dumping, idle) baru bisa dinilai bila Frigate dan backend tersambung ke broker
MQTT; cara menyalakannya juga ada di `backend/README.md`.

Bila halaman dibuka dari tempat lain, misalnya berkasnya dibuka langsung, alamat backend ditentukan
lewat parameter `api`:

```
index.html?api=http://localhost:8000
```

Setelah berkas di folder ini diubah, muat ulang halaman dengan Cmd + Shift + R (Mac) atau Ctrl + F5
(Windows), karena browser kadang masih memakai versi lama.

## Isi halaman

| Bagian | Isi |
|---|---|
| Status | Backend, Frigate, kecepatan detektor, pemakaian CPU dan RAM, serta sambungan MQTT |
| Filter | Rentang waktu, kamera, label, pilihan kotak di gambar kamera, dan tombol jeda |
| Ringkasan | Total deteksi, jumlah truk, excavator, dan objek yang masih terlihat |
| Kamera | Gambar terbaru tiap kamera (tiap 3 detik) dengan kotak di atas tiap objek; klik untuk memperbesar |
| Deteksi terbaru | Foto, waktu, kamera, label, skor, dan durasi; klik baris untuk detailnya |
| Aktivitas truk | Jumlah truk per keadaan, bagian waktu tiap keadaan per kamera, truk yang sedang terlihat, dan aktivitas terakhir |
| Grafik | Jumlah deteksi per label dan per kamera |

### Kotak di gambar kamera

| Kotak | Artinya |
|---|---|
| Tebal biru | Truk bergerak |
| Tebal kuning | Truk dimuat: berhenti di dekat excavator |
| Tebal ungu | Truk dumping: berhenti dengan bak terangkat |
| Tebal merah | Truk idle: berhenti tanpa dilayani |
| Putus-putus hijau | Excavator |
| Putus-putus oranye | Bak terangkat |
| Putus-putus abu-abu | Muatan (bermuatan atau kosong) |

Perlu dibedakan saat membacanya: kotak tebal adalah **kesimpulan backend** dari gerak truk dan objek di
sekitarnya, sedangkan kotak putus-putus adalah **hasil deteksi model** secara langsung. Angka di belakang
keadaan, misalnya "Dimuat 24 dtk", adalah lama truk berada di keadaan itu.

Pilihan **Kotak di kamera → Deteksi Frigate** mengganti semuanya dengan kotak asli dari Frigate — berguna
untuk memeriksa hasil model apa adanya. Arti warnanya ada di [README proyek](../README.md).

### Bila kotak keadaan tidak bisa digambar

Kotak keadaan butuh posisi objek terkini dari backend, dan posisi itu hanya datang lewat MQTT. Bila
posisinya tidak tersedia, kamera otomatis memakai kotak asli Frigate dan catatan penyebabnya muncul di
bagian Kamera, supaya gambar tidak pernah tampil polos tanpa penjelasan. Begitu datanya masuk, kotak
keadaan kembali sendiri tanpa perlu memuat ulang halaman.

| Status di pojok kanan atas | Sebabnya | Yang perlu diperiksa |
|---|---|---|
| Aktivitas: menunggu data MQTT | Broker tersambung, tetapi backend belum menerima satu kabar pun padahal Frigate sedang melacak objek | `mqtt.host` di konfigurasi Frigate: di dalam Docker harus nama layanan broker (`mosquitto`), bukan `localhost` |
| Aktivitas: MQTT tanpa data | Sama, dan sudah berlangsung lebih dari 3 menit | Sama; juga `mqtt.enabled` dan `topic_prefix` |
| Aktivitas: tanpa MQTT | Backend tidak tersambung ke broker | Broker menyala dan port 1883 terbuka; `MQTT_HOST` pada backend |

Angka "objek terpantau" di bagian Aktivitas truk membantu memastikannya: bila tetap 0 sementara kamera
jelas menampilkan truk, kabar dari Frigate memang tidak sampai.

## Catatan

- **Dimuat, dumping, dan idle tidak terlihat di Frigate.** Keadaan ini disimpulkan backend dari posisi
  truk tiap detik (lihat `backend/README.md`), jadi hanya tampil di sini.
- **Lama aktivitas menumpuk pada video uji yang diputar berulang.** Truk yang diam di tempat yang sama
  dianggap Frigate sebagai truk yang sama, sehingga lama idle atau dimuat bisa melebihi panjang videonya.
  Di kamera sungguhan hal ini tidak terjadi.
- **Grafik waktu per keadaan dibatasi 1 jam terakhir dan diperbarui tiap menit.** Perhitungannya berat
  bagi backend — di lokasi ramai sekitar 0,75 detik untuk 1 jam dan 4 detik untuk 6 jam, dan selama itu
  backend tidak melayani permintaan lain — jadi tidak ikut diperbarui tiap 10 detik seperti data lainnya.
- **CPU dan RAM adalah beban mesin tempat Frigate berjalan**, kuning mulai 70% dan merah mulai 90%. Bila
  Frigate berjalan di Docker Desktop atau OrbStack, yang terukur adalah mesin virtualnya, bukan seluruh
  komputer. CPU per kamera dihitung dari satu inti prosesor, sama seperti halaman System di Frigate, jadi
  jumlahnya bisa lebih besar dari angka CPU mesin.
- **Beban CPU bergantung pada detektornya.** Dengan detektor `onnx` di CPU (susunan Windows), 6 kamera
  bisa memakai hampir seluruh inti dan sebagian frame terlewat; lewat Neural Engine di Mac bebannya
  sekitar 11%. Angka "terlewat" di kartu tiap kamera menunjukkan frame yang tidak sempat diproses.
- **Angka pada grafik adalah jumlah event Frigate**, bukan jumlah kendaraan unik. Truk yang diam lama
  bisa tercatat lebih dari satu event.
- **Foto pada tabel deteksi** memerlukan `snapshots.enabled: true` di konfigurasi Frigate. Tanpa itu
  tabelnya tetap terisi, hanya tanpa foto.
- Filter label hanya berlaku untuk tabel deteksi; filter kamera dan rentang waktu berlaku untuk semuanya.
- Tombol jeda menghentikan semua pembaruan. Pembaruan juga berhenti sendiri saat tab browser tidak
  terlihat, supaya tidak membebani Frigate.
- Bila Frigate atau backend mati, muncul pesan merah di atas dan dashboard pulih sendiri setelah
  layanannya menyala lagi.
- Dashboard tetap berjalan dengan backend versi lama. Bagian yang datanya belum tersedia menyesuaikan
  sendiri: tanpa `/cameras/{camera}/objects` kamera memakai kotak Frigate, dan tanpa data beban di
  `/stats` status CPU dan RAM disembunyikan.
