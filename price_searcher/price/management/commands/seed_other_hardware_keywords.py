"""
Seed Keyword rows for CPU, RAM, SSD, Motherboard with Japanese Rakuten-friendly search terms.
Run: python manage.py seed_other_hardware_keywords --category=cpu
     python manage.py seed_other_hardware_keywords --category=all
Category: cpu, ram, ssd, motherboard, all.
"""
from django.core.management.base import BaseCommand
from price.models import Keyword

CPU_KEYWORDS = [
    # Intel 12th gen
    "Core i3-12100",
    "Core i3-12100F",
    # Intel 13th gen
    "Core i3-13100",
    "Core i5-13400F",
    "Core i5-13600K",
    "Core i7-13700K",
    "Core i9-13900K",
    # Intel 14th gen
    "Core i3-14100",
    "Core i5-14400F",
    "Core i5-14600K",
    "Core i7-14700K",
    "Core i9-14900K",
    # Intel Core Ultra
    "Core Ultra 5 225F",
    "Core Ultra 7 265K",
    "Core Ultra 9 285K",
    # AMD Ryzen 5000
    "Ryzen 5 5500",
    "Ryzen 5 5600",
    "Ryzen 5 5600X",
    # AMD Ryzen 7000
    "Ryzen 5 7500F",
    "Ryzen 5 7600",
    "Ryzen 5 7600X",
    "Ryzen 7 7700",
    "Ryzen 7 7700X",
    "Ryzen 7 7800X3D",
    "Ryzen 9 7900X",
    "Ryzen 9 7950X",
    # AMD Ryzen 9000
    "Ryzen 5 9600X",
    "Ryzen 7 9700X",
    "Ryzen 7 9800X3D",
    "Ryzen 9 9900X",
    "Ryzen 9 9950X",
]

RAM_KEYWORDS = [
    # DDR5 容量別
    "DDR5 メモリ 16GB",
    "DDR5 メモリ 32GB",
    "DDR5 メモリ 48GB",
    "DDR5 メモリ 64GB",
    # ブランド別
    "Corsair Vengeance DDR5",
    "Corsair Dominator DDR5",
    "Kingston Fury Beast DDR5",
    "Kingston Fury Renegade DDR5",
    "Crucial Pro DDR5",
    "G.Skill Trident Z5",
    "G.Skill Trident Z5 Neo",
    "T-Force Delta DDR5",
    # DDR4 (まだ需要あり)
    "DDR4 メモリ 16GB",
    "DDR4 メモリ 32GB",
]

SSD_KEYWORDS = [
    # Samsung
    "Samsung 980 Pro SSD",
    "Samsung 990 Evo SSD",
    "Samsung 990 Pro SSD",
    # WD
    "WD Blue SN570 SSD",
    "WD Black SN770 SSD",
    "WD Black SN850X SSD",
    # Crucial
    "Crucial P3 SSD",
    "Crucial T500 SSD",
    "Crucial T700 SSD",
    # Kingston
    "Kingston KC3000 SSD",
    "Kingston NV2 SSD",
    # その他
    "Solidigm P44 Pro SSD",
    "Corsair MP700 SSD",
    "MSI Spatium M570 SSD",
    # 容量別
    "NVMe SSD 1TB",
    "NVMe SSD 2TB",
    "NVMe SSD 4TB",
]

MOTHERBOARD_KEYWORDS = [
    # Intel - エントリー～ミドル
    "マザーボード H610",
    "マザーボード H710",
    "マザーボード B660",
    "マザーボード B760",
    "マザーボード B760M",
    "マザーボード B860",
    # Intel - ハイエンド
    "マザーボード Z690",
    "マザーボード Z790",
    "マザーボード Z890",
    # AMD - エントリー～ミドル
    "マザーボード A620",
    "マザーボード B650",
    "マザーボード B650E",
    # AMD - ハイエンド
    "マザーボード X670",
    "マザーボード X670E",
    "マザーボード X870",
    "マザーボード X870E",
]

CATEGORY_MAP = {
    "cpu": (Keyword.CATEGORY_CPU, CPU_KEYWORDS),
    "ram": (Keyword.CATEGORY_RAM, RAM_KEYWORDS),
    "ssd": (Keyword.CATEGORY_SSD, SSD_KEYWORDS),
    "motherboard": (Keyword.CATEGORY_MOTHERBOARD, MOTHERBOARD_KEYWORDS),
}


class Command(BaseCommand):
    help = "Seed keywords for CPU/RAM/SSD/Motherboard with Japanese Rakuten-friendly search terms."

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            type=str,
            choices=["cpu", "ram", "ssd", "motherboard", "all"],
            required=True,
        )

    def handle(self, *args, **options):
        cat = options["category"]
        categories = CATEGORY_MAP.keys() if cat == "all" else [cat]

        total_created = 0
        for c in categories:
            kw_category, keyword_list = CATEGORY_MAP[c]
            created = 0
            for name in keyword_list:
                _, was_created = Keyword.objects.get_or_create(
                    name=name,
                    defaults={"category": kw_category},
                )
                if was_created:
                    created += 1
                    self.stdout.write(f"  + {name}")
            already = len(keyword_list) - created
            self.stdout.write(self.style.SUCCESS(
                f"  {c.upper()}: {created} new, {already} already existed ({len(keyword_list)} total)"
            ))
            total_created += created

        self.stdout.write(self.style.SUCCESS(f"Done. Added {total_created} new keywords."))
