"""TindraVen: Telegram slash menu, shown when a user types /."""
from telegram import BotCommand, BotCommandScopeAllPrivateChats


async def setup_menu(application):
    commands = [
        BotCommand("start", "❤️ Start / register"),
        BotCommand("search", "🔎 Find people"),
        BotCommand("myprofile", "👤 My profile"),
        BotCommand("edit", "✏️ Edit my profile"),
        BotCommand("settings", "⚙️ Profile settings"),
        BotCommand("safety", "🛡️ Safety and reporting"),
        BotCommand("help", "❓ Help and commands"),
    ]
    await application.bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
