"""Pemetaan lebar kuku (mm) ke nomor ukuran memakai tabel konversi pemilik.

Tabel itu konfigurasi bisnis, bukan angka yang boleh dikarang: kalau belum ada, jawabannya
"belum diisi", bukan tebakan.
"""

from __future__ import annotations

import json
from typing import Any


def read_table(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def suggest_size(width_mm: float, table: dict[str, Any] | None) -> dict[str, Any]:
    """Petakan lebar kuku (mm) ke nomor ukuran; hasil selalu saran yang dicek admin."""
    if not table or not table.get("sizes"):
        return {
            "size": None,
            "reason": "tabel konversi ukuran pemilik belum diisi",
            "needs_admin_check": True,
        }
    best = next(
        (r for r in table["sizes"] if float(r["min_mm"]) <= width_mm <= float(r["max_mm"])),
        None,
    )
    if best is None:
        best = min(
            table["sizes"],
            key=lambda r: min(abs(width_mm - float(r["min_mm"])), abs(width_mm - float(r["max_mm"]))),
        )
    margin = min(abs(width_mm - float(best["min_mm"])), abs(width_mm - float(best["max_mm"])))
    return {
        "size": best.get("size"),
        "range_mm": [float(best["min_mm"]), float(best["max_mm"])],
        "margin_mm": round(float(margin), 2),
        "ambiguous": bool(margin < 0.5),
        "needs_admin_check": True,
    }
