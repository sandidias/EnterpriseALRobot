![Chizuru](https://telegra.ph/file/42bd3883928cf71216489.png)
# Mizuhara Chizuru bot

![Maintenance](https://img.shields.io/badge/Maintained%3F-Yes-green) [![Join Support!](https://img.shields.io/badge/Support%20Chat-EagleUnion-red)](https://t.me/YorktownEagleUnion) [![Codacy Badge](https://app.codacy.com/project/badge/Grade/cfb691a93a064d9ea753ef2b5fccf797)](https://www.codacy.com/manual/Dank-del/EnterpriseALRobot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Dank-del/EnterpriseALRobot&amp;utm_campaign=Badge_Grade)

Bot Python telegram modular yang berjalan di python3 dengan database sqlalchemy.
Konsep diambil dari [Saitama Robot](https://github.com/AnimeKaizoku/SaitamaRobot)

Awalnya marie fork - Chizuru telah berkembang lebih jauh dan dibangun agar lebih berguna untuk Obrolan Anime.

Dapat ditemukan di telegram sebagai [Mizuhara Chizuru](https://t.me/ChizuruChanBot). 

 ## Tombol Deploynya ada disini sayang :) 
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## Menyiapkan bot (Baca ini sebelum mencoba menggunakan!):


# Bagaimana cara menggunakannya
<details>
  <summary>Klik untuk memperluas!! </summary>
  
 
 
 Catatan: Set instruksi ini hanya salinan tempel dari marie, perhatikan bahwa bertujuan untuk menangani dukungan untuk @ChizuruChanBot dan sekarang bagaimana mengatur garpu Anda sendiri, jika Anda menemukan ini agak membingungkan/sulit untuk dipahami maka kami sarankan Anda bertanya kepada dev, mohon hindari bertanya bagaimana mengatur instance bot di obrolan dukungan, ini bertujuan untuk membantu contoh bot kami sendiri.
  
  ## Menyiapkan bot (Baca ini sebelum mencoba menggunakan!):
Harap pastikan untuk menggunakan python3.6, karena saya tidak dapat menjamin semuanya akan berfungsi seperti yang diharapkan pada versi python yang lebih lama!
Ini karena penguraian penurunan harga dilakukan dengan melakukan iterasi melalui dict, yang diurutkan secara default di 3.6.

  ### Konfigurasi

Ada dua cara yang mungkin untuk mengonfigurasi bot Anda: file config.py, atau variabel ENV.

Versi yang lebih disukai adalah menggunakan file `config.py`, karena akan lebih mudah untuk melihat semua pengaturan Anda dikelompokkan bersama.
File ini harus ditempatkan di folder `tg_bot` Anda, di samping file` __main __.py`.
Di sinilah token bot Anda akan dimuat, serta URI database Anda (jika Anda menggunakan database), dan sebagian besar
pengaturan Anda yang lain.

Direkomendasikan untuk mengimpor sample_config dan memperluas kelas Config, karena ini akan memastikan konfigurasi Anda berisi semuanya
default diatur di sample_config, sehingga membuatnya lebih mudah untuk ditingkatkan.

Contoh file `config.py` bisa jadi:
```
from tg_bot.sample_config import Config


class Development(Config):
    OWNER_ID = 254318997  # your telegram ID
    OWNER_USERNAME = "SonOfLars"  # your telegram username
    API_KEY = "your bot api key"  # your api key, as provided by the @botfather
    SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost:5432/database'  # sample db credentials
    MESSAGE_DUMP = '-1234567890' # some group chat that your bot is a member of
    USE_MESSAGE_DUMP = True
    SUDO_USERS = [18673980, 83489514]  # List of id's for users which have sudo access to the bot.
    LOAD = []
    NO_LOAD = ['translation']
```

ika Anda tidak dapat memiliki file config.py (EG di heroku), Anda juga dapat menggunakan variabel lingkungan.
Variabel env berikut ini didukung:
 - `ENV`: Menyetel ini ke ANYTHING akan mengaktifkan variabel env

 - `TOKEN`: Token bot Anda, sebagai string
 - `OWNER_ID`: Integer terdiri dari ID pemilik Anda
 - `OWNER_USERNAME`: Nama pengguna Anda

 - `DATABASE_URL`: URL database Anda
 - `MESSAGE_DUMP`: opsional: obrolan tempat Anda menyimpan pesan balasan yang disimpan, untuk menghentikan orang menghapus pesan lama mereka
 - `LOAD`: Daftar modul yang dipisahkan spasi yang ingin Anda muat
 - `NO_LOAD`: Daftar modul yang dipisahkan spasi yang TIDAK ingin Anda muat
 - `WEBHOOK`: Menyetel ini ke ANYTHING akan mengaktifkan webhook saat dalam mode env
 pesan
 - `URL`: URL yang harus dihubungi webhook Anda (hanya diperlukan untuk mode webhook)

 - `SUDO_USERS`: Daftar user_ids yang dipisahkan spasi yang harus dianggap sebagai pengguna sudo
 - `SUPPORT_USERS`: Daftar user_id yang dipisahkan spasi yang seharusnya dianggap mendukung pengguna (dapat gban/ungban,
 tidak ada lagi)
 - `WHITELIST_USERS`: Daftar user_id yang dipisahkan spasi, yang harus dipertimbangkan dalam daftar putih - tidak dapat dicekal.
 - `DONATION_LINK`: Opsional: tautan tempat Anda ingin menerima donasi.
 - `CERT_PATH`: Jalur ke sertifikat webhook Anda
 - `PORT`: Porta yang akan digunakan untuk webhook Anda
 - `DEL_CMDS`: Apakah akan menghapus perintah dari pengguna yang tidak memiliki hak untuk menggunakan perintah itu
 - `STRICT_GBAN`: Berlakukan gban di seluruh grup baru maupun grup lama. Ketika seorang pengguna gbanned berbicara, dia akan di banned.
 - `WORKERS`: Jumlah utas yang akan digunakan. 8 adalah jumlah yang disarankan (dan default), tetapi pengalaman Anda mungkin berbeda.
 __Note__ bahwa menjadi gila dengan lebih banyak utas tidak akan serta merta mempercepat bot Anda, mengingat sejumlah besar data sql
 mengakses, dan cara kerja panggilan asinkron python.
 - `BAN_STICKER`: Stiker mana yang digunakan saat melarang orang.
 - `ALLOW_EXCL`: Apakah akan mengizinkan penggunaan tanda seru! untuk perintah serta /.
 
  ### Dependensi Python

Instal dependensi python yang diperlukan dengan pindah ke direktori proyek dan menjalankan:

`pip3 install -r requirement.txt`.

Ini akan menginstal semua paket python yang diperlukan.

  ### Database

Jika Anda ingin menggunakan modul yang bergantung pada database (misalnya: kunci, catatan, info pengguna, pengguna, filter, selamat datang),
Anda harus memiliki database yang terpasang di sistem Anda. Saya menggunakan postgres, jadi saya sarankan menggunakannya untuk kompatibilitas optimal.

Dalam kasus postgres, inilah cara Anda mengatur database pada sistem debian/ubuntu. Distribusi lain mungkin berbeda.

- instal postgresql:

`sudo apt-get update && sudo apt-get install postgresql`

- ubah ke pengguna postgres:

`sudo su - postgres`

- buat pengguna database baru (ubah YOUR_USER dengan benar):

`createuser -P -s -e YOUR_USER`

Ini akan diikuti oleh Anda perlu memasukkan kata sandi Anda.

- buat tabel database baru:

`Createdb -O YOUR_USER YOUR_DB_NAME`

Ubah YOUR_USER dan YOUR_DB_NAME dengan tepat.

- akhirnya:

`psql YOUR_DB_NAME -h YOUR_HOST YOUR_USER`

Ini akan memungkinkan Anda untuk terhubung ke database Anda melalui terminal Anda.
Secara default, YOUR_HOST harus 0.0.0.0:5432.

Anda sekarang harus dapat membangun URI database Anda. Ini akan menjadi:

`sqldbtype://username:pw@hostname:port/db_name`

Ganti sqldbtype dengan db mana saja yang Anda gunakan (mis. Postgres, mysql, sqllite, dll)
ulangi untuk nama pengguna, kata sandi, nama host (localhost?), port (5432?), dan nama db Anda.

  ## Modul
   ### Menyetel urutan pemuatan.

Urutan pemuatan modul dapat diubah melalui pengaturan konfigurasi `LOAD` dan` NO_LOAD`.
Keduanya harus mewakili daftar.

Jika `LOAD` adalah daftar kosong, semua modul dalam`modules/`akan dipilih untuk dimuat secara default.

Jika `NO_LOAD` tidak ada, atau merupakan daftar kosong, semua modul yang dipilih untuk dimuat akan dimuat.

Jika modul ada di `LOAD` dan` NO_LOAD`, modul tidak akan dimuat - `NO_LOAD` diprioritaskan.

   ### Membuat modul Anda sendiri.

Membuat modul telah disederhanakan semaksimal mungkin - tetapi jangan ragu untuk menyarankan penyederhanaan lebih lanjut.

Semua yang diperlukan adalah file.py Anda berada di folder modul.

Untuk menambahkan perintah, pastikan untuk mengimpor petugas operator melalui

`dari tg_bot import dispatcher`.

Anda kemudian dapat menambahkan perintah menggunakan biasa

`dispatcher.add_handler ()`.

Menetapkan variabel `__help__` ke string yang menjelaskan ketersediaan modul ini
perintah akan memungkinkan bot memuatnya dan menambahkan dokumentasinya
modul Anda ke perintah `/help`. Menyetel variabel `__mod_name__` juga akan memungkinkan Anda menggunakan pengguna yang lebih baik
nama ramah untuk sebuah modul.

Fungsi `__migrate__ ()` digunakan untuk memigrasi obrolan - saat obrolan ditingkatkan ke supergrup, ID berubah, jadi
itu perlu untuk memindahkannya di db.

Fungsi `__stats__ ()` adalah untuk mengambil statistik modul, misalnya jumlah pengguna, jumlah obrolan. Ini diakses
melalui perintah `/stats`, yang hanya tersedia untuk pemilik bot.

## Memulai bot.

Setelah Anda mengatur database dan konfigurasi Anda selesai, cukup jalankan file bat (jika di windows) atau jalankan (linux):

`python3 -m tg_bot`

Anda dapat menggunakan [nssm](https://nssm.cc/usage) untuk menginstal bot sebagai layanan di windows dan menyetelnya untuk memulai ulang di / gitpull
Pastikan untuk mengedit start dan restart kelelawar sesuai kebutuhan Anda.
Catatan: restart bat mengharuskan kontrol akun Pengguna dinonaktifkan.

## Kredit
Bot ini didasarkan pada karya asli yang dilakukan oleh [PaulSonOfLars]https://github.com/PaulSonOfLars)
Repo ini baru saja diperbarui agar sesuai dengan komunitas yang berpusat pada Anime. Semua kredit asli diberikan kepada Paul dan dedikasinya, Tanpa usahanya, garpu ini tidak akan mungkin terjadi!

Juga, kehilangan kredit yang tepat untuk pengguna daftar hitam yang diambil dari TheRealPhoenixBot (akan menambahkannya nanti, catatan ini mengatakan kecuali jika selesai)

Kepengarangan/kredit lainnya dapat dilihat melalui komit.
