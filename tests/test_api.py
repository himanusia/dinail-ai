"""Kontrak HTTP: bentuk respons, penolakan input salah, dan status tabel konversi."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from dinail_ai.app import app
from dinail_ai.coins import COINS

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
GOOD = "g2_500.jpg"


def client() -> TestClient:
    return TestClient(app)


def test_health_reports_coin_table():
    h = client().get("/health").json()
    assert h["status"] == "ok"
    assert h["coins"]["500"] == 27.10
    assert h["size_table_configured"] is False  # pemilik belum menyerahkan tabel


def test_size_table_reports_not_configured():
    body = client().get("/v1/size-table").json()
    assert body["configured"] is False
    assert "belum diisi" in body["note"]


def test_analyze_full_response():
    case = json.loads((FIX / "ground_truth.json").read_text(encoding="utf-8"))[1]
    files = {"image": (case["file"], (FIX / case["file"]).read_bytes(), "image/jpeg")}
    data = {"coin": case["coin"], "nail_width_px": str(case["nail_width_mm"] * case["px_per_mm"])}
    r = client().post("/v1/analyze", files=files, data=data)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["quality"]["pass"] is True
    assert body["coin"]["type"] == case["coin"]
    assert body["coin"]["diameter_mm"] == COINS[case["coin"]]["diameter_mm"]
    assert body["nail"]["suggestion"]["size"] is None  # tabel pemilik belum ada
    assert body["elapsed_ms"] < 8000


def test_analyze_without_coin_type_blocks_scale():
    case = json.loads((FIX / "ground_truth.json").read_text(encoding="utf-8"))[1]
    files = {"image": (case["file"], (FIX / case["file"]).read_bytes(), "image/jpeg")}
    body = client().post("/v1/analyze", files=files).json()
    assert body["ok"] is False
    assert body["scale_px_per_mm"] is None
    assert any("jenis koin belum dipilih" in r.lower() for r in body["quality"]["reasons"])


def test_analyze_rejects_non_image():
    r = client().post("/v1/analyze", files={"image": ("x.txt", b"bukan gambar", "text/plain")})
    assert r.status_code == 415


def test_analyze_rejects_broken_image():
    r = client().post("/v1/analyze", files={"image": ("x.jpg", b"\xff\xd8bukan jpeg", "image/jpeg")})
    assert r.status_code == 422
