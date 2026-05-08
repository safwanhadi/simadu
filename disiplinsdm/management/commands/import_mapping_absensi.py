"""
Cara menjalankan:
# === STEP 1: Preview dulu (tanpa menyimpan) ===
python manage.py import_mapping_absensi --dry-run

# === STEP 2: Jika sudah yakin, jalankan tanpa --dry-run ===
python manage.py import_mapping_absensi

# === STEP 3: Jika ingin overwrite mapping yang sudah ada ===
python manage.py import_mapping_absensi --overwrite

"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from myaccount.models import Users
from ...models import MappingMesinAbsensi

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import mapping data mesin absensi ke SIMADU'

    def bold(self, text):
        return f'\033[1m{text}\033[0m'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Jalankan tanpa menyimpan ke database (untuk preview)',
        )
        parser.add_argument(
            '--skip-duplicate-mesin',
            action='store_true',
            default=True,
            help='Lewati jika mesin_id sudah dipakai pegawai lain',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite mapping yang sudah ada untuk pegawai yang sama',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_duplicate_mesin = options['skip_duplicate_mesin']
        overwrite = options['overwrite']

        mapping_data = [
            (9, "M. Sapoan Hadi", "00000348", "M. Sapoan Hadi, S.ST.Kep., M.K.M"),
            (10, "Ali Mustofa", "00000223", "Ali Mustofa, S.Kep. Ns. MM.,FisQua"),
            (11, "Muh. Winarta Hidayat", "00000347", "Muh. Winarta Hidayat, S.Kep."),
            (12, "Supardi", "00000349", "Ns. Supardi, S.Kep.,MPH"),
            (14, "Ratnate", "00000259", "Ratnate, S.IP"),
            (15, "Rosaria Rumilan", "00000014", "Rosaria Rumilan, A.Md.Kep."),
            (16, "Ibnu Hariys Munandar", "00000288", "Ibnu Hariys Munandar, A.Md.Kep."),
            (17, "Youri Gagarin", "00000086", "Youri Gagarin, S.Keb."),
            (19, "Lalu Wilham Fauzi", "00000154", "Lalu Wilham Fauzi, A.Md.Perkes"),
            (20, "Riadna Husli Fattul Jannah", "00000027", "Riadna Husli Fattul Jannah, S.T"),
            (21, "Rufaida Rosyida", "00000172", "Rufaida Rosyida S.Tr.Gz,M.Gz."),
            (22, "Wayan Budiartha", "00000267", "I Wayan Budiartha"),
            (23, "Suhardi", "00000247", "Suhardi"),
            (24, "Baiq Pina Dwi Hartati", "00000321", "Baiq Pina Dwi Hartati,A.Md.Gz"),
            (25, "Muliati", "00000028", "Muliati"),
            (26, "Nisa Febriana", "00000137", "Nisa Febriana, AMd.Kep."),
            (27, "Tri Sandi Yasir", "00000082", "Tri Sandi Yasir, A.Md.KG"),
            (33, "Afif Muhammad Kholis", "00000016", "Afif Muhammad Kholis, S.Sos"),
            (34, "Fahrudi Hamdiya'kub", "00000177", "Fahrudi Hamdiya'kub, S.Kom"),
            (37, "Mala Arjuna", "00000010", "MALA ARJUNA, S.Pd."),
            (38, "Mita Sara Dewi", "00000280", "Mita Sara Dewi, A.Md.Ak"),
            (39, "Annisa Aliya Rahmatin", "00000032", "Annisa Aliya Rahmatin, S.S"),
            (41, "Muhammad Habib Ikroman", "00000183", "Muhammad Habib Ikroman, S.IP"),
            (42, "Ida Kurniasari", "00000029", "Ida Kurniasari, SM"),
            (43, "Lalu Abdul Rasyid", "00000061", "Lalu Abdul Rasyid, A.P"),
            (44, "Jabbar Akhmad", "00000322", "Jabbar Akhmad, S.Kom"),
            (46, "Ali Baba", "00000305", "Ali Baba, S.Kom"),
            (53, "Lalu Dedy Supriadi", "00000062", "Lalu Dedy Supriadi"),
            (54, "Ahmadudin", "00000301", "Ahmadudin"),
            (56, "Suherman", "00000124", "Suherman"),
            (57, "Dani Ramdhansyah", "00000337", "Dani Ramdhansyah, S.Kep.Ners"),
            (58, "Sri Noviana Lestari", "00000294", "Sri Noviana Lestari, A.Md.RMIK"),
            (59, "Siti Qamariah", "00000077", "Siti Qamariah, AMK"),
            (62, "Rumelim", "00000320", "Rumelim"),
            (63, "Kadir", "00000072", "Kadir"),
            (64, "Marsandi", "00000039", "Marsandi"),
            (65, "Muhamad Rusli", "00000273", "Muhamad Rusli"),
            (67, "Wawan Hartono", "00000244", "Wawan Hartono"),
            (68, "Agus Kuswara Masudi", "00000038", "Agus Kuswara Masudi"),
            (69, "Nurdiansah", "00000227", "Nurdiansah"),
            (75, "Neni Usmayani", "00000248", "Neni Usmayani"),
            (76, "Sriyuti", "00000042", "Sriyuti, A.Md."),
            (77, "Baiq Erma Asmayati", "00000233", "apt. Baiq Erma Asmayati, S.Farm"),
            (78, "Dwi Nurfinalita Mayanti", "00000235", "apt. Dwi Nurfinalita Mayanti, S.Farm"),
            (79, "Ayu Tri Susilawaty", "00000255", "Ayu Tri Susilawaty, AMd. Farm"),
            (80, "Ishaka", "00000311", "Ishaka, AMd. Farm"),
            (82, "Sugesti putri gare", "00000256", "Sugesti putri gare, AMd. Farm"),
            (83, "Muhammad Syafrudin", "00000253", "Muhammad Syafrudin, AMd. Farm"),
            (84, "Diana Apriani Putri", "00000051", "Diana Apriani Putri, S.ST"),
            (86, "Rindiana", "00000108", "Rindiana, S.Tr.Keb"),
            (87, "Layina Sopiana", "00000143", "Layina Sopiana, S.Tr.Keb"),
            (88, "Samsul Hakim", "00000304", "Samsul Hakim, S.E."),
            (89, "Erny Adi Yanti", "00000212", "Erny Adi Yanti, S.Sos"),
            (92, "Made Nugraha Dwitama", "00000030", "Made Nugraha Dwitama,S.Kom"),
            (93, "Muhammad Sibawaihi", "00000089", "Muhammad Sibawaihi"),
            (97, "Nurul Hidayati", "00000097", "Nurul Hidayati"),
            (100, "Sufianita", "00000243", "Sufianita"),
            (101, "Gusti Ayu Putu Candra Dewi", "00000315", "apt. Gusti Ayu Putu Candra Dewi, S.Farm"),
            (102, "Muhammad Sahindrawan Firmansyah", "00000268", "apt. Muhammad Sahindrawan Firmansyah, S.Farm"),
            (103, "Gede Putra Aditya Brahmantha", "00000325", "Gede Putra Aditya Brahmantha, S.Kom"),
            (105, "Samsi Jayadi", "00000021", "Samsi Jayadi, AMTE"),
            (106, "Haola Agustina Anwar", "00000026", "Haola Agustina Anwar, A.Md.,S.T"),
            (107, "Ni Komang Tri Cahya Septiani", "00000157", "Ni Komang Tri Cahya Septiani, S.Tr.Gz"),
            (108, "Tanthowi Jauhari", "00000155", "Tanthowi Jauhari, A.Md.RMIK"),
            (109, "Aria Wardani", "00000330", "Aria Wardani, A.Md.Farm"),
            (111, "Muhammad Bahraen Sutamandala", "00000258", "apt. Muhammad Bahraen Sutamandala, S.Farm"),
            (112, "Sri Rahayu Wulandari", "00000178", "Sri Rahayu Wulandari, A.Md.Keb"),
            (114, "Darmi Saputri", "00000179", "Darmi Saputri, A.Md.Keb"),
            (115, "Fontanella Dwiputri", "00000035", "Fontanella Dwiputri, A.Md.Keb"),
            (116, "Ayu Oktaviani", "00000129", "Ayu Oktaviani, A.Md.Keb"),
            (117, "Titin Maizuroh", "00000110", "Titin Maizuroh, A.Md.Keb."),
            (118, "Baiq Wahyu Ika Purnami", "00000184", "Baiq Wahyu Ika Purnami, A.Md. Keb."),
            (119, "M. Yusi Iswahyudi", "00000149", "M. Yusi Iswahyudi, A.Md.Kep"),
            (120, "Ahmad Syarkawi", "00000215", "Ahmad Syarkawi, A.Md.Kep"),
            (121, "Hasan Basri", "00000133", "Hasan Basri, A.Md.Kep"),
            (122, "Rahmad Kurniadi", "00000324", "Rahmad Kurniadi, A.Md.Kep"),
            (124, "Fridha Rizky Amelia", "00000130", "Fridha Rizky Amelia, A.Md.Kep"),
            (125, "Dwi Ahyani", "00000343", "Dwi Ahyani, A.Md.Kep"),
            (126, "Ari Kusumawijaya", "00000316", "Ari Kusumawijaya, A.Md.Kep."),
            (127, "Akhmad Sukri Jasilin", "00000165", "Akhmad Sukri Jasilin, A.Md.Kep."),
            (128, "Hana Melia Rosalina", "00000204", "Ns. Hana Melia Rosalina, S.Kep"),
            (129, "Taufiqurrahman", "00000055", "Ns. Taufiqurrahman, S.Kep"),
            (130, "Yulma Hawya Fatmi", "00000111", "Ns. Yulma Hawya Fatmi, S.Kep"),
            (131, "Nahdatuz Zainiah", "00000225", "Ns. Nahdatuz Zainiah, S.Kep"),
            (132, "Rani Via Endaswari", "00000217", "Ns. Rani Via Endaswari, S.Kep"),
            (133, "Nur Arifiyati Rohmi", "00000220", "Ns.Nur Arifiyati Rohmi, S.Kep"),
            (134, "Dewi Helmiza Asmayanti", "00000052", "Ns. Dewi Helmiza Asmayanti, S.Kep"),
            (135, "Baiq Dinda Dewi Langkasari", "00000249", "Ns. Baiq Dinda Dewi Langkasari, S.Kep"),
            (136, "Arini Sofianti", "00000020", "Ns. Arini Sofianti, S.Kep"),
            (137, "Lalu Topan Hidayatullah", "00000351", "Ns. Lalu Topan Hidayatullah, S.Kep"),
            (138, "Shilviani Safitri", "00000353", "Ns. Shilviani Safitri, S.Kep"),
            (139, "Iis Meliana", "00000216", "Ns. Iis Meliana, S.Kep"),
            (140, "Ekky Adietia Saputra", "00000141", "Ns. Ekky Adietia Saputra, S.Kep"),
            (141, "Dewi Santikawati", "00000161", "Ns. Dewi Santikawati, S.Kep"),
            (142, "Ahmad Turmuzi Satriawan", "00000142", "Ns. Ahmad Turmuzi Satriawan, S.Kep"),
            (143, "Akhmad Mukhlis Karunia Ramdhani", "00000292", "Ns. Akhmad Mukhlis Karunia Ramdhani, S.Kep"),
            (144, "Isni Winarni", "00000153", "Ns. Isni Winarni, S.Kep"),
            (145, "Yudhi Slamaet Ruyanda", "00000080", "Ns. Yudhi Slamet Ruyanda, S.Kep."),
            (146, "Ulfathul Khasanah", "00000100", "Ns. Ulfathul Khasanah, S.Kep."),
            (147, "Farid Alpandi", "00000328", "Farid Alpandi, S.Tr.Kep"),
            (148, "Suci Ariani", "00000056", "dr. Suci Ariani"),
            (149, "Redhia Fararri", "00000284", "Redhia Fararri, S.Tr.Kom"),
            (152, "Muhtar Hartono", "00000095", "Muhtar Hartono"),
            (153, "Agus Herman Pilih Harta", "00000025", "Agus Herman Pilih Harta"),
            (155, "Lestari Nur Azizah", "00000164", "Lestari Nur Azizah, A.Md.T"),
            (156, "Rumeli", "00000332", "Rumeli"),
            (157, "Lalu Marindratin Trijunasakti", "00000327", "Lalu Marindratin Trijunasakti, S.Tr.Kes."),
            (159, "Rizki Yuniasti", "00000231", "Rizki Yuniasti, A.Md,Kes"),
            (160, "Moh. Ardiman Rusdiansyah", "00000333", "Moh. Ardiman Rusdiansyah, S.Tr.Rad"),
            (161, "Novia Silviana", "00000201", "Novi Silviana S.Tr.Rad"),
            (162, "Suharti", "00000313", "Suharti, A.Md.AK"),
            (163, "Desi Khaerani", "00000199", "Desi Khaerani, AMd.AK"),
            (165, "Baiq Nida Solehah", "00000314", "Baiq Nida Solehah, S.Tr.Kes"),
            (167, "Erni Yusnitha", "00000319", "Erni Yusnitha, A.Md.RMIK"),
            (168, "Ahmad sofian sauri", "00000296", "Ahmad sofian sauri, A.Md.RMIK"),
            (169, "Hilvia Syurviana", "00000067", "Hilvia Syurviana, A.Md.Kep."),
            (170, "Lale Wahana Yatmi", "00000285", "Lale Wahana Yatmi, A.Md.Kep."),
            (171, "Saharudin", "00000036", "Saharudin, A.Md.Kep."),
            (172, "Baiq Elisha Dwi Apriyatni", "00000287", "Baiq Elisha Dwi Apriyatni, A.Md.Kep."),
            (173, "Irma Ariani", "00000054", "Ns. Irma Ariani, S.Kep."),
            (174, "Nyoman Kusala Putra", "00000049", "Ns. Nyoman Kusala Putra, S.Kep."),
            (175, "Khairunnisak", "00000083", "Ns. Khairunnisak. S.Kep."),
            (176, "Muswarawati", "00000228", "Ns. Muswarawati, S.Kep."),
            (177, "Tino Khairiawan", "00000074", "Ns. Tino Khairiawan, S.Kep."),
            (178, "Rusniati Andani", "00000186", "Ns. Rusniati Andani, S.Kep."),
            (179, "Oktarina Windari", "00000190", "Ns. Oktarina Windari, S.Kep."),
            (180, "Baiq Neneng Septariani", "00000078", "Ns. Baiq Neneng Septariani, S.Kep."),
            (181, "Maylani Chindi Lestari Ayu", "00000057", "Ns. Maylani Chindi Lestari Ayu, S.Kep."),
            (182, "Nanang Alfian", "00000017", "Ns. Nanang Alfian, S.Kep."),
            (183, "Asmawati Fitriana J", "00000162", "Ns. Asmawati Fitriana J, S.Kep."),
            (184, "Ahmad Masyhudi", "00000079", "Ns. Ahmad Masyhudi, S.Kep."),
            (185, "Eka Puspitasari", "00000188", "Ns. Eka Puspitasari, S.Kep."),
            (186, "Eka Noviana Zubaidah", "00000281", "Ns. Eka Noviana Zubaidah, S.Kep."),
            (187, "Muhammad Hilal Arafat", "00000279", "Ns. Muhammad Hilal Arafat, S.Kep."),
            (188, "Siti Shofiyah", "00000112", "Ns. Siti Shofiyah S.Kep."),
            (189, "Lalu Jamiludin", "00000219", "Ns. Lalu Jamiludin, S.Kep."),
            (190, "Siti Hidayatun Nur", "00000189", "Ns. Siti Hidayatun Nur, S.Kep."),
            (191, "Hendra Wadi", "00000192", "Ns. Hendra Wadi, S.Kep."),
            (193, "Widya Dewi Apriyanti", "00000286", "Ns. Widya Dewi Apriyanti, S.Kep."),
            (194, "Muhammad Gazali", "00000195", "Ns. Muhammad Gazali, S.Kep."),
            (197, "Muhamad Kasiran", "00000070", "Ns. Muhamad Kasiran, S.Kep."),
            (199, "Titik Pardianti", "00000115", "Ns. Titik Pardianti, S.Kep."),
            (200, "Martina Irma Firmana", "00000293", "Ns. Martina Irma Firmana, S.Kep."),
            (201, "Lalu Feri Susanto", "00000090", "Ns. Lalu Feri Susanto, S.Kep."),
            (203, "Medal Hadi", "00000069", "Ns. Medal Hadi, S.Kep."),
            (204, "Ida Ayu Made Srigati", "00000053", "Ns. Ida Ayu Made Srigati, S.Kep."),
            (206, "Dewi Ratnasari", "00000152", "Dewi Ratnasari, S.Gz"),
            (207, "Muhamad Dedi Saputra", "00000334", "dr. Muhamad Dedi Saputra"),
            (210, "Baiq Jema Marandra Emkamas", "00000344", "dr. Baiq Jema Marandra Emkamas"),
            (211, "Baiq Nurul Indra Aswari", "00000276", "Baiq Nurul Indra Aswari, A.Md.Keb"),
            (212, "Baiq Heni Mulyana", "00000034", "Baiq Heni Mulyana, A.Md.Keb"),
            (213, "Desfitasari", "00000018", "Desfitasari, A.Md.Keb"),
            (214, "Kornelia Handertika", "00000181", "Kornelia Handertika, S.Tr.Keb"),
            (215, "Faoziah Pebriana Sari", "00000206", "Faoziah Pebriana Sari, S.S.T"),
            (216, "Ni Ketut Sukareni", "00000218", "Ni Ketut Sukareni, S.Tr.Keb"),
            (217, "Nadia Gandari", "00000338", "Nadia Gandari, S.Tr.Keb"),
            (218, "Risma Silvianingsih", "00000208", "Risma Silvianingsih, S.Keb.Bd"),
            (219, "Veronika Maria Efendi", "00000278", "Veronika Maria Efendi, AMd. Farm"),
            (220, "Zulvia Puspita", "00000302", "Zulvia Puspita, SST"),
            (221, "Nur'Aisyah", "00000102", "Nur'Aisyah, S.Tr.Keb"),
            (222, "Eva Mahardika Apriyulan", "00000065", "Eva Mahardika Apriyulan, S.S.T"),
            (223, "Intan Juwita Rahmi", "00000331", "Intan Juwita Rahmi, S.Tr.Keb"),
            (224, "Elsa Fridayanti", "00000085", "Elsa Fridayanti, S.Tr.Keb"),
            (226, "Listiani", "00000116", "Ns. Listiani, S.Kep."),
            (227, "Nanang Purwanto", "00000075", "Ns. Nanang Purwanto, S.Kep."),
            (228, "Alfian Suganda", "00000306", "Ns. Alfian Suganda, S.Kep."),
            (229, "Sahidatullah", "00000068", "Sahidatullah,A.Md.RMIK"),
            (230, "Yayan Mulyawan", "00000230", "Yayan Mulyawan, S.Tr.Kes.(Rad)"),
            (232, "Firman Gangga Putra", "00000265", "Firman Gangga Putra A.Md.Rad."),
            (234, "Cahyo Nugroho Raharjo", "00000335", "Cahyo Nugroho Raharjo, S.Kom"),
            (235, "Reni Hindrawati", "00000050", "Reni Hindrawati, S.Tr.Keb."),
            (236, "Baiq Mita Sri Rahmani", "00000197", "Baiq Mita Sri Rahmani, A.Md. Kes."),
            (238, "Baiq Anggun Aprilia Cahyani Putri", "00000173", "Baiq Anggun Aprilia Cahyani Putri, A.Md.Par."),
            (239, "Radi Taufik", "00000059", "Radi Taufik, S.E"),
            (241, "Intan Rizkiati Ahrar", "00000081", "Ns. Intan Rizkiati Ahrar, S.Kep."),
            (242, "Musleh", "00000224", "Musleh, SH"),
            (247, "Ni Kadek Andriani", "00000063", "Ni Kadek Andriani, A.Md.Kes"),
            (253, "Pandri", "00000120", "Ns. Pandri, S.Kep"),
            (254, "Eka Wahyuni", "00000087", "Eka Wahyuni, A.Md.Kep"),
            (255, "Sri Utami", "00000011", "SRI UTAMI, A.Md.Keb."),
            (256, "Mulyadin", "00000326", "Mulyadin, A.MKg"),
            (261, "Lalu Wira Agus Suparman", "00000094", "Lalu Wira Agus Suparman, SE"),
            (262, "Risma Fitriananingrum", "00000277", "Risma Fitriananingrum"),
            (264, "Khairiyatul Aulia", "00000354", "Ns. Khairiyatul Aulia, S.Kep.,M.Kep."),
            (265, "Vikhabie Yolanda Muslim", "00000176", "Vikhabie Yolanda Muslim, S.Tr.Keb"),
            (267, "Mislan Sukmahardi", "00000205", "Ns. Mislan Sukmahardi, S.Kep."),
            (269, "Lalu Supriyadi", "00000275", "Ns. Lalu Supriyadi, S.Kep."),
            (270, "Baiq Yonik Suci Ramdamayanti", "00000158", "Baiq Yonik Suci Ramdamayanti, A.Md.Gz."),
            (271, "Septian Widiya Murti", "00000091", "Septian Widiya Murti, AMd. Farm"),
            (272, "Yuliana", "00000066", "Ns. Yuliana, S.Kep."),
            (275, "Intan Bhayangkari", "00000109", "Intan Bhayangkari, S.Tr.Keb"),
            (281, "Andreas Budi Setiawan", "00000232", "Andreas Budi Setiawan, A.Md.Rad"),
            (282, "Gunawan Khairul Anam", "00000114", "Gunawan Khairul Anam, S.Tr. Rad"),
            (284, "Rohani", "00000071", "Rohani"),
            (285, "Reditho Filan", "00000307", "Reditho Filan Akbar, S.Tr.Kes."),
            (286, "Elma Yulia Putri", "00000213", "Elma Yulia Putri Ananda, S.Mat."),
            (287, "Siti Aisah", "00000012", "Siti Aisah, S.PdI.,MM"),
            (288, "Suhandi Yusuf", "00000023", "Suhandi Yusuf"),
            (289, "Maslahhatul Wardani", "00000196", "Maslahhatul Wardani, S.K.M"),
            (290, "Suparman", "00000187", "Ns. Suparman, S. Kep."),
            (291, "Lalu Supardi", "00000040", "Lalu Supardi"),
            (293, "Siti Shofiyah", "00000112", "Ns. Siti Shofiyah S.Kep."),
            (295, "L. Lazuardi Sukmana", "00000048", "L. Lazuardi Sukmana"),
            (296, "Khairul Fahmi", "00000245", "Khairul Fahmi"),
            (297, "Muh. Busyairi Putra", "00000033", "Ns. Muh. Busyairi Mandala Putra, S.Kep."),
            (298, "Hazmi Azizaturrohmi", "00000239", "dr. Hazmi Azizaturohmi"),
            (299, "Fathatul Jannah", "00000046", "Fathatul Jannah, A.Md.Kep."),
            (300, "Nurdiansyah", "00000227", "Nurdiansah"),
            (301, "Sudiatun", "00000098", "Sudiatun, AMG"),
            (302, "Ihsan Nur Salam", "00000300", "Ihsan Nursalam"),
            (303, "Siti Khatikah", "00000236", "Siti Khatikah"),
            (304, "Lale Nurrahmawati", "00000211", "Lale Nurrahmawati, S.Pd"),
            (305, "lina fraftimuliani", "00000064", "Ns. Lina frafti muliani, S. Kep."),
            (306, "AKHMAD Satria Mardegune", "00000092", "Akhmad Satrie Mardegune"),
            (307, "Dian Rahayu", "00000169", "Dian Rahayu"),
            (309, "Wati Mila Rosa", "00000193", "Wati Mila Rosa"),
            (310, "Eka Pratiwi", "00000170", "Eka Pratiwi"),
            (311, "Agus Suhirjan", "00000019", "Ns. Agus Suhirjan, S.Kep."),
            (314, "Agus Supriadi", "00000041", "Agus Supriadi"),
            (316, "Baiq Saka Muara Ardian", "00000350", "dr. Baiq Saka Muara Ardian"),
            (317, "Herman Jaelani", "00000047", "Herman Jaelani"),
            (319, "Baiq Erma Asmayati", "00000233", "apt. Baiq Erma Asmayati, S.Farm"),
            (320, "Hiru Sopian Hidayat", "00000088", "Hiru Sopian Hidayat, AMTE"),
            (324, "Budhi Suhartini", "00000024", "Budhi Hartini"),
            (326, "SUHERMAN", "00000124", "Suherman"),
            (327, "MARSANDI", "00000039", "Marsandi"),
            (329, "Yayan Karyadi", "00000242", "M. Yayan Karyadi"),
            (330, "Dede Martha Adi Toma", "00000341", "dr. Dede Martha Adi Toma, S.Ked."),
            (336, "Lalu Supardi", "00000260", "Lalu Supardi"),
            (337, "Clarence Marks Alief", "00000329", "dr. Clarence Marks Alief"),
            (338, "kamarudin", "00000151", "Kamarudin"),
            (339, "Endang Triwindu Sari", "00000308", "Endang Triwindu Sari, S.Tr.Kes"),
            (342, "Tjahyadi", "00000295", "dr. Tjahyadi"),
            (344, "Eva Pradila", "00000238", "Eva Pradila, S.KM"),
            (349, "Baiq Adelina", "00000175", "Baiq Adelina Mandayani, S.Tr.Gz"),
            (350, "Ditha Maharani", "00000174", "Ditha Maharani S.Tr.Kes"),
            (351, "Muhammad Samsul Hadi", "00000015", "Muhammad Samsul Hadi, S. Ds."),
            (352, "Nida'an Khofia", "00000156", "Nida'an Khofia, A.Md.RMIK"),
            (353, "Sharah Dini Yundari", "00000200", "Sharah Dini Yundari, S.Kom"),
            (354, "Febri Syafira", "00000323", "Febri Syafira Adelia Rahma Tyastuti, S.Tr.Kes.(Rad)"),
            (355, "Septia Purnama Dewi", "00000044", "Septia Purnama Dewi"),
            (356, "Minah Ayuningsih", "00000171", "Minah Ayuningsih"),
            (357, "Melani Komala Dewi", "00000045", "Melani Komala Dewi"),
            (358, "Ratmi Karti Nika", "00000194", "Ratmi Kartinika"),
            (360, "Rusmita Nurmala", "00000058", "Rusmita Nurmala Dewi"),
            (361, "lalu geger sahid mardan", "00000043", "Lalu Geger Sahid Mardan"),
            (365, "Syahidatul Kautsar", "00000291", "dr. Syahidatul Kautsar"),
            (366, "arif rahman", "00000013", "ARIF RAHMAN, S.H"),
            (367, "Indah Jasmita Anwar", "00000202", "Indah Jasmita Anwar, S.Si."),
            (368, "Febriyani Nurmayanti", "00000210", "Febriyani Nurmayanti, SE"),
            (369, "radianto", "00000229", "Radianto"),
            (370, "Tomy Hardian Pratama", "00000167", "Tomy Hardian Pratama"),
            (371, "Supriani Ani", "00000168", "Baiq Supriani"),
            (372, "Fakhruli Egis Alfian", "00000257", "Fakhruli Egis Alfian, S.M."),
        ]

        # =============================================
        # DEDIKASI: hindari duplikat berdasarkan simadu_id & mesin_id
        # =============================================
        seen_simadu_ids = set()
        seen_mesin_ids = set()
        deduped_data = []

        for simadu_id, nama_simadu, mesin_id, nama_absensi in mapping_data:
            if simadu_id in seen_simadu_ids:
                self.stdout.write(
                    self.style.WARNING(
                        f"  DILEWATI (dup simadu_id={simadu_id}): "
                        f"{nama_simadu} -> mesin_id={mesin_id}"
                    )
                )
                continue

            if mesin_id in seen_mesin_ids:
                self.stdout.write(
                    self.style.WARNING(
                        f"  DILEWATI (dup mesin_id={mesin_id}): "
                        f"{nama_simadu} -> {nama_absensi}"
                    )
                )
                continue

            seen_simadu_ids.add(simadu_id)
            seen_mesin_ids.add(mesin_id)
            deduped_data.append((simadu_id, nama_simadu, mesin_id, nama_absensi))

        # =============================================
        # PROSES INSERT
        # =============================================
        success_count = 0
        skip_user_not_found = 0
        skip_duplicate_mesin = 0
        skip_already_mapped = 0
        error_count = 0

        if dry_run:
            self.stdout.write(self.style.WARNING("\n===== DRY RUN MODE (tidak ada data yang tersimpan) =====\n"))

        self.stdout.write(f"Total data setelah deduplikasi: {len(deduped_data)}")
        self.stdout.write("=" * 80)

        with transaction.atomic():
            for simadu_id, nama_simadu, mesin_id, nama_absensi in deduped_data:

                try:
                    pegawai = Users.objects.get(pk=simadu_id)
                except Users.DoesNotExist:
                    skip_user_not_found += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ User NOT FOUND (id={simadu_id}): {nama_simadu}"
                        )
                    )
                    continue

                existing_by_mesin = MappingMesinAbsensi.objects.filter(
                    mesin_id=mesin_id
                ).exclude(pegawai=pegawai).first()

                if existing_by_mesin:
                    skip_duplicate_mesin += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ mesin_id={mesin_id} sudah dipakai oleh "
                            f"{existing_by_mesin.pegawai.full_name}, "
                            f"melewatkan: {nama_simadu}"
                        )
                    )
                    continue

                existing_mapping = MappingMesinAbsensi.objects.filter(
                    pegawai=pegawai
                ).first()

                if existing_mapping:
                    if overwrite:
                        if not dry_run:
                            existing_mapping.mesin_id = mesin_id
                            existing_mapping.save(update_fields=['mesin_id'])
                        success_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ↻ OVERWRITE: {pegawai.full_name} "
                                f"({existing_mapping.mesin_id} -> {mesin_id})"
                            )
                        )
                    else:
                        skip_already_mapped += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠ {pegawai.full_name} sudah punya mapping "
                                f"(mesin_id={existing_mapping.mesin_id}), dilewati"
                            )
                        )
                    continue

                try:
                    if not dry_run:
                        MappingMesinAbsensi.objects.create(
                            mesin_id=mesin_id,
                            pegawai=pegawai,
                        )
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ {pegawai.full_name} (id={simadu_id}) "
                            f"-> mesin_id={mesin_id}"
                        )
                    )
                except IntegrityError as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ IntegrityError: {pegawai.full_name} "
                            f"-> mesin_id={mesin_id} | {e}"
                        )
                    )
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ Error: {pegawai.full_name} "
                            f"-> mesin_id={mesin_id} | {e}"
                        )
                    )

            if dry_run:
                transaction.set_rollback(True)

        # =============================================
        # SUMMARY
        # =============================================
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.bold("RINGKASAN:"))
        self.stdout.write(f"  Total data mapping        : {len(mapping_data)}")
        self.stdout.write(f"  Setelah deduplikasi       : {len(deduped_data)}")
        self.stdout.write(f"  Berhasil disimpan         : {self.style.SUCCESS(str(success_count))}")
        self.stdout.write(f"  User tidak ditemukan      : {self.style.ERROR(str(skip_user_not_found))}")
        self.stdout.write(f"  mesin_id sudah dipakai    : {self.style.WARNING(str(skip_duplicate_mesin))}")
        self.stdout.write(f"  Sudah punya mapping       : {self.style.WARNING(str(skip_already_mapped))}")
        self.stdout.write(f"  Error lainnya             : {self.style.ERROR(str(error_count))}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n  Mode DRY RUN — tidak ada data yang tersimpan ke database."
                )
            )