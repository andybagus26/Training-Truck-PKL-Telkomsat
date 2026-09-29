"""Menyimpulkan apa yang sedang dilakukan tiap truk, dari deretan sampel deteksi.

Tiga aktivitas ditangani:

* **loading** — truk berhenti dan ada excavator berdekatan.
* **dumping** — truk berhenti dan baknya terangkat (class `bed_raised` pada model v6).
* **idle**    — truk berhenti tapi tidak sedang dimuat maupun menumpah. Inilah waktu yang terbuang:
  mengantre, menunggu excavator, atau berhenti tanpa dilayani.

Pada satu titik waktu sebuah truk hanya boleh berada di satu keadaan. Urutan penilaiannya:
dumping lebih dulu, lalu loading, lalu idle; truk yang kotaknya bergerak dianggap `moving`.

Batas kemampuannya perlu disebut terus terang, karena ini menyangkut cara membaca angkanya:

* Kamera tidak bisa tahu mesin hidup atau mati. `idle` di sini berarti "berhenti dan tidak sedang
  dilayani" — truk parkir selesai giliran terlihat sama persis. Yang membedakan hanya lama berhentinya
  dan di zone mana, jadi ambangnya harus disetel mengikuti aturan lapangan.
* Id objek Frigate berlaku per kamera dan per kemunculan. Satu truk yang keluar-masuk frame akan
  dihitung sebagai objek baru, sehingga siklus penuh (muat -> angkut -> tumpah -> kembali) belum bisa
  dirangkai. Untuk itu truknya harus dikenali satuan, misalnya lewat nomor lambung — dataset awal
  sebenarnya punya class `tail_number`, jadi jalannya ada, tapi itu pekerjaan tersendiri.

Semua ambang bisa diubah lewat environment variable, karena nilainya bergantung sudut kamera dan
kebiasaan di lokasi.
"""
import bisect
import os
from collections import defaultdict

from .store import store

MOVE_TOLERANCE = float(os.getenv("MOVE_TOLERANCE", "0.03"))   # perpindahan titik tengah, relatif
STILL_WINDOW = float(os.getenv("STILL_WINDOW", "6"))          # detik, jendela penilaian "berhenti"
NEAR_GAP = float(os.getenv("NEAR_GAP", "0.12"))               # jarak maksimal truk-excavator, relatif
END_GRACE = float(os.getenv("END_GRACE", "15"))               # detik syarat boleh hilang sebelum ditutup

# Lama minimal sebelum sebuah keadaan diakui. Idle sengaja lebih panjang: berhenti sebentar untuk
# manuver atau memberi jalan bukan pemborosan, yang dicari adalah berhenti yang benar-benar menunggu.
MIN_DURATION = {
    "loading": float(os.getenv("MIN_DURATION", "8")),
    "dumping": float(os.getenv("MIN_DUMP", "5")),
    "idle": float(os.getenv("MIN_IDLE", "30")),
}
RULE = {
    "loading": "truk berhenti + excavator berdekatan",
    "dumping": "truk berhenti + bak terangkat",
    "idle": "truk berhenti, tidak dimuat dan tidak menumpah",
}
LOAD_LABELS = {"full_load", "empty_load"}
BED_LABEL = "bed_raised"


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
    """Titik tengah kotak nyaris tidak bergeser sepanjang STILL_WINDOW terakhir sampai now_ts.

    `track` harus urut waktu (store selalu mengembalikan ORDER BY ts). Jendela dicari dengan bisect,
    bukan menyisir seluruh track, karena fungsi ini dipanggil untuk tiap sampel: tanpa itu waktu
    hitung naik kuadrat untuk truk yang diam lama (3 truk x 3 jam: 12 detik, API ikut macet).
    """
    lo = bisect.bisect_left(track, now_ts - STILL_WINDOW, key=lambda s: s["ts"])
    hi = bisect.bisect_right(track, now_ts, key=lambda s: s["ts"])
    recent = [s for s in track[lo:hi] if s["x"] is not None]
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


def _bed_raised(truck_sample, others: list) -> bool:
    return any(o["label"] == BED_LABEL and o["x"] is not None and _inside(o, truck_sample)
               for o in others)


def _near_excavator(truck_sample, others: list) -> str | None:
    for o in others:
        if o["label"] == "excavator" and o["x"] is not None and _gap(truck_sample, o) <= NEAR_GAP:
            return o["object_id"]
    return None


def state_at(truck_sample, others: list, track: list) -> tuple[str, str | None]:
    """Keadaan truk pada satu titik waktu, dan id excavator bila sedang dimuat."""
    if truck_sample["x"] is None:
        return "unknown", None
    if not _is_still(track, truck_sample["ts"]):
        return "moving", None
    if _bed_raised(truck_sample, others):
        return "dumping", None
    near = _near_excavator(truck_sample, others)
    if near:
        return "loading", near
    return "idle", None


def _timeline(track: list, others_by_ts: dict) -> list[tuple[float, str, str | None]]:
    """(waktu, keadaan, pasangan) untuk tiap sampel truk."""
    out = []
    for s in track:
        others = others_by_ts.get(s["ts"], [])
        st, partner = state_at(s, others, track)
        out.append((s["ts"], st, partner))
    return out


def _last_run(timeline: list, want: str) -> tuple[float | None, float | None, str | None]:
    """Rentang terakhir saat keadaannya `want`.

    Jeda dihitung dari selisih waktu antar titik yang cocok, bukan dari ada/tidaknya sampel, karena
    objek bisa hilang sama sekali dari Frigate dan tidak menghasilkan sampel apa pun.
    """
    hits = [(ts, partner) for ts, st, partner in timeline if st == want]
    if not hits:
        return None, None, None
    end = hits[-1][0]
    start, partner = hits[-1]
    for i in range(len(hits) - 1, 0, -1):
        if hits[i][0] - hits[i - 1][0] > END_GRACE:
            break
        start, partner = hits[i - 1]
    return start, end, partner


