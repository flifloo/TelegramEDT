from os.path import isfile
from threading import RLock

from aiogram import Bot, Dispatcher, types
from aiogram.types import reply_keyboard
from aiogram.utils.callback_data import CallbackData
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from TelegramEDT.EDTcalendar import Calendar
from TelegramEDT.base import Base, User
from TelegramEDT.lang import lang
from TelegramEDT.logger import logger
from TelegramEDT.EDTscoped_session import scoped_session

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
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)
if not isfile("edt.db"):
    Base.metadata.create_all(engine)

key = reply_keyboard.ReplyKeyboardMarkup()
for k in ["Edt", "Kfet", "Setkfet", "Setedt", "Notif", "Settomuss"]:
    key.add(reply_keyboard.KeyboardButton(k))

modules_active = list()


def check_id(user: types.User):
    with Session as session:
        if (user.id,) not in session.query(User.id).all():
            logger.info(f"{user.username} add to the db")
            if user.locale and user.locale.language:
                lg = user.locale.language
            else:
                lg = ""
            session.add(User(id=user.id, language=lg))
            session.commit()


logger.info("Start loading modules")
from TelegramEDT.modules import load_module
for m in ["modules", "basic", "edt", "kfet", "tomuss", "edt_notif", "tools"]:
    load_module(m)
logger.info("Modules loading finish")
