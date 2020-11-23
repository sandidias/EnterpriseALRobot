from functools import wraps

from telegram import Bot, Chat, ChatMember, Update, ParseMode

from tg_bot import (
    dispatcher,
    DEL_CMDS,
    WHITELIST_USERS,
    SARDEGNA_USERS,
    SUPPORT_USERS,
    SUDO_USERS,
    DEV_USERS,
)


def is_whitelist_plus(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    return any(
        user_id in user
        for user in [
            WHITELIST_USERS,
            SARDEGNA_USERS,
            SUPPORT_USERS,
            SUDO_USERS,
            DEV_USERS,
        ]
    )


def is_support_plus(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    return user_id in SUPPORT_USERS or user_id in SUDO_USERS or user_id in DEV_USERS


def is_sudo_plus(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    return user_id in SUDO_USERS or user_id in DEV_USERS


def is_user_admin(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if (
        chat.type == "private"
        or user_id in SUDO_USERS
        or user_id in DEV_USERS
        or user_id in [777000, 1087968824]
        or chat.all_members_are_administrators
    ):
        return True

    if not member:
        member = chat.get_member(user_id)

    return member.status in ("administrator", "creator")


def is_bot_admin(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    if chat.type == "private" or chat.all_members_are_administrators:
        return True

    if not bot_member:
        bot_member = chat.get_member(bot_id)

    return bot_member.status in ("administrator", "creator")


def can_delete(chat: Chat, bot_id: int) -> bool:
    return chat.get_member(bot_id).can_delete_messages


def is_user_ban_protected(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if (
        chat.type == "private"
        or user_id in SUDO_USERS
        or user_id in DEV_USERS
        or user_id in WHITELIST_USERS
        or user_id in SARDEGNA_USERS
        or user_id in [777000, 1087968824]
        or chat.all_members_are_administrators
    ):
        return True

    if not member:
        member = chat.get_member(user_id)

    return member.status in ("administrator", "creator")


def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    member = chat.get_member(user_id)
    return member.status not in ("left", "kicked")


def dev_plus(func):
    @wraps(func)
    def is_dev_plus_func(bot: Bot, update: Update, *args, **kwargs):

        user = update.effective_user

        if user.id in DEV_USERS:
            return func(bot, update, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()
        else:
            update.effective_message.reply_text(
                "Ini adalah perintah terbatas pengembang."
                " Anda tidak memiliki izin untuk menjalankan ini."
            )

    return is_dev_plus_func


def sudo_plus(func):
    @wraps(func)
    def is_sudo_plus_func(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat

        if user and is_sudo_plus(chat, user.id):
            return func(bot, update, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()
        else:
            update.effective_message.reply_text(
                "Siapa bukan admin yang memberi tahu saya apa yang harus dilakukan? "
            )

    return is_sudo_plus_func


def support_plus(func):
    @wraps(func)
    def is_support_plus_func(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat

        if user and is_whitelist_plus(chat, user.id):
            return func(bot, update, *args, **kwargs)
        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()

    return is_support_plus_func


def whitelist_plus(func):
    @wraps(func)
    def is_whitelist_plus_func(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat

        if user and is_whitelist_plus(chat, user.id):
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                "Anda tidak memiliki akses untuk menggunakan ini./nCoba tanyakan master saya"
            )

    return is_whitelist_plus_func


def user_admin(func):
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat

        if user and is_user_admin(chat, user.id):
            return func(bot, update, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()
        else:
            update.effective_message.reply_text(
                "Siapa bukan admin yang memberi tahu saya apa yang harus dilakukan?"
            )

    return is_admin


def user_admin_no_reply(func):
    @wraps(func)
    def is_not_admin_no_reply(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat

        if user and is_user_admin(chat, user.id):
            return func(bot, update, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()

    return is_not_admin_no_reply


def user_not_admin(func):
    @wraps(func)
    def is_not_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat

        if user and not is_user_admin(chat, user.id):
            return func(bot, update, *args, **kwargs)
        elif not user:
            pass

    return is_not_admin


def bot_admin(func):
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            not_admin = "Saya bukan admin! - Baka"
        else:
            not_admin = f"Saya bukan admin di <b>{update_chat_title}</b>! - Baka"

        if is_bot_admin(chat, bot.id):
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text(not_admin, parse_mode=ParseMode.HTML)

    return is_admin


def bot_can_delete(func):
    @wraps(func)
    def delete_rights(bot: Bot, update: Update, *args, **kwargs):
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_delete = f"Saya tidak bisa menghapus pesan di sini!\nPastikan saya admin dan dapat menghapus pesan pengguna lain."
        else:
            cant_delete = f"Saya tidak bisa menghapus pesan di <b>{update_chat_title}</b>!\nPastikan saya admin dan dapat menghapus pesan pengguna lain di sana."

        if can_delete(chat, bot.id):
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text(cant_delete, parse_mode=ParseMode.HTML)

    return delete_rights


def can_pin(func):
    @wraps(func)
    def pin_rights(bot: Bot, update: Update, *args, **kwargs):
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_pin = (
                f"Saya tidak dapat memasang pin pada pesan di sini!\nPastikan saya admin dan dapat memasang pin pada pesan."
            )
        else:
            cant_pin = f"Saya tidak dapat memasang pin pada pesan <b>{update_chat_title}</b>!\nPastikan saya admin dan dapat menyematkan pesan di sana."

        if chat.get_member(bot.id).can_pin_messages:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text(cant_pin, parse_mode=ParseMode.HTML)

    return pin_rights


def can_promote(func):
    @wraps(func)
    def promote_rights(bot: Bot, update: Update, *args, **kwargs):
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_promote = f"Saya tidak dapat mempromosikan/menurunkan orang di sini!\nPastikan saya adalah admin dan dapat menunjuk admin baru."
        else:
            cant_promote = (
                f"Saya tidak dapat mempromosikan/menurunkan orang di <b>{update_chat_title}</b>!\n"
                f"Pastikan saya admin di sana dan dapat menunjuk admin baru."
            )

        if chat.get_member(bot.id).can_promote_members:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text(cant_promote, parse_mode=ParseMode.HTML)

    return promote_rights


def can_restrict(func):
    @wraps(func)
    def restrict_rights(bot: Bot, update: Update, *args, **kwargs):
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_restrict = f"Saya tidak dapat membatasi orang di sini!/nPastikan saya admin dan dapat membatasi pengguna."
        else:
            cant_restrict = f"Saya tidak dapat membatasi orang di <b>{update_chat_title}</b>!\nPastikan saya admin di sana dan dapat membatasi pengguna."

        if chat.get_member(bot.id).can_restrict_members:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                cant_restrict, parse_mode=ParseMode.HTML
            )

    return restrict_rights


def connection_status(func):
    @wraps(func)
    def connected_status(bot: Bot, update: Update, *args, **kwargs):
        conn = connected(
            bot,
            update,
            update.effective_chat,
            update.effective_user.id,
            need_admin=False,
        )

        if conn:
            chat = dispatcher.bot.getChat(conn)
            update.__setattr__("_effective_chat", chat)
            return func(bot, update, *args, **kwargs)
        else:
            if update.effective_message.chat.type == "private":
                update.effective_message.reply_text(
                    "Kirim /connect dalam grup yang Anda dan saya memiliki kesamaan terlebih dahulu."
                )
                return connected_status

            return func(bot, update, *args, **kwargs)

    return connected_status


# Workaround for circular import with connection.py
from tg_bot.modules import connection

connected = connection.connected
