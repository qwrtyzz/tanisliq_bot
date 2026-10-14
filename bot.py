import logging
import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

# Logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 5 Dildə Mesajlar Sözlüyü
LANGUAGES = {
    "az": {
        "reg_name": "Gəlin profilinizi yaradaq.\n\nZəhmət olmasa **Adınızı** daxil edin:",
        "reg_age": "Zəhmət olmasa **Yaşınızı** daxil edin:",
        "age_error": "Zəhmət olmasa yaşınız üçün düzgün rəqəm daxil edin:",
        "age_limit": "Təəssüf ki, botdan istifadə etmək üçün ən azı 16 yaşınız olmalıdır.",
        "reg_location": "Yaşadığınız **Şəhər / Ünvanı** daxil edin:",
        "bio_ask": "Özünüz haqqında əlavə məlumat vermək istəyirsiniz?",
        "btn_yes": "✅ Hə",
        "btn_no": "❌ Yox",
        "bio_prompt": "Zəhmət olmasa özünüz haqqında məlumatı yazın:",
        "photo_prompt": "Zəhmət olmasa profiliniz üçün bir **şəkil** göndərin:",
        "confirm_profile": "Bu profil ilə davam edək?",
        "profile_saved": "🎉 Profiliniz yadda saxlanıldı! Dost axtarışına başlamaq üçün /search yazın.",
        "edit": "✏️ Profili Redaktə Et",
        "delete": "🗑 Profili Sil",
        "profile_deleted": "🗑 Profiliniz silindi. Yenidən başlamaq üçün /start yazın.",
        "already_registered": "Siz artıq qeydiyyatdan keçmisiniz! Dost axtarmaq üçün /search, profilinizi idarə etmək üçün /myprofile yazın.",
        "search_empty": "Hələ ki sizə uyğun yeni profil yoxdur. Bir az sonra yenidən cəhd edin!",
        "match": "🎉 **Qarşılıqlı Bəyənmə!** {name} də sizi bəyəndi!\nƏlaqə: {contact}",
        "cancel": "Qeydiyyat ləğv edildi."
    },
    "en": {
        "reg_name": "Let's set up your profile.\n\nPlease enter your **Name**:",
        "reg_age": "Please enter your **Age**:",
        "age_error": "Please enter a valid number for your age:",
        "age_limit": "Sorry, you must be at least 16 years old to use this bot.",
        "reg_location": "Please enter your **City / Location**:",
        "bio_ask": "Would you like to add additional information about yourself?",
        "btn_yes": "✅ Yes",
        "btn_no": "❌ No",
        "bio_prompt": "Please write something about yourself:",
        "photo_prompt": "Please send a **photo** for your profile:",
        "confirm_profile": "Shall we continue with this profile?",
        "profile_saved": "🎉 Profile saved successfully! Type /search to start looking for friends.",
        "edit": "✏️ Edit Profile",
        "delete": "🗑 Delete Profile",
        "profile_deleted": "🗑 Profile deleted. Type /start to register again.",
        "already_registered": "You are already registered! Type /search to find friends or /myprofile to manage your profile.",
        "search_empty": "No new profiles found right now. Check back later!",
        "match": "🎉 **It's a Match!** {name} liked you back!\nContact: {contact}",
        "cancel": "Registration cancelled."
    },
    "tr": {
        "reg_name": "Profilinizi oluşturalım.\n\nLütfen **Adınızı** girin:",
        "reg_age": "Lütfen **Yaşınızı** girin:",
        "age_error": "Lütfen yaşınız için geçerli bir sayı girin:",
        "age_limit": "Üzgünüm, bu botu kullanmak için en az 16 yaşında olmalısınız.",
        "reg_location": "Lütfen **Şehrinizi / Konumunuzu** girin:",
        "bio_ask": "Kendiniz hakkında ek bilgi vermek ister misiniz?",
        "btn_yes": "✅ Evet",
        "btn_no": "❌ Hayır",
        "bio_prompt": "Lütfen kendiniz hakkında bir şeyler yazın:",
        "photo_prompt": "Lütfen profiliniz için bir **fotoğraf** gönderin:",
        "confirm_profile": "Bu profil ile devam edelim mi?",
        "profile_saved": "🎉 Profiliniz kaydedildi! Arkadaş aramaya başlamak için /search yazın.",
        "edit": "✏️ Profili Düzenle",
        "delete": "🗑 Profili Sil",
        "profile_deleted": "🗑 Profiliniz silindi. Tekrar kaydolmak için /start yazın.",
        "already_registered": "Zaten kayıtlısınız! /search ile arkadaş arayabilir veya /myprofile ile profilinizi yönetebilirsiniz.",
        "search_empty": "Şu an uygun yeni profil bulunamadı. Daha sonra tekrar deneyin!",
        "match": "🎉 **Eşleşme!** {name} de seni beğendi!\nİletişim: {contact}",
        "cancel": "Kayıt iptal edildi."
    },
    "ru": {
        "reg_name": "Давайте создадим ваш профиль.\n\nПожалуйста, введите ваше **Имя**:",
        "reg_age": "Пожалуйста, введите ваш **Возраст**:",
        "age_error": "Пожалуйста, введите корректное число для возраста:",
        "age_limit": "Извините, вам должно быть не менее 16 лет для использования бота.",
        "reg_location": "Укажите ваш **Город / Местоположение**:",
        "bio_ask": "Хотите добавить дополнительную информацию о себе?",
        "btn_yes": "✅ Да",
        "btn_no": "❌ Нет",
        "bio_prompt": "Пожалуйста, напишите немного о себе:",
        "photo_prompt": "Пожалуйста, отправьте **фотографию** для профиля:",
        "confirm_profile": "Продолжить с этим профилем?",
        "profile_saved": "🎉 Профиль сохранен! Напишите /search, чтобы начать поиск друзей.",
        "edit": "✏️ Редактировать профиль",
        "delete": "🗑 Удалить профиль",
        "profile_deleted": "🗑 Профиль удален. Напишите /start для повторной регистрации.",
        "already_registered": "Вы уже зарегистрированы! Напишите /search для поиска или /myprofile для управления профилем.",
        "search_empty": "Новых профилей пока нет. Попробуйте позже!",
        "match": "🎉 **У вас совпадение!** {name} ответил(а) взаимностью!\nКонтакты: {contact}",
        "cancel": "Регистрация отменена."
    },
    "id": {
        "reg_name": "Mari buat profil Anda.\n\nSilakan masukkan **Nama** Anda:",
        "reg_age": "Silakan masukkan **Usia** Anda:",
        "age_error": "Silakan masukkan angka usia yang valid:",
        "age_limit": "Maaf, Anda harus berusia minimal 16 tahun untuk menggunakan bot ini.",
        "reg_location": "Silakan masukkan **Kota / Lokasi** Anda:",
        "bio_ask": "Apakah Anda ingin menambahkan informasi tambahan tentang diri Anda?",
        "btn_yes": "✅ Ya",
        "btn_no": "❌ Tidak",
        "bio_prompt": "Silakan tulis sesuatu tentang diri Anda:",
        "photo_prompt": "Silakan kirim **foto** untuk profil Anda:",
        "confirm_profile": "Lanjutkan dengan profil ini?",
        "profile_saved": "🎉 Profil berhasil disimpan! Ketik /search untuk mulai mencari teman.",
        "edit": "✏️ Edit Profil",
        "delete": "🗑 Hapus Profil",
        "profile_deleted": "🗑 Profil dihapus. Ketik /start untuk mendaftar lagi.",
        "already_registered": "Anda sudah terdaftar! Ketik /search untuk mencari teman atau /myprofile untuk mengelola profil.",
        "search_empty": "Tidak ada profil baru saat ini. Coba lagi nanti!",
        "match": "🎉 **Cocok!** {name} menyukai Anda kembali!\nKontak: {contact}",
        "cancel": "Pendaftaran dibatalkan."
    }
}

