\
import os
import sqlite3
import logging
from pathlib import Path
from html import escape

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB = Path(os.getenv("DB_PATH", str(Path(__file__).with_name("tindraven.sqlite3"))))

LANG, NAME, AGE, CITY, BIO_CHOICE, BIO, PHOTO, CONFIRM, EDIT, EDIT_VALUE = range(10)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Bütün istifadəçi mesajları seçilmiş dildə göstərilir.
T = {
    "az": {
        "welcome": "TindraVen-ə xoş gəlmisiniz! ❤️ Dilinizi seçin:",
        "name": "Adınızı yazın:",
        "age": "Yaşınızı yazın (yalnız 18+):",
        "under": "TindraVen yalnız 18 yaş və yuxarı şəxslər üçündür.",
        "city": "Şəhərinizi və ya ərazinizi yazın. Dəqiq ev ünvanınızı yazmayın:",
        "bioq": "Özünüz haqqında əlavə məlumat vermək istəyirsiniz?",
        "bio": "Özünüz haqqında qısa məlumat yazın (maksimum 500 simvol):",
        "photo": "Profil şəklinizi göndərin:",
        "confirm": "Bu profillə davam edək?",
        "yes": "Bəli", "no": "Xeyr", "edit": "Redaktə et",
        "delete": "Profili sil", "saved": "Profiliniz təsdiqləndi! ❤️",
        "editq": "Nəyi dəyişmək istəyirsiniz?",
        "namekey": "Ad", "agekey": "Yaş", "citykey": "Şəhər",
        "biokey": "Haqqımda", "photokey": "Şəkil",
        "askname": "Yeni adınızı yazın:", "askage": "Yeni yaşınızı yazın (18+):",
        "askcity": "Yeni şəhərinizi yazın:", "askbio": "Yeni məlumatınızı yazın:",
        "askphoto": "Yeni şəklinizi göndərin:",
        "badage": "Yaşı rəqəmlə yazın. Yalnız 18+ qəbul edilir.",
        "bad": "Zəhmət olmasa, düzgün məlumat göndərin.",
        "profile": "Profiliniz", "about": "Haqqımda",
        "none": "Əlavə məlumat yoxdur", "deleted": "Profil silindi. /start yazın.",
        "need": "Profiliniz yoxdur. /start yazın.",
        "help": "Komandalar: /start, /profile, /delete, /help, /cancel",
        "deleteq": "Profilinizi silmək istəyirsiniz?",
        "cancel": "Əməliyyat dayandırıldı.",
        "languages": ["Azərbaycan", "English", "Turkish", "Russian", "Indonesian"],
    },
    "en": {
        "welcome": "Welcome to TindraVen! ❤️ Please choose your language:",
        "name": "Enter your name:",
        "age": "Enter your age (18+ only):",
        "under": "TindraVen is only for people aged 18 and over.",
        "city": "Enter your city or area. Do not share your exact home address:",
        "bioq": "Would you like to add information about yourself?",
        "bio": "Write a short description (maximum 500 characters):",
        "photo": "Send your profile photo:",
        "confirm": "Would you like to continue with this profile?",
        "yes": "Yes", "no": "No", "edit": "Edit profile",
        "delete": "Delete profile", "saved": "Your profile is confirmed! ❤️",
        "editq": "What would you like to change?",
        "namekey": "Name", "agekey": "Age", "citykey": "City",
        "biokey": "About me", "photokey": "Photo",
        "askname": "Enter your new name:", "askage": "Enter your new age (18+):",
        "askcity": "Enter your new city:", "askbio": "Enter your new description:",
        "askphoto": "Send your new photo:",
        "badage": "Enter a numeric age. Only people aged 18+ are accepted.",
        "bad": "Please send valid information.",
        "profile": "Your profile", "about": "About me",
        "none": "No extra information", "deleted": "Profile deleted. Send /start.",
        "need": "You do not have a profile. Send /start.",
        "help": "Commands: /start, /profile, /delete, /help, /cancel",
        "deleteq": "Do you want to delete your profile?",
        "cancel": "Operation cancelled.",
        "languages": ["Azərbaycan", "English", "Turkish", "Russian", "Indonesian"],
    },
    "tr": {
        "welcome": "TindraVen'e hoş geldiniz! ❤️ Dilinizi seçin:",
        "name": "Adınızı yazın:", "age": "Yaşınızı yazın (yalnızca 18+):",
        "under": "TindraVen yalnızca 18 yaş ve üzeri kişiler içindir.",
        "city": "Şehrinizi veya bölgenizi yazın. Açık ev adresinizi paylaşmayın:",
        "bioq": "Kendiniz hakkında ek bilgi vermek ister misiniz?",
        "bio": "Kendiniz hakkında kısa bir açıklama yazın (maks. 500 karakter):",
        "photo": "Profil fotoğrafınızı gönderin:",
        "confirm": "Bu profille devam edelim mi?",
        "yes": "Evet", "no": "Hayır", "edit": "Profili düzenle",
        "delete": "Profili sil", "saved": "Profiliniz onaylandı! ❤️",
        "editq": "Neyi değiştirmek istersiniz?",
        "namekey": "Ad", "agekey": "Yaş", "citykey": "Şehir",
        "biokey": "Hakkımda", "photokey": "Fotoğraf",
        "askname": "Yeni adınızı yazın:", "askage": "Yeni yaşınızı yazın (18+):",
        "askcity": "Yeni şehrinizi yazın:", "askbio": "Yeni açıklamanızı yazın:",
        "askphoto": "Yeni fotoğrafınızı gönderin:",
        "badage": "Yaşı rakamla yazın. Yalnızca 18+.",
        "bad": "Lütfen geçerli bilgi gönderin.",
        "profile": "Profiliniz", "about": "Hakkımda",
        "none": "Ek bilgi yok", "deleted": "Profil silindi. /start yazın.",
        "need": "Profiliniz yok. /start yazın.",
        "help": "Komutlar: /start, /profile, /delete, /help, /cancel",
        "deleteq": "Profilinizi silmek istiyor musunuz?",
        "cancel": "İşlem iptal edildi.",
        "languages": ["Azərbaycan", "English", "Turkish", "Russian", "Indonesian"],
    },
    "ru": {
        "welcome": "Добро пожаловать в TindraVen! ❤️ Выберите язык:",
        "name": "Введите имя:", "age": "Введите возраст (только 18+):",
        "under": "TindraVen предназначен только для пользователей от 18 лет.",
        "city": "Укажите город или район. Не указывайте точный домашний адрес:",
        "bioq": "Хотите добавить информацию о себе?",
        "bio": "Кратко расскажите о себе (до 500 символов):",
        "photo": "Отправьте фото профиля:",
        "confirm": "Продолжить с этим профилем?",
        "yes": "Да", "no": "Нет", "edit": "Изменить профиль",
        "delete": "Удалить профиль", "saved": "Профиль подтверждён! ❤️",
        "editq": "Что хотите изменить?",
        "namekey": "Имя", "agekey": "Возраст", "citykey": "Город",
        "biokey": "О себе", "photokey": "Фото",
        "askname": "Введите новое имя:", "askage": "Введите новый возраст (18+):",
        "askcity": "Введите новый город:", "askbio": "Введите новое описание:",
        "askphoto": "Отправьте новое фото:",
        "badage": "Введите возраст цифрами. Только 18+.",
        "bad": "Пожалуйста, отправьте корректные данные.",
        "profile": "Ваш профиль", "about": "О себе",
        "none": "Нет дополнительной информации", "deleted": "Профиль удалён. Отправьте /start.",
        "need": "Профиля нет. Отправьте /start.",
        "help": "Команды: /start, /profile, /delete, /help, /cancel",
        "deleteq": "Удалить профиль?",
        "cancel": "Операция отменена.",
        "languages": ["Azərbaycan", "English", "Turkish", "Russian", "Indonesian"],
    },
    "id": {
        "welcome": "Selamat datang di TindraVen! ❤️ Pilih bahasa Anda:",
        "name": "Masukkan nama Anda:", "age": "Masukkan usia Anda (hanya 18+):",
        "under": "TindraVen hanya untuk pengguna berusia 18 tahun ke atas.",
        "city": "Masukkan kota atau area. Jangan bagikan alamat rumah lengkap:",
        "bioq": "Ingin menambahkan informasi tentang diri Anda?",
        "bio": "Tulis deskripsi singkat (maksimal 500 karakter):",
        "photo": "Kirim foto profil Anda:",
        "confirm": "Lanjutkan dengan profil ini?",
        "yes": "Ya", "no": "Tidak", "edit": "Edit profil",
        "delete": "Hapus profil", "saved": "Profil Anda dikonfirmasi! ❤️",
        "editq": "Apa yang ingin Anda ubah?",
        "namekey": "Nama", "agekey": "Usia", "citykey": "Kota",
        "biokey": "Tentang saya", "photokey": "Foto",
        "askname": "Masukkan nama baru:", "askage": "Masukkan usia baru (18+):",
        "askcity": "Masukkan kota baru:", "askbio": "Masukkan deskripsi baru:",
        "askphoto": "Kirim foto baru:",
        "badage": "Masukkan usia dengan angka. Hanya 18+.",
        "bad": "Silakan kirim informasi yang valid.",
        "profile": "Profil Anda", "about": "Tentang saya",
        "none": "Tidak ada info tambahan", "deleted": "Profil dihapus. Kirim /start.",
        "need": "Anda belum memiliki profil. Kirim /start.",
        "help": "Perintah: /start, /profile, /delete, /help, /cancel",
        "deleteq": "Hapus profil Anda?",
        "cancel": "Operasi dibatalkan.",
        "languages": ["Azərbaycan", "English", "Turkish", "Russian", "Indonesian"],
    },
}

