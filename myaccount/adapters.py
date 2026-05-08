from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

User = get_user_model()

class RestrictToExistingUserAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # 1. Ambil email dari akun Google yang mencoba login
        email = sociallogin.user.email
        
        # 2. Cek apakah user dengan email tersebut sudah ada di database Django
        if not User.objects.filter(email=email).exists():
            # 3. Jika tidak ada, batalkan login dan beri respon error
            # Anda bisa melempar PermissionDenied agar muncul halaman 403
            raise PermissionDenied("Akun Anda belum terdaftar. Silakan hubungi administrator.")