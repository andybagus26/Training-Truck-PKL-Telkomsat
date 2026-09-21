"""Siapkan review per-truk untuk label yt_loading.

1. Pilih frame berisi truk (maks MAX_PER_VIDEO per video, merata; video demo Cat 775 semua).
2. Untuk tiap box truk: usulan box muatan dari model-model --models (conf >= PROPOSE_CONF, ambil skor tertinggi);
   opsional YOLO-World (--world) sebagai cadangan, hanya jika box < WORLD_MAX_FRAC luas crop truk.
3. Tulis crops.json + lembar crop bernomor di review_crops/ untuk diperiksa manual.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "datasets/ext/yt_loading"
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
MAX_PER_VIDEO = 80
KEEP_ALL = {"K6zCCLLKbKk"}
PROPOSE_CONF = 0.15
WORLD_CONF, WORLD_MAX_FRAC = 0.05, 0.6
PER_SHEET, COLS, TILE = 40, 8, (240, 180)


def main():
    global BASE, MAX_PER_VIDEO, PROPOSE_CONF
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(BASE))
    ap.add_argument("--models", nargs="+", default=["runs/yolov9t_truck_320/weights/best.pt",
                                                    "runs/yolov9t_truck_320_v2/weights/best.pt"])
    ap.add_argument("--max-per-video", type=int, default=MAX_PER_VIDEO)
    ap.add_argument("--conf", type=float, default=PROPOSE_CONF)
    ap.add_argument("--world", action="store_true", help="pakai YOLO-World sebagai cadangan usulan muatan")
    args = ap.parse_args()
    BASE, MAX_PER_VIDEO, PROPOSE_CONF = Path(args.base), args.max_per_video, args.conf
    meta = json.loads((BASE / "autolabel_meta.json").read_text())
    models = [YOLO(str(ROOT / m)) for m in args.models]
    world = None
    if args.world:
        from ultralytics import YOLOWorld
        world = YOLOWorld(str(ROOT / "weights/yolov8x-worldv2.pt"))
        world.set_classes(["pile of rocks", "heap of dirt", "pile of coal"])
    by_video = {}
    for name, info in sorted(meta.items()):
        if info["trucks"]:
            by_video.setdefault(info["video"], []).append(name)
    selected = []
    for v, names in by_video.items():
        if v not in KEEP_ALL and len(names) > MAX_PER_VIDEO:
            names = [names[i] for i in np.linspace(0, len(names) - 1, MAX_PER_VIDEO).astype(int)]
        selected += names

    crops, tiles = [], []
    for name in selected:
        im = cv2.imread(str(BASE / "images" / f"{name}.jpg"))
        H, W = im.shape[:2]
        for ti, (x1, y1, x2, y2, s) in enumerate(meta[name]["trucks"]):
            mx, my = 0.05 * (x2 - x1), 0.05 * (y2 - y1)
            cx1, cy1, cx2, cy2 = int(max(0, x1 - mx)), int(max(0, y1 - my)), int(min(W, x2 + mx)), int(min(H, y2 + my))
            crop = im[cy1:cy2, cx1:cx2]
            best = None
            if crop.shape[0] >= 32 and crop.shape[1] >= 32:
                for m in models:
                    r = m.predict(crop, imgsz=320, conf=PROPOSE_CONF, classes=[1, 2], device=DEVICE, verbose=False)[0]
                    if len(r.boxes):
                        k = int(r.boxes.conf.argmax())
                        cand = (float(r.boxes.conf[k]), int(r.boxes.cls[k]), (r.boxes.xyxy[k].cpu().numpy() + [cx1, cy1, cx1, cy1]).tolist())
                        if best is None or cand[0] > best[0]:
                            best = cand
                if best is None and world is not None:
                    r = world.predict(crop, imgsz=640, conf=WORLD_CONF, device=DEVICE, verbose=False)[0]
                    ca = crop.shape[0] * crop.shape[1]
                    for b, cf in sorted(zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()), key=lambda z: -z[1]):
                        if (b[2] - b[0]) * (b[3] - b[1]) < WORLD_MAX_FRAC * ca:
                            best = (float(cf), 1, (b + [cx1, cy1, cx1, cy1]).tolist(), "W")
                            break
            idx = len(crops)
            crops.append({"idx": idx, "frame": name, "truck": [x1, y1, x2, y2],
                          "load": None if best is None else {"conf": best[0], "cls": best[1], "box": best[2]}})
            t = crop.copy()
            if best is not None:
                bx = np.array(best[2]) - [cx1, cy1, cx1, cy1]
                col = (0, 200, 0) if best[1] == 1 else (0, 220, 255)
                cv2.rectangle(t, (int(bx[0]), int(bx[1])), (int(bx[2]), int(bx[3])), col, max(2, t.shape[1] // 120))
            t = cv2.resize(t, TILE)
            tag = "-" if best is None else f"{'W' if len(best) > 3 else ('F' if best[1] == 1 else 'E')}{best[0]:.2f}"
            cv2.rectangle(t, (0, 0), (TILE[0], 24), (0, 0, 0), -1)
            cv2.putText(t, f"{idx} {tag}", (3, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            tiles.append(t)

    out = BASE / "review_crops"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    for s in range(0, len(tiles), PER_SHEET):
        ts = tiles[s:s + PER_SHEET]
        while len(ts) % COLS:
            ts.append(np.zeros_like(ts[0]))
        sheet = np.vstack([np.hstack(ts[r:r + COLS]) for r in range(0, len(ts), COLS)])
        cv2.imwrite(str(out / f"crops_{s // PER_SHEET:03d}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 82])
    (BASE / "crops.json").write_text(json.dumps({"selected_frames": selected, "crops": crops}))
    n_load = sum(c["load"] is not None for c in crops)
    print(f"frame terpilih {len(selected)} | crop truk {len(crops)} | punya usulan muatan {n_load} | lembar {(len(tiles) + PER_SHEET - 1) // PER_SHEET}")


if __name__ == "__main__":
    main()
