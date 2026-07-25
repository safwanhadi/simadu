import requests
import logging
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.conf import settings
from .models import JenisSDMPerinstalasi, MappingMesinAbsensi, LogKehadiran
from oauth2_provider.models import get_application_model
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, get_current_timezone
from django.utils import timezone

from datetime import datetime, timedelta, time, date
from .attendance_rules import HOLIDAY, MISSING_SCHEDULE, WORK, classify_daily_obligation

from .models import (
    JadwalDinasSDM, ApprovedJadwalDinasSDM, LogKehadiran, KehadiranKegiatan, 
    DaftarKegiatanPegawai, AlasanTidakHadir, JenisKegiatan, AturanToleransiKeterlambatan, HariLibur
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
    def run_daily_sync(cls, date_from, date_to=None, limit=500):
        """
        Melakukan sinkronisasi data log berdasarkan rentang tanggal tertentu (Per Hari).
        Format parameter: 'YYYY-MM-DD'
        """
        # Jika date_to tidak diisi, setel sama dengan date_from (sinkronisasi 1 hari saja)
        if not date_to:
            date_to = date_from

        total_synced = 0
        total_ignored = 0
        page = 1

        

        while True:
            # Menggunakan fetch_unsynced_by_date atau fetch_logs_by_date tergantung kebutuhan Anda.
            # Di sini kita gunakan fetch_unsynced_by_date yang memiliki filter date_from & date_to.
            data_batch, meta = cls.fetch_unsynced_by_date(
                date_from=date_from, 
                date_to=date_to, 
                page=page, 
                limit=limit
            )

            # Jika data kosong atau bermasalah, hentikan loop
            if not data_batch or not isinstance(data_batch, list):
                
                break

            # Eksekusi sinkronisasi ke MariaDB dan penandaan 'synced' ke SQLite Flask Bridge
            synced, ignored = cls.execute_sync(data_batch)
            total_synced += synced
            total_ignored += ignored

            

            # Cek pagination dari meta response API Flask (jaki Flask API menyediakan info total page)
            total_pages = meta.get('total_pages', meta.get('pages', 1))
            if page >= total_pages:
                break
                
            # Jika API Anda tidak mengembalikan total_pages, gunakan fallback ukuran data:
            if len(data_batch) < limit:
                break

            page += 1

        
        return total_synced, total_ignored

    @classmethod
    def execute_sync(cls, logs_data):
        if not logs_data: return 0, 0
        
        # Gunakan str(m.mesin_id) untuk mengantisipasi jika ID di JSON bertipe integer
        mappings = {str(m.mesin_id): m for m in MappingMesinAbsensi.objects.all()}
        to_create = []
        all_keys_to_mark = [] 
        ignored_count = 0

        for item in logs_data:
            # 1. Masukkan SEMUA log_key tanpa terkecuali
            log_key_str = f"{item['id']}_{item['datetime']}"
            all_keys_to_mark.append(log_key_str)

            # Paksa pencarian menggunakan string key
            mapping = mappings.get(str(item['id']))
            if mapping:
                clean_datetime_str = item['datetime'].replace('T', ' ').split('.')[0] # Bersihkan s/d detik
                clean_datetime_str = clean_datetime_str[:19]
                
                to_create.append(LogKehadiran(
                    mapping=mapping,
                    datetime=clean_datetime_str,
                    direction=item['direction'],
                    devicename=item['devicename'],
                    personname=item['personname']
                ))
            else:
                ignored_count += 1
        
        # 2. Simpan data yang valid ke MariaDB SIMADU (Murni urusan Database)
        if to_create:
            
            try:
                with transaction.atomic():
                    
                    # Matikan ignore_conflicts sementara jika Anda ingin melacak error aslinya!
                    LogKehadiran.objects.bulk_create(to_create, ignore_conflicts=True)
                
            except Exception as e:
                print(f"Error saat menyimpan ke database: {e}")
              
        # KODE INI SAYA GUNAKAN SAAT FRUSTASI MENCARI ERROR ASLI
        # 2. Simpan data yang valid ke MariaDB SIMADU
        # if to_create:
        #     
        #     try:
        #         with transaction.atomic():
        #             
        #             # 1. Ambil data pertama dari list
        #             test_obj = to_create[0]
                    
        #             # 2. Cek apakah data ini sudah ada di DB sebelum dicoba save
        #             exists = LogKehadiran.objects.filter(
        #                 mapping=test_obj.mapping,
        #                 datetime=test_obj.datetime,
        #                 direction=test_obj.direction
        #             ).exists()
        #             
                    
        #             # 3. Paksa save() data pertama ini untuk memancing error asli database
        #             test_obj.save()
        #             
                    
        #             
        #             # Hapus ignore_conflicts=True agar jika ada error tersembunyi langsung meledak di sini
        #             LogKehadiran.objects.bulk_create(to_create[1:]) 
                    
        #         
        #     except Exception as e:
        #         
        #         
        #         
        #         
        
        # 3. KIRIM SEMUA KEYS KE FLASK (Ditaruh di LUAR blok database)
        # Langkah ini harus tetap jalan agar antrean SQLite di Flask bersih
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
        
        
        
        while True:
            # Ambil data per batch
            data_batch = cls.fetch_from_bridge(limit=batch_size)
            
            # Jika data_batch bukan list (misal None atau Error), hentikan
            if not data_batch or not isinstance(data_batch, list):
                
                break
            
            # Eksekusi sync
            synced, ignored = cls.execute_sync(data_batch)
            total_synced += synced
            total_ignored += ignored
            
            
            
            # Cek apakah data sudah habis
            # Gunakan len() untuk mendapatkan int, lalu bandingkan dengan int batch_size
            if len(data_batch) < batch_size:
                break
                
        
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
        jadwals = ApprovedJadwalDinasSDM.objects.filter(tanggal=tanggal).select_related(
            'pegawai__pegawai', 
            'kategori_jadwal'
        )
        

        alasan_tk, _ = AlasanTidakHadir.objects.get_or_create(alasan='Tanpa Keterangan')
        count = 0

        with transaction.atomic():
            
            for jadwal in jadwals:
                user = jadwal.pegawai.pegawai
                detail = jadwal.kategori_jadwal
                
                hitung = 0
                if not detail or not detail.waktu_datang:
                    hitung+=1
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
    
    
# SERVICE BARU UNTUK MENILAI KEHADIRAN 
class AttendanceMappingService:

    @classmethod
    def process_logs_batch(cls, target_date, user_ids):
        """
        Menghubungkan LogKehadiran mentah dengan Header (DaftarKegiatanPegawai)
        lalu di-insert massal ke Detail (KehadiranKegiatan) dengan proteksi Anti-Double Tap (Menit).
        """
        # 1. Ambil JenisKegiatan berdasarkan slug jembatan mesin absensi
        try:
            kegiatan_datang = JenisKegiatan.objects.get(slug='absen-datang')
            kegiatan_pulang = JenisKegiatan.objects.get(slug='absen-pulang')
        except JenisKegiatan.DoesNotExist:
            return False, "Master JenisKegiatan dengan slug 'absen-datang'/'absen-pulang' belum diset."

        # 2. Ambil log mentah dari mesin berdasarkan target_date & scope pegawai
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        
        raw_logs = LogKehadiran.objects.filter(
            datetime__range=(start_dt, end_dt)
        ).filter(
            Q(mapping__pegawai_id__in=user_ids) if user_ids else Q()
        ).select_related('mapping__pegawai')

        if not raw_logs.exists():
            return True, "Tidak ada log mentah baru yang ditemukan pada tanggal ini."

        # 3. AMANKAN HEADER (DaftarKegiatanPegawai) UNTUK BULAN & TAHUN INI
        bulan_target = target_date.month
        tahun_target = target_date.year

        # Ambil metadata struktur sdm pegawai aktif di periode ini
        sdm_structures = JenisSDMPerinstalasi.objects.filter(
            pegawai_id__in=user_ids, bulan=bulan_target, tahun=tahun_target
        ).select_related('instalasi', 'sub_bidang', 'bidang', 'unor', 'jenis_sdm')
        
        sdm_map = {s.pegawai_id: s for s in sdm_structures}

        # Menggunakan dictionary cache untuk mempercepat resolve ID header di memori
        header_cache = {}
        
        # Ambil header yang sudah existing di database biar gak bikin duplikat
        existing_headers = DaftarKegiatanPegawai.objects.filter(
            pegawai_id__in=user_ids, bulan=bulan_target, tahun=tahun_target
        )
        for eh in existing_headers:
            header_cache[(eh.pegawai_id, eh.kegiatan_id)] = eh

        # Loop untuk membuat header baru jika belum terdaftar di database
        headers_to_create = []
        for p_id in user_ids:
            struct = sdm_map.get(p_id)
            if not struct:
                continue
                
            for keg in [kegiatan_datang, kegiatan_pulang]:
                if (p_id, keg.id) not in header_cache:
                    new_header = DaftarKegiatanPegawai(
                        pegawai_id=p_id,
                        kegiatan=keg,
                        bulan=bulan_target,
                        tahun=tahun_target,
                        jenis_sdm=struct.jenis_sdm,
                        unor=struct.unor,
                        bidang=struct.bidang,
                        sub_bidang=struct.sub_bidang,
                        instalasi=struct.instalasi
                    )
                    headers_to_create.append(new_header)
                    header_cache[(p_id, keg.id)] = new_header

        if headers_to_create:
            DaftarKegiatanPegawai.objects.bulk_create(headers_to_create, ignore_conflicts=True)
            
            # Ambil ulang dari DB untuk mendapatkan AutoIncrement ID yang digenerate database
            refreshed_headers = DaftarKegiatanPegawai.objects.filter(
                pegawai_id__in=user_ids, bulan=bulan_target, tahun=tahun_target
            )
            for rh in refreshed_headers:
                header_cache[(rh.pegawai_id, rh.kegiatan_id)] = rh

        # =========================================================================
        # 4. PREPARASI DATA DETAIL (KehadiranKegiatan) - PERBAIKAN ANTI-DOUBLE TAP
        # =========================================================================
        
        # Lapis Pengaman 1: Ambil data detail harian tanggal tersebut yang sudah tertulis di database
        existing_detail_dates = set(
            KehadiranKegiatan.objects.filter(
                pegawai__pegawai_id__in=user_ids,
                tanggal__date=target_date
            ).values_list('tanggal', flat=True)
        )

        # Konversi data existing DB menjadi format string menit (Y-m-d H:M) untuk pencocokan cache
        # Set ini diisi dengan signature format: f"{pegawai_id}-{tahun-bulan-hari jam:menit}"
        # Contoh isi: {"12-2026-06-04 14:05"}
        seen_minutes = set()
        for dt in existing_detail_dates:
            # Cari tahu pegawai_id-nya dari relasi header untuk dimasukkan ke signature unik menit
            # (Gunakan kueri manual jika data existing ditarik massal dengan values)
            pass
            
        # Metode penentuan string menit yang lebih rigid dari database eksistensial:
        existing_details_qs = KehadiranKegiatan.objects.filter(
            pegawai__pegawai_id__in=user_ids,
            tanggal__date=target_date
        ).values_list('pegawai__pegawai_id', 'tanggal')
        
        for p_id_exist, dt_exist in existing_details_qs:
            minute_str_exist = dt_exist.strftime('%Y-%m-%d %H:%M')
            seen_minutes.add(f"{p_id_exist}-{minute_str_exist}")

        kehadiran_detail_inserts = []

        for log in raw_logs:
            p_id = log.mapping.pegawai_id if log.mapping else None
            if not p_id:
                continue

            # Buat token signature unik gabungan ID Pegawai dan Menit Absensi (Abaikan detik eksak)
            minute_str = log.datetime.strftime('%Y-%m-%d %H:%M')
            log_signature = f"{p_id}-{minute_str}"

            # Lapis Pengaman 2 & 3: Jika kombinasi menit ini sudah ada di DB atau loop berjalan, LEWATI (SKIP)
            if log_signature in seen_minutes:
                continue
                
            # Daftarkan ke memori lokal berjalan agar ketukan ganda beberapa detik berikutnya terblokir
            seen_minutes.add(log_signature)

            # Tentukan jenis kegiatan berdasarkan arah log mesin absensi
            if log.direction in ['IN', 'Masuk']:
                kegiatan_target = kegiatan_datang
            else:
                kegiatan_target = kegiatan_pulang

            # Dapatkan object header dari cache memori
            header_obj = header_cache.get((p_id, kegiatan_target.id))
            if not header_obj or not header_obj.id:
                continue

            # Instansiasi objek detail harian KehadiranKegiatan (Hanya untuk ketukan pertama yang lolos)
            kehadiran_detail_inserts.append(KehadiranKegiatan(
                pegawai=header_obj,
                tanggal=log.datetime,  # Tetap simpan waktu asli ketukan pertama
                hadir=True,
                status_ketepatan=None,  # Menunggu penilaian Langkah 2 di Orchestrator
                ket="Dipetakan otomatis dari log jembatan mesin (Anti-Double Tap)."
            ))

        # 5. EKSEKUSI BULK CREATE DETAIL KE DATABASE
        total_inserted = 0
        if kehadiran_detail_inserts:
            inserted_records = KehadiranKegiatan.objects.bulk_create(
                kehadiran_detail_inserts,
                ignore_conflicts=True
            )
            total_inserted = len(inserted_records) if inserted_records else len(kehadiran_detail_inserts)
            
        return True, f"Sukses memetakan {total_inserted} rincian kehadiran harian ke dalam lembar kegiatan pegawai."
    
    
class AttendanceReconciliationService:

    @classmethod
    def evaluate_arrival_status(cls, check_in_time: time, scheduled_in_time: time, rules) -> str:
        dummy_date = date.today()
        dt_actual = datetime.combine(dummy_date, check_in_time)
        dt_schedule = datetime.combine(dummy_date, scheduled_in_time)
        
        if dt_actual <= dt_schedule:
            return 'Tepat Waktu'
            
        delay_minutes = int((dt_actual - dt_schedule).total_seconds() / 60)
        for rule in rules:
            if delay_minutes <= rule.batas_atas_menit:
                return rule.status_yang_dihasilkan
                
        return 'Terlambat Berat'

    @classmethod
    def reconcile_batch(cls, target_date: date, sdm_perinstalasi_queryset):
        
        sdm_ids = [sdm.id for sdm in sdm_perinstalasi_queryset]
        pegawai_user_ids = [sdm.pegawai_id for sdm in sdm_perinstalasi_queryset]
        
        rules = list(AturanToleransiKeterlambatan.objects.filter(is_aktif=True).order_by('batas_atas_menit'))
        
        approved_schedules = {
            sch.pegawai_id: sch.kategori_jadwal 
            for sch in ApprovedJadwalDinasSDM.objects.filter(pegawai_id__in=sdm_ids, tanggal=target_date, is_approved=True).select_related('kategori_jadwal')
        }
        
        draft_schedules = {
            sch.pegawai_id: sch.kategori_jadwal 
            for sch in JadwalDinasSDM.objects.filter(pegawai_id__in=sdm_ids, tanggal=target_date).select_related('kategori_jadwal')
        }
        
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        
        kehadiran_queryset = KehadiranKegiatan.objects.filter(
            pegawai__pegawai_id__in=pegawai_user_ids,
            tanggal__range=(start_dt, end_dt),
            hadir=True
        ).select_related('pegawai__kegiatan', 'pegawai__pegawai')
        
        
        user_to_sdm_map = {sdm.pegawai_id: sdm.id for sdm in sdm_perinstalasi_queryset}
        
        # --- PERUBAHAN DI SINI: Siapkan list untuk menampung objek yang diupdate ---
        updated_objects = []
        
        for kehadiran in kehadiran_queryset:
            user_id = kehadiran.pegawai.pegawai_id
            sdm_id = user_to_sdm_map.get(user_id)
            if not sdm_id:
                continue
                
            log_time = kehadiran.tanggal.time()
            slug_kegiatan = kehadiran.pegawai.kegiatan.slug if kehadiran.pegawai.kegiatan else None
            jadwal_kerja = approved_schedules.get(sdm_id) or draft_schedules.get(sdm_id)
            
            if not jadwal_kerja or not jadwal_kerja.waktu_datang or not jadwal_kerja.waktu_pulang:
                kehadiran.status_ketepatan = None
                kehadiran.ket = "Hadir di luar jadwal dinas resmi terdaftar."
                updated_objects.append(kehadiran) # Masukkan ke list update
                continue
                
            if slug_kegiatan == 'absen-datang':
                status = cls.evaluate_arrival_status(log_time, jadwal_kerja.waktu_datang, rules)
                kehadiran.status_ketepatan = status
                kehadiran.ket = f"Evaluasi otomatis vs Jadwal {jadwal_kerja.kategori_jadwal} (Masuk: {jadwal_kerja.waktu_datang.strftime('%H:%M')})"
                
            elif slug_kegiatan == 'absen-pulang':
                if log_time < jadwal_kerja.waktu_pulang:
                    kehadiran.status_ketepatan = 'Cepat Pulang'
                else:
                    kehadiran.status_ketepatan = 'Tepat Waktu'
                kehadiran.ket = f"Evaluasi otomatis vs Jadwal {jadwal_kerja.kategori_jadwal} (Pulang: {jadwal_kerja.waktu_pulang.strftime('%H:%M')})"
            
            # Masukkan ke list untuk dieksekusi massal nanti
            updated_objects.append(kehadiran)
            
        # --- EKSEKUSI BULK UPDATE (Hanya 1 Kueri SQL ke Database) ---
        if updated_objects:
            KehadiranKegiatan.objects.bulk_update(
                updated_objects, 
                fields=['status_ketepatan', 'ket'] # Tentukan kolom apa saja yang berubah
            )
        
        return len(updated_objects)
    

class AttendanceOrchestrator:

    @classmethod
    def execute_by_structure(cls, target_date, instalasi_id=None, sub_bidang_id=None, bidang_id=None, unor_id=None):
        """
        Orchestrator Tunggal (Single Source of Truth) untuk Evaluasi Presensi.
        Mencakup: Batch Mapping Log Mentah -> Rekonsiliasi Jam Kerja -> Deteksi Mangkir (TK).
        Dapat dipicu secara manual via Web Dashboard maupun otomatis via Django Q2 Worker.
        """
        bulan_target = target_date.month
        tahun_target = target_date.year

        # =========================================================================
        # 1. STRATEGI CAKUPAN / SCOPE HIRARKI ORGANISASI
        # =========================================================================
        scope_filter = Q(bulan=bulan_target, tahun=tahun_target)
        if instalasi_id:
            scope_filter &= Q(instalasi_id=instalasi_id)
        if sub_bidang_id:
            scope_filter &= Q(sub_bidang_id=sub_bidang_id)
        if bidang_id:
            scope_filter &= Q(bidang_id=bidang_id)
        if unor_id:
            scope_filter &= Q(unor_id=unor_id)
            
        print(f"scope_filter: {scope_filter}")

        # Ambil daftar pegawai aktif berdasarkan filter struktur organisasi
        scope_pegawai_qs = JenisSDMPerinstalasi.objects.filter(scope_filter)
        if not scope_pegawai_qs.exists():
            return False, "Tidak ada data pegawai aktif dalam ruang lingkup struktur organisasi yang dipilih."

        # Ekstrak seluruh ID pegawai ke dalam list di memori untuk keperluan batching
        user_ids = list(scope_pegawai_qs.values_list('pegawai_id', flat=True))
        print(f"user_ids: {user_ids}")
        # gunakan atomic transaction untuk menjaga konsistensi state database
        with transaction.atomic():
            
            # =========================================================================
            # TAHAP A: OTOMATISASI BATCH MAPPING (LANGKAH 1 INTERNAL)
            # =========================================================================
            # Memetakan seluruh log mentah dari mesin absensi menjadi record detail KehadiranKegiatan
            success_map, msg_map = AttendanceMappingService.process_logs_batch(
                target_date=target_date, 
                user_ids=user_ids
            )
            if not success_map:
                return False, f"Gagal di Tahap Pemetaan Log: {msg_map}"

            print(f"Mapping Result - Success: {success_map}, Info: {msg_map}")

            # =========================================================================
            # TAHAP B: REKONSILIASI KETEPATAN WAKTU LOG EXISTING (LANGKAH 2 INTERNAL)
            # =========================================================================
            total_reconciled = 0
            
            # Tarik data KehadiranKegiatan yang baru saja dibuat atau yang belum dievaluasi
            kehadiran_to_evaluate = KehadiranKegiatan.objects.filter(
                pegawai__pegawai_id__in=user_ids,
                tanggal__date=target_date,
                status_ketepatan__isnull=True  # Hanya evaluasi yang belum memiliki status
            ).select_related('pegawai__pegawai', 'pegawai__kegiatan')

            # Kumpulkan jadwal dinas pegawai untuk tanggal terkait sebagai pembanding
            jadwal_dinas_map = {
                jd.pegawai_id: jd for jd in ApprovedJadwalDinasSDM.objects.filter(
                    tanggal=target_date, is_approved=True, pegawai_id__in=user_ids
                ).select_related('kategori_jadwal')
            }

            kehadiran_updates = []
            
            for kh in kehadiran_to_evaluate:
                peg_id = kh.pegawai.pegawai_id
                jadwal = jadwal_dinas_map.get(peg_id)
                
                if not jadwal:
                    # Sesuai aturan SIMADU: Lewati pegawai yang tidak memiliki jadwal dinas (JadwalDinasSDM)
                    kh.status_ketepatan = 'Tanpa Jadwal'
                    kh.ket = "Sistem: Pegawai tidak memiliki lembar JadwalDinasSDM pada hari ini."
                    kehadiran_updates.append(kh)
                    continue

                # Ambil batasan jam kerja dari shift yang berlaku
                jam_log = kh.tanggal.time()
                slug_kegiatan = kh.pegawai.kegiatan.slug

                if slug_kegiatan == 'absen-datang':
                    waktu_target = jadwal.kategori_jadwal.waktu_datang
                    # Logika komparasi sederhana (Dapat disesuaikan dengan aturan toleransi instansi Anda)
                    if jam_log <= waktu_target:
                        kh.status_ketepatan = 'Tepat Waktu'
                        kh.ket = f"Hadir tepat waktu. Jadwal masuk: {waktu_target.strftime('%H:%M')}"
                    else:
                        kh.status_ketepatan = 'Terlambat'
                        kh.ket = f"Terlambat. Jadwal masuk: {waktu_target.strftime('%H:%M')}"
                        
                elif slug_kegiatan == 'absen-pulang':
                    waktu_target = jadwal.kategori_jadwal.waktu_pulang
                    if jam_log >= waktu_target:
                        kh.status_ketepatan = 'Sesuai Jadwal'
                        kh.ket = f"Pulang sesuai aturan. Jadwal pulang: {waktu_target.strftime('%H:%M')}"
                    else:
                        kh.status_ketepatan = 'Pulang Cepat'
                        kh.ket = f"Pulang mendahului waktu. Jadwal pulang: {waktu_target.strftime('%H:%M')}"

                kehadiran_updates.append(kh)

            # Eksekusi pembaruan status massal (Bulk Update)
            if kehadiran_updates:
                KehadiranKegiatan.objects.bulk_update(kehadiran_updates, ['status_ketepatan', 'ket'])
                total_reconciled = len(kehadiran_updates)

            # =========================================================================
            # TAHAP C: DETEKSI OTOMATIS PEGAWAI MANGKIR (TANPA KETERANGAN / TK)
            # =========================================================================
            alasan_tk, _ = AlasanTidakHadir.objects.get_or_create(alasan='Tanpa Keterangan')
            total_tk_terbuat = 0

            # Tarik seluruh jadwal dinas aktif hari ini (Kecuali hari libur) di dalam scope user_ids
            jadwal_aktif_scope = ApprovedJadwalDinasSDM.objects.filter(
                tanggal=target_date,
                is_approved=True,
                pegawai_id__in=user_ids
            ).exclude(
                kategori_jadwal__kategori_dinas__kategori_dinas__icontains='Libur'
            ).select_related('pegawai', 'kategori_jadwal')

            tk_to_create = []

            for jdl in jadwal_aktif_scope:
                peg_instalasi = jdl.pegawai
                if not peg_instalasi:
                    continue

                # Kueri efisien mengecek apakah deteksi tap masuk (absen-datang) tersedia di database
                punya_absen_datang = KehadiranKegiatan.objects.filter(
                    pegawai__pegawai_id=peg_instalasi.pegawai_id,
                    pegawai__bulan=bulan_target,
                    pegawai__tahun=tahun_target,
                    pegawai__kegiatan__slug='absen-datang',
                    tanggal__date=target_date
                ).exists()

                # Jika terjadwal dinas tetapi tidak ada transaksi tapping masuk sama sekali
                if not punya_absen_datang:
                    # Resolusi Header rekap bulanan (DaftarKegiatanPegawai)
                    header_kegiatan = DaftarKegiatanPegawai.objects.filter(
                        pegawai_id=peg_instalasi.pegawai_id,
                        bulan=bulan_target,
                        tahun=tahun_target,
                        kegiatan__slug='absen-datang'
                    ).first()

                    if header_kegiatan:
                        # Gabungkan tanggal evaluasi dengan jam masuk ideal untuk penanda waktu TK
                        jam_masuk_ideal = jdl.kategori_jadwal.waktu_datang
                        datetime_tk = timezone.make_aware(datetime.combine(target_date, jam_masuk_ideal))

                        tk_to_create.append(KehadiranKegiatan(
                            pegawai=header_kegiatan,
                            tanggal=datetime_tk,
                            hadir=False,
                            alasan=alasan_tk,
                            status_ketepatan='Terlambat Berat',
                            ket=f"Orchestrator Sistem: Alpa / Tidak melakukan tapping pada jadwal shift {jdl.kategori_jadwal.kategori_jadwal}"
                        ))

            # Masukkan seluruh data alpa ke database secara massal (Aman dari bentrokan duplikasi)
            if tk_to_create:
                inserted_tk = KehadiranKegiatan.objects.bulk_create(tk_to_create, ignore_conflicts=True)
                total_tk_terbuat = len(inserted_tk) if inserted_tk else len(tk_to_create)

        # ---------------------------------------------------------------------
        # RETURN RESPON STATUS (Untuk UI Messages / Logs Django Q)
        # ---------------------------------------------------------------------
        info_pesan = (
            f"Evaluasi Sukses ({target_date.strftime('%d-%m-%Y')}). "
            f"Scope Pemetaan: {len(user_ids)} Pegawai. Berhasil menilai {total_reconciled} data log, "
            f"dan mengunci {total_tk_terbuat} status Mangkir (Tanpa Keterangan)."
        )
        return True, info_pesan
    
    
################################# service model baru #################################
from .models import AbsensiHarian, LogAktivitasAbsen
from collections import defaultdict

class NewAttendanceMappingService:

    @classmethod
    def process_logs_batch(cls, target_date, user_ids):
        """
        Menghubungkan LogKehadiran mentah dengan Parent (AbsensiHarian).
        Mendukung penarikan log PULANG lintas hari (H+1) untuk mengantisipasi Shift Malam.
        """
        if not user_ids:
            return True, "Tidak ada scope pegawai yang diberikan."

        # -------------------------------------------------------------------------
        # PERBAIKAN 1: PERLEBAR RENTANG WAKTU LOG MENTAH (SLIDING RANGE)
        # -------------------------------------------------------------------------
        # Tarik log mulai dari Hari H jam 00:00 SANGGUP sampai Hari H+1 jam 13:00 siang
        start_dt = datetime.combine(target_date, datetime.min.time())
        esok_hari = target_date + timedelta(days=1)
        end_dt = datetime.combine(esok_hari, time(13, 0)) # Batas aman sapuan log shift malam
        
        raw_logs = LogKehadiran.objects.filter(
            datetime__range=(start_dt, end_dt),
            mapping__pegawai_id__in=user_ids
        ).select_related('mapping__pegawai').order_by('datetime')

        # 2. AMANKAN DATA METADATA STRUKTUR SDM
        bulan_target = target_date.month
        tahun_target = target_date.year

        sdm_structures = JenisSDMPerinstalasi.objects.filter(
            pegawai_id__in=user_ids, bulan=bulan_target, tahun=tahun_target # Sesuaikan field tahun Anda
        ).select_related('instalasi', 'sub_bidang', 'bidang', 'unor')
        
        sdm_map = {s.pegawai_id: s for s in sdm_structures}

        # -------------------------------------------------------------------------
        # PERBAIKAN 2: CACHE PARENT UNTUK HARI H DAN HARI H+1
        # -------------------------------------------------------------------------
        # Kita butuh cache dua hari karena log PULANG secara fisik hinggap di parent H+1 sebelum dimutasi
        parent_cache = {}
        existing_parents = AbsensiHarian.objects.filter(
            pegawai_id__in=user_ids, 
            tanggal__in=[target_date, esok_hari]
        )
        for ep in existing_parents:
            parent_cache[f"{ep.pegawai_id}-{ep.tanggal}"] = ep

        # Buat Parent Harian Baru jika benar-benar belum eksis di DB
        parents_to_create = []
        for p_id in user_ids:
            struct = sdm_map.get(p_id)
            if not struct:
                continue
            
            # Pastikan Parent Hari Ini (Hari H) terbentuk
            key_hari_ini = f"{p_id}-{target_date}"
            if key_hari_ini not in parent_cache:
                parents_to_create.append(AbsensiHarian(
                    pegawai_id=p_id, tanggal=target_date,
                    unor=struct.unor, bidang=struct.bidang, sub_bidang=struct.sub_bidang, instalasi=struct.instalasi,
                    status_final=''
                ))
            
            # Pastikan Parent Esok Hari (Hari H+1) JUGA terbentuk sebagai wadah pendaratan log awal
            key_esok = f"{p_id}-{esok_hari}"
            if key_esok not in parent_cache:
                parents_to_create.append(AbsensiHarian(
                    pegawai_id=p_id, tanggal=esok_hari,
                    unor=struct.unor, bidang=struct.bidang, sub_bidang=struct.sub_bidang, instalasi=struct.instalasi,
                    status_final=''
                ))

        if parents_to_create:
            AbsensiHarian.objects.bulk_create(parents_to_create, ignore_conflicts=True)
            
            # Refresh cache setelah bulk_create sukses
            refreshed_parents = AbsensiHarian.objects.filter(pegawai_id__in=user_ids, tanggal__in=[target_date, esok_hari])
            for rp in refreshed_parents:
                parent_cache[f"{rp.pegawai_id}-{rp.tanggal}"] = rp

        # Parent harus tetap terbentuk walaupun tidak ada seorang pun yang
        # melakukan tapping. Parent inilah yang nantinya dinilai ALPA/LIBUR
        # oleh orchestrator berdasarkan kalender dan jadwal.
        if not raw_logs.exists():
            return True, "Tidak ada log mentah baru; parent harian tetap berhasil disiapkan."

        # -------------------------------------------------------------------------
        # 3. PREPARASI DATA DETAIL CHILD (ANTI-DOUBLE TAP LINTAS HARI)
        # -------------------------------------------------------------------------
        seen_minutes = set()
        existing_details_qs = LogAktivitasAbsen.objects.filter(
            absensi_harian__pegawai_id__in=user_ids,
            absensi_harian__tanggal__in=[target_date, esok_hari]
        ).values_list('absensi_harian__pegawai_id', 'waktu')
        
        for p_id_exist, dt_exist in existing_details_qs:
            dt_local = timezone.localtime(dt_exist) if timezone.is_aware(dt_exist) else dt_exist
            minute_str_exist = dt_local.strftime('%Y-%m-%d %H:%M')
            seen_minutes.add(f"{p_id_exist}-{minute_str_exist}")

        child_inserts = []

        for log in raw_logs:
            p_id = log.mapping.pegawai_id if log.mapping else None
            if not p_id:
                continue

            log_dt_local = timezone.localtime(log.datetime) if timezone.is_aware(log.datetime) else log.datetime
            log_date_only = log_dt_local.date() # Deteksi tanggal fisik log diketuk (bisa Hari H / Hari H+1)
            
            minute_str = log_dt_local.strftime('%Y-%m-%d %H:%M')
            log_signature = f"{p_id}-{minute_str}"

            if log_signature in seen_minutes:
                continue
                
            seen_minutes.add(log_signature)

            # Tentukan tipe berdasarkan mesin
            if log.direction in ['IN', 'Masuk']:
                tipe_target = 'DATANG'
            else:
                tipe_target = 'PULANG'
                
            # Jika terdeteksi dari mesin apel, paksa tipenya jadi APEL sejak awal pemetaan
            if log.devicename and log.devicename.strip().lower() == 'apel':
                tipe_target = 'APEL'

            # -------------------------------------------------------------------------
            # PERBAIKAN 3: KAWINKAN LOG KE PARENT YANG SESUAI DENGAN TANGGAL KETUKANNYA
            # -------------------------------------------------------------------------
            # Log Pulang besok subuh akan bersandar dulu di Parent H+1, nanti dipindah oleh ReconciliationService
            parent_key = f"{p_id}-{log_date_only}"
            parent_obj = parent_cache.get(parent_key)
            
            if not parent_obj or not parent_obj.id:
                continue

            child_inserts.append(LogAktivitasAbsen(
                absensi_harian=parent_obj,
                tipe=tipe_target,
                waktu=log.datetime,
                devicename=log.devicename,
                status_ketepatan=None
            ))

        # 4. EXECUTE BULK CREATE CHILD
        total_inserted = 0
        if child_inserts:
            inserted_records = LogAktivitasAbsen.objects.bulk_create(child_inserts, ignore_conflicts=True)
            total_inserted = len(inserted_records) if inserted_records else len(child_inserts)
            
        return True, f"Sukses memetakan {total_inserted} rincian log aktivitas absen harian."
    

class NewAttendanceReconciliationService:

    @classmethod
    def evaluate_arrival_status(cls, check_in_time: time, scheduled_in_time: time, rules) -> str:
        dummy_date = date.today()
        dt_actual = datetime.combine(dummy_date, check_in_time)
        dt_schedule = datetime.combine(dummy_date, scheduled_in_time)
        
        if dt_actual <= dt_schedule:
            return 'Tepat Waktu'
            
        delay_minutes = int((dt_actual - dt_schedule).total_seconds() / 60)
        for rule in rules:
            if delay_minutes <= rule.batas_atas_menit:
                return rule.status_yang_dihasilkan
                
        return 'Terlambat Berat'

    @classmethod
    def reconcile_batch(cls, target_date: date, sdm_perinstalasi_queryset):
        sdm_ids = [sdm.id for sdm in sdm_perinstalasi_queryset]
        pegawai_user_ids = [sdm.pegawai_id for sdm in sdm_perinstalasi_queryset]
        
        rules = list(AturanToleransiKeterlambatan.objects.filter(is_aktif=True).order_by('batas_atas_menit'))
        
        # Load kamus jadwal dinas tepercaya
        approved_schedules = {
            sch.pegawai_id: sch.kategori_jadwal 
            for sch in ApprovedJadwalDinasSDM.objects.filter(
                pegawai_id__in=sdm_ids,
                tanggal=target_date,
                is_approved=True,
            ).select_related('kategori_jadwal__kategori_dinas')
        }
        draft_schedules = {
            sch.pegawai_id: sch.kategori_jadwal 
            for sch in JadwalDinasSDM.objects.filter(
                pegawai_id__in=sdm_ids,
                pegawai__status='disetujui',
                tanggal=target_date,
            ).select_related('kategori_jadwal__kategori_dinas')
        }
        
        user_to_sdm_map = {sdm.pegawai_id: sdm.id for sdm in sdm_perinstalasi_queryset}
        esok_hari = target_date + timedelta(days=1)
        
        # Selalu tarik ulang log yang relevan. Penilaian ulang harus dapat
        # mengikuti perubahan jadwal maupun aturan toleransi, bukan hanya
        # memproses log yang status_ketepatan-nya masih NULL.
        child_logs_queryset = LogAktivitasAbsen.objects.filter(
            absensi_harian__pegawai_id__in=pegawai_user_ids,
        ).filter(
            Q(absensi_harian__tanggal=target_date, tipe='DATANG') |
            Q(absensi_harian__tanggal=target_date, devicename__iexact='apel') |
            Q(absensi_harian__tanggal__in=[target_date, esok_hari], tipe='PULANG')
        ).select_related('absensi_harian').order_by('waktu', 'pk')

        grouped_by_pegawai = defaultdict(list)
        for log in child_logs_queryset:
            grouped_by_pegawai[log.absensi_harian.pegawai_id].append(log)

        child_updates = []
        parent_ids_to_present = set()
        parent_ids_to_revert = set()

        for pegawai_id, logs in grouped_by_pegawai.items():
            sdm_id = user_to_sdm_map.get(pegawai_id)
            if not sdm_id:
                continue
                
            # jadwal_kerja di sini ADALAH objek DetailKategoriJadwalDinas langsung
            jadwal_kerja = approved_schedules.get(sdm_id) or draft_schedules.get(sdm_id)
            if not jadwal_kerja or not jadwal_kerja.waktu_datang or not jadwal_kerja.waktu_pulang:
                for log in logs:
                    if log.absensi_harian.tanggal == target_date:
                        log.status_ketepatan = 'Luar Jadwal'
                        child_updates.append(log)
                        parent_ids_to_present.add(log.absensi_harian_id)
                continue

            is_shift_malam = jadwal_kerja.waktu_pulang < jadwal_kerja.waktu_datang

            datang_log = None
            pulang_log = None
            parent_hari_ini_id = None
            
            for log in logs:
                if log.absensi_harian.tanggal == target_date:
                    parent_hari_ini_id = log.absensi_harian_id
                    if log.tipe == 'DATANG':
                        if datang_log is None or log.waktu < datang_log.waktu:
                            datang_log = log

                if log.tipe == 'PULANG':
                    is_pulang_shift_malam = (
                        is_shift_malam
                        and log.waktu.date() == esok_hari
                        and log.waktu.time() <= time(13, 0)
                    )
                    if is_pulang_shift_malam:
                        if pulang_log is None or log.waktu > pulang_log.waktu:
                            pulang_log = log
                    elif not is_shift_malam and log.absensi_harian.tanggal == target_date:
                        if pulang_log is None or log.waktu > pulang_log.waktu:
                            pulang_log = log

            # Antisipasi darurat: jika shift malam tidak ada log datang hari ini, parent_hari_ini_id bisa dicari dari log milik hari ini yang bertipe APEL jika ada
            if not parent_hari_ini_id:
                for log in logs:
                    if log.absensi_harian.tanggal == target_date:
                        parent_hari_ini_id = log.absensi_harian_id
                        break

            if not parent_hari_ini_id:
                continue

            # A. PENILAIAN LOG DATANG
            if datang_log:
                status_awal = cls.evaluate_arrival_status(datang_log.waktu.time(), jadwal_kerja.waktu_datang, rules)
                if not pulang_log and not is_shift_malam:
                    if status_awal == 'Tepat Waktu':
                        datang_log.status_ketepatan = 'Cepat Pulang'
                    else:
                        datang_log.status_ketepatan = f"{status_awal} + Cepat Pulang"
                else:
                    datang_log.status_ketepatan = status_awal
                
                child_updates.append(datang_log)
                parent_ids_to_present.add(parent_hari_ini_id)

            # B. PENILAIAN LOG PULANG
            if pulang_log:
                if is_shift_malam and pulang_log.absensi_harian.tanggal == esok_hari:
                    parent_ids_to_revert.add(pulang_log.absensi_harian_id)
                    pulang_log.absensi_harian_id = parent_hari_ini_id 
                
                if not datang_log and not is_shift_malam:
                    pulang_log.status_ketepatan = 'Terlambat Berat'
                else:
                    if pulang_log.waktu.time() < jadwal_kerja.waktu_pulang:
                        pulang_log.status_ketepatan = 'Cepat Pulang'
                    else:
                        pulang_log.status_ketepatan = 'Tepat Waktu'
                
                child_updates.append(pulang_log)
                parent_ids_to_present.add(parent_hari_ini_id)

            # C. PENILAIAN LOG APEL
            for log in logs:
                is_mesin_apel = log.devicename and log.devicename.strip().lower() == 'apel'
                
                if is_mesin_apel and log.absensi_harian.tanggal == target_date:
                    
                    # FIX PERBAIKAN: Karena jadwal_kerja langsung mengarah ke DetailKategoriJadwalDinas
                    is_wajib_apel = False
                    if jadwal_kerja:
                        # Langsung tembak field master ke tabel KategoriJadwalDinas melalui foreign key
                        is_reguler = jadwal_kerja.kategori_dinas and 'reguler' in jadwal_kerja.kategori_dinas.kategori_dinas.lower()
                        is_pagi = jadwal_kerja.kategori_jadwal and 'pagi' in jadwal_kerja.kategori_jadwal.lower()
                        
                        if is_reguler or is_pagi:
                            is_wajib_apel = True
                    
                    log.tipe = 'APEL'
                    if is_wajib_apel:
                        if log.waktu.time() <= time(7, 50):
                            log.status_ketepatan = 'Apel'
                        else:
                            log.status_ketepatan = 'Tidak Apel'
                    else:
                        log.status_ketepatan = 'Bukan Kewajiban Apel (Abaikan)'
                        
                    child_updates.append(log)
                    parent_ids_to_present.add(parent_hari_ini_id)

        # -----------------------------------------------------------------
        # EKSEKUSI MASSAL DATABASE (BULK OPERATIONS)
        # -----------------------------------------------------------------
        if child_updates:
            LogAktivitasAbsen.objects.bulk_update(child_updates, fields=['status_ketepatan', 'absensi_harian_id', 'tipe'])

        if parent_ids_to_present:
            # IZIN dan DINAS adalah keputusan administratif dan tidak boleh
            # ditimpa. Status sistem ALPA/LIBUR boleh dikoreksi menjadi HADIR
            # bila pada penilaian ulang ditemukan log yang sah.
            AbsensiHarian.objects.filter(
                id__in=parent_ids_to_present,
            ).exclude(
                status_final__in=['HADIR', 'IZIN', 'DINAS'],
            ).update(
                status_final='HADIR',
                keterangan='Sistem: Hadir berdasarkan log presensi yang telah direkonsiliasi.',
            )

        if parent_ids_to_revert:
            AbsensiHarian.objects.filter(
                id__in=parent_ids_to_revert,
                logs__isnull=True,
                keterangan__startswith='Sistem:',
            ).exclude(
                status_final__in=['IZIN', 'DINAS'],
            ).update(status_final='', keterangan='')
            
        return len(child_updates)
    
    
class NewAttendanceOrchestrator:

    @classmethod
    def execute_by_structure(cls, target_date, instalasi_id=None, sub_bidang_id=None, bidang_id=None, unor_id=None, is_final_stage: bool = False):
        """
        Orchestrator Tunggal Arsitektur Harian Parent-Child.
        Mendukung evaluasi dinamis aman untuk Shift Malam, Lintas Hari, dan Hari Libur Pegawai.
        """
        bulan_target = target_date.month
        tahun_target = target_date.year
        hari_ini = date.today()

        # 1. Scope Cakupan Struktur Organisasi
        scope_filter = Q(bulan=bulan_target, tahun=tahun_target)
        if instalasi_id: scope_filter &= Q(instalasi_id=instalasi_id)
        if sub_bidang_id: scope_filter &= Q(sub_bidang_id=sub_bidang_id)
        if bidang_id: scope_filter &= Q(bidang_id=bidang_id)
        if unor_id: scope_filter &= Q(unor_id=unor_id)

        scope_pegawai_qs = JenisSDMPerinstalasi.objects.filter(scope_filter)
        if not scope_pegawai_qs.exists():
            return False, "Tidak ada data pegawai aktif dalam ruang lingkup struktur organisasi yang dipilih."

        user_ids = list(scope_pegawai_qs.values_list('pegawai_id', flat=True))

        with transaction.atomic():
            
            # TAHAP A: Petakan log mentah mesin ke tabel Child LogAktivitasAbsen
            success_map, msg_map = NewAttendanceMappingService.process_logs_batch(
                target_date=target_date, 
                user_ids=user_ids
            )
            if not success_map:
                return False, f"Gagal di Tahap Pemetaan Log: {msg_map}"

            # TAHAP B: Jalankan Rekonsiliasi Ketepatan Waktu Berpasangan & Mutasi Shift Malam
            total_reconciled = NewAttendanceReconciliationService.reconcile_batch(
                target_date=target_date,
                sdm_perinstalasi_queryset=scope_pegawai_qs,
            )

            # TAHAP C: VERIFIKASI PEGAWAI MANGKIR & HARI LIBUR (Hanya untuk HARI KEMARIN ke belakang)
            total_tk = 0
            total_libur_processed = 0 
            
            if target_date < hari_ini and is_final_stage:
                
                # =========================================================================
                # INTEGRASI LOGIKA 1: IDENTIFIKASI VARIABEL KALENDER GLOBAL
                # =========================================================================
                is_hari_minggu = target_date.weekday() == 6
                libur_nasional_obj = HariLibur.objects.filter(tanggal=target_date).first()
                is_libur_nasional = libur_nasional_obj is not None
                keterangan_libur_kalender = libur_nasional_obj.keterangan if is_libur_nasional else "Hari Ahad / Minggu"

                # =========================================================================
                # LOGIKA 2: PROSES PENANDAAN PEGAWAI TIDAK APEL (Aman dari Pegawai Libur)
                # =========================================================================
                # Pegawai wajib apel diambil dari jadwal yang sudah disetujui.
                # Data draft hanya menjadi fallback bila pengajuan induknya
                # sudah berstatus disetujui (kompatibilitas data lama).
                sdm_ids = [sdm.id for sdm in scope_pegawai_qs]
                kondisi_wajib_apel = (
                    Q(kategori_jadwal__kategori_dinas__kategori_dinas__iexact='Reguler')
                    | Q(kategori_jadwal__kategori_jadwal__icontains='Pagi')
                )
                if is_hari_minggu or is_libur_nasional:
                    kondisi_wajib_apel &= Q(
                        kategori_jadwal__kategori_dinas__kategori_dinas__iexact='Piket'
                    )

                jadwal_disetujui_hari_ini = ApprovedJadwalDinasSDM.objects.filter(
                    tanggal=target_date,
                    pegawai_id__in=sdm_ids,
                    is_approved=True,
                )
                approved_day_sdm_ids = set(
                    jadwal_disetujui_hari_ini.values_list('pegawai_id', flat=True)
                )
                jadwal_wajib_apel_disetujui = jadwal_disetujui_hari_ini.filter(
                    kondisi_wajib_apel,
                ).exclude(
                    kategori_jadwal__kategori_dinas__kategori_dinas__icontains='Libur'
                )
                pegawai_wajib_apel_ids = set(
                    jadwal_wajib_apel_disetujui.values_list(
                        'pegawai__pegawai_id',
                        flat=True,
                    )
                )

                jadwal_wajib_apel_legacy = JadwalDinasSDM.objects.filter(
                    tanggal=target_date,
                    pegawai_id__in=set(sdm_ids) - approved_day_sdm_ids,
                    pegawai__status='disetujui',
                ).filter(
                    kondisi_wajib_apel,
                ).exclude(
                    kategori_jadwal__kategori_dinas__kategori_dinas__icontains='Libur'
                )
                pegawai_wajib_apel_ids.update(
                    jadwal_wajib_apel_legacy.values_list(
                        'pegawai__pegawai_id',
                        flat=True,
                    )
                )

                pegawai_sudah_tap_apel = set(LogAktivitasAbsen.objects.filter(
                    absensi_harian__tanggal=target_date,
                    absensi_harian__pegawai_id__in=pegawai_wajib_apel_ids,
                    devicename__iexact='apel'
                ).values_list('absensi_harian__pegawai_id', flat=True))

                parent_absensi_map = {
                    absb.pegawai_id: absb.id 
                    for absb in AbsensiHarian.objects.select_for_update().filter(
                        tanggal=target_date,
                        pegawai_id__in=pegawai_wajib_apel_ids,
                    )
                }

                # Hapus penanda otomatis milik pegawai yang setelah perubahan
                # jadwal tidak lagi wajib apel.
                LogAktivitasAbsen.objects.filter(
                    absensi_harian__tanggal=target_date,
                    tipe='APEL',
                    devicename='Sistem Otomatis',
                ).exclude(
                    absensi_harian__pegawai_id__in=pegawai_wajib_apel_ids,
                ).delete()

                for p_id in pegawai_wajib_apel_ids:
                    parent_id = parent_absensi_map.get(p_id)
                    if not parent_id:
                        continue

                    synthetic_logs = LogAktivitasAbsen.objects.filter(
                        absensi_harian_id=parent_id,
                        tipe='APEL',
                        devicename='Sistem Otomatis',
                    ).order_by('pk')

                    if p_id in pegawai_sudah_tap_apel:
                        # Tapping asli yang datang belakangan membatalkan
                        # penanda mangkir hasil proses sebelumnya.
                        synthetic_logs.delete()
                        continue

                    synthetic_log = synthetic_logs.first()
                    if synthetic_log:
                        synthetic_logs.exclude(pk=synthetic_log.pk).delete()
                        synthetic_log.waktu = datetime.combine(target_date, time(7, 30))
                        synthetic_log.status_ketepatan = 'Mangkir Apel'
                        synthetic_log.save(update_fields=['waktu', 'status_ketepatan'])
                    else:
                        LogAktivitasAbsen.objects.create(
                            absensi_harian_id=parent_id,
                            tipe='APEL',
                            waktu=datetime.combine(target_date, time(7, 30)),
                            status_ketepatan='Mangkir Apel',
                            devicename='Sistem Otomatis',
                        )
                    
                # =========================================================================
                # LOGIKA 3: KALENDER GLOBAL, KEMUDIAN JADWAL HARIAN PEGAWAI
                # =========================================================================
                schedule_types_by_user = defaultdict(set)

                approved_schedule_rows = ApprovedJadwalDinasSDM.objects.filter(
                    tanggal=target_date,
                    pegawai_id__in=sdm_ids,
                    is_approved=True,
                ).values_list(
                    'pegawai_id',
                    'pegawai__pegawai_id',
                    'kategori_jadwal__kategori_dinas__kategori_dinas',
                )

                approved_sdm_ids = set()
                for sdm_id, user_id, schedule_type in approved_schedule_rows:
                    approved_sdm_ids.add(sdm_id)
                    schedule_types_by_user[user_id].add(schedule_type)

                # Fallback khusus data lama yang pengajuannya sudah disetujui tetapi
                # salinan ApprovedJadwalDinasSDM belum terbentuk.
                legacy_schedule_rows = JadwalDinasSDM.objects.filter(
                    tanggal=target_date,
                    pegawai_id__in=set(sdm_ids) - approved_sdm_ids,
                    pegawai__status='disetujui',
                ).values_list(
                    'pegawai__pegawai_id',
                    'kategori_jadwal__kategori_dinas__kategori_dinas',
                )
                for user_id, schedule_type in legacy_schedule_rows:
                    schedule_types_by_user[user_id].add(schedule_type)

                is_tanggal_merah = is_hari_minggu or is_libur_nasional
                jadwal_libur_ids = []
                jadwal_dinas_ids = []
                jadwal_belum_dibuat_ids = []

                for sdm in scope_pegawai_qs:
                    obligation = classify_daily_obligation(
                        is_calendar_holiday=is_tanggal_merah,
                        schedule_types=schedule_types_by_user.get(sdm.pegawai_id, set()),
                    )
                    if obligation == HOLIDAY:
                        jadwal_libur_ids.append(sdm.pegawai_id)
                    elif obligation == WORK:
                        jadwal_dinas_ids.append(sdm.pegawai_id)
                    elif obligation == MISSING_SCHEDULE:
                        jadwal_belum_dibuat_ids.append(sdm.pegawai_id)

                if is_tanggal_merah:
                    keterangan_final_libur = f"Sistem: Libur kalender ({keterangan_libur_kalender}); tidak ada jadwal piket aktif."
                else:
                    keterangan_final_libur = "Sistem: Libur sesuai jadwal dinas pegawai."

                # =========================================================================
                # LOGIKA 4: EKSEKUSI MUTASI DATA STATUS FINAL
                # =========================================================================
                
                # Eksekusi A: Amankan dan kunci status 'LIBUR' (Mengunci rekor kosong yang tidak tapping)
                libur_parents = AbsensiHarian.objects.filter(
                    pegawai_id__in=jadwal_libur_ids,
                    tanggal=target_date
                ).exclude(
                    status_final__in=['HADIR', 'IZIN', 'DINAS']
                )

                total_libur_processed = libur_parents.count()
                libur_parents.update(
                    status_final='LIBUR',
                    keterangan=keterangan_final_libur
                )
                

                # Eksekusi B: Vonis 'ALPA' bagi yang terjadwal aktif kerja (Hari Biasa atau Piket di hari libur) tapi bolos
                # Gunakan Q filter untuk mengantisipasi status_final berupa string kosong ATAU NULL ATAU 'Belum Presensi'
                real_log_exists = LogAktivitasAbsen.objects.filter(
                    absensi_harian_id=OuterRef('pk'),
                ).exclude(devicename='Sistem Otomatis')

                mangkir_parents = AbsensiHarian.objects.filter(
                    pegawai_id__in=jadwal_dinas_ids,
                    tanggal=target_date,
                ).exclude(
                    # KUNCI: Kecualikan yang sudah jelas status sahnya. 
                    # Apapun sisa statusnya (kosong, 'Belum Presensi', salah ketik), sikat jadi ALPA.
                    status_final__in=['HADIR', 'IZIN', 'DINAS']
                ).annotate(
                    has_real_log=Exists(real_log_exists),
                ).filter(has_real_log=False)

                total_tk = mangkir_parents.count()
                mangkir_parents.update(
                    status_final='ALPA',
                    keterangan="Sistem: Mangkir. Hari kerja aktif tetapi tidak ditemukan log tapping mesin hingga batas waktu evaluasi."
                )

                # Hari kerja biasa tanpa jadwal tetap dinilai ALPA, tetapi
                # keterangannya dibedakan dari mangkir pada jadwal aktif.
                jadwal_kosong_parents = AbsensiHarian.objects.filter(
                    pegawai_id__in=jadwal_belum_dibuat_ids,
                    tanggal=target_date,
                ).exclude(
                    status_final__in=['IZIN', 'DINAS'],
                )

                total_tk_jadwal_kosong = jadwal_kosong_parents.count()
                jadwal_kosong_parents.update(
                    status_final='ALPA',
                    keterangan=(
                        'Sistem: Alpa karena jadwal dinas pegawai belum '
                        'dibuat atau belum disetujui untuk tanggal ini.'
                    ),
                )
                total_tk += total_tk_jadwal_kosong
                
            else:
                total_tk = 0

        info_pesan = (
            f"Evaluasi Berhasil ({target_date.strftime('%d-%m-%Y')}). "
            f"Scope Pemetaan: {len(user_ids)} Pegawai. Menilai {total_reconciled} log aktivitas, "
            f"memproses {total_libur_processed} pegawai libur, "
            f"dan mendeteksi {total_tk} pegawai mangkir (Tanpa Keterangan)."
        )
        return True, info_pesan
