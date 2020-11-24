import html
import re, os
import time
from typing import List

import requests
from telegram import Bot, Update, MessageEntity, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import mention_html
from subprocess import Popen, PIPE

from tg_bot import (
    dispatcher,
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    DEV_USERS,
    SARDEGNA_USERS,
    WHITELIST_USERS,
    INFOPIC,
    sw
)
from tg_bot.__main__ import STATS, USER_INFO, TOKEN
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin, sudo_plus
from tg_bot.modules.helper_funcs.extraction import extract_user
import tg_bot.modules.sql.users_sql as sql

MARKDOWN_HELP = f"""
Markdown adalah alat pemformatan yang sangat kuat yang didukung oleh telegram. {dispatcher.bot.first_name} memiliki beberapa peningkatan, untuk memastikannya \
pesan yang disimpan diurai dengan benar, dan memungkinkan Anda membuat tombol.

- <code>_miring_</code>: membungkus teks dengan '_' akan menghasilkan teks miring
- <code>*tebal*</code>: membungkus teks dengan '*' akan menghasilkan teks tebal
- <code>`kode`</code>: membungkus teks dengan '`' akan menghasilkan teks monospace, juga dikenal sebagai 'kode'
- <code>[teks](URL)</code>: ini akan membuat tautan - pesan hanya akan menampilkan <code>teks</code>, \
dan mengetuknya akan membuka halaman di <code>URL</code>.
Contoh: <code>[test](contoh.com)</code>

- <code>[TombolTeks](buttonurl:URL)</code>: ini adalah perangkat tambahan khusus yang memungkinkan pengguna memiliki \
tombol di markdown mereka. <code>TombolTeks</code> akan menjadi apa yang ditampilkan pada tombol, dan <code>URL</code> \
akan menjadi url yang dibuka.
Contoh: <code>[Ini sebuah tombol](buttonurl:contoh.com)</code>

Jika Anda ingin beberapa tombol pada baris yang sama, gunakan :same, seperti :
<code>[satu](buttonurl:contoh.com)
[dua](buttonurl:google.com:same)</code>
Ini akan membuat dua tombol pada satu baris, bukan satu tombol per baris.

Perlu diingat bahwa pesan Anda <b>HARUS</b> berisi beberapa teks selain hanya sebuah tombol!
"""


