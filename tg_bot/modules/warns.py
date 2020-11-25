import html
import re
from typing import Optional, List

import telegram
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    User,
    CallbackQuery,
)
from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import (
    CommandHandler,
    run_async,
    DispatcherHandlerStop,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, BAN_STICKER, WHITELIST_USERS, SARDEGNA_USERS
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import (
    is_user_admin,
    bot_admin,
    user_admin_no_reply,
    user_admin,
    can_restrict,
)
from tg_bot.modules.helper_funcs.extraction import (
    extract_text,
    extract_user_and_text,
    extract_user,
)
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import split_message
from tg_bot.modules.helper_funcs.string_handling import split_quotes
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import warns_sql as sql

WARN_HANDLER_GROUP = 9
CURRENT_WARNING_FILTER_STRING = "<b>Filter peringatan saat ini dalam obrolan ini:</b>\n"


# Not async
def warn(
    user: User, chat: Chat, reason: str, message: Message, warner: User = None
) -> str:
    if is_user_admin(chat, user.id):
        # message.reply_text("Damn admins, They are too far to be One Punched!")
        return

    if user.id in SARDEGNA_USERS:
        if warner:
            message.reply_text("Sardegnas tidak bisa diperingatkan.")
        else:
            message.reply_text(
                "Sardegna memicu filter peringatan otomatis!\n Saya tidak bisa memperingatkan Sardegnas tetapi mereka harus menghindari penyalahgunaan ini."
            )
        return

    if user.id in WHITELIST_USERS:
        if warner:
            message.reply_text("Neptunia Nations are warn immune.")
        else:
            message.reply_text(
                "Neptunia Nation triggered an auto warn filter!\n I can't warn Neptunians but they should avoid abusing this."
            )
        return

    if warner:
        warner_tag = mention_html(warner.id, warner.first_name)
    else:
        warner_tag = "Filter peringatan otomatis."

    limit, soft_warn = sql.get_warn_setting(chat.id)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)
    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if soft_warn:  # punch
            chat.unban_member(user.id)
            reply = f"{limit} peringatan, *Menendang {mention_html(user.id, user.first_name)}* "

        else:  # ban
            chat.kick_member(user.id)
            reply = f"{limit} peringatan, *Menendang {mention_html(user.id, user.first_name)}* "

        for warn_reason in reasons:
            reply += f"\n - {html.escape(warn_reason)}"

        message.bot.send_sticker(chat.id, BAN_STICKER)  # Kigyō's sticker
        keyboard = []
        log_reason = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#WARN_BAN\n"
            f"<b>Admin:</b> {warner_tag}\n"
            f"<b>Pengguna:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>Alasan:</b> {reason}\n"
            f"<b>Jumlah:</b> <code>{num_warns}/{limit}</code>"
        )

    else:
        keyboard = InlineKeyboardMarkup(
            [
                {
                    InlineKeyboardButton(
                        "Hapus peringatan", callback_data="rm_warn({})".format(user.id)
                    )
                }
            ]
        )

        reply = f"{mention_html(user.id, user.first_name)} memiliki {num_warns}/{limit} peringatan ... hati-hati!"
        if reason:
            reply += f"\nAlasan peringatan terakhir:\n{html.escape(reason)}"

        log_reason = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#WARN\n"
            f"<b>Admin:</b> {warner_tag}\n"
            f"<b>Pengguna:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>Alasan:</b> {reason}\n"
            f"<b>Jumlah:</b> <code>{num_warns}/{limit}</code>"
        )

    try:
        message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except BadRequest as excp:
        if excp.message == "Pesan balasan tidak ditemukan":
            # Do not reply
            message.reply_text(
                reply, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False
            )
        else:
            raise
    return log_reason


@run_async
@user_admin_no_reply
@bot_admin
@loggable
def button(bot: Bot, update: Update) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    match = re.match(r"rm_warn\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat: Optional[Chat] = update.effective_chat
        res = sql.remove_warn(user_id, chat.id)
        if res:
            update.effective_message.edit_text(
                "Peringatkan dihapus oleh {}.".format(mention_html(user.id, user.first_name)),
                parse_mode=ParseMode.HTML,
            )
            user_member = chat.get_member(user_id)
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#UNWARN\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>Pengguna:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
            )
        else:
            update.effective_message.edit_text(
                f"Pengguna sudah tidak memiliki peringatan.", parse_mode=ParseMode.HTML
            )

    return ""


@run_async
@user_admin
@can_restrict
@loggable
def warn_user(bot: Bot, update: Update, args: List[str]) -> str:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    warner: Optional[User] = update.effective_user

    user_id, reason = extract_user_and_text(message, args)

    if user_id:
        if (
            message.reply_to_message
            and message.reply_to_message.from_user.id == user_id
        ):
            return warn(
                message.reply_to_message.from_user,
                chat,
                reason,
                message.reply_to_message,
                warner,
            )
        else:
            return warn(chat.get_member(user_id).user, chat, reason, message, warner)
    else:
        message.reply_text("Bagi saya sepertinya ID Pengguna tidak valid")
    return ""


