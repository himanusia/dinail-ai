"""Deteksi koin: refine sub-piksel harus mengalahkan kuantisasi Hough."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from dinail_ai import detect


def _scene(radius: int = 140, size=(1200, 1600)) -> np.ndarray:
    h, w = size
    img = np.full((h, w, 3), 205, np.uint8)
    cv2.circle(img, (int(w * 0.7), int(h * 0.45)), radius, (95, 100, 110), -1)
    cv2.circle(img, (int(w * 0.7), int(h * 0.45)), int(radius * 0.8), (140, 145, 150), -1)
    return cv2.GaussianBlur(img, (3, 3), 0)


@pytest.mark.parametrize("radius", [90, 140, 220])
def test_refined_diameter_within_one_percent(radius):
    """Target 1%: Hough sendirian meleset 4-6%; refine memotong errornya jadi <1%."""
    best, _ = detect.detect_coin(_scene(radius=radius))
    assert best is not None
    err = abs(2 * best.r - 2 * radius) / (2 * radius)
    assert err <= 0.01, f"r={radius}: diameter {2 * best.r:.2f} (err {err:.2%})"


def test_refine_ignores_inner_ring():
    """Koin rupiah punya cincin dekoratif di dalam tepi: refine harus memilih rim luar."""
    img = _scene(radius=200)
    gray = cv2.medianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 5)
    cx, cy, r = detect.refine_circle(detect.gradient_mag(gray), 1600 * 0.7, 1200 * 0.45, 190)
    assert abs(2 * r - 400) / 400 <= 0.01, f"diameter {2 * r:.1f} vs 400"


def test_refine_keeps_coarse_when_fit_is_wild():
    """Fit yang melompat >20% radius harus ditolak, bukan dipakai."""
    rng = np.random.default_rng(0)
    mag = rng.normal(5, 1, (600, 600)).astype(np.float32)
    cx, cy, r = detect.refine_circle(mag, 300, 300, 100)
    # derau tanpa tepi: hasil tidak boleh melompat jauh dari usulan awal
    assert abs(cx - 300) < 1 and abs(cy - 300) < 1 and abs(r - 100) < 1
