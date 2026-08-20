import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from informasi.models import NasehatdanHadist


class Command(BaseCommand):
    help = "Impor 50 hadis sahih bertema motivasi kerja (aman dijalankan berulang kali)."

    def handle(self, *args, **options):
        csv_path = Path(__file__).resolve().parents[2] / "data" / "hadist_motivasi_pegawai.csv"
        dibuat = 0
        sudah_ada = 0

        with csv_path.open(encoding="utf-8-sig", newline="") as csv_file:
            for row in csv.DictReader(csv_file):
                _, created = NasehatdanHadist.objects.get_or_create(
                    hadist=row["hadist"].strip(),
                    author_perawi=row["author_perawi"].strip(),
                )
                if created:
                    dibuat += 1
                else:
                    sudah_ada += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Impor selesai: {dibuat} dibuat, {sudah_ada} sudah ada."
            )
        )
