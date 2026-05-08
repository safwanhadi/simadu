import requests
import logging
from django.db import transaction
from django.conf import settings
from .models import MappingMesinAbsensi, LogKehadiran
from oauth2_provider.models import get_application_model

from datetime import datetime, timedelta, time
from django.utils import timezone

from .models import (
    JadwalDinasSDM, LogKehadiran, KehadiranKegiatan, 
    DaftarKegiatanPegawai, AlasanTidakHadir
)

logger = logging.getLogger(__name__)

class BridgeSyncService:
    @staticmethod
    def get_token():
        """Mendapatkan Access Token dari SIMADU OAuth2"""
        Application = get_application_model()
        try:
            app = Application.objects.get(name="Attlog_Bridge_Worker")
            token_url = f"{settings.SSO_AUTH_BASE}/o/token/"
            
            res = requests.post(
                token_url,
                data={'grant_type': 'client_credentials'},
                auth=(app.client_id, app.client_secret),
                timeout=15
            )
            res.raise_for_status()
            return res.json().get('access_token')
        except Exception as e:
            logger.error(f"Gagal mengambil token OAuth2: {e}")
            return None

    @classmethod
    def fetch_from_bridge(cls, limit=1000, pegawai_id=None, sort='desc'):
        """Mengambil data dari Flask Bridge"""
        token = cls.get_token()
        if not token:
            return []

        url = f"{settings.PRESENSI_BASE_URL}/api/v1/att-logs/unsynced"
        headers = {'Authorization': f'Bearer {token}'}
        params = {'limit': limit}
        if pegawai_id:
            params['pegawai_id'] = pegawai_id

        try:
            # Menggunakan timeout lebih lama untuk batch besar
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            logger.error(f"Gagal mengambil data dari Bridge: {e}")
            return []

    @classmethod
    def mark_synced_to_bridge(cls, log_keys):
        """Menandai status di SQLite Flask Bridge agar data tidak dikirim ulang"""
        if not log_keys:
            return

        token = cls.get_token()
        url = f"{settings.PRESENSI_BASE_URL}/api/v1/att-logs/mark-synced"
        headers = {'Authorization': f'Bearer {token}'}
        
        try:
            requests.post(url, headers=headers, json={'log_keys': log_keys}, timeout=30)
        except Exception as e:
            logger.error(f"Gagal menandai status synced di Bridge: {e}")

    @classmethod
    def fetch_unsynced_by_date(cls, date_from=None, date_to=None, page=1, limit=None, personname=None):
        token = cls.get_token()
        if not token:
            return [], {}

        url = f"{settings.PRESENSI_BASE_URL}/api/v1/att-logs/unsynced-by-date"
        headers = {'Authorization': f'Bearer {token}'}

        params = {
            'page': page,
        }
        # Jika limit dikirim (dari UI), gunakan limit tersebut. 
        # Jika None, API Flask akan menangani sesuai logic-nya.
        if limit:
            params['limit'] = limit
            
        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to
        if personname:
            params['personname'] = personname

        try:
            response = requests.get(url, headers=headers, params=params, timeout=60) # Timeout ditambah jadi 60s
            response.raise_for_status()
            res_json = response.json()
            return res_json.get('data', []), res_json.get('meta', {})
        except Exception as e:
            logger.error(f"Gagal fetch unsynced by date: {e}")
            return [], {}

    @classmethod
    def execute_sync(cls, logs_data):
        if not logs_data: return 0, 0
        
        mappings = {m.mesin_id: m for m in MappingMesinAbsensi.objects.all()}
        to_create = []
        all_keys_to_mark = [] # INI KUNCINYA: Harus menampung 1000 data
        ignored_count = 0

        for item in logs_data:
            # 1. Masukkan SEMUA log_key tanpa terkecuali
            log_key_str = f"{item['id']}_{item['datetime']}"
            all_keys_to_mark.append(log_key_str)

            mapping = mappings.get(item['id'])
            if mapping:
                to_create.append(LogKehadiran(
                    mapping=mapping,
                    datetime=item['datetime'],
                    direction=item['direction'],
                    devicename=item['devicename'],
                    personname=item['personname']
                ))
            else:
                ignored_count += 1

        # 2. Simpan data yang valid ke MariaDB SIMADU
        if to_create:
            with transaction.atomic():
                LogKehadiran.objects.bulk_create(to_create, ignore_conflicts=True)
        
        # 3. KIRIM SEMUA 1000 KEYS KE FLASK (PEMBERSIHAN MASSAL)
        # Dengan mengirim 1000 keys, Flask akan menandai semuanya sebagai 'synced' 
        # di SQLite, termasuk yang tadi statusnya 'Dilewati'.
        if all_keys_to_mark:
            cls.mark_synced_to_bridge(all_keys_to_mark)
        
        return len(to_create), ignored_count
    
    @classmethod
    def run_total_sync(cls, batch_size=1000):
        """Looping untuk menarik data secara bertahap"""
        # Pastikan batch_size adalah integer
        try:
            batch_size = int(batch_size)
        except (TypeError, ValueError):
            batch_size = 1000

        total_synced = 0
        total_ignored = 0
        
        print(f"Memulai sinkronisasi total dengan batch size: {batch_size}...")
        
        while True:
            # Ambil data per batch
            data_batch = cls.fetch_from_bridge(limit=batch_size)
            
            # Jika data_batch bukan list (misal None atau Error), hentikan
            if not data_batch or not isinstance(data_batch, list):
                print("Tidak ada data lagi atau format data salah.")
                break
            
            # Eksekusi sync
            synced, ignored = cls.execute_sync(data_batch)
            total_synced += synced
            total_ignored += ignored
            
            print(f"Batch diproses: {synced} Sukses, {ignored} Dilewati.")
            
            # Cek apakah data sudah habis
            # Gunakan len() untuk mendapatkan int, lalu bandingkan dengan int batch_size
            if len(data_batch) < batch_size:
                break
                
        print(f"Selesai. Total Sukses: {total_synced}, Total Dilewati: {total_ignored}")
        return total_synced, total_ignored
    
    @classmethod
    def fetch_logs_by_date(cls, date_from=None, date_to=None, page=1, limit=500):
        token = cls.get_token()
        if not token:
            return [], {}

        url = f"{settings.PRESENSI_BASE_URL}/api/v1/att-logs"
        headers = {'Authorization': f'Bearer {token}'}

        params = {
            'page': page,
            'per_page': limit,
            'sort_by': 'datetime',
            'sort_order': 'desc'
        }

        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to

        try:
            res = requests.get(url, headers=headers, params=params, timeout=30)
            res.raise_for_status()
            data = res.json()
            return data.get('data', []), data.get('meta', {})
        except Exception as e:
            logger.error(f"Fetch logs gagal: {e}")
            return [], {}
        
        
        
