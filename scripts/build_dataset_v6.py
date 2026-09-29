"""Menyusun dataset v6: dataset v5 ditambah class `bed_raised` dari rekaman dumping.

Class baru: bak truk yang sedang terangkat saat menumpahkan muatan. Polanya meniru `full_load` /
`empty_load` — kotak kecil di dalam kotak truk — supaya backend bisa menilai "truk ini sedang dumping"
tanpa kehilangan jejak truknya.

Label pada frame dumping disusun begini:

* `bed_raised` — dari pelacakan manual (`track_box.py`), sudah ditinjau satu per satu.
* `truck` — dari pelacakan manual juga untuk dua rekaman yang model v5-nya gagal total mengenali truk
  berbak terangkat; untuk sisanya diambil dari prediksi v5 yang cukup yakin.
* `full_load` / `empty_load` — dari prediksi v5, kecuali yang bertumpuk dengan kotak bak terangkat.
* `excavator` — **semua prediksi dibuang**. Model v5 memang salah mengenali bak terangkat sebagai
  excavator (di satu rekaman: 25 frame), jadi prediksinya justru racun untuk dataset ini.

Frame dumping jumlahnya jauh lebih sedikit daripada data lama, jadi digandakan beberapa kali di split
train agar tidak tenggelam.
"""
import json
import pathlib
import shutil

from ultralytics import YOLO

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "datasets/mining-truck-v5"
RAW = ROOT / "datasets/dump-raw"
OUT = ROOT / "datasets/mining-truck-v6"
NAMES = ["truck", "full_load", "empty_load", "excavator", "bed_raised"]
BED = 4
CONF = 0.40
OVERSAMPLE = 3
VAL_EVERY = 7          # 1 dari 7 frame dumping dipakai untuk validasi


def iou(a, b) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / ua if ua else 0.0


def to_yolo(cls: int, b) -> str:
    x1, y1, x2, y2 = (min(max(v, 0.0), 1.0) for v in b)
    return f"{cls} {(x1+x2)/2:.6f} {(y1+y2)/2:.6f} {x2-x1:.6f} {y2-y1:.6f}\n"


def main() -> None:
    beds = json.loads((RAW / "boxes.json").read_text())
    trucks = json.loads((RAW / "boxes_truck.json").read_text())
    model = YOLO(str(ROOT / "models/mining_truck_yolov9t_320_v5.pt"))

    if OUT.exists():
        shutil.rmtree(OUT)
    for split in ("train", "valid", "test"):
        for sub in ("images", "labels"):
            (OUT / split / sub).mkdir(parents=True, exist_ok=True)

    # data lama: gambar disimbolkan, label disalin apa adanya (class 0-3 tidak berubah)
    kept = 0
    for split in ("train", "valid", "test"):
        src_img, src_lab = BASE / split / "images", BASE / split / "labels"
        if not src_img.exists():
            continue
        for img in src_img.iterdir():
            if img.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            (OUT / split / "images" / img.name).symlink_to(img.resolve())
            lab = src_lab / f"{img.stem}.txt"
            if lab.exists():
                shutil.copy(lab, OUT / split / "labels" / lab.name)
            kept += 1
    print(f"data v5 disalin: {kept} gambar")

    # frame dumping
    added = {"train": 0, "valid": 0}
    skipped: list[str] = []
    per_class = {n: 0 for n in NAMES}
    for vid, frames in beds.items():
        for i, (fr, bed) in enumerate(sorted(frames.items(), key=lambda kv: int(kv[0]))):
            n = int(fr)
            img = RAW / "frames" / f"{vid}_{n:04d}.jpg"
            lines = [to_yolo(BED, bed)]
            per_class["bed_raised"] += 1

            tracked = trucks.get(vid, {}).get(str(n))
            if tracked:
                lines.append(to_yolo(0, tracked))
                per_class["truck"] += 1
            r = model.predict(str(img), imgsz=320, conf=CONF, verbose=False)[0]
            for b, c in zip(r.boxes.xyxyn.tolist(), r.boxes.cls.tolist()):
                name = NAMES[int(c)]
                if name == "excavator":
                    continue
                if name == "truck" and tracked:
                    continue                      # sudah ada versi manual
                if name in ("full_load", "empty_load") and iou(b, bed) > 0.4:
                    continue                      # bentrok dengan bak terangkat
                lines.append(to_yolo(int(c), b))
                per_class[name] += 1

            if not any(l.startswith("0 ") for l in lines):
                # tanpa kotak truk, frame ini justru mengajarkan bahwa truk adalah latar belakang
                per_class["bed_raised"] -= 1
                skipped.append(f"{vid}_{n:04d}")
                continue

            split = "valid" if i % VAL_EVERY == 0 else "train"
            copies = 1 if split == "valid" else OVERSAMPLE
            for k in range(copies):
                name = f"{vid}_{n:04d}" + (f"_x{k}" if k else "")
                (OUT / split / "images" / f"{name}.jpg").symlink_to(img.resolve())
                (OUT / split / "labels" / f"{name}.txt").write_text("".join(lines))
                added[split] += 1

    (OUT / "data.yaml").write_text(
        f"path: {OUT}\ntrain: train/images\nval: valid/images\ntest: test/images\n"
        f"nc: {len(NAMES)}\nnames:\n" + "".join(f"- {n}\n" for n in NAMES))
    print(f"frame dumping: +{added['train']} train (termasuk salinan), +{added['valid']} valid")
    print("kotak baru per class:", {k: v for k, v in per_class.items() if v})
    print(f"dilewati karena truknya tidak terkotaki: {len(skipped)} frame")
    for split in ("train", "valid", "test"):
        print(f"  {split}: {len(list((OUT/split/'images').iterdir()))} gambar")


if __name__ == "__main__":
    main()
