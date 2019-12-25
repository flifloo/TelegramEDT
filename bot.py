import asyncio
import datetime
import hashlib
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import re
import requests
from asyncio import sleep
from os import mkdir
from os.path import isdir, isfile
from threading import RLock

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineQuery, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, ParseMode, reply_keyboard, ContentType
from aiogram.utils import markdown
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageIsTooLong
from EDTcalendar import Calendar
from base import User, KFET_URL, Base
from lang import lang
from ics.parse import ParseError
from requests.exceptions import ConnectionError, InvalidSchema, MissingSchema
from pyzbar.pyzbar import decode
from PIL import Image
from feedparser import parse

tables = False
if not isdir("logs"):
    mkdir("logs")
if not isdir("calendars"):
    mkdir("calendars")
if not isfile("edt.db"):
    tables = True

logger = logging.getLogger("TelegramEDT")
log_date = datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None).date()
logging.basicConfig(
    filename=f"logs/{log_date}.log",
    format="{%(levelname)s}[%(asctime)s]: %(name)s | %(message)s",
    level=logging.INFO,
)

if not isfile("token.ini"):
    logger.critical("No token specified, impossible to start the bot !")
    exit(1)
API_TOKEN = open("token.ini").readline().replace("\n", "")
ADMIN_ID = 148441652
TIMES = ["", "day", "next", "week", "next week"]

bot = Bot(token=API_TOKEN)
posts_cb = CallbackData("post", "id", "action")
dp = Dispatcher(bot)
engine = create_engine("sqlite:///edt.db")
Session = sessionmaker(bind=engine)
session = Session()
if tables:
    Base.metadata.create_all(engine)
dbL = RLock()


def get_now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)


def have_await_cmd(msg: types.Message):
    with dbL:
        return session.query(User).filter_by(id=msg.from_user.id).first().await_cmd


def edt_key():
    key = InlineKeyboardMarkup()
    for i, n in enumerate(["Day", "Next", "Week", "Next week"]):
        key.add(InlineKeyboardButton(n, callback_data=posts_cb.new(id=i, action=n.lower())))
    return key


def calendar(time: str, user_id: int):
    with dbL:
        user = session.query(User).filter_by(id=user_id).first()
        if not user.resources:
            return lang(user, "edt_err_set")
        elif time not in TIMES:
            return lang(user, "edt_err_choice")
        return str(user.calendar(time))


async def notif():
    while True:
        with dbL:
            for u in session.query(User).all():
                nt = None
                kf = None
                tm = None
                try:
                    nt = u.get_notif()
                    kf = u.get_kfet()
                    tm = u.get_tomuss()
                except:
                    pass

                if nt:
                    await bot.send_message(u.id, lang(u, "notif_event")+str(nt), parse_mode=ParseMode.MARKDOWN)
                if kf:
                    if kf == 1:
                        kf = lang(u, "kfet")
                    elif kf == 2:
                        kf = lang(u, "kfet_prb")
                    else:
                        kf = lang(u, "kfet_err")
                    await bot.send_message(u.id, kf, parse_mode=ParseMode.MARKDOWN)
                if tm:
                    for i in tm:
                        msg = markdown.text(
                            markdown.bold(i.title),
                            markdown.code(i.summary.replace("<br>", "\n").replace("<b>", "").replace("</b>", "")),
                            sep="\n"
                        )
                        await bot.send_message(u.id, msg, parse_mode=ParseMode.MARKDOWN)
                    u.tomuss_last = str(i)
            session.commit()

        await sleep(60)


@dp.inline_handler()
async def inline_edt(inline_query: InlineQuery):
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


@dp.message_handler(commands="start")
async def start(message: types.Message):
    user_id = message.from_user.id
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} start")
    with dbL:
        if user_id not in session.query(User.id).all():
            logger.info(f"{message.from_user.username} add to the db")
            if message.from_user.locale and message.from_user.locale.language:
                lg = message.from_user.locale.language
            else:
                lg = ""
            session.add(User(id=user_id, language=lg))
            session.commit()
        user = session.query(User).filter_by(id=user_id).first()
    key = reply_keyboard.ReplyKeyboardMarkup()
    key.add(reply_keyboard.KeyboardButton("Edt"))
    key.add(reply_keyboard.KeyboardButton("Kfet"))
    key.add(reply_keyboard.KeyboardButton("Setkfet"))
    key.add(reply_keyboard.KeyboardButton("Setedt"))
    key.add(reply_keyboard.KeyboardButton("Notif"))
    key.add(reply_keyboard.KeyboardButton("Settomuss"))
    await message.reply(lang(user, "welcome"), parse_mode=ParseMode.MARKDOWN, reply_markup=key)


