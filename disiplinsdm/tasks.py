from .services import BridgeSyncService

def task_auto_sync_presence():
    # Ambil data yang tersisa (unsynced) secara berkala
    data = BridgeSyncService.fetch_from_bridge(limit=1000)
    BridgeSyncService.run_total_sync(data)