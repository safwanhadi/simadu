from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.http import HttpResponse
from django.contrib import messages
from datetime import datetime, date
import os
import qrcode
from io import BytesIO
import locale

#python docx --> library for generate docx
from num2words import num2words
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from bs4 import BeautifulSoup
from docx import Document as CreateDocument
from docx.document import Document
from docx.shared import Inches, Mm, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

#reportlab --> libary for generate pdf
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.pagesizes import letter, A4, landscape, portrait, inch, mm, legal
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Frame, NextPageTemplate, PageBreak, BaseDocTemplate, Spacer
from reportlab.pdfbase.pdfmetrics import getFont, getAscentDescent

from layanan.models import LayananGajiBerkala, LayananCuti, LayananUsulanDiklat, LayananUsulanInovasi, VerifikasiCuti
from dokumen.models import RiwayatDiklat, RiwayatPenempatan
from .models import TextSPTDiklat
from .forms import TextSPTDiklatForm
# Create your views here.


locale.setlocale(locale.LC_ALL, 'id_ID.utf-8')

def clear_document(doc):
    for element in doc.element.body:
        doc.element.body.remove(element)
    
def get_string_date_from_datetime(tanggal):
    tanggal_sekarang = date.today()
    try:
        get_tanggal = datetime.strftime(tanggal, "%d %B %Y")
        return get_tanggal
    except Exception:
        return datetime.strftime(tanggal_sekarang, "%d %B %Y")


#generate pdf
def capaiananak(request, kat, bulan, tahun):
    response = HttpResponse(content_type='application/pdf')
    today = datetime.today()
    d = today.strftime('%Y-%m-%d')
    response['Content-Disposition'] = f'inline: filename="{d}.pdf"'
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setPageSize(portrait(A4))
    p.setTitle(f'Capaian Program Anak - Diunduh - {d}')
    p.drawCentredString(400, 510, 'LAPORAN CAPAIAN PROGRAM KESEHATAN ANAK')
    p.line(50, 500, 760, 500)


alignment_dict = {'justify': WD_PARAGRAPH_ALIGNMENT.JUSTIFY,
                  'center': WD_PARAGRAPH_ALIGNMENT.CENTER,
                  'centre': WD_PARAGRAPH_ALIGNMENT.CENTER,
                  'right': WD_PARAGRAPH_ALIGNMENT.RIGHT,
                  'left': WD_PARAGRAPH_ALIGNMENT.LEFT}

document:Document = CreateDocument()
def add_content(doc=CreateDocument(), content="", content2="", style=None, space_before=0, space_after=0, tab=0, font_name="Times New Roman", font_size=12,
                set_bold=False, set_italic=False, set_underline=False, align="justify", line_spacing=0, keep_together=False, keep_with_next=False, 
                page_break_before=False, widow_control=False, left_indent=0):
    paragraph = doc.add_paragraph(content, style=style)
    font = paragraph.style.font
    font.name = font_name
    font.size = Pt(font_size)
    font.bold = set_bold
    font.italic = set_italic
    font.underline = set_underline
    paragraph.paragraph_format.alignment = alignment_dict.get(align.lower())
    paragraph.paragraph_format.space_before = Pt(space_before)
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.line_spacing = Pt(line_spacing)
    paragraph.paragraph_format.keep_together = keep_together
    paragraph.paragraph_format.keep_with_next = keep_with_next
    paragraph.paragraph_format.page_break_before = page_break_before
    paragraph.paragraph_format.widow_control = widow_control
    paragraph.paragraph_format.tab_stops.add_tab_stop(Inches(tab))
    paragraph.paragraph_format.left_indent = Mm(left_indent)
    data = paragraph.add_run(content2)
    data.bold = set_bold
    data.underline = set_underline
    data.italic = set_italic

def add_table_content(table=document.add_table(0,0), row_index=0, col_index=0, content="", content2="", style=None, space_before=0, space_after=0, tab=0, font_name="Times New Roman", font_size=12,
                set_bold=False, set_italic=False, set_underline=False, align="left", line_spacing=0, keep_together=False, keep_with_next=False, 
                page_break_before=False, widow_control=False, left_indent=0):
    font = table.style.font
    font.name = font_name
    font.size = Pt(font_size)
    paragraph = table.cell(row_idx=row_index, col_idx=col_index).add_paragraph(content, style=style)
    paragraph.paragraph_format.alignment = alignment_dict.get(align.lower())
    paragraph.paragraph_format.space_before = Pt(space_before)
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.line_spacing = Pt(line_spacing)
    paragraph.paragraph_format.keep_together = keep_together
    paragraph.paragraph_format.keep_with_next = keep_with_next
    paragraph.paragraph_format.page_break_before = page_break_before
    paragraph.paragraph_format.widow_control = widow_control
    paragraph.paragraph_format.tab_stops.add_tab_stop(Inches(tab))
    paragraph.paragraph_format.left_indent = Mm(left_indent)
    data = paragraph.add_run(content2)
    data.bold = set_bold
    data.underline = set_underline
    data.italic = set_italic

# table=doc.add_table(0,0)
def add_table_content2(table=document.add_table(0,0), row_index=0, col_index=0, content="", style='Table Grid', space_before=0, space_after=0, tab=0, font_name="Times New Roman", font_size=12,
                set_bold=False, set_italic=False, set_underline=False, align="left", line_spacing=0, keep_together=False, keep_with_next=False, 
                page_break_before=False, widow_control=False, left_indent=0):
    table.style=style
    font = table.style.font
    font.name = font_name
    font.size = Pt(font_size)
    cell = table.cell(row_idx=row_index, col_idx=col_index)
    paragraph = cell.paragraphs[0]
    data = paragraph.add_run(content)
    data.bold = set_bold
    data.underline = set_underline
    data.italic = set_italic
    data.font.size = Pt(font_size)
    data.font.name = font_name
    # paragraph.add_run().add_picture()
    paragraph.paragraph_format.alignment = alignment_dict.get(align.lower())
    paragraph.paragraph_format.space_before = Pt(space_before)
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.line_spacing = Pt(line_spacing)
    paragraph.paragraph_format.keep_together = keep_together
    paragraph.paragraph_format.keep_with_next = keep_with_next
    paragraph.paragraph_format.page_break_before = page_break_before
    paragraph.paragraph_format.widow_control = widow_control
    paragraph.paragraph_format.tab_stops.add_tab_stop(Inches(tab))
    paragraph.paragraph_format.left_indent = Mm(left_indent)


def convert_num_2_word(angka):
        number_dict = {i: num2words(i, lang='id') for i in range(0, 360)}
        return number_dict.get(angka, "Tidak dikenali")

    