@run_async
def get_id(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    chat = update.effective_chat
    msg = update.effective_message
    user_id = extract_user(msg, args)

    if user_id:

        if msg.reply_to_message and msg.reply_to_message.forward_from:

            user1 = message.reply_to_message.from_user
            user2 = message.reply_to_message.forward_from

            msg.reply_text(
                f"Pengirim asli, {html.escape(user2.first_name)},"
                f"memiliki ID <code>{user2.id}</code>.\n"
                f"Penerusan, {html.escape(user1.first_name)},"
                f" memiliki ID <code>{user1.id}</code>.",
                parse_mode=ParseMode.HTML,
            )

        else:

            user = bot.get_chat(user_id)
            msg.reply_text(
                f"{html.escape(user.first_name)}'s id is <code>{user.id}</code>.",
                parse_mode=ParseMode.HTML,
            )

    else:

        if chat.type == "private":
            msg.reply_text(
                f"ID Anda adalah <code>{chat.id}</code>.", parse_mode=ParseMode.HTML
            )

        else:
            msg.reply_text(
                f"Id grup ini adalah <code>{chat.id}</code>.", parse_mode=ParseMode.HTML
            )


@run_async
def gifid(bot: Bot, update: Update):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.animation:
        update.effective_message.reply_text(
            f"Gif ID:\n<code>{msg.reply_to_message.animation.file_id}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        update.effective_message.reply_text("Silakan balas gif untuk mendapatkan ID-nya.")


@run_async
def info(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    chat = update.effective_chat
    user_id = extract_user(update.effective_message, args)

    if user_id:
        user = bot.get_chat(user_id)

    elif not message.reply_to_message and not args:
        user = message.from_user

    elif not message.reply_to_message and (
        not args
        or (
            len(args) >= 1
            and not args[0].startswith("@")
            and not args[0].isdigit()
            and not message.parse_entities([MessageEntity.TEXT_MENTION])
        )
    ):
        message.reply_text("Saya tidak dapat mengekstrak pengguna dari ini.")
        return

    else:
        return

    text = (
        f"<b>Karakteristik:</b>\n"
        f"ID: <code>{user.id}</code>\n"
        f"Nama depan: {html.escape(user.first_name)}"
    )

    if user.last_name:
        text += f"\nNama Belakang: {html.escape(user.last_name)}"

    if user.username:
        text += f"\nNama pengguna: @{html.escape(user.username)}"

    text += f"\nTautan pengguna permanen: {mention_html(user.id, 'link')}"
    
    try:
        spamwtc = sw.get_ban(int(user.id))
        if spamwtc:
            text += "\n\n<b>Orang ini dilarang di Spamwatch!</b>"
            text += f"\nAlasan: <pre>{spamwtc.reason}</pre>"
            text += "\nAppeal at @SpamWatchSupport"
        else:
            pass
    except:
        pass # don't crash if api is down somehow...
    
    Nation_level_present = False

    num_chats = sql.get_user_num_chats(user.id)
    text += f"\nJumlah obrolan: <code>{num_chats}</code>"

    try:
        user_member = chat.get_member(user.id)
        if user_member.status == "administrator":
            result = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={chat.id}&user_id={user.id}"
            )
            result = result.json()["result"]
            if "custom_title" in result.keys():
                custom_title = result["custom_title"]
                text += f"\nPengguna ini memiliki title <b>{custom_title}</b> disini."
    except BadRequest:
        pass

    if user.id == OWNER_ID:
            text += f'\nOrang ini adalah pemilik saya'
            Nation_level_present = True
    elif user.id in DEV_USERS:
            text += f'\nThis Person is a part of Eagle Union'
            Nation_level_present = True
    elif user.id in SUDO_USERS:
            text += f'\nThe Nation level of this person is Royal'
            Nation_level_present = True
    elif user.id in SUPPORT_USERS:
            text += f'\nThe Nation level of this person is Sakura'
            Nation_level_present = True
    elif user.id in SARDEGNA_USERS:
            text += f'\nThe Nation level of this person is Sardegna'
            Nation_level_present = True
    elif user.id in WHITELIST_USERS:
            text += f'\nThe Nation level of this person is Neptunia'
            Nation_level_present = True
            
    if Nation_level_present:
        text += ' [<a href="https://t.me/{}?start=nations">?</a>]'.format(
            bot.username)

    text += "\n"
    for mod in USER_INFO:
        if mod.__mod_name__ == "Users":
            continue

        try:
            mod_info = mod.__user_info__(user.id)
        except TypeError:
            mod_info = mod.__user_info__(user.id, chat.id)
        if mod_info:
            text += "\n" + mod_info
            
    if INFOPIC:
        try:
            profile = bot.get_user_profile_photos(user.id).photos[0][-1]
            _file = bot.get_file(profile["file_id"])
            _file.download(f"{user.id}.png")

            message.reply_document(
                document=open(f"{user.id}.png", "rb"),
                caption=(text),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)

            os.remove(f"{user.id}.png")
        # Incase user don't have profile pic, send normal text
        except IndexError:
            message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    else:
        message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)




@run_async
@user_admin
def echo(bot: Bot, update: Update):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message

    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)

    message.delete()
    
def shell(command):
    process = Popen(command, stdout=PIPE, shell=True, stderr=PIPE)
    stdout, stderr = process.communicate()
    return (stdout, stderr)

@sudo_plus
def ram(bot: Bot, update: Update):
    cmd = "ps -o pid"
    output = shell(cmd)[0].decode()
    processes = output.splitlines()
    mem = 0
    for p in processes[1:]:
        mem += int(
            float(
                shell(
                    "ps u -p {} | awk ".format(p)
                    + "'{sum=sum+$6}; END {print sum/1024}'"
                )[0]
                .decode()
                .rstrip()
                .replace("'", "")
            )
        )
    update.message.reply_text(
        f"RAM usage = <code>{mem} MiB</code>", parse_mode=ParseMode.HTML
    )



@run_async
def markdown_help(bot: Bot, update: Update):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text(
        "Coba teruskan pesan berikut kepada saya, dan Anda akan lihat!"
    )
    update.effective_message.reply_text(
        "/save tes Ini adalah markdown test. _italics_, *bold*, `code`, "
        "[URL](example.com) [button](buttonurl:github.com) "
        "[TombolTeks2](TombolUrl://google.com:same)"
    )


@run_async
@sudo_plus
def stats(bot: Bot, update: Update):
    stats = "Statistik saat ini:\n" + "\n".join([mod.__stats__() for mod in STATS])
    result = re.sub(r"(\d+)", r"<code>\1</code>", stats)
    update.effective_message.reply_text(result, parse_mode=ParseMode.HTML)
    
    
@run_async
def ping(bot: Bot, update: Update):
    msg = update.effective_message
    start_time = time.time()
    message = msg.reply_text("Pinging...")
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 3)
    message.edit_text(
        "*Pong!!!*\n`{}ms`".format(ping_time), parse_mode=ParseMode.MARKDOWN
    )


