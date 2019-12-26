from aiogram import types
from aiogram.types import ParseMode
from feedparser import parse

from TelegramEDT import dbL, dp, key, logger, session, check_id
from TelegramEDT.base import User
from TelegramEDT.lang import lang

logger = logger.getChild("tomuss")


def have_await_cmd(msg: types.Message):
    with dbL:
        user = session.query(User).filter_by(id=msg.from_user.id).first()
        return user and user.await_cmd == "settomuss"


async def settomuss(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do settomuss")
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        user.await_cmd = "settomuss"
        session.commit()

    await message.reply(lang(user, "settomuss_wait"), parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def await_cmd(message: types.message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        logger.info(f"{message.from_user.username} do awaited command")
        if not len(parse(message.text).entries):
            msg = lang(user, "settomuss_error")
        else:
            user.tomuss_rss = message.text
            msg = lang(user, "settomuss")
        user.await_cmd = str()
        session.commit()
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


def load():
    logger.info("Load tomuss module")
    dp.register_message_handler(settomuss, lambda msg: msg.text.lower() == "settomuss")
    dp.register_message_handler(await_cmd, lambda msg: have_await_cmd(msg))


def unload():
    logger.info("Unload tomuss module")
    dp.message_handlers.unregister(settomuss)
    dp.message_handlers.unregister(await_cmd)
