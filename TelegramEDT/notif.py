from asyncio import sleep

from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from aiogram.utils import markdown

from TelegramEDT import bot, dp, logger, posts_cb, Session, check_id, key
from TelegramEDT.base import User
from TelegramEDT.lang import lang

logger = logger.getChild("notif")


def have_await_cmd(msg: types.Message):
    with Session as session:
        user = session.query(User).filter_by(id=msg.from_user.id).first()
        return user and user.await_cmd in ["time", "cooldown"]


async def notif():
    while True:
        with Session as session:
            for u in session.query(User).all():
                nt = None
                kf = None
                tm = None
                try:
                    nt = u.get_notif()
                    kf = u.get_kfet()
                    tm = u.get_tomuss()
                except Exception as e:
                    logger.error(e)

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


async def notif_cmd(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do notif")
    keys = InlineKeyboardMarkup()
    for i, n in enumerate(["Toggle", "Time", "Cooldown"]):
        keys.add(InlineKeyboardButton(n, callback_data=posts_cb.new(id=i, action=n.lower())))
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        msg = lang(user, "notif_info").format(user.nt, user.nt_time, user.nt_cooldown)
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keys)


async def notif_query(query: types.CallbackQuery, callback_data: dict):
    check_id(query.message.from_user)
    await query.message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{query.message.from_user.username} do notif query")
    with Session as session:
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


async def await_cmd(message: types.message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    with Session as session:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        logger.info(f"{message.from_user.username} do awaited command")
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
        user.await_cmd = str()
        session.commit()
    await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


def load():
    logger.info("Load notif module")
    dp.register_message_handler(notif_cmd, lambda msg: msg.text.lower() == "notif")
    dp.register_callback_query_handler(notif_query, posts_cb.filter(action=["toggle", "time", "cooldown"]))
    dp.register_message_handler(await_cmd, lambda msg: have_await_cmd(msg))


def unload():
    logger.info("Unload notif module")
    dp.message_handlers.unregister(notif_cmd)
    dp.callback_query_handlers.unregister(notif_query)
    dp.message_handlers.unregister(await_cmd)