__help__ = """
 - /id: dapatkan id grup saat ini. Jika digunakan dengan membalas pesan, dapatkan id pengguna itu.
 - /gifid: balas gif ke saya untuk memberi tahu Anda ID filenya.
 - /info: mendapatkan informasi tentang pengguna
 - /markdownhelp: ringkasan singkat tentang bagaimana penurunan harga bekerja di telegram - hanya dapat dipanggil dalam obrolan pribadi.
 - /reverse: Melakukan pencarian gambar terbalik dari media yang dibalas.
 - /ud <word>: Ketik kata atau ekspresi yang ingin Anda gunakan pencarian.
 - /urban <word>: Sama dengan /ud
 - /paste - Lakukan tempel di `neko.bin`
 - /react: Bereaksi dengan reaksi acak
 - /weebify <text>: mengembalikan teks weebified
 - /lyrics <lagu>: mengembalikan lirik lagu itu.
 - /tr (kode bahasa) sebagai balasan untuk pesan panjang.
 - /time <query> : Memberikan informasi tentang zona waktu.
 - /cash : konverter mata uang
   contoh sintaks: /cash 1 USD IDR
 - /whois : dapatkan info tentang pengguna (uses @Pyrogram methods)
 - /spbinfo : dapatkan info tentang pengguna dari @Intellivoid's SpamProtection API
───────────────────────────────
*Last.FM*
Bagikan apa yang Anda dengarkan dengan bantuan modul ini!
*Perintah yang tersedia:*
 - /setuser <username>: setel nama pengguna last.fm Anda.
 - /clearuser: menghapus nama pengguna last.fm Anda dari database bot.
 - /lastfm: mengembalikan apa yang Anda cari di last.fm.
───────────────────────────────
*Matematika*
Memecahkan masalah matematika yang rumit menggunakan https://newton.now.sh
 - /math: Menyederhanakan `/simplify 2^2+2(2)`
 - /factor: Faktor `/factor x^2 + 2x`
 - /derive: Memperoleh `/derive x^2+2x`
 - /integrate: Mengintegrasikan `/integrate x^2+2x`
 - /zeroes: Temukan 0's `/zeroes x^2+2x`
 - /tangent: Temukan Tangent `/tangent 2lx^3`
 - /area: Area di Bawah Kurva `/area 2:4lx^3`
 - /cos: Cosine `/cos pi`
 - /sin: Sine `/sin 0`
 - /tan: Tangent `/tan 0`
 - /arccos: Inverse Cosine `/arccos 1`
 - /arcsin: Inverse Sine `/arcsin 0`
 - /arctan: Inverse Tangent `/arctan 0`
 - /abs: Absolute Value `/abs -1`
 - /log: Logarithm `/log 2l8`

__Ingat__: Untuk menemukan garis singgung suatu fungsi pada nilai x tertentu, kirim permintaan sebagai c|f(x) di mana c adalah nilai x yang diberikan dan f(x) adalah ekspresi fungsi, pemisahnya adalah batang vertikal '|' . Lihat tabel di atas untuk contoh permintaan.
Untuk mencari luas di bawah suatu fungsi, kirim permintaan sebagai c:d|f(x) di mana c adalah nilai x awal, d adalah nilai akhir x, dan f(x) adalah fungsi di mana Anda ingin kurva antara dua nilai x.
Untuk menghitung pecahan, masukkan ekspresi sebagai penyebut pembilang (di atas). Misalnya, untuk memproses 2/4 Anda harus mengirimkan ekspresi Anda sebagai 2 (di atas) 4. Ekspresi hasilnya akan dalam notasi matematika standar (1/2, 3/4).

"""

ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)
GIFID_HANDLER = DisableAbleCommandHandler("gifid", gifid)
INFO_HANDLER = DisableAbleCommandHandler("info", info, pass_args=True)
ECHO_HANDLER = DisableAbleCommandHandler("echo", echo, filters=Filters.group)
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)
STATS_HANDLER = CommandHandler("stats", stats)
PING_HANDLER = DisableAbleCommandHandler("ping", ping)
RAM_HANDLER = CommandHandler("ram", ram,)

dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(GIFID_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
dispatcher.add_handler(PING_HANDLER)
dispatcher.add_handler(RAM_HANDLER)

__mod_name__ = "Misc"
__command_list__ = ["id", "info", "echo", "ping"]
__handlers__ = [
    ID_HANDLER,
    GIFID_HANDLER,
    INFO_HANDLER,
    ECHO_HANDLER,
    MD_HELP_HANDLER,
    STATS_HANDLER,
    PING_HANDLER,
]
