"""Deteksi koin: Hough harus menemukan koin yang jelas, skornya masuk akal."""

from __future__ import annotations

import cv2
import numpy as np

from dinail_ai import detect


def _scene(radius: int = 140, size=(1200, 1600)) -> np.ndarray:
    h, w = size
    img = np.full((h, w, 3), 205, np.uint8)
    cv2.circle(img, (int(w * 0.7), int(h * 0.45)), radius, (95, 100, 110), -1)
    cv2.circle(img, (int(w * 0.7), int(h * 0.45)), int(radius * 0.8), (140, 145, 150), -1)
    return cv2.GaussianBlur(img, (3, 3), 0)


def test_finds_drawn_circle():
    img = _scene(radius=140)
    best, cands = detect.detect_coin(img)
    assert best is not None
    assert abs(2 * best.r - 280) / 280 <= 0.05, f"diameter {2 * best.r:.1f} vs 280"
    assert best.score >= detect.MIN_SCORE


def test_empty_plate_returns_none():
    best, _ = detect.detect_coin(np.full((1200, 1600, 3), 205, np.uint8))
    assert best is None


def test_candidates_are_sorted_by_score():
    _, cands = detect.detect_coin(_scene())
    scores = [c.score for c in cands]
    assert scores == sorted(scores, reverse=True)
