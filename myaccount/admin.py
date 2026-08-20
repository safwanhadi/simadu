from django.contrib import admin
from .models import (
    AccountRegistration, AdminScopeAssignment, Gender, ProfilAdmin, ProfilSDM,
    TelegramAccount, Users,
)
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
    list_display = ('email', 'first_name', 'last_name', 'admin_groups', 'is_active',)
    list_filter = ('groups', 'is_staff', 'is_superuser')
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

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('groups')

    @admin.display(description='Grup Admin')
    def admin_groups(self, obj):
        return ', '.join(group.name for group in obj.groups.all()) or '-'
    
    
class DetailProfilSDM(admin.ModelAdmin):
    list_display=('user', 'no_hp', 'nip', 'is_dokter_spesialis')
    list_filter=('is_dokter_spesialis', )
    search_fields=('nip', 'user__email', 'user__first_name', 'user__last_name')

admin.site.register(Users, UserAdmin)
admin.site.register(ProfilSDM, DetailProfilSDM)
admin.site.register(Gender)
admin.site.register(ProfilAdmin)


@admin.register(AdminScopeAssignment)
class AdminScopeAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'group', 'scope_type', 'scope_object_display', 'is_active',
        'valid_from', 'valid_until',
    )
    list_filter = ('group', 'scope_type', 'is_active')
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name', 'group__name',
    )
    autocomplete_fields = ('user',)
    readonly_fields = ('scope_key', 'created_at', 'updated_at')

    @admin.display(description='Target struktur')
    def scope_object_display(self, obj):
        return obj.scope_object or 'Seluruh organisasi'


@admin.register(TelegramAccount)
class TelegramAccountAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'telegram_user_id', 'telegram_username', 'phone_number',
        'verified_at', 'last_reset_requested_at',
    )
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'telegram_username', 'phone_number',
    )
    readonly_fields = ('verified_at', 'created_at', 'updated_at')
#


@admin.register(AccountRegistration)
class AccountRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'submitted_at', 'reviewed_at', 'reviewed_by')
    list_filter = ('status',)
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'user__profil_user__nip',
    )
    readonly_fields = ('submitted_at', 'reviewed_at', 'reviewed_by')
