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

# Translations Dictionary
LANGUAGES = {
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
        "search_no_profile": "Please register first by typing /start.",
        "search_empty": "No new profiles found right now. Check back later!",
        "match": "🎉 **It's a Match!** {name} liked you back!\nContact: {contact}",
        "edit": "✏️ Edit Profile",
        "delete": "🗑 Delete Profile",
        "cancel": "Registration cancelled."
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
        "search_no_profile": "Lütfen önce /start yazarak kayıt olun.",
        "search_empty": "Şu an uygun yeni profil bulunamadı. Daha sonra tekrar deneyin!",
        "match": "🎉 **Eşleşme!** {name} de seni beğendi!\nİletişim: {contact}",
        "edit": "✏️ Profili Düzenle",
        "delete": "🗑 Profili Sil",
        "cancel": "Kayıt iptal edildi."
    },
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
        "already_registered": "Siz artıq qeydiyyatdan keçmisiniz! Profillərə baxmaq üçün /search yazın.",
        "search_no_profile": "Zəhmət olmasa əvvəlcə /start yazaraq qeydiyyatdan keçin.",
        "search_empty": "Hələ ki sizə uyğun yeni profil yoxdur. Bir az sonra yenidən cəhd edin!",
        "match": "🎉 **Qarşılıqlı Bəyənmə!** {name} də sizi bəyəndi!\nƏlaqə: {contact}",
        "edit": "✏️ Profili Redaktə Et",
        "delete": "🗑 Profili Sil",
        "cancel": "Qeydiyyat ləğv edildi."
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
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
            InlineKeyboardButton("🇦🇿 Azərbaycan", callback_data="lang_az")
        ]
    ]
    await update.message.reply_text(
        "Welcome! Please choose your language / Dil seçin / Dil seçimi:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LANG_SELECT

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1] # en, tr, az
    context.user_data['language'] = lang
    user_id = query.from_user.id

    # Temporary save language to db so helper works
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
    
    keyboard = [["👨 Male / Erkek", "👩 Female / Kadın", "⚧ Other / Diğer"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(get_text(user_id, "gender_select"), reply_markup=reply_markup)
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['gender'] = update.message.text
    
    keyboard = [["👨 Men / Erkekler", "👩 Women / Kadınlar", "🌈 Everyone / Herkes"]]
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

# Search & Matchmaking
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT gender, looking_for FROM users WHERE user_id = ?', (user_id,))
    current_user = cursor.fetchone()
    
    if not current_user:
        await update.message.reply_text("Please register first / Lütfen kayıt olun / Qeydiyyatdan keçin.")
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

    if my_preference and "Men" in my_preference or "Erkekler" in my_preference:
        query += " AND (gender LIKE '%Male%' OR gender LIKE '%Erkek%')"
    elif my_preference and "Women" in my_preference or "Kadınlar" in my_preference:
        query += " AND (gender LIKE '%Female%' OR gender LIKE '%Kadın%')"

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
    user_id = query.from_user.id

    if data == "delete_profile":
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM likes WHERE from_user_id = ? OR to_user_id = ?', (user_id, user_id))
        conn.commit()
        conn.close()
        await query.message.delete()
        await context.bot.send_message(chat_id=user_id, text="Profile deleted / Profil silindi. /start")
        return

    elif data == "edit_profile":
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        await query.message.delete()
        await context.bot.send_message(chat_id=user_id, text="Please type /start to register again.")
        return

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

            # Send messages in their respective languages
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
    app.add_handler(CommandHandler('search', search))
    app.add_handler(CallbackQueryHandler(handle_action))

    print("Bot started successfully with multi-language support...")
    app.run_polling()

if __name__ == '__main__':
    main()
