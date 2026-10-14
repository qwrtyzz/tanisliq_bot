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

# Translations Dictionary for 5 Languages
LANGUAGES = {
    "az": {
        "welcome": "Xoş gəldiniz! Zəhmət olmasa dil seçin:",
        "reg_name": "Gəlin profilinizi yaradaq.\n\nZəhmət olmasa **Adınızı** daxil edin:",
        "reg_age": "Zəhmət olmasa **Yaşınızı** daxil edin:",
        "age_error": "Zəhmət olmasa yaşınız üçün düzgün rəqəm daxil edin:",
        "age_limit": "Təəssüf ki, botdan istifadə etmək üçün ən azı 16 yaşınız olmalıdır.",
        "reg_location": "Yaşadığınız **Şəhər / Ünvanı** daxil edin:",
        "gender_select": "Cinsinizi seçin:",
        "looking_for": "Hansı cinslə tanış olmaq istəyirsiniz?",
        "bio_prompt": "Özünüz və axtardığınız şəxs haqqında qısa **məlumat** yazın:",
        "photo_prompt": "İndi isə profiliniz üçün **şəkil** göndərin:",
        "profile_done": "🎉 Profil uğurla tamamlandı! İnsanlar səni belə görür:",
        "already_registered": "Siz artıq qeydiyyatdan keçmisiniz! Profillərə baxmaq üçün /search yazın və ya profilinizi idarə etmək üçün /myprofile yazın.",
        "search_empty": "Hələ ki sizə uyğun yeni profil yoxdur. Bir az sonra yenidən cəhd edin!",
        "match": "🎉 **Qarşılıqlı Bəyənmə!** {name} də sizi bəyəndi!\nƏlaqə: {contact}",
        "edit": "✏️ Profili Redaktə Et",
        "delete": "🗑 Profili Sil",
        "cancel": "Qeydiyyat ləğv edildi."
    },
    "en": {
        "welcome": "Welcome! Please choose your language:",
        "reg_name": "Let's set up your profile.\n\nPlease enter your **Name**:",
        "reg_age": "Please enter your **Age**:",
        "age_error": "Please enter a valid number for your age:",
        "age_limit": "Sorry, you must be at least 16 years old to use this bot.",
        "reg_location": "Please enter your **City / Location**:",
        "gender_select": "Select your **Gender**:",
        "looking_for": "Who are you looking to meet?",
        "bio_prompt": "Write a short **Bio** about yourself and what you are looking for:",
        "photo_prompt": "Now, please send a **photo** for your profile:",
        "profile_done": "🎉 Profile completed successfully! Here is how people see you:",
        "already_registered": "You are already registered! Use /search to browse profiles or /myprofile to manage your profile.",
        "search_empty": "No new profiles found right now. Check back later!",
        "match": "🎉 **It's a Match!** {name} liked you back!\nContact: {contact}",
        "edit": "✏️ Edit Profile",
        "delete": "🗑 Delete Profile",
        "cancel": "Registration cancelled."
    },
    "ru": {
        "welcome": "Добро пожаловать! Пожалуйста, выберите язык:",
        "reg_name": "Давайте создадим ваш профиль.\n\nПожалуйста, введите ваше **Имя**:",
        "reg_age": "Пожалуйста, введите ваш **Возраст**:",
        "age_error": "Пожалуйста, введите корректное число для возраста:",
        "age_limit": "Извините, вам должно быть не менее 16 лет для использования бота.",
        "reg_location": "Укажите ваш **Город / Местоположение**:",
        "gender_select": "Выберите ваш **Пол**:",
        "looking_for": "Кого вы ищете?",
        "bio_prompt": "Напишите краткую **информацию о себе** и кого вы ищете:",
        "photo_prompt": "Теперь отправьте **фотографию** для профиля:",
        "profile_done": "🎉 Профиль успешно создан! Вот как вас видят другие:",
        "already_registered": "Вы уже зарегистрированы! Используйте /search для поиска или /myprofile для управления профилем.",
        "search_empty": "Новых профилей пока нет. Попробуйте позже!",
        "match": "🎉 **У вас совпадение!** {name} ответил(а) взаимностью!\nКонтакты: {contact}",
        "edit": "✏️ Редактировать профиль",
        "delete": "🗑 Удалить профиль",
        "cancel": "Регистрация отменена."
    },
    "tr": {
        "welcome": "Hoş geldiniz! Lütfen dil seçin:",
        "reg_name": "Profilinizi oluşturalım.\n\nLütfen **Adınızı** girin:",
        "reg_age": "Lütfen **Yaşınızı** girin:",
        "age_error": "Lütfen yaşınız için geçerli bir sayı girin:",
        "age_limit": "Üzgünüm, bu botu kullanmak için en az 16 yaşında olmalısınız.",
        "reg_location": "Lütfen **Şehrinizi / Konumunuzu** girin:",
        "gender_select": "Cinsiyetinizi seçin:",
        "looking_for": "Kiminle tanışmak istiyorsunuz?",
        "bio_prompt": "Kendiniz ve aradığınız kişi hakkında kısa bir **biyografi** yazın:",
        "photo_prompt": "Şimdi profiliniz için bir **fotoğraf** gönderin:",
        "profile_done": "🎉 Profil başarıyla tamamlandı! İnsanlar seni böyle görüyor:",
        "already_registered": "Zaten kayıtlısınız! /search ile profillere göz atın veya /myprofile ile profilinizi yönetin.",
        "search_empty": "Şu an uygun yeni profil bulunamadı. Daha sonra tekrar deneyin!",
        "match": "🎉 **Eşleşme!** {name} de seni beğendi!\nİletişim: {contact}",
        "edit": "✏️ Profili Düzenle",
        "delete": "🗑 Profili Sil",
        "cancel": "Kayıt iptal edildi."
    },
    "id": {
        "welcome": "Selamat datang! Silakan pilih bahasa Anda:",
        "reg_name": "Mari buat profil Anda.\n\nSilakan masukkan **Nama** Anda:",
        "reg_age": "Silakan masukkan **Usia** Anda:",
        "age_error": "Silakan masukkan angka usia yang valid:",
        "age_limit": "Maaf, Anda harus berusia minimal 16 tahun untuk menggunakan bot ini.",
        "reg_location": "Silakan masukkan **Kota / Lokasi** Anda:",
        "gender_select": "Pilih **Jenis Kelamin** Anda:",
        "looking_for": "Siapa yang ingin Anda temui?",
        "bio_prompt": "Tulis **Bio** singkat tentang diri Anda dan apa yang Anda cari:",
        "photo_prompt": "Sekarang, silakan kirim **foto** untuk profil Anda:",
        "profile_done": "🎉 Profil berhasil dibuat! Begini tampilan profil Anda untuk orang lain:",
        "already_registered": "Anda sudah terdaftar! Gunakan /search untuk mencari atau /myprofile untuk mengelola profil.",
        "search_empty": "Tidak ada profil baru saat ini. Coba lagi nanti!",
        "match": "🎉 **Cocok!** {name} menyukai Anda kembali!\nKontak: {contact}",
        "edit": "✏️ Edit Profil",
        "delete": "🗑 Hapus Profil",
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
            gender TEXT,
            looking_for TEXT,
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

# Helper function to get text based on user language
def get_text(user_id, key):
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    lang = res[0] if res and res[0] in LANGUAGES else 'en'
    return LANGUAGES[lang].get(key, LANGUAGES['en'][key])

# Registration States
LANG_SELECT, NAME, AGE, LOCATION, GENDER, LOOKING_FOR, BIO, PHOTO = range(8)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        text = get_text(user_id, "already_registered")
        await update.message.reply_text(text)
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("🇦🇿 Azərbaycan", callback_data="lang_az")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr")],
        [InlineKeyboardButton("🇮🇩 Bahasa Indonesia", callback_data="lang_id")]
    ]
    await update.message.reply_text(
        "Please choose your language / Dil seçin / Выберите язык / Pilih bahasa:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LANG_SELECT

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1] # az, en, ru, tr, id
    context.user_data['language'] = lang
    user_id = query.from_user.id

    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (user_id, language) VALUES (?, ?)', (user_id, lang))
    conn.commit()
    conn.close()

    await query.message.delete()
    await context.bot.send_message(chat_id=user_id, text=get_text(user_id, "reg_name"))
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['name'] = update.message.text
    await update.message.reply_text(get_text(user_id, "reg_age"))
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text(get_text(user_id, "age_error"))
        return AGE
    
    age = int(text)
    if age < 16:
        await update.message.reply_text(get_text(user_id, "age_limit"))
        return ConversationHandler.END

    context.user_data['age'] = age
    await update.message.reply_text(get_text(user_id, "reg_location"))
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['location'] = update.message.text
    
    keyboard = [["👨 Male / Kişi / Мужчина / Erkek / Pria"], ["👩 Female / Qadın / Женщина / Kadın / Wanita"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(get_text(user_id, "gender_select"), reply_markup=reply_markup)
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['gender'] = update.message.text
    
    keyboard = [
        ["👨 Men / Kişilər / Мужчины / Erkekler / Pria"],
        ["👩 Women / Qadınlar / Женщины / Kadınlar / Wanita"],
        ["🌈 Everyone / Hər kəs / Все / Herkes / Semua"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(get_text(user_id, "looking_for"), reply_markup=reply_markup)
    return LOOKING_FOR

async def get_looking_for(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['looking_for'] = update.message.text
    
    await update.message.reply_text(
        get_text(user_id, "bio_prompt"),
        reply_markup=ReplyKeyboardRemove()
    )
    return BIO

async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['bio'] = update.message.text
    await update.message.reply_text(get_text(user_id, "photo_prompt"))
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = update.message.photo[-1].file_id
    user = update.effective_user
    user_id = user.id
    lang = context.user_data.get('language', 'en')
    
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET username=?, name=?, age=?, location=?, gender=?, looking_for=?, bio=?, photo_id=?, language=?
        WHERE user_id=?
    ''', (
        user.username or "Private",
        context.user_data['name'],
        context.user_data['age'],
        context.user_data['location'],
        context.user_data['gender'],
        context.user_data['looking_for'],
        context.user_data['bio'],
        photo_file,
        lang,
        user_id
    ))
    conn.commit()
    conn.close()

    await update.message.reply_text(get_text(user_id, "profile_done"))
    
    caption = f"👤 **{context.user_data['name']}**, {context.user_data['age']}\n📍 {context.user_data['location']}\n\n📝 {context.user_data['bio']}"
    keyboard = [
        [
            InlineKeyboardButton(get_text(user_id, "edit"), callback_data="edit_profile"),
            InlineKeyboardButton(get_text(user_id, "delete"), callback_data="delete_profile")
        ]
    ]
    await update.message.reply_photo(photo=photo_file, caption=caption, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, "cancel"), reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# My Profile Management (/myprofile)
async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, age, location, gender, looking_for, bio, photo_id FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        await update.message.reply_text("You haven't registered yet! Type /start to create a profile.")
        return

    name, age, loc, gender, looking_for, bio, photo_id = user
    caption = f"👤 **{name}**, {age}\n📍 {loc}\nGender: {gender} | Looking for: {looking_for}\n\n📝 {bio}"
    
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

# Profile Action Handler (Edit / Delete)
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
        await context.bot.send_message(chat_id=user_id, text="🗑 Profile deleted. Type /start to register again.")

    elif query.data == "edit_profile":
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

        await query.message.delete()
        await context.bot.send_message(chat_id=user_id, text="Let's update your profile! Please type /start to begin.")

# Search & Matchmaking
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT gender, looking_for FROM users WHERE user_id = ?', (user_id,))
    current_user = cursor.fetchone()
    
    if not current_user:
        await update.message.reply_text("Please register first by typing /start.")
        conn.close()
        return

    my_gender, my_preference = current_user

    query = '''
        SELECT user_id, name, age, location, bio, photo_id FROM users 
        WHERE user_id != ? AND user_id NOT IN (
            SELECT to_user_id FROM likes WHERE from_user_id = ?
        )
    '''
    params = [user_id, user_id]

    if my_preference and any(word in my_preference for word in ["Men", "Kişilər", "Мужчины", "Erkekler", "Pria"]):
        query += " AND (gender LIKE '%Male%' OR gender LIKE '%Kişi%' OR gender LIKE '%Мужчина%' OR gender LIKE '%Erkek%' OR gender LIKE '%Pria%')"
    elif my_preference and any(word in my_preference for word in ["Women", "Qadınlar", "Женщины", "Kadınlar", "Wanita"]):
        query += " AND (gender LIKE '%Female%' OR gender LIKE '%Qadın%' OR gender LIKE '%Женщина%' OR gender LIKE '%Kadın%' OR gender LIKE '%Wanita%')"

    query += " LIMIT 1"

    cursor.execute(query, params)
    profile = cursor.fetchone()
    conn.close()

    if not profile:
        await update.message.reply_text(get_text(user_id, "search_empty"))
        return

    p_id, name, age, loc, bio, photo_id = profile
    caption = f"👤 **{name}**, {age}\n📍 {loc}\n\n📝 {bio}"
    
    keyboard = [
        [
            InlineKeyboardButton("❤️ Like", callback_data=f"like_{p_id}"),
            InlineKeyboardButton("❌ Skip", callback_data=f"skip_{p_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(chat_id=user_id, photo=photo_id, caption=caption, parse_mode="Markdown", reply_markup=reply_markup)

# Like / Skip Handler
async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
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
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            LOOKING_FOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_looking_for)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('myprofile', my_profile))
    app.add_handler(CommandHandler('search', search))
    app.add_handler(CallbackQueryHandler(handle_action))

    print("Bot started successfully...")
    app.run_polling()

if __name__ == '__main__':
    main()
