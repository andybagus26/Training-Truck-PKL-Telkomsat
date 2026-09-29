"""Bentuk data yang dikembalikan API ini (hasil perapian dari data mentah Frigate)."""
from datetime import datetime

from pydantic import BaseModel, Field

# Label sesuai model v5 yang aktif di Frigate
LABELS = ["truck", "full_load", "empty_load", "excavator"]


class Box(BaseModel):
    x: float = Field(description="Titik kiri kotak, relatif 0-1 terhadap lebar frame")
    y: float = Field(description="Titik atas kotak, relatif 0-1 terhadap tinggi frame")
    w: float = Field(description="Lebar kotak, relatif 0-1")
    h: float = Field(description="Tinggi kotak, relatif 0-1")


class Detection(BaseModel):
    id: str
    camera: str
    label: str = Field(description="truck, full_load, empty_load, atau excavator")
    score: float | None = Field(default=None, description="Skor tertinggi selama objek dilacak, 0-1")
    start_time: datetime
    end_time: datetime | None = Field(default=None, description="Kosong bila objek masih terlihat")
    duration_seconds: float | None = None
    ongoing: bool = Field(description="True bila objek masih terlihat saat ini")
    zones: list[str] = Field(default_factory=list, description="Zone yang dimasuki objek")
    box: Box | None = None
    has_snapshot: bool = False
    has_clip: bool = False
    snapshot_url: str | None = Field(default=None, description="Endpoint gambar di API ini")


class CameraInfo(BaseModel):
    name: str
    enabled: bool
    detect_fps: int | None = None
    resolution: str | None = None
    zones: list[str] = Field(default_factory=list)
    tracked_labels: list[str] = Field(default_factory=list)


class LabelCount(BaseModel):
    label: str
    count: int
    average_score: float | None = None
    last_seen: datetime | None = None


class CameraSummary(BaseModel):
    camera: str
    total: int
    per_label: list[LabelCount]


class Summary(BaseModel):
    since: datetime
    until: datetime
    total: int
    per_label: list[LabelCount]
    per_camera: list[CameraSummary]


class DetectorStats(BaseModel):
    name: str
    inference_speed_ms: float | None = None
    detection_start: float | None = None


class CameraStats(BaseModel):
    camera: str
    camera_fps: float | None = None
    process_fps: float | None = None
    detection_fps: float | None = None
    skipped_fps: float | None = None


class Stats(BaseModel):
    detectors: list[DetectorStats]
    cameras: list[CameraStats]
    frigate_version: str | None = None
    uptime_seconds: float | None = None


class Health(BaseModel):
    status: str = Field(description="ok bila Frigate terjangkau, degraded bila tidak")
    frigate_url: str
    frigate_reachable: bool
    frigate_version: str | None = None
    model_labels: list[str] = LABELS


class Activity(BaseModel):
    id: int
    type: str = Field(description="Jenis aktivitas; tahap 1 baru menangani 'loading'")
    camera: str
    truck_id: str = Field(description="Id objek truk di Frigate")
    partner_id: str | None = Field(default=None, description="Id excavator yang memuat, bila terdeteksi")
    start_time: datetime
    end_time: datetime | None = Field(default=None, description="Kosong bila masih berlangsung")
    duration_seconds: float | None = None
    ongoing: bool
    load_before: str | None = Field(default=None, description="Status muatan saat aktivitas dimulai")
    load_after: str | None = Field(default=None, description="Status muatan terakhir yang terlihat")
    rule: str | None = Field(default=None, description="Aturan yang memicu aktivitas ini")


class TruckState(BaseModel):
    truck_id: str
    camera: str
    label: str = "truck"
    last_seen: datetime
    score: float | None = None
    load_state: str | None = Field(default=None, description="full_load, empty_load, atau kosong bila bak tidak terlihat")
    stationary: bool = Field(description="Titik tengah kotak nyaris tidak bergerak dalam jendela penilaian")
    excavator_nearby: str | None = None
    activity: str | None = Field(default=None, description="'loading' bila sedang dimuat")
    activity_seconds: float | None = None


class MqttStatus(BaseModel):
    connected: bool = Field(description="True bila backend tersambung ke broker MQTT Frigate")
    broker: str
    topic: str
    messages: int = 0
    last_message: datetime | None = None
    tracked_objects: int = Field(default=0, description="Objek yang sedang terlihat menurut kabar terakhir")
    last_error: str | None = None


class PollerStatus(BaseModel):
    running: bool
    last_poll: datetime | None = None
    polls: int = 0
    samples_collected: int = 0
    last_error: str | None = None
    samples_in_db: int | None = None
    activities_in_db: int | None = None
    source: str = Field(default="", description="Asal sampel: 'mqtt' (posisi terkini) atau 'rest' (cadangan)")
    mqtt: MqttStatus | None = None
