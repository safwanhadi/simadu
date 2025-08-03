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