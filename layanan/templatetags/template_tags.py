import calendar
from django import template

register = template.Library()


@register.filter
def month_name(bulan):
    return calendar.month_name[bulan]