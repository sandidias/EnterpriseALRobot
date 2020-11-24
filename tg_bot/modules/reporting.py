# Haruka Aya
# Copyright (C) 2020  HarukaNetwork https://github.com/HarukaNetwork
import html
from typing import Optional, List
import re
from telegram import (
    Message,
    Chat,
    Update,
    Bot,
    User,
    ParseMode,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.error import BadRequest, Unauthorized
from telegram.ext import (
    CommandHandler,
    RegexHandler,
    run_async,
    Filters,
    CallbackQueryHandler,
)
from telegram.utils.helpers import mention_html

from tg_bot.modules.helper_funcs.chat_status import user_not_admin, user_admin
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import reporting_sql as sql
from tg_bot import dispatcher, LOGGER, SUDO_USERS, SARDEGNA_USERS

REPORT_GROUP = 5
REPORT_IMMUNE_USERS = SUDO_USERS + SARDEGNA_USERS


@run_async
@user_admin
def report_setting(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if chat.type == chat.PRIVATE:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text(
                    "Aktifkan pelaporan! Anda akan diberi tahu setiap kali ada yang melaporkan sesuatu."
                )

            elif args[0] in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("Nonaktifkan pelaporan! Anda tidak akan mendapatkan laporan apapun.")
        else:
            msg.reply_text(
                "Preferensi laporan Anda saat ini adalah: `{}`".format(
                    sql.user_should_report(chat.id)
                ),
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_chat_setting(chat.id, True)
                msg.reply_text(
                    "Aktifkan pelaporan! Admin yang telah mengaktifkan laporan akan diberi tahu ketika /report "
                    "atau @admin jika dipanggil."
                )

            elif args[0] in ("no", "off"):
                sql.set_chat_setting(chat.id, False)
                msg.reply_text(
                    "Nonaktifkan pelaporan! Tidak ada admin yang akan diberitahukan pada /report atau @admin."
                )
        else:
            msg.reply_text(
                "Pengaturan obrolan saat ini adalah: `{}`".format(
                    sql.chat_should_report(chat.id)
                ),
                parse_mode=ParseMode.MARKDOWN,
            )


@run_async
@user_not_admin
@loggable
def report(bot: Bot, update: Update) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user = message.reply_to_message.from_user  # type: Optional[User]
        chat_name = chat.title or chat.first or chat.username
        admin_list = chat.get_administrators()

        if reported_user.id in REPORT_IMMUNE_USERS:
            message.reply_text("Uh? Anda melaporkan pengguna yang masuk daftar putih?")
            return ""

        if chat.username and chat.type == Chat.SUPERGROUP:
            msg = (
                "<b>{}:</b>"
                "\n<b>Pengguna yang dilaporkan:</b> {} (<code>{}</code>)"
                "\n<b>Dilaporkan oleh:</b> {} (<code>{}</code>)".format(
                    html.escape(chat.title),
                    mention_html(reported_user.id, reported_user.first_name),
                    reported_user.id,
                    mention_html(user.id, user.first_name),
                    user.id,
                )
            )
            link = (
                "\n<b>Link:</b> "
                '<a href="http://telegram.me/{}/{}">click here</a>'.format(
                    chat.username, message.message_id
                )
            )

            should_forward = False
            keyboard = [
                [
                    InlineKeyboardButton(
                        u"➡ Message",
                        url="https://t.me/{}/{}".format(
                            chat.username, str(message.reply_to_message.message_id)
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        u"⚠ Kick",
                        callback_data="report_{}=kick={}={}".format(
                            chat.id, reported_user.id, reported_user.first_name
                        ),
                    ),
                    InlineKeyboardButton(
                        u"⛔️ Ban",
                        callback_data="report_{}=banned={}={}".format(
                            chat.id, reported_user.id, reported_user.first_name
                        ),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        u"❎ Hapus pesan",
                        callback_data="report_{}=delete={}={}".format(
                            chat.id,
                            reported_user.id,
                            message.reply_to_message.message_id,
                        ),
                    )
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

        else:
            msg = '{} is calling for admins in "{}"!'.format(
                mention_html(user.id, user.first_name), html.escape(chat_name)
            )
            link = ""
            should_forward = True

        for admin in admin_list:
            if admin.user.is_bot:  # can't message bots
                continue

            if sql.user_should_report(admin.user.id):
                try:
                    if not chat.type == Chat.SUPERGROUP:
                        bot.send_message(
                            admin.user.id, msg + link, parse_mode=ParseMode.HTML
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)

                    if not chat.username:
                        bot.send_message(
                            admin.user.id, msg + link, parse_mode=ParseMode.HTML
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)

                    if chat.username and chat.type == Chat.SUPERGROUP:
                        bot.send_message(
                            admin.user.id,
                            msg + link,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)

                except Unauthorized:
                    pass
                except BadRequest as excp:  # TODO: cleanup exceptions
                    LOGGER.exception("Exception while reporting user")

        message.reply_to_message.reply_text(
            "{} melaporkan pesan tersebut kepada admin.".format(
                mention_html(user.id, user.first_name)
            ),
            parse_mode=ParseMode.HTML,
        )
        return msg

    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(bot, update, chat, chatP, user):
    return "Obrolan ini disiapkan untuk mengirim laporan pengguna ke admin, melalui /report dan @admin: `{}`".format(
        sql.chat_should_report(chat.id)
    )


def __user_settings__(bot, update, user):
    if sql.user_should_report(user.id) == True:
        text = "Anda akan menerima laporan dari obrolan yang Anda kelola."
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Nonaktifkan pelaporan", callback_data="panel_reporting_U_disable"
                )
            ]
        ]
    else:
        text = "Anda *tidak* akan menerima laporan dari obrolan yang Anda kelola."
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Aktifkan pelaporan", callback_data="panel_reporting_U_enable"
                )
            ]
        ]

    return text, keyboard


