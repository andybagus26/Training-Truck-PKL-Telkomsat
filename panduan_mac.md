# Panduan Mac: dari clone sampai Dashboard jalan

Panduan ini untuk Mac dengan chip Apple (M1 ke atas). Ikuti dari atas ke bawah. Tiap langkah punya dua
bagian: **hasil yang benar**, supaya ketahuan kalau ada yang meleset, dan **kalau gagal**, berisi pesan
error yang mungkin muncul, sebabnya, dan cara membereskannya. Pemasangan pertama butuh sekitar 20 menit,
sebagian besar untuk menunggu unduhan.

Yang akan berjalan di akhir:

```
Video uji  ──►  Frigate + model v6  ──►  Broker MQTT  ──►  Backend  ──►  Dashboard
               (di dalam Docker)        (di dalam Docker)  (Python)     (browser)
```

Semua perintah diketik di aplikasi **Terminal**. Bila memakai VS Code, Terminal di dalamnya juga bisa
(menu Terminal → New Terminal). Untuk pengguna Windows, pakai [`panduan_wd.md`](panduan_wd.md).

Aturan yang paling sering menyelamatkan: **perhatikan sedang berada di folder mana.** Sebagian besar error
di panduan ini muncul karena perintah dijalankan dari folder yang salah. Ketik `pwd` untuk melihatnya.

## 1. Yang harus terpasang

| Yang diperiksa | Perintah | Hasil yang benar |
|---|---|---|
| Git | `git --version` | Muncul nomor versi |
| Docker | `docker --version` | Muncul nomor versi |
| Python | `python3 --version` | **3.10 atau lebih baru** |