class LayananGajiBerkalaDocxView(View):
    def set_col_widths(self, table):
        widths = (Inches(1), Inches(0.2), Inches(2.5), Inches(1), Inches(3))
        # height = (Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2))
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width
                # row.cells[idx].height = height

    def set_paragraph_space(self, row):
        for cell in row:
            for content in cell.paragraphs:
                content.paragraph_format.space_after=Pt(0.0)
                content.paragraph_format.space_before=Pt(0.0)

    def add_table_content(self, row, contents):
        # for cell in row:
        for idx, content in enumerate(contents):
            row[idx].text = content

    def get_object(self, id):
        try:
            data = LayananGajiBerkala.objects.get(id=id)
            return data
        except Exception:
            return None

    def get(self, request, **kwargs):
        #Pengaturan ukuran kertas
        doc:Document=CreateDocument()
        id = kwargs.get('layanan_id')
        layanan_berkala = self.get_object(id=id)
        page_size = doc.sections[0]
        page_size.page_width = Mm(215.9)
        page_size.page_height = Mm(330.0)
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.5)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)
            section.bottom_margin = Inches(1.0)
        #penambahan gambar kop
        doc.add_picture('static/img/KOP RS MANDALIKA 2024.png', width=Inches(7.0))
        first_line = doc.add_paragraph('Lombok Tengah, ${tanggal_naskah}')
        first_line.alignment=2 #0=left 1=center 2=right 3=justify

        table1 = doc.add_table(rows=5, cols=5)
        table1.autofit = False
        self.set_col_widths(table1)
        
        row1 = table1.rows[0].cells
        contents = ('','','','','Kepada:')
        self.add_table_content(row1, contents)
        self.set_paragraph_space(row1)

        row2 = table1.rows[1].cells
        contents = ('Nomor', ':', '${nomor_naskah}', '', 'Yth. Kepala Badan Pengelolaan')
        self.add_table_content(row2, contents)
        self.set_paragraph_space(row2)

        row3 = table1.rows[2].cells
        contents = ('Sifat', ':', '${sifat}', '', 'Keuangan dan Aset Daerah')
        self.add_table_content(row3, contents)
        self.set_paragraph_space(row3)

        row4 = table1.rows[3].cells
        contents = ('Lampiran', ':', '-', '', 'Provinsi NTB')
        self.add_table_content(row4, contents)
        self.set_paragraph_space(row4)

        row5 = table1.rows[4].cells
        contents = ('Perihal', ':', f'Kenaikan Gaji Berkala a/n {layanan_berkala.pegawai.full_name if layanan_berkala is not None else ""}, NIP. {layanan_berkala.pegawai.profil_user.nip  if layanan_berkala is not None else ""}', '', 'di Mataram')
        self.add_table_content(row5, contents)
        self.set_paragraph_space(row5)

        paragraph1 = doc.add_paragraph('Dengan ini diberitahukan bahwa berhubung dengan telah dipenuhinya masa kerja dan syarat-syarat lainnya kepada:')
        paragraph1.paragraph_format.space_before = Pt(16)
        paragraph1.paragraph_format.space_after = Pt(6)

        add_content(doc=doc, content=f'Nama\t: {layanan_berkala.pegawai.full_name if layanan_berkala is not None and hasattr(layanan_berkala.pegawai, "full_name") else ""}', style='List Number', tab=2.5, left_indent=7)
        add_content(doc=doc, content=f'NIP\t: {layanan_berkala.pegawai.profil_user.nip if layanan_berkala is not None and hasattr(layanan_berkala.pegawai, "profil_user") else ""}', style="List Number", tab=2.5, left_indent=7)
        add_content(doc=doc, content=f'Pangkat\t: {layanan_berkala.riwayat.pangkat.panggol if layanan_berkala is not None and hasattr(layanan_berkala.riwayat, "pangkat") and hasattr(layanan_berkala.riwayat.pangkat, "panggol") else ""}', style="List Number", tab=2.5, left_indent=7)
        add_content(doc=doc, content=f'Tempat Bekerja\t: {layanan_berkala.riwayat.tempat_kerja.unor if layanan_berkala is not None and hasattr(layanan_berkala.riwayat, "tempat_kerja") and hasattr(layanan_berkala.riwayat.tempat_kerja, "unor") else ""}', style="List Number", tab=2.5, left_indent=7)
        add_content(doc=doc, content=f'Gaji Pokok\t: {locale.currency(layanan_berkala.riwayat.gaji_pkk, grouping=True) if layanan_berkala is not None and hasattr(layanan_berkala.riwayat, "gaji_pkk") else ""} {layanan_berkala.riwayat.pertek}', style="List Number", tab=2.5, left_indent=7)
        add_content(doc=doc, content='Atas dasar keputusan gaji/pangkat yang ditetapkan : ', style="List Number", space_after=6, left_indent=7)
        add_content(doc=doc, content='\ta.   Oleh', tab=0.3, content2=f' Pejabat\t\t\t: {layanan_berkala.riwayat.tempat_kerja.pimpinan if layanan_berkala is not None and hasattr(layanan_berkala.riwayat, "tempat_kerja") and hasattr(layanan_berkala.riwayat.tempat_kerja, "pimpinan") else ""}', left_indent=7)
        add_content(doc=doc, content='\tb.   Nomor dan', tab=0.3, content2=f' Tanggal\t\t: {layanan_berkala.riwayat.no_srt_gaji if layanan_berkala is not None and hasattr(layanan_berkala.riwayat, "no_srt_gaji") else ""}', left_indent=7)
        add_content(doc=doc, content='\tc.   Terhitung mulai', tab=0.3, content2=f' tanggal\t: {layanan_berkala.riwayat.tgl_srt_gaji.strftime("%d %B %Y") if layanan_berkala is not None and hasattr(layanan_berkala.riwayat, "tgl_srt_gaji") else ""}', left_indent=7)
        add_content(doc=doc, content=f'\td.   Masa kerja golongan pada tanggal tersebut : {layanan_berkala.riwayat.masa_kerja_tahun if layanan_berkala is not None and hasattr(layanan_berkala.riwayat, "masa_kerja_tahun") else ""} Tahun {layanan_berkala.riwayat.masa_kerja_bulan if layanan_berkala is not None and hasattr(layanan_berkala.riwayat, "masa_kerja_bulan") else ""} Bulan', tab=0.3, left_indent=7)
        add_content(doc=doc, content2='Diberikan kenaikan gaji berkala hingga memperoleh :', set_bold=True, set_underline=True, space_after=6, space_before=10)
        add_content(doc=doc, content=f'Gaji Pokok Baru\t: {locale.currency(layanan_berkala.berkala.gaji_pkk, grouping=True) if layanan_berkala is not None and hasattr(layanan_berkala.berkala, "gaji_pkk") else ""}', style='List Number', tab=2.5, left_indent=7)
        add_content(doc=doc, content=f'Berdasarkan masa kerja\t: {layanan_berkala.berkala.masa_kerja_tahun if layanan_berkala is not None and hasattr(layanan_berkala.berkala, "masa_kerja_tahun") else ""} Tahun {layanan_berkala.berkala.masa_kerja_bulan if layanan_berkala is not None and hasattr(layanan_berkala.berkala, "masa_kerja_bulan") else ""} Bulan', style='List Number', tab=2.5, left_indent=7)
        add_content(doc=doc, content=f'Dalam golongan ruang\t: {layanan_berkala.berkala.pangkat.panggol if layanan_berkala is not None and hasattr(layanan_berkala.berkala, "pangkat") else ""}', style='List Number', tab=2.5, left_indent=7)
        add_content(doc=doc, content=f'Mulai tanggal\t: {layanan_berkala.berkala.tgl_srt_gaji.strftime("%d %B %Y") if layanan_berkala is not None and hasattr(layanan_berkala.berkala, "tgl_srt_gaji") else ""}', style='List Number', tab=2.5, left_indent=7)
        add_content(doc=doc, content=f'Diharapkan agar sesuai Peraturan Pemerintah Nomor 15 Tahun 2019 kepada pegawai tersebut dapat dibayarkan penghasilannya berdasarkan gaji pokok yang baru.', space_after=10, space_before=6)
        add_content(doc=doc, content='${jabatan_pengirim}', left_indent=100, align='center')
        add_content(doc=doc, content='${ttd_pengirim}', left_indent=100, align='center')
        add_content(doc=doc, content='${nama_pengirim}', left_indent=100, align='center')
        add_content(doc=doc, content=f'NIP.', left_indent=100, align='center')
        add_content(doc=doc, content='Tembusan :', space_before=30, )
        add_content(doc=doc, content='1.Ketua Badan Pemeriksaan Keuangan di Jakarta')
        add_content(doc=doc, content='2.Mendagri (Kepala Biro Kepeg./Kepala Bag. Mutasi Peg. Daerah) di Jakarta')
        add_content(doc=doc, content='3.Kepala Badan Kepegawaian Negara di Jakarta')
        add_content(doc=doc, content='4.Kepala Kantor Regional X BKN di Denpasar')
        add_content(doc=doc, content='5.Kepala Badan Kepegawaian Daerah Provinsi NTB di Mataram')
        add_content(doc=doc, content='6.Inspektur Inspektorat Provinsi NTB di Mataram')
        add_content(doc=doc, content='7.Ka. Sub Bag Keuangan/Pembuat Daftar Gaji Dikes Provivinsi NTB di Mataram')
        add_content(doc=doc, content='8.Yang Bersangkutan Untuk Maklum')

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename=berkala-{layanan_berkala.pegawai.first_name}.docx'
        doc.save(response)

        return response


