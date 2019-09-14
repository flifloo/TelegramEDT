import logging, shelve, datetime, hashlib
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle
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
                return "Your EDT is not set !"
            now = datetime.datetime.now()
            if text == "week":
                firstdate = now.date() - datetime.timedelta(days=now.isoweekday()-1)
                lastdate = now.date() + datetime.timedelta(days=(7 - now.isoweekday()))
            elif text == "next":
                now += datetime.timedelta(days=7)
                firstdate = now.date() - datetime.timedelta(days=now.isoweekday())
                lastdate = now.date() + datetime.timedelta(days=(7 - now.isoweekday()))
            elif text == "":
                firstdate, lastdate = now, now
            else:
                return "Invalid choice !"

            url = f"{db[str(user_id)]}&firstDate={firstdate}&lastDate={lastdate}"
            c = Calendar(get(url).text)
            msg = str()

            for e in list(c.timeline):
                begin = e.begin.datetime
                end = e.end.datetime
                if str(begin.date())[5:] not in msg:
                    msg += f"<{str(begin.date())[5:]}>" + "\n"

                msg += f"[{e.name}]:" + "\n"
                msg += f"{str(begin.time())[:-3]} -> {str(end.time())[:-3]}" + "\n"
                prof = e.description.split('\n')[3]
                msg += f"{e.location} {prof}" + "\n\n"

            if msg == "":
                msg = "but nobody came..."
            return msg


@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    await message.reply("""Welcome to the TelegramEDT, a calendar bot for the Lyon 1 University !
/edt [week | next], for show your next course
/setedt <url>, to setup your calendar
/getedt, to get your calendar url
/help, to show this command""")


@dp.message_handler(commands=["edt"])
async def edt_cmd(message: types.Message):
    await message.reply(edt(message.text[5:], message.from_user.id))


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
    # don't forget to set cache_time=1 for testing (default is 300s or 5m)
    await bot.answer_inline_query(inline_query.id, results=[item], cache_time=1)


@dp.message_handler(commands=["setedt"])
async def edt_set(message: types.Message):
    url_http = message.text.find("http")
    url_end = message.text.find(" ", url_http)
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


@dp.message_handler(commands=["getedturl"])
async def edt_geturl(message: types.Message):
    with dbL:
        with shelve.open("edt") as db:
            if str(message.from_user.id) in db:
                await message.reply(db[str(message.from_user.id)])
            else:
                await message.reply("No EDT set !")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)