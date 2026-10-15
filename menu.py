"""Register TindraVen slash commands in Telegram's native / menu."""
import logging
from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeAllPrivateChats

COMMANDS = [
    BotCommand('start', 'Start or register'),
    BotCommand('search', 'Find people'),
    BotCommand('myprofile', 'View my profile'),
    BotCommand('edit', 'Edit my profile'),
    BotCommand('settings', 'Profile settings'),
    BotCommand('safety', 'Safety and reporting'),
    BotCommand('help', 'Help and commands'),
]

async def setup_menu(application):
    bot = application.bot
    # Set both scopes: the default menu and private-chat-specific menu.
    await bot.set_my_commands(COMMANDS, scope=BotCommandScopeDefault())
    await bot.set_my_commands(COMMANDS, scope=BotCommandScopeAllPrivateChats())
    actual = await bot.get_my_commands(scope=BotCommandScopeAllPrivateChats())
    logging.info('Telegram private-chat slash menu registered: %s', [c.command for c in actual])
