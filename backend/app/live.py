"""Keadaan objek terkini, dibaca langsung dari MQTT Frigate.

Kenapa tidak cukup lewat `/api/events`: kotak yang dikembalikan endpoint itu adalah posisi saat
snapshot terbaik objek diambil, bukan posisi sekarang. Dua objek yang sama-sama terlihat di layar
bisa punya kotak dari detik yang berbeda, sehingga tidak bisa dipakai menilai "excavator berdekatan
dengan truk" atau "kotak muatan di dalam kotak truk".

Frigate mengirim kabar tiap objek ke topik `frigate/events` saat objek bergerak, berpindah zone, atau
berubah status; isinya posisi terkini, status diam, dan zone yang sedang ditempati. Objek yang diam
justru jarang dikabarkan: pada pengujian, truk yang sedang dimuat hanya mendapat 1 kabar dalam 100
detik, padahal Frigate terus melacaknya. Karena itu objek baru dianggap hilang saat Frigate
mengirim kabar "end", atau setelah STALE_AFTER detik tanpa kabar sebagai pengaman bila kabar itu
terlewat. Modul ini menampung pesan itu sebagai gambaran keadaan sekarang; poller tinggal
memotretnya secara berkala.

Kotak dari MQTT berupa pixel (x1, y1, x2, y2) pada resolusi deteksi, jadi perlu dinormalkan ke 0-1
memakai ukuran tiap kamera dari `/api/config`.
"""
import json
import logging
import os
import threading
import time

import paho.mqtt.client as mqtt

logger = logging.getLogger("live")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER") or None
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD") or None
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "frigate/events")
# Detik tanpa kabar sebelum objek dilupakan. Harus jauh di atas jeda kabar untuk objek diam (sekitar
# 1 menit); dengan 30 detik, truk yang dimuat atau idle hilang separuh waktu dan aktivitasnya terpecah.
STALE_AFTER = float(os.getenv("MQTT_STALE_AFTER", "120"))


class LiveObjects:
    """Objek yang sedang terlihat, menurut kabar terakhir dari Frigate."""

    def __init__(self) -> None:
        self._objects: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._dims: dict[str, tuple[int, int]] = {}
        self._client: mqtt.Client | None = None
        self.connected = False
        self.messages = 0
        self.last_message_ts: float | None = None
        self.last_error: str | None = None

    # ---------- ukuran frame ----------

    def has_dimensions(self) -> bool:
        with self._lock:
            return bool(self._dims)

    def set_dimensions(self, dims: dict[str, tuple[int, int]]) -> None:
        """dims: {nama_kamera: (lebar, tinggi)} pada resolusi deteksi."""
        with self._lock:
            self._dims.update(dims)

    # ---------- siklus hidup ----------

    def start(self) -> None:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="truck-backend")
        if MQTT_USER:
            client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        self._client = client
        try:
            client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_start()   # paho menjalankan thread-nya sendiri dan menyambung ulang otomatis
        except Exception as e:
            self.last_error = f"{e.__class__.__name__}: {e}"
            logger.warning("gagal menyambung ke MQTT: %s", self.last_error)

    def stop(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
        self.connected = False

    # ---------- callback paho ----------

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        if reason_code == 0:
            self.connected = True
            self.last_error = None
            client.subscribe(MQTT_TOPIC)
            logger.info("tersambung ke MQTT %s:%s, berlangganan %s", MQTT_HOST, MQTT_PORT, MQTT_TOPIC)
        else:
            self.connected = False
            self.last_error = f"connect ditolak: {reason_code}"

    def _on_disconnect(self, client, userdata, *args) -> None:
        self.connected = False
        logger.warning("koneksi MQTT terputus, paho akan menyambung ulang")

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        after = payload.get("after") or {}
        obj_id = after.get("id")
        if not obj_id:
            return
        with self._lock:
            if payload.get("type") == "end":
                self._objects.pop(obj_id, None)
            elif not after.get("false_positive"):
                self._objects[obj_id] = {
                    "id": obj_id,
                    "camera": after.get("camera"),
                    "label": after.get("label"),
                    "score": after.get("score") or after.get("top_score"),
                    "box": after.get("box"),
                    "stationary": bool(after.get("stationary")),
                    "position_changes": after.get("position_changes"),
                    "zones": after.get("current_zones") or [],
                    "updated": time.time(),
                }
            self.messages += 1
            self.last_message_ts = time.time()

    # ---------- pembacaan ----------

    def _normalize(self, camera: str, box) -> tuple:
        """Kotak pixel (x1,y1,x2,y2) -> (x, y, w, h) relatif 0-1."""
        dims = self._dims.get(camera)
        if not dims or not box or len(box) != 4:
            return (None, None, None, None)
        w, h = dims
        if not w or not h:
            return (None, None, None, None)
        x1, y1, x2, y2 = box
        return (x1 / w, y1 / h, (x2 - x1) / w, (y2 - y1) / h)

    def snapshot(self, ts: float) -> list[dict]:
        """Potret keadaan sekarang. Objek yang lama tak dikabarkan dianggap sudah hilang."""
        with self._lock:
            stale = [k for k, v in self._objects.items() if ts - v["updated"] > STALE_AFTER]
            for k in stale:
                del self._objects[k]
            out = []
            for o in self._objects.values():
                x, y, w, h = self._normalize(o["camera"], o["box"])
                out.append({**o, "x": x, "y": y, "w": w, "h": h})
            return out

    def status(self) -> dict:
        return {
            "connected": self.connected,
            "broker": f"{MQTT_HOST}:{MQTT_PORT}",
            "topic": MQTT_TOPIC,
            "messages": self.messages,
            "last_message_ts": self.last_message_ts,
            "tracked_objects": len(self._objects),
            "last_error": self.last_error,
        }


live = LiveObjects()