# service proses interpretasi kehadiran pegawai

class KehadiranServicePerPegawai:
    @staticmethod
    def proses_penilaian_by_jadwal(tanggal, pegawai=None):
        # Ambil semua jadwal pada tanggal tersebut
        # Kita mulai dari JadwalDinasSDM agar otomatis mengabaikan yang tidak punya jadwal
        jadwals = JadwalDinasSDM.objects.filter(tanggal=tanggal).select_related(
            'pegawai__pegawai', 
            'kategori_jadwal'
        )
        if pegawai:
            jadwals = jadwals.filter(pegawai__pegawai=pegawai)

        alasan_tk, _ = AlasanTidakHadir.objects.get_or_create(alasan='Tanpa Keterangan')
        processed_count = 0

        for jadwal in jadwals:
            user = jadwal.pegawai.pegawai
            detail = jadwal.kategori_jadwal
            
            if not detail or not detail.waktu_datang:
                continue

            # 1. Cari DaftarKegiatanPegawai yang sesuai untuk relasi model KehadiranKegiatan
            from .models import DaftarKegiatanPegawai
            pegawai_kegiatan = DaftarKegiatanPegawai.objects.filter(
                pegawai=user,
                bulan=tanggal.month,
                tahun=tanggal.year
            ).first()

            if not pegawai_kegiatan:
                continue

            # 2. Ambil Log dari Mesin (IN & OUT)
            # Rentang waktu: dari target datang hingga H+1 untuk shift malam
            logs = LogKehadiran.objects.filter(
                mapping__pegawai=user,
                datetime__date__range=[tanggal, tanggal + timedelta(days=1)]
            )

            target_datang = timezone.make_aware(datetime.combine(tanggal, detail.waktu_datang))
            target_pulang = timezone.make_aware(datetime.combine(tanggal, detail.waktu_pulang))
            
            # Koreksi tanggal pulang jika melewati tengah malam (Shift Malam)
            if detail.waktu_pulang < detail.waktu_datang:
                target_pulang += timedelta(days=1)#[cite: 1]

            log_in = logs.filter(direction__iexact='IN').order_by('datetime').first()
            log_out = logs.filter(direction__iexact='OUT').order_by('-datetime').first()

            # 3. Penentuan Status
            status_final = 'Tanpa Keterangan'
            is_hadir = False
            waktu_simpan = target_datang

            if log_in:
                is_hadir = True
                waktu_simpan = log_in.datetime
                selisih_masuk = (log_in.datetime - target_datang).total_seconds() / 60
                
                # Cek Pulang Cepat
                if log_out:
                    selisih_pulang = (target_pulang - log_out.datetime).total_seconds() / 60
                    if selisih_pulang > 15: # Contoh toleransi pulang cepat 15 menit
                        status_final = 'Cepat Pulang'
                    elif selisih_masuk <= 0:
                        status_final = 'Tepat Waktu'
                    else:
                        status_final = 'Terlambat' # Bisa ditarik dari AturanToleransiKeterlambatan
                else:
                    status_final = 'Hanya Absen Datang'

            # 4. Simpan ke KehadiranKegiatan
            KehadiranKegiatan.objects.update_or_create(
                pegawai=pegawai_kegiatan,
                tanggal=waktu_simpan,
                defaults={
                    'hadir': is_hadir,
                    'alasan': None if is_hadir else alasan_tk,
                    'status_ketepatan': status_final,
                    'ket': f"Jadwal: {detail.kategori_jadwal} ({detail.waktu_datang}-{detail.waktu_pulang})"
                }
            )
            processed_count += 1
        
        return processed_count
    

