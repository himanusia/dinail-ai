"""Orkestrasi satu foto: kualitas -> deteksi koin -> skala px/mm -> saran nomor ukuran."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from . import quality
from .coins import AMBIGUOUS_PAIRS, COINS
from .detect import detect_coin
from .sizes import read_table, suggest_size


@dataclass
class Result:
    ok: bool
    quality: dict[str, Any] = field(default_factory=dict)
    coin: dict[str, Any] | None = None
    scale_px_per_mm: float | None = None
    nail: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "quality": self.quality,
            "coin": self.coin,
            "scale_px_per_mm": None if self.scale_px_per_mm is None else round(self.scale_px_per_mm, 4),
            "nail": self.nail,
            "warnings": self.warnings,
        }


def decode_image(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("File bukan gambar yang bisa dibaca (JPEG/PNG/WebP).")
    return img


def coin_type(declared: str | None) -> dict[str, Any]:
    """Jenis koin datang dari form, bukan ditebak dari ukuran (Rp200 vs Rp1000 beda 1 mm)."""
    if not declared:
        return {"type": None, "confidence": 0.0, "reason": "jenis koin belum dipilih"}
    key = str(declared).strip().lower().replace("rp", "").replace(".", "")
    if key not in COINS:
        return {"type": None, "confidence": 0.0, "reason": f"jenis koin '{declared}' tidak dikenal"}
    return {"type": key, "confidence": 1.0, "reason": "dipilih di form pemesanan"}


def analyze(
    data: bytes,
    coin: str | None = None,
    nail_width_px: float | None = None,
    coin_diameter_px: float | None = None,
    size_table_path: str | None = None,
) -> Result:
    img = decode_image(data)
    m = quality.metrics(img)

    diameter_px = coin_diameter_px
    coin_info: dict[str, Any] | None = None
    if diameter_px is None:
        best, cands = detect_coin(img)
        if best is not None:
            diameter_px = 2 * best.r
            coin_info = {
                "found": True,
                "center_px": [round(best.cx, 1), round(best.cy, 1)],
                "radius_px": round(best.r, 1),
                "diameter_px": round(diameter_px, 1),
                "score": round(best.score, 3),
                "alternatives": [
                    {
                        "center_px": [round(c.cx, 1), round(c.cy, 1)],
                        "radius_px": round(c.r, 1),
                        "score": round(c.score, 3),
                    }
                    for c in cands[1:4]
                ],
            }
    else:
        coin_info = {"found": True, "source": "manual", "diameter_px": round(float(diameter_px), 1)}

    reasons = quality.gate(m, (diameter_px / 2) if diameter_px is not None else None)

    warnings: list[str] = []
    scale = None
    kind = coin_type(coin)
    if diameter_px is not None:
        if kind["type"]:
            d_mm = COINS[kind["type"]]["diameter_mm"]
            scale = diameter_px / d_mm
            coin_info = {**(coin_info or {}), "type": kind["type"], "diameter_mm": d_mm}
            for a, b in AMBIGUOUS_PAIRS:
                if kind["type"] in (a, b):
                    other = b if kind["type"] == a else a
                    warnings.append(
                        f"Koin {kind['type']} dan {other} hanya berbeda "
                        f"{abs(COINS[a]['diameter_mm'] - COINS[b]['diameter_mm']):.0f} mm; "
                        "hasil sebaiknya dicek admin."
                    )
        elif coin:
            reasons.append(
                f"Jenis koin tidak dikenal: '{coin}'. Pilih Rp50, Rp100, Rp200, Rp500, atau Rp1000."
            )
        else:
            reasons.append(
                "Jenis koin belum dipilih (koin 24 mm vs 25 mm tidak bisa dibedakan dari ukuran saja)."
            )

    nail = None
    if nail_width_px is not None and scale:
        width_mm = float(nail_width_px) / scale
        nail = {
            "width_px": round(float(nail_width_px), 1),
            "width_mm": round(width_mm, 2),
            "suggestion": suggest_size(width_mm, read_table(size_table_path)),
        }
    elif nail_width_px is not None:
        reasons.append("Lebar kuku tidak bisa dikonversi ke mm tanpa skala koin.")

    return Result(
        ok=not reasons,
        quality={"pass": not reasons, "reasons": reasons, **m},
        coin=coin_info,
        scale_px_per_mm=scale,
        nail=nail,
        warnings=warnings,
    )
