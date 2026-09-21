"""Bandingkan model v1 vs v2: test set asli, test set rf100, dan video di luar domain (tidak dipakai training)."""
from pathlib import Path

import cv2
import numpy as np
import torch
import yaml
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    # "v1": ROOT / "runs/yolov9t_truck_320/weights/best.pt",
    # "v2": ROOT / "runs/yolov9t_truck_320_v2/weights/best.pt",
    "v3": ROOT / "runs/yolov9t_truck_320_v3/weights/best.pt",
    "v4": ROOT / "runs/yolov9t_truck_320_v4/weights/best.pt",
}
MODELS = {k: v for k, v in MODELS.items() if v.exists()}
V2 = ROOT / "datasets/mining-truck-v2"
OUT = ROOT / "runs/eval_v1_v2"
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
NAMES = ["truck", "full_load", "empty_load"]
VIDEOS = {
    "cat775": Path.home() / "frigate/media/cat775_crusher_demo.mp4",
    "perlini": Path.home() / "frigate/media/candidates/pexels_20712739.mp4",
    "komatsu": Path.home() / "frigate/media/truck_raw.mp4",
    "lewat": Path.home() / "frigate/media/truck_lewat.mp4",
    "malam": Path.home() / "frigate/media/truck_malam.mp4",
}


def split_yaml(name, pattern):
    """data.yaml yang test-nya hanya berisi gambar test v2 yang cocok dengan pattern."""
    imgs = sorted(p for p in (V2 / "test/images").iterdir() if pattern(p.name))
    lst = OUT / f"{name}.txt"
    lst.write_text("\n".join(str(p) for p in imgs) + "\n")
    y = OUT / f"{name}.yaml"
    y.write_text(yaml.safe_dump({"path": str(V2), "train": str(lst), "val": str(lst), "test": str(lst),
                                 "nc": 3, "names": NAMES}, sort_keys=False))
    return y, len(imgs)


def night_yaml():
    """Test set asli versi malam sintetis (seed tetap) -> sama untuk semua model."""
    import subprocess, sys
    d = OUT / "test_malam"
    if not (d / "images").exists():
        subprocess.run([sys.executable, str(ROOT / "night_aug.py"), str(ROOT / "datasets/mining-truck-clean/test/images"),
                        str(ROOT / "datasets/mining-truck-clean/test/labels"), str(d / "images"), str(d / "labels"),
                        "--seed", "123"], check=True)
    y = OUT / "test_malam.yaml"
    y.write_text(yaml.safe_dump({"path": str(d), "train": "images", "val": "images", "test": "images",
                                 "nc": 3, "names": NAMES}, sort_keys=False))
    return y, len(list((d / "images").iterdir()))


def video_frames(path, n=24):
    cap = cv2.VideoCapture(str(path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    for i in np.linspace(0, total - 1, n).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, fr = cap.read()
        if ok:
            frames.append(fr)
    return frames


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sets = {"asli": split_yaml("test_asli", lambda n: not n.startswith("rf100_")),
            "rf100": split_yaml("test_rf100", lambda n: n.startswith("rf100_")),
            "malam": night_yaml()}
    models = {k: YOLO(str(v)) for k, v in MODELS.items()}

    print("=== mAP per test set (imgsz 320) ===")
    print(f"{'set':<7}{'model':<5}{'class':<12}{'P':>7}{'R':>7}{'mAP50':>8}{'mAP50-95':>10}")
    for sname, (y, n) in sets.items():
        for mname, m in models.items():
            r = m.val(data=str(y), split="test", imgsz=320, batch=16, device=DEVICE, verbose=False, plots=False,
                      project=str(OUT), name=f"{sname}_{mname}", exist_ok=True)
            print(f"{sname:<7}{mname:<5}{'all':<12}{r.box.mp:>7.3f}{r.box.mr:>7.3f}{r.box.map50:>8.3f}{r.box.map:>10.3f}  (n={n})")
            for i, c in enumerate(r.box.ap_class_index):
                p, rc, a50, a = r.box.class_result(i)
                print(f"{'':<12}{NAMES[c]:<12}{p:>7.3f}{rc:>7.3f}{a50:>8.3f}{a:>10.3f}")

    print("\n=== Video luar domain: jumlah box per frame (conf 0.4) ===")
    print("box_raksasa = box truck > 60% frame (false positive khas v1)")
    for vname, vpath in VIDEOS.items():
        if not vpath.exists():
            print(f"{vname}: file tidak ada, dilewati")
            continue
        frames = video_frames(vpath)
        rows = []
        for mname, m in models.items():
            giant, trucks, loads, f_truck, f_full, tiles = 0, 0, 0, 0, 0, []
            for fr in frames:
                r = m.predict(fr, imgsz=320, conf=0.4, device=DEVICE, verbose=False)[0]
                b = r.boxes
                area = ((b.xywhn[:, 2] * b.xywhn[:, 3]).cpu().numpy()) if len(b) else np.array([])
                cls = b.cls.cpu().numpy().astype(int) if len(b) else np.array([], int)
                ok_truck = (cls == 0) & (area <= 0.6)
                giant += int(((cls == 0) & (area > 0.6)).sum())
                trucks += int((cls == 0).sum())
                loads += int((cls > 0).sum())
                f_truck += int(ok_truck.any())
                f_full += int((cls == 1).any())
                t = cv2.resize(r.plot(line_width=2), (320, 180))
                tiles.append(t)
            n = len(frames)
            print(f"{vname:<8}{mname}: {n} frame | frame dgn truck {f_truck}/{n} | frame dgn full_load {f_full}/{n} | "
                  f"box truck {trucks} (raksasa {giant}) | box load {loads}")
            strip = np.hstack(tiles[::3])
            cv2.putText(strip, f"{vname} {mname}", (5, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            rows.append(strip)
        cv2.imwrite(str(OUT / f"video_{vname}.jpg"), np.vstack(rows))
    print(f"\nGambar perbandingan: {OUT}/video_*.jpg")


if __name__ == "__main__":
    main()
