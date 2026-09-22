"""Usulkan kotak excavator untuk gambar non-rf100 di dataset v4, lalu susun lembar pemeriksaan.

Model tahap A dijalankan pada gambar asli (bukan salinan/versi malam). Hasilnya:
  - proposals.json  : {nama_gambar: ["3 cx cy w h", ...]} untuk dipakai build_dataset_v5.py --stage b
  - review/*.jpg    : lembar bernomor; kotak biru = label lama, magenta = usulan excavator
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "datasets/mining-truck-v4"
SOURCES = ["datasets/mining-truck-clean", "datasets/ext/yt_loading_clean", "datasets/ext/yt_v4_clean"]
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
OLD = {0: (255, 128, 0), 1: (0, 200, 0), 2: (0, 220, 255)}
PER_SHEET, COLS, TILE = 12, 4, (480, 300)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=str(ROOT / "runs/yolov9t_v5a_excavator/weights/best.pt"))
    ap.add_argument("--out", default=str(ROOT / "datasets/ext/excavator_review"))
    ap.add_argument("--conf", type=float, default=0.25)
    args = ap.parse_args()

    model = YOLO(args.weights)
    out = Path(args.out)
    (out / "review").mkdir(parents=True, exist_ok=True)
    for old in (out / "review").glob("*.jpg"):
        old.unlink()

    # gambar asli (bukan rf100) diambil dari dataset sumbernya, supaya salinan _dupN/_rN tidak terlewat
    imgs = []
    for src in SOURCES:
        for split in ["train", "valid", "test"]:
            d = ROOT / src / split / "images"
            if d.exists():
                imgs += [(ROOT / src / split, p) for p in sorted(d.iterdir())]

    proposals, tiles, index = {}, [], []
    for split, p in imgs:
        r = model.predict(str(p), imgsz=320, conf=args.conf, classes=[3], device=DEVICE, verbose=False)[0]
        if not len(r.boxes):
            continue
        rows = [f"3 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}" for cx, cy, w, h in r.boxes.xywhn.cpu().numpy()]
        proposals[p.stem] = rows
        im = cv2.imread(str(p))
        H, W = im.shape[:2]
        lw = max(2, W // 320)
        for line in (split / "labels" / f"{p.stem}.txt").read_text().split("\n"):
            v = line.split()
            if not v:
                continue
            c, cx, cy, w, h = int(v[0]), *map(float, v[1:5])
            cv2.rectangle(im, (int((cx - w / 2) * W), int((cy - h / 2) * H)),
                          (int((cx + w / 2) * W), int((cy + h / 2) * H)), OLD[c], lw)
        for (cx, cy, w, h), s in zip(r.boxes.xywhn.cpu().numpy(), r.boxes.conf.cpu().numpy()):
            p1 = (int((cx - w / 2) * W), int((cy - h / 2) * H))
            p2 = (int((cx + w / 2) * W), int((cy + h / 2) * H))
            cv2.rectangle(im, p1, p2, (255, 0, 255), lw + 1)
            cv2.putText(im, f"{s:.2f}", (p1[0] + 4, p1[1] + int(H / 14)), cv2.FONT_HERSHEY_SIMPLEX, W / 800, (255, 0, 255), lw)
        idx = len(index)
        index.append(p.stem)
        t = cv2.resize(im, TILE)
        cv2.rectangle(t, (0, 0), (86, 26), (0, 0, 0), -1)
        cv2.putText(t, f"{idx} x{len(rows)}", (4, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        tiles.append(t)

    for s in range(0, len(tiles), PER_SHEET):
        ts = tiles[s:s + PER_SHEET]
        while len(ts) % COLS:
            ts.append(np.zeros_like(ts[0]))
        cv2.imwrite(str(out / "review" / f"exc_{s // PER_SHEET:03d}.jpg"),
                    np.vstack([np.hstack(ts[r:r + COLS]) for r in range(0, len(ts), COLS)]),
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
    (out / "proposals.json").write_text(json.dumps(proposals))
    (out / "index.txt").write_text("\n".join(f"{i}\t{s}" for i, s in enumerate(index)) + "\n")
    print(f"{len(imgs)} gambar diperiksa | {len(proposals)} punya usulan excavator "
          f"({sum(len(v) for v in proposals.values())} kotak) | {(len(tiles) + PER_SHEET - 1) // PER_SHEET} lembar")


if __name__ == "__main__":
    main()
