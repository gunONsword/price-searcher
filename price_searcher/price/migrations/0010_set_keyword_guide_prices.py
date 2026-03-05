"""
Data migration: set guide_price (JPY) for all keywords.
Prices based on Japan market, circa February 2025.

Sources:
- AKIBA PC Hotline! 2025年2月前半CPU価格調査
- AKIBA PC Hotline! 2025年2月後半SSD/メモリ価格調査
- NVIDIA GeForce RTX 50 国内発表価格 (PC Watch)
"""

from django.db import migrations

GUIDE_PRICES = {
    # GPU: NVIDIA RTX 50 series (just released Jan-Feb 2025)
    "RTX 5090 32GB":          450000,
    "RTX 5080 16GB":          250000,
    "RTX 5070 Ti 16GB":       195000,
    "RTX 5070 12GB":          115000,
    "RTX 5060 Ti 16GB":        80000,
    "RTX 5060 8GB":            52000,
    # GPU: NVIDIA RTX 40 series
    "RTX 4090 24GB":          250000,
    "RTX 4080 Super 16GB":    165000,
    "RTX 4080 16GB":          145000,
    "RTX 4070 Ti Super 16GB": 140000,
    "RTX 4070 Ti 12GB":       115000,
    "RTX 4070 Super 12GB":    100000,
    "RTX 4070 12GB":           90000,
    "RTX 4060 Ti 16GB":        75000,
    "RTX 4060 Ti 8GB":         60000,
    "RTX 4060 8GB":            45000,
    # GPU: NVIDIA RTX 30 series
    "RTX 3090 24GB":           70000,
    "RTX 3080 Ti 12GB":        50000,
    "RTX 3080 10GB":           45000,
    "RTX 3070 Ti 8GB":         38000,
    "RTX 3070 8GB":            35000,
    "RTX 3060 Ti 8GB":         28000,
    "RTX 3060 12GB":           25000,
    # GPU: AMD Radeon RX 7000
    "RX 7900 XTX 24GB":       115000,
    "RX 7900 XT 20GB":         90000,
    "RX 7800 XT 16GB":         80000,
    "RX 7700 XT 12GB":         60000,
    "RX 7600 XT 16GB":         45000,
    "RX 7600 8GB":             38000,
    # GPU: AMD Radeon RX 6000
    "RX 6900 XT 16GB":         55000,
    "RX 6800 XT 16GB":         45000,
    "RX 6800 16GB":            40000,
    "RX 6700 XT 12GB":         32000,
    "RX 6650 XT 8GB":          25000,
    "RX 6600 XT 8GB":          22000,
    "RX 6600 8GB":             20000,
    # GPU: Intel Arc
    "Arc A770 16GB":           35000,
    "Arc A750 8GB":            25000,
    "Arc A580 8GB":            22000,
    "Arc A380 6GB":            16000,
    # CPU: Intel 14th Gen
    "Core i9-14900K":          77980,
    "Core i7-14700K":          58880,
    "Core i5-14600K":          41980,
    "Core i5-14400F":          24780,
    "Core i3-14100":           19580,
    "Core i3-14100F":          13480,
    # CPU: Intel 13th Gen
    "Core i9-13900K":          62000,
    "Core i7-13700K":          48000,
    "Core i5-13600K":          35000,
    "Core i5-13400F":          20000,
    "Core i3-13100":           16000,
    # CPU: Intel 12th Gen
    "Core i3-12100":           15000,
    "Core i3-12100F":          11000,
    # CPU: Intel Core Ultra 200S
    "Core Ultra 9 285K":      115800,
    "Core Ultra 7 265K":       67800,
    "Core Ultra 5 225F":       39800,
    # CPU: AMD Ryzen 9000
    "Ryzen 9 9950X":          113800,
    "Ryzen 9 9900X":           82800,
    "Ryzen 7 9800X3D":         83800,
    "Ryzen 7 9700X":           65800,
    "Ryzen 5 9600X":           47480,
    # CPU: AMD Ryzen 7000
    "Ryzen 9 7950X":          106800,
    "Ryzen 9 7900X":           78800,
    "Ryzen 7 7800X3D":         83800,
    "Ryzen 7 7700X":           63480,
    "Ryzen 7 7700":            52000,
    "Ryzen 5 7600X":           44480,
    "Ryzen 5 7600":            36800,
    "Ryzen 5 7500F":           28000,
    # CPU: AMD Ryzen 5000
    "Ryzen 5 5600X":           28000,
    "Ryzen 5 5600":            26000,
    "Ryzen 5 5500":            15680,
    # Memory: DDR5 generic (メモリ)
    "DDR5 \u30e1\u30e2\u30ea 16GB":   9000,
    "DDR5 \u30e1\u30e2\u30ea 32GB":  18780,
    "DDR5 \u30e1\u30e2\u30ea 48GB":  20680,
    "DDR5 \u30e1\u30e2\u30ea 64GB":  48100,
    # Memory: DDR4 generic
    "DDR4 \u30e1\u30e2\u30ea 16GB":   6290,
    "DDR4 \u30e1\u30e2\u30ea 32GB":  14290,
    # Memory: brand DDR5 (32GB 2x16GB kit)
    "Corsair Dominator DDR5":          30000,
    "Corsair Vengeance DDR5":          22000,
    "Crucial Pro DDR5":                22000,
    "G.Skill Trident Z5":              28000,
    "G.Skill Trident Z5 Neo":          25000,
    "Kingston Fury Beast DDR5":        20000,
    "Kingston Fury Renegade DDR5":     24000,
    "T-Force Delta DDR5":              22000,
    # SSD (1TB reference price)
    "Samsung 980 Pro SSD":             14480,
    "Samsung 990 Evo SSD":             11680,
    "Samsung 990 Pro SSD":             19980,
    "WD Black SN850X SSD":             11600,
    "WD Black SN770 SSD":               9780,
    "WD Blue SN570 SSD":                7500,
    "Crucial P3 SSD":                   8330,
    "Crucial T500 SSD":                11480,
    "Crucial T700 SSD":                24380,
    "Kingston KC3000 SSD":             12000,
    "Kingston NV2 SSD":                 7500,
    "Solidigm P44 Pro SSD":             9500,
    "Corsair MP700 SSD":               25000,
    "MSI Spatium M570 SSD":            28000,
    "NVMe SSD 1TB":                     7770,
    "NVMe SSD 2TB":                    15660,
    "NVMe SSD 4TB":                    29800,
}

