"""Tabel diameter resmi koin Rupiah.

Dipakai sebagai patokan skala: skala (px/mm) = diameter_px / diameter_mm.
Sumber: `referensi_diameter_koin.csv` dari paket data pemilik (Peraturan Bank Indonesia),
bukan lagi Wikipedia. Seri berbeda punya diameter berbeda: Rp500 TE2003 27,00 mm sedangkan
TE2016 27,20 mm, jadi memakai satu angka untuk semua seri = galat sistematis ~0,7%.

`COINS` memakai satu angka per nominal untuk API yang hanya tahu nominal; untuk Rp500 dipakai
nilai tengah 27,10 mm (emisi sering tidak terbaca di foto) dan `SERIES` menyimpan angka resmi
per seri kalau nanti jenis koin dipilih lebih spesifik.
"""

COINS = {
    "50": {"diameter_mm": 20.00, "thickness_mm": 2.00, "mass_g": 1.36, "years": [1999]},
    "100": {"diameter_mm": 23.00, "thickness_mm": 2.00, "mass_g": 1.79, "years": [1999, 2016]},
    "200": {"diameter_mm": 25.00, "thickness_mm": 2.20, "mass_g": 2.38, "years": [2003, 2016]},
    "500": {"diameter_mm": 27.10, "thickness_mm": 2.35, "mass_g": 3.10, "years": [2003, 2016]},
    "1000": {"diameter_mm": 24.10, "thickness_mm": 1.45, "mass_g": 4.50, "years": [2010, 2016]},
}

# Diameter resmi per seri (dari tabel pemilik) untuk pemakaian yang lebih teliti.
SERIES = {
    "500-2003": 27.00,
    "500-2016": 27.20,
    "200-2003": 25.00,
    "200-2016": 25.00,
    "100-2016": 23.00,
    "1000-2016": 24.10,
}

# Koin yang ukurannya terlalu berdekatan untuk dibedakan dari diameter saja.
AMBIGUOUS_PAIRS = [("1000", "200")]  # 24,1 mm vs 25,0 mm -> selisih <1 mm
