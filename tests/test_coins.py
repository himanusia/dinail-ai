"""Tabel diameter koin: sumbernya harus jelas dan jarak antar nominal harus cukup."""

from dinail_ai.coins import AMBIGUOUS_PAIRS, COINS


def test_table_matches_official_diameters():
    assert {k: v["diameter_mm"] for k, v in COINS.items()} == {
        "50": 20.0, "100": 23.0, "200": 25.0, "500": 27.10, "1000": 24.10,
    }


def test_ambiguous_pairs_are_the_tight_ones():
    """Rp200 25 mm vs Rp1000 24 mm: selisih 1 mm, tidak bisa dibedakan dari diameter saja."""
    assert AMBIGUOUS_PAIRS == [("1000", "200")]


def test_every_coin_has_source_metadata():
    for denom, row in COINS.items():
        assert row["diameter_mm"] > 0
        assert row["thickness_mm"] > 0
        assert row["mass_g"] > 0
        assert row["years"], denom
