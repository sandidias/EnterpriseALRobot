import html
from io import BytesIO
from typing import Optional, List
import random
import uuid
import re
import json
import time
import csv
import os
from time import sleep

from future.utils import string_types
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram import (
    ParseMode,
    Update,
    Bot,
    Chat,
    User,
    MessageEntity,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    run_async,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from tg_bot import (
    dispatcher,
    OWNER_ID,
    SUDO_USERS,
    WHITELIST_USERS,
    SARDEGNA_USERS,
    GBAN_LOGS,
    LOGGER,
)
from tg_bot.modules.helper_funcs.handlers import CMD_STARTERS
from tg_bot.modules.helper_funcs.misc import is_module_loaded, send_to_list
from tg_bot.modules.helper_funcs.chat_status import is_user_admin
from tg_bot.modules.helper_funcs.extraction import (
    extract_user,
    extract_unt_fedban,
    extract_user_fban,
)
from tg_bot.modules.helper_funcs.string_handling import markdown_parser
from tg_bot.modules.disable import DisableAbleCommandHandler

import tg_bot.modules.sql.feds_sql as sql

from tg_bot.modules.connection import connected
from tg_bot.modules.helper_funcs.alternate import send_message

# Hello bot owner, I spended for feds many hours of my life, Please don't remove this if you still respect MrYacha and peaktogoo and AyraHikari too
# Federation by MrYacha 2018-2019
# Federation rework by Mizukito Akito 2019
# Federation update v2 by Ayra Hikari 2019
# Time spended on feds = 10h by #MrYacha
# Time spended on reworking on the whole feds = 22+ hours by @peaktogoo
# Time spended on updating version to v2 = 26+ hours by @AyraHikari
# Total spended for making this features is 68+ hours
# LOGGER.info("Original federation module by MrYacha, reworked by Mizukito Akito (@peaktogoo) on Telegram.")

FBAN_ERRORS = {
    "Pengguna adalah administrator obrolan",
    "Obrolan tidak ditemukan",
    "Tidak cukup hak untuk membatasi / tidak membatasi anggota obrolan",
    "User_not_participant",
    "Peer_id_invalid",
    "Obrolan berkelompok telah dinonaktifkan",
    "Perlu mengundang pengguna untuk menendang dari grup dasar",
    "Chat_admin_required",
    "Hanya pembuat grup dasar yang dapat menendang administrator grup",
    "Channel_private",
    "Tidak dalam obrolan",
    "Tidak punya hak untuk mengirim pesan",
}

UNFBAN_ERRORS = {
    "Pengguna adalah administrator obrolan",
    "Obrolan tidak ditemukan",
    "Tidak cukup hak untuk membatasi / tidak membatasi anggota obrolan",
    "User_not_participant",
    "Metode hanya tersedia untuk obrolan grup super dan saluran",
    "Tidak dalam obrolan",
    "Channel_private",
    "Chat_admin_required",
    "Tidak punya hak untuk mengirim pesan",
}


@run_async
def new_fed(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if chat.type != "private":
        update.effective_message.reply_text(
            "Federasi hanya dapat dibuat dengan mengirimi saya pesan secara pribadi."
        )
        return
    if len(message.text) == 1:
        send_message(
            update.effective_message, "Silakan tulis nama federasi!"
        )
        return
    fednam = message.text.split(None, 1)[1]
    if not fednam == "":
        fed_id = str(uuid.uuid4())
        fed_name = fednam
        LOGGER.info(fed_id)

        # Currently only for creator
        # if fednam == 'Team Nusantara Disciplinary Circle':
        # fed_id = "TeamNusantaraDevs"

        x = sql.new_fed(user.id, fed_name, fed_id)
        if not x:
            update.effective_message.reply_text(
                "Tidak bisa bersekutu!"
            )
            return

        update.effective_message.reply_text(
            "*Anda berhasil membuat federasi baru!*"
            "\nNama: `{}`"
            "\nID: `{}`"
            "\n\nGunakan perintah di bawah ini untuk bergabung dengan federasi:"
            "\n`/joinfed {}`".format(fed_name, fed_id, fed_id),
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            bot.send_message(
                GBAN_LOGS,
                "Federasi Baru: <b>{}</b>\nID: <pre>{}</pre>".format(fed_name, fed_id),
                parse_mode=ParseMode.HTML,
            )
        except:
            LOGGER.warning("Tidak dapat mengirim pesan ke GBAN_LOGS")
    else:
        update.effective_message.reply_text(
            "Harap tuliskan nama federasi"
        )


@run_async
def del_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type != "private":
        update.effective_message.reply_text(
            "Federasi hanya dapat dihapus dengan mengirimi saya pesan secara pribadi."
        )
        return
    if args:
        is_fed_id = args[0]
        getinfo = sql.get_fed_info(is_fed_id)
        if getinfo == False:
            update.effective_message.reply_text("Federasi ini tidak ada")
            return
        if int(getinfo["owner"]) == int(user.id) or int(user.id) == OWNER_ID:
            fed_id = is_fed_id
        else:
            update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
            return
    else:
        update.effective_message.reply_text("Apa yang harus saya hapus?")
        return

    if is_user_fed_owner(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
        return

    update.effective_message.reply_text(
        "Anda yakin ingin menghapus federasi Anda? Ini tidak dapat dikembalikan, Anda akan kehilangan seluruh daftar cekal Anda, dan '{}' akan hilang secara permanen.".format(
            getinfo["fname"]
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="⚠️ Hapus Federas ⚠️",
                        callback_data="rmfed_{}".format(fed_id),
                    )
                ],
                [InlineKeyboardButton(text="Cancel", callback_data="rmfed_cancel")],
            ]
        ),
    )


@run_async
def fed_chat(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user
    fed_id = sql.get_fed_id(chat.id)

    user_id = update.effective_message.from_user.id
    if not is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text(
            "Anda harus menjadi admin untuk menjalankan perintah ini"
        )
        return

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak tergabung dalam federasi mana pun!")
        return

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "Grup ini adalah bagian dari federasi berikut:"
    text += "\n{} (ID: <code>{}</code>)".format(info["fname"], fed_id)

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def join_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    message = update.effective_message
    administrators = chat.get_administrators()
    fed_id = sql.get_fed_id(chat.id)

    if user.id in SUDO_USERS:
        pass
    else:
        for admin in administrators:
            status = admin.status
            if status == "creator":
                if str(admin.user.id) == str(user.id):
                    pass
                else:
                    update.effective_message.reply_text(
                        "Hanya pembuat grup yang dapat menggunakan perintah ini!"
                    )
                    return
    if fed_id:
        message.reply_text("Anda tidak dapat bergabung dengan dua federasi dari satu obrolan")
        return

    if len(args) >= 1:
        getfed = sql.search_fed_by_id(args[0])
        if getfed == False:
            message.reply_text("Harap masukkan ID federasi yang valid")
            return

        x = sql.chat_join_fed(args[0], chat.title, chat.id)
        if not x:
            message.reply_text(
                "Gagal bergabung dengan federasi!"
            )
            return

        get_fedlog = sql.get_fed_log(args[0])
        if get_fedlog:
            if eval(get_fedlog):
                bot.send_message(
                    get_fedlog,
                    "Obrolan *{}* telah bergabung dengan federasi *{}*".format(
                        chat.title, getfed["fname"]
                    ),
                    parse_mode="markdown",
                )

        message.reply_text(
            "Grup ini telah bergabung dengan federasi: {}!".format(getfed["fname"])
        )


@run_async
def leave_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fed_info = sql.get_fed_info(fed_id)

    # administrators = chat.get_administrators().status
    getuser = bot.get_chat_member(chat.id, user.id).status
    if getuser in "creator" or user.id in SUDO_USERS:
        if sql.chat_leave_fed(chat.id) == True:
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if eval(get_fedlog):
                    bot.send_message(
                        get_fedlog,
                        "Obrolan *{}* telah meninggalkan federasi *{}*".format(
                            chat.title, fed_info["fname"]
                        ),
                        parse_mode="markdown",
                    )
            send_message(
                update.effective_message,
                "Grup ini telah meninggalkan federasi {}!".format(fed_info["fname"]),
            )
        else:
            update.effective_message.reply_text(
                "Bagaimana Anda bisa meninggalkan federasi yang belum pernah Anda ikuti?!"
            )
    else:
        update.effective_message.reply_text("Hanya pembuat grup yang dapat menggunakan perintah ini!")


@run_async
def user_join_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id) or user.id in SUDO_USERS:
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)
        elif not msg.reply_to_message and not args:
            user = msg.from_user
        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            msg.reply_text("Saya tidak dapat mengekstrak pengguna dari pesan ini")
            return
        else:
            LOGGER.warning("error")
        getuser = sql.search_user_in_fed(fed_id, user_id)
        fed_id = sql.get_fed_id(chat.id)
        info = sql.get_fed_info(fed_id)
        get_owner = eval(info["fusers"])["owner"]
        get_owner = bot.get_chat(get_owner).id
        if user_id == get_owner:
            update.effective_message.reply_text(
                "Anda tahu bahwa pengguna adalah pemilik federasi, bukan? BAIK?"
            )
            return
        if getuser:
            update.effective_message.reply_text(
                "Saya tidak dapat mempromosikan pengguna yang sudah menjadi admin federasi! Dapat menghapusnya jika Anda mau!"
            )
            return
        if user_id == bot.id:
            update.effective_message.reply_text(
                "Saya sudah menginginkan admin federasi di semua federasi!"
            )
            return
        res = sql.user_join_fed(fed_id, user_id)
        if res:
            update.effective_message.reply_text("Berhasil Dipromosikan!")
        else:
            update.effective_message.reply_text("Gagal mempromosikan!")
    else:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")