class LayananUsulanCutiDocxView(View):
    def set_col_widths(self, table):
        widths = (Inches(3.5), Inches(4.5))
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width

    def get_object(self, id):
        try:
            data = LayananCuti.objects.get(id=id)
            return data
        except Exception:
            return None
    
    def get_data_cuti(self, data_input=None, data_output=None, attr=""):
        if data_input is not None and hasattr(data_input.cuti, attr):
            return data_output
        return ""

    def get_verification_object(self, id):
        try:
            cuti = LayananCuti.objects.get(id=id)
            data = VerifikasiCuti.objects.get(layanan_cuti=cuti)
            return data
        except LayananCuti.DoesNotExist:
            return None

    def get(self, request, **kwargs):
        #Pengaturan ukuran kertas
        id = kwargs.get('layanan_id')
        doc:Document=CreateDocument()
        verifikasi_cuti = self.get_verification_object(id)
        layanan_cuti = self.get_object(id=id)
        verifikator1 = None
        verifikator2 = None
        verifikator3 = None
        sdm_cuti = None
        if layanan_cuti is not None:
            sdm_cuti = {
                'pegawai':layanan_cuti.pegawai.full_name_2,
                'nip':layanan_cuti.pegawai.profil_user.nip if layanan_cuti is not None and hasattr(layanan_cuti.pegawai, 'profil_user') else None,
                'validasi_file':f'http://{request.get_host()}{reverse("file_urls:usulan_cuti_docx", kwargs={"layanan_id":id})}'
            }
        if verifikasi_cuti is not None:
            verifikator1 = {
                'id':verifikasi_cuti.id,
                'verifikator': verifikasi_cuti.verifikator1.full_name_2,
                'nip':verifikasi_cuti.verifikator1.profil_user.nip,
                'validasi_file':f'http://{request.get_host()}{reverse("file_urls:usulan_cuti_docx", kwargs={"layanan_id":id})}'
            }
            verifikator2 = {
                'id':verifikasi_cuti.id,
                'verifikator': verifikasi_cuti.verifikator2.full_name_2,
                'nip':verifikasi_cuti.verifikator2.profil_user.nip,
                'validasi_file':f'http://{request.get_host()}{reverse("file_urls:usulan_cuti_docx", kwargs={"layanan_id":id})}'
            }
            verifikator3 = {
                'id':verifikasi_cuti.id,
                'verifikator': verifikasi_cuti.verifikator3.full_name_2,
                'nip':verifikasi_cuti.verifikator3.profil_user.nip
            }
        jabatan = layanan_cuti.pegawai.riwayatjabatan_set.last()
        data_instansi = layanan_cuti.pegawai.riwayatpenempatan_set.last()
        lama_cuti = layanan_cuti.cuti.lama_cuti if layanan_cuti is not None and hasattr(layanan_cuti.cuti, "lama_cuti") else 0
        page_size = doc.sections[0]
        page_size.page_width = Mm(215.9)
        page_size.page_height = Mm(330.0)
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.5)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)
            section.bottom_margin = Inches(1.0)
        #penambahan gambar kop
        doc.paragraphs.clear()
        doc.add_picture('static/img/KOP RS MANDALIKA 2024.png', width=Inches(7.0))
        add_content(doc=doc, content2='LAMPIRAN IV SURAT EDARAN KEPALA BADAN ADMINISTRASI KEPEGAWAIAN NEGARA', align='left', left_indent=75.0, set_bold=True)
        add_content(doc=doc, content2='NOMOR \t: 893/1450/BKD/2018', left_indent=90.0, tab=1, set_bold=True)
        add_content(doc=doc, content2='TANGGAL \t: 21 Mei 2018', left_indent=90.0, tab=1, set_bold=True, space_after=10)
        add_content(doc=doc, content=f'Lombok Tengah, {verifikasi_cuti.tanggal.strftime("%d %B %Y") if verifikasi_cuti.tanggal is not None else ""}', align='right', space_after=6)

        table1 = doc.add_table(rows=1, cols=2)
        table1.autofit = False
        self.set_col_widths(table1)
        add_table_content2(table=table1, row_index=0, col_index=0, content=f'PERMINTAAN {(self.get_data_cuti(layanan_cuti, layanan_cuti.cuti.jenis_cuti, "jenis_cuti")).upper()}', font_size=13, set_bold=True)
        add_table_content2(table=table1, row_index=0, col_index=1, style=None, content='\tK e p a d a \nYth.\tDirektur RS Mandalika  \n\tProvinsi Nusa Tenggara Barat \n\tdi Lombok Tengah')
        # generate qrcode
        pegawai_qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=7, border=4,)
        pegawai_qr.add_data(sdm_cuti)
        pegawai_qr.make(fit=True)
        img = pegawai_qr.make_image(fill='black', back_color='white')
        # Save QR code to a BytesIO object
        pegawai_buffer = BytesIO()
        img.save(pegawai_buffer, format='PNG')
        pegawai_buffer.seek(0)

        kasi_qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=7, border=4,)
        kasi_qr.add_data(verifikator1)
        kasi_qr.make(fit=True)
        img = kasi_qr.make_image(fill='black', back_color='white')
        kasi_buffer = BytesIO()
        img.save(kasi_buffer, format='PNG')
        kasi_buffer.seek(0)

        kabid_qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=7, border=4,)
        kabid_qr.add_data(verifikator2)
        kabid_qr.make(fit=True)
        img = kabid_qr.make_image(fill='black', back_color='white')
        kabid_buffer = BytesIO()
        img.save(kabid_buffer, format='PNG')
        kabid_buffer.seek(0)

        dir_qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=7, border=4,)
        dir_qr.add_data(verifikator3)
        dir_qr.make(fit=True)
        img = dir_qr.make_image(fill='black', back_color='white')
        dir_buffer = BytesIO()
        img.save(dir_buffer, format='PNG')
        dir_buffer.seek(0)
        
        add_content(doc=doc, content='Yang bertanda tangan dibawah ini :', space_before=10, space_after=6)
        add_content(doc=doc, content=f'\tNama \t\t\t:  {layanan_cuti.pegawai.full_name_2 if layanan_cuti is not None and hasattr(layanan_cuti.pegawai, "full_name_2") else ""}', align="left")
        add_content(doc=doc, content=f'\tNIP/NRK \t\t: {layanan_cuti.pegawai.profil_user.nip if layanan_cuti is not None and hasattr(layanan_cuti.pegawai, "profil_user") and hasattr(layanan_cuti.pegawai.profil_user, "nip") else ""}')
        add_content(doc=doc, content=f'\tJabatan \t\t: {jabatan.nama_jabatan if jabatan is not None and hasattr(jabatan, "nama_jabatan") else ""}')
        add_content(doc=doc, content=f'\tSatuan Organisasi \t: {data_instansi.unor if data_instansi is not None else "" }')
        add_content(doc=doc, content=f'Dengan ini mengajukan permintaan {self.get_data_cuti(layanan_cuti, layanan_cuti.cuti.jenis_cuti, "jenis_cuti")} karena {self.get_data_cuti(layanan_cuti, layanan_cuti.cuti.alasan_cuti, "alasan_cuti")} selama {convert_num_2_word(lama_cuti)} ({lama_cuti}) hari, terhitung mulai tanggal {self.get_data_cuti(layanan_cuti, layanan_cuti.cuti.tgl_mulai_cuti.strftime("%d %B"), "tgl_mulai_cuti")} s.d {self.get_data_cuti(layanan_cuti, layanan_cuti.cuti.tgl_akhir_cuti.strftime("%d %B %Y"), "tgl_akhir_cuti")} dan selama menjalankan cuti alamat saya adalah {self.get_data_cuti(layanan_cuti, layanan_cuti.cuti.domisili_saat_cuti, "domisili_saat_cuti")}', space_after=6, space_before=6)
        add_content(doc=doc, content='Demikian permintaan ini saya buat untuk dapat dipertimbangkan sebagaimana mestinya.', space_after=16)
        add_content(doc=doc, content=f'Hormat Saya', left_indent=80, align='center')
        paragraf = doc.add_paragraph()
        paragraf.add_run().add_picture(pegawai_buffer, Inches(1))
        paragraf.paragraph_format.left_indent=Mm(80.0)
        paragraf.paragraph_format.alignment = alignment_dict.get('center')
        add_content(doc=doc, content2=f'{layanan_cuti.pegawai.full_name_2 if layanan_cuti is not None and hasattr(layanan_cuti.pegawai, "full_name_2") else ""}', set_underline=True, align='center', left_indent=80)
        add_content(doc=doc, content=f'NIP/NRK: {layanan_cuti.pegawai.profil_user.nip if layanan_cuti is not None and hasattr(layanan_cuti.pegawai, "profil_user") and hasattr(layanan_cuti.pegawai.profil_user, "nip") else ""}', left_indent=80, align='center', space_after=20)

        table2 = doc.add_table(rows=4, cols=2)
        self.set_col_widths(table2)
        table2.cell(0,0).merge(table2.cell(0,2))
        add_table_content2(table=table2, row_index=0, col_index=0 , content='CATATAN KEPEGAWAIAN  :\nCuti yang telah diambil dalam tahun yang bersangkutan :\n1. Cuti Tahunan \t: \n2. Cuti Besar  \t\t: \n3. Cuti Sakit \t\t: \n4. Cuti Bersalin \t: \n5. Cuti Karena Alasan Penting  : \n6. Keterangan lain – lain :')
        add_table_content2(table=table2, row_index=0, col_index=1, content='CATATAN PERTIMBANGAN ATASAN LANGSUNG  :', space_after=10)
        add_table_content2(table=table2, row_index=1, col_index=1, content=f'{data_instansi.jabatan_atasan["jabatan_atasan1"] if data_instansi is not None else ""} {data_instansi.jabatan_atasan["instansi1"] if data_instansi is not None else ""} \n')
        table2.cell(row_idx=1, col_idx=1).paragraphs[0].add_run().add_picture(kasi_buffer, Inches(1))
        add_table_content2(table=table2, row_index=1, col_index=1, content=f'\n {data_instansi.nama_atasan["nama_atasan1"] if data_instansi is not None else ""}', set_bold=True, set_underline=True)
        add_table_content2(table=table2, row_index=1, col_index=1, content=f'\nNIP. {data_instansi.nama_atasan["nip_atasan1"] if data_instansi is not None else ""}', set_bold=True, align='center')
        add_table_content2(table=table2, row_index=2, col_index=1, content='MENGETAHUI  :', space_before=10, space_after=6)
        add_table_content2(table=table2, row_index=3, col_index=1, content=f'{data_instansi.jabatan_atasan["jabatan_atasan2"] if data_instansi is not None else ""} {data_instansi.jabatan_atasan["instansi2"] if data_instansi is not None else ""} \n')
        table2.cell(row_idx=3, col_idx=1).paragraphs[0].add_run().add_picture(kabid_buffer, Inches(1))
        add_table_content2(table=table2, row_index=3, col_index=1, content=f'\n {data_instansi.nama_atasan["nama_atasan2"] if data_instansi is not None else ""} ', set_bold=True, set_underline=True)
        add_table_content2(table=table2, row_index=3, col_index=1, style=None, content=f'\nNIP. {data_instansi.nama_atasan["nip_atasan2"] if data_instansi is not None else ""}', set_bold=True, align='center')

        section = doc.sections[0]
        footer = section.footer.paragraphs[0]
        footer.style.font.size=Pt(10.0)
        data_footer = footer.add_run()
        data_footer.add_text("Tanda tangan elektronik ini dapat dilacak keabsahannya melalui link yang terdapat dalam qrcode")
        data_footer.italic=True

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename=usulan-cuti-{layanan_cuti.pegawai.first_name}.docx'
        doc.save(response)

        return response


