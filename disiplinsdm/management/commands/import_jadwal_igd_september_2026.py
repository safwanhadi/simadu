from collections import Counter
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from disiplinsdm.models import (
    DetailKategoriJadwalDinas,
    JadwalDinasSDM,
    JenisSDMPerinstalasi,
)
from myaccount.models import Users


TAHUN = 2026
BULAN = 9

# Pegawai nomor satu (Yuyun) sengaja tidak dimasukkan.
# Tanda petik pada foto dianggap sebagai penanda koreksi tulisan, bukan kode shift.
JADWAL = {
    "Anindhita Pangestika": "PHCS P M T L P S M T L P S M T L P LX M T L P S M T L P S M T L",
    "Genta Faesal Atsani": "S S M T L S P M T L S P M T L PHCS P M T L S LX M T L S P M T L",
    "Kevin Tanoto": "S M T L P S M T L P LX M T L S S M T L P PHCS M T L P S M T L P",
    "dr Lintang Usnaini": "P M T L S P M T L S P M T L PHCS LX M T L S P M T L S P M T L S",
    "I Made Bayu Sanjaya": "M T L P M M T L LX S M T L PHCS LX M T L P S M T L P S M T L P S",
    "Baiq Saka Muara Ardian": "L P C C T L P S M T L P S M T L P S M T L P PHCS M T L P S M T",
    "Dian Novita Rahmah": "T L PHCS P M T L PHCS P M T L S P M T L S P M T L S P M T L LX P M",
    "Dede Martha Adi Toma": "T L S M T L P S M T L P S M T L P S M T L P PHCS M T L P S M T",
    "Muhammad Hardi Tenggara": "L S P M T L S LX M T L P PHCMID M T L S P M T L P S P M T L S P M",
    "Suci Ariani": "P PHCS M T L P P M T L P S M T L S P M T L P PHCS M T L LX P M T L",
    "dr. LALU YUDI PRAJADIANTA": "S M T L P S M T L S S M T L S S M T L S LX M T L P S M T L PHCS",
    "Anis": "M T L S P M T L PHCS LX M T L S P M T L S P M T L S P M T L S P",
    "dr. Akbar Dwi Juliardi NR": "M T L P S M T L S P M T L S M M T L S P M T L LX S M T L PHCS P",
    "dr. I Gede Andre Putra Rio Deyanta": "M T L S S M T L S P M T L S P M T L LX S M T L PHCS M T L PHCS M M",
    "Clarence Marks Alief": "L S S M T L S P M T L S P M T L PHCS LX M T L S P M T L PHCMID P M T",
    "Baiq Jema Marandra Emkamas": "P P P P PHCS PHCS L PHCS P P PHCS PHCS PHCS L LX P P S PHCS PHCS L S P S S PHCS PHCS L P LX",
}

KATEGORI = {
    "P": "Pagi",
    "S": "Siang",
    "M": "Malam",
    "T": "Lepas Piket",
    "L": "Libur",
    "LX": "Libur Extra",
    "C": "Cuti",
    "MID": "Middle",
}


def normalisasi_nama(value):
    return " ".join((value or "").casefold().replace(".", " ").split())


