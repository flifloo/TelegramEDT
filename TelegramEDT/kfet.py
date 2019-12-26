import datetime

import requests
from aiogram import types
from aiogram.types import ParseMode
from aiogram.utils import markdown

from TelegramEDT import dbL, dp, key, logger, session, check_id
from TelegramEDT.base import User, KFET_URL
from TelegramEDT.lang import lang


def get_now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)


async def kfet(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do kfet")
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        if not 9 < get_now().hour < 14 or not get_now().isoweekday() < 6:
            msg = lang(user, "kfet_close")
        else:
            msg = lang(user, "kfet_list")
            cmds = requests.get(KFET_URL).json()
            if cmds:
                for c in cmds:
                    msg += markdown.code(c) + " " if cmds[c] == "ok" else ""
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def kfet_set(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do setkfet")
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        if not 9 < get_now().hour < 14 or not get_now().isoweekday() < 5:
            msg = lang(user, "kfet_close")
        else:
            user.await_cmd = "setkfet"
            msg = lang(user, "kfet_set_await")
            session.commit()

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


def load():
    logger.info("Load kfet module")
    dp.register_message_handler(kfet, lambda msg: msg.text.lower() == "kfet")
    dp.register_message_handler(kfet_set, lambda msg: msg.text.lower() == "setkfet")


def unload():
    logger.info("Unload kfet module")
    dp.message_handlers.unregister(kfet)
    dp.message_handlers.unregister(kfet_set)