# Database initialization
def init_db():
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            age INTEGER,
            location TEXT,
            bio TEXT,
            photo_id TEXT,
            language TEXT DEFAULT 'en'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            from_user_id INTEGER,
            to_user_id INTEGER,
            PRIMARY KEY (from_user_id, to_user_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_text(user_id, key, lang_fallback='en'):
    try:
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
        res = cursor.fetchone()
        conn.close()
        lang = res[0] if res and res[0] in LANGUAGES else lang_fallback
        return LANGUAGES[lang].get(key, LANGUAGES['en'].get(key, ""))
    except Exception:
        return LANGUAGES[lang_fallback].get(key, "")

# Registration States
LANG_SELECT, NAME, AGE, LOCATION, BIO_CHOICE, BIO_INPUT, PHOTO, CONFIRM = range(8)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM users WHERE user_id = ? AND name IS NOT NULL', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        await update.message.reply_text(get_text(user_id, "already_registered"))
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("Azerbaycan", callback_data="lang_az")],
        [InlineKeyboardButton("English", callback_data="lang_en")],
        [InlineKeyboardButton("Turkish", callback_data="lang_tr")],
        [InlineKeyboardButton("Russia", callback_data="lang_ru")],
        [InlineKeyboardButton("Indonesia", callback_data="lang_id")]
    ]
    await update.message.reply_text(
        "Please choose your language:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LANG_SELECT

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    context.user_data['language'] = lang
    user_id = query.from_user.id

    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (user_id, language) VALUES (?, ?)', (user_id, lang))
    conn.commit()
    conn.close()

    await query.message.delete()
    await context.bot.send_message(chat_id=user_id, text=get_text(user_id, "reg_name", lang))
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'en')
    context.user_data['name'] = update.message.text
    await update.message.reply_text(get_text(user_id, "reg_age", lang))
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'en')
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text(get_text(user_id, "age_error", lang))
        return AGE
    
    age = int(text)
    if age < 16:
        await update.message.reply_text(get_text(user_id, "age_limit", lang))
        return ConversationHandler.END

    context.user_data['age'] = age
    await update.message.reply_text(get_text(user_id, "reg_location", lang))
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'en')
    context.user_data['location'] = update.message.text

    yes_str = get_text(user_id, "btn_yes", lang)
    no_str = get_text(user_id, "btn_no", lang)

    keyboard = [[yes_str, no_str]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(get_text(user_id, "bio_ask", lang), reply_markup=reply_markup)
    return BIO_CHOICE

async def get_bio_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'en')
    choice = update.message.text

    yes_str = get_text(user_id, "btn_yes", lang)

    if yes_str in choice or "Yes" in choice or "Hə" in choice or "Evet" in choice or "Да" in choice or "Ya" in choice:
        await update.message.reply_text(get_text(user_id, "bio_prompt", lang), reply_markup=ReplyKeyboardRemove())
        return BIO_INPUT
    else:
        context.user_data['bio'] = "-"
        await update.message.reply_text(get_text(user_id, "photo_prompt", lang), reply_markup=ReplyKeyboardRemove())
        return PHOTO

