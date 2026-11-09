"""Buat foto contoh + gambar hasil anotasi untuk README (ikut di-commit, bukan fixture uji).

Tiga kelompok:
1. samples/asli/    foto asli pemilik (jempol + empat jari dengan koin Rp500), EXIF dihapus,
                    dipakai dengan izin pemilik. Butuh --data-dir ke paket data pemilik.
2. samples/real/    foto tangan CC BY 2.0 sebagai uji negatif.
3. samples/contoh-* scene sintetis ber-ground-truth untuk uji geometri.

Pakai:
    python scripts/make_samples.py --data-dir ~/Downloads/dinail_data_siap_pakai
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dinail_ai.analyze import analyze

FIX = ROOT / "fixtures"
OUT = ROOT / "samples"
REAL = OUT / "real"

REAL_CASES = [
    ("real-hand-coin", "tangan-koin-emas.jpg", "Koin dipegang tangan, tidak datar"),
    ("real-hand-coin2", "tangan-koin-kecil.jpg", "Koin kecil di jari, bukan patokan"),
    ("real-hand-ruler", "tangan-penggaris.jpg", "Tangan di penggaris, tanpa koin"),
]

# Foto pemilik yang dipakai di README: grup S01 (berlabel ukuran), koin Rp500 27,10 mm.
ASLI_CASES = [
    ("jempol-koin-500", "FOTO_027.jpg", "500", "Jempol + koin Rp500"),
    ("empat-jari-koin-500", "FOTO_028.jpg", "500", "Empat jari + koin Rp500"),
]

CASES = [
    ("contoh-01-layak", "g2_500.jpg", "500", 118.8, "Foto layak, koin Rp500"),
    ("contoh-02-buram", "bad_blur.jpg", "500", None, "Foto buram"),
    ("contoh-03-koin-kecil", "g5_100.jpg", "100", None, "Koin terlalu kecil di foto"),
    ("contoh-04-tanpa-jenis-koin", "g4_200.jpg", None, 186.0, "Jenis koin tidak dipilih"),
]


def annotate(img: np.ndarray, res, title: str, object_label: str = "objek uji") -> np.ndarray:
    out = img.copy()
    ok = res.ok
    color = (60, 150, 60) if ok else (40, 60, 200)

    if res.coin and "center_px" in res.coin:
        cx, cy = [int(v) for v in res.coin["center_px"]]
        r = int(res.coin["radius_px"])
        cv2.circle(out, (cx, cy), r, color, 3)
        cv2.drawMarker(out, (cx, cy), color, cv2.MARKER_CROSS, 26, 2)
        label = f"koin Rp{res.coin.get('type')} - {res.coin.get('diameter_mm')} mm"
        cv2.putText(out, label, (cx - r, cy - r - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    if res.nail:
        w_px = int(res.nail["width_px"])
        y = int(img.shape[0] * 0.36) + 10
        x0, x1 = int(img.shape[1] * 0.20), int(img.shape[1] * 0.20) + w_px
        cv2.line(out, (x0, y), (x1, y), (30, 30, 200), 3)
        for x in (x0, x1):
            cv2.line(out, (x, y - 12), (x, y + 12), (30, 30, 200), 3)
        cv2.putText(out, f"{res.nail['width_mm']} mm ({object_label})", (x0, y - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (30, 30, 200), 2)

    if res.scale_px_per_mm:
        text = f"skala {res.scale_px_per_mm:.2f} px/mm"
        (tw, _th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(out, (24, img.shape[0] - 72), (36 + tw, img.shape[0] - 44), (0, 0, 0), -1)
        cv2.putText(out, text, (30, img.shape[0] - 52),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    verdict = "LOLOS" if ok else "DITOLAK"
    cv2.rectangle(out, (0, 0), (img.shape[1], 54), (0, 0, 0), -1)
    cv2.putText(out, f"{verdict} - {title}", (16, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                color, 2)
    if not ok and res.quality["reasons"]:
        reason = res.quality["reasons"][0]
        cv2.putText(out, reason[:110], (16, img.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
    return out


def read_clean(path: Path) -> np.ndarray:
    """Baca lalu tulis ulang tanpa EXIF: foto pemilik tidak membawa metadata kamera/GPS."""
    img = cv2.imread(str(path))
    if img is None:
        raise SystemExit(f"tidak bisa membaca {path}")
    return img


def emit_asli(data_dir: Path) -> None:
    src_dir = data_dir / "02_foto_ukuran" / "foto"
    out = OUT / "asli"
    out.mkdir(exist_ok=True)
    for name, src, coin, title in ASLI_CASES:
        img = read_clean(src_dir / src)
        h, w = img.shape[:2]
        if max(h, w) > 1280:
            f = 1280 / max(h, w)
            img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        # imwrite menulis JPEG baru: EXIF (GPS, model kamera, waktu) tidak ikut
        cv2.imwrite(str(out / f"{name}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])

        res = analyze((out / f"{name}.jpg").read_bytes(), coin=coin)
        annotated = annotate(img, res, title, "lebar kuku (input UI)")
        cv2.imwrite(str(out / f"hasil-{name}.jpg"), annotated, [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(f"{name}: ok={res.ok} koin={bool(res.coin)} skala={res.scale_px_per_mm} "
              f"| {res.quality['reasons'][:1]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", help="paket data pemilik (berisi 02_foto_ukuran/foto)")
    args = ap.parse_args()

    if args.data_dir:
        emit_asli(Path(args.data_dir).expanduser())

    if not (FIX / "ground_truth.json").exists():
        print("fixtures belum ada: jalankan scripts/make_fixtures.py dulu", file=sys.stderr)
        return 1
    OUT.mkdir(exist_ok=True)

    for name, src, coin, nail_px, title in CASES:
        src_path = FIX / src
        if not src_path.exists():
            print(f"lewat: {src} tidak ada", file=sys.stderr)
            continue
        data = src_path.read_bytes()
        res = analyze(data, coin=coin, nail_width_px=nail_px)

        shutil.copyfile(src_path, OUT / f"{name}.jpg")
        # scene sintetis: objeknya kotak pengganti kuku, jangan diberi label "kuku"
        annotated = annotate(cv2.imread(str(src_path)), res,
                             f"{title} (scene sintetis, bukan kuku)", "objek uji")
        cv2.imwrite(str(OUT / f"hasil-{name.split('-', 2)[2]}.jpg"), annotated,
                    [cv2.IMWRITE_JPEG_QUALITY, 88])

        print(f"{name}: ok={res.ok} scale={res.scale_px_per_mm} reasons={res.quality['reasons']}")

    for name, src, title in REAL_CASES:
        src_path = REAL / src
        if not src_path.exists():
            print(f"lewat: {src_path} tidak ada", file=sys.stderr)
            continue
        res = analyze(src_path.read_bytes(), coin="500")
        annotated = annotate(cv2.imread(str(src_path)), res, title)
        out_path = REAL / f"hasil-{name}.jpg"
        cv2.imwrite(str(out_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(f"{name}: ok={res.ok} reasons={res.quality['reasons'][:1]} -> {out_path.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