class Command(BaseCommand):
    help = "Mengimpor jadwal jaga dokter IGD bulan September 2026 dari lembar jadwal."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validasi pencocokan tanpa menyimpan perubahan.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        kategori = self._ambil_kategori()
        users = {normalisasi_nama(user.full_name): user for user in Users.objects.all()}
        ditemukan = []
        dilewati = []

        for nama in JADWAL:
            user = users.get(normalisasi_nama(nama))
            if user is None:
                dilewati.append(nama)
            else:
                ditemukan.append((nama, user))

        instalasi_id = self._tentukan_instalasi_igd([user.pk for _, user in ditemukan])
        dibuat = 0
        diperbarui = 0
        tidak_berubah = 0
        dikembalikan_ke_draft = 0

        for nama, user in ditemukan:
            roster = self._ambil_atau_buat_roster(user, instalasi_id)
            kode_harian = JADWAL[nama].split()
            if len(kode_harian) != 30:
                raise CommandError(f"Jadwal {nama} berisi {len(kode_harian)} hari, seharusnya 30.")

            roster_berubah = False
            for hari, kode_sumber in enumerate(kode_harian, start=1):
                kode, catatan = self._urai_kode(kode_sumber)
                tanggal = date(TAHUN, BULAN, hari)
                jadwal_lama = JadwalDinasSDM.objects.filter(
                    pegawai=roster,
                    tanggal=tanggal,
                ).first()
                jadwal_berubah = (
                    jadwal_lama is None
                    or jadwal_lama.kategori_jadwal_id != kategori[kode].pk
                    or jadwal_lama.catatan != catatan
                )
                _, created = JadwalDinasSDM.objects.update_or_create(
                    pegawai=roster,
                    tanggal=tanggal,
                    defaults={"kategori_jadwal": kategori[kode], "catatan": catatan},
                )
                dibuat += int(created)
                diperbarui += int(not created and jadwal_berubah)
                tidak_berubah += int(not jadwal_berubah)
                roster_berubah = roster_berubah or jadwal_berubah

            # Jadwal yang berubah harus ditetapkan ulang oleh kepala ruangan/instalasi.
            # Salinan jadwal aktif yang lama tidak dihapus agar tetap berlaku sampai
            # proses penetapan berikutnya selesai.
            if roster_berubah and roster.status != "draft":
                roster.status = "draft"
                roster.alasan_penolakan = ""
                roster.save(update_fields=["status", "alasan_penolakan", "updated_at"])
                dikembalikan_ke_draft += 1

        if options["dry_run"]:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("DRY RUN: tidak ada perubahan yang disimpan."))

        self.stdout.write(
            self.style.SUCCESS(
                f"Pegawai diproses: {len(ditemukan)}; jadwal baru: {dibuat}; "
                f"jadwal diperbarui: {diperbarui}; tidak berubah: {tidak_berubah}; "
                f"persetujuan dikembalikan ke draft: {dikembalikan_ke_draft}."
            )
        )
        if dilewati:
            self.stdout.write(self.style.WARNING("Pegawai dilewati: " + ", ".join(dilewati)))

    def _ambil_kategori(self):
        hasil = {}
        for kode, nama in KATEGORI.items():
            queryset = DetailKategoriJadwalDinas.objects.filter(kategori_jadwal__iexact=nama)
            if queryset.count() > 1:
                # Shift pada lembar IGD tidak dibedakan menurut hari kerja reguler.
                queryset = queryset.filter(hari="")
            if queryset.count() != 1:
                raise CommandError(
                    f"Kategori jadwal '{nama}' harus tersedia tepat satu kali; "
                    f"ditemukan {queryset.count()}."
                )
            hasil[kode] = queryset.get()
        return hasil

    def _tentukan_instalasi_igd(self, user_ids):
        riwayat = JenisSDMPerinstalasi.objects.filter(
            pegawai_id__in=user_ids,
            instalasi__instalasi__iexact="IGD",
        ).values_list("instalasi_id", flat=True)
        hitungan = Counter(riwayat)
        if not hitungan:
            raise CommandError("Instalasi IGD tidak dapat ditentukan dari riwayat pegawai yang cocok.")
        return hitungan.most_common(1)[0][0]

    def _ambil_atau_buat_roster(self, user, instalasi_id):
        roster = JenisSDMPerinstalasi.objects.filter(
            pegawai=user,
            bulan=BULAN,
            tahun=TAHUN,
            instalasi_id=instalasi_id,
        ).first()
        if roster:
            return roster

        riwayat = JenisSDMPerinstalasi.objects.filter(
            pegawai=user,
            instalasi_id=instalasi_id,
        ).order_by("-tahun", "-bulan", "-pk").first()
        return JenisSDMPerinstalasi.objects.create(
            pegawai=user,
            instalasi_id=instalasi_id,
            jenis_sdm_id=getattr(riwayat, "jenis_sdm_id", None),
            unor_id=getattr(riwayat, "unor_id", None),
            bidang_id=getattr(riwayat, "bidang_id", None),
            sub_bidang_id=getattr(riwayat, "sub_bidang_id", None),
            bulan=BULAN,
            tahun=TAHUN,
            status="draft",
        )

    @staticmethod
    def _urai_kode(kode_sumber):
        if kode_sumber.startswith("PHC"):
            return kode_sumber[3:], "PHC"
        return kode_sumber, None