def evaluate(now_ts: float, window: float = 600.0) -> dict:
    """Perbarui aktivitas semua truk berdasarkan sampel terakhir. Kembalikan ringkasan perubahan."""
    rows = store.samples_since(now_ts - window)
    by_object: dict[str, list] = defaultdict(list)
    per_camera_ts: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_object[r["object_id"]].append(r)
        per_camera_ts[r["camera"]][r["ts"]].append(r)

    changed = {"opened": 0, "closed": 0, "discarded": 0}
    for obj_id, track in by_object.items():
        if track[-1]["label"] != "truck":
            continue
        camera = track[-1]["camera"]
        timeline = _timeline(track, per_camera_ts[camera])
        last = track[-1]
        others_now = per_camera_ts[camera].get(last["ts"], [])

        for type_ in ("loading", "dumping", "idle"):
            start_ts, last_ts, partner = _last_run(timeline, type_)
            ongoing = store.ongoing_activity(type_, obj_id)
            if ongoing is None:
                if start_ts and last_ts and last_ts - start_ts >= MIN_DURATION[type_] \
                        and now_ts - last_ts < END_GRACE:
                    store.open_activity(type_, camera, obj_id, start_ts, partner,
                                        _load_state(last, others_now) if last["x"] is not None else None,
                                        {"rule": RULE[type_]})
                    changed["opened"] += 1
            else:
                if last["x"] is not None:
                    state = _load_state(last, others_now)
                    if state:
                        store.update_activity(ongoing["id"], load_after=state)
                reference = last_ts or ongoing["start_ts"]
                if now_ts - reference >= END_GRACE:
                    if reference - ongoing["start_ts"] < MIN_DURATION[type_]:
                        store.delete_activity(ongoing["id"])
                        changed["discarded"] += 1
                    else:
                        store.update_activity(ongoing["id"], end_ts=reference)
                        changed["closed"] += 1

    return {"objects": len(by_object), **changed}


def utilization(since_ts: float, camera: str | None = None) -> list[dict]:
    """Berapa lama tiap truk berada di tiap keadaan, dihitung ulang dari sampel.

    Sengaja dihitung dari sampel, bukan dari tabel aktivitas, supaya waktu yang terlalu pendek untuk
    diakui sebagai aktivitas pun tetap terhitung — jadi jumlah seluruh keadaan sama dengan lama truk
    itu terlihat.
    """
    rows = store.samples_since(since_ts, camera)
    by_object: dict[str, list] = defaultdict(list)
    per_camera_ts: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_object[r["object_id"]].append(r)
        per_camera_ts[r["camera"]][r["ts"]].append(r)

    out = []
    for obj_id, track in by_object.items():
        if track[-1]["label"] != "truck" or len(track) < 2:
            continue
        cam = track[-1]["camera"]
        seconds: dict[str, float] = defaultdict(float)
        loads: set[str] = set()
        for i, s in enumerate(track[:-1]):
            dt = min(track[i + 1]["ts"] - s["ts"], END_GRACE)   # jeda panjang tidak ikut dihitung
            st, partner = state_at(s, per_camera_ts[cam].get(s["ts"], []), track)
            seconds[st] += dt
            if partner:
                loads.add(partner)
        total = sum(seconds.values())
        out.append({
            "truck_id": obj_id,
            "camera": cam,
            "seen_seconds": round(total, 1),
            "seconds": {k: round(v, 1) for k, v in sorted(seconds.items())},
            "idle_share": round(seconds["idle"] / total, 3) if total else None,
            "excavators": sorted(loads),
        })
    return sorted(out, key=lambda r: r["seen_seconds"], reverse=True)


def operations(since_ts: float, camera: str | None = None) -> list[dict]:
    """Rekap per kamera: berapa truk terlihat, berapa kali dimuat/menumpah, dan berapa waktu terbuang.

    Inilah bentuk angka yang biasanya dicari pengawas lapangan. Yang belum bisa dijawab dari sini
    adalah siklus penuh per truk (muat -> angkut -> tumpah -> kembali), karena truknya belum dikenali
    satuan antar kamera.
    """
    per_truck = utilization(since_ts, camera)
    acts = store.activities(camera=camera, since_ts=since_ts, limit=1000)

    by_cam: dict[str, dict] = {}
    for t in per_truck:
        c = by_cam.setdefault(t["camera"], {
            "camera": t["camera"], "trucks": 0, "seen_seconds": 0.0,
            "seconds": defaultdict(float), "events": defaultdict(list), "excavators": set()})
        c["trucks"] += 1
        c["seen_seconds"] += t["seen_seconds"]
        for k, v in t["seconds"].items():
            c["seconds"][k] += v
        c["excavators"].update(t["excavators"])

    for a in acts:
        c = by_cam.get(a["camera"])
        if c is None or a["end_ts"] is None:
            continue
        c["events"][a["type"]].append(a["end_ts"] - a["start_ts"])

    out = []
    for c in by_cam.values():
        total = sum(c["seconds"].values())
        out.append({
            "camera": c["camera"],
            "trucks_seen": c["trucks"],
            "truck_seconds": round(total, 1),
            "seconds": {k: round(v, 1) for k, v in sorted(c["seconds"].items())},
            "idle_share": round(c["seconds"]["idle"] / total, 3) if total else None,
            "events": {k: {"count": len(v), "average_seconds": round(sum(v) / len(v), 1)}
                       for k, v in sorted(c["events"].items()) if v},
            "excavators_seen": len(c["excavators"]),
        })
    return sorted(out, key=lambda r: r["truck_seconds"], reverse=True)
