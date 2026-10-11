class Scopes:
    # Kepegawaian (SIMADU)
    READ_PEGAWAI = 'read:pegawai'
    READ_LIST_PEGAWAI='read:listpegawai'
    
    # Presensi Fingerprint
    READ_ATTLOG = 'read:attlog'
    SYNC_ATTLOG = 'sync:attlog'
    MANAGE_ATTLOG = 'manage:attlog'
    
    # Medis (SIMRS)
    READ_RM = 'read:rm_read'
    WRITE_RM = 'write:rm_write'
    
    # Pasien (Epasien)
    READ_RESUME = 'read:resume_read'
    WRITE_BOOKING = 'write:booking_write'
    
    # Dashboard
    READ_DASH = 'read:dash'
    
    # OpenID Connect
    OPENID = 'openid'
    PROFILE = 'profile'
    
    # MCU
    WRITE_MCU='write:mcu'
    
    # Koneksi Backend-Frontend
    READ_BACKEND='read:backend'
    
    SIMRS_INDIKATOR = 'simrs.indicators.read'
    SIMRS_API = 'simrs_api'
    @classmethod
    def as_choices(cls):
        return {
            cls.OPENID: 'OpenID Connect Hub',
            cls.PROFILE: 'Akses informasi profil dasar',
            
            cls.READ_PEGAWAI: 'Membaca data profil pegawai',
            cls.READ_LIST_PEGAWAI: 'Membaca daftar pegawai',
            cls.READ_ATTLOG: 'Membaca log kehadiran presensi',
            cls.SYNC_ATTLOG: 'Menandai data sudah sinkron',
            cls.MANAGE_ATTLOG: 'Menghapus atau memodifikasi data',
            
            cls.READ_RM: 'Membaca rekam medis lengkap',
            cls.WRITE_RM: 'Menulis rekam medis',
            cls.WRITE_MCU: 'Akses admin MCU',
            
            cls.READ_RESUME: 'Membaca resume medis pasien',
            cls.WRITE_BOOKING: 'Menulis booking pemeriksaan',
            cls.SIMRS_API: 'AKtifitas CRUD API SIMRS',
            cls.READ_DASH: 'Membaca data untuk dashboard',
            cls.SIMRS_INDIKATOR: 'Membaca indikator SIMRS',
            
            cls.READ_BACKEND: 'Membaca data dari backend',
        }