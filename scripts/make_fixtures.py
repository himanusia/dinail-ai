"""Bangun fixtures uji.

Dua jenis data:
1. Scene sintetis ber-ground-truth eksak: koin digambar sebagai lingkaran ber-radius R
   (tepi tajam, tekstur foto koin domain publik di dalamnya). Karena radiusnya digambar
   langsung, skala sebenarnya diketahui persis dan error pengukuran bisa dihitung.
2. Foto koin asli domain publik (Wikimedia Commons) untuk uji ketahanan detektor,
   bukan uji akurasi (diameternya tidak diketahui dari piksel saja).

Sumber foto (domain publik): 500/200/100/1000 rupiah coin obverse, Wikimedia Commons.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
COIN_URLS = {
    "500": "https://upload.wikimedia.org/wikipedia/commons/1/12/500_rupiah_coin_obverse.jpg",
    "100": "https://upload.wikimedia.org/wikipedia/commons/0/08/100_rupiah_coin_obverse.jpg",
    "1000": "https://upload.wikimedia.org/wikipedia/commons/f/fb/1000_rupiah_coin_obverse.jpg",
    "200": "https://upload.wikimedia.org/wikipedia/commons/4/43/200_rupiah_coin_obverse.jpg",
}
UA = {"User-Agent": "dinail-ai-fixtures/1.0 (capstone; non-commercial)"}


def fetch() -> dict[str, Path]:
    FIX.mkdir(exist_ok=True)
    out = {}
    for denom, url in COIN_URLS.items():
        p = FIX / f"coin_{denom}.jpg"
        if not p.exists():
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                p.write_bytes(resp.read())
        out[denom] = p
    return out


def _table_texture(seed: int, h: int, w: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = np.array([208, 214, 221], np.float32)  # BGR, meja terang
    grain = rng.normal(0, 5, (h // 8, w // 8, 3)).astype(np.float32)
    grain = cv2.resize(grain, (w, h), interpolation=cv2.INTER_CUBIC)
    img = np.clip(base + grain, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(img, (0, 0), 2)


def coin_crop(coin_path: Path) -> np.ndarray:
    """Potong foto koin tepat di tepi luarnya, supaya margin putih di foto tidak ikut
    masuk dan tepi koin di scene = tepi yang digambar (ground truth eksak)."""
    sys.path.insert(0, str(ROOT))
    from dinail_ai import detect

    cache = FIX / f"crop_{coin_path.stem}.png"
    if cache.exists():
        return cv2.imread(str(cache))

    src = cv2.imread(str(coin_path))
    h, w = src.shape[:2]
    s = min(1.0, 1100.0 / max(h, w))
    small = cv2.resize(src, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1.0 else src
    g = cv2.medianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), 7)
    hs, _ws = g.shape
    circles = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT, dp=1.1, minDist=hs * 0.5, param1=110,
                               param2=50, minRadius=int(hs * 0.25), maxRadius=int(hs * 0.60))
    if circles is None:
        raise RuntimeError(f"koin referensi tidak terdeteksi: {coin_path.name}")
    cx, cy, r = [float(v) for v in np.round(circles[0], 1)[0]]
    cx, cy, r = detect.refine_circle(detect.gradient_mag(g), cx, cy, r)
    cx, cy, r = cx / s, cy / s, r / s

    x0, y0 = round(cx - r), round(cy - r)
    side = round(2 * r)
    x0 = max(0, min(x0, w - side))
    y0 = max(0, min(y0, h - side))
    crop = src[y0:y0 + side, x0:x0 + side]
    cv2.imwrite(str(cache), crop)
    return crop


def make_scene(coin_path: Path, d_mm: float, px_per_mm: float, nail_mm: float, seed: int,
               size=(1200, 1600)) -> np.ndarray:
    """Koin = lingkaran radius d_mm*px_per_mm/2 (ground truth eksak)."""
    rng = np.random.default_rng(seed)
    H, W = size
    bg = _table_texture(seed, H, W)

    R = d_mm * px_per_mm / 2.0
    D = round(2 * R)
    coin = cv2.resize(coin_crop(coin_path), (D, D), interpolation=cv2.INTER_AREA)

    mask = np.zeros((D, D), np.uint8)
    cv2.circle(mask, (D // 2, D // 2), round(R), 255, -1)
    mask_f = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), 0.8)[..., None]

    cx, cy = int(W * 0.70), int(H * 0.45)
    x0, y0 = cx - D // 2, cy - D // 2
    roi = bg[y0:y0 + D, x0:x0 + D].astype(np.float32)
    bg[y0:y0 + D, x0:x0 + D] = np.clip(coin * mask_f + roi * (1 - mask_f), 0, 255).astype(np.uint8)

    # bayangan lembut di bawah koin supaya tidak "tempelan"
    shadow = np.zeros((H, W), np.float32)
    cv2.ellipse(shadow, (cx, cy + int(R * 0.55)), (int(R * 1.05), int(R * 0.55)), 0, 0, 360, 1.0, -1)
    shadow = cv2.GaussianBlur(shadow, (0, 0), R * 0.25)
    bg = np.clip(bg.astype(np.float32) * (1 - 0.18 * shadow[..., None]), 0, 255).astype(np.uint8)

    # "kuku" berlebar nail_mm (ground truth eksak)
    w_px = round(nail_mm * px_per_mm)
    h_px = round(w_px * 1.45)
    nx, ny = int(W * 0.20), int(H * 0.36)
    color = (198, 186, 214)
    cv2.rectangle(bg, (nx, ny), (nx + w_px, ny + h_px), color, -1)
    cv2.ellipse(bg, (nx + w_px // 2, ny), (w_px // 2, max(4, int(h_px * 0.22))), 0, 180, 360, color, -1)
    bg = cv2.GaussianBlur(bg, (0, 0), 0.7)
    out = np.clip(bg.astype(np.float32) + rng.normal(0, 2.5, bg.shape), 0, 255).astype(np.uint8)
    return out, R, w_px


def main() -> int:
    coins = fetch()
    truth = []
    cases = [
        ("g1_500", "500", 27.0, 6.0, 11.5, 1),
        ("g2_500", "500", 27.0, 9.0, 13.2, 2),
        ("g3_1000", "1000", 24.0, 7.5, 14.0, 3),
        ("g4_200", "200", 25.0, 12.0, 15.5, 4),
        ("g5_100", "100", 23.0, 4.5, 10.4, 5),
        ("g6_1000", "1000", 24.0, 14.0, 16.8, 6),
    ]
    for name, denom, d_mm, ppm, nail_mm, seed in cases:
        img, R, w_px = make_scene(coins[denom], d_mm, ppm, nail_mm, seed)
        p = FIX / f"{name}.jpg"
        cv2.imwrite(str(p), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        truth.append({
            "file": p.name,
            "coin": denom,
            "diameter_mm": d_mm,
            "px_per_mm": ppm,
            "true_diameter_px": round(2 * R, 1),
            "nail_width_mm": nail_mm,
            "true_nail_width_px": w_px,
        })
        print("wrote", p.name, img.shape, "d_px", round(2 * R, 1))

    # kasus negatif
    img = cv2.imread(str(FIX / "g1_500.jpg"))
    cv2.imwrite(str(FIX / "bad_blur.jpg"), cv2.GaussianBlur(img, (0, 0), 14))
    cv2.imwrite(str(FIX / "bad_dark.jpg"), (img * 0.12).astype(np.uint8))
    cv2.imwrite(str(FIX / "bad_small.jpg"), cv2.resize(img, (480, 360)))
    plain = cv2.GaussianBlur(np.full_like(img, 205), (0, 0), 3)
    cv2.imwrite(str(FIX / "bad_nocoin.jpg"), plain)

    (FIX / "ground_truth.json").write_text(json.dumps(truth, indent=2), encoding="utf-8")
    print(json.dumps(truth, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
