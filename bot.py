import logging, shelve, datetime, hashlib
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle, ParseMode, reply_keyboard
from aiogram.utils import markdown
from ics import Calendar
from ics.parse import ParseError
from requests import get
from requests.exceptions import ConnectionError, InvalidSchema, MissingSchema
from threading import RLock

API_TOKEN = open("token.ini").read()
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dbL = RLock()


def edt(text, user_id):
    with dbL:
        with shelve.open("edt") as db:
            if not str(user_id) in db:
                return markdown.bold("Your EDT is not set !")
            now = datetime.datetime.now()
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
                return markdown.bold("Invalid choice !")

            url = f"{db[str(user_id)]}&firstDate={firstdate}&lastDate={lastdate}"
            c = Calendar(get(url).text)
            msg = list()
            days = list()

            for e in list(c.timeline):
                begin = e.begin.datetime
                end = e.end.datetime
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


@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    msg = markdown.text(
        markdown.text("💠 Welcome to the TelegramEDT, a calendar bot for the Lyon 1 University ! 💠\n"),
        markdown.text(markdown.code("/edt [day | week | next]"), markdown.text(", for show your next course")),
        markdown.text(markdown.code("/setedt <url>"), markdown.text(", to setup your calendar")),
        markdown.text(markdown.code("/getedt"), markdown.text(", to get your calendar url")),
        markdown.text(markdown.code("/help"), markdown.text(", to show this command")),
        sep="\n"
    )
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=["edt"])
@dp.message_handler(lambda msg: msg.text.lower() in ["day", "week", "next"])
async def edt_cmd(message: types.Message):
    text = message.text
    if message.text[:4] == "/edt":
        text = message.text[5:]
    resp = edt(text, message.from_user.id)
    key = reply_keyboard.ReplyKeyboardMarkup()
    key.add(reply_keyboard.KeyboardButton("Day"))
    key.add(reply_keyboard.KeyboardButton("Week"))
    key.add(reply_keyboard.KeyboardButton("Next"))
    await message.reply(resp, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


@dp.inline_handler()
async def inline_echo(inline_query: InlineQuery):
    text = inline_query.query
    if text not in ["week", "next", ""]:
        text = "invalid"
    res = edt(text, inline_query.from_user.id)
    input_content = InputTextMessageContent(res)
    result_id: str = hashlib.md5(res.encode()).hexdigest()
    item = InlineQueryResultArticle(
        id=result_id,
        title=f"Your {text} course",
        input_message_content=input_content
    )
    await bot.answer_inline_query(inline_query.id, results=[item], cache_time=1)


@dp.message_handler(commands=["setedt"])
async def edt_set(message: types.Message):
    url_http = message.text.find("http")
    url_end = message.text.find(" ", url_http)
    if url_end == -1:
        url_end = None
    url = message.text[url_http:url_end]

    try:
        Calendar(get(url).text)
    except (ParseError, ConnectionError, InvalidSchema, MissingSchema):
        await message.reply("Invalid URL !")
    else:
        if "calType=vcal" in url:
            url = url[:url.find("vcal")] + "ical"
        elif "firstDate" in url:
            url = url[:url.find("&firstDate")]

        with dbL:
            with shelve.open("edt") as db:
                db[str(message.from_user.id)] = url

        await message.reply("EDT set !")


@dp.message_handler(commands=["getedt"])
async def edt_geturl(message: types.Message):
    with dbL:
        with shelve.open("edt") as db:
            if str(message.from_user.id) in db:
                await message.reply(db[str(message.from_user.id)])
            else:
                await message.reply("No EDT set !")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
