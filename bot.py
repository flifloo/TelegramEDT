import asyncio
import datetime
import hashlib
import logging
import shelve
import re
import requests
from asyncio import sleep
from os import mkdir
from os.path import isdir, isfile
from threading import RLock

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle, ParseMode, reply_keyboard, ContentType
from aiogram.utils import markdown
from aiogram.utils.exceptions import MessageIsTooLong
from EDTcalendar import Calendar
from EDTuser import User, KFET_URL
from lang import lang
from ics.parse import ParseError
from requests.exceptions import ConnectionError, InvalidSchema, MissingSchema
from pyzbar.pyzbar import decode
from PIL import Image


if not isdir("logs"):
    mkdir("logs")

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
dp = Dispatcher(bot)
dbL = RLock()


def get_now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)


def calendar(time: str, user_id: int):
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            user = db[str(user_id)]
            if not user.resources:
                return lang(user, "edt_err_set")
            elif time not in TIMES:
                return lang(user, "edt_err_choice")
            return str(user.calendar(time))


async def notif():
    while True:
        with dbL:
            with shelve.open("edt", writeback=True) as db:
                for u in db:
                    nt = db[u].get_notif()
                    kf = db[u].get_kfet()
                    if nt:
                        await bot.send_message(int(u), lang(db[u], "notif_event")+str(nt), parse_mode=ParseMode.MARKDOWN)
                    if kf is not None:
                        if kf == 1:
                            kf = lang(db[u], "kfet")
                        elif kf == 2:
                            kf = lang(db[u], "kfet_prb")
                        else:
                            kf = lang(db[u], "kfet_err")
                        await bot.send_message(int(u), kf, parse_mode=ParseMode.MARKDOWN)
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


@dp.message_handler(commands="Start")
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} start : {message.text}")
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            if user_id not in db:
                lg = message.from_user.locale.language if message.from_user.locale.language else ""
                db[user_id] = User(int(user_id), lg)
            user = db[user_id]
    await message.reply(lang(user, "welcome"), parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="help")
async def help_cmd(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do help command: {message.text}")
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            user = db[str(message.from_user.id)]
    await message.reply(lang(user, "help"), parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="edt")
@dp.message_handler(lambda msg: msg.text.lower() in TIMES[1:])
async def edt_cmd(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do edt command: {message.text}")
    text = message.text.lower()
    if text[:4] == "/edt":
        text = text[5:]
    resp = calendar(text, message.from_user.id)
    key = reply_keyboard.ReplyKeyboardMarkup()
    key.add(reply_keyboard.KeyboardButton("Day"))
    key.add(reply_keyboard.KeyboardButton("Next"))
    key.add(reply_keyboard.KeyboardButton("Week"))
    key.add(reply_keyboard.KeyboardButton("Next week"))
    await message.reply(resp, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


@dp.message_handler(commands="kfet")
async def kfet(message: types.Message):
    user_id = str(message.from_user.id)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do kfet command: {message.text}")
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            if not 9 < get_now().hour < 14 or not get_now().isoweekday() < 6:
                msg = lang(db[user_id], "kfet_close")
            else:
                msg = lang(db[user_id], "kfet_list")
                cmds = requests.get(KFET_URL).json()
                if cmds:
                    for c in cmds:
                        msg += markdown.code(c) + " " if cmds[c]["statut"] == "T" else ""
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="setkfet")
async def kfet_set(message: types.Message):
    user_id = str(message.from_user.id)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do setkfet command: {message.text}")
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            if not 9 < get_now().hour < 14 or not get_now().isoweekday() < 5:
                msg = lang(db[user_id], "kfet_close")
            else:
                try:
                    int(message.text[9:])
                except ValueError:
                    msg = lang(db[user_id], "err_num")
                else:
                    db[user_id].kfet = int(message.text[9:])
                    msg = lang(db[user_id], "kfet_set")
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="setedt")
@dp.message_handler(content_types=ContentType.PHOTO)
async def edt_set(message: types.Message):
    user_id = str(message.from_user.id)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do setedt command: {message.text}")

    url = str()
    if message.photo and message.caption == "/setedt":
        file_path = await bot.get_file(message.photo[0].file_id)
        file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_path['file_path']}"
        qr = decode(Image.open(requests.get(file_url, stream=True).raw))
        if qr:
            url = str(qr[0].data)
    elif message.text:
        msg_url = re.findall("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", message.text)
        if msg_url:
            url = msg_url[0]
    
    if url:
        resources = url[url.find("resources")+10:][:4]
    elif message.text:
        resources = message.text[8:]

    with dbL:
        with shelve.open("edt", writeback=True) as db:
            try:
                Calendar("", int(resources))
            except (ParseError, ConnectionError, InvalidSchema, MissingSchema, ValueError, UnboundLocalError):
                msg = lang(db[user_id], "setedt_err_res")
            else:
                db[user_id].resources = int(resources)
                msg = lang(db[user_id], "setedt")

            await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="getedt")
async def edt_geturl(message: types.Message):
    user_id = str(message.from_user.id)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do getedt command: {message.text}")
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            if db[user_id].resources:
                await message.reply(db[user_id].resources)
            else:
                await message.reply(lang(db[user_id], "getedt_err"))


@dp.message_handler(commands="notif")
async def notif_cmd(message: types.Message):
    user_id = str(message.from_user.id)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do notif command: {message.text}")
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            if message.text[7:13] == "toggle":
                if db[user_id].nt:
                    res = False
                else:
                    res = True

                db[user_id].nt = res
                msg = lang(db[user_id], "notif_set").format(res)

            elif message.text[7:11] == "time" or message.text[7:15] == "cooldown":
                cut = 11 if message.text[7:11] == "time" else 15
                try:
                    int(message.text[cut+1:])
                except ValueError:
                    msg = lang(db[user_id], "err_num")
                else:
                    if cut == 11:
                        db[user_id].nt_time = int(message.text[cut+1:])
                    else:
                        db[user_id].nt_cooldown = int(message.text[cut + 1:])

                    msg = lang(db[user_id], "notif_time_cooldown").format(message.text[7:cut], message.text[cut + 1:])

            elif message.text[7:11] == "info":
                msg = lang(db[user_id], "notif_info").format(db[user_id].nt, db[user_id].nt_time,
                                                             db[user_id].nt_cooldown)

            elif message.text[7:] == "":
                msg = lang(db[user_id], "notif_help")
            else:
                msg = lang(db[user_id], "notif_err_act")

            await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="getid")
async def get_id(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do getid command: {message.text}")
    await message.reply(message.from_user.id)


@dp.message_handler(commands="getlogs")
async def get_logs(message: types.Message):
    logger.info(f"{message.from_user.username} do getlog command: {message.text}")
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
    logger.info(f"{message.from_user.username} do getdb command: {message.text}")
    if message.from_user.id == ADMIN_ID:
        with dbL:
            with shelve.open("edt") as db:
                msg = markdown.text(
                    markdown.italic("db:"),
                    markdown.code(dict(db)),
                    sep="\n"
                )
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="eval")
async def eval_cmd(message: types.Message):
    logger.info(f"{message.from_user.username} do eval command: {message.text}")
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