class LayananCutiDocxView(View):
    def set_col_widths(self, table):
        widths = (Inches(0.3), Inches(7.7))
        # height = (Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2))
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width
                # row.cells[idx].height = heigh

    def get_object(self, id):
        try:
            data = LayananCuti.objects.get(id=id)
            return data
        except Exception:
            return None
        
    def get_data_cuti(self, data_input=None, data_output=None, attr=""):
        if data_input is not None and hasattr(data_input.cuti, attr):
            return data_output
        return ""

    def get(self, request, **kwargs):
        #Pengaturan ukuran kertas
        doc:Document=CreateDocument()
        id = kwargs.get('layanan_id')
        layanan_cuti = self.get_object(id=id)
        jabatan = layanan_cuti.pegawai.riwayatjabatan_set.last()
        data_instansi = layanan_cuti.pegawai.riwayatpenempatan_set.last()
        lama_cuti = layanan_cuti.cuti.lama_cuti if layanan_cuti is not None and hasattr(layanan_cuti.cuti, "lama_cuti") else 0
        page_size = doc.sections[0]
        page_size.page_width = Mm(215.9)
        page_size.page_height = Mm(330.0)
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.5)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)
            section.bottom_margin = Inches(1.0)
        #penambahan gambar kop
        doc.paragraphs.clear()
        doc.add_picture('static/img/KOP RS MANDALIKA 2024.png', width=Inches(7.0))
        add_content(doc=doc, content2=f'SURAT IZIN {layanan_cuti.cuti.jenis_cuti.upper() if layanan_cuti is not None and hasattr(layanan_cuti.cuti, "jenis_cuti") else ""}', align='center', set_bold=True, set_underline=True)
        add_content(doc=doc, content2='Nomor : ${nomor_naskah}', align='center')
        # add_content(doc=doc, 'Lombok Tengah, ${tanggal_naskah}', align='right', space_after=6)
        
        add_content(doc=doc, content=f'Diberikan {layanan_cuti.cuti.jenis_cuti.lower() if layanan_cuti is not None and hasattr(layanan_cuti.cuti, "jenis_cuti") else ""} kepada pegawai negeri sipil,', space_before=10, space_after=10, style='List Number')
        add_content(doc=doc, content=f'nama \t\t: {layanan_cuti.pegawai.full_name_2 if layanan_cuti is not None and hasattr(layanan_cuti.pegawai, "full_name_2") else ""},', tab=1)
        add_content(doc=doc, content=f'NIP/NRK \t\t: {layanan_cuti.pegawai.profil_user.nip if layanan_cuti is not None and hasattr(layanan_cuti.pegawai, "profil_user") and hasattr(layanan_cuti.pegawai.profil_user, "nip") else ""},', tab=1)
        add_content(doc=doc, content=f'jabatan \t\t: {jabatan.nama_jabatan if jabatan is not None and hasattr(jabatan, "nama_jabatan") else ""}', tab=1)
        add_content(doc=doc, content=f'satuan organisasi \t: {data_instansi.unor if data_instansi is not None else "" },', tab=1)
        add_content(doc=doc, content=f'selama {convert_num_2_word(lama_cuti)} ({lama_cuti}) hari, terhitung mulai tanggal {layanan_cuti.cuti.tgl_mulai_cuti.strftime("%d %B %Y") if hasattr(layanan_cuti, "cuti") and hasattr(layanan_cuti.cuti, "tgl_mulai_cuti") and hasattr(layanan_cuti.cuti.tgl_mulai_cuti, "strftime") else ""} s.d {layanan_cuti.cuti.tgl_akhir_cuti.strftime("%d %B %Y") if hasattr(layanan_cuti, "cuti") and hasattr(layanan_cuti.cuti ,"tgl_akhir_cuti") and hasattr(layanan_cuti.cuti.tgl_akhir_cuti, "strftime") else ""} dengan ketentuan sebagai berikut :', space_after=10, space_before=10)
        
        table2 = doc.add_table(rows=2, cols=2)
        self.set_col_widths(table2)
        add_table_content2(table=table2, row_index=0, col_index=0, content='a. ')
        add_table_content2(table=table2, row_index=0, col_index=1, content=f'Sebelum menjalankan {layanan_cuti.cuti.jenis_cuti.lower() if layanan_cuti is not None and hasattr(layanan_cuti.cuti, "jenis_cuti") else ""} wajib menyerahkan pekerjaannya kepada atasan langsungnya atau pejabat lain yang ditentukan.')
        add_table_content2(table=table2, row_index=1, col_index=0, content='b. ')
        add_table_content2(table=table2, row_index=1, col_index=1, style=None, content=f'Setelah selesai menjalankan {layanan_cuti.cuti.jenis_cuti.lower() if layanan_cuti is not None and hasattr(layanan_cuti.cuti, "jenis_cuti") else ""} wajib melaporkan diri kepada atasan langsungnya dan bekerja kembali sebagaimana mestinya.')
        
        add_content(doc=doc, content='Demikian surat cuti ini dibuat untuk dapat dipergunakan sebagaimana mestinya.', space_before=10, space_after=16, style='List Number')
        add_content(doc=doc, content='Lombok Tengah, ${tanggal_naskah}', left_indent=80)
        add_content(doc=doc, content='${jabatan_pengirim}', left_indent=80)
        add_content(doc=doc, content='${ttd_pengirim}', left_indent=80)
        add_content(doc=doc, content='${nama_pengirim}', left_indent=80)
        add_content(doc=doc, content=f'NIP. {layanan_cuti.pegawai.riwayatpenempatan_set.last().penempatan_level1.nama_pimpinan.profil_user.nip}', left_indent=80)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename=cuti-{layanan_cuti.pegawai.full_name}.docx'
        doc.save(response)

        return response
    
