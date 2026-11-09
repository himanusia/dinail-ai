"""Orkestrasi satu foto: gerbang kualitas, skala dari koin, konversi lebar kuku."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dinail_ai.analyze import analyze

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
CASE = "g2_500.jpg"
TOL_SCALE = 0.02      # 2% error skala
TOL_WIDTH_MM = 0.35   # jauh di bawah 1 nomor ukuran (~1 mm)
TOO_SMALL = {"g5_100.jpg"}


def truth() -> list[dict]:
    p = FIX / "ground_truth.json"
    if not p.exists():
        pytest.skip("fixtures belum dibuat: jalankan scripts/make_fixtures.py")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def case() -> dict:
    return next(c for c in truth() if c["file"] == CASE)


@pytest.mark.parametrize("case", [c for c in truth() if c["file"] not in TOO_SMALL],
                         ids=lambda c: c["file"])
def test_scale_and_width_accuracy(case):
    data = (FIX / case["file"]).read_bytes()
    res = analyze(data, coin=case["coin"], nail_width_px=case["nail_width_mm"] * case["px_per_mm"])

    assert res.quality["pass"], res.quality["reasons"]
    err = abs(res.scale_px_per_mm - case["px_per_mm"]) / case["px_per_mm"]
    assert err <= TOL_SCALE, f"skala {res.scale_px_per_mm:.2f} vs {case['px_per_mm']} px/mm (err {err:.2%})"

    assert abs(res.nail["width_mm"] - case["nail_width_mm"]) <= TOL_WIDTH_MM
    assert res.nail["suggestion"]["needs_admin_check"] is True


def test_small_coin_rejected_with_reason():
    case = next(c for c in truth() if c["file"] in TOO_SMALL)
    res = analyze((FIX / case["file"]).read_bytes(), coin=case["coin"])
    assert not res.ok
    assert any("terlalu kecil" in r.lower() for r in res.quality["reasons"]), res.quality["reasons"]


def test_scale_comes_from_declared_coin(case):
    res = analyze((FIX / CASE).read_bytes(), coin="500")
    assert res.ok
    assert res.coin["diameter_mm"] == 27.10
    assert "source" not in res.coin  # terdeteksi dari foto, bukan input manual


def test_manual_coin_diameter_override(case):
    """Jalur admin: kalau deteksi gagal, diameter koin bisa diisi manual."""
    res = analyze((FIX / CASE).read_bytes(), coin="500", coin_diameter_px=case["true_diameter_px"])
    assert res.ok
    assert res.coin["source"] == "manual"
    assert abs(res.scale_px_per_mm - case["px_per_mm"]) / case["px_per_mm"] <= TOL_SCALE


def test_coin_type_parsing_accepts_common_forms():
    for form in ("500", "Rp500", "Rp.500", " 500 "):
        assert analyze((FIX / CASE).read_bytes(), coin=form).coin["type"] == "500"


def test_unknown_coin_value_is_reported(case):
    res = analyze((FIX / CASE).read_bytes(), coin="2000")
    assert not res.ok
    assert any("tidak dikenal" in r for r in res.quality["reasons"])


def test_ambiguous_denomination_warns(case):
    res = analyze((FIX / CASE).read_bytes(), coin="200")
    assert res.ok
    assert any("200" in w for w in res.warnings)


def test_nail_width_needs_scale(case):
    res = analyze((FIX / CASE).read_bytes(), nail_width_px=100.0)
    assert not res.ok
    assert any("tanpa skala" in r for r in res.quality["reasons"])


def test_nail_width_mapped_with_owner_table(case, tmp_path):
    table = tmp_path / "size_table.json"
    table.write_text(json.dumps({"sizes": [
        {"size": "S", "min_mm": 12.6, "max_mm": 14.0},
        {"size": "M", "min_mm": 14.1, "max_mm": 15.5},
    ]}), encoding="utf-8")

    res = analyze(
        (FIX / CASE).read_bytes(),
        coin="500",
        nail_width_px=case["nail_width_mm"] * case["px_per_mm"],
        size_table_path=str(table),
    )
    assert abs(res.nail["width_mm"] - case["nail_width_mm"]) <= TOL_WIDTH_MM
    assert res.nail["suggestion"]["size"] == "S"
    assert res.nail["suggestion"]["needs_admin_check"] is True
