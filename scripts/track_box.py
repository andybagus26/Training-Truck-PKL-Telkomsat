"""Melacak satu kotak anotasi dari frame acuan ke frame-frame sekitarnya.

Dipakai untuk melabeli class `bed_raised` pada rekaman dumping. Melabeli ribuan frame satu per satu
tidak masuk akal, sedangkan interpolasi sederhana meleset karena kameranya ikut bergoyang. Jadi satu
kotak digambar manual pada frame acuan, lalu dilacak maju dan mundur.

Cara kerjanya pencocokan template multi-skala: potongan gambar di dalam kotak dicari lagi di frame
berikutnya dalam radius terbatas, dengan beberapa skala supaya kotak ikut membesar saat bak terangkat
makin tinggi. Template diperbarui perlahan agar mengikuti perubahan bentuk tanpa gampang melenceng.

Hasilnya tetap harus ditinjau (lihat review_boxes.py) — pelacak ini alat bantu, bukan pengganti mata.
"""
import argparse
import json
import pathlib

import cv2
import numpy as np

FRAMES = pathlib.Path(__file__).resolve().parents[1] / "datasets/dump-raw/frames"
SCALES = (0.94, 0.97, 1.0, 1.03, 1.06)
BLEND = 0.75          # bobot template lama saat diperbarui
MIN_SCORE = 0.45      # di bawah ini pelacakan dianggap gagal dan dihentikan


def _load(vid: str, n: int):
    f = FRAMES / f"{vid}_{n:04d}.jpg"
    if not f.exists():
        return None
    return cv2.cvtColor(cv2.imread(str(f)), cv2.COLOR_BGR2GRAY)


def _match(img, tpl, box, margin=0.6):
    """Cari tpl di sekitar box. box = (x1,y1,x2,y2) pixel. Kembalikan box baru + skor."""
    H, W = img.shape
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    mx, my = int(bw * margin) + 12, int(bh * margin) + 12
    sx1, sy1 = max(0, x1 - mx), max(0, y1 - my)
    sx2, sy2 = min(W, x2 + mx), min(H, y2 + my)
    search = img[sy1:sy2, sx1:sx2]
    best = None
    for s in SCALES:
        tw, th = int(tpl.shape[1] * s), int(tpl.shape[0] * s)
        if tw < 12 or th < 12 or tw >= search.shape[1] or th >= search.shape[0]:
            continue
        t = cv2.resize(tpl, (tw, th))
        res = cv2.matchTemplate(search, t, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(res)
        if best is None or score > best[0]:
            best = (score, (sx1 + loc[0], sy1 + loc[1], sx1 + loc[0] + tw, sy1 + loc[1] + th))
    return (None, 0.0) if best is None else (best[1], best[0])


def track(vid: str, ref: int, box_n: tuple, start: int, end: int) -> dict:
    """box_n: (x1,y1,x2,y2) relatif 0-1 pada frame acuan. Kembalikan {frame: box_relatif}."""
    img = _load(vid, ref)
    if img is None:
        raise SystemExit(f"frame acuan {vid}_{ref:04d} tidak ada")
    H, W = img.shape
    box = tuple(int(v * (W if i % 2 == 0 else H)) for i, v in enumerate(box_n))
    out = {ref: box}
    for direction in (1, -1):
        cur_box, tpl = box, img[box[1]:box[3], box[0]:box[2]].copy()
        n = ref + direction
        while start <= n <= end:
            nxt = _load(vid, n)
            if nxt is None:
                break
            new_box, score = _match(nxt, tpl, cur_box)
            if new_box is None or score < MIN_SCORE:
                break
            out[n] = cur_box = new_box
            patch = nxt[new_box[1]:new_box[3], new_box[0]:new_box[2]]
            if patch.size and patch.shape[0] > 8 and patch.shape[1] > 8:
                tpl = cv2.addWeighted(tpl, BLEND, cv2.resize(patch, (tpl.shape[1], tpl.shape[0])), 1 - BLEND, 0)
            n += direction
    return {n: (b[0]/W, b[1]/H, b[2]/W, b[3]/H) for n, b in sorted(out.items())}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("vid")
    p.add_argument("ref", type=int)
    p.add_argument("box", help="x1,y1,x2,y2 relatif 0-1")
    p.add_argument("start", type=int)
    p.add_argument("end", type=int)
    p.add_argument("--out", default="datasets/dump-raw/boxes.json")
    a = p.parse_args()
    boxes = track(a.vid, a.ref, tuple(float(v) for v in a.box.split(",")), a.start, a.end)
    path = pathlib.Path(a.out)
    data = json.loads(path.read_text()) if path.exists() else {}
    data.setdefault(a.vid, {}).update({str(k): [round(v, 5) for v in b] for k, b in boxes.items()})
    path.write_text(json.dumps(data, indent=1))
    print(f"{a.vid}: {len(boxes)} frame terlacak (f{min(boxes)}-f{max(boxes)}) -> {path}")