@run_async
@user_admin
@bot_admin
@loggable
def reset_warns(bot: Bot, update: Update, args: List[str]) -> str:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user

    user_id = extract_user(message, args)

    if user_id:
        sql.reset_warns(user_id, chat.id)
        message.reply_text("Peringatan telah disetel ulang!")
        warned = chat.get_member(user_id).user
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#RESETWARNS\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>Pengguna:</b> {mention_html(warned.id, warned.first_name)}"
        )
    else:
        message.reply_text("Tidak ada pengguna yang ditunjuk!")
    return ""


@run_async
def warns(bot: Bot, update: Update, args: List[str]):
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user_id = extract_user(message, args) or update.effective_user.id
    result = sql.get_warns(user_id, chat.id)

    if result and result[0] != 0:
        num_warns, reasons = result
        limit, soft_warn = sql.get_warn_setting(chat.id)

        if reasons:
            text = (
                f"Pengguna ini memiliki {num_warns}/{limit} memperingatkan, karena alasan berikut:"
            )
            for reason in reasons:
                text += f"\n - {reason}"

            msgs = split_message(text)
            for msg in msgs:
                update.effective_message.reply_text(msg)
        else:
            update.effective_message.reply_text(
                f"Pengguna memiliki {num_warns}/{limit} memperingatkan, tapi tidak ada alasan untuk salah satu dari mereka."
            )
    else:
        update.effective_message.reply_text("Pengguna ini tidak memiliki peringatan apa pun!")


# Dispatcher handler stop - do not async
@user_admin
def add_warn_filter(bot: Bot, update: Update):
    chat: Optional[Chat] = update.effective_chat
    msg: Optional[Message] = update.effective_message

    args = msg.text.split(
        None, 1
    )  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) >= 2:
        # set trigger -> lower, so as to avoid adding duplicate filters with different cases
        keyword = extracted[0].lower()
        content = extracted[1]

    else:
        return

    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(WARN_HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, WARN_HANDLER_GROUP)

    sql.add_warn_filter(chat.id, keyword, content)

    update.effective_message.reply_text(f"Penangan peringatan ditambahkan untuk '{keyword}'!")
    raise DispatcherHandlerStop


@user_admin
def remove_warn_filter(bot: Bot, update: Update):
    chat: Optional[Chat] = update.effective_chat
    msg: Optional[Message] = update.effective_message

    args = msg.text.split(
        None, 1
    )  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) < 1:
        return

    to_remove = extracted[0]

    chat_filters = sql.get_chat_warn_triggers(chat.id)

    if not chat_filters:
        msg.reply_text("Tidak ada filter peringatan yang aktif di sini!")
        return

    for filt in chat_filters:
        if filt == to_remove:
            sql.remove_warn_filter(chat.id, to_remove)
            msg.reply_text("Oke, saya akan berhenti memperingatkan orang untuk itu.")
            raise DispatcherHandlerStop

    msg.reply_text(
        "Itu bukan filter peringatan saat ini - jalankan /warnlist untuk semua filter peringatan aktif."
    )


@run_async
def list_warn_filters(bot: Bot, update: Update):
    chat: Optional[Chat] = update.effective_chat
    all_handlers = sql.get_chat_warn_triggers(chat.id)

    if not all_handlers:
        update.effective_message.reply_text("Tidak ada filter peringatan yang aktif di sini!")
        return

    filter_list = CURRENT_WARNING_FILTER_STRING
    for keyword in all_handlers:
        entry = f" - {html.escape(keyword)}\n"
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == CURRENT_WARNING_FILTER_STRING:
        update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)


@run_async
@loggable
def reply_filter(bot: Bot, update: Update) -> str:
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message

    chat_warn_filters = sql.get_chat_warn_triggers(chat.id)
    to_match = extract_text(message)
    if not to_match:
        return ""

    for keyword in chat_warn_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            user: Optional[User] = update.effective_user
            warn_filter = sql.get_warn_filter(chat.id, keyword)
            return warn(user, chat, warn_filter.reply, message)
    return ""


