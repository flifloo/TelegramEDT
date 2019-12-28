from aiogram import types
from aiogram.types import ParseMode

from TelegramEDT import dp, key, logger, Session, check_id
from TelegramEDT.base import User
from TelegramEDT.lang import lang

logger = logger.getChild("basic")


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
    logger.info("Load basic module")
    dp.register_message_handler(start, commands="start")
    dp.register_message_handler(help_cmd, commands="help")


def unload():
    logger.info("Unload basic module")
    dp.message_handlers.unregister(start)
    dp.message_handlers.unregister(help_cmd)