async def get_bio_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'en')
    context.user_data['bio'] = update.message.text
    await update.message.reply_text(get_text(user_id, "photo_prompt", lang))
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'en')
    
    photo_file = update.message.photo[-1].file_id
    context.user_data['photo_id'] = photo_file

    caption = f"👤 **{context.user_data['name']}**, {context.user_data['age']}\n📍 {context.user_data['location']}"
    if context.user_data.get('bio') and context.user_data['bio'] != "-":
        caption += f"\n\n📝 {context.user_data['bio']}"

    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ No", callback_data="confirm_no")
        ]
    ]
    
    await update.message.reply_photo(
        photo=photo_file, 
        caption=f"{caption}\n\n{get_text(user_id, 'confirm_profile', lang)}", 
        parse_mode="Markdown", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = context.user_data.get('language', 'en')

    if query.data == "confirm_yes":
        user = query.from_user
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET username=?, name=?, age=?, location=?, bio=?, photo_id=?, language=?
            WHERE user_id=?
        ''', (
            user.username or "Private",
            context.user_data['name'],
            context.user_data['age'],
            context.user_data['location'],
            context.user_data['bio'],
            context.user_data['photo_id'],
            lang,
            user_id
        ))
        conn.commit()
        conn.close()

        await query.message.delete()
        await context.bot.send_message(chat_id=user_id, text=get_text(user_id, "profile_saved", lang))
        return ConversationHandler.END

    elif query.data == "confirm_no":
        await query.message.delete()
        keyboard = [
            [
                InlineKeyboardButton(get_text(user_id, "edit", lang), callback_data="edit_profile"),
                InlineKeyboardButton(get_text(user_id, "delete", lang), callback_data="delete_profile")
            ]
        ]
        await context.bot.send_message(
            chat_id=user_id,
            text="Please choose an option:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, "cancel"), reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, age, location, bio, photo_id FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user or not user[0]:
        await update.message.reply_text("You haven't registered yet! Type /start to create a profile.")
        return

    name, age, loc, bio, photo_id = user
    caption = f"👤 **{name}**, {age}\n📍 {loc}"
    if bio and bio != "-":
        caption += f"\n\n📝 {bio}"

    keyboard = [
        [
            InlineKeyboardButton(get_text(user_id, "edit"), callback_data="edit_profile"),
            InlineKeyboardButton(get_text(user_id, "delete"), callback_data="delete_profile")
        ]
    ]
    
    await update.message.reply_photo(
        photo=photo_id, 
        caption=caption, 
        parse_mode="Markdown", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_profile_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "delete_profile":
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM likes WHERE from_user_id = ? OR to_user_id = ?', (user_id, user_id))
        conn.commit()
        conn.close()

        await query.message.delete()
        await context.bot.send_message(chat_id=user_id, text=get_text(user_id, "profile_deleted"))

    elif query.data == "edit_profile":
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

        await query.message.delete()
        await context.bot.send_message(chat_id=user_id, text="Profile reset! Please type /start to begin again.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM users WHERE user_id = ?', (user_id,))
    current_user = cursor.fetchone()
    
    if not current_user or not current_user[0]:
        await update.message.reply_text("Please register first by typing /start.")
        conn.close()
        return

    query_str = (
        "SELECT user_id, name, age, location, bio, photo_id FROM users "
        "WHERE user_id != ? AND name IS NOT NULL AND user_id NOT IN ("
        "SELECT to_user_id FROM likes WHERE from_user_id = ?"
        ") LIMIT 1"
    )

    cursor.execute(query_str, (user_id, user_id))
    profile = cursor.fetchone()
    conn.close()

    if not profile:
        await update.message.reply_text(get_text(user_id, "search_empty"))
        return

    p_id, name, age, loc, bio, photo_id = profile
    caption = f"👤 **{name}**, {age}\n📍 {loc}"
    if bio and bio != "-":
        caption += f"\n\n📝 {bio}"

    keyboard = [
        [
            InlineKeyboardButton("❤️ Like", callback_data=f"like_{p_id}"),
            InlineKeyboardButton("❌ Skip", callback_data=f"skip_{p_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(chat_id=user_id, photo=photo_id, caption=caption, parse_mode="Markdown", reply_markup=reply_markup)

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id

    if data == "edit_profile" or data == "delete_profile":
        return await handle_profile_action(update, context)

    action, target_id = data.split("_")
    target_id = int(target_id)
    from_id = query.from_user.id

    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()

    if action == "like":
        cursor.execute('INSERT OR IGNORE INTO likes (from_user_id, to_user_id) VALUES (?, ?)', (from_id, target_id))
        conn.commit()

        cursor.execute('SELECT * FROM likes WHERE from_user_id = ? AND to_user_id = ?', (target_id, from_id))
        is_match = cursor.fetchone()

        if is_match:
            cursor.execute('SELECT username, name, language FROM users WHERE user_id = ?', (target_id,))
            target_user = cursor.fetchone()
            
            cursor.execute('SELECT username, name, language FROM users WHERE user_id = ?', (from_id,))
            from_user = cursor.fetchone()

            target_link = f"@{target_user[0]}" if target_user[0] != "Private" else target_user[1]
            from_link = f"@{from_user[0]}" if from_user[0] != "Private" else from_user[1]

            t_text = LANGUAGES.get(target_user[2], LANGUAGES['en'])["match"].format(name=from_user[1], contact=from_link)
            f_text = LANGUAGES.get(from_user[2], LANGUAGES['en'])["match"].format(name=target_user[1], contact=target_link)

            await context.bot.send_message(chat_id=from_id, text=f_text)
            await context.bot.send_message(chat_id=target_id, text=t_text)

    elif action == "skip":
        cursor.execute('INSERT OR IGNORE INTO likes (from_user_id, to_user_id) VALUES (?, ?)', (from_id, target_id))
        conn.commit()

    conn.close()
    
    await query.message.delete()
    await search(update, context)

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is missing!")

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANG_SELECT: [CallbackQueryHandler(language_chosen, pattern="^lang_")],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)],
            BIO_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio_choice)],
            BIO_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio_input)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            CONFIRM: [CallbackQueryHandler(handle_confirmation, pattern="^confirm_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_chat=True,
        per_user=True
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('myprofile', my_profile))
    app.add_handler(CommandHandler('search', search))
    app.add_handler(CallbackQueryHandler(handle_action))

    print("Bot is up and running...")
    app.run_polling()

if __name__ == '__main__':
    main()
