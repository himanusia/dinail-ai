"""Gerbang kualitas foto: apakah foto layak diukur, dan kalau tidak, kenapa.

Semua alasan dikembalikan sebagai teks yang bisa langsung ditampilkan ke customer.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

QUALITY = {
    "min_side_px": 700,               # foto lebih kecil dari ini -> skala terlalu kasar
    # Ketajaman: p99,5 gradien per petak 128 px, diambil petak TERAJAM. Foto dengan latar polos
    # membuat statistik global (p99,5 seluruh gambar) jatuh walau tepi koinnya tajam: scene uji
    # ber-skala 6-14 px/mm cuma 22-48 secara global, tetapi 380-510 per petak terajam. Foto
    # buram tetap rendah di semua petak (51-55), jadi jarak pisahnya ~8x, bukan 1,7x.
    "sharpness_min": 150.0,
    "sharpness_tile_px": 128,
    "sharpness_target_px": 1024,
    "brightness_min": 45.0,
    "brightness_max": 235.0,
    "coin_min_radius_frac_ok": 0.06,  # diameter <12% sisi pendek -> skala terlalu kasar
}


def metrics(img: np.ndarray) -> dict[str, Any]:
    """Metrik kualitas pada salinan <=1024 px, plus dimensi asli."""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    f = min(1.0, 1024 / max(h, w))
    g = cv2.resize(gray, (int(w * f), int(h * f)), interpolation=cv2.INTER_AREA) if f < 1.0 else gray

    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)

    tile = QUALITY["sharpness_tile_px"]
    step = tile // 2
    scores = [
        float(np.percentile(mag[y:y + tile, x:x + tile], 99.5))
        for y in range(0, max(1, mag.shape[0] - tile + 1), step)
        for x in range(0, max(1, mag.shape[1] - tile + 1), step)
        if mag[y:y + tile, x:x + tile].size
    ]
    sharpness = max(scores) if scores else float(np.percentile(mag, 99.5))

    return {
        "width": int(w),
        "height": int(h),
        "min_side": int(min(h, w)),
        "sharpness": round(sharpness, 1),
        "sharpness_global": round(float(np.percentile(mag, 99.5)), 1),
        "blur_var": round(float(cv2.Laplacian(g, cv2.CV_64F).var()), 2),
        "brightness": round(float(gray.mean()), 2),
        "contrast_std": round(float(gray.std()), 2),
    }


def gate(m: dict[str, Any], coin_radius_px: float | None) -> list[str]:
    """Daftar alasan foto ditolak; kosong berarti lolos."""
    reasons: list[str] = []
    if m["min_side"] < QUALITY["min_side_px"]:
        reasons.append(f"Foto terlalu kecil ({m['min_side']} px), minimal {QUALITY['min_side_px']} px.")
    if m["sharpness"] < QUALITY["sharpness_min"]:
        reasons.append(
            f"Foto buram (ketajaman {m['sharpness']:.0f}, minimal {QUALITY['sharpness_min']:.0f})."
            " Pegang kamera lebih stabil atau dekatkan cahaya."
        )
    if not (QUALITY["brightness_min"] <= m["brightness"] <= QUALITY["brightness_max"]):
        reasons.append(f"Pencahayaan tidak wajar (kecerahan {m['brightness']}).")
    if coin_radius_px is None:
        reasons.append("Patokan koin tidak terdeteksi: letakkan koin datar di samping tangan.")
    elif coin_radius_px < m["min_side"] * QUALITY["coin_min_radius_frac_ok"]:
        reasons.append(
            f"Koin terlalu kecil di foto (diameter {round(2 * coin_radius_px)} px). "
            "Dekatkan kamera supaya koin minimal 12% lebar foto."
        )
    return reasons
