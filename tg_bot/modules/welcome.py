import html
import random
import re
import time
from typing import List
from functools import partial

from telegram import Update, Bot, CallbackQuery
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import (
    MessageHandler,
    Filters,
    CommandHandler,
    run_async,
    CallbackQueryHandler,
    JobQueue,
)
from telegram.utils.helpers import mention_markdown, mention_html, escape_markdown

import tg_bot.modules.sql.welcome_sql as sql
from tg_bot import (
    dispatcher,
    OWNER_ID,
    DEV_USERS,
    SUDO_USERS,
    SUPPORT_USERS,
    SARDEGNA_USERS,
    WHITELIST_USERS,
    LOGGER,
    sw,
)
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_ban_protected
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.msg_types import get_welcome_type
from tg_bot.modules.helper_funcs.string_handling import (
    markdown_parser,
    escape_invalid_curly_brackets,
)
from tg_bot.modules.log_channel import loggable

VALID_WELCOME_FORMATTERS = [
    "first",
    "last",
    "fullname",
    "username",
    "id",
    "count",
    "chatname",
    "mention",
]

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video,
}

VERIFIED_USER_WAITLIST = {}

# do not async
def send(update, message, keyboard, backup_message):
    try:
        msg = update.effective_message.reply_text(
            message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nCatatan: pesan saat ini memiliki url yang tidak valid "
                    "di salah satu tombolnya. Harap perbarui."
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        elif excp.message == "Unsupported url protocol":
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nCatatan: pesan saat ini memiliki tombol yang "
                    "gunakan protokol url yang tidak didukung oleh "
                    "telegram. Harap perbarui."
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        elif excp.message == "Host url salah":
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nCatatan: pesan saat ini memiliki beberapa url yang buruk. "
                    "Harap perbarui."
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("Could not parse! got invalid url host errors")
        else:
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nCatatan: Terjadi kesalahan saat mengirim "
                    "pesan khusus. Harap perbarui."
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
            LOGGER.exception()

    return msg


@run_async
@loggable
def new_member(bot: Bot, update: Update, job_queue: JobQueue):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    should_welc, cust_welcome, welc_type = sql.get_welc_pref(chat.id)
    welc_mutes = sql.welcome_mutes(chat.id)
    human_checks = sql.get_human_checks(user.id, chat.id)

    new_members = update.effective_message.new_chat_members

    for new_mem in new_members:

        welcome_log = None
        sent = None
        should_mute = True
        welcome_bool = True

        if sw != None:
            sw_ban = sw.get_ban(new_mem.id)
            if sw_ban:
                return

        if should_welc:

            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text("Oh, Kamu ya? Mari kita mulai.")
                welcome_log = (
                    f"{html.escape(chat.title)}\n"
                    f"#USER_JOINED\n"
                    f"Pemilik Bot baru saja bergabung dalam obrolan"
                )

            # Welcome Devs
            elif new_mem.id in DEV_USERS:
                update.effective_message.reply_text(
                    "Wah! Seorang anggota baru saja bergabung!"
                )

            # Welcome Sudos
            elif new_mem.id in SUDO_USERS:
                update.effective_message.reply_text(
                    "Huh! A Royal Nation just joined! Stay Alert!"
                )

            # Welcome Support
            elif new_mem.id in SUPPORT_USERS:
                update.effective_message.reply_text(
                    "Huh! Someone with a Sakura Nation level just joined!"
                )

            # Welcome Whitelisted
            elif new_mem.id in SARDEGNA_USERS:
                update.effective_message.reply_text(
                    "Oof! A Sardegna Nation just joined!"
                )

            # Welcome Sardegnas
            elif new_mem.id in WHITELIST_USERS:
                update.effective_message.reply_text(
                    "Oof! A Neptunia Nation just joined!"
                )

            # Welcome yourself
            elif new_mem.id == bot.id:
                update.effective_message.reply_text("Terima kasih telah menambahkan saya!")

            else:
                # If welcome message is media, send with appropriate function
                if welc_type not in (sql.Types.TEXT, sql.Types.BUTTON_TEXT):
                    ENUM_FUNC_MAP[welc_type](chat.id, cust_welcome)
                    continue

                # else, move on
                first_name = (
                    new_mem.first_name or "PersonWithNoName"
                )  # edge case of empty name - occurs for some bugs.

                if cust_welcome:
                    if cust_welcome == sql.DEFAULT_WELCOME:
                        cust_welcome = random.choice(
                            sql.DEFAULT_WELCOME_MESSAGES
                        ).format(first=escape_markdown(first_name))

                    if new_mem.last_name:
                        fullname = escape_markdown(f"{first_name} {new_mem.last_name}")
                    else:
                        fullname = escape_markdown(first_name)
                    count = chat.get_members_count()
                    mention = mention_markdown(new_mem.id, escape_markdown(first_name))
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(
                        cust_welcome, VALID_WELCOME_FORMATTERS
                    )
                    res = valid_format.format(
                        first=escape_markdown(first_name),
                        last=escape_markdown(new_mem.last_name or first_name),
                        fullname=escape_markdown(fullname),
                        username=username,
                        mention=mention,
                        count=count,
                        chatname=escape_markdown(chat.title),
                        id=new_mem.id,
                    )
                    buttons = sql.get_welc_buttons(chat.id)
                    keyb = build_keyboard(buttons)

                else:
                    res = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                        first=escape_markdown(first_name)
                    )
                    keyb = []

                backup_message = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                    first=escape_markdown(first_name)
                )
                keyboard = InlineKeyboardMarkup(keyb)

        else:
            welcome_bool = False
            res = None
            keyboard = None
            backup_message = None

        # User exceptions from welcomemutes
        if (
            is_user_ban_protected(chat, new_mem.id, chat.get_member(new_mem.id))
            or human_checks
        ):
            should_mute = False
        # Join welcome: soft mute
        if new_mem.is_bot:
            should_mute = False

        if user.id == new_mem.id:
            if should_mute:
                if welc_mutes == "soft":
                    bot.restrict_chat_member(
                        chat.id,
                        new_mem.id,
                        can_send_messages=True,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                        until_date=(int(time.time() + 24 * 60 * 60)),
                    )

                if welc_mutes == "strong":
                    welcome_bool = False
                    VERIFIED_USER_WAITLIST.update(
                        {
                            new_mem.id: {
                                "should_welc": should_welc,
                                "status": False,
                                "update": update,
                                "res": res,
                                "keyboard": keyboard,
                                "backup_message": backup_message,
                            }
                        }
                    )
                    new_join_mem = f"[{escape_markdown(new_mem.first_name)}](tg://user?id={user.id})"
                    message = msg.reply_text(
                        f"{new_join_mem}, klik tombol di bawah untuk membuktikan bahwa Anda adalah manusia.\nWaktumu 160 detik.",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                {
                                    InlineKeyboardButton(
                                        text="Ya, saya manusia.",
                                        callback_data=f"user_join_({new_mem.id})",
                                    )
                                }
                            ]
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    bot.restrict_chat_member(
                        chat.id,
                        new_mem.id,
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                    )

                    job_queue.run_once(
                        partial(check_not_bot, new_mem, chat.id, message.message_id),
                        160,
                        name="welcomemute",
                    )

        if welcome_bool:
            sent = send(update, res, keyboard, backup_message)

            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

        if welcome_log:
            return welcome_log

        return (
            f"{html.escape(chat.title)}\n"
            f"#USER_JOINED\n"
            f"<b>Pengguna</b>: {mention_html(user.id, user.first_name)}\n"
            f"<b>ID</b>: <code>{user.id}</code>"
        )

    return ""


