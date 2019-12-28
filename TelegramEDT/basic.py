from aiogram import types
from aiogram.types import ParseMode

from TelegramEDT import dp, key, logger, Session, check_id, modules
from TelegramEDT.base import User
from TelegramEDT.lang import lang

module_name = "basic"
logger = logger.getChild(module_name)


async def start(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} start")
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        msg = lang(user, "welcome")

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def help_cmd(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do help command")
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        msg = lang(user, "help")

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


def load():
    logger.info(f"Load {module_name} module")
    dp.register_message_handler(start, commands="start")
    dp.register_message_handler(help_cmd, commands="help")
    modules.append(module_name)


def unload():
    logger.info(f"Unload {module_name} module")
    dp.message_handlers.unregister(start)
    dp.message_handlers.unregister(help_cmd)
    modules.remove(module_name)
