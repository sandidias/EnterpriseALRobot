import random
import threading

from sqlalchemy import Column, String, Boolean, UnicodeText, Integer, BigInteger

from tg_bot.modules.helper_funcs.msg_types import Types
from tg_bot.modules.sql import SESSION, BASE

DEFAULT_WELCOME = "Hai {first}, apa kabar?"
DEFAULT_GOODBYE = "Selamat tinggal!"

DEFAULT_WELCOME_MESSAGES = [
    "{first} ada di sini!",
    "Siap pemain {first}",
    "Genos, {first} ada di sini.",
    "A liar {first} muncul.",
    "{first} datang seperti Singa!",
    "{first} telah bergabung dengan pesta Anda.",
    "{first} baru saja bergabung. Bisakah saya sembuh?",
    "{first} baru saja bergabung dalam obrolan - asdgfhak!",
    "{first} baru saja bergabung. Semuanya, terlihat sibuk!",
    "Selamat datang, {first}. Tetaplah sebentar dan dengarkan.",
    "Selamat datang, {first}. Kami mengharapkan Anda (͡ ° ͜ʖ ͡ °)",
    "Selamat datang, {first}. Kami harap Anda membawa pizza.",
    "Selamat datang, {first}. Tinggalkan senjatamu di dekat pintu.",
    "Swoooosh. {First} baru saja mendarat.",
    "Persiapkan dirimu. {First} baru saja bergabung dengan chat.",
    "{first} baru saja bergabung. Sembunyikan pisang Anda.",
    "{first} baru saja tiba. Sepertinya OP - tolong nerf.",
    "{first} baru saja masuk ke obrolan.",
    "A {first} telah muncul di obrolan.",
    "Besar {first} muncul!",
    "Di mana {first}? Dalam obrolan!",
    "{first} melompat ke obrolan. Kanguru !!",
    "{first} baru saja muncul. Pegang birku.",
    "Penantang mendekat! {first} telah muncul!",
    "Itu burung! Ini pesawat! Lupakan, ini hanya {first}.",
    "Ini {first}! Puji matahari! \O/",
    "Jangan pernah menyerah {first}. Tidak akan pernah mengecewakan {first}.",
    "Ha! {First} telah bergabung! Anda mengaktifkan kartu perangkap saya!",
    "Cheers, love! {first} ada di sini!",
    "Hei! Dengar! {first} telah bergabung!",
    "Kami sudah menunggumu {first}",
    "Berbahaya pergi sendiri, ambil {first}!",
    "{first} telah bergabung dengan obrolan! Ini sangat efektif!",
    "Cheers, love! {First} ada di sini!",
    "{first} ada di sini, seperti yang dinubuatkan.",
    "{first} telah tiba. Pesta selesai.",
    "{first} di sini untuk menendang pantat dan mengunyah permen karet. Dan {first} semua dari permen karet.",
    "Halo. Apakah ini {first} yang Anda cari?",
    "{first} telah bergabung. Tunggu sebentar dan dengarkan!",
    "Mawar itu merah, violet itu biru, {first} bergabung dalam obrolan ini denganmu",
    "Selamat datang {first}, Hindari Pukulan jika Anda bisa!",
    "Itu burung! Ini pesawat! - Tidak, ini {first}!",
    "{first} Bergabung! - Ok.",
    "Semua Salam {first}!",
    "Hai, {first}. Jangan mengintai, Hanya Penjahat yang melakukan itu.",
    "{first} telah bergabung dengan bus pertempuran.",
    "Penantang baru masuk!",
    "Baik!",
    "{first} baru saja masuk ke obrolan!",
    "Sesuatu baru saja jatuh dari langit! - oh, ini {first}.",
    "{first} Baru saja berteleportasi ke dalam obrolan!",
    "Hai, {first}, tunjukkan Lisensi Hunter Anda!",
    "Saya mencari bunga, oh tunggu dulu, ini {first}.",
    "Selamat datang {first}, Keluar bukanlah pilihan!",
    "Run Forest! .. Maksudku ... {first}.",
    "Hah?\nApakah seseorang dengan tingkat Bangsa baru saja bergabung?\nOh tunggu, baru saja {first}.",
    "Hei, {first}, pernah dengar King Engine?",
    "Hei, {first}, Kosongkan sakumu.",
    "Hei, {first} !, Apakah kamu kuat?",
    "Panggil Avengers! - {first} baru saja bergabung dengan obrolan.",
    "{first} bergabung. Anda harus membangun tiang tambahan.",
    "Ermagherd. {First} ada di sini.",
]
DEFAULT_GOODBYE_MESSAGES = [
    "{first} akan terlewat.",
    "{first} baru saja offline.",
    "{first} telah meninggalkan lobi.",
    "{first} telah meninggalkan klan.",
    "{first} telah meninggalkan permainan.",
    "{first} telah meninggalkan area tersebut.",
    "{first} keluar dari proses.",
    "Senang mengenalmu, {first}!",
    "Itu adalah waktu yang menyenangkan {first}.",
    "Kami berharap dapat bertemu Anda lagi segera, {first}.",
    "Saya tidak ingin mengucapkan selamat tinggal, {first}.",
    "Selamat tinggal {first}! Tebak siapa yang akan merindukanmu: ')",
    "Selamat tinggal {first}! Ini akan sepi tanpamu.",
    "Tolong jangan tinggalkan aku sendirian di tempat ini, {first}!",
    "Semoga berhasil menemukan pembawa pesan yang lebih baik dari kita, {first}!",
    "Kamu tahu kami akan merindukanmu {first}. Benar? Benar? Benar?",
    "Selamat, {first}! Anda resmi bebas dari kekacauan ini.",
    "{first}. Anda adalah lawan yang layak untuk dilawan.",
    "Kamu pergi, {first}? Yare Yare Daze.",
]


