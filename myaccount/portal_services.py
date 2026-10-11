from django.conf import settings

from .models import PortalApplication


PORTAL_MODEL_FIELDS = (
    'label', 'type', 'client_id', 'redirect_uri', 'login_url', 'scopes',
    'dashboard', 'dashboard_absensi', 'icon', 'icon_image', 'bg_class',
    'category', 'enabled',
)


def get_portal_applications(include_disabled=False):
    applications = {}
    for key, client in settings.SSO_CLIENTS.items():
        visual = settings.APP_VISUAL.get(key, {})
        applications[key] = {
            'key': key,
            'label': client.get('label', key),
            'type': client.get('type', PortalApplication.OAUTH_CLIENT),
            'client_id': client.get('client_id', ''),
            'redirect_uri': client.get('redirect_uri', ''),
            'login_url': client.get('login_url') or '',
            'scopes': client.get('scopes', ''),
            'dashboard': client.get('dashboard', ''),
            'dashboard_absensi': client.get('dashboard_absensi', ''),
            'icon': visual.get('icon', 'fas fa-th-large'),
            'icon_image': visual.get('icon_image', ''),
            'bg_class': visual.get(
                'bg_class',
                'bg-gradient-to-br from-blue-500 to-blue-600',
            ),
            'category': visual.get('category', 'Umum'),
            'enabled': True,
            'is_default': True,
        }

    for stored in PortalApplication.objects.all():
        applications[stored.key] = {
            field: getattr(stored, field)
            for field in PORTAL_MODEL_FIELDS
        } | {
            'key': stored.key,
            'is_default': stored.key in settings.SSO_CLIENTS,
            'pk': stored.pk,
        }

    if not include_disabled:
        applications = {
            key: application
            for key, application in applications.items()
            if application['enabled']
        }
    return applications


def get_portal_application(key):
    return get_portal_applications(include_disabled=True).get(key)


def portal_application_model_defaults(application):
    return {
        field: application[field]
        for field in PORTAL_MODEL_FIELDS
    }
