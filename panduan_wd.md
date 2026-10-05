# Panduan Windows: dari clone sampai Dashboard jalan

Panduan ini untuk Windows 10 atau 11. Ikuti dari atas ke bawah. Tiap langkah punya dua bagian: **hasil
yang benar**, supaya ketahuan kalau ada yang meleset, dan **kalau gagal**, berisi pesan error yang mungkin
muncul, sebabnya, dan cara membereskannya. Pemasangan pertama butuh sekitar 20 menit, sebagian besar untuk
menunggu unduhan.

Yang akan berjalan di akhir:

```
Video uji  ──►  Frigate + model v6  ──►  Broker MQTT  ──►  Backend  ──►  Dashboard
               (di dalam Docker)        (di dalam Docker)  (Python)     (browser)
```

Semua perintah diketik di **PowerShell** (cari "PowerShell" di menu Start). Bila memakai VS Code, Terminal
di dalamnya juga bisa (menu Terminal → New Terminal). Untuk pengguna Mac, pakai
[`panduan_mac.md`](panduan_mac.md).

Aturan yang paling sering menyelamatkan: **perhatikan sedang berada di folder mana.** Sebagian besar error
di panduan ini muncul karena perintah dijalankan dari folder yang salah. Folder saat ini tertulis di depan
tanda `>` pada PowerShell.

## 1. Yang harus terpasang

| Yang diperiksa | Perintah | Hasil yang benar |
|---|---|---|
| Git | `git --version` | Muncul nomor versi |
| Docker | `docker --version` | Muncul nomor versi |
| Python | `python --version` | **3.10 atau lebih baru** |