@run_async
def user_demote_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id):
        msg = update.effective_message
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)

        elif not msg.reply_to_message and not args:
            user = msg.from_user

        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            msg.reply_text("Saya tidak dapat mengekstrak pengguna dari pesan ini")
            return
        else:
            LOGGER.warning("error")

        if user_id == bot.id:
            update.effective_message.reply_text(
                "Hal yang Anda coba turunkan dari saya akan gagal bekerja tanpa saya! Hanya mengatakan."
            )
            return

        if sql.search_user_in_fed(fed_id, user_id) == False:
            update.effective_message.reply_text(
                "Saya tidak dapat menurunkan orang yang bukan admin federasi!"
            )
            return

        res = sql.user_demote_fed(fed_id, user_id)
        if res == True:
            update.effective_message.reply_text("Diturunkan dari Admin Fed!")
        else:
            update.effective_message.reply_text("Demosi gagal!")
    else:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
        return


@run_async
def fed_info(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user
    if args:
        fed_id = args[0]
        info = sql.get_fed_info(fed_id)
    else:
        fed_id = sql.get_fed_id(chat.id)
        if not fed_id:
            send_message(
                update.effective_message, "Grup ini tidak tergabung dalam federasi mana pun!"
            )
            return
        info = sql.get_fed_info(fed_id)

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    owner = bot.get_chat(info["owner"])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    FEDADMIN = sql.all_fed_users(fed_id)
    FEDADMIN.append(int(owner.id))
    TotalAdminFed = len(FEDADMIN)

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "<b>ℹ️ Federation Information:</b>"
    text += "\nFedID: <code>{}</code>".format(fed_id)
    text += "\nNama: {}".format(info["fname"])
    text += "\nPencipta: {}".format(mention_html(owner.id, owner_name))
    text += "\nSemua Admin: <code>{}</code>".format(TotalAdminFed)
    getfban = sql.get_all_fban_users(fed_id)
    text += "\nTotal pengguna yang dilarang: <code>{}</code>".format(len(getfban))
    getfchat = sql.all_fed_chats(fed_id)
    text += "\nJumlah grup di federasi ini: <code>{}</code>".format(
        len(getfchat)
    )

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def fed_admin(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak tergabung dalam federasi mana pun!")
        return

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "<b>Federation Admin {}:</b>\n\n".format(info["fname"])
    text += "👑 Pemilik:\n"
    owner = bot.get_chat(info["owner"])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    text += " • {}\n".format(mention_html(owner.id, owner_name))

    members = sql.all_fed_members(fed_id)
    if len(members) == 0:
        text += "\n🔱 Tidak ada admin di federasi ini"
    else:
        text += "\n🔱 Admin:\n"
        for x in members:
            user = bot.get_chat(x)
            text += " • {}\n".format(mention_html(user.id, user.first_name))

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def fed_ban(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    info = sql.get_fed_info(fed_id)
    getfednotif = sql.user_feds_report(info["owner"])

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    message = update.effective_message

    user_id, reason = extract_unt_fedban(message, args)

    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)

    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna")
        return

    if user_id == bot.id:
        message.reply_text(
            "Apa yang lebih lucu daripada menendang pembuat grup? Pengorbanan diri."
        )
        return

    if is_user_fed_owner(fed_id, user_id) == True:
        message.reply_text("Mengapa Anda mencoba federasi fban?")
        return

    if is_user_fed_admin(fed_id, user_id) == True:
        message.reply_text("Dia adalah admin federasi, saya tidak bisa melarangnya.")
        return

    if user_id == OWNER_ID:
        message.reply_text("Nation level God cannot be fed banned!")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Royals cannot be fed banned!")
        return

    if int(user_id) in SARDEGNA_USERS:
        message.reply_text("SARDEGNAs cannot be fed banned!")
        return

    if int(user_id) in WHITELIST_USERS:
        message.reply_text("Neptunians cannot be fed banned!")
        return
    
    if int(user_id) in (777000, 1087968824):
        message.reply_text("Saya tidak melarang bot Telegram.")
        
    try:
        user_chat = bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_name = user_chat.first_name
        fban_user_lname = user_chat.last_name
        fban_user_uname = user_chat.username
    except BadRequest as excp:
        if not str(user_id).isdigit():
            send_message(update.effective_message, excp.message)
            return
        elif not len(str(user_id)) == 9:
            send_message(update.effective_message, "Itu bukan pengguna!")
            return
        isvalid = False
        fban_user_id = int(user_id)
        fban_user_name = "user({})".format(user_id)
        fban_user_lname = None
        fban_user_uname = None

    if isvalid and user_chat.type != "private":
        send_message(update.effective_message, "Itu bukan pengguna!")
        return

    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_name)
    else:
        user_target = fban_user_name

    if fban:
        fed_name = info["fname"]
        # 
        # starting = "The reason fban is replaced for {} in the Federation <b>{}</b>.".format(user_target, fed_name)
        # send_message(update.effective_message, starting, parse_mode=ParseMode.HTML)

        if reason == "":
            reason = "Tidak ada alasan yang diberikan."

        temp = sql.un_fban_user(fed_id, fban_user_id)
        if not temp:
            message.reply_text("Gagal memperbarui alasan fedban!")
            return
        x = sql.fban_user(
            fed_id,
            fban_user_id,
            fban_user_name,
            fban_user_lname,
            fban_user_uname,
            reason,
            int(time.time()),
        )
        if not x:
            message.reply_text(
                "Gagal mencekal dari federasi!"
            )
            return

        fed_chats = sql.all_fed_chats(fed_id)
        # Will send to current chat
        bot.send_message(
            chat.id,
            "<b>Alasan FedBan diperbarui</b>"
            "\n<b>Federasi:</b> {}"
            "\n<b>Federation Admin:</b> {}"
            "\n<b>Pengguna:</b> {}"
            "\n<b>ID Pengguna:</b> <code>{}</code>"
            "\n<b>Alasan:</b> {}".format(
                fed_name,
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
                reason,
            ),
            parse_mode="HTML",
        )
        # Send message to owner if fednotif is enabled
        if getfednotif:
            bot.send_message(
                info["owner"],
                "<b>Alasan FedBan diperbarui</b>"
                "\n<b>Federasi:</b> {}"
                "\n<b>Federation Admin:</b> {}"
                "\n<b>Pengguna:</b> {}"
                "\n<b>ID Penguna:</b> <code>{}</code>"
                "\n<b>Alasan:</b> {}".format(
                    fed_name,
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
                    reason,
                ),
                parse_mode="HTML",
            )
        # If fedlog is set, then send message, except fedlog is current chat
        get_fedlog = sql.get_fed_log(fed_id)
        if get_fedlog:
            if int(get_fedlog) != int(chat.id):
                bot.send_message(
                    get_fedlog,
                    "<b>Alasan FedBan diperbarui</b>"
                    "\n<b>Federasi:</b> {}"
                    "\n<b>Federation Admin:</b> {}"
                    "\n<b>Pengguna:</b> {}"
                    "\n<b>ID Pengguna:</b> <code>{}</code>"
                    "\n<b>Alasan:</b> {}".format(
                        fed_name,
                        mention_html(user.id, user.first_name),
                        user_target,
                        fban_user_id,
                        reason,
                    ),
                    parse_mode="HTML",
                )
        for fedschat in fed_chats:
            try:
                # Do not spam all fed chats
                """
				bot.send_message(chat, "<b>Alasan FedBan diperbarui</b>" \
							 "\n<b>Federasi:</b> {}" \
							 "\n<b>Federation Admin:</b> {}" \
							 "\n<b>Pengguna:</b> {}" \
							 "\n<b>ID Pengguna:</b> <code>{}</code>" \
							 "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
				"""
                bot.kick_chat_member(fedschat, fban_user_id)
            except BadRequest as excp:
                if excp.message in FBAN_ERRORS:
                    try:
                        dispatcher.bot.getChat(fedschat)
                    except Unauthorized:
                        sql.chat_leave_fed(fedschat)
                        LOGGER.info(
                            "Obrolan {} telah meninggalkan fed {} karena saya ditendang".format(
                                fedschat, info["fname"]
                            )
                        )
                        continue
                elif excp.message == "User_id_invalid":
                    break
                else:
                    LOGGER.warning(
                        "Tidak bisa fban pada {} karena: {}".format(chat, excp.message)
                    )
            except TelegramError:
                pass
        # Also do not spam all fed admins
        """
		send_to_list(bot, FEDADMIN,
				 "<b>Alasan FedBan diperbarui</b>" \
							 "\n<b>Federasi:</b> {}" \
							 "\n<b>Federation Admin:</b> {}" \
							 "\n<b>Pengguna:</b> {}" \
							 "\n<b>ID Pengguna:</b> <code>{}</code>" \
							 "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), 
							html=True)
		"""

        # Fban for fed subscriber
        subscriber = list(sql.get_subscriber(fed_id))
        if len(subscriber) != 0:
            for fedsid in subscriber:
                all_fedschat = sql.all_fed_chats(fedsid)
                for fedschat in all_fedschat:
                    try:
                        bot.kick_chat_member(fedschat, fban_user_id)
                    except BadRequest as excp:
                        if excp.message in FBAN_ERRORS:
                            try:
                                dispatcher.bot.getChat(fedschat)
                            except Unauthorized:
                                targetfed_id = sql.get_fed_id(fedschat)
                                sql.unsubs_fed(fed_id, targetfed_id)
                                LOGGER.info(
                                    "Obrolan {} memiliki unsub fed {} karena saya ditendang".format(
                                        fedschat, info["fname"]
                                    )
                                )
                                continue
                        elif excp.message == "User_id_invalid":
                            break
                        else:
                            LOGGER.warning(
                                "Tak dapat mengikuti {} karena: {}".format(
                                    fedschat, excp.message
                                )
                            )
                    except TelegramError:
                        pass
        # send_message(update.effective_message, "Fedban Reason has been updated.")
        return

    fed_name = info["fname"]

    starting = "Memulai larangan federasi untuk {} di Federas <b>{}</b>.".format(
        user_target, fed_name
    )
    update.effective_message.reply_text(starting, parse_mode=ParseMode.HTML)

    if reason == "":
        reason = "Tidak ada alasan yang diberikan."

    x = sql.fban_user(
        fed_id,
        fban_user_id,
        fban_user_name,
        fban_user_lname,
        fban_user_uname,
        reason,
        int(time.time()),
    )
    if not x:
        message.reply_text(
            "Gagal mencekal dari federasi!"
        )
        return

    fed_chats = sql.all_fed_chats(fed_id)
    # Will send to current chat
    bot.send_message(
        chat.id,
        "<b>Alasan FedBan diperbarui</b>"
        "\n<b>Federasi:</b> {}"
        "\n<b>Federation Admin:</b> {}"
        "\n<b>Pengguna:</b> {}"
        "\n<b>ID Pengguna:</b> <code>{}</code>"
        "\n<b>Alasan:</b> {}".format(
            fed_name,
            mention_html(user.id, user.first_name),
            user_target,
            fban_user_id,
            reason,
        ),
        parse_mode="HTML",
    )
    # Send message to owner if fednotif is enabled
    if getfednotif:
        bot.send_message(
            info["owner"],
            "<b>Alasan FedBan diperbarui</b>"
            "\n<b>Federasi:</b> {}"
            "\n<b>Federation Admin:</b> {}"
            "\n<b>Pengguna:</b> {}"
            "\n<b>ID Pengguna:</b> <code>{}</code>"
            "\n<b>Alasan:</b> {}".format(
                fed_name,
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
                reason,
            ),
            parse_mode="HTML",
        )
    # If fedlog is set, then send message, except fedlog is current chat
    get_fedlog = sql.get_fed_log(fed_id)
    if get_fedlog:
        if int(get_fedlog) != int(chat.id):
            bot.send_message(
                get_fedlog,
                "<b>Alasan FedBan diperbarui</b>"
                "\n<b>Federasi:</b> {}"
                "\n<b>Federation Admin:</b> {}"
                "\n<b>Pengguna:</b> {}"
                "\n<b>ID Pengguna:</b> <code>{}</code>"
                "\n<b>Alasan:</b> {}".format(
                    fed_name,
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
                    reason,
                ),
                parse_mode="HTML",
            )
    chats_in_fed = 0
    for fedschat in fed_chats:
        chats_in_fed += 1
        try:
            # Do not spamming all fed chats
            """
			bot.send_message(chat, "<b>Alasan FedBan diperbarui</b>" \
							"\n<b>Federasi:</b> {}" \
							"\n<b>Federation Admin:</b> {}" \
							"\n<b>Pengguna:</b> {}" \
							"\n<b>ID Pengguna:</b> <code>{}</code>" \
							"\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
			"""
            bot.kick_chat_member(fedschat, fban_user_id)
        except BadRequest as excp:
            if excp.message in FBAN_ERRORS:
                pass
            elif excp.message == "User_id_invalid":
                break
            else:
                LOGGER.warning(
                    "Tidak bisa fban pada {} karena: {}".format(chat, excp.message)
                )
        except TelegramError:
            pass

        # Also do not spamming all fed admins
        """
		send_to_list(bot, FEDADMIN,
				 "<b>Alasan FedBan diperbarui</b>" \
							 "\n<b>Federasi:</b> {}" \
							 "\n<b>Federation Admin:</b> {}" \
							 "\n<b>Pengguna:</b> {}" \
							 "\n<b>ID Pengguna:</b> <code>{}</code>" \
							 "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), 
							html=True)
		"""

        # Fban for fed subscriber
        subscriber = list(sql.get_subscriber(fed_id))
        if len(subscriber) != 0:
            for fedsid in subscriber:
                all_fedschat = sql.all_fed_chats(fedsid)
                for fedschat in all_fedschat:
                    try:
                        bot.kick_chat_member(fedschat, fban_user_id)
                    except BadRequest as excp:
                        if excp.message in FBAN_ERRORS:
                            try:
                                dispatcher.bot.getChat(fedschat)
                            except Unauthorized:
                                targetfed_id = sql.get_fed_id(fedschat)
                                sql.unsubs_fed(fed_id, targetfed_id)
                                LOGGER.info(
                                    "Obrolan {} memiliki unsub fed {} karena saya ditendang".format(
                                        fedschat, info["fname"]
                                    )
                                )
                                continue
                        elif excp.message == "User_id_invalid":
                            break
                        else:
                            LOGGER.warning(
                                "Tak dapat mengikuti {} karena: {}".format(
                                    fedschat, excp.message
                                )
                            )
                    except TelegramError:
                        pass
    if chats_in_fed == 0:
        send_message(update.effective_message, "Fedban memengaruhi 0 obrolan. ")
    elif chats_in_fed > 0:
        send_message(
            update.effective_message, "Fedban memengaruhi {} obrolan. ".format(chats_in_fed)
        )


@run_async
def unfban(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    info = sql.get_fed_info(fed_id)
    getfednotif = sql.user_feds_report(info["owner"])

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    user_id = extract_user_fban(message, args)
    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return

    try:
        user_chat = bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_name = user_chat.first_name
        fban_user_lname = user_chat.last_name
        fban_user_uname = user_chat.username
    except BadRequest as excp:
        if not str(user_id).isdigit():
            send_message(update.effective_message, excp.message)
            return
        elif not len(str(user_id)) == 9:
            send_message(update.effective_message, "Itu bukan pengguna!")
            return
        isvalid = False
        fban_user_id = int(user_id)
        fban_user_name = "pengguna({})".format(user_id)
        fban_user_lname = None
        fban_user_uname = None

    if isvalid and user_chat.type != "private":
        message.reply_text("Itu bukan pengguna!")
        return

    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_name)
    else:
        user_target = fban_user_name

    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, fban_user_id)
    if fban == False:
        message.reply_text("Pengguna ini tidak dilarang!")
        return

    banner = update.effective_user

    message.reply_text(
        "Saya akan memberi {} kesempatan lagi di federasi ini".format(user_chat.first_name)
    )

    chat_list = sql.all_fed_chats(fed_id)
    # Will send to current chat
    bot.send_message(
        chat.id,
        "<b>Un-FedBan</b>"
        "\n<b>Federasi:</b> {}"
        "\n<b>Federation Admin:</b> {}"
        "\n<b>Pengguna:</b> {}"
        "\n<b>ID Pengguna:</b> <code>{}</code>".format(
            info["fname"],
            mention_html(user.id, user.first_name),
            user_target,
            fban_user_id,
        ),
        parse_mode="HTML",
    )
    # Send message to owner if fednotif is enabled
    if getfednotif:
        bot.send_message(
            info["owner"],
            "<b>Un-FedBan</b>"
            "\n<b>Federasi:</b> {}"
            "\n<b>Federation Admin:</b> {}"
            "\n<b>Pengguna:</b> {}"
            "\n<b>ID Pengguna:</b> <code>{}</code>".format(
                info["fname"],
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
            ),
            parse_mode="HTML",
        )
    # If fedlog is set, then send message, except fedlog is current chat
    get_fedlog = sql.get_fed_log(fed_id)
    if get_fedlog:
        if int(get_fedlog) != int(chat.id):
            bot.send_message(
                get_fedlog,
                "<b>Un-FedBan</b>"
                "\n<b>Federasi:</b> {}"
                "\n<b>Federation Admin:</b> {}"
                "\n<b>Pengguna:</b> {}"
                "\n<b>ID Pengguna:</b> <code>{}</code>".format(
                    info["fname"],
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
                ),
                parse_mode="HTML",
            )
    unfbanned_in_chats = 0
    for fedchats in chat_list:
        unfbanned_in_chats += 1
        try:
            member = bot.get_chat_member(fedchats, user_id)
            if member.status == "kicked":
                bot.unban_chat_member(fedchats, user_id)
            # Do not spamming all fed chats
            """
			bot.send_message(chat, "<b>Un-FedBan</b>" \
						 "\n<b>Federasi:</b> {}" \
						 "\n<b>Federation Admin:</b> {}" \
						 "\n<b>Pengguna:</b> {}" \
						 "\n<b>ID Pengguna:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
			"""
        except BadRequest as excp:
            if excp.message in UNFBAN_ERRORS:
                pass
            elif excp.message == "User_id_invalid":
                break
            else:
                LOGGER.warning(
                    "Tidak bisa fban pada {} karena: {}".format(chat, excp.message)
                )
        except TelegramError:
            pass

    try:
        x = sql.un_fban_user(fed_id, user_id)
        if not x:
            send_message(
                update.effective_message,
                "Batalkan fban gagal, pengguna ini mungkin sudah tidak lagi diblokir!",
            )
            return
    except:
        pass

    # UnFban for fed subscriber
    subscriber = list(sql.get_subscriber(fed_id))
    if len(subscriber) != 0:
        for fedsid in subscriber:
            all_fedschat = sql.all_fed_chats(fedsid)
            for fedschat in all_fedschat:
                try:
                    bot.unban_chat_member(fedchats, user_id)
                except BadRequest as excp:
                    if excp.message in FBAN_ERRORS:
                        try:
                            dispatcher.bot.getChat(fedschat)
                        except Unauthorized:
                            targetfed_id = sql.get_fed_id(fedschat)
                            sql.unsubs_fed(fed_id, targetfed_id)
                            LOGGER.info(
                                "Obrolan {} memiliki unsub fed {} karena saya ditendang".format(
                                    fedschat, info["fname"]
                                )
                            )
                            continue
                    elif excp.message == "User_id_invalid":
                        break
                    else:
                        LOGGER.warning(
                            "Tak dapat mengikuti {} karena: {}".format(
                                fedschat, excp.message
                            )
                        )
                except TelegramError:
                    pass

    if unfbanned_in_chats == 0:
        send_message(
            update.effective_message, "Orang ini telah dicopot dari 0 obrolan."
        )
    if unfbanned_in_chats > 0:
        send_message(
            update.effective_message,
            "Orang ini telah dicabut dari {} obrolan.".format(unfbanned_in_chats),
        )
    # Also do not spamming all fed admins
    """
	FEDADMIN = sql.all_fed_users(fed_id)
	for x in FEDADMIN:
		getreport = sql.user_feds_report(x)
		if getreport == False:
			FEDADMIN.remove(x)
	send_to_list(bot, FEDADMIN,
			 "<b>Un-FedBan</b>" \
			 "\n<b>Federasi:</b> {}" \
			 "\n<b>Federation Admin:</b> {}" \
			 "\n<b>Pengguna:</b> {}" \
			 "\n<b>ID Pengguna:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name),
												 mention_html(user_chat.id, user_chat.first_name),
															  user_chat.id),
			html=True)
	"""


