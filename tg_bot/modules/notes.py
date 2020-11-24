import re
from io import BytesIO
from typing import Optional, List

from telegram import MAX_MESSAGE_LENGTH, ParseMode, InlineKeyboardMarkup
from telegram import Message, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, RegexHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.notes_sql as sql
from tg_bot import dispatcher, MESSAGE_DUMP, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin, connection_status
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.msg_types import get_note_type

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")

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


# Do not async
@connection_status
def get(bot, update, notename, show_none=True, no_format=False):
    chat_id = update.effective_chat.id
    note = sql.get_note(chat_id, notename)
    message = update.effective_message  # type: Optional[Message]

    if note:
        # If we're replying to a message, reply to that message (unless it's an error)
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id
        else:
            reply_id = message.message_id

        if note.is_reply:
            if MESSAGE_DUMP:
                try:
                    bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=MESSAGE_DUMP,
                        message_id=note.value,
                    )
                except BadRequest as excp:
                    if excp.message == "Message to forward not found":
                        message.reply_text(
                            "Pesan ini sepertinya telah hilang - Saya akan menghapusnya "
                            "dari daftar catatan Anda."
                        )
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
            else:
                try:
                    bot.forward_message(
                        chat_id=chat_id, from_chat_id=chat_id, message_id=note.value
                    )
                except BadRequest as excp:
                    if excp.message == "Message to forward not found":
                        message.reply_text(
                            "Sepertinya pengirim asli catatan ini telah dihapus "
                            "pesan mereka - maaf! Minta admin bot Anda untuk mulai menggunakan file "
                            "pesan dump untuk menghindari ini. Saya akan menghapus catatan ini dari "
                            "catatan Anda yang disimpan."
                        )
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
        else:
            text = note.value
            keyb = []
            parseMode = ParseMode.MARKDOWN
            buttons = sql.get_buttons(chat_id, notename)
            if no_format:
                parseMode = None
                text += revert_buttons(buttons)
            else:
                keyb = build_keyboard(buttons)

            keyboard = InlineKeyboardMarkup(keyb)

            try:
                if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                    bot.send_message(
                        chat_id,
                        text,
                        reply_to_message_id=reply_id,
                        parse_mode=parseMode,
                        disable_web_page_preview=True,
                        reply_markup=keyboard,
                    )
                else:
                    ENUM_FUNC_MAP[note.msgtype](
                        chat_id,
                        note.file,
                        caption=text,
                        reply_to_message_id=reply_id,
                        parse_mode=parseMode,
                        disable_web_page_preview=True,
                        reply_markup=keyboard,
                    )

            except BadRequest as excp:
                if excp.message == "Entity_mention_user_invalid":
                    message.reply_text(
                        "Sepertinya Anda mencoba menyebut seseorang yang belum pernah saya lihat sebelumnya. Jika Anda benar-benar "
                        "ingin menyebutkan mereka, meneruskan salah satu pesan mereka kepada saya, dan saya akan bisa "
                        "untuk menandai mereka!"
                    )
                elif FILE_MATCHER.match(note.value):
                    message.reply_text(
                        "Catatan ini adalah file yang diimpor dengan tidak benar dari bot lain - Saya tidak dapat menggunakan "
                        "Itu. Jika Anda benar-benar membutuhkannya, Anda harus menyimpannya lagi. Di "
                        "sementara itu, saya akan menghapusnya dari daftar catatan Anda."
                    )
                    sql.rm_note(chat_id, notename)
                else:
                    message.reply_text(
                        "Catatan ini tidak dapat dikirim, karena formatnya salah."
                    )
                    LOGGER.exception(
                        "Could not parse message #%s in chat %s", notename, str(chat_id)
                    )
                    LOGGER.warning("Message was: %s", str(note.value))
        return
    elif show_none:
        message.reply_text("Catatan ini tidak ada")


@run_async
@connection_status
def cmd_get(bot: Bot, update: Update, args: List[str]):
    if len(args) >= 2 and args[1].lower() == "noformat":
        get(bot, update, args[0], show_none=True, no_format=True)
    elif len(args) >= 1:
        get(bot, update, args[0], show_none=True)
    else:
        update.effective_message.reply_text("Dapatkan rekt")


