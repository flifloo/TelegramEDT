import re

import requests
from PIL import Image
from aiogram import types
from aiogram.types import ParseMode
from feedparser import parse
from ics.parse import ParseError
from pyzbar.pyzbar import decode
from requests.exceptions import ConnectionError, InvalidSchema, MissingSchema

from TelegramEDT import API_TOKEN, bot, dbL, key, logger, session, check_id
from TelegramEDT.EDTcalendar import Calendar
from TelegramEDT.base import User
from TelegramEDT.lang import lang

re_url = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")


def have_await_cmd(msg: types.Message):
    with dbL:
        user = session.query(User).filter_by(id=msg.from_user.id).first()
        return user and user.await_cmd


async def await_cmd(message: types.message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    msg = None
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        logger.info(f"{message.from_user.username} do awaited commande: {user.await_cmd}")
        if user.await_cmd == "setedt":
            url = str()
            if message.photo:
                file_path = await bot.get_file(message.photo[0].file_id)
                file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_path['file_path']}"
                qr = decode(Image.open(requests.get(file_url, stream=True).raw))
                if qr:
                    url = str(qr[0].data)
            elif message.text:
                msg_url = re_url.findall(message.text)
                if msg_url:
                    url = msg_url[0]

            if url:
                resources = url[url.find("resources") + 10:][:4]
            elif message.text:
                resources = message.text

            try:
                Calendar("", int(resources))
            except (ParseError, ConnectionError, InvalidSchema, MissingSchema, ValueError, UnboundLocalError):
                msg = lang(user, "setedt_err_res")
            else:
                user.resources = int(resources)
                msg = lang(user, "setedt")

        elif user.await_cmd == "setkfet":
            try:
                int(message.text)
            except ValueError:
                msg = lang(user, "err_num")
            else:
                user.kfet = int(message.text)
                msg = lang(user, "kfet_set")

        elif user.await_cmd == "settomuss":
            if not len(parse(message.text).entries):
                msg = lang(user, "settomuss_error")
            else:
                user.tomuss_rss = message.text
                msg = lang(user, "settomuss")

        elif user.await_cmd in ["time", "cooldown"]:
            try:
                value = int(message.text)
            except ValueError:
                msg = lang(user, "err_num")
            else:
                if user.await_cmd == "time":
                    user.nt_time = value
                else:
                    user.nt_cooldown = value

                msg = lang(user, "notif_time_cooldown").format(user.await_cmd[6:], value)

        if user.await_cmd:
            user.await_cmd = str()
            session.commit()

    if msg:
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)