def check_not_bot(member, chat_id, message_id, bot, job):

    member_dict = VERIFIED_USER_WAITLIST.pop(member.id)
    member_status = member_dict.get("status")
    if not member_status:
        try:
            bot.unban_chat_member(chat_id, member.id)
        except:
            pass

        try:
            bot.edit_message_text(
                "*pengguna ditendang*\nMereka selalu dapat bergabung kembali dan mencoba.",
                chat_id=chat_id,
                message_id=message_id,
            )
        except:
            pass


@run_async
def left_member(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)

    if user.id == bot.id:
        return

    if should_goodbye:
        left_mem = update.effective_message.left_chat_member
        if left_mem:

            if sw != None:
                sw_ban = sw.get_ban(left_mem.id)
                if sw_ban:
                    return

            # Ignore bot being kicked
            if left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text("Oi! @admin! Dia pergi..")
                return

            # Give the devs a special goodbye
            elif left_mem.id in DEV_USERS:
                update.effective_message.reply_text("See you later at the Eagle Union!")
                return

            # if media goodbye, use appropriate function for it
            if goodbye_type != sql.Types.TEXT and goodbye_type != sql.Types.BUTTON_TEXT:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = (
                left_mem.first_name or "PersonWithNoName"
            )  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if cust_goodbye == sql.DEFAULT_GOODBYE:
                    cust_goodbye = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(
                        first=escape_markdown(first_name)
                    )
                if left_mem.last_name:
                    fullname = escape_markdown(f"{first_name} {left_mem.last_name}")
                else:
                    fullname = escape_markdown(first_name)
                count = chat.get_members_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(
                    cust_goodbye, VALID_WELCOME_FORMATTERS
                )
                res = valid_format.format(
                    first=escape_markdown(first_name),
                    last=escape_markdown(left_mem.last_name or first_name),
                    fullname=escape_markdown(fullname),
                    username=username,
                    mention=mention,
                    count=count,
                    chatname=escape_markdown(chat.title),
                    id=left_mem.id,
                )
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(
                    first=first_name
                )
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            send(
                update,
                res,
                keyboard,
                random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(first=first_name),
            )