Sediakan juga ruang kosong sekitar 8 GB (image Frigate sekitar 6 GB setelah terpasang).

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `No developer tools were found`, atau muncul jendela yang menawarkan pemasangan | Git belum terpasang | Klik **Install** di jendela itu (atau jalankan `xcode-select --install`), tunggu selesai |
| `command not found: docker` | Docker belum terpasang, atau belum pernah dibuka | Pasang [OrbStack](https://orbstack.dev) (lebih ringan) atau [Docker Desktop](https://www.docker.com/products/docker-desktop/), lalu buka aplikasinya sekali |
| `Python 3.9.x` | Itu Python bawaan macOS, terlalu lama untuk backend | Pasang yang baru dari [python.org](https://www.python.org/downloads/macos/) atau `brew install python@3.12`. Bila `python3 --version` masih 3.9, ganti setiap `python3` di panduan ini dengan `python3.12` |

## 2. Clone repo

```bash
git clone https://github.com/andybagus26/Training-Truck-PKL-Telkomsat.git
cd Training-Truck-PKL-Telkomsat
```

Folder `Training-Truck-PKL-Telkomsat` ini selanjutnya disebut **folder utama**.

Hasil yang benar: `ls` menampilkan antara lain `Dashboard`, `backend`, `frigate`, dan `models`.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `fatal: destination path 'Training-Truck-PKL-Telkomsat' already exists and is not an empty directory.` | Di tempat itu sudah ada folder bernama sama | Pakai folder yang sudah ada (`cd Training-Truck-PKL-Telkomsat`, lalu `git pull`), atau pindah dulu ke tempat lain dengan `cd` sebelum clone |
| `Could not resolve host: github.com` | Tidak ada sambungan internet | Periksa internet, lalu ulangi |

## 3. Siapkan video uji

Video tidak ikut di GitHub. Unduh dari folder Google Drive berikut:

https://drive.google.com/drive/folders/1Mmq6ZctimH3E_j7f7894gHnq74gcZ2HB

Pilih tiga video dari sana (atau pakai video tambang sendiri berformat `.mp4`), lalu taruh di folder
`frigate/` dan **ganti namanya** sesuai tabel ini:

| Nama file yang harus ada | Tampil di Dashboard sebagai |
|---|---|
| `frigate/cctv_short.mp4` | `truck_cam` |
| `frigate/truck_cam_3.mp4` | `truck_cam_3` |
| `frigate/truck_excavator_night.mp4` | `truck_excavator_night` |

Namanya harus diganti karena ketiga nama itu sudah tertulis di pengaturan Frigate; video bernama lain
tidak akan dibaca. Isi videonya bebas, dan bila hanya punya satu video, salin video yang sama tiga kali.

Contoh, bila hasil unduhan ada di folder Downloads (ganti `video1.mp4` dengan nama file sebenarnya):

```bash
cp ~/Downloads/video1.mp4 frigate/cctv_short.mp4
cp ~/Downloads/video2.mp4 frigate/truck_cam_3.mp4
cp ~/Downloads/video3.mp4 frigate/truck_excavator_night.mp4
```

Lewat Finder juga boleh: seret file ke folder `frigate`, lalu klik kanan → Rename.

Hasil yang benar: `ls frigate/*.mp4` menampilkan ketiga nama di tabel, persis sampai garis bawahnya.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `cp: … No such file or directory` | Nama atau letak file sumbernya salah | Lihat nama sebenarnya dengan `ls ~/Downloads/*.mp4`, lalu ulangi dengan nama itu |
| `cp: frigate/…: No such file or directory` | Sedang tidak berada di folder utama | `cd` ke folder utama dulu |
| Tidak ada error, tetapi nanti kamera tidak bergambar | Nama file meleset (misalnya `cctv-short.mp4`) | Samakan dengan tabel di atas |

## 4. Nyalakan Frigate dan broker MQTT

Buka aplikasi Docker (OrbStack atau Docker Desktop) dan tunggu sampai siap, lalu:

```bash
cd frigate
docker compose up -d
cd ..
```

Saat pertama kali, Docker mengunduh Frigate (sekitar 1,4 GB) dan broker MQTT. Ini langkah paling lama.
Tunggu sampai Terminal bisa diketik lagi.

Hasil yang benar:

- Di akhir muncul `Container frigate-truk Started` dan `Container frigate-mqtt Started`.
- `docker ps` menampilkan dua baris: `frigate-truk` dan `frigate-mqtt`.
- **http://localhost:5000** menampilkan halaman Frigate dengan tiga kamera yang bergambar.

Di folder `frigate/` akan muncul tiga folder kosong bernama `cctv5.mp4`, `cctv_truck2.mp4`, dan
`cctv_truck4.mp4`. Itu sisa pengaturan kamera lama; biarkan saja.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `failed to connect to the docker API …` atau `Cannot connect to the Docker daemon` | Aplikasi Docker belum dibuka atau belum siap | Buka OrbStack atau Docker Desktop, tunggu ikonnya muncul di bar atas, lalu ulangi |
| `no configuration file provided: not found` | Perintah dijalankan di luar folder `frigate` | `cd frigate`, lalu ulangi |
| `port is already allocated` atau `address already in use`, menyebut 5000 | Port 5000 dipakai AirPlay Receiver | System Settings → General → AirDrop & Handoff → matikan **AirPlay Receiver**, lalu ulangi |
| Sama, menyebut 1883 | Ada broker MQTT lain yang berjalan di Mac | Matikan broker itu, lalu ulangi |
| Unduhan berhenti di tengah atau `timeout` | Internet putus | Jalankan lagi `docker compose up -d`; unduhan dilanjutkan, tidak dari awal |
| Kamera di http://localhost:5000 tidak bergambar | Video belum ada atau namanya salah, sehingga Docker membuat **folder** kosong bernama sama | `docker compose down`, hapus folder kosong itu, taruh videonya (bagian 3), lalu `docker compose up -d` |

## 5. Pasang backend (cukup sekali)

Dari folder utama:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
```

Perintah pertama membuat ruang Python tersendiri untuk backend; perintah kedua memasang pustakanya.

Hasil yang benar: perintah kedua berakhir tanpa tulisan `ERROR`. Tulisan `[notice] A new release of pip`
boleh diabaikan.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `ERROR: Could not open requirements file: … 'backend/requirements.txt'` | Sedang tidak berada di folder utama (misalnya masih di `frigate`) | `cd` ke folder utama, lalu ulangi |
| `No matching distribution found for fastapi==0.141.1` | Python di bawah 3.10 | Pasang Python baru (bagian 1), hapus folder `backend/.venv`, lalu ulangi dengan `python3.12` |
| `no such file or directory: backend/.venv/bin/python` | Perintah pertama belum berhasil, atau salah folder | Jalankan perintah pertama dari folder utama |

## 6. Jalankan backend

Dari folder utama, dalam **satu baris**:

```bash
FRIGATE_URL=http://localhost:5000 backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8000
```

Bagian `FRIGATE_URL=…` memberi tahu backend alamat Frigate.

Hasil yang benar: muncul `Uvicorn running on http://127.0.0.1:8000`. Terminal ini tidak kembali ke tanda
`$` karena backend sedang berjalan di dalamnya. **Biarkan jendela ini terbuka**; untuk perintah lain, buka
jendela Terminal baru.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `ModuleNotFoundError: No module named 'backend'` | Dijalankan di luar folder utama | `cd` ke folder utama, lalu ulangi |
| `no such file or directory: backend/.venv/bin/python` | Backend belum dipasang | Kerjakan bagian 5 |
| `address already in use` | Backend lain masih berjalan di jendela Terminal lain | Tekan Ctrl + C di jendela itu, lalu ulangi |
| Berulang-ulang `gagal mengambil sampel: … Frigate tidak bisa dihubungi di http://localhost:8971` | `FRIGATE_URL=…` tidak ikut ditulis, jadi backend mencari di alamat bawaan | Ctrl + C, lalu jalankan lagi persis seperti di atas |
| Sama, tetapi alamatnya `http://localhost:5000` | Frigate belum menyala | Kerjakan bagian 4; backend akan tersambung sendiri |

## 7. Buka Dashboard

Buka **http://localhost:8000** di browser. Alamat itu otomatis diarahkan ke Dashboard.

Hasil yang benar, setelah menunggu sekitar satu menit:

- Di pojok kanan atas: `Backend aktif`, `Frigate 0.17.1`, `Detektor onnx_cpu: … ms`, dan
  `Aktivitas: MQTT tersambung`.
- Tiga kamera tampil, dan di atas truk muncul kotak berwarna dengan tulisan seperti `Bergerak`, `Idle`,
  atau `Dimuat 24 dtk`.
- Tabel **Deteksi terbaru** terisi beserta fotonya.

Sampai di sini Dashboard sudah jalan. Deteksinya dikerjakan CPU, jadi pemakaian CPU cukup tinggi (sekitar
40–55% untuk tiga kamera pada Mac 10 inti). Supaya ringan, lanjutkan ke bagian 10.

**Kalau gagal**

| Yang terlihat | Sebabnya | Caranya |
|---|---|---|
| Browser: halaman tidak bisa dibuka | Backend tidak berjalan | Lihat jendela Terminal backend; kerjakan bagian 6 |
| `Backend tidak terjangkau` atau pesan merah di atas | Backend berhenti setelah halaman terbuka | Jalankan lagi bagian 6; Dashboard pulih sendiri |
| `Frigate tidak terjangkau` | `FRIGATE_URL` tidak ditulis, atau Frigate mati | Lihat tabel bagian 6; cek http://localhost:5000 |
| Kamera tampil, kotak belum ada | Baru dinyalakan, atau videonya sedang tidak memuat truk | Tunggu satu sampai dua menit |
| `Aktivitas: menunggu data MQTT` atau `MQTT tanpa data`, kotak yang tampil kotak asli Frigate | Frigate tidak tersambung ke broker | Jalankan `docker logs frigate-mqtt`; harus ada `truck-backend` **dan** `frigate`. Bila `frigate` tidak ada: `git pull`, lalu di folder `frigate` jalankan `docker compose down` dan `docker compose up -d` |
| `Aktivitas: tanpa MQTT` | Broker mati | `docker ps` harus menampilkan `frigate-mqtt`; bila tidak, kerjakan bagian 4 |
| Kotak tampil dobel sesaat setelah Frigate dinyalakan ulang | Backend masih mengingat objek dari Frigate sebelumnya | Tunggu paling lama 2 menit; hilang sendiri |
| Tabel deteksi terisi tetapi tanpa foto | Pengaturan Frigate versi lama | `git pull`, lalu nyalakan ulang Frigate |
| Tampilan masih versi lama setelah `git pull` | Browser memakai salinan lama | Tekan **Cmd + Shift + R** |

## 8. Mematikan

1. Di jendela Terminal backend, tekan **Ctrl + C**.
2. Matikan Frigate dan broker:

```bash
cd frigate
docker compose down
cd ..
```

Rekaman Frigate tetap tersimpan dan terus bertambah (sekitar 160 MB dalam 15 menit untuk tiga kamera).
Untuk mematikan sekaligus menghapus rekamannya, pakai `docker compose down -v`.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `no configuration file provided: not found` | Bukan di folder `frigate` | `cd frigate`, lalu ulangi |

## 9. Menjalankan lagi lain waktu

Tidak perlu memasang ulang dan tidak ada unduhan lagi. Buka aplikasi Docker, lalu dari folder utama:

```bash
cd frigate && docker compose up -d && cd ..
FRIGATE_URL=http://localhost:5000 backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8000
```

Lalu buka http://localhost:8000.

Bila repo diperbarui teman (`git pull`), nyalakan ulang Frigate dengan `docker compose down` lalu
`docker compose up -d`, dan muat ulang Dashboard dengan **Cmd + Shift + R**.

## 10. Tambahan: supaya ringan, pakai Neural Engine

Mac punya chip khusus AI (Neural Engine) yang jauh lebih hemat untuk deteksi, tetapi program di dalam
Docker tidak bisa memakainya. Jadi detektornya dijalankan langsung di Mac, di luar Docker. Hasil ukur
dengan tiga kamera: pemakaian CPU turun dari sekitar 55% menjadi sekitar 10%.

Bagian ini opsional. Kerjakan setelah bagian 1 sampai 7 berhasil.

**a. Pasang detektornya (cukup sekali).** Dari folder utama:

```bash
git clone https://github.com/frigate-nvr/apple-silicon-detector.git
cd apple-silicon-detector
git apply ../frigate/apple-silicon-detector-nms-fix.patch
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd ..
```

Perintah `git apply` wajib dijalankan. Tanpa itu, kotak muatan yang berada di dalam kotak truk ikut
terhapus.

**b. Jalankan detektornya** di jendela Terminal baru, dari folder utama:

```bash
cd apple-silicon-detector
.venv/bin/python detector/zmq_onnx_client.py --endpoint "tcp://127.0.0.1:5555" --model AUTO --providers CoreMLExecutionProvider CPUExecutionProvider
```

Biarkan jendela ini terbuka juga.

**c. Buat pengaturan Frigate untuk Mac (cukup sekali).** Di jendela Terminal lain, dari folder utama,
salin seluruh blok ini sekaligus:

```bash
cd frigate
python3 - <<'EOF'
s = open("config.windows.yml").read()
lama = "  onnx_cpu:\n    type: onnx\n"
baru = "  apple-silicon:\n    type: zmq\n    endpoint: tcp://host.docker.internal:5555\n"
assert lama in s, "Bagian detektor di config.windows.yml berubah; panduan ini perlu disesuaikan."
open("config.mac.yml", "w").write(s.replace(lama, baru))
print("config.mac.yml dibuat")
EOF
cat > docker-compose.override.yml <<'EOF'
# Khusus Mac: Frigate memakai config.mac.yml (detektor Neural Engine).
# Hapus file ini untuk kembali ke detektor CPU.
services:
  frigate:
    volumes:
      - ./config.mac.yml:/config/config.yml:ro
EOF
cd ..
```

Blok ini membuat dua file di folder `frigate/`: `config.mac.yml` (salinan pengaturan yang ada, hanya
bagian detektornya diganti) dan `docker-compose.override.yml` (membuat Frigate memakai salinan itu).
Keduanya hanya ada di komputermu dan tidak ikut ke GitHub.

**d. Nyalakan ulang Frigate:**

```bash
cd frigate
docker compose up -d
cd ..
```

Hasil yang benar: di Dashboard, tulisan detektor berubah menjadi `Detektor apple-silicon: … ms` dan angka
CPU turun. Di jendela detektor muncul `Model ready for inference`.

Selama memakai cara ini, urutan menyalakannya: detektor (langkah b), lalu Frigate, lalu backend.

**Kembali ke detektor CPU:** hapus `frigate/docker-compose.override.yml`, lalu jalankan lagi
`docker compose up -d` di folder `frigate/`.

**Bila pengaturan kamera di repo berubah** (setelah `git pull`), ulangi langkah c supaya `config.mac.yml`
ikut diperbarui.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `error: patch failed` atau `patch does not apply` saat `git apply` | Patch sudah pernah diterapkan | Lanjut saja ke perintah berikutnya |
| `AssertionError: Bagian detektor di config.windows.yml berubah` | Pengaturan di repo sudah tidak sama dengan saat panduan ditulis | Kabari Zacky; sementara itu pakai detektor CPU |
| Detektor masih `onnx_cpu` setelah langkah d | File `docker-compose.override.yml` tidak terbuat, atau langkah d dijalankan di luar folder `frigate` | Periksa `ls frigate/`, ulangi langkah c dan d |
| Kamera tampil tetapi tidak ada deteksi baru | Jendela detektor tertutup | Jalankan lagi langkah b |
| `Address already in use` di jendela detektor | Detektor lain masih berjalan | Tutup jendela detektor yang lama |

## 11. Hal lain yang perlu diketahui

- Dua pesan di `docker logs frigate-truk` ini wajar dan boleh diabaikan: `Config file is read-only, unable
  to migrate config file` dan `Did not detect hwaccel`.
- Bila CPU tinggi dan tulisan `terlewat … fps` muncul di kartu kamera, deteksinya tidak terkejar. Pakai
  bagian 10.
- Bila masih buntu, kirim tiga hal ini ke Zacky: tangkapan layar Dashboard, isi
  http://localhost:8000/poller, dan hasil `docker logs frigate-mqtt`.

---

Langkah 1 sampai 10 dicoba dari hasil clone baru pada 5 Oktober 2026, di Mac Apple M5 dengan OrbStack dan
Python 3.11, memakai Frigate 0.17.1. Pesan error di tabel "kalau gagal" sebagian besar dipicu langsung di
Mac itu; pesan soal port 5000, port 1883, dan `git apply` ditulis dari perilaku umum programnya, jadi
bunyinya bisa sedikit berbeda. Dengan Docker Desktop langkahnya sama, tetapi belum dicoba.