Sediakan juga ruang kosong sekitar 8 GB (image Frigate sekitar 6 GB setelah terpasang).

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `The term 'git' is not recognized …` | Git belum terpasang | Pasang [Git for Windows](https://git-scm.com/download/win) dengan pilihan bawaan, lalu tutup dan buka lagi PowerShell |
| `The term 'docker' is not recognized …` | Docker belum terpasang | Pasang [Docker Desktop](https://www.docker.com/products/docker-desktop/) (pilih WSL 2 saat ditanya), lalu buka aplikasinya |
| `python` membuka Microsoft Store, atau `… is not recognized …` | Python belum terpasang atau belum masuk PATH | Pasang dari [python.org](https://www.python.org/downloads/windows/) dan **centang "Add python.exe to PATH"** di jendela pertama pemasangnya. Tutup dan buka lagi PowerShell |
| `python` tetap tidak dikenali, tetapi `py --version` berhasil | Python terpasang tanpa PATH | Ganti setiap `python` di bagian 5 dengan `py` |
| Versi Python di bawah 3.10 | Terlalu lama untuk backend | Pasang versi yang lebih baru |

## 2. Clone repo

```powershell
git clone https://github.com/andybagus26/Training-Truck-PKL-Telkomsat.git
cd Training-Truck-PKL-Telkomsat
```

Folder `Training-Truck-PKL-Telkomsat` ini selanjutnya disebut **folder utama**.

Hasil yang benar: `dir` menampilkan antara lain `Dashboard`, `backend`, `frigate`, dan `models`.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `fatal: destination path 'Training-Truck-PKL-Telkomsat' already exists and is not an empty directory.` | Di tempat itu sudah ada folder bernama sama | Pakai folder yang sudah ada (`cd Training-Truck-PKL-Telkomsat`, lalu `git pull`), atau pindah dulu ke tempat lain dengan `cd` sebelum clone |
| `Could not resolve host: github.com` | Tidak ada sambungan internet | Periksa internet, lalu ulangi |

## 3. Siapkan video uji

Video tidak ikut di GitHub. Unduh dari folder Google Drive berikut:

https://drive.google.com/drive/folders/1Mmq6ZctimH3E_j7f7894gHnq74gcZ2HB

Pilih tiga video dari sana (atau pakai video tambang sendiri berformat `.mp4`), lalu taruh di folder
`frigate\` dan **ganti namanya** sesuai tabel ini:

| Nama file yang harus ada | Tampil di Dashboard sebagai |
|---|---|
| `frigate\cctv_short.mp4` | `truck_cam` |
| `frigate\truck_cam_3.mp4` | `truck_cam_3` |
| `frigate\truck_excavator_night.mp4` | `truck_excavator_night` |

Namanya harus diganti karena ketiga nama itu sudah tertulis di pengaturan Frigate; video bernama lain
tidak akan dibaca. Isi videonya bebas, dan bila hanya punya satu video, salin video yang sama tiga kali.

Contoh, bila hasil unduhan ada di folder Downloads (ganti `video1.mp4` dengan nama file sebenarnya):

```powershell
Copy-Item "$HOME\Downloads\video1.mp4" frigate\cctv_short.mp4
Copy-Item "$HOME\Downloads\video2.mp4" frigate\truck_cam_3.mp4
Copy-Item "$HOME\Downloads\video3.mp4" frigate\truck_excavator_night.mp4
```

Lewat File Explorer juga boleh: salin file ke folder `frigate`, lalu klik kanan → Rename.

Hasil yang benar: `dir frigate\*.mp4` menampilkan ketiga nama di tabel, persis sampai garis bawahnya.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `Copy-Item : Cannot find path … because it does not exist` | Nama atau letak file sumbernya salah | Lihat nama sebenarnya dengan `dir $HOME\Downloads\*.mp4`, lalu ulangi dengan nama itu |
| `Could not find a part of the path …\frigate\…` | Sedang tidak berada di folder utama | `cd` ke folder utama dulu |
| Nama file menjadi `cctv_short.mp4.mp4` | File Explorer menyembunyikan akhiran `.mp4`, jadi akhirannya terketik dua kali | Di File Explorer, View → centang "File name extensions", lalu betulkan namanya |
| Tidak ada error, tetapi nanti kamera tidak bergambar | Nama file meleset (misalnya `cctv-short.mp4`) | Samakan dengan tabel di atas |

## 4. Nyalakan Frigate dan broker MQTT

Buka **Docker Desktop** dan tunggu sampai tulisannya "Engine running", lalu:

```powershell
cd frigate
docker compose up -d
cd ..
```

Saat pertama kali, Docker mengunduh Frigate (sekitar 1,8 GB) dan broker MQTT. Ini langkah paling lama.
Tunggu sampai PowerShell bisa diketik lagi.

Hasil yang benar:

- Di akhir muncul `Container frigate-truk Started` dan `Container frigate-mqtt Started`.
- `docker ps` menampilkan dua baris: `frigate-truk` dan `frigate-mqtt`.
- **http://localhost:5000** menampilkan halaman Frigate dengan tiga kamera yang bergambar.

Di folder `frigate\` bisa muncul tiga folder kosong bernama `cctv5.mp4`, `cctv_truck2.mp4`, dan
`cctv_truck4.mp4`. Itu sisa pengaturan kamera lama; biarkan saja.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `error during connect …` atau `… docker daemon is not running` | Docker Desktop belum dibuka atau belum siap | Buka Docker Desktop, tunggu "Engine running", lalu ulangi |
| `no configuration file provided: not found` | Perintah dijalankan di luar folder `frigate` | `cd frigate`, lalu ulangi |
| `port is already allocated`, menyebut 5000 atau 1883 | Port itu dipakai program lain | Lihat pemakainya dengan `netstat -ano \| findstr :1883` (atau `:5000`). Angka di kolom terakhir adalah nomor prosesnya; tutup program itu, lalu ulangi |
| Unduhan berhenti di tengah atau `timeout` | Internet putus | Jalankan lagi `docker compose up -d`; unduhan dilanjutkan, tidak dari awal |
| Docker Desktop meminta WSL diperbarui | WSL 2 belum terpasang atau terlalu lama | Jalankan `wsl --update` di PowerShell, nyalakan ulang komputer bila diminta |
| Kamera di http://localhost:5000 tidak bergambar | Video belum ada atau namanya salah, sehingga Docker membuat **folder** kosong bernama sama | `docker compose down`, hapus folder kosong itu, taruh videonya (bagian 3), lalu `docker compose up -d` |

## 5. Pasang backend (cukup sekali)

Dari folder utama:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
```

Perintah pertama membuat ruang Python tersendiri untuk backend; perintah kedua memasang pustakanya.

Hasil yang benar: perintah kedua berakhir tanpa tulisan `ERROR`. Tulisan `[notice] A new release of pip`
boleh diabaikan.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `ERROR: Could not open requirements file: … 'backend\requirements.txt'` | Sedang tidak berada di folder utama (misalnya masih di `frigate`) | `cd` ke folder utama, lalu ulangi |
| `No matching distribution found for fastapi==0.141.1` | Python di bawah 3.10 | Pasang Python yang lebih baru, hapus folder `backend\.venv`, lalu ulangi |
| `backend\.venv\Scripts\python … is not recognized` atau `cannot find the path` | Perintah pertama belum berhasil, atau salah folder | Jalankan perintah pertama dari folder utama |

## 6. Jalankan backend

Dari folder utama, dua baris ini di **jendela PowerShell yang sama**:

```powershell
$env:FRIGATE_URL = "http://localhost:5000"
backend\.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000
```

Baris pertama memberi tahu backend alamat Frigate. Isiannya hanya berlaku di jendela itu, jadi harus
diulang setiap kali membuka PowerShell baru.

Hasil yang benar: muncul `Uvicorn running on http://127.0.0.1:8000`. PowerShell ini tidak kembali ke tanda
`>` karena backend sedang berjalan di dalamnya. **Biarkan jendela ini terbuka**; untuk perintah lain, buka
jendela PowerShell baru. Bila Windows Firewall bertanya, pilih "Allow".

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `ModuleNotFoundError: No module named 'backend'` | Dijalankan di luar folder utama | `cd` ke folder utama, lalu ulangi kedua baris |
| `backend\.venv\Scripts\python … is not recognized` | Backend belum dipasang | Kerjakan bagian 5 |
| `only one usage of each socket address …` atau `address already in use` | Backend lain masih berjalan di jendela lain | Tekan Ctrl + C di jendela itu, lalu ulangi |
| Berulang-ulang `gagal mengambil sampel: … Frigate tidak bisa dihubungi di http://localhost:8971` | Baris `$env:FRIGATE_URL` belum dijalankan di jendela ini, jadi backend mencari di alamat bawaan | Ctrl + C, lalu jalankan lagi kedua baris |
| Sama, tetapi alamatnya `http://localhost:5000` | Frigate belum menyala | Kerjakan bagian 4; backend akan tersambung sendiri |

## 7. Buka Dashboard

Buka **http://localhost:8000** di browser. Alamat itu otomatis diarahkan ke Dashboard.

Hasil yang benar, setelah menunggu sekitar satu menit:

- Di pojok kanan atas: `Backend aktif`, `Frigate 0.17.1`, `Detektor onnx_cpu: … ms`, dan
  `Aktivitas: MQTT tersambung`.
- Tiga kamera tampil, dan di atas truk muncul kotak berwarna dengan tulisan seperti `Bergerak`, `Idle`,
  atau `Dimuat 24 dtk`.
- Tabel **Deteksi terbaru** terisi beserta fotonya.

Di Windows deteksi dikerjakan CPU, jadi pemakaian CPU memang tinggi. Lihat bagian 10 bila komputer terasa
berat.

**Kalau gagal**

| Yang terlihat | Sebabnya | Caranya |
|---|---|---|
| Browser: halaman tidak bisa dibuka | Backend tidak berjalan | Lihat jendela PowerShell backend; kerjakan bagian 6 |
| `Backend tidak terjangkau` atau pesan merah di atas | Backend berhenti setelah halaman terbuka | Jalankan lagi bagian 6; Dashboard pulih sendiri |
| `Frigate tidak terjangkau` | `$env:FRIGATE_URL` belum diisi, atau Frigate mati | Lihat tabel bagian 6; cek http://localhost:5000 |
| Kamera tampil, kotak belum ada | Baru dinyalakan, atau videonya sedang tidak memuat truk | Tunggu satu sampai dua menit |
| `Aktivitas: menunggu data MQTT` atau `MQTT tanpa data`, kotak yang tampil kotak asli Frigate | Frigate dan backend tidak bertemu di broker yang sama | Ikuti "Memeriksa MQTT" di bawah tabel ini |
| `Aktivitas: tanpa MQTT` | Broker mati | `docker ps` harus menampilkan `frigate-mqtt`; bila tidak, kerjakan bagian 4 |
| Kotak tampil dobel sesaat setelah Frigate dinyalakan ulang | Backend masih mengingat objek dari Frigate sebelumnya | Tunggu paling lama 2 menit; hilang sendiri |
| Tabel deteksi terisi tetapi tanpa foto | Pengaturan Frigate versi lama | `git pull`, lalu nyalakan ulang Frigate |
| Tampilan masih versi lama setelah `git pull` | Browser memakai salinan lama | Tekan **Ctrl + F5** |

**Memeriksa MQTT.** Jalankan:

```powershell
docker logs frigate-mqtt
```

| Yang muncul di log | Artinya | Caranya |
|---|---|---|
| `truck-backend` dan `frigate` | Sudah benar | Tunggu satu menit, lalu Ctrl + F5 |
| Hanya `truck-backend` | Frigate tidak sampai ke broker | Jalankan `findstr /B /C:"  host:" frigate\config.windows.yml`; hasilnya harus `host: mosquitto`. Bila bukan: `git pull`, lalu di folder `frigate` jalankan `docker compose down` dan `docker compose up -d` |
| Hanya `frigate` | Backend tersambung ke broker lain di komputer ini | Jalankan `netstat -ano \| findstr :1883` untuk melihat program lain yang memakai port 1883, lalu matikan program itu |

## 8. Mematikan

1. Di jendela PowerShell backend, tekan **Ctrl + C**.
2. Matikan Frigate dan broker:

```powershell
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

Tidak perlu memasang ulang dan tidak ada unduhan lagi. Buka Docker Desktop, lalu dari folder utama:

```powershell
cd frigate
docker compose up -d
cd ..
$env:FRIGATE_URL = "http://localhost:5000"
backend\.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000
```

Lalu buka http://localhost:8000.

Bila repo diperbarui teman (`git pull`), nyalakan ulang Frigate dengan `docker compose down` lalu
`docker compose up -d`, dan muat ulang Dashboard dengan **Ctrl + F5**.

## 10. Bila komputer terasa berat

Tanda-tandanya terlihat di Dashboard: status `CPU` berwarna merah, dan di kartu kamera muncul tulisan
`terlewat … fps` (frame yang tidak sempat diproses). Kotak jadi terasa tertinggal dari gambarnya.

Yang bisa dilakukan, dari yang paling mudah:

1. Tutup program lain yang berat selama Dashboard dipakai.
2. Kurangi kamera: buka `frigate\config.windows.yml`, dan pada kamera yang tidak diperlukan ubah
   `enabled: true` di bawah `detect:` menjadi `enabled: false`. Simpan, lalu jalankan
   `docker compose down` dan `docker compose up -d` di folder `frigate\`.
3. Turunkan `fps: 5` pada tiap kamera menjadi `fps: 3`, lalu nyalakan ulang dengan cara yang sama.

Perubahan nomor 2 dan 3 mengubah file milik repo. Jangan ikut di-commit, dan kembalikan dengan
`git checkout frigate/config.windows.yml` sebelum `git pull` supaya tidak bentrok.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| Frigate tidak mau menyala setelah file diubah (`docker ps` tidak menampilkan `frigate-truk`, atau statusnya `Restarting`) | Susunan baris di file rusak; jarak spasi di awal baris ikut menentukan arti | Kembalikan dengan `git checkout frigate/config.windows.yml`, lalu ubah lagi dengan hati-hati |
| `error: Your local changes to the following files would be overwritten by merge` saat `git pull` | File pengaturan masih dalam keadaan diubah | Jalankan `git checkout frigate/config.windows.yml`, lalu `git pull` lagi |

## 11. Hal lain yang perlu diketahui

- Dua pesan di `docker logs frigate-truk` ini wajar dan boleh diabaikan: `Config file is read-only, unable
  to migrate config file` dan `Did not detect hwaccel`.
- Bila masih buntu, kirim tiga hal ini ke Zacky: tangkapan layar Dashboard, isi
  http://localhost:8000/poller, dan hasil `docker logs frigate-mqtt`.

---

Catatan kejujuran: langkah Docker dan backend di panduan ini dicoba dari hasil clone baru pada
5 Oktober 2026 dengan file repo yang sama, tetapi **di Mac**. Perintah PowerShell-nya belum dijalankan di
komputer Windows sungguhan, dan pesan error khas Windows di tabel "kalau gagal" ditulis dari perilaku umum
programnya, jadi bunyinya bisa sedikit berbeda. Bila ada perintah atau pesan yang tidak cocok, kabari
Zacky supaya panduannya diperbaiki.
