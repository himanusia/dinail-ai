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


def test_real_coin_photo_with_margin_is_detected():
    """Foto koin asli (domain publik) dengan koin utuh di dalam frame harus terdeteksi."""
    p = FIX / "coin_500.jpg"
    if not p.exists():
        pytest.skip("fixtures belum dibuat")
    img = cv2.imread(str(p))
    s = 1024 / max(img.shape[:2])
    best, _ = detect.detect_coin(cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
    assert best is not None, "koin utuh tidak terdeteksi"
    assert 0.42 * 1024 <= best.r <= 0.50 * 1024, f"radius {best.r:.0f} di luar rentang wajar koin penuh"
    assert best.edge > 0.4


def test_frame_filling_crop_does_not_use_clipped_rim():
    """Kalau koin dipotong tepat di tepi frame, rim-nya tidak boleh dipakai sebagai skala.

    Foto seperti ini bukan input produk (koin harus utuh di dalam frame), tapi berguna untuk
    memastikan tidak ada lingkaran sebesar frame yang diterima.
    """
    for denom in ("200", "1000"):
        p = FIX / f"coin_{denom}.jpg"
        if not p.exists():
            pytest.skip("fixtures belum dibuat")
        img = cv2.imread(str(p))
        s = 1024 / max(img.shape[:2])
        small = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        best, _ = detect.detect_coin(small)
        if best is not None:
            assert best.r < 0.45 * min(small.shape[:2]), \
                f"koin {denom}: rim terpotong dipakai (r={best.r:.0f})"


REAL = ROOT / "samples" / "real"


@pytest.mark.parametrize("name", ["tangan-koin-kecil.jpg", "tangan-penggaris.jpg"])
def test_real_hand_photos_without_usable_coin_are_rejected(name):
    p = REAL / name
    if not p.exists():
        pytest.skip("foto asli tidak ada")
    best, _ = detect.detect_coin(cv2.imread(str(p)))
    assert best is None, f"{name}: diterima sebagai koin (r={best.r:.0f}, skor={best.score:.2f})"


def test_known_limitation_palm_can_look_like_a_coin():
    """Batas yang diketahui: telapak dengan koin yang digenggam masih bisa diterima.

    Ambang gerbang diturunkan supaya koin pada foto pemilik benar-benar ketemu (31/32 foto);
    akibatnya busur telapak di foto ini lolos. Mitigasinya: hasil selalu saran yang dicek
    admin. Kalau nanti ada diskriminator yang lebih baik, test ini yang berubah.
    """
    p = REAL / "tangan-koin-emas.jpg"
    if not p.exists():
        pytest.skip("foto asli tidak ada")
    best, _ = detect.detect_coin(cv2.imread(str(p)))
    assert best is not None and best.r > 100
