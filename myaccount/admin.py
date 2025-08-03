from django.contrib import admin
from .models import ProfilSDM, Users, Gender, ProfilAdmin
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
# from.models import ExtendedUser
# from django.contrib.auth.admin import UserAdmin


from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserAdminCreationForm, UserAdminChangeForm


# @admin.register(Group)
# class GroupAdmin(admin.ModelAdmin):
#     search_fields = ("name",)
#     ordering = ("name",)
#     filter_horizontal = ("permissions",)

#     def formfield_for_manytomany(self, db_field, request=None, **kwargs):
#         if db_field.name == "permissions":
#             qs = kwargs.get("queryset", db_field.remote_field.model.objects)
#             # Avoid a major performance hit resolving permission names which
#             # triggers a content_type load:
#             kwargs["queryset"] = qs.select_related("content_type")
#         return super().formfield_for_manytomany(db_field, request=request, **kwargs)

class UserAdmin(BaseUserAdmin):
    # The forms to add and Change user instance
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    # the fields to be used in displaying the user model
    # these override the definitions on the base useradmin
    # that refrence specific fields on auth.user
    list_display = ('email', 'first_name', 'last_name', 'is_active',)
    list_filter = ('is_staff', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('email', 'password', 'first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_guest', 'is_staff', 'is_superuser', 'groups', 'user_permissions',)})
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2')}
         ),
    )
    search_fields = ('email', 'first_name')
    ordering = ('email',)
    filter_horizontal = (
        "groups",
        "user_permissions",
    )
    
    class Meta:
        model = Users
    
    
class DetailProfilSDM(admin.ModelAdmin):
    list_display=('user', 'no_hp', 'nip', 'is_dokter_spesialis')
    list_filter=('is_dokter_spesialis', )
    search_fields=('nip', 'user__email', 'user__first_name', 'user__last_name')

admin.site.register(Users, UserAdmin)
admin.site.register(ProfilSDM, DetailProfilSDM)
admin.site.register(Gender)
admin.site.register(ProfilAdmin)
#