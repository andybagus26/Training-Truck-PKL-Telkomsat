"""Buat lembar review bernomor dari label YOLO: review_grid.py <images_dir> <labels_dir> <out_dir> [per_sheet]."""
import sys
from pathlib import Path

import cv2
import numpy as np

COLORS = {0: (0, 0, 255), 1: (0, 200, 0), 2: (0, 220, 255)}
NAMES = {0: "truck", 1: "full", 2: "empty"}


def tile(img_path, lbl_path, idx, size=(400, 225)):
    im = cv2.imread(str(img_path))
    H, W = im.shape[:2]
    lw = max(2, W // 320)
    for row in lbl_path.read_text().splitlines():
        v = row.split()
        if not v:
            continue
        c, cx, cy, w, h = int(v[0]), *map(float, v[1:5])
        p1 = (int((cx - w / 2) * W), int((cy - h / 2) * H))
        p2 = (int((cx + w / 2) * W), int((cy + h / 2) * H))
        cv2.rectangle(im, p1, p2, COLORS[c], lw)
        cv2.putText(im, NAMES[c], (p1[0] + 4, p1[1] + int(H / 16)), cv2.FONT_HERSHEY_SIMPLEX, W / 900, COLORS[c], lw)
    t = cv2.resize(im, size)
    cv2.rectangle(t, (0, 0), (70, 30), (0, 0, 0), -1)
    cv2.putText(t, str(idx), (4, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
    return t


def main():
    imgs, lbls, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    per = int(sys.argv[4]) if len(sys.argv) > 4 else 24
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(imgs.glob("*.jpg"))
    (out / "index.txt").write_text("\n".join(f"{i}\t{f.stem}" for i, f in enumerate(files)) + "\n")
    cols = 4
    for s in range(0, len(files), per):
        tiles = [tile(f, lbls / (f.stem + ".txt"), s + i) for i, f in enumerate(files[s:s + per])]
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        sheet = np.vstack([np.hstack(tiles[r:r + cols]) for r in range(0, len(tiles), cols)])
        cv2.imwrite(str(out / f"sheet_{s // per:03d}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(f"{len(files)} frame -> {(len(files) + per - 1) // per} lembar di {out}")


if __name__ == "__main__":
    main()
