HADIST_MODAL_SESSION_VERSION = 'v3'


def hadist_modal_session_key(user):
    """Kunci session modal yang berbeda untuk setiap akun pengguna."""
    return (
        f'hadist_modal_sudah_ditampilkan_'
        f'{HADIST_MODAL_SESSION_VERSION}_{user.pk}'
    )
