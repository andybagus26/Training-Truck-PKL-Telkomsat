"""Training YOLOv9 untuk deteksi truk tambang (truck / full_load / empty_load).

Contoh:
    .venv/bin/python train.py --epochs 3 --name smoke_test   # percobaan singkat
    .venv/bin/python train.py                                # training penuh
"""
import argparse
from pathlib import Path

import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
DATA_YAML = ROOT / "datasets" / "mining-truck-clean" / "data.yaml"
BASE_WEIGHTS = ROOT / "weights" / "yolov9t.pt"
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

TRAIN_CFG = dict(
    data=str(DATA_YAML),
    imgsz=320,
    epochs=150,
    patience=40,        # early stopping kalau mAP50-95 val tidak naik 40 epoch
    batch=16,
    optimizer="AdamW",
    lr0=0.001,
    lrf=0.01,           # LR akhir = lr0 * lrf = 1e-5
    cos_lr=True,
    warmup_epochs=3,
    weight_decay=0.0005,
    # Augmentasi: default Ultralytics + penyesuaian untuk dataset kecil
    mosaic=1.0,
    close_mosaic=15,    # matikan mosaic 15 epoch terakhir supaya fine-tune di distribusi gambar asli
    mixup=0.1,
    degrees=5.0,
    fliplr=0.5,
    flipud=0.0,
    hsv_v=0.5,          # variasi brightness lebih besar; dataset berisi gambar siang & malam
    cache="ram",        # 430 gambar kecil, muat di RAM -> epoch lebih cepat
    workers=4,
    device=DEVICE,
    seed=42,
    deterministic=False,  # MPS tidak punya implementasi deterministik untuk beberapa op
    project=str(ROOT / "runs"),
    name="yolov9t_truck_320",
    exist_ok=False,
    plots=True,
)


def train(weights=BASE_WEIGHTS, **overrides):
    cfg = {**TRAIN_CFG, **overrides}
    print(f"Device: {cfg['device']} | base: {weights} | data: {cfg['data']}")
    model = YOLO(str(weights))
    model.train(**cfg)
    return model


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=TRAIN_CFG["epochs"])
    ap.add_argument("--name", default=TRAIN_CFG["name"])
    ap.add_argument("--device", default=TRAIN_CFG["device"])
    ap.add_argument("--data", default=TRAIN_CFG["data"])
    ap.add_argument("--batch", type=int, default=TRAIN_CFG["batch"])
    ap.add_argument("--patience", type=int, default=TRAIN_CFG["patience"])
    ap.add_argument("--scale", type=float, default=0.5, help="augmentasi zoom acak ±scale (default ultralytics 0.5)")
    ap.add_argument("--weights", default=str(BASE_WEIGHTS), help="bobot awal (mis. best.pt model sebelumnya untuk fine-tune)")
    ap.add_argument("--lr0", type=float, default=TRAIN_CFG["lr0"])
    ap.add_argument("--warmup-epochs", type=float, default=TRAIN_CFG["warmup_epochs"])
    args = ap.parse_args()
    train(weights=args.weights, epochs=args.epochs, name=args.name, device=args.device, data=args.data,
          batch=args.batch, patience=args.patience, scale=args.scale, lr0=args.lr0,
          warmup_epochs=args.warmup_epochs)
