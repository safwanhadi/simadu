import os
from docxtpl import DocxTemplate
from django.conf import settings
from django.utils import timezone
from django.utils.formats import date_format
from django.template.defaultfilters import date as d_filter

from dokumen.models import RiwayatJabatan


def safe_str(value, default="-"):
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default


def get_profil(pegawai):
    return getattr(pegawai, "profil_user", None)


def format_ttl(profil):
    if not profil:
        return "-"

    tempat = safe_str(profil.tmp_lahir)

    if profil.tgl_lahir:
        tanggal = date_format(profil.tgl_lahir, "d F Y")
    else:
        tanggal = "-"

    return f"{tempat}, {tanggal}"


def get_tahun_lulus(ijazah):
    if ijazah and ijazah.tgl_lulus:
        return ijazah.tgl_lulus.year
    return "-"


def get_jabatan_terakhir(pegawai):
    jabatan = (
        RiwayatJabatan.objects
        .filter(pegawai=pegawai)
        .select_related(
            "nama_jabatan",
            "jenjang_jabatan",
            "unor",
            "bidang",
            "sub_bidang",
            "instalasi",
        )
        .order_by("-tmt_jabatan", "-created_at")
        .first()
    )

    if not jabatan:
        return "-", "RS Mandalika Provinsi NTB"

    nama_jabatan = (
        jabatan.detail_nama_jabatan
        or jabatan.nama_jabatan
        or jabatan.jenjang_jabatan
        or "-"
    )

    unit = (
        jabatan.instalasi
        or jabatan.sub_bidang
        or jabatan.bidang
        or jabatan.unor
        or "RS Mandalika Provinsi NTB"
    )

    return safe_str(nama_jabatan), safe_str(unit)


def build_context_sip(layanan_sip):
    pegawai = layanan_sip.pegawai
    profil = get_profil(pegawai)
    ijazah = layanan_sip.ijazah
    str_profesi = layanan_sip.str_profesi

    jabatan_sekarang, instalasi = get_jabatan_terakhir(pegawai)

    return {
        "nama": safe_str(pegawai.full_name_2),
        "nik": safe_str(profil.no_ktp if profil else None),
        "ttl": format_ttl(profil),
        "pendidikan": safe_str(profil.pendidikan if profil else None),
        "alumni": safe_str(ijazah.nama_sek if ijazah else None),
        "tahun_lulus": get_tahun_lulus(ijazah),
        "alamat": safe_str(profil.alamat if profil else None),
        "no_hp": safe_str(profil.no_hp if profil else None),
        "email": safe_str(profil.email_pribadi if profil else None),
        "jabatan_sekarang": jabatan_sekarang,
        "instalasi": instalasi,
        "instansi": "RS Mandalika Provinsi NTB",
        "no_str": safe_str(str_profesi.no_str if str_profesi else None),
        "tanggal_surat": d_filter(timezone.now(), "j F Y"),
        "nama_ttd": safe_str(pegawai.full_name),
    }


def render_docx_template(template_path, output_path, context):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(output_path)

    return output_path

def generate_rekomendasi_sip(layanan_sip):
    context = build_context_sip(layanan_sip)

    template_path = os.path.join(
        settings.BASE_DIR,
        "templates_word",
        "sip",
        "rekomendasi_sip.docx",
    )

    output_path = os.path.join(
        settings.MEDIA_ROOT,
        "layanan",
        "sip",
        "generated",
        f"rekomendasi_sip_{layanan_sip.pk}.docx",
    )

    return render_docx_template(template_path, output_path, context)

def generate_permohonan_rekomendasi_sip(layanan_sip):
    context = build_context_sip(layanan_sip)

    template_path = os.path.join(
        settings.BASE_DIR,
        "templates_word",
        "sip",
        "permohonan_rekomendasi_sip.docx",
    )

    output_path = os.path.join(
        settings.MEDIA_ROOT,
        "layanan",
        "sip",
        "generated",
        f"permohonan_rekomendasi_sip_{layanan_sip.pk}.docx",
    )

    return render_docx_template(template_path, output_path, context)


def generate_surat_kecukupan_skp(layanan_sip):
    context = build_context_sip(layanan_sip)

    template_path = os.path.join(
        settings.BASE_DIR,
        "templates_word",
        "sip",
        "surat_kecukupan_skp.docx",
    )

    output_path = os.path.join(
        settings.MEDIA_ROOT,
        "layanan",
        "sip",
        "generated",
        f"surat_kecukupan_skp_{layanan_sip.pk}.docx",
    )

    return render_docx_template(template_path, output_path, context)