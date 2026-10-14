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
            photo_id TEXT
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

# Registration States
NAME, AGE, LOCATION, GENDER, LOOKING_FOR, BIO, PHOTO = range(7)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        await update.message.reply_text(
            "You are already registered! Use /search to browse profiles or /myprofile to manage your profile."
        )
        return ConversationHandler.END

    await update.message.reply_text("Welcome! Let's set up your profile.\n\nPlease enter your **Name**:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Please enter your **Age**:")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text("Please enter a valid number for your age:")
        return AGE
    
    age = int(text)
    if age < 16:
        await update.message.reply_text("Sorry, you must be at least 16 years old to use this bot.")
        return ConversationHandler.END

    context.user_data['age'] = age
    await update.message.reply_text("Please enter your **City / Location**:")
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['location'] = update.message.text
    
    keyboard = [["👨 Male", "👩 Female", "⚧ Other"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text("Select your **Gender**:", reply_markup=reply_markup)
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    
    keyboard = [["👨 Men", "👩 Women", "🌈 Everyone"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text("Who are you looking to meet?", reply_markup=reply_markup)
    return LOOKING_FOR

async def get_looking_for(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['looking_for'] = update.message.text
    
    await update.message.reply_text(
        "Write a short **Bio** about yourself and what you are looking for:",
        reply_markup=ReplyKeyboardRemove()
    )
    return BIO

async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bio'] = update.message.text
    await update.message.reply_text("Now, please send a **photo** for your profile:")
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = update.message.photo[-1].file_id
    user = update.effective_user
    
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, name, age, location, gender, looking_for, bio, photo_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user.id,
        user.username or "Private",
        context.user_data['name'],
        context.user_data['age'],
        context.user_data['location'],
        context.user_data['gender'],
        context.user_data['looking_for'],
        context.user_data['bio'],
        photo_file
    ))
    conn.commit()
    conn.close()

    await update.message.reply_text("🎉 Profile completed successfully! Here is how people see you:")
    
    # Send preview to the user
    caption = f"👤 **{context.user_data['name']}**, {context.user_data['age']}\n📍 {context.user_data['location']}\n\n📝 {context.user_data['bio']}"
    keyboard = [
        [
            InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile"),
            InlineKeyboardButton("🗑 Delete Profile", callback_data="delete_profile")
        ]
    ]
    await update.message.reply_photo(photo=photo_file, caption=caption, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled.", reply_markup=ReplyKeyboardRemove())
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
            InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile"),
            InlineKeyboardButton("🗑 Delete Profile", callback_data="delete_profile")
        ]
    ]
    
    await update.message.reply_photo(
        photo=photo_id, 
        caption=f"Your Profile:\n\n{caption}", 
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
        await context.bot.send_message(chat_id=user_id, text="🗑 Your profile has been deleted. Type /start to register again.")

    elif query.data == "edit_profile":
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

        await query.message.delete()
        await context.bot.send_message(chat_id=user_id, text="Let's update your profile! Please enter your new **Name**:")
        # Return state for registration starting from NAME
        return NAME

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

    if my_preference == "👨 Men":
        query += " AND gender = '👨 Male'"
    elif my_preference == "👩 Women":
        query += " AND gender = '👩 Female'"

    query += " LIMIT 1"

    cursor.execute(query, params)
    profile = cursor.fetchone()
    conn.close()

    if not profile:
        await update.message.reply_text("No new profiles found right now. Check back later!")
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
    if data.startswith("edit_profile") or data.startswith("delete_profile"):
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
            cursor.execute('SELECT username, name FROM users WHERE user_id = ?', (target_id,))
            target_user = cursor.fetchone()
            
            cursor.execute('SELECT username, name FROM users WHERE user_id = ?', (from_id,))
            from_user = cursor.fetchone()

            target_link = f"@{target_user[0]}" if target_user[0] != "Private" else target_user[1]
            from_link = f"@{from_user[0]}" if from_user[0] != "Private" else from_user[1]

            await context.bot.send_message(
                chat_id=from_id, 
                text=f"🎉 **It's a Match!** {target_user[1]} liked you back!\nContact: {target_link}"
            )
            await context.bot.send_message(
                chat_id=target_id, 
                text=f"🎉 **It's a Match!** {from_user[1]} liked you back!\nContact: {from_link}"
            )

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