@run_async
@connection_status
def hash_get(bot: Bot, update: Update):
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:]
    get(bot, update, no_hash, show_none=False)


@run_async
@user_admin
@connection_status
def save(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]

    note_name, text, data_type, content, buttons = get_note_type(msg)

    if data_type is None:
        msg.reply_text("Teman, tidak ada catatan")
        return

    sql.add_note_to_db(
        chat_id, note_name, text, data_type, buttons=buttons, file=content
    )

    msg.reply_text(
        f"Yey! Ditambahkan {note_name}.\nDapatkan dengan /get {note_name}, or #{note_name}"
    )

    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
        if text:
            msg.reply_text(
                "Sepertinya Anda mencoba menyimpan pesan dari bot. Sayangnya, "
                "bot tidak dapat meneruskan pesan bot, jadi saya tidak dapat menyimpan pesan persisnya. "
                "\nSaya akan menyimpan semua teks yang saya bisa, tetapi jika Anda menginginkan lebih, Anda harus melakukannya "
                "teruskan pesan itu sendiri, lalu simpan."
            )
        else:
            msg.reply_text(
                "Bot agak cacat oleh telegram, menyulitkan bot "
                "berinteraksi dengan bot lain, jadi saya tidak dapat menyimpan pesan ini "
                "seperti yang biasanya saya lakukan - apakah Anda keberatan meneruskannya dan "
                "lalu menyimpan pesan baru itu? Terima kasih!"
            )
        return


@run_async
@user_admin
@connection_status
def clear(bot: Bot, update: Update, args: List[str]):
    chat_id = update.effective_chat.id
    if len(args) >= 1:
        notename = args[0]

        if sql.rm_note(chat_id, notename):
            update.effective_message.reply_text("Catatan berhasil dihapus.")
        else:
            update.effective_message.reply_text("Itu bukan catatan di database saya!")


@run_async
@connection_status
def list_notes(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    note_list = sql.get_all_chat_notes(chat_id)

    msg = "*Catatan dalam obrolan:*\n"
    for note in note_list:
        note_name = escape_markdown(f" - {note.name}\n")
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if msg == "*Catatan dalam obrolan:*\n":
        update.effective_message.reply_text("Tidak ada catatan dalam obrolan ini!")

    elif len(msg) != 0:
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def __import_data__(chat_id, data):
    failures = []
    for notename, notedata in data.get("extra", {}).items():
        match = FILE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            notedata = notedata[match.end() :].strip()
            if notedata:
                sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(
                chat_id,
                document=output,
                filename="failed_imports.txt",
                caption="File / foto ini gagal diimpor karena aslinya "
                "dari bot lain. Ini adalah batasan API telegram, dan tidak bisa "
                "dihindari. Maaf untuk ketidaknyamanannya!",
            )


def __stats__():
    return f"{sql.num_notes()} notes, across {sql.num_chats()} chats."


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return f"Ada `{len(notes)}` catatan dalam obrolan ini."


__help__ = """
 - /get <notename>: dapatkan catatan dengan nama note ini
 - #<notename>: sama /get
 - /notes atau /saved: daftar semua catatan yang disimpan dalam obrolan ini
Jika Anda ingin mengambil konten catatan tanpa pemformatan apa pun, gunakan `/get <notename> noformat`. Ini bisa \
berguna saat memperbarui catatan saat ini.
*Admin saja:*
 - /save <notename> <notedata>: menyimpan noteata sebagai catatan dengan nama notename
Tombol dapat ditambahkan ke catatan dengan menggunakan sintaks tautan penurunan harga standar - tautan seharusnya hanya diawali dengan \
`buttonurl:` bagian, seperti itu: `[Contoh](tombolurl:contoh.com)`. Periksa /markdownhelp untuk info lebih lanjut.
 - /save <notename>: simpan pesan yang dibalas sebagai catatan dengan nama notename
 - /clear <notename>: hapus catatan dengan nama ini
"""

__mod_name__ = "Notes"

GET_HANDLER = CommandHandler("get", cmd_get, pass_args=True)
HASH_GET_HANDLER = RegexHandler(r"^#[^\s]+", hash_get)

SAVE_HANDLER = CommandHandler("save", save)
DELETE_HANDLER = CommandHandler("clear", clear, pass_args=True)

LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"], list_notes, admin_ok=True)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
