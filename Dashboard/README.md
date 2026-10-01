# Dashboard Deteksi Truk Tambang

Halaman web untuk memantau hasil deteksi dan aktivitas truk secara visual. Datanya diambil dari backend
FastAPI (`backend/`), bukan langsung dari Frigate.

```
Frigate  ──►  Backend FastAPI  ──►  Dashboard (halaman ini)
```

Tidak perlu install apa pun: cukup HTML, CSS, dan JavaScript biasa, tanpa library dari internet.

| File | Isi |
|---|---|
| `index.html` | Kerangka halaman |
| `style.css` | Tampilan (tema terang dan gelap mengikuti setelan perangkat) |
| `app.js` | Pengambilan data dari backend dan pembaruan tampilan |

## Isi halaman

Urutannya dari atas ke bawah:

- **Status** (pojok kanan atas): backend, Frigate, kecepatan detektor, pemakaian **CPU** dan **RAM**, serta
  sambungan MQTT untuk aktivitas.
- **Filter**: rentang waktu, kamera, label, pilihan **Kotak di kamera**, dan tombol **Jeda**.
- **Ringkasan**: total deteksi, jumlah truk, excavator, dan objek yang masih terlihat.
- **Kamera**: gambar terbaru tiap kamera, diperbarui tiap 3 detik, dengan kotak di atas tiap objek.
  - Truk diberi **kotak tebal** berwarna sesuai keadaannya beserta lamanya, misalnya "Dimuat 24 dtk".
  - Excavator, bak terangkat, dan muatan diberi **kotak putus-putus**.
  - Klik gambar untuk memperbesar. Tampilan besar terus diperbarui dan menampilkan keadaan tiap truk.
  - Kartu tiap kamera menampilkan kecepatan proses serta CPU dan RAM yang dipakai kamera itu.
  - Arti warnanya ada di **Keterangan warna kotak** di bawah daftar kamera.
- **Aktivitas truk**: jumlah truk yang sedang dimuat, dumping, idle, dan bergerak; sumber data, jumlah objek
  terpantau, dan aktivitas tersimpan; bagian waktu tiap keadaan per kamera; tabel truk yang sedang terlihat;
  dan daftar aktivitas terakhir.
- **Grafik**: jumlah deteksi per label dan per kamera.
- **Deteksi terbaru**: foto, waktu, kamera, label, skor, dan durasi. Klik baris untuk melihat detailnya.

### Warna kotak di gambar kamera

| Kotak | Artinya |
|---|---|
| Tebal biru | Truk bergerak |
| Tebal kuning | Truk dimuat: berhenti di dekat excavator |
| Tebal ungu | Truk dumping: berhenti dengan bak terangkat |
| Tebal merah | Truk idle: berhenti tanpa dilayani |
| Putus-putus hijau | Excavator |
| Putus-putus oranye | Bak terangkat |
| Putus-putus abu-abu | Muatan (bermuatan atau kosong) |

Kotak tebal adalah **kesimpulan backend** dari gerak truk dan objek di sekitarnya. Kotak putus-putus adalah
**hasil deteksi model** secara langsung. Pilihan **Kotak di kamera → Deteksi Frigate** mengganti semuanya
dengan kotak asli dari Frigate; arti warnanya ada di README proyek.

## Menjalankan

Frigate harus sudah jalan. Dari root repo:

```bash
FRIGATE_URL=http://localhost:8971 backend/.venv/bin/uvicorn backend.app.main:app --port 8000
```

Lalu buka **http://localhost:8000/dashboard/**.

Backend otomatis menyajikan folder ini di `/dashboard/` bila foldernya ada. Kalau folder `Dashboard/`
tidak ada, backend tetap jalan normal tanpa dashboard.

Supaya keadaan truk (idle, dimuat, dumping) akurat, Frigate dan backend harus tersambung ke broker MQTT.
Cara menyalakannya ada di `backend/README.md`.

Kalau halaman dibuka dari tempat lain (misalnya file dibuka langsung), tentukan alamat backend lewat
parameter `api`:

```
index.html?api=http://localhost:8000
```

Setelah file di folder ini diubah, muat ulang halaman dengan **Cmd + Shift + R** (Mac) atau **Ctrl + F5**
(Windows), karena browser kadang masih memakai versi lama.

## Catatan

**Aktivitas truk**

- **Idle, dimuat, dan dumping tidak terlihat di Frigate.** Keadaan ini disimpulkan backend dari posisi
  truk tiap detik (lihat `backend/README.md`). Bila backend tidak tersambung ke MQTT, Dashboard menampilkan
  peringatan kuning di bagian Aktivitas truk dan di bagian Kamera, karena letak kotak dan keadaannya bisa
  tidak sesuai.
- Bila broker MQTT tersambung tetapi Frigate tidak mengirim data (misalnya `mqtt.enabled` lupa
  dinyalakan), status berubah menjadi "MQTT tanpa data" beserta peringatannya.
- Grafik **waktu per keadaan** paling jauh mencakup 1 jam terakhir dan diperbarui tiap menit. Perhitungannya
  berat bagi backend (di lokasi ramai sekitar 0,75 detik untuk 1 jam dan 4 detik untuk 6 jam, dan selama
  itu backend tidak melayani permintaan lain), jadi tidak ikut diperbarui tiap 10 detik.
- Pada video uji yang diputar berulang, lama idle atau dimuat bisa terus bertambah melebihi panjang videonya.
  Itu wajar: truk yang diam di tempat yang sama dianggap Frigate sebagai truk yang sama.

**CPU dan RAM**

- Pil **CPU** dan **RAM** di atas adalah beban seluruh mesin tempat Frigate berjalan. Warnanya kuning mulai
  70% dan merah mulai 90%. Bila Frigate berjalan di dalam Docker Desktop atau OrbStack, yang terukur adalah
  mesin virtualnya, bukan seluruh komputer.
- CPU per kamera dihitung dari **satu inti prosesor**, sama seperti halaman System di Frigate, jadi jumlah
  semua kamera bisa lebih besar dari angka CPU mesin.

**Lain-lain**

- Angka pada grafik adalah **jumlah event Frigate** (objek yang dilacak), bukan jumlah kendaraan unik.
  Truk yang diam lama bisa tercatat lebih dari satu event.
- Filter **Label** hanya berlaku untuk tabel. Filter **Kamera** dan **Rentang waktu** berlaku untuk
  semuanya.
- Tombol **Jeda** menghentikan semua pembaruan. Pembaruan juga berhenti otomatis saat tab browser tidak
  terlihat, supaya tidak membebani Frigate.
- Bila Frigate atau backend mati, muncul pesan merah di atas dan dashboard pulih sendiri setelah
  layanannya menyala lagi.
- Dashboard tetap berjalan dengan backend versi lama. Bagian yang datanya belum tersedia disesuaikan
  sendiri: tanpa `/cameras/{kamera}/objects` kamera menampilkan kotak Frigate, dan tanpa data beban di
  `/stats` pil CPU dan RAM disembunyikan.
- Backend juga punya halaman pemantau lain di `/monitor/` (`backend/dashboard/`). Halaman itu berfokus pada
  keadaan truk saat ini; Dashboard ini menambahkan ringkasan, grafik, riwayat deteksi, filter, dan beban mesin.