class Welcome(BASE):
    __tablename__ = "welcome_pref"
    chat_id = Column(String(14), primary_key=True)
    should_welcome = Column(Boolean, default=True)
    should_goodbye = Column(Boolean, default=True)

    custom_welcome = Column(
        UnicodeText, default=random.choice(DEFAULT_WELCOME_MESSAGES)
    )
    welcome_type = Column(Integer, default=Types.TEXT.value)

    custom_leave = Column(UnicodeText, default=random.choice(DEFAULT_GOODBYE_MESSAGES))
    leave_type = Column(Integer, default=Types.TEXT.value)

    clean_welcome = Column(BigInteger)

    def __init__(self, chat_id, should_welcome=True, should_goodbye=True):
        self.chat_id = chat_id
        self.should_welcome = should_welcome
        self.should_goodbye = should_goodbye

    def __repr__(self):
        return "<Chat {} should Welcome new users: {}>".format(
            self.chat_id, self.should_welcome
        )


class WelcomeButtons(BASE):
    __tablename__ = "welcome_urls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(14), primary_key=True)
    name = Column(UnicodeText, nullable=False)
    url = Column(UnicodeText, nullable=False)
    same_line = Column(Boolean, default=False)

    def __init__(self, chat_id, name, url, same_line=False):
        self.chat_id = str(chat_id)
        self.name = name
        self.url = url
        self.same_line = same_line


class GoodbyeButtons(BASE):
    __tablename__ = "leave_urls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(14), primary_key=True)
    name = Column(UnicodeText, nullable=False)
    url = Column(UnicodeText, nullable=False)
    same_line = Column(Boolean, default=False)

    def __init__(self, chat_id, name, url, same_line=False):
        self.chat_id = str(chat_id)
        self.name = name
        self.url = url
        self.same_line = same_line


class WelcomeMute(BASE):
    __tablename__ = "welcome_mutes"
    chat_id = Column(String(14), primary_key=True)
    welcomemutes = Column(UnicodeText, default=False)

    def __init__(self, chat_id, welcomemutes):
        self.chat_id = str(chat_id)  # ensure string
        self.welcomemutes = welcomemutes


