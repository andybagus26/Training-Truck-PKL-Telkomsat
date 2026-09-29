"""Menyusun dataset benih untuk class `bed_raised` dari kotak hasil pelacakan.

Satu class saja, dipakai melatih detektor sementara yang tugasnya melabeli sisa rekaman dumping
secara otomatis. Hasil pelabelan otomatis itu ditinjau dulu sebelum masuk ke dataset v6.
"""
import json
import pathlib
import random
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "datasets/dump-raw"
OUT = ROOT / "datasets/dump-seed"
VAL_RATIO = 0.2


def main() -> None:
    boxes = json.loads((RAW / "boxes.json").read_text())
    items = [(v, int(f), b) for v, fr in boxes.items() for f, b in fr.items()]
    random.Random(0).shuffle(items)
    n_val = int(len(items) * VAL_RATIO)
    for split in ("train", "valid"):
        for sub in ("images", "labels"):
            (OUT / split / sub).mkdir(parents=True, exist_ok=True)
            for f in (OUT / split / sub).glob("*"):
                f.unlink()
    for i, (vid, fr, b) in enumerate(items):
        split = "valid" if i < n_val else "train"
        src = RAW / "frames" / f"{vid}_{fr:04d}.jpg"
        name = f"{vid}_{fr:04d}"
        shutil.copy(src, OUT / split / "images" / f"{name}.jpg")
        x1, y1, x2, y2 = b
        cx, cy, w, h = (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1
        (OUT / split / "labels" / f"{name}.txt").write_text(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
    (OUT / "data.yaml").write_text(
        f"path: {OUT}\ntrain: train/images\nval: valid/images\nnc: 1\nnames: [bed_raised]\n")
    print(f"{len(items)} gambar -> {OUT} (train {len(items)-n_val}, valid {n_val})")


if __name__ == "__main__":
    main()
