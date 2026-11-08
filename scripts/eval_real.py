"""Evaluasi detektor pada foto asli pemilik (paket data dinail.co) — bukan foto publik.

Paket data tidak masuk repo (berisi tangan pelanggan). Skrip ini hanya membaca di lokal dan
menulis laporan agregat: tingkat deteksi + selisih diameter koin terhadap ukuran yang diukur
manual oleh tim DS di `metadata_foto.csv`.

Pakai:
    python scripts/eval_real.py --data-dir ~/Downloads/dinail_data_siap_pakai --out eval
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dinail_ai import quality
from dinail_ai.analyze import decode_image
from dinail_ai.detect import detect_coin


def load_rows(data_dir: Path) -> list[dict]:
    meta = data_dir / "02_foto_ukuran" / "metadata_foto.csv"
    with meta.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", default="eval")
    args = ap.parse_args()

    data_dir = Path(args.data_dir).expanduser()
    rows = load_rows(data_dir)
    foto_dir = data_dir / "02_foto_ukuran" / "foto"

    results = []
    for row in rows:
        path = foto_dir / Path(row["file"]).name
        if not path.exists():
            continue
        data = path.read_bytes()
        img = decode_image(data)

        gt_d_px = float(row["koin_diameter_px"])
        gt_ppm = float(row["piksel_per_mm"])
        coin_series = row["koin_utama"].strip()

        best, _ = detect_coin(img)
        det_d_px = 2 * best.r if best else None
        m = quality.metrics(img)

        reasons = quality.gate(m, (det_d_px / 2) if det_d_px else None)
        err = None
        if det_d_px:
            err = (det_d_px - gt_d_px) / gt_d_px

        results.append({
            "id": row["id_foto"],
            "group": row["id_grup"],
            "jenis": row["jenis_foto"],
            "koin": coin_series,
            "gt_diameter_px": gt_d_px,
            "gt_px_per_mm": gt_ppm,
            "det_diameter_px": None if not det_d_px else round(det_d_px, 1),
            "det_px_per_mm_500": None if not det_d_px else round(det_d_px / 27.2, 3),
            "rel_error": None if err is None else round(err, 4),
            "score": None if not best else round(best.score, 3),
            "sharpness": m["sharpness"],
            "min_side": m["min_side"],
            "status_ds": row["status_kualitas_awal"],
            "catatan": row["catatan"],
            "ditolak_gate": reasons,
        })

    detected = [r for r in results if r["det_diameter_px"]]
    errs = [abs(r["rel_error"]) for r in detected]

    summary = {
        "n_foto": len(results),
        "terdeteksi": len(detected),
        "tingkat_deteksi": round(len(detected) / max(len(results), 1), 3),
        "median_abs_error_diameter": round(statistics.median(errs), 4) if errs else None,
        "p90_abs_error_diameter": round(sorted(errs)[int(0.9 * (len(errs) - 1))], 4) if errs else None,
        "maks_abs_error_diameter": round(max(errs), 4) if errs else None,
        "dalam_2persen": sum(1 for e in errs if e <= 0.02),
        "gagal_deteksi": [r["id"] for r in results if not r["det_diameter_px"]],
    }

    out = Path(args.out)
    out.mkdir(exist_ok=True)
    (out / "report.json").write_text(json.dumps({"summary": summary, "rows": results}, indent=2),
                                     encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print("\nselisih per foto (urut terburuk):")
    for r in sorted(detected, key=lambda x: -abs(x["rel_error"]))[:8]:
        print(f"  {r['id']} {r['jenis']:11s} {r['koin']:16s} gt={r['gt_diameter_px']:6.1f} "
              f"det={r['det_diameter_px']:6.1f} err={r['rel_error']*100:+6.2f}%")
    print("\nyang tidak terdeteksi:")
    for r in results:
        if not r["det_diameter_px"]:
            print(f"  {r['id']} {r['jenis']:11s} min_side={r['min_side']} sharp={r['sharpness']} "
                  f"| {r['ditolak_gate'][:1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
