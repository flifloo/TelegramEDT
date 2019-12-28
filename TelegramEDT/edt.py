import hashlib
import re

import requests
from PIL import Image
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputTextMessageContent, \
    InlineQueryResultArticle, InlineQuery, ContentType
from aiogram.types import ParseMode
from ics.parse import ParseError, string_to_container
from pyzbar.pyzbar import decode
from requests.exceptions import ConnectionError, InvalidSchema, MissingSchema

from TelegramEDT import API_TOKEN, TIMES, bot, dp, key, logger, Session, check_id, posts_cb, modules_active
from TelegramEDT.EDTcalendar import Calendar
from TelegramEDT.base import User
from TelegramEDT.lang import lang

module_name = "edt"
logger = logger.getChild(module_name)
re_url = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")


def calendar(time: str, user_id: int):
    with Session as session:
        user = session.query(User).filter_by(id=user_id).first()
        if not user.resources:
            return lang(user, "edt_err_set")
        elif time not in TIMES:
            return lang(user, "edt_err_choice")
        return str(user.calendar(time))


def edt_key():
    keys = InlineKeyboardMarkup()
    for i, n in enumerate(["Day", "Next", "Week", "Next week"]):
        keys.add(InlineKeyboardButton(n, callback_data=posts_cb.new(id=i, action=n.lower())))
    return keys


def have_await_cmd(msg: types.Message):
    with Session as session:
        user = session.query(User).filter_by(id=msg.from_user.id).first()
        return user and user.await_cmd == "setedt"


async def edt_cmd(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do edt")
    await message.reply(calendar("day", message.from_user.id), parse_mode=ParseMode.MARKDOWN, reply_markup=edt_key())


async def inline_edt(inline_query: InlineQuery):
    check_id(inline_query.from_user)
    text = inline_query.query.lower() if inline_query.query.lower() in TIMES else "invalid"
    res = calendar(text, inline_query.from_user.id)
    input_content = InputTextMessageContent(res, parse_mode=ParseMode.MARKDOWN)
    result_id: str = hashlib.md5(res.encode()).hexdigest()
    item = InlineQueryResultArticle(
        id=result_id,
        title=f"Your {text} course",
        input_message_content=input_content,
    )
    await bot.answer_inline_query(inline_query.id, results=[item], cache_time=1)


async def edt_query(query: types.CallbackQuery, callback_data: dict):
    check_id(query.message.from_user)
    await query.message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{query.message.from_user.username} do edt query")
    await query.message.reply(calendar(callback_data["action"], query.from_user.id), parse_mode=ParseMode.MARKDOWN,
                              reply_markup=edt_key())


async def edt_await(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do setedt")
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        user.await_cmd = "setedt"
        session.commit()
        msg = lang(user, "setedt_wait")

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def await_cmd(message: types.message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        logger.info(f"{message.from_user.username} do edt awaited command")
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
            string_to_container(requests.get(Calendar("", int(resources)).url).text)

        except (ParseError, ConnectionError, InvalidSchema, MissingSchema, ValueError, UnboundLocalError):
            msg = lang(user, "setedt_err_res")
        else:
            user.resources = int(resources)
            msg = lang(user, "setedt")
        user.await_cmd = str()
        session.commit()
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def edt_geturl(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do getedt command")
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        if user.resources:
            msg = user.resources
        else:
            msg = lang(user, "getedt_err")

    await message.reply(msg, reply_markup=key)


def load():
    logger.info(f"Load {module_name} module")
    dp.register_message_handler(edt_cmd, lambda msg: msg.text.lower() == "edt")
    dp.register_inline_handler(inline_edt)
    dp.register_callback_query_handler(edt_query, posts_cb.filter(action=["day", "next", "week", "next week"]))
    dp.register_message_handler(edt_await, lambda msg: msg.text.lower() == "setedt")
    dp.register_message_handler(await_cmd, lambda msg: have_await_cmd(msg), content_types=[ContentType.TEXT,
                                                                                           ContentType.PHOTO])
    dp.register_message_handler(edt_geturl, commands="getedt")
    modules_active.append(module_name)


def unload():
    logger.info(f"Unload {module_name} module")
    dp.message_handlers.unregister(edt_cmd)
    dp.inline_query_handlers.unregister(inline_edt)
    dp.callback_query_handlers.unregister(edt_query)
    dp.message_handlers.unregister(edt_await)
    dp.message_handlers.unregister(await_cmd)
    dp.message_handlers.unregister(edt_geturl)
    modules_active.remove(module_name)
