from aiogram import types
from aiogram.types import ParseMode

from TelegramEDT import dbL, dp, key, logger, session, check_id
from TelegramEDT.base import User
from TelegramEDT.lang import lang

logger = logger.getChild("tomuss")


async def settomuss(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do settomuss")
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        user.await_cmd = "settomuss"
        session.commit()

    await message.reply(lang(user, "settomuss_wait"), parse_mode=ParseMode.MARKDOWN, reply_markup=key)


def load():
    logger.info("Load tomuss module")
    dp.register_message_handler(settomuss, lambda msg: msg.text.lower() == "settomuss")


def unload():
    logger.info("Unload tomuss module")
    dp.message_handlers.unregister(settomuss)
