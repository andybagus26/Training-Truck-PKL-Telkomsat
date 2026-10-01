# Dashboard Deteksi Truk Tambang

Halaman web untuk memantau hasil deteksi secara visual. Datanya diambil dari backend FastAPI
(`backend/`), bukan langsung dari Frigate.

```
Frigate  ──►  Backend FastAPI  ──►  Dashboard (halaman ini)
```

Isinya:

- **Status**: backend, Frigate, kecepatan detektor, sambungan MQTT untuk aktivitas, serta pemakaian **CPU** dan
  **RAM** mesin tempat Frigate berjalan (kuning mulai 70%, merah mulai 90%). Kartu tiap kamera juga menampilkan CPU
  dan RAM yang dipakai kamera itu. CPU per kamera dihitung dari satu inti prosesor, sama seperti halaman System di
  Frigate, jadi jumlahnya bisa lebih besar dari angka CPU mesin.
- **Ringkasan**: total deteksi, jumlah truk, excavator, dan objek yang masih terlihat.
- **Kamera**: gambar terbaru tiap kamera, diperbarui tiap 3 detik. Truk diberi kotak tebal berwarna sesuai
  keadaannya (biru bergerak, kuning dimuat, ungu dumping, merah idle) beserta lamanya, misalnya "Dimuat 24 dtk";
  excavator, bak terangkat, dan muatan diberi kotak putus-putus. Pilihan **Kotak di kamera** bisa diganti ke
  "Deteksi Frigate" untuk melihat kotak asli dari Frigate. Klik gambar untuk memperbesar: tampilan besar terus
  diperbarui dan menampilkan keadaan tiap truk. Arti warnanya ada di **Keterangan warna kotak** di bawah kamera.
- **Aktivitas truk**: berapa truk yang sedang dimuat, dumping, idle, dan bergerak; sumber data, jumlah objek
  terpantau, dan aktivitas tersimpan; bagian waktu tiap keadaan per kamera; tabel truk yang sedang terlihat; dan
  daftar aktivitas terakhir.
- **Grafik**: jumlah deteksi per label dan per kamera.
- **Tabel deteksi terbaru**: foto, waktu, kamera, label, skor, durasi. Klik baris untuk detail.

Tidak perlu install apa pun: cukup HTML, CSS, dan JavaScript biasa, tanpa library dari internet.

## Menjalankan

Frigate harus sudah jalan. Dari root repo:

```bash
FRIGATE_URL=http://localhost:8971 backend/.venv/bin/uvicorn backend.app.main:app --port 8000
```

Lalu buka **http://localhost:8000/dashboard/**.

Backend otomatis menyajikan folder ini di `/dashboard/` bila foldernya ada. Kalau folder `Dashboard/`
tidak ada, backend tetap jalan normal tanpa dashboard.

Kalau halaman dibuka dari tempat lain (misalnya file dibuka langsung), tentukan alamat backend lewat
parameter `api`:

```
index.html?api=http://localhost:8000
```

## Catatan

- **Idle, dimuat, dan dumping tidak terlihat di Frigate.** Keadaan ini disimpulkan backend dari posisi
  truk tiap detik (lihat `backend/README.md`), dan hanya tampil di Dashboard. Supaya akurat, backend
  harus tersambung ke MQTT; bila tidak, Dashboard menampilkan peringatan kuning di bagian Aktivitas truk.
- Grafik **waktu per keadaan** paling jauh mencakup 1 jam terakhir dan diperbarui tiap menit. Perhitungannya
  berat bagi backend (di lokasi ramai sekitar 0,75 detik untuk 1 jam dan 4 detik untuk 6 jam, dan selama
  itu backend tidak melayani permintaan lain), jadi tidak ikut diperbarui tiap 10 detik.
- Kotak keadaan di gambar kamera memakai endpoint `/cameras/{kamera}/objects` (sama dengan halaman `/monitor/`).
  Pada backend lama yang belum punya endpoint itu, kamera otomatis menampilkan kotak Frigate beserta penjelasannya.
- Bila broker MQTT tersambung tetapi Frigate tidak mengirim data (misalnya `mqtt.enabled` lupa
  dinyalakan), status berubah menjadi "MQTT tanpa data" beserta peringatannya.
- Angka pada grafik adalah **jumlah event Frigate** (objek yang dilacak), bukan jumlah kendaraan unik.
  Truk yang diam lama bisa tercatat lebih dari satu event.
- Filter **Label** hanya berlaku untuk tabel. Filter **Kamera** dan **Rentang waktu** berlaku untuk
  semuanya.
- Tombol **Jeda** menghentikan semua pembaruan. Pembaruan juga berhenti otomatis saat tab browser tidak
  terlihat, supaya tidak membebani Frigate.
- Bila Frigate atau backend mati, muncul pesan merah di atas dan dashboard pulih sendiri setelah
  layanannya menyala lagi.
- Folder ini masuk `.gitignore`, jadi tidak ikut ter-commit.