def control_panel_user(bot, update):
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat
    query = update.callback_query
    enable = re.match(r"panel_reporting_U_enable", query.data)
    disable = re.match(r"panel_reporting_U_disable", query.data)

    query.message.delete()

    if enable:
        sql.set_user_setting(chat.id, True)
        text = "Pelaporan diaktifkan di pm Anda!"
    else:
        sql.set_user_setting(chat.id, False)
        text = "Pelaporan dinonaktifkan di pm Anda!"

    keyboard = [
        [InlineKeyboardButton(text="⬅️ Kembali", callback_data="cntrl_panel_U(1)")]
    ]

    update.effective_message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
    )


def buttons(bot: Bot, update):
    query = update.callback_query
    splitter = query.data.replace("report_", "").split("=")
    if splitter[1] == "kick":
        try:
            bot.kickChatMember(splitter[0], splitter[2])
            bot.unbanChatMember(splitter[0], splitter[2])
            query.answer("✅ Berhasil ditendang")
            return ""
        except Exception as err:
            query.answer("❎ Gagal menendang seseorang")
            bot.sendMessage(
                text="Error: {}".format(err),
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
    elif splitter[1] == "banned":
        try:
            bot.kickChatMember(splitter[0], splitter[2])
            query.answer("✅  Berhasil Diblokir")
            return ""
        except Exception as err:
            bot.sendMessage(
                text="Error: {}".format(err),
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
            query.answer("❎ Gagal memblokir")
    elif splitter[1] == "delete":
        try:
            bot.deleteMessage(splitter[0], splitter[3])
            query.answer("✅ Pesan dihapus")
            return ""
        except Exception as err:
            bot.sendMessage(
                text="Error: {}".format(err),
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
            query.answer("❎ Gagal menghapus pesan!")


__mod_name__ = "Reporting"

__help__ = """
 - /report <alasan>: balas pesan untuk melaporkannya ke admin.
 - @admin: balas pesan untuk melaporkannya ke admin.
CATATAN: tidak satu pun dari ini akan dipicu jika digunakan oleh admin
*Admin saja:*
 - /reports <on/off>: ubah pengaturan laporan, atau lihat status saat ini.
   - Jika selesai di pm, matikan status Anda.
   - Jika dalam obrolan, matikan status obrolan itu.
"""

REPORT_HANDLER = CommandHandler("report", report, filters=Filters.group)
SETTING_HANDLER = CommandHandler("reports", report_setting, pass_args=True)
ADMIN_REPORT_HANDLER = RegexHandler("(?i)@admin(s)?", report)

cntrl_panel_user_callback_handler = CallbackQueryHandler(
    control_panel_user, pattern=r"panel_reporting_U"
)
report_button_user_handler = CallbackQueryHandler(buttons, pattern=r"report_")
dispatcher.add_handler(cntrl_panel_user_callback_handler)
dispatcher.add_handler(report_button_user_handler)

dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(SETTING_HANDLER)
