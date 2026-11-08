"""Gerbang kualitas: setiap alasan tolak harus punya pemicu yang jelas."""

import cv2
import numpy as np

from dinail_ai import quality


def _scene(sharp: bool = True, brightness: float = 1.0, size=(1200, 1600)) -> np.ndarray:
    rng = np.random.default_rng(0)
    h, w = size
    img = np.full((h, w, 3), 205, np.uint8)
    cv2.circle(img, (int(w * 0.7), int(h * 0.45)), int(min(h, w) * 0.12), (90, 95, 100), -1)
    cv2.rectangle(img, (int(w * 0.2), int(h * 0.35)), (int(w * 0.2) + 120, int(h * 0.35) + 170), (200, 190, 215), -1)
    img = np.clip(img.astype(np.float32) + rng.normal(0, 6, img.shape), 0, 255).astype(np.uint8)
    if not sharp:
        img = cv2.GaussianBlur(img, (0, 0), 12)
    return np.clip(img.astype(np.float32) * brightness, 0, 255).astype(np.uint8)


def test_metrics_report_dimensions_and_medias():
    m = quality.metrics(_scene())
    assert m["width"] == 1600 and m["height"] == 1200
    assert m["min_side"] == 1200
    assert m["sharpness"] > quality.QUALITY["sharpness_min"]
    assert 180 < m["brightness"] < 230


def test_sharp_photo_with_coin_passes():
    m = quality.metrics(_scene())
    assert quality.gate(m, coin_radius_px=200) == []


def test_blurred_photo_rejected():
    m = quality.metrics(_scene(sharp=False))
    reasons = quality.gate(m, coin_radius_px=200)
    assert any("buram" in r for r in reasons), reasons


def test_dark_photo_rejected():
    m = quality.metrics(_scene(brightness=0.12))
    assert any("encahayaan" in r for r in quality.gate(m, coin_radius_px=200))


def test_small_photo_rejected():
    m = quality.metrics(_scene(size=(480, 360)))
    assert any("terlalu kecil" in r for r in quality.gate(m, coin_radius_px=60))


def test_missing_coin_rejected():
    m = quality.metrics(_scene())
    assert any("tidak terdeteksi" in r for r in quality.gate(m, coin_radius_px=None))


def test_small_coin_rejected_with_pixel_size():
    m = quality.metrics(_scene())
    reasons = quality.gate(m, coin_radius_px=50)  # 100 px di foto 1200 px
    assert any("terlalu kecil di foto (diameter 100 px)" in r for r in reasons), reasons