@run_async
def set_frules(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak tergabung dalam federasi mana pun!")
        return

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya admin yang diberi fed yang dapat melakukan ini!")
        return

    if len(args) >= 1:
        msg = update.effective_message
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        if len(args) == 2:
            txt = args[1]
            offset = len(txt) - len(raw_text)  # set correct offset relative to command
            markdown_rules = markdown_parser(
                txt, entities=msg.parse_entities(), offset=offset
            )
        x = sql.set_frules(fed_id, markdown_rules)
        if not x:
            update.effective_message.reply_text(
                "Wah! Terjadi kesalahan saat menyetel aturan federasi!"
            )
            return

        rules = sql.get_fed_info(fed_id)["frules"]
        getfed = sql.get_fed_info(fed_id)
        get_fedlog = sql.get_fed_log(fed_id)
        if get_fedlog:
            if eval(get_fedlog):
                bot.send_message(
                    get_fedlog,
                    "*{}* telah memperbarui aturan federasi untuk fed *{}*".format(
                        user.first_name, getfed["fname"]
                    ),
                    parse_mode="markdown",
                )
        update.effective_message.reply_text(f"Aturan telah diubah menjadi :\n{rules}!")
    else:
        update.effective_message.reply_text("Harap tulis aturan untuk menyiapkan ini!")


@run_async
def get_frules(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak tergabung dalam federasi mana pun!")
        return

    rules = sql.get_frules(fed_id)
    text = "*Aturan di fed ini:*\n"
    text += rules
    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@run_async
def fed_broadcast(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    if args:
        chat = update.effective_chat
        fed_id = sql.get_fed_id(chat.id)
        fedinfo = sql.get_fed_info(fed_id)
        if is_user_fed_owner(fed_id, user.id) == False:
            update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
            return
        # Parsing md
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        text_parser = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
        text = text_parser
        try:
            broadcaster = user.first_name
        except:
            broadcaster = user.first_name + " " + user.last_name
        text += "\n\n- {}".format(mention_markdown(user.id, broadcaster))
        chat_list = sql.all_fed_chats(fed_id)
        failed = 0
        for chat in chat_list:
            title = "*Siaran baru dari Fed {}*\n".format(fedinfo["fname"])
            try:
                bot.sendMessage(chat, title + text, parse_mode="markdown")
            except TelegramError:
                try:
                    dispatcher.bot.getChat(chat)
                except Unauthorized:
                    failed += 1
                    sql.chat_leave_fed(chat)
                    LOGGER.info(
                        "Obrolan {} tidak diberi fed {} karena saya dipukul".format(
                            chat, fedinfo["fname"]
                        )
                    )
                    continue
                failed += 1
                LOGGER.warning("Tidak dapat mengirim siaran ke {}".format(str(chat)))

        send_text = "Siaran federasi selesai"
        if failed >= 1:
            send_text += "{} kelompok gagal menerima pesan, mungkin karena meninggalkan Federasi.".format(
                failed
            )
        update.effective_message.reply_text(send_text)


@run_async
def fed_ban_list(bot: Bot, update: Update, args: List[str], chat_data):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    if is_user_fed_owner(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya pemilik Federasi yang dapat melakukan ini!")
        return

    user = update.effective_user
    chat = update.effective_chat
    getfban = sql.get_all_fban_users(fed_id)
    if len(getfban) == 0:
        update.effective_message.reply_text(
            "Daftar larangan federasi {} kosong".format(info["fname"]),
            parse_mode=ParseMode.HTML,
        )
        return

    if args:
        if args[0] == "json":
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get("status"):
                if jam <= int(cek.get("value")):
                    waktu = time.strftime(
                        "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value"))
                    )
                    update.effective_message.reply_text(
                        "Anda dapat mencadangkan data Anda setiap 30 menit sekali!\nAnda dapat mencadangkan data lagi di `{}`".format(
                            waktu
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                else:
                    if user.id not in SUDO_USERS:
                        put_chat(chat.id, new_jam, chat_data)
            else:
                if user.id not in SUDO_USERS:
                    put_chat(chat.id, new_jam, chat_data)
            backups = ""
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                json_parser = {
                    "user_id": users,
                    "first_name": getuserinfo["first_name"],
                    "last_name": getuserinfo["last_name"],
                    "user_name": getuserinfo["user_name"],
                    "reason": getuserinfo["reason"],
                }
                backups += json.dumps(json_parser)
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "kigyo_fbanned_users.json"
                update.effective_message.reply_document(
                    document=output,
                    filename="kigyo_fbanned_users.json",
                    caption="Total {} Pengguna diblokir oleh Federasi {}.".format(
                        len(getfban), info["fname"]
                    ),
                )
            return
        elif args[0] == "csv":
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get("status"):
                if jam <= int(cek.get("value")):
                    waktu = time.strftime(
                        "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value"))
                    )
                    update.effective_message.reply_text(
                        "Anda dapat mencadangkan data setiap 30 menit sekali!\nAnda dapat mencadangkan data lagi di `{}`".format(
                            waktu
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                else:
                    if user.id not in SUDO_USERS:
                        put_chat(chat.id, new_jam, chat_data)
            else:
                if user.id not in SUDO_USERS:
                    put_chat(chat.id, new_jam, chat_data)
            backups = "id,firstname,lastname,username,reason\n"
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                backups += "{user_id},{first_name},{last_name},{user_name},{reason}".format(
                    user_id=users,
                    first_name=getuserinfo["first_name"],
                    last_name=getuserinfo["last_name"],
                    user_name=getuserinfo["user_name"],
                    reason=getuserinfo["reason"],
                )
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "kigyo_fbanned_users.csv"
                update.effective_message.reply_document(
                    document=output,
                    filename="kigyo_fbanned_users.csv",
                    caption="Total {} Pengguna diblokir oleh Federasi {}.".format(
                        len(getfban), info["fname"]
                    ),
                )
            return

    text = "<b>{} pengguna telah dilarang dari federasi {}:</b>\n".format(
        len(getfban), info["fname"]
    )
    for users in getfban:
        getuserinfo = sql.get_all_fban_users_target(fed_id, users)
        if getuserinfo == False:
            text = "Tidak ada pengguna yang dilarang dari federasi {}".format(
                info["fname"]
            )
            break
        user_name = getuserinfo["first_name"]
        if getuserinfo["last_name"]:
            user_name += " " + getuserinfo["last_name"]
        text += " • {} (<code>{}</code>)\n".format(
            mention_html(users, user_name), users
        )

    try:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get("status"):
            if jam <= int(cek.get("value")):
                waktu = time.strftime(
                    "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value"))
                )
                update.effective_message.reply_text(
                    "Anda dapat mencadangkan data setiap 30 menit sekali!\nAnda dapat mencadangkan data lagi di `{}`".format(
                        waktu
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            else:
                if user.id not in SUDO_USERS:
                    put_chat(chat.id, new_jam, chat_data)
        else:
            if user.id not in SUDO_USERS:
                put_chat(chat.id, new_jam, chat_data)
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fbanlist.txt"
            update.effective_message.reply_document(
                document=output,
                filename="fbanlist.txt",
                caption="Berikut ini adalah daftar pengguna yang saat ini dilarang di Federasi {}.".format(
                    info["fname"]
                ),
            )


@run_async
def fed_notif(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    if args:
        if args[0] in ("yes", "on"):
            sql.set_feds_setting(user.id, True)
            msg.reply_text(
                "Pelaporan Federasi kembali! Setiap pengguna fban / unfban Anda akan diberi tahu melalui PM."
            )
        elif args[0] in ("no", "off"):
            sql.set_feds_setting(user.id, False)
            msg.reply_text(
                "Federasi Pelapor telah berhenti! Setiap pengguna yang fban / unfban tidak akan diberitahukan melalui PM."
            )
        else:
            msg.reply_text("Silakan masukkan `on`/`off`", parse_mode="markdown")
    else:
        getreport = sql.user_feds_report(user.id)
        msg.reply_text(
            "Preferensi laporan Federasi Anda saat ini: `{}`".format(getreport),
            parse_mode="markdown",
        )


@run_async
def fed_chats(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    getlist = sql.all_fed_chats(fed_id)
    if len(getlist) == 0:
        update.effective_message.reply_text(
            "Tidak ada pengguna yang dilarang dari federasi {}".format(info["fname"]),
            parse_mode=ParseMode.HTML,
        )
        return

    text = "<b>Obrolan baru bergabung dengan federasi {}:</b>\n".format(info["fname"])
    for chats in getlist:
        try:
            chat_name = dispatcher.bot.getChat(chats).title
        except Unauthorized:
            sql.chat_leave_fed(chats)
            LOGGER.info(
                "Obrolan {} telah meninggalkan fed {} karena saya ditendang".format(
                    chats, info["fname"]
                )
            )
            continue
        text += " • {} (<code>{}</code>)\n".format(chat_name, chats)

    try:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except:
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fedchats.txt"
            update.effective_message.reply_document(
                document=output,
                filename="fedchats.txt",
                caption="Berikut adalah daftar semua obrolan yang bergabung dengan federasi {}.".format(
                    info["fname"]
                ),
            )


@run_async
def fed_import_bans(bot: Bot, update: Update, chat_data):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)
    getfed = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    if is_user_fed_owner(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya pemilik Federasi yang dapat melakukan ini!")
        return

    if msg.reply_to_message and msg.reply_to_message.document:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get("status"):
            if jam <= int(cek.get("value")):
                waktu = time.strftime(
                    "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value"))
                )
                update.effective_message.reply_text(
                    "Anda bisa mendapatkan data Anda setiap 30 menit sekali!\nAnda bisa mendapatkan data lagi di `{}`".format(
                        waktu
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            else:
                if user.id not in SUDO_USERS:
                    put_chat(chat.id, new_jam, chat_data)
        else:
            if user.id not in SUDO_USERS:
                put_chat(chat.id, new_jam, chat_data)
        # if int(int(msg.reply_to_message.document.file_size)/1024) >= 200:
        # 	msg.reply_text("This file is too big!")
        # 	return
        success = 0
        failed = 0
        try:
            file_info = bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            msg.reply_text(
                "Coba unduh dan unggah ulang file, yang ini sepertinya rusak!"
            )
            return
        fileformat = msg.reply_to_message.document.file_name.split(".")[-1]
        if fileformat == "json":
            multi_fed_id = []
            multi_import_userid = []
            multi_import_firstname = []
            multi_import_lastname = []
            multi_import_username = []
            multi_import_reason = []
            with BytesIO() as file:
                file_info.download(out=file)
                file.seek(0)
                reading = file.read().decode("UTF-8")
                splitting = reading.split("\n")
                for x in splitting:
                    if x == "":
                        continue
                    try:
                        data = json.loads(x)
                    except json.decoder.JSONDecodeError as err:
                        failed += 1
                        continue
                    try:
                        import_userid = int(data["user_id"])  # Make sure it int
                        import_firstname = str(data["first_name"])
                        import_lastname = str(data["last_name"])
                        import_username = str(data["user_name"])
                        import_reason = str(data["reason"])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) == True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) == True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in SUDO_USERS:
                        failed += 1
                        continue
                    if int(import_userid) in SARDEGNA_USERS:
                        failed += 1
                        continue
                    if int(import_userid) in WHITELIST_USERS:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
            text = "Blok berhasil diimpor. {} orang diblokir.".format(
                success
            )
            if failed >= 1:
                text += " {} Failed to import.".format(failed)
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if eval(get_fedlog):
                    teks = "Fed *{}* berhasil mengimpor data. {} banned.".format(
                        getfed["fname"], success
                    )
                    if failed >= 1:
                        teks += " {} Gagal mengimpor.".format(failed)
                    bot.send_message(get_fedlog, teks, parse_mode="markdown")
        elif fileformat == "csv":
            multi_fed_id = []
            multi_import_userid = []
            multi_import_firstname = []
            multi_import_lastname = []
            multi_import_username = []
            multi_import_reason = []
            file_info.download(
                "fban_{}.csv".format(msg.reply_to_message.document.file_id)
            )
            with open(
                "fban_{}.csv".format(msg.reply_to_message.document.file_id),
                "r",
                encoding="utf8",
            ) as csvFile:
                reader = csv.reader(csvFile)
                for data in reader:
                    try:
                        import_userid = int(data[0])  # Make sure it int
                        import_firstname = str(data[1])
                        import_lastname = str(data[2])
                        import_username = str(data[3])
                        import_reason = str(data[4])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) == True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) == True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in SUDO_USERS:
                        failed += 1
                        continue
                    if int(import_userid) in SARDEGNA_USERS:
                        failed += 1
                        continue
                    if int(import_userid) in WHITELIST_USERS:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                    # t = ThreadWithReturnValue(target=sql.fban_user, args=(fed_id, str(import_userid), import_firstname, import_lastname, import_username, import_reason,))
                    # t.start()
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
            csvFile.close()
            os.remove("fban_{}.csv".format(msg.reply_to_message.document.file_id))
            text = "Files were imported successfully. {} people banned.".format(success)
            if failed >= 1:
                text += " {} Failed to import.".format(failed)
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if eval(get_fedlog):
                    teks = "Fed *{}* berhasil mengimpor data. {} dilarang.".format(
                        getfed["fname"], success
                    )
                    if failed >= 1:
                        teks += " {} Gagal mengimpor.".format(failed)
                    bot.send_message(get_fedlog, teks, parse_mode="markdown")
        else:
            send_message(update.effective_message, "File ini tidak didukung.")
            return
        send_message(update.effective_message, text)


@run_async
def del_fed_button(bot, update):
    query = update.callback_query
    userid = query.message.chat.id
    fed_id = query.data.split("_")[1]

    if fed_id == "cancel":
        query.message.edit_text("Penghapusan federasi dibatalkan")
        return

    getfed = sql.get_fed_info(fed_id)
    if getfed:
        delete = sql.del_fed(fed_id)
        if delete:
            query.message.edit_text(
                "Anda telah menghapus Federasi Anda! Sekarang semua Grup yang terhubung dengan `{}` tidak memiliki Federasi.".format(
                    getfed["fname"]
                ),
                parse_mode="markdown",
            )


@run_async
def fed_stat_user(bot, update, args):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if args:
        if args[0].isdigit():
            user_id = args[0]
        else:
            user_id = extract_user(msg, args)
    else:
        user_id = extract_user(msg, args)

    if user_id:
        if len(args) == 2 and args[0].isdigit():
            fed_id = args[1]
            user_name, reason, fbantime = sql.get_user_fban(fed_id, str(user_id))
            if fbantime:
                fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
            else:
                fbantime = "Unavaiable"
            if user_name == False:
                send_message(
                    update.effective_message,
                    "Fed {} not found!".format(fed_id),
                    parse_mode="markdown",
                )
                return
            if user_name == "" or user_name == None:
                user_name = "He/she"
            if not reason:
                send_message(
                    update.effective_message,
                    "{} tidak dilarang di federasi ini!".format(user_name),
                )
            else:
                teks = "{} dilarang dalam federasi ini karena:\n`{}`\n*Dicekal pada:* `{}`".format(
                    user_name, reason, fbantime
                )
                send_message(update.effective_message, teks, parse_mode="markdown")
            return
        user_name, fbanlist = sql.get_user_fbanlist(str(user_id))
        if user_name == "":
            try:
                user_name = bot.get_chat(user_id).first_name
            except BadRequest:
                user_name = "He/she"
            if user_name == "" or user_name == None:
                user_name = "He/she"
        if len(fbanlist) == 0:
            send_message(
                update.effective_message,
                "{} tidak dilarang di federasi mana pun!".format(user_name),
            )
            return
        else:
            teks = "{} telah dilarang di federasi ini:\n".format(user_name)
            for x in fbanlist:
                teks += "- `{}`: {}\n".format(x[0], x[1][:20])
            teks += "\nJika Anda ingin mengetahui lebih lanjut tentang alasan Fedban secara khusus, gunakan /fbanstat <FedID>"
            send_message(update.effective_message, teks, parse_mode="markdown")

    elif not msg.reply_to_message and not args:
        user_id = msg.from_user.id
        user_name, fbanlist = sql.get_user_fbanlist(user_id)
        if user_name == "":
            user_name = msg.from_user.first_name
        if len(fbanlist) == 0:
            send_message(
                update.effective_message,
                "{} tidak dilarang di federasi mana pun!".format(user_name),
            )
        else:
            teks = "{} telah dilarang di federasi ini:\n".format(user_name)
            for x in fbanlist:
                teks += "- `{}`: {}\n".format(x[0], x[1][:20])
            teks += "\nJika Anda ingin mengetahui lebih lanjut tentang alasan Fedban secara khusus, gunakan /fbanstat <FedID>"
            send_message(update.effective_message, teks, parse_mode="markdown")

    else:
        fed_id = args[0]
        fedinfo = sql.get_fed_info(fed_id)
        if not fedinfo:
            send_message(update.effective_message, "Fed {} not found!".format(fed_id))
            return
        name, reason, fbantime = sql.get_user_fban(fed_id, msg.from_user.id)
        if fbantime:
            fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
        else:
            fbantime = "Unavaiable"
        if not name:
            name = msg.from_user.first_name
        if not reason:
            send_message(
                update.effective_message,
                "{} tidak dilarang di federasi ini".format(name),
            )
            return
        send_message(
            update.effective_message,
            "{} dilarang dalam federasi ini karena:\n`{}`\n*Dicekal pada:* `{}`".format(
                name, reason, fbantime
            ),
            parse_mode="markdown",
        )


@run_async
def set_fed_log(bot, update, args):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    if args:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            send_message(update.effective_message, "Federasi ini tidak ada!")
            return
        isowner = is_user_fed_owner(args[0], user.id)
        if not isowner:
            send_message(
                update.effective_message,
                "Hanya pembuat federasi yang dapat menyetel log federasi.",
            )
            return
        setlog = sql.set_fed_log(args[0], chat.id)
        if setlog:
            send_message(
                update.effective_message,
                "Log Federasi `{}` telah diatur ke {}".format(
                    fedinfo["fname"], chat.title
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message, "Anda belum memberikan ID federasi And!"
        )


@run_async
def unset_fed_log(bot, update, args):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    if args:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            send_message(update.effective_message, "Federasi ini tidak ada!")
            return
        isowner = is_user_fed_owner(args[0], user.id)
        if not isowner:
            send_message(
                update.effective_message,
                "Hanya pembuat federasi yang dapat menyetel log federasi.",
            )
            return
        setlog = sql.set_fed_log(args[0], None)
        if setlog:
            send_message(
                update.effective_message,
                "Federasi log `{}` telah dicabut {}".format(
                    fedinfo["fname"], chat.title
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message, "Anda belum memberikan ID federasi And!"
        )


@run_async
def subs_feds(bot, update, args):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "Grup ini tidak tergabung dalam federasi mana pun!")
        return

    if is_user_fed_owner(fed_id, user.id) == False:
        send_message(update.effective_message, "Hanya pemilik yang diberi fed yang dapat melakukan ini!")
        return

    if args:
        getfed = sql.search_fed_by_id(args[0])
        if getfed == False:
            send_message(
                update.effective_message, "Harap masukkan ID federasi yang valid."
            )
            return
        subfed = sql.subs_fed(args[0], fed_id)
        if subfed:
            send_message(
                update.effective_message,
                "Federasi `{}` telah berlangganan federasi `{}`. Setiap kali ada Fedban dari federasi tersebut, federasi ini juga akan mencekal pengguna tersebut.".format(
                    fedinfo["fname"], getfed["fname"]
                ),
                parse_mode="markdown",
            )
            get_fedlog = sql.get_fed_log(args[0])
            if get_fedlog:
                if int(get_fedlog) != int(chat.id):
                    bot.send_message(
                        get_fedlog,
                        "Federation `{}` telah berlangganan federasi `{}`".format(
                            fedinfo["fname"], getfed["fname"]
                        ),
                        parse_mode="markdown",
                    )
        else:
            send_message(
                update.effective_message,
                "Federation `{}` sudah berlangganan federasi `{}`.".format(
                    fedinfo["fname"], getfed["fname"]
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message, "Anda belum memberikan ID federasi Anda!"
        )


@run_async
def unsubs_feds(bot, update, args):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "Grup ini tidak tergabung dalam federasi mana pun!")
        return

    if is_user_fed_owner(fed_id, user.id) == False:
        send_message(update.effective_message, "Hanya pemilik yang diberi fed yang dapat melakukan ini!")
        return

    if args:
        getfed = sql.search_fed_by_id(args[0])
        if getfed == False:
            send_message(
                update.effective_message, "Harap masukkan ID federasi yang valid."
            )
            return
        subfed = sql.unsubs_fed(args[0], fed_id)
        if subfed:
            send_message(
                update.effective_message,
                "Federation `{}` sekarang berhenti berlangganan fed `{}`.".format(
                    fedinfo["fname"], getfed["fname"]
                ),
                parse_mode="markdown",
            )
            get_fedlog = sql.get_fed_log(args[0])
            if get_fedlog:
                if int(get_fedlog) != int(chat.id):
                    bot.send_message(
                        get_fedlog,
                        "Federation `{}` telah berhenti berlangganan fed `{}`.".format(
                            fedinfo["fname"], getfed["fname"]
                        ),
                        parse_mode="markdown",
                    )
        else:
            send_message(
                update.effective_message,
                "Federasi `{}` tidak berlangganan `{}`.".format(
                    fedinfo["fname"], getfed["fname"]
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message, "Anda belum memberikan ID federasi Anda!"
        )


@run_async
def get_myfedsubs(bot, update, args):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk pm kami!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "Grup ini tidak tergabung dalam federasi mana pun!")
        return

    if is_user_fed_owner(fed_id, user.id) == False:
        send_message(update.effective_message, "Hanya pemilik yang diberi fed yang dapat melakukan ini!")
        return

    try:
        getmy = sql.get_mysubs(fed_id)
    except:
        getmy = []

    if len(getmy) == 0:
        send_message(
            update.effective_message,
            "Federasi `{}` tidak berlangganan federasi mana pun.".format(
                fedinfo["fname"]
            ),
            parse_mode="markdown",
        )
        return
    else:
        listfed = "Federasi `{}` berlangganan federasi:\n".format(
            fedinfo["fname"]
        )
        for x in getmy:
            listfed += "- `{}`\n".format(x)
        listfed += (
            "\nUntuk mendapatkan info fed `/fedinfo <fedid>`. Untuk berhenti berlangganan `/unsubfed <fedid>`."
        )
        send_message(update.effective_message, listfed, parse_mode="markdown")


@run_async
def get_myfeds_list(bot, update):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    fedowner = sql.get_user_owner_fed_full(user.id)
    if fedowner:
        text = "*Anda adalah pemilik feds:\n*"
        for f in fedowner:
            text += "- `{}`: *{}*\n".format(f["fed_id"], f["fed"]["fname"])
    else:
        text = "*Anda tidak memiliki fed!*"
    send_message(update.effective_message, text, parse_mode="markdown")


def is_user_fed_admin(fed_id, user_id):
    fed_admins = sql.all_fed_users(fed_id)
    if fed_admins == False:
        return False
    if int(user_id) in fed_admins or int(user_id) == OWNER_ID:
        return True
    else:
        return False


def is_user_fed_owner(fed_id, user_id):
    getsql = sql.get_fed_info(fed_id)
    if getsql == False:
        return False
    getfedowner = eval(getsql["fusers"])
    if getfedowner == None or getfedowner == False:
        return False
    getfedowner = getfedowner["owner"]
    if str(user_id) == getfedowner or int(user_id) == OWNER_ID:
        return True
    else:
        return False


@run_async
def welcome_fed(bot, update):
    chat = update.effective_chat
    user = update.effective_user
    fed_id = sql.get_fed_id(chat.id)
    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user.id)
    if fban:
        update.effective_message.reply_text(
            "Pengguna ini dilarang di federasi saat ini! Saya akan menghapusnya."
        )
        bot.kick_chat_member(chat.id, user.id)
        return True
    else:
        return False


def __stats__():
    all_fbanned = sql.get_all_fban_users_global()
    all_feds = sql.get_all_feds_users_global()
    return "{} users banned, across {} Federations".format(
        len(all_fbanned), len(all_feds)
    )


def __user_info__(user_id, chat_id):
    fed_id = sql.get_fed_id(chat_id)
    if fed_id:
        fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)
        info = sql.get_fed_info(fed_id)
        infoname = info["fname"]

        if int(info["owner"]) == user_id:
            text = "Pengguna ini adalah pemilik Federasi saat ini: <b>{}</b>.".format(
                infoname
            )
        elif is_user_fed_admin(fed_id, user_id):
            text = "Pengguna ini adalah admin Federasi saat ini: <b>{}</b>.".format(
                infoname
            )

        elif fban:
            text = "Dilarang di Federasi saat ini: <b>Yes</b>"
            text += "\n<b>Alasan:</b> {}".format(fbanreason)
        else:
            text = "Dilarang di Federasi saat ini: <b>No</b>"
    else:
        text = ""
    return text


# Temporary data
def put_chat(chat_id, value, chat_data):
    # print(chat_data)
    if value == False:
        status = False
    else:
        status = True
    chat_data[chat_id] = {"federation": {"status": status, "value": value}}


def get_chat(chat_id, chat_data):
    # print(chat_data)
    try:
        value = chat_data[chat_id]["federation"]
        return value
    except KeyError:
        return {"status": False, "value": False}


@run_async
def fed_owner_help(bot: Bot, update: Update):
    update.effective_message.reply_text(
        """*👑 Pemilik Fed Saja:*
 • `/newfed <fed_name>`*:* Membuat Federasi, Satu diperbolehkan per pengguna. Bisa juga digunakan untuk mengganti nama Fed. (maks. 64 karakter)
 • `/delfed <fed_id>`*:* Hapus Federasi, dan informasi apa pun yang terkait dengannya. Tidak akan membatalkan pengguna yang diblokir.
 • `/fpromote <user>`*:* Menetapkan pengguna sebagai admin federasi. Mengaktifkan semua perintah untuk pengguna di bawah `Admin Fed`.
 • `/fdemote  <user>`*:* Menurunkan Pengguna dari Federasi admin ke Pengguna biasa.
 • `/subfed <fed_id>`*:* Berlangganan ke fed ID yang diberikan, larangan dari fed langganan itu juga akan terjadi di fed Anda.
 • `/unsubfed <fed_id>`*:* Berhenti berlangganan ID fed yang diberikan.
 • `/setfedlog <fed_id>`*:* Menetapkan grup sebagai basis laporan log fed untuk federasi.
 • `/unsetfedlog <fed_id>`*:* Menghapus grup sebagai basis laporan log fed untuk federasi.
 • `/fbroadcast <message>`*:* Menyiarkan pesan ke semua grup yang telah bergabung dengan fed Anda.
 • `/fedsubs`*:* Menampilkan fed langganan grup Anda. `(rusak rn)`""",
        parse_mode=ParseMode.MARKDOWN,
    )


@run_async
def fed_admin_help(bot: Bot, update: Update):
    update.effective_message.reply_text(
        """*🔱 Fed Admins:*
 • `/fban <user> <reason>`*:* Fed melarang pengguna.
 • `/unfban <user> <reason>`*:* Menghapus pengguna dari larangan fed.
 • `/fedinfo <fed_id>`*:* Informasi tentang Federasi yang ditentukan.
 • `/joinfed <fed_id>`*:* Bergabunglah dengan obrolan saat ini ke Federasi. Hanya pemilik obrolan yang dapat melakukan ini. Setiap obrolan hanya boleh di satu Federasi.
 • `/leavefed <fed_id>`*:* Biarkan Federasi diberikan. Hanya pemilik obrolan yang dapat melakukan ini.
 • `/setfrules <rules>`*:* Atur aturan Federasi.
 • `/fednotif <on/off>`*:* Pengaturan federasi tidak ada di PM bila ada pengguna yang berada fbaned/unfbanned.
 • `/frules`*:* Lihat peraturan Federasi.
 • `/fedadmins`*:* Tampilkan admin Federasi.
 • `/fbanlist`*:* Menampilkan semua pengguna yang menjadi korban di Federasi saat ini.
 • `/fedchats`*:* Dapatkan semua obrolan yang terhubung di Federasi.\n""",
        parse_mode=ParseMode.MARKDOWN,
    )


@run_async
def fed_user_help(bot: Bot, update: Update):
    update.effective_message.reply_text(
        """*🎩 Semua pengguna:*
• `/fbanstat`*:* Menunjukkan apakah Anda / atau pengguna yang Anda balas atau nama pengguna mereka di-fbanned di suatu tempat atau tidak.
• `/chatfed `*:* Lihat Federasi di obrolan saat ini.\n""",
        parse_mode=ParseMode.MARKDOWN,
    )


__mod_name__ = "Federations"

__help__ = """
Semuanya menyenangkan, sampai pelaku spam mulai memasuki grup Anda, dan Anda harus memblokirnya. Maka Anda perlu mulai melarang lebih banyak, dan lebih banyak lagi, dan itu menyakitkan.
Tetapi kemudian Anda memiliki banyak grup, dan Anda tidak ingin pelaku spam ini berada di salah satu grup Anda - bagaimana Anda bisa menangani? Apakah Anda harus memblokirnya secara manual, di semua grup Anda?\n
*Tidak lagi!* Dengan Federasi, Anda dapat membuat larangan di satu obrolan tumpang tindih dengan semua obrolan lainnya.\n
Anda bahkan dapat menunjuk admin federasi, sehingga admin tepercaya Anda dapat memblokir semua pengirim spam dari obrolan yang ingin Anda lindungi.\n

*Perintah:*\n
Feds sekarang dibagi menjadi 3 bagian untuk memudahkan Anda.
• `/fedownerhelp`*:* Memberikan bantuan untuk perintah pembuatan fed dan hanya pemilik.
• `/fedadminhelp`*:* Memberikan bantuan untuk perintah administrasi fed.
• `/feduserhelp`*:* Memberikan bantuan untuk perintah yang dapat digunakan siapa saja.

"""

NEW_FED_HANDLER = CommandHandler("newfed", new_fed)
DEL_FED_HANDLER = CommandHandler("delfed", del_fed, pass_args=True)
JOIN_FED_HANDLER = CommandHandler("joinfed", join_fed, pass_args=True)
LEAVE_FED_HANDLER = CommandHandler("leavefed", leave_fed, pass_args=True)
PROMOTE_FED_HANDLER = CommandHandler("fpromote", user_join_fed, pass_args=True)
DEMOTE_FED_HANDLER = CommandHandler("fdemote", user_demote_fed, pass_args=True)
INFO_FED_HANDLER = CommandHandler("fedinfo", fed_info, pass_args=True)
BAN_FED_HANDLER = DisableAbleCommandHandler(["fban", "fedban"], fed_ban, pass_args=True)
UN_BAN_FED_HANDLER = CommandHandler("unfban", unfban, pass_args=True)
FED_BROADCAST_HANDLER = CommandHandler("fbroadcast", fed_broadcast, pass_args=True)
FED_SET_RULES_HANDLER = CommandHandler("setfrules", set_frules, pass_args=True)
FED_GET_RULES_HANDLER = CommandHandler("frules", get_frules, pass_args=True)
FED_CHAT_HANDLER = CommandHandler("chatfed", fed_chat, pass_args=True)
FED_ADMIN_HANDLER = CommandHandler("fedadmins", fed_admin, pass_args=True)
FED_USERBAN_HANDLER = CommandHandler(
    "fbanlist", fed_ban_list, pass_args=True, pass_chat_data=True
)
FED_NOTIF_HANDLER = CommandHandler("fednotif", fed_notif, pass_args=True)
FED_CHATLIST_HANDLER = CommandHandler("fedchats", fed_chats, pass_args=True)
FED_IMPORTBAN_HANDLER = CommandHandler(
    "importfbans", fed_import_bans, pass_chat_data=True
)
FEDSTAT_USER = DisableAbleCommandHandler(
    ["fedstat", "fbanstat"], fed_stat_user, pass_args=True
)
SET_FED_LOG = CommandHandler("setfedlog", set_fed_log, pass_args=True)
UNSET_FED_LOG = CommandHandler("unsetfedlog", unset_fed_log, pass_args=True)
SUBS_FED = CommandHandler("subfed", subs_feds, pass_args=True)
UNSUBS_FED = CommandHandler("unsubfed", unsubs_feds, pass_args=True)
MY_SUB_FED = CommandHandler("fedsubs", get_myfedsubs, pass_args=True)
MY_FEDS_LIST = CommandHandler("myfeds", get_myfeds_list)
DELETEBTN_FED_HANDLER = CallbackQueryHandler(del_fed_button, pattern=r"rmfed_")
FED_OWNER_HELP_HANDLER = CommandHandler("fedownerhelp", fed_owner_help)
FED_ADMIN_HELP_HANDLER = CommandHandler("fedadminhelp", fed_admin_help)
FED_USER_HELP_HANDLER = CommandHandler("feduserhelp", fed_user_help)

dispatcher.add_handler(NEW_FED_HANDLER)
dispatcher.add_handler(DEL_FED_HANDLER)
dispatcher.add_handler(JOIN_FED_HANDLER)
dispatcher.add_handler(LEAVE_FED_HANDLER)
dispatcher.add_handler(PROMOTE_FED_HANDLER)
dispatcher.add_handler(DEMOTE_FED_HANDLER)
dispatcher.add_handler(INFO_FED_HANDLER)
dispatcher.add_handler(BAN_FED_HANDLER)
dispatcher.add_handler(UN_BAN_FED_HANDLER)
dispatcher.add_handler(FED_BROADCAST_HANDLER)
dispatcher.add_handler(FED_SET_RULES_HANDLER)
dispatcher.add_handler(FED_GET_RULES_HANDLER)
dispatcher.add_handler(FED_CHAT_HANDLER)
dispatcher.add_handler(FED_ADMIN_HANDLER)
dispatcher.add_handler(FED_USERBAN_HANDLER)
dispatcher.add_handler(FED_NOTIF_HANDLER)
dispatcher.add_handler(FED_CHATLIST_HANDLER)
# dispatcher.add_handler(FED_IMPORTBAN_HANDLER)
dispatcher.add_handler(FEDSTAT_USER)
dispatcher.add_handler(SET_FED_LOG)
dispatcher.add_handler(UNSET_FED_LOG)
dispatcher.add_handler(SUBS_FED)
dispatcher.add_handler(UNSUBS_FED)
dispatcher.add_handler(MY_SUB_FED)
dispatcher.add_handler(MY_FEDS_LIST)
dispatcher.add_handler(DELETEBTN_FED_HANDLER)
dispatcher.add_handler(FED_OWNER_HELP_HANDLER)
dispatcher.add_handler(FED_ADMIN_HELP_HANDLER)
dispatcher.add_handler(FED_USER_HELP_HANDLER)
