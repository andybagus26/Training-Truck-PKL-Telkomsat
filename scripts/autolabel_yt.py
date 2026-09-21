"""Ekstrak frame dari video loading haul truck + label otomatis.

- truck      : YOLOv9-e COCO (class 7 'truck'), dipakai hanya sebagai alat pelabel
- full/empty : model v1 dijalankan pada crop tiap truk (crop mirip distribusi data training asli)
- Video K6zCCLLKbKk detik 0-31 (segmen demo Cat 775) TIDAK diambil.
Output: datasets/ext/yt_loading/{images,labels}, review/*.jpg untuk pemeriksaan visual.
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
EVERY_S = 1.5          # ambil 1 frame tiap 1.5 detik
DEDUP_DIFF = 6.0       # lewati frame yang hampir sama dengan frame terakhir yang disimpan
EXCLUDE = {"K6zCCLLKbKk": (0.0, 32.0)}   # segmen demo
TRUCK_CONF, LOAD_CONF = 0.4, 0.6


def frames(video, every_s):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step, i, last = max(int(round(fps * every_s)), 1), 0, None
    ex = EXCLUDE.get(video.stem)
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            t = i / fps
            if not (ex and ex[0] <= t < ex[1]):
                _, fr = cap.retrieve()
                g = cv2.cvtColor(cv2.resize(fr, (160, 90)), cv2.COLOR_BGR2GRAY).astype(np.float32)
                if last is None or np.abs(g - last).mean() > DEDUP_DIFF:
                    last = g
                    yield t, fr
        i += 1


def main():
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(BASE))
    ap.add_argument("--every", type=float, default=EVERY_S)
    ap.add_argument("--load-weights", default=str(ROOT / "runs/yolov9t_truck_320/weights/best.pt"))
    args = ap.parse_args()
    BASE = Path(args.base)
    VIDEOS = BASE / "videos"
    coco = YOLO(str(ROOT / "weights/yolov9e.pt"))
    v1 = YOLO(args.load_weights)
    (BASE / "images").mkdir(parents=True, exist_ok=True)
    (BASE / "labels").mkdir(parents=True, exist_ok=True)
    meta = {}
    for video in sorted(VIDEOS.glob("*.mp4")):
        n = 0
        for t, fr in frames(video, args.every):
            H, W = fr.shape[:2]
            name = f"yt_{video.stem}_{t:06.1f}"
            r = coco.predict(fr, imgsz=640, conf=TRUCK_CONF, classes=[7], device=DEVICE, verbose=False)[0]
            rows, info = [], {"video": video.stem, "t": t, "trucks": [], "loads": []}
            for (x1, y1, x2, y2), s in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()):
                if (x2 - x1) * (y2 - y1) > 0.9 * W * H:
                    continue
                rows.append(f"0 {(x1 + x2) / 2 / W:.6f} {(y1 + y2) / 2 / H:.6f} {(x2 - x1) / W:.6f} {(y2 - y1) / H:.6f}")
                info["trucks"].append([float(x1), float(y1), float(x2), float(y2), float(s)])
                mx, my = 0.05 * (x2 - x1), 0.05 * (y2 - y1)
                cx1, cy1 = int(max(0, x1 - mx)), int(max(0, y1 - my))
                cx2, cy2 = int(min(W, x2 + mx)), int(min(H, y2 + my))
                if cx2 - cx1 < 48 or cy2 - cy1 < 48:
                    continue
                lr = v1.predict(fr[cy1:cy2, cx1:cx2], imgsz=320, conf=LOAD_CONF, classes=[1, 2], device=DEVICE, verbose=False)[0]
                if len(lr.boxes):
                    k = int(lr.boxes.conf.argmax())
                    c = int(lr.boxes.cls[k])
                    bx1, by1, bx2, by2 = lr.boxes.xyxy[k].cpu().numpy() + [cx1, cy1, cx1, cy1]
                    rows.append(f"{c} {(bx1 + bx2) / 2 / W:.6f} {(by1 + by2) / 2 / H:.6f} {(bx2 - bx1) / W:.6f} {(by2 - by1) / H:.6f}")
                    info["loads"].append([c, float(bx1), float(by1), float(bx2), float(by2), float(lr.boxes.conf[k])])
            cv2.imwrite(str(BASE / "images" / f"{name}.jpg"), fr, [cv2.IMWRITE_JPEG_QUALITY, 92])
            (BASE / "labels" / f"{name}.txt").write_text("\n".join(rows) + ("\n" if rows else ""))
            meta[name] = info
            n += 1
        print(f"{video.stem}: {n} frame")
    (BASE / "autolabel_meta.json").write_text(json.dumps(meta))


if __name__ == "__main__":
    main()
