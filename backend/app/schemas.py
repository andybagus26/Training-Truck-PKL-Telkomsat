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
