import logging, shelve, datetime, hashlib, asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle, ParseMode, reply_keyboard
from aiogram.utils import markdown
from ics import Calendar
from ics.parse import ParseError
from requests import get
from requests.exceptions import ConnectionError, InvalidSchema, MissingSchema
from threading import RLock
from asyncio import sleep
from os import mkdir
from os.path import isdir, isfile


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

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dbL = RLock()


def edt(text, user_id):
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            if str(user_id) not in db or "url" not in db[str(user_id)]:
                return markdown.bold("Your EDT is not set ! ❌")
            now = datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)
            if text.lower() == "week":
                firstdate = now.date() - datetime.timedelta(days=now.isoweekday()-1)
                lastdate = now.date() + datetime.timedelta(days=(7 - now.isoweekday()))
            elif text.lower() == "next":
                now += datetime.timedelta(days=7)
                firstdate = now.date() - datetime.timedelta(days=now.isoweekday())
                lastdate = now.date() + datetime.timedelta(days=(7 - now.isoweekday()))
            elif text == "" or text.lower() == "day":
                firstdate, lastdate = now.date(), now.date()
            else:
                return markdown.bold("Invalid choice ! ❌")

            url = f"{db[str(user_id)]['url']}&firstDate={firstdate}&lastDate={lastdate}"
            c = Calendar(get(url).text)
            msg = list()
            days = list()

            for e in list(c.timeline):
                begin = e.begin.datetime.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
                end = e.end.datetime.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
                if begin.date() not in days:
                    days.append(begin.date())
                    msg.append(markdown.bold(f"<{str(begin.date())[5:]}>"))

                msg.append(markdown.code(f"📓[{e.name}]:"))
                msg.append(markdown.text(f"⌚️ {str(begin.time())[:-3]} -> {str(end.time())[:-3]}"))
                prof = markdown.text(e.description.split('\n')[3])
                msg.append(markdown.italic(f"📍 {e.location} 👨‍🏫 {prof}" + "\n"))

            if len(msg) == 0:
                msg.append(markdown.italic("but nobody came..."))
            return markdown.text(*msg, sep="\n")


async def notif():
    while True:
        with dbL:
            with shelve.open("edt", writeback=True) as db:
                for u in db:
                    if ("url" in db[u]) and ("notif" in db[u]) and (db[u]["notif"]["state"]):
                        now = datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)
                        c = Calendar(get(f"{db[u]['url']}&firstDate={now.date()}&lastDate={now.date()}").text)
                        for e in c.events:
                            event = e.begin.datetime.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
                            if (event - now).seconds/60 <= db[u]["notif"]["time"] and\
                                    (now - db[u]["notif"]["last"]).seconds/60 >= db[u]["notif"]["cooldown"]:
                                db[u]["notif"]["last"] = now

                                msg = markdown.text(
                                    markdown.text("🔔"),
                                    markdown.code(e.name),
                                    markdown.text("in"),
                                    markdown.bold((event - now).seconds//60),
                                    markdown.text("minutes !"),
                                    sep="\n"
                                )
                                await bot.send_message(int(u), msg, parse_mode=ParseMode.MARKDOWN)
        await sleep(60)


@dp.inline_handler()
async def inline_echo(inline_query: InlineQuery):
    text = inline_query.query
    if text not in ["day", "week", "next", ""]:
        text = "invalid"
    res = edt(text, inline_query.from_user.id)
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
            markdown.code("/edt [day | week | next]"),
            markdown.text(", for show your next course")
        ),
        markdown.text(
            markdown.text("🔔"),
            markdown.code("/notif <set | info | time number | cooldown number>"),
            markdown.text(", setup notifications")
        ),
        markdown.text(
            markdown.text("⚙️"),
            markdown.code("/setedt <url>"),
            markdown.text(", to setup your calendar")
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
@dp.message_handler(lambda msg: msg.text.lower() in ["day", "week", "next"])
async def edt_cmd(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do edt command: {message.text}")
    text = message.text
    if message.text[:4] == "/edt":
        text = message.text[5:]
    resp = edt(text, message.from_user.id)
    key = reply_keyboard.ReplyKeyboardMarkup()
    key.add(reply_keyboard.KeyboardButton("Day"))
    key.add(reply_keyboard.KeyboardButton("Week"))
    key.add(reply_keyboard.KeyboardButton("Next"))
    await message.reply(resp, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


@dp.message_handler(commands=["setedt"])
async def edt_set(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do setedt command: {message.text}")
    url_http = message.text.find("http")
    url_end = message.text.find(" ", url_http)
    if url_end == -1:
        url_end = None
    url = message.text[url_http:url_end]

    try:
        Calendar(get(url).text)
    except (ParseError, ConnectionError, InvalidSchema, MissingSchema, ValueError):
        msg = markdown.bold("Invalid URL ! ❌")
    else:
        if "calType=vcal" in url:
            url = url[:url.find("vcal")] + "ical"
        elif "firstDate" in url:
            url = url[:url.find("&firstDate")]

        with dbL:
            with shelve.open("edt", writeback=True) as db:
                db[str(message.from_user.id)]["url"] = url
        msg = markdown.text("EDT set ✅")

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=["getedt"])
async def edt_geturl(message: types.Message):
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do getedt command: {message.text}")
    with dbL:
        with shelve.open("edt", writeback=True) as db:
            if (str(message.from_user.id) in db) and ("url" in db[str(message.from_user.id)]):
                await message.reply(db[str(message.from_user.id)]["url"])
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
        await message.chat.do(types.ChatActions.UPLOAD_DOCUMENT)
        await message.reply_document(types.InputFile(f"logs/{log_date}.log"), caption=f"The {log_date} logs")


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