@run_async
@user_admin
def welcome(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    # if no args, show current replies.
    if not args or args[0].lower() == "noformat":
        noformat = True
        pref, welcome_m, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(
            f"Obrolan ini memiliki setelan selamat datang yang disetel ke: `{pref}`.\n"
            f"*Pesan selamat datang (tidak mengisi {{}}) :*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if welcome_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)

        else:
            if noformat:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m)

            else:
                ENUM_FUNC_MAP[welcome_type](
                    chat.id, welcome_m, parse_mode=ParseMode.MARKDOWN
                )

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text(
                "Baik! Saya akan menyapa anggota saat mereka bergabung."
            )

        elif args[0].lower() in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text(
                "Aku akan pergi bermalas-malasan dan tidak menyambut siapa pun."
            )

        else:
            update.effective_message.reply_text(
                "Saya hanya mengerti'on/yes' atau 'off/no' saja!"
            )


@run_async
@user_admin
def goodbye(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat

    if not args or args[0] == "noformat":
        noformat = True
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(
            f"Obrolan ini memiliki setelan selamat tinggal yang disetel ke: `{pref}`.\n"
            f"*Pesan selamat tinggal (tidak mengisi {{}}):*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)

        else:
            if noformat:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

            else:
                ENUM_FUNC_MAP[goodbye_type](
                    chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN
                )

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("Ok!")

        elif args[0].lower() in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("Ok!")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text(
                "Saya mengerti 'on/yes' atau 'off/no' saja!"
            )


@run_async
@user_admin
@loggable
def set_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Anda tidak menentukan harus membalas dengan apa!")
        return ""

    sql.set_custom_welcome(chat.id, content or text, data_type, buttons)
    msg.reply_text("Berhasil menyetel pesan selamat datang!")

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Atur pesan selamat datang."
    )


@run_async
@user_admin
@loggable
def reset_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_welcome(chat.id, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    update.effective_message.reply_text(
        "Berhasil menyetel ulang pesan selamat datang ke default!"
    )

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Setel ulang pesan selamat datang ke default."
    )


@run_async
@user_admin
@loggable
def set_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Anda tidak menentukan harus membalas dengan apa!")
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    msg.reply_text("Berhasil menyetel pesan selamat tinggal!")
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_GOODBYE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Atur pesan selamat tinggal."
    )


@run_async
@user_admin
@loggable
def reset_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text(
        "Berhasil mengatur ulang pesan selamat tinggal ke default!"
    )

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_GOODBYE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Setel ulang pesan selamat tinggal."
    )


@run_async
@user_admin
@loggable
def welcomemute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if len(args) >= 1:
        if args[0].lower() in ("off", "no"):
            sql.set_welcome_mutes(chat.id, False)
            msg.reply_text("Saya tidak akan lagi menonaktifkan orang saat bergabung!")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Telah mengaktifkan bisukan selamat datang ke <b>OFF</b>."
            )
        elif args[0].lower() in ["soft"]:
            sql.set_welcome_mutes(chat.id, "soft")
            msg.reply_text(
                "Saya akan membatasi izin pengguna untuk mengirim media selama 24 jam."
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Telah mengaktifkan bisukan selamat datang ke <b>SOFT</b>."
            )
        elif args[0].lower() in ["strong"]:
            sql.set_welcome_mutes(chat.id, "strong")
            msg.reply_text(
                "Sekarang saya akan membisukan orang ketika mereka bergabung sampai mereka membuktikan bahwa mereka bukan bot.\nMereka memiliki waktu 160 detik sebelum ditendang."
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>STRONG</b>."
            )
        else:
            msg.reply_text(
                "Silahkan masukkan `off`/`no`/`soft`/`strong`!",
                parse_mode=ParseMode.MARKDOWN,
            )
            return ""
    else:
        curr_setting = sql.welcome_mutes(chat.id)
        reply = (
            f"\n Beri saya pengaturan!\nPilih salah satu dari: `off`/`no` atau `soft` atau `strong` saja! \n"
            f"Pengaturan saat ini: `{curr_setting}`"
        )
        msg.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        return ""


