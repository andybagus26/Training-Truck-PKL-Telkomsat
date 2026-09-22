"""Bangun dataset 4 class (truck, full_load, empty_load, excavator).

Tahap A (--stage a): hanya gambar rf100, dengan label excavator dari dataset aslinya.
  Dipakai untuk melatih model sementara yang bisa mengusulkan kotak excavator.
Tahap B (--stage b): dataset v4 lengkap + label excavator (rf100 dari aslinya,
  sisanya dari file usulan yang sudah diperiksa manual lewat --excavator-json).
"""
import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "datasets/mining-truck-v4"
RF100 = ROOT / "datasets/ext/rf100-excavators"
NAMES = ["truck", "full_load", "empty_load", "excavator"]
RF100_EXCAVATOR = 0  # index class 'EXCAVATORS' di dataset rf100


def rf100_excavator_boxes(stem: str) -> list[str]:
    """Kotak excavator (format YOLO) untuk satu gambar rf100, dari label aslinya."""
    name = stem[len("rf100_"):] if stem.startswith("rf100_") else stem
    for split in ("train", "valid", "test"):
        f = RF100 / split / "labels" / f"{name}.txt"
        if f.exists():
            return [f"3 {' '.join(r.split()[1:5])}"
                    for r in f.read_text().split("\n")
                    if r.strip() and int(r.split()[0]) == RF100_EXCAVATOR]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["a", "b"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--excavator-json", help="tahap b: hasil review {accepted: {gambar: [kotak]}, exclude: [gambar]}")
    args = ap.parse_args()

    out = Path(args.out)
    reviewed = json.loads(Path(args.excavator_json).read_text()) if args.excavator_json else {}
    extra, exclude = reviewed.get("accepted", {}), set(reviewed.get("exclude", []))
    if out.exists():
        shutil.rmtree(out)
    stat = Counter()
    for split in ["train", "valid", "test"]:
        (out / split / "images").mkdir(parents=True)
        (out / split / "labels").mkdir(parents=True)
        for img in (V4 / split / "images").iterdir():
            is_rf100 = img.stem.startswith("rf100_")
            if args.stage == "a" and not is_rf100:
                continue
            base = re.sub(r"_(dup\d|r\d)$", "", img.stem[:-6] if img.stem.endswith("_night") else img.stem)
            if base in exclude:      # excavator terlihat tapi tidak punya kotak yang layak
                stat[f"{split} dikeluarkan"] += 1
                continue
            rows = [r for r in (V4 / split / "labels" / f"{img.stem}.txt").read_text().split("\n") if r.strip()]
            exc = rf100_excavator_boxes(base) if is_rf100 else extra.get(base, [])
            rows += exc
            shutil.copy2(img, out / split / "images" / img.name)
            (out / split / "labels" / f"{img.stem}.txt").write_text("\n".join(rows) + ("\n" if rows else ""))
            stat[f"{split} gambar"] += 1
            stat[f"{split} kotak excavator"] += len(exc)

    (out / "data.yaml").write_text(yaml.safe_dump(
        {"path": str(out.resolve()), "train": "train/images", "val": "valid/images", "test": "test/images",
         "nc": len(NAMES), "names": NAMES}, sort_keys=False))
    for k in sorted(stat):
        print(f"{k:<26} {stat[k]}")


if __name__ == "__main__":
    main()
