"""Pengambil sampel berkala: memotret keadaan objek tiap beberapa detik.

Sumber utamanya MQTT (lihat live.py), karena hanya di situ posisi objek benar-benar terkini.
Bila broker tidak tersedia, backend tetap jalan dengan membaca `/api/events` — presensi objek tetap
terpantau, hanya saja kotaknya tidak bisa dipercaya untuk menilai kedekatan antar objek.

Dari sampel inilah aktivitas disimpulkan (lihat activity.py).
"""
import asyncio
import json
import logging
import os
import time

from .activity import evaluate
from .frigate import client
from .live import live
from .store import store

logger = logging.getLogger("poller")

POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1"))       # detik antar pengambilan sampel
# Sampel mentah hanya dipakai untuk jendela penilaian beberapa menit terakhir; sisanya untuk
# penelusuran bila ada hasil yang janggal. Aktivitas yang sudah tersimpul disimpan terpisah dan
# tidak ikut terhapus. Pada 5 kamera, sampel bertambah sekitar 11 MB/jam.
RETENTION_HOURS = float(os.getenv("RETENTION_HOURS", "6"))   # sampel lama dibuang setelah ini
POLL_LIMIT = int(os.getenv("POLL_LIMIT", "200"))
# Broker tersambung belum berarti Frigate mengirim data (mqtt.enabled lupa dinyalakan, host atau
# topic_prefix berbeda). Frigate mengabari objek diam kira-kira sekali per menit, jadi baru dianggap
# diam bila lebih lama dari ini sementara Frigate sedang melacak objek.
MQTT_SILENT_AFTER = float(os.getenv("MQTT_SILENT_AFTER", "180"))
FLOW_CHECK_EVERY = 30                                         # detik antar pengecekan ke Frigate

state: dict = {"running": False, "last_poll": None, "last_error": None,
               "polls": 0, "samples": 0, "source": "belum mulai",
               "mqtt_receiving": None, "warning": None, "last_flow_check": 0.0}


async def refresh_frame_sizes() -> None:
    """Ukuran frame deteksi tiap kamera, untuk menormalkan kotak MQTT (pixel) ke 0-1."""
    cfg = await client.get_json("/api/config")
    dims = {name: (cam["detect"]["width"], cam["detect"]["height"])
            for name, cam in (cfg.get("cameras") or {}).items()
            if (cam.get("detect") or {}).get("width") and cam["detect"].get("height")}
    if dims:
        live.set_dimensions(dims)


def _rows_from_mqtt(ts: float) -> list[tuple]:
    return [(o["id"], o["camera"], o["label"], ts, o["score"],
             o["x"], o["y"], o["w"], o["h"], json.dumps(o["zones"]),
             int(o["stationary"]), o["position_changes"])
            for o in live.snapshot(ts) if o["camera"] and o["label"]]


async def _rows_from_rest(ts: float) -> list[tuple]:
    events = await client.get_json("/api/events", {"in_progress": 1, "limit": POLL_LIMIT})
    rows = []
    for ev in events:
        d = ev.get("data") or {}
        box = d.get("box") or []
        rows.append((
            ev["id"], ev["camera"], ev["label"], ts,
            d.get("score") or d.get("top_score"),
            *(box[:4] if len(box) == 4 else (None, None, None, None)),
            json.dumps(ev.get("zones") or []), None, None,
        ))
    return rows


async def _check_mqtt_flow(ts: float) -> None:
    """Tandai bila Frigate sedang melacak objek tapi tidak ada kabar MQTT yang masuk.

    Tanpa ini aktivitas bisa berhenti tercatat sama sekali sementara /poller tetap melapor
    tersambung. Jalur data tidak diubah; hanya status dan peringatannya.
    """
    if ts - state["last_flow_check"] < FLOW_CHECK_EVERY:
        return
    state["last_flow_check"] = ts
    try:
        tracking = bool(await client.get_json("/api/events", {"in_progress": 1, "limit": 1}))
    except Exception:
        return  # Frigate tak terjangkau: sudah terlihat di /health, status lama dibiarkan
    last = max(live.last_message_ts or 0.0, live.connected_at or ts)
    silent = tracking and ts - last > MQTT_SILENT_AFTER
    if silent:
        state["mqtt_receiving"] = False
        state["warning"] = (f"Broker MQTT tersambung, tetapi tidak ada kabar dari Frigate selama {ts - last:.0f} "
                            "detik padahal Frigate sedang melacak objek, jadi aktivitas tidak tercatat. "
                            "Cek mqtt.enabled, host, dan topic_prefix di config Frigate.")
    else:
        recent = live.last_message_ts is not None and ts - live.last_message_ts <= MQTT_SILENT_AFTER
        state["mqtt_receiving"] = True if recent else None
        state["warning"] = None


async def _poll_once() -> None:
    ts = time.time()
    if live.connected and not live.has_dimensions():
        # Frigate mungkin belum siap saat backend start; coba lagi sampai dapat
        await refresh_frame_sizes()
    if live.connected:
        rows, source = _rows_from_mqtt(ts), "mqtt"
        await _check_mqtt_flow(ts)
    else:
        rows, source = await _rows_from_rest(ts), "rest (kotak tidak terkini)"
        state["mqtt_receiving"], state["warning"] = None, None
    if rows:
        state["samples"] += store.add_samples(rows)
    evaluate(ts)
    state["last_poll"] = ts
    state["polls"] += 1
    state["source"] = source
    state["last_error"] = None


async def run() -> None:
    state["running"] = True
    last_prune = 0.0
    try:
        while True:
            try:
                await _poll_once()
                if time.time() - last_prune > 3600:
                    store.prune(time.time() - RETENTION_HOURS * 3600)
                    last_prune = time.time()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # Frigate mati/timeout: catat lalu coba lagi
                state["last_error"] = f"{e.__class__.__name__}: {e}"
                logger.warning("gagal mengambil sampel: %s", state["last_error"])
            await asyncio.sleep(POLL_INTERVAL)
    finally:
        state["running"] = False
