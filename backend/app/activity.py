"""Menyimpulkan aktivitas dari deretan deteksi.

Tahap 1 menangani satu aktivitas: **loading** (truk sedang dimuat).

Aturannya, dinilai pada tiap putaran sampel:

1. Truk **berhenti** — titik tengah kotaknya bergeser kurang dari MOVE_TOLERANCE selama
   STILL_WINDOW detik terakhir.
2. Ada **excavator berdekatan** dengan truk — jarak antar kotak kurang dari NEAR_GAP (relatif
   terhadap lebar frame); 0 berarti kotaknya bertumpuk.
3. Aktivitas **dimulai** bila kedua syarat itu bertahan selama MIN_DURATION detik. Putus-putus
   sesaat dijembatani, karena deteksi kadang hilang satu-dua frame.
4. Aktivitas **selesai** bila excavator menjauh, truk jalan lagi, atau truk hilang selama
   END_GRACE detik.
5. Status muatan sebelum dan sesudah dicatat bila terlihat, sebagai bukti pendukung.

Syarat "truk berhenti" hanya bisa dipakai karena sampelnya diambil dari MQTT. Kotak pada
`/api/events` adalah posisi saat snapshot terbaik objek diambil, bukan posisi sekarang, sehingga
semua objek tampak diam dan kotak antar objek tidak bisa dibandingkan. Lihat live.py.

Ambang dipilih dari pengukuran pada rekaman uji: truk yang benar-benar dimuat menghasilkan rentang
27-30 detik, sedangkan truk yang sekadar lewat dekat excavator hanya 0-2 detik setelah syarat diam
ikut dihitung. Angka ini berasal dari video demo, jadi perlu disetel ulang begitu ada rekaman dari
lokasi sebenarnya.

Status muatan truk diambil dari kotak `full_load`/`empty_load` yang titik tengahnya berada di dalam
kotak truk pada waktu yang sama.

Semua ambang bisa diubah lewat environment variable, karena nilainya bergantung pada sudut kamera.
"""
import os
from collections import defaultdict

from .store import store

MOVE_TOLERANCE = float(os.getenv("MOVE_TOLERANCE", "0.03"))   # perpindahan titik tengah, relatif
STILL_WINDOW = float(os.getenv("STILL_WINDOW", "6"))            # detik, jendela penilaian "diam"
NEAR_GAP = float(os.getenv("NEAR_GAP", "0.12"))                # jarak maksimal truk-excavator, relatif
MIN_DURATION = float(os.getenv("MIN_DURATION", "8"))           # detik, sebelum diakui sebagai loading
END_GRACE = float(os.getenv("END_GRACE", "15"))                # detik tanpa excavator sebelum dianggap selesai
LOAD_LABELS = {"full_load", "empty_load"}


def _center(r) -> tuple[float, float]:
    return r["x"] + r["w"] / 2, r["y"] + r["h"] / 2


def _inside(inner, outer) -> bool:
    """Titik tengah kotak `inner` berada di dalam kotak `outer`."""
    cx, cy = _center(inner)
    return outer["x"] <= cx <= outer["x"] + outer["w"] and outer["y"] <= cy <= outer["y"] + outer["h"]


def _gap(a, b) -> float:
    """Jarak terpendek antar dua kotak; 0 bila bersinggungan atau bertumpuk."""
    dx = max(a["x"] - (b["x"] + b["w"]), b["x"] - (a["x"] + a["w"]), 0)
    dy = max(a["y"] - (b["y"] + b["h"]), b["y"] - (a["y"] + a["h"]), 0)
    return (dx ** 2 + dy ** 2) ** 0.5


def _is_still(track: list, now_ts: float) -> bool:
    """Titik tengah kotak nyaris tidak bergeser sepanjang STILL_WINDOW terakhir sampai now_ts."""
    recent = [s for s in track
              if now_ts - STILL_WINDOW <= s["ts"] <= now_ts and s["x"] is not None]
    if len(recent) < 2:
        return False
    xs = [_center(s)[0] for s in recent]
    ys = [_center(s)[1] for s in recent]
    return (max(xs) - min(xs)) <= MOVE_TOLERANCE and (max(ys) - min(ys)) <= MOVE_TOLERANCE


