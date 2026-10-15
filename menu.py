
from telegram import (
    BotCommand,
    BotCommandScopeDefault,
    MenuButtonCommands,
)
from telegram.ext import Application


COMMANDS = [
    BotCommand("start", "Start / register"),
    BotCommand("search", "Find people"),
    BotCommand("myprofile", "My profile"),
    BotCommand("edit", "Edit my profile"),
    BotCommand("settings", "Profile settings"),
    BotCommand("safety", "Safety and reporting"),
    BotCommand("help", "Help and commands"),
]


async def setup_menu(application: Application) -> None:
    """Configure the Telegram command menu on bot startup."""

    bot = application.bot

    await bot.set_my_commands(
        commands=COMMANDS,
        scope=BotCommandScopeDefault(),
    )

    await bot.set_chat_menu_button(
        menu_button=MenuButtonCommands()
    )

    print("TindraVen menu activated successfully!")


def register_menu(application: Application) -> None:
    """Register menu setup without replacing existing handlers."""

    application.post_init = setup_menu
