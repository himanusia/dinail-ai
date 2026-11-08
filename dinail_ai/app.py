"""API layanan model AI dinail.co.

Kontrak untuk FS (frontend/backend):
  POST /v1/analyze  multipart/form-data
     image             : JPEG/PNG/WebP (wajib, maks 12 MB)
     coin              : "50" | "100" | "200" | "500" | "1000" (opsional, jalur cadangan form)
     nail_width_px     : float (opsional, lebar kuku dari alat ukur di UI/admin)
     coin_diameter_px  : float (opsional, kalau admin mengukur koin manual)
  -> { ok, quality{pass,reasons,metrics}, coin, scale_px_per_mm, nail{...}, warnings[] }

  GET  /health       status + versi + status tabel konversi
  GET  /v1/size-table tabel konversi pemilik (kosong = belum diisi)
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from .analyze import analyze
from .coins import COINS
from .sizes import read_table

VERSION = "0.1.0"
SIZE_TABLE_PATH = os.environ.get("DINAIL_SIZE_TABLE", str(Path(__file__).with_name("size_table.json")))
MAX_BYTES = 12 * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png", "image/webp"}

app = FastAPI(title="dinail AI - foto ukuran kuku", version=VERSION)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": VERSION,
        "coins": {k: v["diameter_mm"] for k, v in COINS.items()},
        "size_table_configured": Path(SIZE_TABLE_PATH).exists(),
        "size_table_path": SIZE_TABLE_PATH,
    }


@app.get("/v1/size-table")
def size_table() -> dict:
    table = read_table(SIZE_TABLE_PATH)
    if not table:
        return {"configured": False, "sizes": [], "note": "tabel konversi nomor ukuran dari pemilik belum diisi"}
    return {"configured": True, **table}


@app.post("/v1/analyze")
async def analyze_photo(
    image: UploadFile = File(...),
    coin: str | None = Form(None),
    nail_width_px: float | None = Form(None),
    coin_diameter_px: float | None = Form(None),
) -> JSONResponse:
    if image.content_type not in ALLOWED:
        raise HTTPException(
            status_code=415,
            detail=f"Tipe file {image.content_type} tidak didukung; kirim JPEG/PNG/WebP.",
        )
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="File kosong.")
    if len(data) > MAX_BYTES:
        raise HTTPException(
            status_code=413, detail=f"Foto lebih dari {MAX_BYTES // (1024 * 1024)} MB, perkecil dulu."
        )

    t0 = time.perf_counter()
    try:
        result = analyze(
            data,
            coin=coin,
            nail_width_px=nail_width_px,
            coin_diameter_px=coin_diameter_px,
            size_table_path=SIZE_TABLE_PATH,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    payload = result.as_dict()
    payload["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return JSONResponse(payload)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).with_name("index.html")).read_text(encoding="utf-8")
