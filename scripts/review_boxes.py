"""Menggambar kotak hasil pelacakan ke lembar tinjauan, supaya kesalahan kelihatan sebelum dipakai."""
import argparse
import json
import pathlib

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRAMES = ROOT / "datasets/dump-raw/frames"


def sheet(vid: str, boxes: dict, out: pathlib.Path, every: int = 6, cols: int = 4, cw: int = 400):
    keys = sorted(boxes, key=int)[::every]
    ch = int(cw * 9 / 16)
    rows = (len(keys) + cols - 1) // cols
    g = Image.new("RGB", (cw * cols, ch * rows), "black")
    d = ImageDraw.Draw(g)
    for i, k in enumerate(keys):
        im = Image.open(FRAMES / f"{vid}_{int(k):04d}.jpg").convert("RGB").resize((cw, ch))
        dd = ImageDraw.Draw(im)
        x1, y1, x2, y2 = boxes[k]
        dd.rectangle([x1 * cw, y1 * ch, x2 * cw, y2 * ch], outline=(0, 255, 0), width=3)
        ox, oy = (i % cols) * cw, (i // cols) * ch
        g.paste(im, (ox, oy))
        d.text((ox + 6, oy + 4), f"f{k}", fill="yellow")
    g.save(out, quality=88)
    return len(keys)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("vid")
    p.add_argument("--boxes", default="datasets/dump-raw/boxes.json")
    p.add_argument("--every", type=int, default=6)
    p.add_argument("--out", default=None)
    a = p.parse_args()
    data = json.loads(pathlib.Path(a.boxes).read_text())[a.vid]
    default = ROOT / "datasets/dump-raw/review"
    default.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out) if a.out else default / f"review_{a.vid}.jpg"
    n = sheet(a.vid, data, out, a.every)
    print(f"{n} frame di {out}")