LANG_CODES = ["az", "en", "tr", "ru", "id"]
LANG_NAMES = ["🇦🇿 Azərbaycan", "🇬🇧 English", "🇹🇷 Turkish",
              "🇷🇺 Russian", "🇮🇩 Indonesian"]


def db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            language TEXT NOT NULL DEFAULT 'en',
            name TEXT,
            age INTEGER,
            city TEXT,
            bio TEXT DEFAULT '',
            photo TEXT,
            confirmed INTEGER DEFAULT 0
        )
        """)


def get_profile(uid):
    with db() as c:
        return c.execute(
            "SELECT * FROM profiles WHERE user_id=?", (uid,)
        ).fetchone()


def save(uid, field, value):
    allowed = {"language", "name", "age", "city", "bio", "photo", "confirmed"}
    if field not in allowed:
        raise ValueError("Invalid field")
    with db() as c:
        c.execute(
            f"UPDATE profiles SET {field}=? WHERE user_id=?",
            (value, uid),
        )


def ensure(uid, language):
    with db() as c:
        c.execute(
            "INSERT OR IGNORE INTO profiles(user_id, language) VALUES (?, ?)",
            (uid, language),
        )


def language(context):
    return context.user_data.get("language", "en")


def tr(context, key):
    return T[language(context)].get(key, T["en"].get(key, key))


def language_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(LANG_NAMES[0], callback_data="lang:az"),
         InlineKeyboardButton(LANG_NAMES[1], callback_data="lang:en")],
        [InlineKeyboardButton(LANG_NAMES[2], callback_data="lang:tr"),
         InlineKeyboardButton(LANG_NAMES[3], callback_data="lang:ru")],
        [InlineKeyboardButton(LANG_NAMES[4], callback_data="lang:id")],
    ])


def yes_no(context, prefix):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(tr(context, "yes"), callback_data=f"{prefix}:yes"),
        InlineKeyboardButton(tr(context, "no"), callback_data=f"{prefix}:no"),
    ]])


def profile_text(p, context):
    x = T[p["language"]]
    return (
        f"<b>{escape(x['profile'])}</b>\n"
        f"{escape(x['namekey'])}: {escape(str(p['name'] or ''))}\n"
        f"{escape(x['agekey'])}: {p['age']}\n"
        f"{escape(x['citykey'])}: {escape(str(p['city'] or ''))}\n"
        f"{escape(x['about'])}: {escape(str(p['bio'] or x['none']))}"
    )


async def show_profile(chat_id, uid, context):
    p = get_profile(uid)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(tr(context, "yes"), callback_data="confirm:yes"),
        InlineKeyboardButton(tr(context, "no"), callback_data="confirm:no"),
    ]])
    await context.bot.send_photo(
        chat_id=chat_id,
        photo=p["photo"],
        caption=profile_text(p, context),
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.effective_message.reply_text(
        T["en"]["welcome"], reply_markup=language_keyboard()
    )
    return LANG


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    code = q.data.split(":")[1]
    context.user_data["language"] = code
    ensure(q.from_user.id, code)
    save(q.from_user.id, "language", code)

    p = get_profile(q.from_user.id)
    if p and p["confirmed"] and p["name"] and p["photo"]:
        await q.edit_message_text(T[code]["saved"])
        return ConversationHandler.END

    await q.edit_message_text(T[code]["name"])
    return NAME


async def name_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = (update.effective_message.text or "").strip()
    if not value or len(value) > 50:
        await update.effective_message.reply_text(tr(context, "bad"))
        return NAME
    uid = update.effective_user.id
    ensure(uid, language(context))
    save(uid, "name", value)
    await update.effective_message.reply_text(tr(context, "age"))
    return AGE


async def age_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int((update.effective_message.text or "").strip())
    except ValueError:
        await update.effective_message.reply_text(tr(context, "badage"))
        return AGE

    if age < 18:
        await update.effective_message.reply_text(tr(context, "under"))
        with db() as c:
            c.execute("DELETE FROM profiles WHERE user_id=?",
                      (update.effective_user.id,))
        context.user_data.clear()
        return ConversationHandler.END

    if age > 120:
        await update.effective_message.reply_text(tr(context, "badage"))
        return AGE

    save(update.effective_user.id, "age", age)
    await update.effective_message.reply_text(tr(context, "city"))
    return CITY


async def city_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = (update.effective_message.text or "").strip()
    if not value or len(value) > 100:
        await update.effective_message.reply_text(tr(context, "bad"))
        return CITY
    save(update.effective_user.id, "city", value)
    await update.effective_message.reply_text(
        tr(context, "bioq"), reply_markup=yes_no(context, "biochoice")
    )
    return BIO_CHOICE


async def bio_choice_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data.endswith(":yes"):
        await q.edit_message_text(tr(context, "bio"))
        return BIO
    save(q.from_user.id, "bio", "")
    await q.edit_message_text(tr(context, "photo"))
    return PHOTO


async def bio_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = (update.effective_message.text or "").strip()
    if len(value) > 500:
        await update.effective_message.reply_text(tr(context, "bad"))
        return BIO
    save(update.effective_user.id, "bio", value)
    await update.effective_message.reply_text(tr(context, "photo"))
    return PHOTO


async def photo_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg.photo:
        await msg.reply_text(tr(context, "photo"))
        return PHOTO
    save(update.effective_user.id, "photo", msg.photo[-1].file_id)
    await show_profile(update.effective_chat.id, update.effective_user.id, context)
    return CONFIRM


async def confirm_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "confirm:yes":
        save(q.from_user.id, "confirmed", 1)
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(tr(context, "saved"))
        return ConversationHandler.END

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(context, "namekey"), callback_data="edit:name"),
         InlineKeyboardButton(tr(context, "agekey"), callback_data="edit:age")],
        [InlineKeyboardButton(tr(context, "citykey"), callback_data="edit:city"),
         InlineKeyboardButton(tr(context, "biokey"), callback_data="edit:bio")],
        [InlineKeyboardButton(tr(context, "photokey"), callback_data="edit:photo")],
        [InlineKeyboardButton(tr(context, "delete"), callback_data="edit:delete")],
    ])
    await q.edit_message_reply_markup(reply_markup=None)
    await q.message.reply_text(tr(context, "editq"), reply_markup=kb)
    return EDIT


async def edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    field = q.data.split(":")[1]

    if field == "delete":
        with db() as c:
            c.execute("DELETE FROM profiles WHERE user_id=?", (q.from_user.id,))
        context.user_data.clear()
        await q.edit_message_text(tr(context, "deleted"))
        return ConversationHandler.END

    context.user_data["editing"] = field
    prompt = {
        "name": "askname", "age": "askage", "city": "askcity",
        "bio": "askbio", "photo": "askphoto",
    }
    await q.edit_message_text(tr(context, prompt[field]))
    return EDIT_VALUE


async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    uid = update.effective_user.id
    field = context.user_data.get("editing")

    if field == "photo":
        if not msg.photo:
            await msg.reply_text(tr(context, "askphoto"))
            return EDIT_VALUE
        save(uid, "photo", msg.photo[-1].file_id)
    elif field == "age":
        try:
            age = int((msg.text or "").strip())
        except ValueError:
            await msg.reply_text(tr(context, "badage"))
            return EDIT_VALUE
        if not 18 <= age <= 120:
            await msg.reply_text(tr(context, "badage"))
            return EDIT_VALUE
        save(uid, "age", age)
    else:
        value = (msg.text or "").strip()
        limits = {"name": 50, "city": 100, "bio": 500}
        if (field != "bio" and not value) or len(value) > limits[field]:
            await msg.reply_text(tr(context, "bad"))
            return EDIT_VALUE
        save(uid, field, value)

    context.user_data.pop("editing", None)
    save(uid, "confirmed", 0)
    await show_profile(update.effective_chat.id, uid, context)
    return CONFIRM


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_profile(update.effective_user.id)
    if not p or not p["name"] or not p["photo"]:
        await update.effective_message.reply_text(tr(context, "need"))
        return
    context.user_data["language"] = p["language"]
    await update.effective_message.reply_photo(
        photo=p["photo"],
        caption=profile_text(p, context),
        parse_mode=ParseMode.HTML,
    )


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_profile(update.effective_user.id)
    if p:
        context.user_data["language"] = p["language"]
    await update.effective_message.reply_text(
        tr(context, "deleteq"), reply_markup=yes_no(context, "delete")
    )


async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    p = get_profile(q.from_user.id)
    code = p["language"] if p else language(context)

    if q.data == "delete:no":
        await q.edit_message_text(T[code]["cancel"])
        return

    with db() as c:
        c.execute("DELETE FROM profiles WHERE user_id=?", (q.from_user.id,))
    context.user_data.clear()
    await q.edit_message_text(T[code]["deleted"])


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_profile(update.effective_user.id)
    code = p["language"] if p else language(context)
    await update.effective_message.reply_text(T[code]["help"])


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(tr(context, "cancel"))
    return ConversationHandler.END


def main():
    if not TOKEN:
        raise SystemExit(
            "BOT_TOKEN is missing. Set it in Windows or Railway Variables."
        )

    init_db()
    app = Application.builder().token(TOKEN).build()

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [CallbackQueryHandler(choose_language, pattern=r"^lang:(az|en|tr|ru|id)$")],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_step)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_step)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_step)],
            BIO_CHOICE: [CallbackQueryHandler(bio_choice_step, pattern=r"^biochoice:(yes|no)$")],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, bio_step)],
            PHOTO: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), photo_step)],
            CONFIRM: [CallbackQueryHandler(confirm_step, pattern=r"^confirm:(yes|no)$")],
            EDIT: [CallbackQueryHandler(edit_choice, pattern=r"^edit:(name|age|city|bio|photo|delete)$")],
            EDIT_VALUE: [MessageHandler(filters.ALL & ~filters.COMMAND, edit_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conversation)
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(delete_confirm, pattern=r"^delete:(yes|no)$"))

    logging.info("TindraVen bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