class KehadiranService:
    @staticmethod
    def proses_kehadiran_massal(tanggal):
        # Ambil semua jadwal pada tanggal terpilih
        jadwals = JadwalDinasSDM.objects.filter(tanggal=tanggal).select_related(
            'pegawai__pegawai', 
            'kategori_jadwal'
        )

        alasan_tk, _ = AlasanTidakHadir.objects.get_or_create(alasan='Tanpa Keterangan')
        count = 0

        with transaction.atomic():
            for jadwal in jadwals:
                user = jadwal.pegawai.pegawai
                detail = jadwal.kategori_jadwal
                
                if not detail or not detail.waktu_datang:
                    continue

                # Ambil container kegiatan pegawai untuk bulan/tahun terkait
                pegawai_kegiatan = DaftarKegiatanPegawai.objects.filter(
                    pegawai=user,
                    bulan=tanggal.month,
                    tahun=tanggal.year
                ).first()

                if not pegawai_kegiatan:
                    continue

                # 1. Tentukan Target Waktu (Naive)
                target_in = datetime.combine(tanggal, detail.waktu_datang)
                target_out = datetime.combine(tanggal, detail.waktu_pulang)
                
                # Logika Shift Malam: Jika pulang < datang, maka pulang di H+1
                if detail.waktu_pulang < detail.waktu_datang:
                    target_out += timedelta(days=1)

                # 2. Ambil Log Mesin (Naive)
                # Filter range datetime untuk mengakomodasi shift malam
                logs = LogKehadiran.objects.filter(
                    mapping__pegawai=user,
                    datetime__range=[target_in - timedelta(hours=4), target_out + timedelta(hours=4)]
                ).exclude(devicename__icontains='apel-pagi') # Pastikan tidak mengambil log dari mesin apel pagi

                log_in = logs.filter(direction__iexact='IN').order_by('datetime').first()
                log_out = logs.filter(direction__iexact='OUT').order_by('datetime').last()

                # 3. Penilaian
                is_hadir = False
                status_ketepatan = 'Tanpa Keterangan'
                waktu_final = target_in

                if log_in:
                    is_hadir = True
                    waktu_final = log_in.datetime
                    selisih_in = (log_in.datetime - target_in).total_seconds() / 60
                    
                    if selisih_in <= 15: # Contoh toleransi keterlambatan 15 menit
                        status_ketepatan = 'Tepat Waktu'
                    else:
                        status_ketepatan = 'Terlambat' # Logika detail bisa ditambah di sini

                    if log_out:
                        selisih_out = (target_out - log_out.datetime).total_seconds() / 60
                        if selisih_out > 15: # Pulang lebih awal > 15 menit
                            status_ketepatan = 'Cepat Pulang'

                # 4. Upsert data ke KehadiranKegiatan
                KehadiranKegiatan.objects.update_or_create(
                    pegawai=pegawai_kegiatan,
                    tanggal=waktu_final,
                    defaults={
                        'hadir': is_hadir,
                        'alasan': None if is_hadir else alasan_tk,
                        'status_ketepatan': status_ketepatan,
                        'ket': f"Jadwal: {detail.kategori_jadwal} ({detail.waktu_datang}-{detail.waktu_pulang})"
                    }
                )
                count += 1
        return count
    

