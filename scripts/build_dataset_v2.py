"""Dataset v2 = dataset bersih (3 class) + rf100-excavators.

rf100: 'dump truck' -> truck; excavator & wheel loader tidak dilabel (jadi contoh negatif);
full_load/empty_load dari pseudo-label model v1 per crop truk (hanya conf >= PSEUDO_CONF).
"""
import json, shutil, sys, yaml
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "datasets" / "mining-truck-clean"
RF100 = ROOT / "datasets" / "ext" / "rf100-excavators"
OUT = ROOT / "datasets" / "mining-truck-v2"
PSEUDO = Path(sys.argv[1])
PSEUDO_CONF = 0.7
NAMES = ["truck", "full_load", "empty_load"]

pseudo = json.loads(PSEUDO.read_text())
if OUT.exists():
    shutil.rmtree(OUT)
stat = Counter()
for split in ["train", "valid", "test"]:
    for sub in ["images", "labels"]:
        (OUT / split / sub).mkdir(parents=True)
    # 1) data asli
    for img in (CLEAN / split / "images").iterdir():
        shutil.copy2(img, OUT / split / "images" / img.name)
        shutil.copy2(CLEAN / split / "labels" / (img.stem + ".txt"), OUT / split / "labels" / (img.stem + ".txt"))
        stat[f"{split} asli"] += 1
    # 2) rf100
    for img in (RF100 / split / "images").iterdir():
        p = pseudo[str(img.relative_to(ROOT))]
        rows = [f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}" for cx, cy, w, h in p["trucks"]]
        rows += [f"{int(c)} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}" for c, cx, cy, w, h, s in p["loads"] if s >= PSEUDO_CONF]
        name = "rf100_" + img.name
        shutil.copy2(img, OUT / split / "images" / name)
        (OUT / split / "labels" / (Path(name).stem + ".txt")).write_text("\n".join(rows) + ("\n" if rows else ""))
        stat[f"{split} rf100 {'dengan truk' if p['trucks'] else 'negatif'}"] += 1
        stat[f"{split} rf100 pseudo-load"] += sum(1 for l in p["loads"] if l[5] >= PSEUDO_CONF)

(OUT / "data.yaml").write_text(yaml.safe_dump({
    "path": str(OUT), "train": "train/images", "val": "valid/images", "test": "test/images",
    "nc": len(NAMES), "names": NAMES}, sort_keys=False))
for k in sorted(stat):
    print(f"{k:<32} {stat[k]}")
