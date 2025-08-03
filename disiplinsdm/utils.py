import calendar
from datetime import datetime, date, timedelta

# def get_mingguan_lengkap(bulan, tahun):
#     cal = calendar.Calendar(firstweekday=0)
#     minggu = []
#     for minggu_ini in cal.monthdatescalendar(tahun, bulan):
#         aktif = [d for d in minggu_ini if d.month == bulan]
#         if aktif:
#             minggu.append(aktif)
#     return minggu

# def get_mingguan_lengkap(bulan, tahun):
#     from datetime import date, timedelta

#     start_date = date(tahun, bulan, 1)
#     last_day = calendar.monthrange(tahun, bulan)[1]
#     end_date = date(tahun, bulan, last_day)

#     minggu = []
#     hari = start_date
#     while hari <= end_date:
#         minggu_akhir = min(hari + timedelta(days=6), end_date)
#         minggu.append([hari + timedelta(days=i) for i in range((minggu_akhir - hari).days + 1)])
#         hari = minggu_akhir + timedelta(days=1)
#     return minggu

def get_mingguan_lengkap(bulan, tahun):
    # Cari hari pertama dan terakhir bulan
    start_date = date(tahun, bulan, 1)
    last_day = calendar.monthrange(tahun, bulan)[1]
    end_date = date(tahun, bulan, last_day)

    # Geser start_date ke hari Senin sebelumnya (jika belum Senin)
    start_date -= timedelta(days=start_date.weekday())

    minggu = []
    hari = start_date
    while hari <= end_date:
        minggu_akhir = hari + timedelta(days=6)
        minggu.append([hari + timedelta(days=i) for i in range(7) if (hari + timedelta(days=i)).month == bulan])
        hari += timedelta(days=7)

    return minggu


def hitung_total_jam(items, model_penyimpanan_waktu):
    total = 0
    for item in items:
        # Ambil ID kategori_jadwal tergantung tipe objek
        kategori_id = None

        if hasattr(item, 'cleaned_data') and 'kategori_jadwal' in item.cleaned_data:
            kategori = item.cleaned_data.get('kategori_jadwal')
            kategori_id = kategori.pk if kategori else None
        elif hasattr(item, 'initial') and 'kategori_jadwal' in item.initial:
            kategori_id = item.initial.get('kategori_jadwal')
        elif hasattr(item, 'kategori_jadwal_id'):
            kategori_id = item.kategori_jadwal_id
        elif hasattr(item, 'kategori_jadwal') and item.kategori_jadwal:
            kategori_id = item.kategori_jadwal.pk

        # Ambil data shift dari model penyimpanan
        
        try:
            data = None
            if isinstance(kategori_id, int):
                data = model_penyimpanan_waktu.objects.get(pk=kategori_id)
            pass
        except model_penyimpanan_waktu.DoesNotExist:
            data = None

        if data and data.waktu_datang and data.waktu_pulang:
            mulai = datetime.combine(date.today(), data.waktu_datang)
            selesai = datetime.combine(date.today(), data.waktu_pulang)
            if selesai < mulai:
                selesai += timedelta(days=1)  # ini yang benar
            selisih = (selesai - mulai).total_seconds() / 3600
            total += selisih
    return round(total, 1)


#fungsi perhitungan beban kerja berdasarkan hari kerja dan hari libur nasional (hari libur nasional ditambahkan secara manual)
def hitung_standar_jam_kerja(model, bulan, tahun):
    _, total_hari = calendar.monthrange(tahun, bulan)
    jam_kerja = 0
    # kurang lebih 39 jam kerja seminggu
    for hari in range(1, total_hari + 1):
        tanggal = date(tahun, bulan, hari)
        
        # Lewati jika hari libur (berdasarkan model)
        if model.objects.filter(tanggal=tanggal).exists():
            continue

        weekday = tanggal.weekday()
        if weekday >= 0 and weekday <= 3:  # Senin s.d. Kamis
            jam_kerja += 7
        elif weekday == 4:  # Jumat
            jam_kerja += 6.5
        elif weekday == 5:  # Sabtu
            jam_kerja += 4.5
        # Ahad (weekday == 6) diabaikan

    return jam_kerja


def hitung_standar_max_jam_kerja(model, bulan, tahun):
    _, total_hari = calendar.monthrange(tahun, bulan)
    jam_kerja = 0
    # kurang lebih 40 jam kerja dalam seminggu
    for hari in range(1, total_hari + 1):
        tanggal = date(tahun, bulan, hari)
        
        # Lewati jika hari libur (berdasarkan model)
        if model.objects.filter(tanggal=tanggal).exists():
            continue

        weekday = tanggal.weekday()
        if weekday >= 0 and weekday <= 3:  # Senin s.d. Kamis
            jam_kerja += 7.1667  # 7 jam 10 menit
        elif weekday == 4:  # Jumat
            jam_kerja += 6.6667  # 6 jam 40 menit
        elif weekday == 5:  # Sabtu
            jam_kerja += 4.6667  # 4 jam 40 menit
        # Ahad (weekday == 6) diabaikan

    return jam_kerja


# # untuk menghitung total cuti pegawai
# def jam_standar_min_hari(bulan, tahun) -> float:
#     _, total_hari = calendar.monthrange(tahun, bulan)
#     jam_kerja = 0
#     # kurang lebih 40 jam kerja dalam seminggu
#     for hari in range(1, total_hari + 1):
#         tanggal = date(tahun, bulan, hari)
        
#     wd = tanggal.weekday()
#     if wd <= 3: return 7
#     if wd == 4: return 6.5
#     if wd == 5: return 4.5
#     return 0
# untuk menghitung total cuti pegawai
def jam_standar_min_hari(tanggal:date) -> float:    
    wd = tanggal.weekday()
    if wd <= 3: return 7
    if wd == 4: return 6.5
    if wd == 5: return 4.5
    return 0

# def jam_standar_max_hari(bulan, tahun) -> float:
#     _, total_hari = calendar.monthrange(tahun, bulan)
#     jam_kerja = 0
#     # kurang lebih 40 jam kerja dalam seminggu
#     for hari in range(1, total_hari + 1):
#         tanggal = date(tahun, bulan, hari)
        
#     wd = tanggal.weekday()
#     if wd <= 3: return 7.1667
#     if wd == 4: return 6.6667
#     if wd == 5: return 4.6667
#     return 0
def jam_standar_max_hari(tanggal:date) -> float:
    wd = tanggal.weekday()
    if wd <= 3: return 7.1667
    if wd == 4: return 6.6667
    if wd == 5: return 4.6667
    return 0


#sistem approval jadwal
def is_user_authorized_to_approve(user, jenis_sdm):
    try:
        profil = user.profil_admin
    except Exception:
        return False

    return (
        profil and (
            jenis_sdm.unor and jenis_sdm.unor.nama_pimpinan == user or
            jenis_sdm.bidang and jenis_sdm.bidang.nama_pimpinan == user or
            jenis_sdm.sub_bidang and jenis_sdm.sub_bidang.nama_pimpinan == user
        )
    )
