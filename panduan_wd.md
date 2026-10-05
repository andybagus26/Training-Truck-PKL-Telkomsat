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

Untuk pengguna Mac, pakai [`panduan_mac.md`](panduan_mac.md).

## 0. Pilih jalur dulu

Di Windows ada dua cara menjalankan backend. Frigate dan broker MQTT selalu jalan di Docker; yang berbeda
hanya terminal dan Python yang dipakai.

| | **Jalur A: PowerShell** | **Jalur B: WSL (Ubuntu)** |
|---|---|---|
| Terminal | PowerShell (cari di menu Start) | Aplikasi Ubuntu, atau Terminal di VS Code yang tersambung ke WSL |
| Python | Python untuk Windows | Python di dalam Ubuntu |
| Folder venv | `backend\.venv\Scripts\` | `backend/.venv/bin/` |
| Cocok untuk | Yang ingin paling sederhana | Yang sudah terbiasa dengan Linux/WSL |

**Satu panduan, satu jalur.** Venv yang dibuat di satu jalur tidak bisa dipakai di jalur lain. Kalau
berpindah jalur, hapus folder `backend\.venv` lalu buat ulang (bagian 5).

Setiap langkah di bawah memakai tanda **[A]** untuk PowerShell dan **[B]** untuk WSL. Langkah tanpa tanda
berlaku untuk keduanya.

Aturan yang paling sering menyelamatkan: **perhatikan sedang berada di folder mana.** Sebagian besar error
di panduan ini muncul karena perintah dijalankan dari folder yang salah.

## 1. Yang harus terpasang

| Yang diperiksa | Perintah | Hasil yang benar |
|---|---|---|
| Git | `git --version` | Muncul nomor versi |
| Docker | `docker --version` | Muncul nomor versi |
| Python | `python --version` ([B]: `python3 --version`) | **3.10 atau lebih baru** |

Sediakan juga ruang kosong sekitar 8 GB (image Frigate sekitar 6 GB setelah terpasang).

**Khusus [B]:** pasang WSL dan Ubuntu dulu bila belum ada. Di PowerShell (sebagai Administrator):

```powershell
wsl -l -v
wsl --install -d Ubuntu
```

Hasil yang benar: `wsl -l -v` menampilkan `Ubuntu` dengan VERSION `2`. Di Docker Desktop, buka
**Settings → Resources → WSL Integration** dan aktifkan untuk distro Ubuntu. Setelah itu, `docker --version`
juga harus berhasil di terminal Ubuntu. Di Ubuntu, pasang juga paket venv: `sudo apt install python3-venv`.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `The term 'git' is not recognized …` | Git belum terpasang | Pasang [Git for Windows](https://git-scm.com/download/win) dengan pilihan bawaan, lalu tutup dan buka lagi PowerShell |
| `The term 'docker' is not recognized …` | Docker belum terpasang | Pasang [Docker Desktop](https://www.docker.com/products/docker-desktop/) (pilih WSL 2 saat ditanya), lalu buka aplikasinya |
| [A] `python` membuka Microsoft Store, atau `… is not recognized …` | Python belum terpasang atau belum masuk PATH | Pasang dari [python.org](https://www.python.org/downloads/windows/) dan **centang "Add python.exe to PATH"** di jendela pertama pemasangnya. Tutup dan buka lagi PowerShell |
| [A] `python` tetap tidak dikenali, tetapi `py --version` berhasil | Python terpasang tanpa PATH | Ganti setiap `python` di bagian 5 dengan `py` |
| [B] `docker: command not found` di Ubuntu | Integrasi WSL belum aktif | Aktifkan WSL Integration di Docker Desktop (lihat di atas) |
| [B] `The virtual environment was not created successfully … ensurepip is not available` | `python3-venv` belum terpasang | `sudo apt install python3-venv`, lalu ulangi bagian 5 |
| Versi Python di bawah 3.10 | Terlalu lama untuk backend | Pasang versi yang lebih baru |

## 2. Clone repo

**[A]** di PowerShell:

```powershell
git clone https://github.com/andybagus26/Training-Truck-PKL-Telkomsat.git
cd Training-Truck-PKL-Telkomsat
```

**[B]** di terminal Ubuntu. Clone di dalam folder home Ubuntu (`~`), **bukan** di `/mnt/c/...`, karena
akses file lewat `/mnt/c` jauh lebih lambat dan sering bermasalah dengan permission:

```bash
cd ~
git clone https://github.com/andybagus26/Training-Truck-PKL-Telkomsat.git
cd Training-Truck-PKL-Telkomsat
```

Folder `Training-Truck-PKL-Telkomsat` ini selanjutnya disebut **folder utama**.

Hasil yang benar: `dir` ([B]: `ls`) menampilkan antara lain `Dashboard`, `backend`, `frigate`, dan `models`.

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

**[A]**

```powershell
Copy-Item "$HOME\Downloads\video1.mp4" frigate\cctv_short.mp4
Copy-Item "$HOME\Downloads\video2.mp4" frigate\truck_cam_3.mp4
Copy-Item "$HOME\Downloads\video3.mp4" frigate\truck_excavator_night.mp4
```

**[B]** (ganti `NamaWindows` dengan nama pengguna Windows kamu):

```bash
cp /mnt/c/Users/NamaWindows/Downloads/video1.mp4 frigate/cctv_short.mp4
cp /mnt/c/Users/NamaWindows/Downloads/video2.mp4 frigate/truck_cam_3.mp4
cp /mnt/c/Users/NamaWindows/Downloads/video3.mp4 frigate/truck_excavator_night.mp4
```

Hasil yang benar: `dir frigate\*.mp4` ([B]: `ls frigate/*.mp4`) menampilkan ketiga nama di tabel, persis
sampai garis bawahnya.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `Cannot find path … because it does not exist` / `No such file or directory` | Nama atau letak file sumbernya salah | Lihat nama sebenarnya dengan `dir $HOME\Downloads\*.mp4` ([B]: `ls /mnt/c/Users/NamaWindows/Downloads/*.mp4`), lalu ulangi dengan nama itu |
| `Could not find a part of the path …\frigate\…` | Sedang tidak berada di folder utama | `cd` ke folder utama dulu |
| Nama file menjadi `cctv_short.mp4.mp4` | File Explorer menyembunyikan akhiran `.mp4`, jadi akhirannya terketik dua kali | Di File Explorer, View → centang "File name extensions", lalu betulkan namanya |
| Tidak ada error, tetapi nanti kamera tidak bergambar | Nama file meleset (misalnya `cctv-short.mp4`) | Samakan dengan tabel di atas |

## 4. Nyalakan Frigate dan broker MQTT

Buka **Docker Desktop** dan tunggu sampai tulisannya "Engine running". Sebelum menyalakan, pastikan port
**1883** dan **5000** kosong.

**Cek port 1883.** Ini sumber masalah yang paling sering.

**[A]** di PowerShell:

```powershell
netstat -ano | findstr :1883
```

**[B]** di terminal Ubuntu:

```bash
sudo ss -ltnp | grep 1883
```

Hasil yang benar: tidak ada output sama sekali.

Perhatikan: di Windows, `netstat` untuk port yang dipakai program di dalam WSL hanya menampilkan
`wslrelay.exe`. Itu cuma penerus port, bukan pelakunya. Pelaku sebenarnya hanya kelihatan lewat `ss` di
Ubuntu. Kalau yang muncul `mosquitto`, lihat tabel "Kalau gagal" di bawah.

Lalu nyalakan Frigate dari folder utama:

```bash
cd frigate
docker compose up -d
cd ..
```

Saat pertama kali, Docker mengunduh Frigate (sekitar 1,8 GB) dan broker MQTT. Ini langkah paling lama.
Tunggu sampai terminal bisa diketik lagi.

Hasil yang benar:

- Di akhir muncul `Container frigate-truk Started` dan `Container frigate-mqtt Started`.
- `docker ps` menampilkan dua baris: `frigate-truk` dan `frigate-mqtt`.
- **http://localhost:5000** menampilkan halaman Frigate dengan tiga kamera yang bergambar.

Bila repo kamu masih versi lama, di folder `frigate/` bisa muncul folder kosong bernama `cctv5.mp4`,
`cctv_truck2.mp4`, atau `cctv_truck4.mp4`. Itu sisa pengaturan kamera lama; biarkan saja atau hapus bila
kamera itu sudah dibuang dari `config.windows.yml` dan `docker-compose.yml`.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `error during connect …` atau `… docker daemon is not running` | Docker Desktop belum dibuka atau belum siap | Buka Docker Desktop, tunggu "Engine running", lalu ulangi |
| `no configuration file provided: not found` | Perintah dijalankan di luar folder `frigate` | `cd frigate`, lalu ulangi |
| `failed to bind host port 0.0.0.0:1883/tcp: address already in use`, atau `port is already allocated` | Port 1883 (atau 5000) dipakai program lain | Cari pemakainya dengan perintah cek port di atas. Bila itu `mosquitto` di Ubuntu, lihat baris berikutnya. Bila program lain, tutup dulu, lalu `docker compose up -d --force-recreate mosquitto` |
| [B] `ss` menampilkan `mosquitto` | Mosquitto terpasang langsung di Ubuntu dan merebut port 1883. Menghentikannya saja tidak cukup, karena hidup lagi setelah WSL atau laptop dinyalakan ulang | `sudo systemctl disable --now mosquitto`, cek lagi dengan `ss` sampai kosong, lalu `docker compose up -d --force-recreate mosquitto` |
| `Conflict. The container name "/frigate-mqtt" is already in use` | Ada container lama bernama sama yang tidak dikelola compose ini | `docker rm -f frigate-mqtt frigate-truk`, lalu `docker compose up -d`. Config dan rekaman tidak ikut hilang |
| Unduhan berhenti di tengah atau `timeout` | Internet putus | Jalankan lagi `docker compose up -d`; unduhan dilanjutkan, tidak dari awal |
| Docker Desktop meminta WSL diperbarui | WSL 2 belum terpasang atau terlalu lama | Jalankan `wsl --update` di PowerShell, nyalakan ulang komputer bila diminta |
| Kamera di http://localhost:5000 tidak bergambar | Video belum ada atau namanya salah, sehingga Docker membuat **folder** kosong bernama sama | `docker compose down`, hapus folder kosong itu, taruh videonya (bagian 3), lalu `docker compose up -d` |

Peringatan `the attribute 'version' is obsolete` boleh diabaikan.

## 5. Pasang backend (cukup sekali)

Dari folder utama.

**[A]** di PowerShell:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
```

**[B]** di terminal Ubuntu:

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
| `ERROR: Could not open requirements file: … requirements.txt` | Sedang tidak berada di folder utama (misalnya masih di `frigate`) | `cd` ke folder utama, lalu ulangi |
| `No matching distribution found for fastapi==…` | Python di bawah 3.10 | Pasang Python yang lebih baru, hapus folder `backend/.venv`, lalu ulangi |
| [A] `backend\.venv\Scripts\python … is not recognized` | Perintah pertama belum berhasil, atau salah folder | Jalankan perintah pertama dari folder utama |
| [B] `No such file or directory: backend/.venv/bin/python` | Perintah pertama belum berhasil | Ulangi perintah pertama; bila gagal, lihat baris `python3-venv` di bagian 1 |
| [B] `bin/python` tidak ada, tetapi ada folder `Scripts` di dalam `.venv` | Venv dibuat dari Windows, bukan dari Ubuntu | Hapus `backend/.venv`, lalu buat ulang dari terminal Ubuntu |

## 6. Jalankan backend

Dari folder utama, di terminal yang masih terbuka sampai selesai dipakai.

**[A]** dua baris ini di **jendela PowerShell yang sama**:

```powershell
$env:FRIGATE_URL = "http://localhost:5000"
backend\.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000
```

Isian `$env:` hanya berlaku di jendela itu, jadi harus diulang setiap kali membuka PowerShell baru.

**[B]** satu perintah di terminal Ubuntu (sintaks `VAR=nilai` hanya jalan di bash, bukan di PowerShell):

```bash
FRIGATE_URL=http://localhost:5000 \
MQTT_HOST=localhost \
MQTT_PORT=1883 \
backend/.venv/bin/uvicorn backend.app.main:app --port 8000
```

Hasil yang benar: muncul `Uvicorn running on http://127.0.0.1:8000`. Terminal ini tidak kembali ke tanda
prompt karena backend sedang berjalan di dalamnya. **Biarkan terminal ini terbuka**; untuk perintah lain,
buka terminal baru. Bila Windows Firewall bertanya, pilih "Allow".

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `ModuleNotFoundError: No module named 'backend'` | Dijalankan di luar folder utama | `cd` ke folder utama, lalu ulangi |
| `… is not recognized` / `No such file or directory` pada `.venv` | Backend belum dipasang | Kerjakan bagian 5 |
| `only one usage of each socket address …` atau `address already in use` | Backend lain masih berjalan di terminal lain | Tekan Ctrl + C di terminal itu, lalu ulangi |
| Berulang-ulang `gagal mengambil sampel: … Frigate tidak bisa dihubungi di http://localhost:8971` | `FRIGATE_URL` belum diisi di terminal ini, jadi backend mencari di alamat bawaan | Ctrl + C, lalu jalankan lagi dengan `FRIGATE_URL` |
| Sama, tetapi alamatnya `http://localhost:5000` | Frigate belum menyala | Kerjakan bagian 4; backend akan tersambung sendiri |
| [B] `sintaks … tidak dikenali` setelah menempelkan perintah | Perintah bash ditempel di PowerShell | Jalankan dari terminal Ubuntu |

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
| Browser: halaman tidak bisa dibuka | Backend tidak berjalan | Lihat terminal backend; kerjakan bagian 6 |
| `Backend tidak terjangkau` atau pesan merah di atas | Backend berhenti setelah halaman terbuka | Jalankan lagi bagian 6; Dashboard pulih sendiri |
| `Frigate tidak terjangkau` | `FRIGATE_URL` belum diisi, atau Frigate mati | Lihat tabel bagian 6; cek http://localhost:5000 |
| Kamera tampil, kotak belum ada | Baru dinyalakan, atau videonya sedang tidak memuat truk | Tunggu satu sampai dua menit |
| `Aktivitas: menunggu data MQTT` atau `MQTT tanpa data`, kotak yang tampil kotak asli Frigate | Frigate dan backend tidak bertemu di broker yang sama | Ikuti "Memeriksa MQTT" di bawah tabel ini |
| `Aktivitas: tanpa MQTT` | Broker mati | `docker ps` harus menampilkan `frigate-mqtt`; bila tidak, kerjakan bagian 4 |
| Kotak tampil dobel sesaat setelah Frigate dinyalakan ulang | Backend masih mengingat objek dari Frigate sebelumnya | Tunggu paling lama 2 menit; hilang sendiri |
| Tabel deteksi terisi tetapi tanpa foto | Pengaturan Frigate versi lama | `git pull`, lalu nyalakan ulang Frigate |
| Tampilan masih versi lama setelah `git pull` | Browser memakai salinan lama | Tekan **Ctrl + F5** |

**Memeriksa MQTT.** Jalankan salah satunya. Cek pertama menunjukkan apakah Frigate benar-benar mengirim
pesan ke broker.

```bash
docker exec frigate-mqtt mosquitto_sub -t "frigate/#" -v -C 5
docker port frigate-mqtt
docker logs frigate-mqtt
```

| Yang muncul | Artinya | Caranya |
|---|---|---|
| `mosquitto_sub` menampilkan pesan seperti `frigate/truck_cam/detect/state ON` | Frigate sudah publish ke broker | Restart backend (Ctrl + C, jalankan lagi), lalu Ctrl + F5 di browser |
| `mosquitto_sub` diam, tidak ada pesan | Frigate belum tersambung ke broker | Cek `host: mosquitto` di `frigate/config.windows.yml` (bukan `localhost`: di dalam container, `localhost` adalah container Frigate sendiri). Lalu `docker restart frigate-truk` |
| `docker port frigate-mqtt` kosong | Port 1883 tidak di-publish karena bentrok | Kembali ke bagian 4, tabel "Kalau gagal", baris port 1883 |
| `docker logs frigate-mqtt` hanya menyebut `truck-backend` | Frigate tidak sampai ke broker | Lihat dua baris di atas |
| `docker logs frigate-mqtt` hanya menyebut `frigate` | Backend tersambung ke broker lain di komputer ini | Periksa port 1883 (bagian 4); matikan broker lain itu |
| Menyebut `truck-backend` dan `frigate` | Sudah benar | Tunggu satu menit, lalu Ctrl + F5 |

## 8. Mematikan

1. Di terminal backend, tekan **Ctrl + C**.
2. Matikan Frigate dan broker:

```bash
cd frigate
docker compose down
cd ..
```

Rekaman Frigate tetap tersimpan dan terus bertambah (sekitar 160 MB dalam 15 menit untuk tiga kamera).
Untuk mematikan sekaligus menghapus rekamannya, pakai `docker compose down -v`.

**[B]** Untuk melepas RAM yang ditahan WSL, jalankan juga di PowerShell Windows:

```powershell
wsl --shutdown
```

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `no configuration file provided: not found` | Bukan di folder `frigate` | `cd frigate`, lalu ulangi |

## 9. Menjalankan lagi lain waktu

Tidak perlu memasang ulang dan tidak ada unduhan lagi. Buka Docker Desktop, cek port 1883 kosong (bagian 4),
lalu dari folder utama:

**[A]**

```powershell
cd frigate
docker compose up -d
cd ..
$env:FRIGATE_URL = "http://localhost:5000"
backend\.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000
```

**[B]**

```bash
cd frigate
docker compose up -d
cd ..
FRIGATE_URL=http://localhost:5000 MQTT_HOST=localhost MQTT_PORT=1883 \
  backend/.venv/bin/uvicorn backend.app.main:app --port 8000
```

Lalu buka http://localhost:8000.

Bila repo diperbarui teman (`git pull`), nyalakan ulang Frigate dengan `docker compose down` lalu
`docker compose up -d`, dan muat ulang Dashboard dengan **Ctrl + F5**.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| `error: Your local changes to the following files would be overwritten by merge` saat `git pull` | File yang kamu ubah juga diubah di GitHub | Bila perubahan lokal tidak diperlukan: `git restore <nama file>`, lalu `git pull`. Bila masih diperlukan: `git stash`, `git pull`, `git stash pop`, lalu selesaikan konflik bila ada |
| `Please clean your repository working tree before checkout` di VS Code | Penyebabnya sama dengan di atas: ada perubahan lokal yang belum di-commit | Selesaikan dengan salah satu cara di baris atas |

## 10. Bila komputer terasa berat

Tanda-tandanya terlihat di Dashboard: status `CPU` berwarna merah, dan di kartu kamera muncul tulisan
`terlewat … fps` (frame yang tidak sempat diproses). Kotak jadi terasa tertinggal dari gambarnya.

Yang bisa dilakukan, dari yang paling mudah:

1. Tutup program lain yang berat selama Dashboard dipakai.
2. Kurangi kamera: buka `frigate/config.windows.yml`, dan pada kamera yang tidak diperlukan ubah
   `enabled: true` di bawah `detect:` menjadi `enabled: false`. Simpan, lalu jalankan
   `docker compose down` dan `docker compose up -d` di folder `frigate/`.
3. Turunkan `fps: 5` pada tiap kamera menjadi `fps: 3`, lalu nyalakan ulang dengan cara yang sama.
4. **Batasi memori WSL.** Docker Desktop memakai WSL 2, dan proses `vmmemWSL` di Task Manager bisa
   menghabiskan banyak RAM. Buat file `C:\Users\NamaWindows\.wslconfig` berisi:

   ```ini
   [wsl2]
   memory=6GB
   processors=4
   ```

   Sesuaikan angkanya dengan spesifikasi laptop, lalu jalankan `wsl --shutdown` di PowerShell. Berlaku
   setelah Docker Desktop dan WSL dinyalakan lagi.

Perubahan nomor 2 dan 3 mengubah file milik repo. Jangan ikut di-commit, dan kembalikan dengan
`git checkout frigate/config.windows.yml` sebelum `git pull` supaya tidak bentrok.

**Kalau gagal**

| Yang muncul | Sebabnya | Caranya |
|---|---|---|
| Frigate tidak mau menyala setelah file diubah (`docker ps` tidak menampilkan `frigate-truk`, atau statusnya `Restarting`) | Susunan baris di file rusak; jarak spasi di awal baris ikut menentukan arti | Kembalikan dengan `git checkout frigate/config.windows.yml`, lalu ubah lagi dengan hati-hati |
| RAM tidak turun walau container sudah dimatikan | WSL menahan memori yang pernah dipakai | `wsl --shutdown` di PowerShell |

## 11. Hal lain yang perlu diketahui

- Dua pesan di `docker logs frigate-truk` ini wajar dan boleh diabaikan: `Config file is read-only, unable
  to migrate config file` dan `Did not detect hwaccel`.
- Skrip debug sementara (misalnya `debug-windows.ps1` atau `debug-wsl.sh`) tidak perlu di-commit; isinya
  terikat ke nama distro dan path komputer masing-masing.
- Bila masih buntu, kirim tiga hal ini ke Zacky: tangkapan layar Dashboard, isi
  http://localhost:8000/poller, dan hasil `docker logs frigate-mqtt`.

---
