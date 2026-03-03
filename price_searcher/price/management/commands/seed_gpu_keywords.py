"""
Seed mainstream GPU model keywords (with VRAM) for price tracking on Rakuten Japan.
Run once: python manage.py seed_gpu_keywords
"""
from django.core.management.base import BaseCommand
from price.models import Keyword

# Mainstream GPU search keywords with VRAM (NVIDIA, AMD, Intel)
GPU_KEYWORDS = [
    # NVIDIA RTX 50 series
    "RTX 5090 32GB",
    "RTX 5080 16GB",
    "RTX 5070 Ti 16GB",
    "RTX 5070 12GB",
    "RTX 5060 Ti 16GB",
    "RTX 5060 8GB",
    # NVIDIA RTX 40 series
    "RTX 4090 24GB",
    "RTX 4080 Super 16GB",
    "RTX 4080 16GB",
    "RTX 4070 Ti Super 16GB",
    "RTX 4070 Ti 12GB",
    "RTX 4070 Super 12GB",
    "RTX 4070 12GB",
    "RTX 4060 Ti 16GB",
    "RTX 4060 Ti 8GB",
    "RTX 4060 8GB",
    # NVIDIA RTX 30 series
    "RTX 3090 24GB",
    "RTX 3080 Ti 12GB",
    "RTX 3080 10GB",
    "RTX 3070 Ti 8GB",
    "RTX 3070 8GB",
    "RTX 3060 Ti 8GB",
    "RTX 3060 12GB",
    # AMD RX 7000 series
    "RX 7900 XTX 24GB",
    "RX 7900 XT 20GB",
    "RX 7800 XT 16GB",
    "RX 7700 XT 12GB",
    "RX 7600 XT 16GB",
    "RX 7600 8GB",
    # AMD RX 6000 series
    "RX 6900 XT 16GB",
    "RX 6800 XT 16GB",
    "RX 6800 16GB",
    "RX 6700 XT 12GB",
    "RX 6650 XT 8GB",
    "RX 6600 XT 8GB",
    "RX 6600 8GB",
    # Intel Arc
    "Arc A770 16GB",
    "Arc A750 8GB",
    "Arc A580 8GB",
    "Arc A380 6GB",
]


class Command(BaseCommand):
    help = "Add mainstream GPU model names (with VRAM) as keywords."

    def handle(self, *args, **options):
        created = 0
        for name in GPU_KEYWORDS:
            _, was_created = Keyword.objects.get_or_create(
                name=name,
                defaults={"category": Keyword.CATEGORY_GPU},
            )
            if was_created:
                created += 1
                self.stdout.write(f"  + {name}")
        self.stdout.write(self.style.SUCCESS(f"Done. Added {created} new keywords, {len(GPU_KEYWORDS) - created} already existed."))
