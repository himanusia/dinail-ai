"""Deteksi koin: akurasi diameter pada scene ber-ground-truth + ketahanan pada foto asli."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import pytest

from dinail_ai import detect

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
TOL_DIAMETER = 0.02  # 2% error diameter koin
TOO_SMALL = {"g5_100.jpg"}  # koin 105 px: terdeteksi, tapi ditolak gerbang kualitas


def truth() -> list[dict]:
    p = FIX / "ground_truth.json"
    if not p.exists():
        pytest.skip("fixtures belum dibuat: jalankan scripts/make_fixtures.py")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", truth(), ids=lambda c: c["file"])
def test_detected_diameter_close_to_ground_truth(case):
    best, _ = detect.detect_coin(cv2.imread(str(FIX / case["file"])))
    assert best is not None, case["file"]
    err = abs(2 * best.r - case["true_diameter_px"]) / case["true_diameter_px"]
    assert err <= TOL_DIAMETER, (
        f"{case['file']}: diameter {2 * best.r:.1f} vs {case['true_diameter_px']} px (err {err:.2%})"
    )


def test_small_coin_is_still_located():
    """Koin kecil tetap harus ketemu; yang menolak adalah gerbang kualitas, bukan detektor."""
    case = next(c for c in truth() if c["file"] in TOO_SMALL)
    best, _ = detect.detect_coin(cv2.imread(str(FIX / case["file"])))
    assert best is not None
    assert 2 * best.r < 0.12 * 1200


def test_no_coin_on_empty_scene():
    best, _ = detect.detect_coin(cv2.imread(str(FIX / "bad_nocoin.jpg")))
    assert best is None


def test_real_coin_photos_detected():
    """Ketahanan pada foto koin asli (bukan uji akurasi: diameter aslinya tak diketahui)."""
    for denom in ("500", "200", "100", "1000"):
        p = FIX / f"coin_{denom}.jpg"
        if not p.exists():
            pytest.skip("fixtures belum dibuat")
        img = cv2.imread(str(p))
        s = 1024 / max(img.shape[:2])
        best, _ = detect.detect_coin(cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
        assert best is not None, f"koin {denom} tidak terdeteksi"
        assert best.score > 0.5