def _load_state(truck_sample, others: list) -> str | None:
    """Status muatan truk pada satu titik waktu: 'full_load', 'empty_load', atau None."""
    best = None
    for o in others:
        if o["label"] in LOAD_LABELS and o["x"] is not None and _inside(o, truck_sample):
            if best is None or (o["score"] or 0) > (best["score"] or 0):
                best = o
    return best["label"] if best else None


def _condition_timeline(track: list, others_by_ts: dict) -> list[tuple[float, bool, str | None]]:
    """Untuk tiap sampel truk: apakah syarat loading terpenuhi, dan id excavator yang berdekatan."""
    out = []
    for s in track:
        if s["x"] is None:
            out.append((s["ts"], False, None))
            continue
        near = None
        for o in others_by_ts.get(s["ts"], []):
            if o["label"] == "excavator" and o["x"] is not None and _gap(s, o) <= NEAR_GAP:
                near = o["object_id"]
                break
        out.append((s["ts"], near is not None and _is_still(track, s["ts"]), near))
    return out


def _last_true_run(timeline: list) -> tuple[float | None, float | None, str | None]:
    """Rentang terakhir saat syarat terpenuhi.

    Jeda dihitung dari selisih waktu antar titik yang memenuhi syarat, bukan dari ada/tidaknya sampel,
    karena objek bisa hilang sama sekali dari Frigate (tidak menghasilkan sampel apa pun).
    """
    hits = [(ts, near) for ts, ok, near in timeline if ok]
    if not hits:
        return None, None, None
    end = hits[-1][0]
    start, partner = hits[-1]
    for i in range(len(hits) - 1, 0, -1):
        if hits[i][0] - hits[i - 1][0] > END_GRACE:
            break
        start, partner = hits[i - 1]
    return start, end, partner


def evaluate(now_ts: float, window: float = 300.0) -> dict:
    """Perbarui aktivitas loading berdasarkan sampel terakhir. Kembalikan ringkasan perubahan."""
    rows = store.samples_since(now_ts - window)
    by_object: dict[str, list] = defaultdict(list)
    per_camera_ts: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_object[r["object_id"]].append(r)
        per_camera_ts[r["camera"]][r["ts"]].append(r)

    opened = closed = discarded = 0
    for obj_id, track in by_object.items():
        if track[-1]["label"] != "truck":
            continue
        camera = track[-1]["camera"]
        timeline = _condition_timeline(track, per_camera_ts[camera])
        start_ts, last_true_ts, partner = _last_true_run(timeline)
        ongoing = store.ongoing_activity("loading", obj_id)

        if ongoing is None:
            # syarat harus terpenuhi terus-menerus selama MIN_DURATION
            if start_ts and last_true_ts and last_true_ts - start_ts >= MIN_DURATION \
                    and now_ts - last_true_ts < END_GRACE:
                state = _load_state(track[-1], [o for o in per_camera_ts[camera].get(track[-1]["ts"], [])
                                                if o["label"] in LOAD_LABELS])
                store.open_activity("loading", camera, obj_id, start_ts, partner, state,
                                    {"rule": "truk diam + excavator berdekatan"})
                opened += 1
        else:
            state = _load_state(track[-1], [o for o in per_camera_ts[camera].get(track[-1]["ts"], [])
                                            if o["label"] in LOAD_LABELS]) if track[-1]["x"] is not None else None
            if state:
                store.update_activity(ongoing["id"], load_after=state)
            # tutup bila syarat sudah tidak terpenuhi melewati masa tenggang
            reference = last_true_ts or ongoing["start_ts"]
            if now_ts - reference >= END_GRACE:
                duration = reference - ongoing["start_ts"]
                if duration < MIN_DURATION:
                    store.delete_activity(ongoing["id"])
                    discarded += 1
                else:
                    store.update_activity(ongoing["id"], end_ts=reference)
                    closed += 1

    return {"objects": len(by_object), "opened": opened, "closed": closed, "discarded": discarded}