@run_async
@user_admin
@loggable
def set_warn_limit(bot: Bot, update: Update, args: List[str]) -> str:
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    msg: Optional[Message] = update.effective_message

    if args:
        if args[0].isdigit():
            if int(args[0]) < 3:
                msg.reply_text("Batas peringatan minimum adalah 3!")
            else:
                sql.set_warn_limit(chat.id, int(args[0]))
                msg.reply_text("Updated the warn limit to {}".format(args[0]))
                return (
                    f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#SET_WARN_LIMIT\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"Setel batas peringatan ke <code>{args[0]}</code>"
                )
        else:
            msg.reply_text("Beri saya nomor sebagai argumen!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)

        msg.reply_text("Batas peringatan saat ini adalah {}".format(limit))
    return ""


@run_async
@user_admin
def set_warn_strength(bot: Bot, update: Update, args: List[str]):
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    msg: Optional[Message] = update.effective_message

    if args:
        if args[0].lower() in ("on", "yes"):
            sql.set_warn_strength(chat.id, False)
            msg.reply_text("Terlalu banyak peringatan sekarang akan mengakibatkan Ban!")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Telah mengaktifkan peringatan yang kuat. Pengguna akan saya tendang keluar.(banned)"
            )

        elif args[0].lower() in ("off", "no"):
            sql.set_warn_strength(chat.id, True)
            msg.reply_text(
                "TTelah mengaktifkan peringatan yang kuat. Pengguna akan ditendang dengan serius"
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Telah menonaktifkan. Saya akan menendang bokong pada pengguna."
            )

        else:
            msg.reply_text("Saya hanya mengert on/yes/no/off!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)
        if soft_warn:
            msg.reply_text(
                "Peringatan saat ini disetel untuk *ditendang* pengguna saat mereka melebihi batas.",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            msg.reply_text(
                "Peringatan saat ini disetel ke *DiCekal* pengguna saat mereka melebihi batas.",
                parse_mode=ParseMode.MARKDOWN,
            )
    return ""


def __stats__():
    return (
        f"{sql.num_warns()} overall warns, across {sql.num_warn_chats()} chats.\n"
        f"{sql.num_warn_filters()} warn filters, across {sql.num_warn_filter_chats()} chats."
    )


def __import_data__(chat_id, data):
    for user_id, count in data.get("warns", {}).items():
        for x in range(int(count)):
            sql.warn_user(user_id, chat_id)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    num_warn_filters = sql.num_warn_chat_filters(chat_id)
    limit, soft_warn = sql.get_warn_setting(chat_id)
    return (
        f"Obrolan ini memiliki `{num_warn_filters}` peringatkan filter. "
        f"Dibutuhkan `{limit}` memperingatkan sebelum pengguna mendapatkannya *{'kicked' if soft_warn else 'banned'}*."
    )


__help__ = """
 - /warns <userhandle>: dapatkan nomor pengguna, dan alasan, peringatan.
 - /warnlist: daftar semua filter peringatan saat ini

*Admins saja:*
 - /warn <userhandle>: peringatkan pengguna. Setelah 3 peringatan, pengguna akan diblokir dari grup. Bisa juga digunakan sebagai balasan.
 - /resetwarn <userhandle>: setel ulang peringatan untuk pengguna. Bisa juga digunakan sebagai balasan.
 - /addwarn <kata kunci> <balas pesan>: setel filter peringatan pada kata kunci tertentu. Jika Anda ingin kata kunci Anda \
jadilah kalimat, lengkapi dengan tanda kutip, seperti itu: `/addwarn "sangat marah" Ini adalah pengguna yang marah`. 
 - /nowarn <kata kunci>: hentikan filter peringatan
 - /warnlimit <num>: setel batas peringatan
 - /strongwarn <on/yes/off/no>: Jika disetel ke aktif, melebihi batas peringatan akan mengakibatkan larangan. Lain, hanya akan ditendang.
"""

__mod_name__ = "Warnings"

WARN_HANDLER = CommandHandler("warn", warn_user, pass_args=True, filters=Filters.group)
RESET_WARN_HANDLER = CommandHandler(
    ["resetwarn", "resetwarns"], reset_warns, pass_args=True, filters=Filters.group
)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(button, pattern=r"rm_warn")
MYWARNS_HANDLER = DisableAbleCommandHandler(
    "warns", warns, pass_args=True, filters=Filters.group
)
ADD_WARN_HANDLER = CommandHandler("addwarn", add_warn_filter, filters=Filters.group)
RM_WARN_HANDLER = CommandHandler(
    ["nowarn", "stopwarn"], remove_warn_filter, filters=Filters.group
)
LIST_WARN_HANDLER = DisableAbleCommandHandler(
    ["warnlist", "warnfilters"], list_warn_filters, filters=Filters.group, admin_ok=True
)
WARN_FILTER_HANDLER = MessageHandler(
    CustomFilters.has_text & Filters.group, reply_filter
)
WARN_LIMIT_HANDLER = CommandHandler(
    "warnlimit", set_warn_limit, pass_args=True, filters=Filters.group
)
WARN_STRENGTH_HANDLER = CommandHandler(
    "strongwarn", set_warn_strength, pass_args=True, filters=Filters.group
)

dispatcher.add_handler(WARN_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
dispatcher.add_handler(RESET_WARN_HANDLER)
dispatcher.add_handler(MYWARNS_HANDLER)
dispatcher.add_handler(ADD_WARN_HANDLER)
dispatcher.add_handler(RM_WARN_HANDLER)
dispatcher.add_handler(LIST_WARN_HANDLER)
dispatcher.add_handler(WARN_LIMIT_HANDLER)
dispatcher.add_handler(WARN_STRENGTH_HANDLER)
dispatcher.add_handler(WARN_FILTER_HANDLER, WARN_HANDLER_GROUP)