# Motherboard: match by chipset substring (order matters for B650E before B650)
MOTHERBOARD_CHIPSET_PRICES = {
    "H610":  12000,
    "H710":  14000,
    "B660":  15000,
    "B760M": 17000,
    "B760":  20000,
    "B860":  22000,
    "Z690":  28000,
    "Z790":  38000,
    "Z890":  48000,
    "A620":  12000,
    "B650E": 30000,
    "B650":  22000,
    "X670E": 52000,
    "X670":  42000,
    "X870E": 62000,
    "X870":  48000,
}


def set_guide_prices(apps, schema_editor):
    Keyword = apps.get_model("price", "Keyword")
    updates = []
    for kw in Keyword.objects.all():
        price = GUIDE_PRICES.get(kw.name)
        if price is None and kw.category == "motherboard":
            for chipset, chipset_price in MOTHERBOARD_CHIPSET_PRICES.items():
                if chipset in kw.name:
                    price = chipset_price
                    break
        if price is not None:
            kw.guide_price = price
            updates.append(kw)
    if updates:
        Keyword.objects.bulk_update(updates, ["guide_price"])


def clear_guide_prices(apps, schema_editor):
    Keyword = apps.get_model("price", "Keyword")
    Keyword.objects.update(guide_price=None)


class Migration(migrations.Migration):

    dependencies = [
        ("price", "0009_add_keyword_guide_price"),
    ]

    operations = [
        migrations.RunPython(set_guide_prices, clear_guide_prices),
    ]
