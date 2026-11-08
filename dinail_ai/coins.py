"""Tabel diameter resmi koin Rupiah (Bank Indonesia / Wikipedia 'Uang koin rupiah').

Dipakai sebagai patokan skala: skala (px/mm) = diameter_px / diameter_mm.
Sumber: id.wikipedia.org/wiki/Uang_koin_rupiah (tabel koin beredar), diambil 2026-11-08.
CATATAN: nilai harus dikonfirmasi ke pemilik (dinail.co) saat tabel konversi ukuran diserahkan.
"""

# diameter_mm, tebal_mm, berat_g, tahun berlaku
COINS = {
    "50":   {"diameter_mm": 20.0, "thickness_mm": 2.00, "mass_g": 1.36, "years": [1999]},
    "100":  {"diameter_mm": 23.0, "thickness_mm": 2.00, "mass_g": 1.79, "years": [1999, 2016]},
    "200":  {"diameter_mm": 25.0, "thickness_mm": 2.20, "mass_g": 2.38, "years": [2003, 2016]},
    "500":  {"diameter_mm": 27.0, "thickness_mm": 2.35, "mass_g": 3.10, "years": [2003, 2016]},
    "1000": {"diameter_mm": 24.0, "thickness_mm": 1.45, "mass_g": 4.50, "years": [2010, 2016]},
}

# Koin yang ukurannya terlalu berdekatan untuk dibedakan dari diameter saja.
AMBIGUOUS_PAIRS = [("1000", "200")]  # 24 mm vs 25 mm -> selisih 1 mm
