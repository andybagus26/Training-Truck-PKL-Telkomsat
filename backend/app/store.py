"""Penyimpanan riwayat deteksi dan aktivitas (SQLite).

Frigate hanya menyimpan ringkasan per objek dan membersihkan datanya setelah beberapa hari, sedangkan
untuk menghitung durasi dan siklus kerja kita butuh rekaman keadaan dari waktu ke waktu. Karena itu
backend mengambil sampel berkala dan menyimpannya di sini.
"""
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).resolve().parents[1] / "data" / "activity.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    object_id TEXT NOT NULL,
    camera    TEXT NOT NULL,
    label     TEXT NOT NULL,
    ts        REAL NOT NULL,
    score     REAL,
    x REAL, y REAL, w REAL, h REAL,
    zones     TEXT NOT NULL DEFAULT '[]',
    stationary        INTEGER,            -- 1 bila Frigate menganggap objek berhenti
    position_changes  INTEGER,            -- berapa kali objek berpindah posisi sejak muncul
    PRIMARY KEY (object_id, ts)
);
CREATE INDEX IF NOT EXISTS idx_samples_cam_ts ON samples (camera, ts);

CREATE TABLE IF NOT EXISTS activities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,              -- untuk saat ini: 'loading'
    camera      TEXT NOT NULL,
    truck_id    TEXT NOT NULL,
    partner_id  TEXT,                       -- excavator yang memuat, bila terdeteksi
    start_ts    REAL NOT NULL,
    end_ts      REAL,                       -- kosong selama masih berlangsung
    load_before TEXT,                       -- status muatan saat mulai
    load_after  TEXT,                       -- status muatan saat selesai
    meta        TEXT NOT NULL DEFAULT '{}',
    UNIQUE (type, truck_id, start_ts)
);
CREATE INDEX IF NOT EXISTS idx_activities_cam_start ON activities (camera, start_ts);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    # kolom yang ditambahkan belakangan, agar database lama tetap terpakai
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(samples)")}
    for col in ("stationary", "position_changes"):
        if col not in existing:
            conn.execute(f"ALTER TABLE samples ADD COLUMN {col} INTEGER")
    conn.commit()
    return conn


class Store:
    def __init__(self) -> None:
        self.conn = connect()

    def close(self) -> None:
        self.conn.close()

    # ---------- sampel deteksi ----------

    def add_samples(self, rows: list[tuple]) -> int:
        """rows: (object_id, camera, label, ts, score, x, y, w, h, zones_json, stationary, position_changes)"""
        cur = self.conn.executemany(
            "INSERT OR IGNORE INTO samples "
            "(object_id,camera,label,ts,score,x,y,w,h,zones,stationary,position_changes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        self.conn.commit()
        return cur.rowcount

    def samples_since(self, since_ts: float, camera: str | None = None) -> list[sqlite3.Row]:
        q = "SELECT * FROM samples WHERE ts >= ?"
        args: list[Any] = [since_ts]
        if camera:
            q += " AND camera = ?"
            args.append(camera)
        return self.conn.execute(q + " ORDER BY ts", args).fetchall()

    def object_track(self, object_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM samples WHERE object_id = ? ORDER BY ts", (object_id,)).fetchall()

    def prune(self, before_ts: float) -> int:
        cur = self.conn.execute("DELETE FROM samples WHERE ts < ?", (before_ts,))
        self.conn.commit()
        return cur.rowcount

    def counts(self) -> dict:
        c = self.conn.execute("SELECT COUNT(*) n, MAX(ts) last FROM samples").fetchone()
        a = self.conn.execute("SELECT COUNT(*) n FROM activities").fetchone()
        return {"samples": c["n"], "last_sample_ts": c["last"], "activities": a["n"]}

    # ---------- aktivitas ----------

    def open_activity(self, type_: str, camera: str, truck_id: str, start_ts: float,
                      partner_id: str | None, load_before: str | None, meta: dict) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO activities (type,camera,truck_id,partner_id,start_ts,load_before,meta) "
            "VALUES (?,?,?,?,?,?,?)",
            (type_, camera, truck_id, partner_id, start_ts, load_before, json.dumps(meta)))
        self.conn.commit()

    def update_activity(self, activity_id: int, **fields) -> None:
        if not fields:
            return
        if "meta" in fields:
            fields["meta"] = json.dumps(fields["meta"])
        sets = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(f"UPDATE activities SET {sets} WHERE id = ?", [*fields.values(), activity_id])
        self.conn.commit()

    def ongoing_activity(self, type_: str, truck_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM activities WHERE type = ? AND truck_id = ? AND end_ts IS NULL "
            "ORDER BY start_ts DESC LIMIT 1", (type_, truck_id)).fetchone()

    def activities(self, type_: str | None = None, camera: str | None = None,
                   since_ts: float | None = None, ongoing_only: bool = False,
                   limit: int = 100) -> list[sqlite3.Row]:
        q, args = "SELECT * FROM activities WHERE 1=1", []
        if type_:
            q += " AND type = ?"; args.append(type_)
        if camera:
            q += " AND camera = ?"; args.append(camera)
        if since_ts:
            q += " AND start_ts >= ?"; args.append(since_ts)
        if ongoing_only:
            q += " AND end_ts IS NULL"
        q += " ORDER BY start_ts DESC LIMIT ?"; args.append(limit)
        return self.conn.execute(q, args).fetchall()

    def delete_activity(self, activity_id: int) -> None:
        self.conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
        self.conn.commit()

    def activity(self, activity_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM activities WHERE id = ?", (activity_id,)).fetchone()


store = Store()
