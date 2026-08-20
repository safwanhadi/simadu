import calendar
from django import template

register = template.Library()


@register.filter
def month_name(bulan):
    try:
        nomor_bulan = int(bulan)
    except (TypeError, ValueError):
        return ''

    if not 1 <= nomor_bulan <= 12:
        return ''
    return calendar.month_name[nomor_bulan]
