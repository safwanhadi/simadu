from django import template
import locale
from datetime import datetime


register = template.Library()

@register.simple_tag
def wajib_field(form, field_name):
    """Render hidden or required field even kalau tidak terlihat di form."""
    bound_field = form[field_name]
    return str(bound_field)



@register.filter
def tanggal_indonesia(value):
    if isinstance(value, datetime):
        value = value.date()
    try:
        locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
    except locale.Error:
        # Fallback jika locale tidak tersedia
        return value.strftime('%d %B %Y')
    return value.strftime('%d %B %Y')


@register.simple_tag(takes_context=True)
def querystring_filter(context, *keys):
    request = context['request']
    params = request.GET.copy()
    for k in list(params.keys()):
        if k not in keys:
            del params[k]
    return params.urlencode()


@register.filter(name='to_month_name')
def to_month_name(month_number):
    """
    Mengonversi angka (integer) 1-12 menjadi nama bulan Indonesia.
    """
    # Pastikan input adalah integer
    try:
        month_number = int(month_number)
    except (ValueError, TypeError):
        return month_number # Kembalikan nilai asli jika bukan angka

    # Daftar nama bulan (index 0 dikosongkan agar index 1 = Januari)
    months = [
        None, 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ]

    # Periksa apakah angka berada dalam rentang yang valid (1-12)
    if 1 <= month_number <= 12:
        return months[month_number]
    
    # Kembalikan nilai asli jika angka tidak valid
    return month_number