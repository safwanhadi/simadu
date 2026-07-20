import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

logger = logging.getLogger(__name__)


class RestrictToExistingUserAdapter(DefaultSocialAccountAdapter):
    """Izinkan social login hanya untuk user lokal yang sudah terdaftar."""

    def is_open_for_signup(self, request, sociallogin):
        # Matching user existing ditangani secara aman melalui konfigurasi
        # EMAIL_AUTHENTICATION Google. Jika tidak cocok, jangan buat user baru.
        return False

    def on_authentication_error(
        self,
        request,
        provider,
        error=None,
        exception=None,
        extra_context=None,
    ):
        # Catat tipe kegagalan tanpa menulis authorization code, token, atau
        # detail exception yang mungkin memuat data autentikasi ke log.
        logger.warning(
            'Social login gagal: provider=%s code=%s exception_type=%s',
            getattr(provider, 'id', 'unknown'),
            error,
            type(exception).__name__ if exception else None,
        )
        return super().on_authentication_error(
            request,
            provider,
            error=error,
            exception=exception,
            extra_context=extra_context,
        )
