import asyncio
import datetime
import hashlib
import logging
import shelve
from asyncio import sleep
from os import mkdir
from os.path import isdir, isfile
from threading import RLock

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle, ParseMode, reply_keyboard
from aiogram.utils import markdown
from aiogram.utils.exceptions import MessageIsTooLong
from EDTcalendar import Calendar
from ics.parse import ParseError
from requests.exceptions import ConnectionError, InvalidSchema, MissingSchema


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
API_TOKEN = open("token.ini").read()
ADMIN_ID = 148441652
TIMES = ["", "day", "next", "week", "next week"]

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dbL = RLock()


def calendar(time: str, user_id: int):
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            if str(user_id) not in db or "resources" not in db[str(user_id)]:
                return markdown.bold("Your EDT is not set ! ❌")
            elif time not in TIMES:
                return markdown.bold("Invalid choice ! ❌")
            return str(Calendar(time, db[str(user_id)]["resources"]))


async def notif():
    while True:
        with dbL:
            with shelve.open("edt", writeback=True) as db:
                for u in db:
                    if ("resources" in db[u]) and ("notif" in db[u]) and (db[u]["notif"]["state"]):
                        logger.info(f"notif check for {u}")
                        now = datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)
                        c = Calendar("day", db[u]["resources"], pass_week=False)
                        for e in c.timeline:
                            logger.info(f"{(e.begin - now).total_seconds().__abs__()//60.} <= {db[u]['notif']['time']} and {(now - db[u]['notif']['last']).total_seconds()//60} | >= {db[u]['notif']['cooldown']}")
                            logger.info(f"{(e.begin - now).total_seconds().__abs__()//60 <= db[u]['notif']['time']} and {(now - db[u]['notif']['last']).total_seconds()//60 >= db[u]['notif']['cooldown']}")
                            if (e.begin - now).total_seconds().__abs__()//60 <= db[u]["notif"]["time"] and\
                                    (now - db[u]["notif"]["last"]).total_seconds()//60 >= db[u]["notif"]["cooldown"]:
                                db[u]["notif"]["last"] = now
                                await bot.send_message(int(u), e, parse_mode=ParseMode.MARKDOWN)
        await sleep(60)


@dp.inline_handler()
async def inline_echo(inline_query: InlineQuery):
    text = inline_query.query.lower() if inline_query.query.lower() not in TIMES else "invalid"
    res = calendar(text, inline_query.from_user.id)
    input_content = InputTextMessageContent(res, parse_mode=ParseMode.MARKDOWN)
    result_id: str = hashlib.md5(res.encode()).hexdigest()
    item = InlineQueryResultArticle(
        id=result_id,
        title=f"Your {text} course",
        input_message_content=input_content,
    )
    await bot.answer_inline_query(inline_query.id, results=[item], cache_time=1)


@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do start/help command: {message.text}")
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            if str(message.from_user.id) not in db:
                db[str(message.from_user.id)] = dict()
                logger.info(f"db creation for {message.from_user.username}")

    msg = markdown.text(
        markdown.text("💠 Welcome to the TelegramEDT, a calendar bot for the Lyon 1 University ! 💠\n"),
        markdown.text(
            markdown.text("🗓"),
            markdown.code("/edt [day | next | week | next week]"),
            markdown.text(", for show your next course")
        ),
        markdown.text(
            markdown.text("🔔"),
            markdown.code("/notif <set | info | time number | cooldown number>"),
            markdown.text(", setup notifications")
        ),
        markdown.text(
            markdown.text("⚙️"),
            markdown.code("/setedt <resources>"),
            markdown.text(", to setup your calendar\nThe resources can be get on the url of exported calendar")
        ),
        markdown.text(
            markdown.text("🔗"),
            markdown.code("/getedt"),
            markdown.text(", to get your calendar url")
        ),
        markdown.text(
            markdown.text("ℹ️"),
            markdown.code("/help"),
            markdown.text(", to show this command")
        ),
        sep="\n"
    )
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=["edt"])
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


@dp.message_handler(commands=["setedt"])
async def edt_set(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do setedt command: {message.text}")
    resources = message.text[8:]

    try:
        Calendar("", int(resources))
    except (ParseError, ConnectionError, InvalidSchema, MissingSchema, ValueError):
        msg = markdown.bold("Invalid resources ! ❌")
    else:
        with dbL:
            with shelve.open("edt", writeback=True) as db:
                db[str(message.from_user.id)]["resources"] = int(resources)
        msg = markdown.text("EDT set ✅")

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=["getedt"])
async def edt_geturl(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do getedt command: {message.text}")
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            if (str(message.from_user.id) in db) and ("resources" in db[str(message.from_user.id)]):
                await message.reply(db[str(message.from_user.id)]["resources"])
            else:
                await message.reply("No EDT set ! ❌")


@dp.message_handler(commands=["notif"])
async def notif_cmd(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do notif command: {message.text}")
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            if "notif" not in db[str(message.from_user.id)]:
                db[str(message.from_user.id)]["notif"] = dict()
                db[str(message.from_user.id)]["notif"]["state"] = False
                db[str(message.from_user.id)]["notif"]["time"] = 20
                db[str(message.from_user.id)]["notif"]["cooldown"] = 20
                last = datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None) - datetime.timedelta(minutes=20)
                db[str(message.from_user.id)]["notif"]["last"] = last

            if message.text[7:10] == "set":
                if db[str(message.from_user.id)]["notif"]["state"]:
                    res = False
                else:
                    res = True

                db[str(message.from_user.id)]["notif"]["state"] = res

                msg = markdown.text(
                    markdown.text("Notifications set on "),
                    markdown.code(res),
                    markdown.text("✅")
                )
            elif message.text[7:11] == "time" or message.text[7:15] == "cooldown":
                cut = 11 if message.text[7:11] == "time" else 15
                try:
                    int(message.text[cut+1:])
                except ValueError:
                    msg = markdown.bold("Invalid number ! ❌")
                else:
                    db[str(message.from_user.id)]["notif"][message.text[7:cut]] = int(message.text[cut+1:])

                    msg = markdown.text(
                        markdown.text("Notification"),
                        markdown.code(message.text[7:cut]),
                        markdown.text("set to"),
                        markdown.bold(message.text[cut+1:]),
                        markdown.text("✅")
                    )
            elif message.text[7:11] == "info":
                msg = markdown.text(
                    markdown.code("Notification:"),
                    markdown.text(
                      markdown.bold("State:"),
                      markdown.text(db[str(message.from_user.id)]["notif"]["state"])
                    ),
                    markdown.text(
                        markdown.bold("Time:"),
                        markdown.text(db[str(message.from_user.id)]["notif"]["time"])
                    ),
                    markdown.text(
                        markdown.bold("Cooldown:"),
                        markdown.text(db[str(message.from_user.id)]["notif"]["cooldown"])
                    ),
                    sep="\n"
                )
            else:
                msg = markdown.bold("Invalid action ! ❌")

            await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=["getid"])
async def get_id(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do getid command: {message.text}")
    await message.reply(message.from_user.id)


@dp.message_handler(commands=["getlogs"])
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


@dp.message_handler(commands=["getdb"])
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


@dp.message_handler(commands=["eval"])
async def get_db(message: types.Message):
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