class LayananCutiPelimpahanTugasDocxView(View):
    def set_col_widths(self, table):
        widths = (Inches(4), Inches(4))
        # height = (Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2))
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width
                # row.cells[idx].height = heigh

    def get_object(self, id):
        try:
            data = LayananCuti.objects.get(id=id)
            return data
        except Exception:
            return None
        
    def get_data_cuti(self, data_input=None, data_output=None, attr=""):
        if data_input is not None and hasattr(data_input.cuti, attr):
            return data_output
        return ""

    def get(self, request, **kwargs):
        #Pengaturan ukuran kertas
        doc:Document=CreateDocument()
        id = kwargs.get('layanan_id')
        layanan_cuti = self.get_object(id=id)
        jabatan = layanan_cuti.pegawai.riwayatjabatan_set.last()
        data_instansi = layanan_cuti.pegawai.riwayatpenempatan_set.last()
        lama_cuti = layanan_cuti.cuti.lama_cuti if layanan_cuti is not None and hasattr(layanan_cuti.cuti, "lama_cuti") else 0
        page_size = doc.sections[0]
        page_size.page_width = Mm(215.9)
        page_size.page_height = Mm(330.0)
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.5)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)
            section.bottom_margin = Inches(1.0)
        #penambahan gambar kop
        doc.paragraphs.clear()
        doc.add_picture('static\img\KOP RS MANDALIKA 2024.png', width=Inches(7.0))
        add_content(doc=doc, content2=f'SURAT PELIMPAHAN TUGAS', align='center', set_bold=True, set_underline=True)
        add_content(doc=doc, content2='Nomor : ${nomor_naskah}', align='center')
        # add_content(doc=doc, 'Lombok Tengah, ${tanggal_naskah}', align='right', space_after=6)
        
        add_content(doc=doc, content='Yang bertanda tangan di bawah ini :', space_before=10, space_after=10)
        add_content(doc=doc, content=f'nama \t\t: {layanan_cuti.pegawai.full_name_2 if layanan_cuti is not None and hasattr(layanan_cuti.pegawai, "full_name_2") else ""},', tab=1)
        add_content(doc=doc, content=f'NIP/NRK \t\t: {layanan_cuti.pegawai.profil_user.nip if layanan_cuti is not None and hasattr(layanan_cuti.pegawai, "profil_user") and hasattr(layanan_cuti.pegawai.profil_user, "nip") else ""},', tab=1)
        add_content(doc=doc, content=f'jabatan \t\t: {jabatan.nama_jabatan if jabatan is not None and hasattr(jabatan, "nama_jabatan") else ""}', tab=1)
        add_content(doc=doc, content=f'satuan organisasi \t: {data_instansi.unor if data_instansi is not None else "" },', tab=1)
        add_content(doc=doc, content=f'Benar akan menjalankan cuti {layanan_cuti.cuti.jenis_cuti.lower() if layanan_cuti is not None and hasattr(layanan_cuti.cuti, "jenis_cuti") else ""} selama {convert_num_2_word(lama_cuti)} ({lama_cuti}) hari, terhitung mulai tanggal {self.get_data_cuti(layanan_cuti, layanan_cuti.cuti.tgl_mulai_cuti.strftime("%d %B"), "tgl_mulai_cuti")} s.d {self.get_data_cuti(layanan_cuti, layanan_cuti.cuti.tgl_akhir_cuti.strftime("%d %B %Y"), "tgl_akhir_cuti")}, maka dengan ini saya melimpahkan tugas kepada :', space_after=10, space_before=10)

        add_content(doc=doc, content=f'nama \t\t: ', tab=1, space_before=10)
        add_content(doc=doc, content=f'NIP/NRK \t\t: ', tab=1)
        add_content(doc=doc, content=f'jabatan \t\t: ', tab=1)
        add_content(doc=doc, content=f'satuan organisasi \t: ', tab=1)
        add_content(doc=doc, content='Untuk melaksanakan tugas saya sehari-hari selama menjalankan cuti', space_before=10, space_after=10)
        
        add_content(doc=doc, content='Demikian surat pelimpahan tugas ini dibuat untuk dapat dipergunakan sebagaimana mestinya.', space_before=10, space_after=30)

        table2 = doc.add_table(rows=2, cols=2)
        self.set_col_widths(table2)
        add_table_content2(table=table2, row_index=0, col_index=0, content='Yang dilimpahkan tugas', space_after=50, align='center')
        add_table_content2(table=table2, row_index=0, col_index=1, content='Yang melimpahkan tugas', align='center')
        add_table_content2(table=table2, row_index=1, col_index=0, content='(__________________)\n NIP/NRK. ', align='center')
        add_table_content2(table=table2, row_index=1, col_index=1, style=None, content='(__________________)\n NIP/NRK. ')

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename=pelimpahan_tugas-{layanan_cuti.pegawai.full_name}.docx'
        doc.save(response)

        return response


