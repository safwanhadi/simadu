from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from disiplinsdm.models import ApprovedJadwalDinasSDM, PolaKerjaPegawai


class Command(BaseCommand):
    KETERANGAN_INISIALISASI = (
        'Inisialisasi otomatis dari jadwal dinas disetujui terakhir.'
    )

    help = (
        'Inisialisasi pola kerja pegawai dari bulan jadwal terakhir yang '
        'sudah disetujui. Tanpa --apply command hanya menampilkan pratinjau.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            dest='apply_changes',
            help='Simpan hasil inisialisasi ke database.',
        )
        parser.add_argument(
            '--bersihkan-nonaktif',
            action='store_true',
            help=(
                'Bersihkan pola milik pegawai nonaktif yang dibuat oleh '
                'command inisialisasi ini. Tanpa --apply hanya pratinjau.'
            ),
        )

    def handle(self, *args, **options):
        apply_changes = options['apply_changes']
        show_details = options['verbosity'] >= 2
        if options['bersihkan_nonaktif']:
            self._bersihkan_nonaktif(apply_changes, show_details)
            return

        mode = 'APPLY' if apply_changes else 'DRY-RUN'
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Inisialisasi pola kerja dari jadwal terakhir [{mode}]'
        ))

        schedule_rows = (
            ApprovedJadwalDinasSDM.objects.filter(
                is_approved=True,
                pegawai__status='disetujui',
                pegawai__pegawai__is_active=True,
            )
            .values_list(
                'pegawai__pegawai_id',
                'tanggal',
                'kategori_jadwal__kategori_dinas__kategori_dinas',
            )
            .order_by('pegawai__pegawai_id', '-tanggal')
        )
        latest_by_employee = {}
        for employee_id, schedule_date, category in schedule_rows.iterator(
            chunk_size=5000
        ):
            period = (schedule_date.year, schedule_date.month)
            current = latest_by_employee.get(employee_id)
            if current is None:
                current = {'period': period, 'categories': set()}
                latest_by_employee[employee_id] = current
            if current['period'] == period:
                current['categories'].add((category or '').strip().lower())

        existing_employee_ids = set(
            PolaKerjaPegawai.objects.values_list('pegawai_id', flat=True)
        )

        counters = {
            'shift': 0,
            'reguler': 0,
            'sudah_ada': 0,
            'tidak_dapat_ditentukan': 0,
        }

        to_create = []
        with transaction.atomic():
            for employee_id, latest in latest_by_employee.items():
                year, month = latest['period']
                if employee_id in existing_employee_ids:
                    counters['sudah_ada'] += 1
                    continue

                normalized = latest['categories']

                if any('piket' in category for category in normalized):
                    pola_kerja = PolaKerjaPegawai.SHIFT
                elif any('reguler' in category for category in normalized):
                    pola_kerja = PolaKerjaPegawai.REGULER
                else:
                    counters['tidak_dapat_ditentukan'] += 1
                    if show_details:
                        self.stdout.write(self.style.WARNING(
                            f'LEWATI pegawai_id={employee_id}: jadwal terakhir '
                            f'{month:02d}/{year} hanya Libur/tidak berkategori.'
                        ))
                    continue

                counters[pola_kerja] += 1
                mulai = date(year, month, 1)
                if show_details:
                    self.stdout.write(
                        f'{pola_kerja.upper():7} pegawai_id={employee_id} '
                        f'berlaku_mulai={mulai:%Y-%m-%d}'
                    )
                if apply_changes:
                    to_create.append(PolaKerjaPegawai(
                        pegawai_id=employee_id,
                        pola_kerja=pola_kerja,
                        berlaku_mulai=mulai,
                        keterangan=(
                            self.KETERANGAN_INISIALISASI
                        ),
                    ))

            if apply_changes and to_create:
                PolaKerjaPegawai.objects.bulk_create(to_create)

            if not apply_changes:
                transaction.set_rollback(True)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Ringkasan: '
            f"Shift={counters['shift']}, "
            f"Reguler={counters['reguler']}, "
            f"Sudah memiliki pola={counters['sudah_ada']}, "
            'Tidak dapat ditentukan='
            f"{counters['tidak_dapat_ditentukan']}."
        ))
        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                'Tidak ada data yang disimpan. Jalankan ulang dengan --apply.'
            ))

    def _bersihkan_nonaktif(self, apply_changes, show_details):
        mode = 'APPLY' if apply_changes else 'DRY-RUN'
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Pembersihan pola hasil inisialisasi pegawai nonaktif [{mode}]'
        ))
        queryset = PolaKerjaPegawai.objects.filter(
            pegawai__is_active=False,
            keterangan=self.KETERANGAN_INISIALISASI,
        ).order_by('pegawai_id', 'berlaku_mulai', 'pk')
        jumlah = queryset.count()

        if show_details:
            for pola in queryset.iterator(chunk_size=2000):
                self.stdout.write(
                    f'HAPUS pegawai_id={pola.pegawai_id} '
                    f'pola={pola.pola_kerja} '
                    f'berlaku_mulai={pola.berlaku_mulai:%Y-%m-%d}'
                )

        if apply_changes and jumlah:
            queryset.delete()

        self.stdout.write(self.style.SUCCESS(
            f'Ringkasan: pola hasil inisialisasi pegawai nonaktif={jumlah}.'
        ))
        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                'Tidak ada data yang dihapus. Jalankan ulang dengan '
                '--bersihkan-nonaktif --apply.'
            ))
