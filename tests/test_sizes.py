"""Pemetaan lebar kuku -> nomor ukuran memakai tabel milik pemilik."""

from dinail_ai.sizes import suggest_size

TABLE = {"sizes": [
    {"size": "XS", "min_mm": 10.0, "max_mm": 12.5},
    {"size": "S", "min_mm": 12.6, "max_mm": 14.0},
    {"size": "M", "min_mm": 14.1, "max_mm": 15.5},
]}


def test_maps_inside_range():
    s = suggest_size(13.3, TABLE)
    assert s["size"] == "S"
    assert s["range_mm"] == [12.6, 14.0]
    assert s["needs_admin_check"] is True


def test_flags_near_boundary():
    assert suggest_size(14.05, TABLE)["ambiguous"] is True
    assert suggest_size(13.3, TABLE)["ambiguous"] is False


def test_out_of_range_snaps_to_nearest_bucket():
    s = suggest_size(9.0, TABLE)
    assert s["size"] == "XS" and s["needs_admin_check"] is True


def test_without_owner_table_no_guess():
    s = suggest_size(13.0, None)
    assert s["size"] is None
    assert "belum diisi" in s["reason"]
    assert s["needs_admin_check"] is True
