from django.core.management.base import BaseCommand
from disiplinsdm.services import BridgeSyncService

class Command(BaseCommand):
    help = 'Sinkronisasi awal data presensi dalam jumlah besar'

    def handle(self, *args, **kwargs):
        self.stdout.write("Mengambil 500 data pertama dari Bridge...")
        data = BridgeSyncService.fetch_from_bridge(limit=500)
        synced, ignored = BridgeSyncService.run_total_sync(data)
        self.stdout.write(self.style.SUCCESS(f"Berhasil sinkronisasi {synced} data."))