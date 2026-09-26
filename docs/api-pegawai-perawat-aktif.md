# Akses API Pegawai Perawat Aktif dengan Client M-to-M

Dokumen ini menjelaskan cara aplikasi server mengakses daftar pegawai perawat aktif di SIMADU menggunakan OAuth 2.0 `client_credentials`. Alur ini ditujukan untuk komunikasi antarsistem (machine-to-machine/M-to-M), tanpa login pengguna melalui browser.

## Endpoint

| Keperluan | Method | URL produksi |
| --- | --- | --- |
| Meminta access token | `POST` | `https://simadu.rsmandalika.com/o/token/` |
| Mengambil semua perawat aktif | `GET` | `https://simadu.rsmandalika.com/accounts/api/pegawai-perawat-aktif/` |
| Mencari perawat aktif berdasarkan NIP | `GET` | `https://simadu.rsmandalika.com/accounts/api/pegawai-perawat-aktif/?nip={NIP}` |

Endpoint data memerlukan scope `read:pegawai`. Respons tidak dipaginasi dan hanya berisi identitas minimum pegawai.

## 1. Pembuatan credential oleh admin SIMADU

Admin yang memiliki peran **Admin SSO** membuka menu **Pengelolaan Integrasi SSO**, kemudian membuat aplikasi dengan konfigurasi berikut:

- Tipe client: **Confidential**
- Jenis grant: **Client credentials**
- Redirect URI: dikosongkan karena alur ini tidak menggunakan browser
- Nama aplikasi: gunakan nama sistem pemanggil yang mudah diaudit

SIMADU menampilkan `client_secret` hanya satu kali setelah aplikasi dibuat atau secret dirotasi. Pengelola sistem pemanggil harus menyimpan `client_id` dan `client_secret` di secret manager atau environment variable pada server, bukan di source code, repository, log, maupun aplikasi sisi browser.

## 2. Meminta access token

Kirim credential menggunakan HTTP Basic Authentication. Cara ini lebih disarankan daripada mengirim secret di request body.

```bash
curl --request POST \
  --url "https://simadu.rsmandalika.com/o/token/" \
  --user "${SIMADU_CLIENT_ID}:${SIMADU_CLIENT_SECRET}" \
  --header "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=client_credentials" \
  --data-urlencode "scope=read:pegawai"
```

Contoh respons berhasil:

```json
{
  "access_token": "ACCESS_TOKEN",
  "expires_in": 3600,
  "token_type": "Bearer",
  "scope": "read:pegawai"
}
```

Access token berlaku selama nilai `expires_in` (saat ini 3.600 detik). Grant `client_credentials` tidak menggunakan refresh token; minta access token baru ketika token akan atau sudah kedaluwarsa.

## 3. Mengakses data

Gunakan access token sebagai Bearer token:

```bash
curl --request GET \
  --url "https://simadu.rsmandalika.com/accounts/api/pegawai-perawat-aktif/" \
  --header "Authorization: Bearer ${SIMADU_ACCESS_TOKEN}" \
  --header "Accept: application/json"
```

Pencarian satu NIP dapat dilakukan dengan query parameter yang di-URL-encode:

```bash
curl --get \
  --url "https://simadu.rsmandalika.com/accounts/api/pegawai-perawat-aktif/" \
  --header "Authorization: Bearer ${SIMADU_ACCESS_TOKEN}" \
  --header "Accept: application/json" \
  --data-urlencode "nip=198001012010011001"
```

Contoh respons berhasil (`200 OK`):

```json
[
  {
    "nip": "198001012010011001",
    "email": "perawat@example.go.id",
    "first_name": "Siti",
    "last_name": "Perawat",
    "full_name": "Siti Perawat"
  }
]
```

Jika NIP tidak ditemukan atau pegawai tidak lagi aktif/terklasifikasi sebagai perawat, respons tetap `200 OK` dengan array kosong (`[]`). Nilai `nip` dapat berupa `null` bila profil pegawai belum memiliki NIP.

## Penanganan kegagalan

| Kondisi | Respons umum | Tindakan |
| --- | --- | --- |
| `client_id` atau `client_secret` salah | `401` dari token endpoint, `invalid_client` | Verifikasi credential; minta admin merotasi secret bila perlu. |
| Grant aplikasi bukan `client_credentials` | `400`, `unauthorized_client` | Minta admin memperbaiki jenis grant aplikasi. |
| Scope tidak menyertakan `read:pegawai` | `403 Forbidden` pada endpoint data | Minta token ulang dengan `scope=read:pegawai`. |
| Token tidak ada, salah, atau kedaluwarsa | `401 Unauthorized` | Minta access token baru dan ulangi request satu kali. |
| Gangguan sementara server | `5xx` | Terapkan retry terbatas dengan exponential backoff; jangan mencatat token pada log. |

## Ketentuan keamanan operasional

- Panggil endpoint hanya melalui HTTPS dari backend/server tepercaya.
- Jangan mengirim `client_secret` atau access token ke frontend, aplikasi seluler, URL, maupun query string.
- Cache access token hanya sampai masa berlakunya dan beri margin sebelum kedaluwarsa.
- Rotasi secret segera jika credential diduga bocor. Secret lama langsung tidak berlaku setelah rotasi.
- Batasi log pada status HTTP, waktu, dan correlation ID; jangan mencatat header `Authorization` atau isi credential.
- Gunakan data hanya untuk tujuan integrasi yang telah disetujui dan terapkan pembatasan akses pada sistem penerima.
