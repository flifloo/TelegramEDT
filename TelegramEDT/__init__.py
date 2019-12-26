import datetime
import logging
from os import mkdir
from os.path import isdir, isfile
from threading import RLock

from aiogram import Bot, Dispatcher, types
from aiogram.types import reply_keyboard
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


from TelegramEDT.modules import load_module, load_cmd, unload_cmd
dp.register_message_handler(load_cmd, commands="load")
dp.register_message_handler(unload_cmd, commands="unload")

logger.info("Start loading modules")
for m in ["basic", "edt", "kfet", "tomuss", "notif", "await_cmd", "tools"]:
    load_module(m)
logger.info("Modules loading finish")
