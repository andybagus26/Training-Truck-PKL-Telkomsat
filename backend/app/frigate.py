"""Klien untuk API Frigate.

Semua pemanggilan ke Frigate lewat satu tempat ini, supaya penanganan error dan timeout seragam.
"""
import os

import httpx
from fastapi import HTTPException

FRIGATE_URL = os.getenv("FRIGATE_URL", "http://localhost:8971").rstrip("/")
TIMEOUT = float(os.getenv("FRIGATE_TIMEOUT", "10"))


class FrigateClient:
    def __init__(self, base_url: str = FRIGATE_URL, timeout: float = TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, path: str, params: dict | None = None) -> httpx.Response:
        try:
            r = await self._client.get(path, params=params)
        except httpx.TimeoutException:
            raise HTTPException(504, f"Frigate tidak merespons dalam {TIMEOUT} detik ({self.base_url})")
        except httpx.RequestError as e:
            raise HTTPException(503, f"Frigate tidak bisa dihubungi di {self.base_url}: {e.__class__.__name__}")
        if r.status_code == 404:
            raise HTTPException(404, f"Tidak ditemukan di Frigate: {path}")
        if r.status_code >= 400:
            raise HTTPException(502, f"Frigate mengembalikan status {r.status_code} untuk {path}")
        return r

    async def get_json(self, path: str, params: dict | None = None):
        r = await self._request(path, params)
        try:
            return r.json()
        except ValueError:
            raise HTTPException(502, f"Jawaban Frigate untuk {path} bukan JSON")

    async def get_bytes(self, path: str, params: dict | None = None) -> tuple[bytes, str]:
        r = await self._request(path, params)
        return r.content, r.headers.get("content-type", "application/octet-stream")

    async def is_up(self) -> tuple[bool, str | None]:
        try:
            r = await self._client.get("/api/version")
            return (True, r.text.strip()) if r.status_code == 200 else (False, None)
        except httpx.RequestError:
            return False, None


client = FrigateClient()
