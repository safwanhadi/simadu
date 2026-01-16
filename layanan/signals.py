from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import LayananCuti, PersetujuanCuti, RiwayatCuti
from .services import CutiApprovalService

@receiver(post_save, sender=LayananCuti)
def create_initial_approval(sender, instance, created, **kwargs):
    """Create initial approval records when a new leave request is created"""
    if created:
        approval_service = CutiApprovalService()
        approval_chain = approval_service.get_approval_chain(instance.pegawai)
        
        # Create approval records for each level in the chain
        for level in approval_chain:
            PersetujuanCuti.objects.get_or_create(
                layanan_cuti=instance,
                level_approval=level,
                defaults={'status': 'Pending'}
            )

@receiver(post_save, sender=PersetujuanCuti)
def update_leave_status(sender, instance, created, **kwargs):
    """Update leave request status when approval is processed"""
    if instance.status in ['Approved', 'Rejected']:
        layanan_cuti = instance.layanan_cuti
        
        if instance.status == 'Rejected':
            # If any approval is rejected, reject the entire leave request
            layanan_cuti.status = 'Ditolak'
        else:
            # Check if this is the final approval
            approval_service = CutiApprovalService()
            next_level = approval_service.get_next_approval_level(layanan_cuti)
            
            if not next_level:
                # This was the final approval
                layanan_cuti.status = 'Disetujui Unor'
                
                # Create riwayat cuti record
                RiwayatCuti.objects.create(
                    layanan_cuti=layanan_cuti,
                    pegawai=layanan_cuti.pegawai,
                    jenis_cuti=layanan_cuti.jenis_cuti,
                    alasan_cuti=layanan_cuti.alasan_cuti,
                    tgl_mulai_cuti=layanan_cuti.tgl_mulai,
                    tgl_akhir_cuti=layanan_cuti.tgl_akhir,
                    lama_cuti=layanan_cuti.lama_cuti,
                    domisili_saat_cuti=layanan_cuti.alamat_cuti,
                    tahun_cuti=layanan_cuti.tahun_cuti,
                    file_pengajuan=layanan_cuti.file_pengajuan,
                    file_pendukung=layanan_cuti.file_pendukung,
                    status_cuti='Selesai'
                )
            else:
                # Update to intermediate approval status
                layanan_cuti.status = f'Disetujui {instance.level_approval.title()}'
        
        layanan_cuti.save()