@run_async
@user_admin
@loggable
def clean_welcome(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user

    if not args:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text(
                "Saya harus menghapus pesan selamat datang yang berumur hingga dua hari."
            )
        else:
            update.effective_message.reply_text(
                "Saat ini saya tidak menghapus pesan selamat datang yang lama!"
            )
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text("Saya akan mencoba menghapus pesan selamat datang yang lama!")
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Telah toggled menyambut bersih <code>ON</code>."
        )
    elif args[0].lower() in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text("Saya tidak akan menghapus pesan selamat datang yang lama.")
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Telah toggled menyambut bersih <code>OFF</code>."
        )
    else:
        update.effective_message.reply_text("Saya mengerti 'on/yes' atau 'off/no' saja!")
        return ""


@run_async
def user_button(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    query = update.callback_query
    match = re.match(r"user_join_\((.+?)\)", query.data)
    message = update.effective_message
    join_user = int(match.group(1))

    if join_user == user.id:
        member_dict = VERIFIED_USER_WAITLIST.pop(user.id)
        member_dict["status"] = True
        VERIFIED_USER_WAITLIST.update({user.id: member_dict})
        query.answer(text="Uh! Anda seorang manusia, disuarakan!")
        bot.restrict_chat_member(
            chat.id,
            user.id,
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        )
        bot.deleteMessage(chat.id, message.message_id)
        if member_dict["should_welc"]:
            sent = send(
                member_dict["update"],
                member_dict["res"],
                member_dict["keyboard"],
                member_dict["backup_message"],
            )

            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

    else:
        query.answer(text="Anda tidak diizinkan melakukan ini!")


WELC_HELP_TXT = (
    "Pesan selamat datang/selamat tinggal grup Anda dapat dipersonalisasi dengan berbagai cara. Jika Anda menginginkan pesan"
    " untuk dibuat satu per satu, seperti pesan selamat datang default, Anda dapat menggunakan variabel *ini*:\n"
    " - `{first}`: ini mewakili nama *depan* pengguna\n"
    " - `{last}`: ni mewakili nama *belakang* pengguna. Default-nya adalah *nama depan* jika pengguna tidak memiliki "
    "nama belakang.\n"
    " - `{fullname}`: ini mewakili nama *lengkap* pengguna. Default-nya adalah *nama depan* jika pengguna tidak memiliki "
    "nama belakang.\n"
    " - `{username}`: ini mewakili *nama pengguna* pengguna. Secara default, *sebutan* pengguna "
    "first name if has no username.\n"
    " - `{mention}`: ini hanya *menyebutkan* pengguna - memberi tag mereka dengan nama depan mereka.\n"
    " - `{id}`: ini mewakili *id* pengguna\n"
    " - `{count}`: ini mewakili *nomor anggota* pengguna.\n"
    " - `{chatname}`: ini mewakili *nama obrolan saat ini*.\n"
    "\nSetiap variabel HARUS diapit oleh `{}` untuk diganti.\n"
    "Pesan selamat datang juga mendukung penurunan harga, sehingga Anda dapat membuat elemen apa pun bold/italic/code/links. "
    "Tombol juga didukung, sehingga Anda dapat membuat sambutan Anda terlihat luar biasa dengan beberapa tombol intro yang "
    "bagus.\n"
    f"Untuk membuat tombol yang menautkan ke aturan Anda, gunakan ini: `[Rules](buttonurl://t.me/{dispatcher.bot.username}?start=group_id)`. "
    "Cukup ganti `group_id` dengan id grup Anda, yang dapat diperoleh melalui /id, dan Anda baik-baik saja "
    "Pergilah. Perhatikan bahwa id grup biasanya diawali dengan tanda `-`; ini diperlukan, jadi tolong jangan "
    "dihapus.\n"
    "Jika Anda merasa senang, Anda bahkan dapat mengatur gambar/gif/video/pesan suara sebagai pesan selamat datang "
    "membalas media yang diinginkan, dan menelepon /setwelcome."
)

WELC_MUTE_HELP_TXT = (
    "Anda bisa mendapatkan bot untuk menonaktifkan orang baru yang bergabung dengan grup Anda dan karenanya mencegah robot spam membanjiri grup Anda. "
    "Opsi berikut dimungkinkan:\n"
    "- `/welcomemute soft`: rmembatasi anggota baru mengirim media selama 24 jam.\n"
    "- `/welcomemute strong`: membungkam anggota baru sampai mereka mengetuk tombol sehingga memverifikasi bahwa mereka manusia.\n"
    "- `/welcomemute off`: mematikan selamat datang.\n"
    "`Catatan` Mode kuat menendang pengguna dari obrolan jika mereka tidak memverifikasi dalam 160 detik. Mereka selalu bisa bergabung kembali"
)


@run_async
@user_admin
def welcome_help(bot: Bot, update: Update):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


@run_async
@user_admin
def welcome_mute_help(bot: Bot, update: Update):
    update.effective_message.reply_text(
        WELC_MUTE_HELP_TXT, parse_mode=ParseMode.MARKDOWN
    )


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
    return (
        "Obrolan ini memiliki preferensi selamat datang yang disetel ke `{}`.\n"
        "Ini preferensi selamat tinggal `{}`.".format(welcome_pref, goodbye_pref)
    )


__help__ = """
{}

*Admin saja:*
 - /welcome <on/off>: aktifkan/nonaktifkan pesan selamat datang
 - /welcome: menunjukkan pengaturan selamat datang saat ini.
 - /welcome noformat: menunjukkan pengaturan selamat datang saat ini, tanpa pemformatan - berguna untuk mendaur ulang pesan selamat datang Anda!
 - /goodbye -> penggunaan dan argumen yang sama seperti /welcome.
 - /setwelcome <beberapa teks>: setel pesan selamat datang khusus. Jika digunakan membalas media, gunakan media itu.
 - /setgoodbye <beberapa teks>: setel pesan selamat tinggal khusus. Jika digunakan membalas media, gunakan media itu.
 - /resetwelcome: setel ulang ke pesan selamat datang default.
 - /resetgoodbye: reset ke pesan selamat tinggal default.
 - /cleanwelcome <on/off>: Pada anggota baru, coba hapus pesan selamat datang sebelumnya untuk menghindari spamming pada obrolan.
 - /welcomemutehelp: memberikan informasi tentang pembungkaman selamat datang.
 - /welcomehelp: lihat lebih banyak informasi pemformatan untuk pesan selamat datang / selamat tinggal khusus.
""".format(
    WELC_HELP_TXT
)

NEW_MEM_HANDLER = MessageHandler(
    Filters.status_update.new_chat_members, new_member, pass_job_queue=True
)
LEFT_MEM_HANDLER = MessageHandler(Filters.status_update.left_chat_member, left_member)
WELC_PREF_HANDLER = CommandHandler(
    "welcome", welcome, pass_args=True, filters=Filters.group
)
GOODBYE_PREF_HANDLER = CommandHandler(
    "goodbye", goodbye, pass_args=True, filters=Filters.group
)
SET_WELCOME = CommandHandler("setwelcome", set_welcome, filters=Filters.group)
SET_GOODBYE = CommandHandler("setgoodbye", set_goodbye, filters=Filters.group)
RESET_WELCOME = CommandHandler("resetwelcome", reset_welcome, filters=Filters.group)
RESET_GOODBYE = CommandHandler("resetgoodbye", reset_goodbye, filters=Filters.group)
WELCOMEMUTE_HANDLER = CommandHandler(
    "welcomemute", welcomemute, pass_args=True, filters=Filters.group
)
CLEAN_WELCOME = CommandHandler(
    "cleanwelcome", clean_welcome, pass_args=True, filters=Filters.group
)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help)
WELCOME_MUTE_HELP = CommandHandler("welcomemutehelp", welcome_mute_help)
BUTTON_VERIFY_HANDLER = CallbackQueryHandler(user_button, pattern=r"user_join_")

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(WELCOME_HELP)
dispatcher.add_handler(WELCOMEMUTE_HANDLER)
dispatcher.add_handler(BUTTON_VERIFY_HANDLER)
dispatcher.add_handler(WELCOME_MUTE_HELP)

__mod_name__ = "Greetings"
__command_list__ = [
    "welcome",
    "goodbye",
    "setwelcome",
    "setgoodbye",
    "resetwelcome",
    "resetgoodbye",
    "welcomemute",
    "cleanwelcome",
    "welcomehelp",
    "welcomemutehelp",
]
__handlers__ = [
    NEW_MEM_HANDLER,
    LEFT_MEM_HANDLER,
    WELC_PREF_HANDLER,
    GOODBYE_PREF_HANDLER,
    SET_WELCOME,
    SET_GOODBYE,
    RESET_WELCOME,
    RESET_GOODBYE,
    CLEAN_WELCOME,
    WELCOME_HELP,
    WELCOMEMUTE_HANDLER,
    BUTTON_VERIFY_HANDLER,
    WELCOME_MUTE_HELP,
]