@dp.message_handler(commands="help")
async def help_cmd(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do help command")
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
    await message.reply(lang(user, "help"), parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(lambda msg: msg.text.lower() == "edt")
async def edt_cmd(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do edt")
    await message.reply(calendar("day", message.from_user.id), parse_mode=ParseMode.MARKDOWN, reply_markup=edt_key())


@dp.callback_query_handler(posts_cb.filter(action=["day", "next", "week", "next week"]))
async def edt_query(query: types.CallbackQuery, callback_data: dict):
    await query.message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{query.message.from_user.username} do edt query")
    await query.message.reply(calendar(callback_data["action"], query.from_user.id), parse_mode=ParseMode.MARKDOWN, reply_markup=edt_key())


@dp.message_handler(lambda msg: msg.text.lower() == "kfet")
async def kfet(message: types.Message):
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
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(lambda msg: msg.text.lower() == "setkfet")
async def kfet_set(message: types.Message):
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

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(lambda msg: msg.text.lower() == "setedt")
async def edt_await(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do setedt")
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        user.await_cmd = "setedt"
        session.commit()

    await message.reply(lang(user, "setedt_wait"), parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(lambda msg: msg.text.lower() == "settomuss")
async def edt_await(message: types.Message):
    user_id = str(message.from_user.id)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do settomuss")
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        user.await_cmd = "settomuss"
        session.commit()

    await message.reply(lang(user, "settomuss_wait"), parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="getedt")
async def edt_geturl(message: types.Message):
    user_id = str(message.from_user.id)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do getedt command")
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        if user.resources:
            await message.reply(user.resources)
        else:
            await message.reply(lang(user, "getedt_err"))


@dp.message_handler(lambda msg: msg.text.lower() == "notif")
async def notif_cmd(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do notif")
    key = InlineKeyboardMarkup()
    for i, n in enumerate(["Toggle", "Time", "Cooldown"]):
        key.add(InlineKeyboardButton(n, callback_data=posts_cb.new(id=i, action=n.lower())))
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        msg = lang(user, "notif_info").format(user.nt, user.nt_time, user.nt_cooldown)
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


@dp.callback_query_handler(posts_cb.filter(action=["toggle", "time", "cooldown"]))
async def notif_query(query: types.CallbackQuery, callback_data: dict):
    await query.message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{query.message.from_user.username} do notif query")
    with dbL:
        user = session.query(User).filter_by(id=query.from_user.id).first()
        if callback_data["action"] == "toggle":
            if user.nt:
                res = False
            else:
                res = True

            user.nt = res
            msg = lang(user, "notif_set").format(res)

        elif callback_data["action"] in ["time", "cooldown"]:
            user.await_cmd = callback_data["action"]
            msg = lang(user, "notif_await")
        session.commit()

    await query.message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(lambda msg: have_await_cmd(msg), content_types=[ContentType.TEXT, ContentType.PHOTO])
async def await_cmd(message: types.message):
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
                msg_url = re.findall(
                    "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", message.text)
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
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="getid")
async def get_id(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do getid command")
    await message.reply(message.from_user.id)


@dp.message_handler(commands="getlogs")
async def get_logs(message: types.Message):
    logger.info(f"{message.from_user.username} do getlog command")
    if message.from_user.id == ADMIN_ID:
        try:
            int(message.text[9:])
        except ValueError:
            await message.chat.do(types.ChatActions.UPLOAD_DOCUMENT)
            await message.reply_document(types.InputFile(f"logs/{log_date}.log"), caption=f"The {log_date} logs")
        else:
            await message.chat.do(types.ChatActions.TYPING)
            logs = (open(f"logs/{log_date}.log", "r").readlines())[-int(message.text[9:]):]
            log = str()
            for i in logs:
                log += i
            msg = markdown.text(
                markdown.italic("logs:"),
                markdown.code(log),
                sep="\n"
            )
            try:
                await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
            except MessageIsTooLong:
                await message.reply(markdown.bold("Too much logs ! ❌"))


@dp.message_handler(commands="getdb")
async def get_db(message: types.Message):
    logger.info(f"{message.from_user.username} do getdb command")
    if message.from_user.id == ADMIN_ID:
        with dbL:
            users = dict()
            for u in session.query(User).all():
                users[u] = u.__dict__
            msg = markdown.text(
                markdown.italic("db:"),
                markdown.code(users),
                sep="\n"
            )
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="eval")
async def eval_cmd(message: types.Message):
    logger.info(f"{message.from_user.username} do eval command")
    if message.from_user.id == ADMIN_ID:
        msg = markdown.text(
            markdown.italic("eval:"),
            markdown.code(eval(message.text[6:])),
            sep="\n"
        )
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.errors_handler()
async def errors(*args, **partial_data):
    msg = markdown.text(
        markdown.bold("⚠️ An error occurred:"),
        markdown.code(args),
        markdown.code(partial_data),
        sep="\n"
    )
    await bot.send_message(ADMIN_ID, msg, parse_mode=ParseMode.MARKDOWN)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(notif())
    loop.create_task(executor.start_polling(dp, skip_updates=True))
    loop.run_forever()
