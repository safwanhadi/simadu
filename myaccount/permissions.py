from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from oauth2_provider.contrib.rest_framework.permissions import IsAuthenticatedOrTokenHasScope


class IsAppAdminOrTokenHasScope(IsAuthenticatedOrTokenHasScope):
    def has_permission(self, request, view):
        if isinstance(request.successful_authenticator, OAuth2Authentication):
            return super().has_permission(request, view)

        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_app_admin
        )