class WelcomeMuteUsers(BASE):
    __tablename__ = "human_checks"
    user_id = Column(Integer, primary_key=True)
    chat_id = Column(String(14), primary_key=True)
    human_check = Column(Boolean)

    def __init__(self, user_id, chat_id, human_check):
        self.user_id = user_id  # ensure string
        self.chat_id = str(chat_id)
        self.human_check = human_check


Welcome.__table__.create(checkfirst=True)
WelcomeButtons.__table__.create(checkfirst=True)
GoodbyeButtons.__table__.create(checkfirst=True)
WelcomeMute.__table__.create(checkfirst=True)
WelcomeMuteUsers.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()
WELC_BTN_LOCK = threading.RLock()
LEAVE_BTN_LOCK = threading.RLock()
WM_LOCK = threading.RLock()


def welcome_mutes(chat_id):
    try:
        welcomemutes = SESSION.query(WelcomeMute).get(str(chat_id))
        if welcomemutes:
            return welcomemutes.welcomemutes
        return False
    finally:
        SESSION.close()


def set_welcome_mutes(chat_id, welcomemutes):
    with WM_LOCK:
        prev = SESSION.query(WelcomeMute).get((str(chat_id)))
        if prev:
            SESSION.delete(prev)
        welcome_m = WelcomeMute(str(chat_id), welcomemutes)
        SESSION.add(welcome_m)
        SESSION.commit()


def set_human_checks(user_id, chat_id):
    with INSERTION_LOCK:
        human_check = SESSION.query(WelcomeMuteUsers).get((user_id, str(chat_id)))
        if not human_check:
            human_check = WelcomeMuteUsers(user_id, str(chat_id), True)

        else:
            human_check.human_check = True

        SESSION.add(human_check)
        SESSION.commit()

        return human_check


def get_human_checks(user_id, chat_id):
    try:
        human_check = SESSION.query(WelcomeMuteUsers).get((user_id, str(chat_id)))
        if not human_check:
            return None
        human_check = human_check.human_check
        return human_check
    finally:
        SESSION.close()


def get_welc_mutes_pref(chat_id):
    welcomemutes = SESSION.query(WelcomeMute).get(str(chat_id))
    SESSION.close()

    if welcomemutes:
        return welcomemutes.welcomemutes

    return False


def get_welc_pref(chat_id):
    welc = SESSION.query(Welcome).get(str(chat_id))
    SESSION.close()
    if welc:
        return welc.should_welcome, welc.custom_welcome, welc.welcome_type
    else:
        # Welcome by default.
        return True, DEFAULT_WELCOME, Types.TEXT


def get_gdbye_pref(chat_id):
    welc = SESSION.query(Welcome).get(str(chat_id))
    SESSION.close()
    if welc:
        return welc.should_goodbye, welc.custom_leave, welc.leave_type
    else:
        # Welcome by default.
        return True, DEFAULT_GOODBYE, Types.TEXT


def set_clean_welcome(chat_id, clean_welcome):
    with INSERTION_LOCK:
        curr = SESSION.query(Welcome).get(str(chat_id))
        if not curr:
            curr = Welcome(str(chat_id))

        curr.clean_welcome = int(clean_welcome)

        SESSION.add(curr)
        SESSION.commit()


def get_clean_pref(chat_id):
    welc = SESSION.query(Welcome).get(str(chat_id))
    SESSION.close()

    if welc:
        return welc.clean_welcome

    return False


def set_welc_preference(chat_id, should_welcome):
    with INSERTION_LOCK:
        curr = SESSION.query(Welcome).get(str(chat_id))
        if not curr:
            curr = Welcome(str(chat_id), should_welcome=should_welcome)
        else:
            curr.should_welcome = should_welcome

        SESSION.add(curr)
        SESSION.commit()


def set_gdbye_preference(chat_id, should_goodbye):
    with INSERTION_LOCK:
        curr = SESSION.query(Welcome).get(str(chat_id))
        if not curr:
            curr = Welcome(str(chat_id), should_goodbye=should_goodbye)
        else:
            curr.should_goodbye = should_goodbye

        SESSION.add(curr)
        SESSION.commit()