class ApelPagiService:
    @staticmethod
    def proses_penilaian_apel_massal(tanggal):
        # 1. Ambil semua pegawai yang punya jadwal Shift Pagi atau Reguler hari ini
        jadwal_pagi = JadwalDinasSDM.objects.filter(
            tanggal=tanggal,
            kategori_jadwal__kategori_jadwal__icontains='Pagi'
        ).select_related('pegawai__pegawai')

        alasan_tk, _ = AlasanTidakHadir.objects.get_or_create(alasan='Tanpa Keterangan')
        count_diproses = 0

        for jadwal in jadwal_pagi:
            user = jadwal.pegawai.pegawai
            
            # 2. Cari DaftarKegiatanPegawai khusus untuk kegiatan 'apel-pagi'
            # Pastikan di database sudah ada JenisKegiatan dengan nama/slug 'apel-pagi'
            kegiatan_apel = DaftarKegiatanPegawai.objects.filter(
                pegawai=user,
                bulan=tanggal.month,
                tahun=tanggal.year,
                kegiatan__slug__icontains='apel-pagi' # Mengacu ke field kegiatan
            ).first()

            # Jika pegawai tidak memiliki baris kegiatan 'apel-pagi', lewati (atau buat otomatis)
            if not kegiatan_apel:
                continue

            # 3. Cek apakah ada log di mesin 'apel-pagi'
            log_apel = LogKehadiran.objects.filter(
                mapping__pegawai=user,
                devicename='apel-pagi', # Filter berdasarkan nama alat khusus
                datetime__date=tanggal,
                datetime__time__range=(time(6, 0), time(8, 0)) # Range waktu apel[cite: 1]
            ).first()

            # 4. Update atau Create record KehadiranKegiatan khusus untuk kegiatan apel
            KehadiranKegiatan.objects.update_or_create(
                pegawai=kegiatan_apel, # Mengacu ke DaftarKegiatanPegawai kategori apel[cite: 1]
                tanggal=datetime.combine(tanggal, time(7, 30)),
                defaults={
                    'hadir': True if log_apel else False,
                    'alasan': None if log_apel else alasan_tk,
                    'status_ketepatan': 'Tepat Waktu' if log_apel else None,
                    'ket': f"Presensi via alat: {log_apel.devicename}" if log_apel else "Tidak ada log di mesin apel-pagi"
                }
            )
            count_diproses += 1
            
        return count_diproses