class FormatPenilaianInovasiView(View):
    def set_col_widths(self, table):
        widths = (Inches(0.3), Inches(4.0), Inches(8.0), Inches(3.0), Inches(3.0))
        # height = (Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2))
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width
                # row.cells[idx].height = height

    def get_object(self, id):
        try:
            data = LayananUsulanInovasi.objects.get(id=id)
            return data
        except Exception:
            return None

    def get(self, request, **kwargs):
        #Pengaturan ukuran kertas
        # clear_document(doc)
        doc:Document=CreateDocument()
        id = kwargs.get('layanan_id')
        layanan_inovasi = self.get_object(id=id)
        page_size = doc.sections[0]
        page_size.page_width = Mm(215.9)
        page_size.page_height = Mm(330.0)
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.5)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)
            section.bottom_margin = Inches(1.0)
        #penambahan gambar kop
        doc.paragraphs.clear()
        doc.add_picture('static/img/KOP RS MANDALIKA 2024.png', width=Inches(7.0))
        add_content(doc=doc, content2=f'FORMAT PENILAIAN DAN PEMBINAAN KATEGORI INOVASI', align='center', set_bold=True, set_underline=True)
        add_content(doc=doc, content2='', align='center', space_after=10)
        # add_content(doc=doc, 'Lombok Tengah, ${tanggal_naskah}', align='right', space_after=6)

        data_penempatan = layanan_inovasi.pegawai.riwayatpenempatan_set.last().penempatan
        add_content(doc=doc, content=f'Nama Nakes/Named \t\t: {layanan_inovasi.pegawai.full_name if layanan_inovasi is not None and hasattr(layanan_inovasi.pegawai, "full_name") else ""},', tab=1)
        add_content(doc=doc, content=f'Jenis Nakes/Named \t\t: {layanan_inovasi.pegawai.riwayatjabatan_set.last().nama_jabatan if layanan_inovasi is not None and hasattr(layanan_inovasi, "pegawai") else ""},', tab=1)
        add_content(doc=doc, content=f'Instalasi \t\t\t: {data_penempatan}', tab=1)
        add_content(doc=doc, content=f'Judul Inovasi \t\t\t: {layanan_inovasi.inovasi.judul if layanan_inovasi is not None and hasattr(layanan_inovasi.inovasi, "judul") else ""},', tab=1, space_after=10)

        table2 = doc.add_table(rows=6, cols=5)
        self.set_col_widths(table2)
        table2.cell(1,4).merge(table2.cell(4,4))
        table2.cell(5,1).merge(table2.cell(5,2))
        add_table_content2(table=table2, row_index=0, col_index=0, content='No.')
        add_table_content2(table=table2, row_index=0, col_index=1, content='Aspek Penilaian')
        add_table_content2(table=table2, row_index=0, col_index=2, content='Unsur Penilaian')
        add_table_content2(table=table2, row_index=0, col_index=3, content='Nilai/Poin')
        add_table_content2(table=table2, row_index=0, col_index=4, content='Total Nilai')

        add_table_content2(table=table2, row_index=1, col_index=0, content='1.')
        add_table_content2(table=table2, row_index=1, col_index=1, content='Makalah/Essay \n(Skor: 30)')
        add_table_content2(table=table2, row_index=1, col_index=2, content='1. Kriteria Umum (Teknis Penulisan)')
        add_table_content2(table=table2, row_index=1, col_index=3, content='')
        add_table_content2(table=table2, row_index=1, col_index=4, content='')

        add_table_content2(table=table2, row_index=2, col_index=0, content='')
        add_table_content2(table=table2, row_index=2, col_index=1, content='')
        add_table_content2(table=table2, row_index=2, col_index=2, content='2. Kriteria Khusus (Keberhasilan dan Keberlanjutan Program)')
        add_table_content2(table=table2, row_index=2, col_index=3, content='')
        add_table_content2(table=table2, row_index=2, col_index=4, content='')

        add_table_content2(table=table2, row_index=3, col_index=0, content='2.')
        add_table_content2(table=table2, row_index=3, col_index=1, content='Presentasi dan Wawancara \n(Skor: 40)')
        add_table_content2(table=table2, row_index=3, col_index=2, content='1. Materi \n2. Kemampuan Menjawab Pertanyaan \n3. Kemampuan Presentasi')
        add_table_content2(table=table2, row_index=3, col_index=3, content='')
        add_table_content2(table=table2, row_index=3, col_index=4, content='')

        add_table_content2(table=table2, row_index=4, col_index=0, content='3.')
        add_table_content2(table=table2, row_index=4, col_index=1, content='Daya ungkit Inovasi dan Dampak \n(Skor: 30)')
        add_table_content2(table=table2, row_index=4, col_index=2, content='')
        add_table_content2(table=table2, row_index=4, col_index=3, content='')
        add_table_content2(table=table2, row_index=4, col_index=4, content='')

        add_table_content2(table=table2, row_index=5, col_index=0, content='')
        add_table_content2(table=table2, row_index=5, col_index=1, content='TOTAL NILAI')
        add_table_content2(table=table2, row_index=5, col_index=2, content='')
        add_table_content2(table=table2, row_index=5, col_index=3, content='')
        add_table_content2(table=table2, row_index=5, col_index=4, content='')
        
        add_content(doc=doc, content='', space_before=10)
        add_content(doc=doc, content='Lombok Tengah, ${tanggal_naskah}', align='center', left_indent=80)
        add_content(doc=doc, content='${jabatan_pengirim}', left_indent=80, align='center')
        add_content(doc=doc, content='${ttd_pengirim}', left_indent=80, align='center')
        add_content(doc=doc, content='${nama_pengirim}', align='center', left_indent=80)
        add_content(doc=doc, content='NIP. ', left_indent=80, align='center')

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename=format-penilaian-inovasi ({layanan_inovasi.pegawai.full_name}).docx'
        doc.save(response)
        return response

