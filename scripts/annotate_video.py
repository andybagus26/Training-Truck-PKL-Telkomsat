"""Jalankan model di setiap frame video -> video beranotasi + ringkasan per detik.

Contoh: annotate_video.py <video> <out.mp4> [weights] [--seen-from DETIK]
"""
import argparse
import subprocess
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
COLORS = {0: (0, 0, 255), 1: (0, 200, 0), 2: (0, 220, 255)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--weights", default=str(ROOT / "runs/yolov9t_truck_320_v3/weights/best.pt"))
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--seen-from", type=float, default=None, help="detik mulai bagian yang ikut dipakai training")
    args = ap.parse_args()

    m = YOLO(args.weights)
    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp = Path(args.out).with_suffix(".tmp.mp4")
    wr = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    per_sec, i = {}, 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        t = i / fps
        r = m.predict(fr, imgsz=320, conf=args.conf, device=DEVICE, verbose=False)[0]
        s = per_sec.setdefault(int(t), {"n": 0, "truck": 0, "full": 0, "empty": 0, "tscore": []})
        s["n"] += 1
        cls = r.boxes.cls.cpu().numpy().astype(int)
        conf = r.boxes.conf.cpu().numpy()
        s["truck"] += int((cls == 0).any())
        s["full"] += int((cls == 1).any())
        s["empty"] += int((cls == 2).any())
        if (cls == 0).any():
            s["tscore"].append(float(conf[cls == 0].max()))
        for (x1, y1, x2, y2), c, sc in zip(r.boxes.xyxy.cpu().numpy().astype(int), cls, conf):
            cv2.rectangle(fr, (x1, y1), (x2, y2), COLORS[c], 3)
            label = f"{m.names[c]} {sc:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(fr, (x1, y1 - th - 8), (x1 + tw + 6, y1), COLORS[c], -1)
            cv2.putText(fr, label, (x1 + 3, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        seen = args.seen_from is not None and t >= args.seen_from
        tag = f"{t:5.1f}s | model v3 | " + ("bagian ini ikut training" if seen else "TIDAK dipakai training")
        cv2.rectangle(fr, (0, H - 34), (W, H), (0, 0, 0), -1)
        cv2.putText(fr, tag, (10, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255) if not seen else (200, 200, 200), 2)
        wr.write(fr)
        i += 1
    wr.release()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out], check=True)
    tmp.unlink()

    print(f"{'detik':>5} {'truck':>6} {'full':>5} {'empty':>6} {'skor truck':>10}")
    for sec in sorted(per_sec):
        s = per_sec[sec]
        sc = f"{np.median(s['tscore']):.2f}" if s["tscore"] else "-"
        print(f"{sec:>5} {s['truck']/s['n']*100:>5.0f}% {s['full']/s['n']*100:>4.0f}% {s['empty']/s['n']*100:>5.0f}% {sc:>10}")
    tot = {k: sum(s[k] for s in per_sec.values()) for k in ("n", "truck", "full", "empty")}
    print(f"TOTAL {tot['n']} frame | truck {tot['truck']/tot['n']*100:.0f}% | full_load {tot['full']/tot['n']*100:.0f}% | empty_load {tot['empty']/tot['n']*100:.0f}%")


if __name__ == "__main__":
    main()
