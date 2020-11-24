import html
import re

import telegram
from telegram import Bot, Update
from telegram import ParseMode, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    DispatcherHandlerStop,
    run_async,
)
from telegram.utils.helpers import escape_markdown

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin, connection_status
from tg_bot.modules.helper_funcs.extraction import extract_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import build_keyboard
from tg_bot.modules.helper_funcs.string_handling import (
    split_quotes,
    button_markdown_parser,
)
from tg_bot.modules.sql import cust_filters_sql as sql

HANDLER_GROUP = 10


@run_async
@connection_status
def list_handlers(bot: Bot, update: Update):
    chat = update.effective_chat
    all_handlers = sql.get_chat_triggers(chat.id)

    update_chat_title = chat.title
    message_chat_title = update.effective_message.chat.title

    if update_chat_title == message_chat_title:
        BASIC_FILTER_STRING = "<b>Filter di obrolan ini:</b>\n"
    else:
        BASIC_FILTER_STRING = f"<b>Filter masuk {update_chat_title}</b>:\n"

    if not all_handlers:
        if update_chat_title == message_chat_title:
            update.effective_message.reply_text("Tidak ada filter yang aktif di sini!")
        else:
            update.effective_message.reply_text(
                f"Tidak ada filter yang aktif di <b>{update_chat_title}</b>!",
                parse_mode=telegram.ParseMode.HTML,
            )
        return

    filter_list = ""
    for keyword in all_handlers:
        entry = f" - {escape_markdown(keyword)}\n"
        if (
            len(entry) + len(filter_list) + len(BASIC_FILTER_STRING)
            > telegram.MAX_MESSAGE_LENGTH
        ):
            filter_list = BASIC_FILTER_STRING + html.escape(filter_list)
            update.effective_message.reply_text(
                filter_list, parse_mode=telegram.ParseMode.HTML
            )
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == BASIC_FILTER_STRING:
        filter_list = BASIC_FILTER_STRING + html.escape(filter_list)
        update.effective_message.reply_text(
            filter_list, parse_mode=telegram.ParseMode.HTML
        )


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@connection_status
@user_admin
def filters(bot: Bot, update: Update):
    chat = update.effective_chat
    msg = update.effective_message
    args = msg.text.split(None, 1)

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])
    if len(extracted) < 1:
        return
    # set trigger -> lower, so as to avoid adding duplicate filters with different cases
    keyword = extracted[0].lower()

    is_sticker = False
    is_document = False
    is_image = False
    is_voice = False
    is_audio = False
    is_video = False
    buttons = []

    # determine what the contents of the filter are - text, image, sticker, etc
    if len(extracted) >= 2:
        offset = len(extracted[1]) - len(
            msg.text
        )  # set correct offset relative to command + notename
        content, buttons = button_markdown_parser(
            extracted[1], entities=msg.parse_entities(), offset=offset
        )
        content = content.strip()
        if not content:
            msg.reply_text(
                "Tidak ada pesan catatan - Anda tidak bisa HANYA memiliki tombol, Anda perlu pesan untuk menyertainya!"
            )
            return

    elif msg.reply_to_message and msg.reply_to_message.sticker:
        content = msg.reply_to_message.sticker.file_id
        is_sticker = True

    elif msg.reply_to_message and msg.reply_to_message.document:
        content = msg.reply_to_message.document.file_id
        is_document = True

    elif msg.reply_to_message and msg.reply_to_message.photo:
        content = msg.reply_to_message.photo[-1].file_id  # last elem = best quality
        is_image = True

    elif msg.reply_to_message and msg.reply_to_message.audio:
        content = msg.reply_to_message.audio.file_id
        is_audio = True

    elif msg.reply_to_message and msg.reply_to_message.voice:
        content = msg.reply_to_message.voice.file_id
        is_voice = True

    elif msg.reply_to_message and msg.reply_to_message.video:
        content = msg.reply_to_message.video.file_id
        is_video = True

    else:
        msg.reply_text("Anda tidak menentukan harus membalas dengan apa!")
        return

    # Add the filter
    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, HANDLER_GROUP)

    sql.add_filter(
        chat.id,
        keyword,
        content,
        is_sticker,
        is_document,
        is_image,
        is_audio,
        is_voice,
        is_video,
        buttons,
    )

    msg.reply_text("Handler '{}' added!".format(keyword))
    raise DispatcherHandlerStop


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@connection_status
@user_admin
def stop_filter(bot: Bot, update: Update):
    chat = update.effective_chat
    msg = update.effective_message
    args = msg.text.split(None, 1)

    if len(args) < 2:
        return

    chat_filters = sql.get_chat_triggers(chat.id)

    if not chat_filters:
        msg.reply_text("Tidak ada filter yang aktif di sini!")
        return

    for keyword in chat_filters:
        if keyword == args[1]:
            sql.remove_filter(chat.id, args[1])
            msg.reply_text("Ya, saya akan berhenti menjawab itu.")
            raise DispatcherHandlerStop

    msg.reply_text("Itu bukan filter saat ini - jalankan /filters untuk semua filter aktif.")


