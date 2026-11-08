"""Deteksi patokan koin dengan HoughCircles, lalu skor kandidat.

Catatan: radius dari Hough masih kuantisasi akumulator (meleset 4-6%), jadi angka ini baru
cukup untuk memastikan "ada koin", belum untuk skala mm. Refine sub-piksel menyusul.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

MAX_SIDE = 1600          # px, foto diperkecil untuk deteksi saja
MIN_RADIUS_FRAC = 0.035  # kandidat terkecil yang dicari (3,5% sisi pendek)
MIN_SCORE = 0.30         # di bawah ini: dianggap tidak ada koin, bukan "yang terbaik dari nol"


@dataclass
class Candidate:
    cx: float
    cy: float
    r: float
    score: float
    edge: float
    contrast: float


def resize_for_detection(img: np.ndarray, max_side: int = MAX_SIDE) -> np.ndarray:
    h, w = img.shape[:2]
    m = max(h, w)
    if m <= max_side:
        return img
    f = max_side / m
    return cv2.resize(img, (int(round(w * f)), int(round(h * f))), interpolation=cv2.INTER_AREA)


def gradient_mag(gray: np.ndarray) -> np.ndarray:
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def edge_support(mag: np.ndarray, cx: float, cy: float, r: float, n: int = 180) -> float:
    """Rerata magnitudo gradien di sepanjang lingkaran, dinormalisasi ke 0..1."""
    h, w = mag.shape
    vals = []
    for t in np.linspace(0, 2 * math.pi, n, endpoint=False):
        x = int(round(cx + r * math.cos(t)))
        y = int(round(cy + r * math.sin(t)))
        if 0 <= x < w and 0 <= y < h:
            vals.append(float(mag[y, x]))
    if not vals:
        return 0.0
    return float(min(255.0, np.mean(vals)) / 255.0)


def contrast(gray: np.ndarray, cx: float, cy: float, r: float) -> float:
    """Selisih rerata intensitas bagian dalam koin vs cincin di luarnya -> 0..1."""
    h, w = gray.shape
    inner = np.zeros((h, w), np.uint8)
    cv2.circle(inner, (int(cx), int(cy)), max(1, int(r * 0.7)), 255, -1)
    outer = np.zeros((h, w), np.uint8)
    cv2.circle(outer, (int(cx), int(cy)), int(r * 1.45), 255, -1)
    cv2.circle(outer, (int(cx), int(cy)), int(r * 1.05), 0, -1)
    d = abs(float(cv2.mean(gray, mask=inner)[0]) - float(cv2.mean(gray, mask=outer)[0]))
    return float(min(1.0, d / 90.0))


def detect_coin(img: np.ndarray) -> tuple[Candidate | None, list[Candidate]]:
    """Cari koin patokan. Mengembalikan kandidat terbaik (atau None) dan alternatifnya."""
    small = resize_for_detection(img)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.medianBlur(gray, 5)

    h, w = gray.shape
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(h, w) * 0.25,
        param1=110,
        param2=34,
        minRadius=int(min(h, w) * MIN_RADIUS_FRAC),
        maxRadius=int(min(h, w) * 0.5),
    )

    mag = gradient_mag(gray)
    cands: list[Candidate] = []
    if circles is not None:
        for cx, cy, r in np.round(circles[0], 1)[:8]:
            e = edge_support(mag, cx, cy, r)
            c = contrast(gray, cx, cy, r)
            cands.append(Candidate(float(cx), float(cy), float(r), 0.65 * e + 0.35 * c, e, c))

    cands.sort(key=lambda k: k.score, reverse=True)
    best = cands[0] if cands and cands[0].score >= MIN_SCORE else None
    return best, cands
