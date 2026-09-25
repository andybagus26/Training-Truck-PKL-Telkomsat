"""API perantara untuk data deteksi Frigate.

Alur: Frigate menyimpan hasil deteksi -> API ini mengambil dan merapikannya -> dashboard/sistem lain
cukup memanggil API ini.

Menjalankan:
    .venv/bin/uvicorn backend.app.main:app --reload --port 8000
Dokumentasi interaktif: http://localhost:8000/docs
"""
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path as FsPath

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .frigate import FRIGATE_URL, client
from .schemas import (LABELS, Box, CameraInfo, CameraStats, CameraSummary, Detection, DetectorStats,
                      Health, LabelCount, Stats, Summary)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await client.close()


app = FastAPI(
    title="API Deteksi Truk Tambang",
    description=(
        "Perantara untuk data deteksi Frigate NVR. Model yang dipakai: YOLOv9-t 320x320 dengan class "
        "`truck`, `full_load`, `empty_load`, `excavator`.\n\n"
        "Catatan: pada model versi pertama class truk bernama `mining_truck`; sejak itu digabung "
        "menjadi `truck`, dan `excavator` ditambahkan pada model v5."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"],
)


# Penarikan per halaman untuk filter min_score di /detections (maks 20 x 500 = 10.000 event).
MIN_SCORE_PAGE_SIZE = 500
MIN_SCORE_MAX_PAGES = 20


def _to_dt(ts: float | None) -> datetime | None:
    return datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None


def _as_detection(ev: dict) -> Detection:
    """Ubah satu event Frigate menjadi bentuk yang dipakai API ini."""
    data = ev.get("data") or {}
    start, end = ev.get("start_time"), ev.get("end_time")
    box = data.get("box") or []
    return Detection(
        id=ev["id"],
        camera=ev["camera"],
        label=ev["label"],
        score=round(data.get("top_score") or data.get("score") or 0, 4) or None,
        start_time=_to_dt(start),
        end_time=_to_dt(end),
        duration_seconds=round(end - start, 1) if start and end else None,
        ongoing=end is None,
        zones=ev.get("zones") or [],
        box=Box(x=box[0], y=box[1], w=box[2], h=box[3]) if len(box) == 4 else None,
        has_snapshot=bool(ev.get("has_snapshot")),
        has_clip=bool(ev.get("has_clip")),
        snapshot_url=f"/detections/{ev['id']}/snapshot" if ev.get("has_snapshot") else None,
    )


@app.get("/health", response_model=Health, tags=["status"], summary="Status API dan koneksi ke Frigate")
async def health() -> Health:
    up, version = await client.is_up()
    return Health(
        status="ok" if up else "degraded",
        frigate_url=FRIGATE_URL,
        frigate_reachable=up,
        frigate_version=version,
    )


@app.get("/labels", response_model=list[str], tags=["status"], summary="Daftar class yang dikenali model")
async def labels() -> list[str]:
    return LABELS


@app.get("/cameras", response_model=list[CameraInfo], tags=["kamera"], summary="Daftar kamera beserta zone-nya")
async def cameras() -> list[CameraInfo]:
    cfg = await client.get_json("/api/config")
    out = []
    for name, cam in (cfg.get("cameras") or {}).items():
        detect = cam.get("detect") or {}
        w, h = detect.get("width"), detect.get("height")
        out.append(CameraInfo(
            name=name,
            enabled=bool(cam.get("enabled", True)),
            detect_fps=detect.get("fps"),
            resolution=f"{w}x{h}" if w and h else None,
            zones=list((cam.get("zones") or {}).keys()),
            tracked_labels=list((cam.get("objects") or {}).get("track") or []),
        ))
    return out


@app.get("/detections", response_model=list[Detection], tags=["deteksi"],
         summary="Daftar deteksi, bisa disaring")
async def detections(
    camera: str | None = Query(None, description="Nama kamera, mis. site_cctv_test"),
    label: str | None = Query(None, description=f"Salah satu dari: {', '.join(LABELS)}"),
    zone: str | None = Query(None, description="Hanya deteksi yang masuk zone ini"),
    since_minutes: int | None = Query(None, ge=1, description="Ambil deteksi sejak N menit terakhir"),
    after: datetime | None = Query(None, description="Batas waktu mulai (ISO 8601)"),
    before: datetime | None = Query(None, description="Batas waktu akhir (ISO 8601)"),
    min_score: float | None = Query(None, ge=0, le=1, description="Skor minimum"),
    ongoing_only: bool = Query(False, description="Hanya objek yang masih terlihat"),
    limit: int = Query(100, ge=1, le=500),
) -> list[Detection]:
    if label and label not in LABELS:
        raise HTTPException(422, f"Label '{label}' tidak dikenali. Pilihan: {', '.join(LABELS)}")

    params: dict = {}
    if camera:
        params["camera"] = camera
    if label:
        params["label"] = label
    if zone:
        params["zone"] = zone
    if since_minutes:
        params["after"] = (datetime.now(timezone.utc) - timedelta(minutes=since_minutes)).timestamp()
    if after:
        params["after"] = after.timestamp()
    if before:
        params["before"] = before.timestamp()
    if ongoing_only:
        params["in_progress"] = 1

    if min_score is None:
        events = await client.get_json("/api/events", {**params, "limit": limit})
        return [_as_detection(e) for e in events]

    # min_score disaring di sini, bukan diteruskan ke Frigate: min_score milik Frigate memakai skor
    # terakhir, sedangkan API ini menampilkan skor tertinggi (top_score). Agar hasil tidak berkurang
    # karena dipotong limit lebih dulu, event diambil per halaman (terbaru dulu) sampai cukup.
    items: list[Detection] = []
    page = dict(params)
    for _ in range(MIN_SCORE_MAX_PAGES):
        events = await client.get_json("/api/events", {**page, "limit": MIN_SCORE_PAGE_SIZE})
        items += [d for d in map(_as_detection, events) if (d.score or 0) >= min_score]
        if len(items) >= limit or len(events) < MIN_SCORE_PAGE_SIZE:
            break
        page["before"] = events[-1]["start_time"]
    return items[:limit]


@app.get("/detections/{detection_id}", response_model=Detection, tags=["deteksi"],
         summary="Detail satu deteksi")
async def detection(detection_id: str = Path(description="Id deteksi dari Frigate")) -> Detection:
    return _as_detection(await client.get_json(f"/api/events/{detection_id}"))


@app.get("/detections/{detection_id}/snapshot", tags=["deteksi"], response_class=Response,
         summary="Gambar deteksi (JPEG)",
         responses={200: {"content": {"image/jpeg": {}}, "description": "Gambar saat objek terdeteksi"}})
async def snapshot(
    detection_id: str,
    bbox: bool = Query(True, description="Gambar kotak deteksi di atas gambar"),
) -> Response:
    content, media_type = await client.get_bytes(
        f"/api/events/{detection_id}/snapshot.jpg", {"bbox": int(bbox)}
    )
    return Response(content=content, media_type=media_type)


@app.get("/cameras/{camera}/latest", tags=["kamera"], response_class=Response,
         summary="Frame terbaru dari sebuah kamera (JPEG)",
         responses={200: {"content": {"image/jpeg": {}}, "description": "Frame terbaru"}})
async def latest_frame(
    camera: str,
    bbox: bool = Query(True, description="Gambar kotak deteksi"),
    height: int = Query(480, ge=120, le=2160, description="Tinggi gambar dalam piksel"),
) -> Response:
    content, media_type = await client.get_bytes(
        f"/api/{camera}/latest.jpg", {"bbox": int(bbox), "height": height}
    )
    return Response(content=content, media_type=media_type)


@app.get("/summary", response_model=Summary, tags=["deteksi"],
         summary="Rekap jumlah deteksi per label dan per kamera")
async def summary(
    since_minutes: int = Query(60, ge=1, le=10080, description="Rentang waktu ke belakang, dalam menit"),
    camera: str | None = Query(None),
    limit: int = Query(500, ge=1, le=2000, description="Batas jumlah event yang ditarik dari Frigate"),
) -> Summary:
    until = datetime.now(timezone.utc)
    since = until - timedelta(minutes=since_minutes)
    params: dict = {"after": since.timestamp(), "limit": limit}
    if camera:
        params["camera"] = camera
    items = [_as_detection(e) for e in await client.get_json("/api/events", params)]

    def counts(dets: list[Detection]) -> list[LabelCount]:
        by_label: dict[str, list[Detection]] = defaultdict(list)
        for d in dets:
            by_label[d.label].append(d)
        out = []
        for lab, group in by_label.items():
            scores = [d.score for d in group if d.score is not None]
            out.append(LabelCount(
                label=lab,
                count=len(group),
                average_score=round(sum(scores) / len(scores), 4) if scores else None,
                last_seen=max(d.start_time for d in group),
            ))
        return sorted(out, key=lambda c: -c.count)

    by_camera: dict[str, list[Detection]] = defaultdict(list)
    for d in items:
        by_camera[d.camera].append(d)

    return Summary(
        since=since, until=until, total=len(items), per_label=counts(items),
        per_camera=sorted(
            (CameraSummary(camera=cam, total=len(dets), per_label=counts(dets)) for cam, dets in by_camera.items()),
            key=lambda c: -c.total,
        ),
    )


@app.get("/stats", response_model=Stats, tags=["status"], summary="Performa detektor dan kamera")
async def stats() -> Stats:
    s = await client.get_json("/api/stats")
    service = s.get("service") or {}
    return Stats(
        detectors=[
            DetectorStats(name=n, inference_speed_ms=d.get("inference_speed"), detection_start=d.get("detection_start"))
            for n, d in (s.get("detectors") or {}).items()
        ],
        cameras=[
            CameraStats(camera=n, camera_fps=c.get("camera_fps"), process_fps=c.get("process_fps"),
                        detection_fps=c.get("detection_fps"), skipped_fps=c.get("skipped_fps"))
            for n, c in (s.get("cameras") or {}).items()
        ],
        frigate_version=service.get("version"),
        uptime_seconds=service.get("uptime"),
    )


# Dashboard visual (folder Dashboard/ di root repo) disajikan di /dashboard/.
# Dilewati bila foldernya tidak ada, jadi API tetap jalan tanpa dashboard.
DASHBOARD_DIR = FsPath(__file__).resolve().parents[2] / "Dashboard"
if DASHBOARD_DIR.is_dir():
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")
