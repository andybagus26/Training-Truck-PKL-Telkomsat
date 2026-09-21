"""Terapkan decisions.txt (hasil review manual) ke crops.json -> dataset yt_loading_clean (train/valid)."""
import argparse, json, shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_ap = argparse.ArgumentParser()
_ap.add_argument("--base", default=str(ROOT / "datasets/ext/yt_loading"))
_ap.add_argument("--out", default=str(ROOT / "datasets/ext/yt_loading_clean"))
_args = _ap.parse_args()
BASE, OUT = Path(_args.base), Path(_args.out)
VALID_EVERY = 7   # tiap frame ke-7 per video -> valid

data = json.loads((BASE / "crops.json").read_text())
crops = {c["idx"]: c for c in data["crops"]}
dec = {}
for line in (BASE / "decisions.txt").read_text().splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    code, *ids = line.split()
    for i in ids:
        i = int(i)
        assert i not in dec, f"crop {i} diputuskan dua kali"
        dec[i] = code
missing = sorted(set(crops) - set(dec))
assert not missing, f"crop belum direview: {missing[:20]}"
for i, code in dec.items():
    if code in "FE":
        assert crops[i]["load"] is not None, f"crop {i} ditandai {code} tapi tidak punya usulan box"

amb = {int(x) for line in (BASE / "ambiguous_trucks.txt").read_text().splitlines()
       if line.strip() and not line.startswith("#") for x in line.split()}
assert all(dec[i] == "d" for i in amb), "crop ambigu harus berkode d"
frames = {}
for i, c in crops.items():
    frames.setdefault(c["frame"], []).append(i)
if OUT.exists():
    shutil.rmtree(OUT)
stat, per_video = Counter(), Counter()
for split in ["train", "valid"]:
    (OUT / split / "images").mkdir(parents=True)
    (OUT / split / "labels").mkdir(parents=True)
for name in sorted(frames):
    ids = frames[name]
    if any(i in amb for i in ids):
        stat["frame dibuang (truk ambigu)"] += 1
        continue
    trucks = [i for i in ids if dec[i] != "d"]
    if not trucks:
        stat["frame dibuang (tanpa truk)"] += 1
        continue
    stat["box bukan-truk dihapus"] += len(ids) - len(trucks)
    ids = trucks
    img = BASE / "images" / f"{name}.jpg"
    import cv2
    H, W = cv2.imread(str(img)).shape[:2]
    rows = []
    for i in ids:
        x1, y1, x2, y2 = crops[i]["truck"]
        rows.append(f"0 {(x1+x2)/2/W:.6f} {(y1+y2)/2/H:.6f} {(x2-x1)/W:.6f} {(y2-y1)/H:.6f}")
        stat["truck"] += 1
        if dec[i] in "FE":
            bx1, by1, bx2, by2 = crops[i]["load"]["box"]
            c = 1 if dec[i] == "F" else 2
            rows.append(f"{c} {(bx1+bx2)/2/W:.6f} {(by1+by2)/2/H:.6f} {(bx2-bx1)/W:.6f} {(by2-by1)/H:.6f}")
            stat["full_load" if c == 1 else "empty_load"] += 1
    video = name.split("_")[1] if not name.startswith("yt__") else "_" + name.split("_")[2]
    per_video[video] += 1
    split = "valid" if per_video[video] % VALID_EVERY == 0 else "train"
    shutil.copy2(img, OUT / split / "images" / img.name)
    (OUT / split / "labels" / f"{name}.txt").write_text("\n".join(rows) + "\n")
    stat[f"frame {split}"] += 1
print(dict(stat))
print("frame per video:", dict(per_video))
