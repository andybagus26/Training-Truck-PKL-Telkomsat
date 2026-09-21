"""Augmentasi malam sintetis: buat salinan gelap dari gambar training (label tidak berubah).

night_aug.py <src_images_dir> <src_labels_dir> <dst_images_dir> <dst_labels_dir> [--n N] [--seed S] [--preview out.jpg]
"""
import argparse
import random
import shutil
from pathlib import Path

import cv2
import numpy as np


def to_night(img, rng):
    f = img.astype(np.float32) / 255.0
    # desaturasi (mata/kamera kurang peka warna saat gelap)
    gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)[..., None]
    f = f * rng.uniform(0.35, 0.7) + gray * (1 - rng.uniform(0.35, 0.7))
    # gelap non-linear: bayangan tenggelam, bagian terang tetap sedikit terlihat
    f = np.power(np.clip(f, 0, 1), rng.uniform(2.2, 3.2)) * rng.uniform(0.18, 0.4)
    # warna cahaya: sodium (oranye), LED (biru-putih), atau netral
    tint = rng.choice([np.array([0.75, 0.9, 1.15]), np.array([1.15, 1.0, 0.85]), np.array([1.0, 1.0, 1.0])])
    f = f * tint
    H, W = f.shape[:2]
    # 0-3 sumber cahaya (lampu sorot / lampu kendaraan) dengan pendar halus
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for _ in range(rng.randint(0, 3)):
        cx, cy = rng.uniform(0, W), rng.uniform(0, H * 0.7)
        r = rng.uniform(0.03, 0.12) * max(H, W)
        glow = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))[..., None]
        f = f + glow * rng.uniform(0.08, 0.3)
    # noise sensor + sedikit blur (ISO tinggi, eksposur lama)
    f = f + np.random.default_rng(rng.randint(0, 1 << 30)).normal(0, rng.uniform(0.008, 0.025), f.shape)
    out = np.clip(f * 255, 0, 255).astype(np.uint8)
    if rng.random() < 0.5:
        out = cv2.GaussianBlur(out, (3, 3), 0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src_images")
    ap.add_argument("src_labels")
    ap.add_argument("dst_images")
    ap.add_argument("dst_labels")
    ap.add_argument("--n", type=int, default=0, help="jumlah gambar (0 = semua)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--only-with-labels", action="store_true", help="lewati gambar tanpa objek")
    ap.add_argument("--preview", default=None)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    src_i, src_l = Path(args.src_images), Path(args.src_labels)
    dst_i, dst_l = Path(args.dst_images), Path(args.dst_labels)
    dst_i.mkdir(parents=True, exist_ok=True)
    dst_l.mkdir(parents=True, exist_ok=True)
    imgs = sorted(p for p in src_i.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if args.only_with_labels:
        imgs = [p for p in imgs if (src_l / (p.stem + ".txt")).exists() and (src_l / (p.stem + ".txt")).read_text().strip()]
    if args.n:
        imgs = rng.sample(imgs, min(args.n, len(imgs)))
    previews = []
    for p in imgs:
        out = to_night(cv2.imread(str(p)), rng)
        name = f"{p.stem}_night"
        cv2.imwrite(str(dst_i / f"{name}.jpg"), out, [cv2.IMWRITE_JPEG_QUALITY, 90])
        shutil.copy2(src_l / (p.stem + ".txt"), dst_l / f"{name}.txt")
        if args.preview and len(previews) < 8:
            previews.append(np.hstack([cv2.resize(cv2.imread(str(p)), (320, 200)), cv2.resize(out, (320, 200))]))
    if args.preview and previews:
        while len(previews) % 2:
            previews.append(np.zeros_like(previews[0]))
        cv2.imwrite(args.preview, np.vstack([np.hstack(previews[i:i + 2]) for i in range(0, len(previews), 2)]))
    print(f"{len(imgs)} gambar malam dibuat -> {dst_i}")


if __name__ == "__main__":
    main()
