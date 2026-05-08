from django import template
from urllib.parse import urlencode

register = template.Library()

@register.filter
def dict_get(d, key):
    return d.get(key)


@register.simple_tag(takes_context=True)
def querystring_smart_filter(context, *args_to_keep, **kwargs_to_set):
    """
    Tag serbaguna untuk memanipulasi parameter query.
    - Mempertahankan semua parameter yang ada secara default.
    - Jika diberi argumen posisi ('q', 'inst'), hanya akan mempertahankan parameter tersebut.
    - Jika diberi argumen keyword (page=2), akan menambah/mengubah parameter tersebut.
    """
    # Mulai dengan dictionary kosong yang akan kita bangun
    final_params = {}
    
    # Ambil QueryDict dari request
    request_params = context['request'].GET

    # Jika ada argumen posisi, artinya kita HANYA ingin mempertahankan kunci-kunci ini
    if args_to_keep:
        for key in args_to_keep:
            # Ambil semua nilai untuk kunci tersebut
            if key in request_params:
                final_params[key] = request_params.getlist(key)
    # Jika tidak ada argumen posisi, kita pertahankan SEMUA parameter yang ada
    else:
        for key in request_params.keys():
            final_params[key] = request_params.getlist(key)

    # Sekarang, terapkan perubahan dari argumen keyword
    for key, value in kwargs_to_set.items():
        # Jika nilainya valid, set ke dictionary. Ini akan menggantikan yang lama.
        if value is not None and value != '':
            final_params[key] = value
        # Jika tidak, hapus kuncinya jika ada
        elif key in final_params:
            del final_params[key]
            
    # Logic Pembersihan Terakhir
    if not final_params:
        return ""  # Jika kosong, jangan beri apa pun
        
    # Kembalikan dengan tanda tanya di depannya secara otomatis
    return "?" + urlencode(final_params, doseq=True)