#SPT diklat untuk satu orang
class LayananDiklatSPTDocxView(View):
    def set_col_widths(self, table):
        widths = (Inches(2), Inches(0.3), Inches(10))
        # height = (Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2))
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width
                # row.cells[idx].height = heigh

    def get_object(self, id):
        try:
            data = RiwayatDiklat.objects.get(id=id)
            return data
        except Exception:
            return None

    def get(self, request, **kwargs):
        #Pengaturan ukuran kertas
        doc:Document=CreateDocument()
        id = kwargs.get('diklat_id')
        riwayatdiklat = self.get_object(id=id)
        spt_text = TextSPTDiklat.objects.filter(diklat=riwayatdiklat.usulan).first()
        jabatan = None
        panggol_sdm = None
        panggol = None
        penempatan = None
        pegawai = riwayatdiklat.pegawai.first()
        if pegawai:
            jabatan = pegawai.riwayatjabatan_set.last()
            penempatan = RiwayatPenempatan.objects.filter(pegawai=pegawai, status=True).last()
            panggol_sdm = pegawai.riwayatpanggol_set.last()
            panggol = penempatan.penempatan_level1.nama_pimpinan.riwayatpanggol_set.last() if hasattr(penempatan, 'penempatan_level1') else None
        # Parse the HTML content (you can use BeautifulSoup or lxml)
        dasar_pelaksanaan = BeautifulSoup(spt_text.dasar_pelaksanaan, 'html.parser')
        items_dasar = [li.text for li in dasar_pelaksanaan.find_all('li')]
        tujuan_pelaksanaan = BeautifulSoup(spt_text.tujuan_pelaksanaan, 'html.parser')
        items_tujuan = [li.text for li in tujuan_pelaksanaan.find_all('li')]
        
        page_size = doc.sections[0]
        page_size.page_width = Mm(215.9)
        page_size.page_height = Mm(330.0)
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.5)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)
            section.bottom_margin = Inches(1.0)
        #penambahan gambar kop
        doc.add_picture('static/img/KOP RS MANDALIKA 2024.png', width=Inches(7.0))
        add_content(doc=doc, content2=f'SURAT TUGAS', align='center', set_bold=True, set_underline=True)
        add_content(doc=doc, content2='Nomor : ${nomor_naskah}', align='center')
        # add_content(doc=doc, 'Lombok Tengah, ${tanggal_naskah}', align='right', space_after=6)
        table2 = doc.add_table(rows=4, cols=3)
        self.set_col_widths(table2)
        add_table_content(table=table2, row_index=0, col_index=0, content='Dasar')
        add_table_content(table=table2, row_index=0, col_index=1, content=':')
        for item in items_dasar:
            add_table_content(table=table2, row_index=0, col_index=2, content2=f'{item}', left_indent=5, style='List Number')
        
        add_table_content(table=table2, row_index=1, col_index=0, content='Kepada')
        add_table_content(table=table2, row_index=1, col_index=1, content=':')
        if pegawai:
            add_table_content(table=table2, row_index=1, col_index=2, content=f'Nama \t\t\t: {pegawai.full_name_2}')
            add_table_content(table=table2, row_index=1, col_index=2, content=f'Pangkat/Gol \t\t: {panggol_sdm.panggol if panggol_sdm is not None and hasattr(panggol_sdm, "panggol") else "-"}')
            add_table_content(table=table2, row_index=1, col_index=2, content=f'Jabatan/Profesi \t: {jabatan.nama_jabatan if jabatan is not None and hasattr(jabatan, "nama_jabatan") else "-"}')
            add_table_content(table=table2, row_index=1, col_index=2, content=f'NIP \t\t\t: {pegawai.profil_user.nip if hasattr(pegawai, "profil_user") else ""}')
        else:
            add_table_content(table=table2, row_index=1, col_index=2, content=f'Nama \t\t\t: -')
            add_table_content(table=table2, row_index=1, col_index=2, content=f'Pangkat/Gol \t\t: -')
            add_table_content(table=table2, row_index=1, col_index=2, content=f'Jabatan/Profesi \t: -')
            add_table_content(table=table2, row_index=1, col_index=2, content=f'NIP \t\t\t: -')
        table2.cell(2,0).merge(table2.cell(2,2))#merge row ketiga sampai kolom ketiga
        add_table_content(table=table2, row_index=2, col_index=0, content='MEMERINTAHKAN:', align='center')
        add_table_content(table=table2, row_index=3, col_index=0, content='Untuk')
        add_table_content(table=table2, row_index=3, col_index=1, content=':')
        for item in items_tujuan:
            add_table_content(table=table2, row_index=3, col_index=2, content2=f'{item}', left_indent=5, style='List Number 2')

        add_content(doc=doc, content='Lombok Tengah, ${tanggal_naskah}', space_before=30, left_indent=80)
        add_content(doc=doc, content='Direktur', left_indent=80, space_after=30)
        add_content(doc=doc, content='${ttd_pengirim}', left_indent=80, )
        add_content(doc=doc, content=f'{penempatan.penempatan_level1.nama_pimpinan.full_name_2}', left_indent=80, space_before=30)
        add_content(doc=doc, content=f'{panggol.panggol if hasattr(panggol, "panggol") else None}', left_indent=80)
        add_content(doc=doc, content=f'NIP. {penempatan.penempatan_level1.nama_pimpinan.profil_user.nip}', left_indent=80)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename=pelimpahan_tugas-{pegawai.full_name}.docx'
        doc.save(response)

        return response


