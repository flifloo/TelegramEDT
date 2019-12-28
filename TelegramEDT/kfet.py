import datetime

import requests
from aiogram import types
from aiogram.types import ParseMode
from aiogram.utils import markdown

from TelegramEDT import dp, key, logger, Session, check_id, modules_active, bot
from TelegramEDT.base import User, KFET_URL
from TelegramEDT.lang import lang

module_name = "kfet"
logger = logger.getChild(module_name)


def get_now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)


def have_await_cmd(msg: types.Message):
    with Session as session:
        user = session.query(User).filter_by(id=msg.from_user.id).first()
        return user and user.await_cmd == "setkfet"


async def kfet(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do kfet")
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        if not 9 < get_now().hour < 14 or not get_now().isoweekday() < 6:
            msg = lang(user, "kfet_close")
        else:
            msg = lang(user, "kfet_list")
            try:
                cmds = requests.get(KFET_URL).json()
            except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
                msg = markdown.bold(lang(user, "kfet_error"))
            else:
                if cmds:
                    for c in cmds:
                        msg += markdown.code(c) + " " if cmds[c] == "ok" else ""
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def kfet_set(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do setkfet")
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        if not 9 < get_now().hour < 14 or not get_now().isoweekday() < 5:
            msg = lang(user, "kfet_close")
        else:
            user.await_cmd = "setkfet"
            msg = lang(user, "kfet_set_await")
            session.commit()

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def await_cmd(message: types.message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        logger.info(f"{message.from_user.username} do awaited command")
        try:
            int(message.text)
        except ValueError:
            msg = lang(user, "err_num")
        else:
            user.kfet = int(message.text)
            msg = lang(user, "kfet_set")
        user.await_cmd = str()
        session.commit()
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def notif():
    with Session as session:
        for u in session.query(User).all():
            try:
                kf = u.get_kfet()
            except Exception as e:
                logger.error(e)
            else:
                if kf is not None:
                    if kf == 1:
                        kf = lang(u, "kfet")
                    elif kf == 2:
                        kf = lang(u, "kfet_prb")
                    else:
                        kf = lang(u, "kfet_err")
                    await bot.send_message(u.id, kf, parse_mode=ParseMode.MARKDOWN)


def load():
    logger.info(f"Load {module_name} module")
    dp.register_message_handler(kfet, lambda msg: msg.text.lower() == "kfet")
    dp.register_message_handler(kfet_set, lambda msg: msg.text.lower() == "setkfet")
    dp.register_message_handler(await_cmd, lambda msg: have_await_cmd(msg))
    modules_active.append(module_name)


def unload():
    logger.info(f"Unload {module_name} module")
    dp.message_handlers.unregister(kfet)
    dp.message_handlers.unregister(kfet_set)
    dp.message_handlers.unregister(await_cmd)
    modules_active.remove(module_name)
