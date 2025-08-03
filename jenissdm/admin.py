from django.contrib import admin

from .models import JenisSDM, ListKompetensi, ProfesiSDM

# Register your models here.
class ListKompetensiAdmin(admin.ModelAdmin):
    ordering = ["jenis_sdm"]
    search_fields = ['kompetensi']

    # def get_search_results(self, request, queryset, search_term):
    #     queryset, use_distinct = super().get_search_results(request, queryset, search_term)
    #     if 'autocomplete' in request.path and request.GET.get('model_name') == 'standarinstalasi' and request.GET.get('field_name') == 'kompetensi_wajib':
    #         queryset = queryset.filter(sifat='Wajib')
    #     elif 'autocomplete' in request.path and request.GET.get('model_name') == 'standarinstalasi' and request.GET.get('field_name') == 'kompetensi_pendukung':
    #         queryset = queryset.filter(sifat='Pendukung')
    #     return queryset, use_distinct

admin.site.register(ProfesiSDM)
admin.site.register(JenisSDM)
admin.site.register(ListKompetensi, ListKompetensiAdmin)