#SPT diklat untuk lebih dari satu orang
class LayananDiklatSPTDocxView2(View):
    def set_col_widths(self, table):
        widths = (Inches(2.5), Inches(0.3), Inches(9.5))
        # height = (Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2))
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width
                # row.cells[idx].height = heigh
                
    def set_col_table3_widths(self, table):
        widths = (Inches(2.5), Inches(0.3), Inches(0.5), Inches(9.5))
        # height = (Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2), Inches(0.2))
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width
                # row.cells[idx].height = heigh

    def get_object(self, id):
        try:
            data = RiwayatDiklat.objects.get(id=id)
            return data
        except Exception:
            return None

    def get(self, request, **kwargs):
        #Pengaturan ukuran kertas
        doc:Document=CreateDocument()
        id = kwargs.get('diklat_id')
        riwayatdiklat = self.get_object(id=id)
        spt_text = TextSPTDiklat.objects.filter(diklat=riwayatdiklat.usulan).first()
        jabatan = None
        panggol = None
        penempatan = None
        pegawai = riwayatdiklat.pegawai.all()
        detail_pegawai = riwayatdiklat.pegawai.first()
        if detail_pegawai:
            penempatan = RiwayatPenempatan.objects.filter(pegawai=detail_pegawai, status=True).last()
            panggol = penempatan.penempatan_level1.nama_pimpinan.riwayatpanggol_set.last() if hasattr(penempatan, 'penempatan_level1') else None
        # Parse the HTML content (you can use BeautifulSoup or lxml)
        dasar_pelaksanaan = BeautifulSoup(spt_text.dasar_pelaksanaan, 'html.parser')
        items_dasar = [li.text for li in dasar_pelaksanaan.find_all('li')]
        tujuan_pelaksanaan = BeautifulSoup(spt_text.tujuan_pelaksanaan, 'html.parser')
        items_tujuan = [li.text for li in tujuan_pelaksanaan.find_all('li')]
        
        page_size = doc.sections[0]
        page_size.page_width = Mm(215.9)
        page_size.page_height = Mm(330.0)
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.5)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)
            section.bottom_margin = Inches(1.0)
        #penambahan gambar kop
        doc.add_picture('static/img/KOP RS MANDALIKA 2024.png', width=Inches(7.0))
        add_content(doc=doc, content2=f'SURAT TUGAS', align='center', set_bold=True, set_underline=True)
        add_content(doc=doc, content2='Nomor : ${nomor_naskah}', align='center')
        # add_content(doc=doc, 'Lombok Tengah, ${tanggal_naskah}', align='right', space_after=6)
        table2 = doc.add_table(rows=4, cols=3)
        self.set_col_widths(table2)
        add_table_content(table=table2, row_index=0, col_index=0, content='Dasar')
        add_table_content(table=table2, row_index=0, col_index=1, content=':')
        for item in items_dasar:
            add_table_content(table=table2, row_index=0, col_index=2, content2=f'{item}', left_indent=5, style='List Number')
        
        add_table_content(table=table2, row_index=1, col_index=0, content='Kepada')
        add_table_content(table=table2, row_index=1, col_index=1, content=':')
        add_table_content(table=table2, row_index=1, col_index=2, content=f'(Daftar Terlampir)')
        
        table2.cell(2,0).merge(table2.cell(2,2))#merge row ketiga sampai kolom ketiga
        add_table_content(table=table2, row_index=2, col_index=0, content='MEMERINTAHKAN:', align='center')
        add_table_content(table=table2, row_index=3, col_index=0, content='Untuk')
        add_table_content(table=table2, row_index=3, col_index=1, content=':')
        for item in items_tujuan:
            add_table_content(table=table2, row_index=3, col_index=2, content2=f'{item}', left_indent=5, style='List Number 2')

        add_content(doc=doc, content='Lombok Tengah, ${tanggal_naskah}', space_before=20, left_indent=80)
        add_content(doc=doc, content='Direktur', left_indent=80, space_after=30)
        add_content(doc=doc, content='${ttd_pengirim}', left_indent=80, )
        add_content(doc=doc, content=f'{penempatan.penempatan_level1.nama_pimpinan.full_name_2}', left_indent=80, space_before=30)
        add_content(doc=doc, content=f'{panggol.panggol if hasattr(panggol, "panggol") else None}', left_indent=80)
        add_content(doc=doc, content=f'NIP. {penempatan.penempatan_level1.nama_pimpinan.profil_user.nip}', left_indent=80)

        doc.add_page_break()
        add_content(doc=doc, content='Lampiran:')
        add_content(doc=doc, content='Surat Tugas')
        add_content(doc=doc, content='Nomor: ${nomor_naskah}')
        rows = pegawai.count() + 1
        table3 = doc.add_table(rows=rows, cols=4)
        self.set_col_table3_widths(table3)
        add_table_content(table=table3, row_index=0, col_index=0, content='Kepada')
        add_table_content(table=table3, row_index=0, col_index=1, content=':')
        for i, p in enumerate(pegawai, start=0):
            add_table_content(table=table3, row_index=i, col_index=2, content=f'{i+1}.')
            add_table_content(table=table3, row_index=i, col_index=3, content=f'Nama \t\t\t: {p.full_name_2}')
            if p.riwayatjabatan_set.last():
                add_table_content(table=table3, row_index=i, col_index=3, content=f'Jabatan/Profesi \t: {p.riwayatjabatan_set.last().nama_jabatan}')
            else:
                add_table_content(table=table3, row_index=i, col_index=3, content=f'Jabatan/Profesi \t: -')
            if p.profil_user:
                add_table_content(table=table3, row_index=i, col_index=3, content=f'NIP \t\t\t: {p.profil_user.nip}')
            else:
                add_table_content(table=table3, row_index=i, col_index=3, content=f'NIP \t\t\t: -')
            if p.riwayatpanggol_set.last():
                add_table_content(table=table3, row_index=i, col_index=3, content=f'Pangkat/Gol \t\t: {p.riwayatpanggol_set.last().panggol}')
            else:
                add_table_content(table=table3, row_index=i, col_index=3, content=f'Pangkat/Gol \t\t: -')
            if p.riwayatjabatan_set.last():
                add_table_content(table=table3, row_index=i, col_index=3, content=f'Jabatan \t\t: {p.riwayatjabatan_set.last().detail_nama_jabatan}')
            else:
                add_table_content(table=table3, row_index=i, col_index=3, content=f'Jabatan \t\t: -')
        
        add_content(doc=doc, content='Lombok Tengah, ${tanggal_naskah}', space_before=20, left_indent=80)
        add_content(doc=doc, content='Direktur', left_indent=80, space_after=30)
        add_content(doc=doc, content='${ttd_pengirim}', left_indent=80, )
        add_content(doc=doc, content=f'{penempatan.penempatan_level1.nama_pimpinan.full_name_2}', left_indent=80, space_before=30)
        add_content(doc=doc, content=f'{panggol.panggol if hasattr(panggol, "panggol") else None}', left_indent=80)
        add_content(doc=doc, content=f'NIP. {penempatan.penempatan_level1.nama_pimpinan.profil_user.nip}', left_indent=80)
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename=spt-pelatihan-{detail_pegawai.full_name}.docx'
        doc.save(response)

        return response


class TextSPTDiklatView(View):
    def get_object(self, id):
        try:
            data=TextSPTDiklat.objects.get(id=id)
            return data
        except TextSPTDiklat.DoesNotExist:
            return None
        
    def get_diklat_object(self, id):
        try:
            data = RiwayatDiklat.objects.get(id=id)
            return data
        except RiwayatDiklat.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        id_diklat = kwargs.get('diklat_id')
        id = kwargs.get('id')
        get_form = request.GET.get('f')
        data_view = 'block'
        form_view = 'none'
        if get_form is not None:
            form_view = 'block'
            data_view = 'none'
        detail = self.get_object(id)
        riwayatdiklat = self.get_diklat_object(id_diklat)
        data=TextSPTDiklat.objects.filter(diklat=riwayatdiklat.usulan)
        form = TextSPTDiklatForm(instance=detail, diklat=riwayatdiklat.usulan)
        context={
            'id_layanan':id_diklat,
            'layanan':riwayatdiklat.usulan,
            'data':data,
            'form':form,
            'data_view':data_view,
            'form_view':form_view
        }
        return render(request, 'spt_text/spt_text_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        id_diklat = kwargs.get('diklat_id')
        detail = self.get_object(id)
        form = TextSPTDiklatForm(data=request.POST, instance=detail)
        if form.is_valid():
            form.save()
            messages.success(request, "Data berhasil disimpan!")
            return redirect(reverse('file_urls:text_spt_view', kwargs={'diklat_id':id_diklat}))
        messages.error(request, 'Datata gagal disimpan!')
        return redirect(reverse('file_urls:text_spt_view', kwargs={'diklat_id':id_diklat}))