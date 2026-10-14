import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
import sqlite3

# Logging konfiqurasiyası
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Məlumat bazasını qurmaq
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
            photo_id TEXT,
            gender TEXT
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

# State-lər (Mərhələlər)
NAME, AGE, LOCATION, PHOTO, GENDER = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        await update.message.reply_text("Siz artıq qeydiyyatdan keçmisiniz! Profillərə baxmaq üçün /search yazın.")
        return ConversationHandler.END

    await update.message.reply_text("Xoş gəldiniz! Qeydiyyat üçün adınızı daxil edin:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Yaşınızı daxil edin:")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text("Xahiş olunur yalnız rəqəm daxil edin:")
        return AGE
    
    age = int(text)
    if age < 16:
        await update.message.reply_text("Təəssüf ki, 16 yaşdan aşağı şəxslərin qeydiyyatına icazə verilmir.")
        return ConversationHandler.END

    context.user_data['age'] = age
    await update.message.reply_text("Yaşadığınız şəhər/ünvanı daxil edin:")
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['location'] = update.message.text
    keyboard = [["Kişi", "Qadın"]]
    await update.message.reply_text("Cinsinizi seçin:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("İndi isə şəklinizi göndərin:")
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = update.message.photo[-1].file_id
    user = update.effective_user
    
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, name, age, location, photo_id, gender)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        user.id,
        user.username or "Gizli",
        context.user_data['name'],
        context.user_data['age'],
        context.user_data['location'],
        photo_file,
        context.user_data['gender']
    ))
    conn.commit()
    conn.close()

    await update.message.reply_text("Təbriklər! Profili tamamladınız. Əks cinsin profillərinə baxmaq üçün /search yazın.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Qeydiyyat ləğv edildi.")
    return ConversationHandler.END

# Profillərə baxmaq
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    
    # Cari istifadəçini tapırıq
    cursor.execute('SELECT gender FROM users WHERE user_id = ?', (user_id,))
    current_user = cursor.fetchone()
    if not current_user:
        await update.message.reply_text("Lütfən əvvəlcə /start yazaraq qeydiyyatdan keçin.")
        conn.close()
        return

    target_gender = "Qadın" if current_user[0] == "Kişi" else "Kişi"
    
    # Hələ bəyənmədiyi və ya keçmədiyi profilləri tapırıq
    cursor.execute('''
        SELECT user_id, name, age, location, photo_id FROM users 
        WHERE gender = ? AND user_id != ? AND user_id NOT IN (
            SELECT to_user_id FROM likes WHERE from_user_id = ?
        ) LIMIT 1
    ''', (target_gender, user_id, user_id))
    
    profile = cursor.fetchone()
    conn.close()

    if not profile:
        await update.message.reply_text("Hələ ki sizə uyğun yeni profil yoxdur. Bir az sonra yenidən cəhd edin!")
        return

    p_id, name, age, loc, photo_id = profile
    caption = f"👤 {name}, {age}\n📍 {loc}"
    
    keyboard = [
        [
            InlineKeyboardButton("❤️ Bəyən", callback_data=f"like_{p_id}"),
            InlineKeyboardButton("❌ Keç", callback_data=f"skip_{p_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(chat_id=user_id, photo=photo_id, caption=caption, reply_markup=reply_markup)

# Bəyənmə/Keçmə Callback Handler
async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action, target_id = query.data.split("_")
    target_id = int(target_id)
    from_id = query.from_user.id

    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()

    if action == "like":
        # Likes cədvəlinə əlavə edirik
        cursor.execute('INSERT OR IGNORE INTO likes (from_user_id, to_user_id) VALUES (?, ?)', (from_id, target_id))
        conn.commit()

        # Qarşılıqlı bəyənməni yoxlayırıq
        cursor.execute('SELECT * FROM likes WHERE from_user_id = ? AND to_user_id = ?', (target_id, from_id))
        is_match = cursor.fetchone()

        if is_match:
            # Qarşı tərəfin istifadəçi adını alırıq
            cursor.execute('SELECT username, name FROM users WHERE user_id = ?', (target_id,))
            target_user = cursor.fetchone()
            
            cursor.execute('SELECT username, name FROM users WHERE user_id = ?', (from_id,))
            from_user = cursor.fetchone()

            target_username = f"@{target_user[0]}" if target_user[0] != "Gizli" else target_user[1]
            from_username = f"@{from_user[0]}" if from_user[0] != "Gizli" else from_user[1]

            # Hər iki tərəfə bildiriş veririk
            await context.bot.send_message(
                chat_id=from_id, 
                text=f"🎉 Qarşılıqlı Bəyənmə! {target_user[1]} də sizi bəyəndi!\nYazışmaq üçün: {target_username}"
            )
            await context.bot.send_message(
                chat_id=target_id, 
                text=f"🎉 Qarşılıqlı Bəyənmə! {from_user[1]} də sizi bəyəndi!\nYazışmaq üçün: {from_username}"
            )

    elif action == "skip":
        # Sadece keçi qeyd etmək üçün də istifadə oluna bilər
        cursor.execute('INSERT OR IGNORE INTO likes (from_user_id, to_user_id) VALUES (?, ?)', (from_id, target_id))
        conn.commit()

    conn.close()
    
    # Köhnə mesajı silirik və növbəti profili göstəririk
    await query.message.delete()
    await search(update, context)

def main():
    # BotFather-dən aldığınız Tokeni bura yazın
    TOKEN = "8816146283:AAEwHKdv7K7DFbPBzTH21qcoEOvqbkglPY4"
    
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('search', search))
    app.add_handler(CallbackQueryHandler(handle_action))

    print("Bot işə düşdü...")
    app.run_polling()

if __name__ == '__main__':
    main()