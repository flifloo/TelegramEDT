import datetime
import logging
from os import mkdir
from os.path import isdir, isfile
from threading import RLock

from aiogram import Bot, Dispatcher, types
from aiogram.types import reply_keyboard, ContentType
from aiogram.utils.callback_data import CallbackData
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from TelegramEDT.EDTcalendar import Calendar
from TelegramEDT.base import Base, User
from TelegramEDT.lang import lang

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

key = reply_keyboard.ReplyKeyboardMarkup()
for k in ["Edt", "Kfet", "Setkfet", "Setedt", "Notif", "Settomuss"]:
    key.add(reply_keyboard.KeyboardButton(k))


def check_id(user: types.User):
    with dbL:
        if (user.id,) not in session.query(User.id).all():
            logger.info(f"{user.username} add to the db")
            if user.locale and user.locale.language:
                lg = user.locale.language
            else:
                lg = ""
            session.add(User(id=user.id, language=lg))
            session.commit()


from TelegramEDT.basic import start, help_cmd
dp.register_message_handler(start, commands="start")
dp.register_message_handler(help_cmd, commands="help")

from TelegramEDT.edt import edt_cmd, edt_query, inline_edt, edt_await, edt_geturl
dp.register_message_handler(edt_cmd, lambda msg: msg.text.lower() == "edt")
dp.register_inline_handler(inline_edt)
dp.register_callback_query_handler(edt_query, posts_cb.filter(action=["day", "next", "week", "next week"]))
dp.register_message_handler(edt_await, lambda msg: msg.text.lower() == "setedt")
dp.register_message_handler(edt_geturl, commands="getedt")

from TelegramEDT.kfet import kfet, kfet_set
dp.register_message_handler(kfet, lambda msg: msg.text.lower() == "kfet")
dp.register_message_handler(kfet_set, lambda msg: msg.text.lower() == "setkfet")

from TelegramEDT.tomuss import settomuss
dp.register_message_handler(settomuss, lambda msg: msg.text.lower() == "settomuss")

from TelegramEDT.notif import notif, notif_cmd, notif_query
dp.register_message_handler(notif_cmd, lambda msg: msg.text.lower() == "notif")
dp.register_callback_query_handler(notif_query, posts_cb.filter(action=["toggle", "time", "cooldown"]))

from TelegramEDT.await_cmd import await_cmd, have_await_cmd
dp.register_message_handler(await_cmd, lambda msg: have_await_cmd(msg), content_types=[ContentType.TEXT, ContentType.PHOTO])

from TelegramEDT.tools import get_id, get_logs, get_db, eval_cmd, errors
dp.register_message_handler(get_id, commands="getid")
dp.register_message_handler(get_logs, commands="getlogs")
dp.register_message_handler(get_db, commands="getdb")
dp.register_message_handler(eval_cmd, commands="eval")
dp.register_errors_handler(errors)