@run_async
def reply_filter(bot: Bot, update: Update):
    chat = update.effective_chat
    message = update.effective_message
    to_match = extract_text(message)

    if not to_match:
        return

    chat_filters = sql.get_chat_triggers(chat.id)
    for keyword in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            filt = sql.get_filter(chat.id, keyword)
            if filt.is_sticker:
                message.reply_sticker(filt.reply)
            elif filt.is_document:
                message.reply_document(filt.reply)
            elif filt.is_image:
                message.reply_photo(filt.reply)
            elif filt.is_audio:
                message.reply_audio(filt.reply)
            elif filt.is_voice:
                message.reply_voice(filt.reply)
            elif filt.is_video:
                message.reply_video(filt.reply)
            elif filt.has_markdown:
                buttons = sql.get_buttons(chat.id, filt.keyword)
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                try:
                    message.reply_text(
                        filt.reply,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True,
                        reply_markup=keyboard,
                    )
                except BadRequest as excp:
                    if excp.message == "Unsupported url protocol":
                        message.reply_text(
                            "Anda tampaknya mencoba menggunakan protokol url yang tidak didukung. Telegram "
                            "tidak mendukung tombol untuk beberapa protokol, seperti tg://. Coba ulangi "
                            "lagi."
                        )
                    elif excp.message == "Pesan balasan tidak ditemukan":
                        bot.send_message(
                            chat.id,
                            filt.reply,
                            parse_mode=ParseMode.MARKDOWN,
                            disable_web_page_preview=True,
                            reply_markup=keyboard,
                        )
                    else:
                        message.reply_text(
                            "Catatan ini tidak dapat dikirim, karena formatnya salah. Tanya  "
                            "master saya, mungkin ada yang bisa dia lakukan!"
                        )
                        LOGGER.warning(
                            "Message %s could not be parsed", str(filt.reply)
                        )
                        LOGGER.exception(
                            "Could not parse filter %s in chat %s",
                            str(filt.keyword),
                            str(chat.id),
                        )

            else:
                # LEGACY - all new filters will have has_markdown set to True.
                message.reply_text(filt.reply)
            break


def __stats__():
    return "{} filters, across {} chats.".format(sql.num_filters(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    cust_filters = sql.get_chat_triggers(chat_id)
    return "Saat ini ada `{}` filter khusus di sini.".format(len(cust_filters))


__help__ = """
 - /filters: daftar semua filter aktif dalam obrolan ini.

*Hanya Admin:*
 - /filter <keyword> <balas pesan>: tambahkan filter ke obrolan ini. Bot sekarang akan membalas pesan itu setiap kali 'kata kunci'\
disebutkan. Jika Anda membalas stiker dengan kata kunci, bot akan membalas dengan stiker itu. CATATAN: semua filter \
kata kunci menggunakan huruf kecil. Jika Anda ingin kata kunci Anda menjadi kalimat, gunakan tanda kutip. misal: /filter "hey there" Bagaimana kabarmu \
doin?
 - /stop <filter keyword>: hentikan filter itu.
"""

FILTER_HANDLER = CommandHandler("filter", filters)
STOP_HANDLER = CommandHandler("stop", stop_filter)
LIST_HANDLER = DisableAbleCommandHandler("filters", list_handlers, admin_ok=True)
CUST_FILTER_HANDLER = MessageHandler(CustomFilters.has_text, reply_filter)

dispatcher.add_handler(FILTER_HANDLER)
dispatcher.add_handler(STOP_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(CUST_FILTER_HANDLER, HANDLER_GROUP)

__mod_name__ = "Filter"
__handlers__ = [
    FILTER_HANDLER,
    STOP_HANDLER,
    LIST_HANDLER,
    (CUST_FILTER_HANDLER, HANDLER_GROUP),
]