def set_custom_welcome(chat_id, custom_welcome, welcome_type, buttons=None):
    if buttons is None:
        buttons = []

    with INSERTION_LOCK:
        welcome_settings = SESSION.query(Welcome).get(str(chat_id))
        if not welcome_settings:
            welcome_settings = Welcome(str(chat_id), True)

        if custom_welcome:
            welcome_settings.custom_welcome = custom_welcome
            welcome_settings.welcome_type = welcome_type.value

        else:
            welcome_settings.custom_welcome = DEFAULT_GOODBYE
            welcome_settings.welcome_type = Types.TEXT.value

        SESSION.add(welcome_settings)

        with WELC_BTN_LOCK:
            prev_buttons = (
                SESSION.query(WelcomeButtons)
                .filter(WelcomeButtons.chat_id == str(chat_id))
                .all()
            )
            for btn in prev_buttons:
                SESSION.delete(btn)

            for b_name, url, same_line in buttons:
                button = WelcomeButtons(chat_id, b_name, url, same_line)
                SESSION.add(button)

        SESSION.commit()


def get_custom_welcome(chat_id):
    welcome_settings = SESSION.query(Welcome).get(str(chat_id))
    ret = DEFAULT_WELCOME
    if welcome_settings and welcome_settings.custom_welcome:
        ret = welcome_settings.custom_welcome

    SESSION.close()
    return ret


def set_custom_gdbye(chat_id, custom_goodbye, goodbye_type, buttons=None):
    if buttons is None:
        buttons = []

    with INSERTION_LOCK:
        welcome_settings = SESSION.query(Welcome).get(str(chat_id))
        if not welcome_settings:
            welcome_settings = Welcome(str(chat_id), True)

        if custom_goodbye:
            welcome_settings.custom_leave = custom_goodbye
            welcome_settings.leave_type = goodbye_type.value

        else:
            welcome_settings.custom_leave = DEFAULT_GOODBYE
            welcome_settings.leave_type = Types.TEXT.value

        SESSION.add(welcome_settings)

        with LEAVE_BTN_LOCK:
            prev_buttons = (
                SESSION.query(GoodbyeButtons)
                .filter(GoodbyeButtons.chat_id == str(chat_id))
                .all()
            )
            for btn in prev_buttons:
                SESSION.delete(btn)

            for b_name, url, same_line in buttons:
                button = GoodbyeButtons(chat_id, b_name, url, same_line)
                SESSION.add(button)

        SESSION.commit()


def get_custom_gdbye(chat_id):
    welcome_settings = SESSION.query(Welcome).get(str(chat_id))
    ret = DEFAULT_GOODBYE
    if welcome_settings and welcome_settings.custom_leave:
        ret = welcome_settings.custom_leave

    SESSION.close()
    return ret


def get_welc_buttons(chat_id):
    try:
        return (
            SESSION.query(WelcomeButtons)
            .filter(WelcomeButtons.chat_id == str(chat_id))
            .order_by(WelcomeButtons.id)
            .all()
        )
    finally:
        SESSION.close()


def get_gdbye_buttons(chat_id):
    try:
        return (
            SESSION.query(GoodbyeButtons)
            .filter(GoodbyeButtons.chat_id == str(chat_id))
            .order_by(GoodbyeButtons.id)
            .all()
        )
    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_LOCK:
        chat = SESSION.query(Welcome).get(str(old_chat_id))
        if chat:
            chat.chat_id = str(new_chat_id)

        with WELC_BTN_LOCK:
            chat_buttons = (
                SESSION.query(WelcomeButtons)
                .filter(WelcomeButtons.chat_id == str(old_chat_id))
                .all()
            )
            for btn in chat_buttons:
                btn.chat_id = str(new_chat_id)

        with LEAVE_BTN_LOCK:
            chat_buttons = (
                SESSION.query(GoodbyeButtons)
                .filter(GoodbyeButtons.chat_id == str(old_chat_id))
                .all()
            )
            for btn in chat_buttons:
                btn.chat_id = str(new_chat_id)

        SESSION.commit()
