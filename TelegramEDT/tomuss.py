from aiogram import types
from aiogram.types import ParseMode
from aiogram.utils import markdown
from feedparser import parse

from TelegramEDT import dp, key, logger, Session, check_id, modules, bot
from TelegramEDT.base import User
from TelegramEDT.lang import lang

module_name = "tomuss"
logger = logger.getChild(module_name)


def have_await_cmd(msg: types.Message):
    with Session as session:
        user = session.query(User).filter_by(id=msg.from_user.id).first()
        return user and user.await_cmd == "settomuss"


async def settomuss(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do settomuss")
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        user.await_cmd = "settomuss"
        session.commit()
        msg = lang(user, "settomuss_wait")

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def await_cmd(message: types.message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        logger.info(f"{message.from_user.username} do awaited command")
        if not len(parse(message.text).entries):
            msg = lang(user, "settomuss_error")
        else:
            user.tomuss_rss = message.text
            user.tomuss_last = str()
            msg = lang(user, "settomuss")
        user.await_cmd = str()
        session.commit()

    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def notif():
    with Session as session:
        for u in session.query(User).all():
            try:
                tm = u.get_tomuss()
            except Exception as e:
                logger.error(e)
            else:
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


def load():
    logger.info(f"Load {module_name} module")
    dp.register_message_handler(settomuss, lambda msg: msg.text.lower() == "settomuss")
    dp.register_message_handler(await_cmd, lambda msg: have_await_cmd(msg))
    modules.append(module_name)


def unload():
    logger.info(f"Unload {module_name} module")
    dp.message_handlers.unregister(settomuss)
    dp.message_handlers.unregister(await_cmd)
    modules.remove(module_name)
