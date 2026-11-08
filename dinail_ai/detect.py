"""Deteksi patokan koin: Hough kasar lalu refine sub-piksel ke rim luar.

Kenapa dua tahap: HoughCircles meleset 4-6% karena kuantisasi akumulator, dan koin rupiah
punya cincin dekoratif di dalam tepi yang gradiennya lebih kuat daripada siluetnya. Refine
menelusuri puncak gradien per sudut, memilih radius LUAR, lalu mencocokkan lingkaran.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

MAX_SIDE = 1600          # px, foto diperkecil untuk deteksi saja
MIN_RADIUS_FRAC = 0.035  # kandidat terkecil yang dicari (3,5% sisi pendek)
MIN_SCORE = 0.36         # di bawah ini: dianggap tidak ada koin, bukan "yang terbaik dari nol"
# Ambang gerbang diturunkan dari 32 foto pemilik: pada 0,60 hanya 17/32 koin ketemu, pada 0,25
# jadi 27/32 (median selisih diameter 1,8%). Konsekuensinya foto tangan tanpa koin bisa lolos
# (1 dari 3 foto uji), jadi hasil tetap saran yang dicek admin.
MIN_COVERAGE = 0.25      # fraksi keliling yang benar-benar kena tepi kuat


@dataclass
class Candidate:
    cx: float
    cy: float
    r: float
    score: float
    edge: float


def resize_for_detection(img: np.ndarray, max_side: int = MAX_SIDE) -> np.ndarray:
    h, w = img.shape[:2]
    m = max(h, w)
    if m <= max_side:
        return img
    f = max_side / m
    return cv2.resize(img, (round(w * f), round(h * f)), interpolation=cv2.INTER_AREA)


def gradient_mag(gray: np.ndarray) -> np.ndarray:
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def edge_support(mag: np.ndarray, cx: float, cy: float, r: float, n: int = 180) -> float:
    """Rerata magnitudo gradien di sepanjang lingkaran, dinormalisasi ke 0..1."""
    h, w = mag.shape
    vals = []
    for t in np.linspace(0, 2 * math.pi, n, endpoint=False):
        x = round(cx + r * math.cos(t))
        y = round(cy + r * math.sin(t))
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


def coverage(mag: np.ndarray, cx: float, cy: float, r: float, n: int = 360,
             tol: float = 0.03) -> float:
    """Fraksi keliling yang benar-benar kena tepi kuat.

    Sudut yang sampelnya keluar frame tidak dihitung, bukan dianggap "tanpa tepi", supaya
    koin yang terpotong tepi foto tidak dihukum dua kali.
    """
    h, w = mag.shape
    angles = np.linspace(0, 2 * math.pi, n, endpoint=False)
    radii = np.linspace(r * (1 - tol), r * (1 + tol), 5, dtype=np.float32)
    xs = (cx + np.cos(angles)[:, None] * radii[None, :]).astype(np.float32)
    ys = (cy + np.sin(angles)[:, None] * radii[None, :]).astype(np.float32)
    inside = (xs >= 1) & (xs < w - 1) & (ys >= 1) & (ys < h - 1)
    samp = cv2.remap(mag, xs, ys, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    samp = np.where(inside, samp, 0.0)
    vals = samp.max(axis=1)
    usable = inside.any(axis=1)
    if usable.sum() < 45:
        return 0.0
    thr = max(0.45 * float(np.percentile(vals[usable], 90)), 55.0)
    strong = usable & (vals >= thr)
    return float(strong.sum() / usable.sum())


def refine_circle(mag: np.ndarray, cx: float, cy: float, r: float) -> tuple[float, float, float]:
    """Perbaiki lingkaran Hough dengan menelusuri puncak gradien radial di 360 sudut."""
    angles = np.linspace(0, 2 * math.pi, 360, endpoint=False)
    radii = np.arange(max(3.0, r * 0.85), r * 1.15, 0.4, dtype=np.float32)
    xs = (cx + np.cos(angles)[:, None] * radii[None, :]).astype(np.float32)
    ys = (cy + np.sin(angles)[:, None] * radii[None, :]).astype(np.float32)
    samp = cv2.remap(mag, xs, ys, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

    # Puncak paling LUAR per sudut (rim koin), bukan puncak global (bisa cincin dekoratif).
    peak_val = samp.max(axis=1)
    mask = samp >= (0.62 * peak_val)[:, None]
    idx = np.where(mask, np.arange(samp.shape[1])[None, :], -1).max(axis=1)
    ok = idx > 0
    idx = np.where(ok, idx, 0)

    # Sub-piksel: parabola lewat 3 sampel di sekitar puncak.
    i0 = np.clip(idx - 1, 0, samp.shape[1] - 1)
    i2 = np.clip(idx + 1, 0, samp.shape[1] - 1)
    rows = np.arange(len(angles))
    y0, y1, y2 = samp[rows, i0], samp[rows, idx], samp[rows, i2]
    denom = y0 - 2 * y1 + y2
    with np.errstate(divide="ignore", invalid="ignore"):
        delta = np.where(np.abs(denom) > 1e-3, 0.5 * (y0 - y2) / denom, 0.0)
    delta = np.nan_to_num(delta, nan=0.0, posinf=0.0, neginf=0.0)
    step = float(radii[1] - radii[0]) if len(radii) > 1 else 1.0
    rr = radii[idx] + np.clip(delta, -0.5, 0.5).astype(np.float32) * step

    keep = ok & (peak_val >= np.percentile(peak_val[ok], 40) if ok.any() else ok)
    if keep.sum() < 30:
        return cx, cy, r

    px = (cx + np.cos(angles) * rr)[keep]
    py = (cy + np.sin(angles) * rr)[keep]

    # Kasa algebraic circle fit
    a = np.column_stack([px, py, np.ones_like(px)])
    b = px ** 2 + py ** 2
    sol, *_ = np.linalg.lstsq(a, b, rcond=None)
    ncx, ncy = sol[0] / 2, sol[1] / 2
    nr = math.sqrt(max(1e-6, sol[2] + ncx ** 2 + ncy ** 2))

    # Jangan menerima "perbaikan" yang liar. Hough meleset sampai ~6%, jadi 10% cukup lega;
    # lebih dari itu artinya tidak ada tepi yang jelas dan usulan awal lebih jujur.
    if not (0.9 * r <= nr <= 1.1 * r) or math.hypot(ncx - cx, ncy - cy) > 0.15 * r:
        return cx, cy, r
    return float(ncx), float(ncy), float(nr)


def detect_coin(img: np.ndarray) -> tuple[Candidate | None, list[Candidate]]:
    """Cari koin patokan. Mengembalikan kandidat terbaik (atau None) dan alternatifnya."""
    small = resize_for_detection(img)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.medianBlur(gray, 5)

    h, w = gray.shape
    # HOUGH_GRADIENT_ALT: 10-100x lebih cepat pada foto asli bertekstur (akumulator 3D-nya
    # jauh lebih kecil) dan langsung presisi. Dengan HOUGH_GRADIENT biasa, satu foto pemilik
    # bisa butuh 16-139 detik dan tetap salah kunci; ALT 75-110 ms.
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT_ALT,
        dp=1.5,
        minDist=min(h, w) * 0.10,
        param1=300,
        param2=0.80,
        minRadius=int(min(h, w) * MIN_RADIUS_FRAC),
        maxRadius=int(min(h, w) * 0.5),
    )

    mag = gradient_mag(gray)
    cands: list[Candidate] = []
    if circles is not None:
        for cx, cy, r in np.round(circles[0], 1)[:8]:
            cx, cy, r = refine_circle(mag, float(cx), float(cy), float(r))
            e = edge_support(mag, cx, cy, r)
            c = contrast(gray, cx, cy, r)
            if (cx - r < 0.01 * w or cx + r > 0.99 * w
                    or cy - r < 0.01 * h or cy + r > 0.99 * h):
                continue  # koin menyentuh tepi foto: kelilingnya tidak utuh, skala tak bisa dipercaya
            cov = coverage(mag, cx, cy, r)
            if cov < MIN_COVERAGE:
                continue  # kelilingnya nyaris tanpa tepi: bukan benda bulat
            score = 0.45 * cov + 0.30 * e + 0.25 * c
            cands.append(Candidate(float(cx), float(cy), float(r), float(score), e))

    cands.sort(key=lambda k: k.score, reverse=True)
    best = cands[0] if cands and cands[0].score >= MIN_SCORE else None
    return best, cands
