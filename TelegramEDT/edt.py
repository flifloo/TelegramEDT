import hashlib

from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, InputTextMessageContent, \
    InlineQueryResultArticle, InlineQuery

from TelegramEDT import dbL, dp, key, logger, posts_cb, session, TIMES, bot, check_id
from TelegramEDT.base import User
from TelegramEDT.lang import lang

logger = logger.getChild("edt")


def calendar(time: str, user_id: int):
    with dbL:
        user = session.query(User).filter_by(id=user_id).first()
        if not user.resources:
            return lang(user, "edt_err_set")
        elif time not in TIMES:
            return lang(user, "edt_err_choice")
        return str(user.calendar(time))


def edt_key():
    keys = InlineKeyboardMarkup()
    for i, n in enumerate(["Day", "Next", "Week", "Next week"]):
        keys.add(InlineKeyboardButton(n, callback_data=posts_cb.new(id=i, action=n.lower())))
    return keys


async def edt_cmd(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do edt")
    await message.reply(calendar("day", message.from_user.id), parse_mode=ParseMode.MARKDOWN, reply_markup=edt_key())


async def inline_edt(inline_query: InlineQuery):
    check_id(inline_query.from_user)
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


async def edt_query(query: types.CallbackQuery, callback_data: dict):
    check_id(query.message.from_user)
    await query.message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{query.message.from_user.username} do edt query")
    await query.message.reply(calendar(callback_data["action"], query.from_user.id), parse_mode=ParseMode.MARKDOWN,
                              reply_markup=edt_key())


async def edt_await(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do setedt")
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        user.await_cmd = "setedt"
        session.commit()

    await message.reply(lang(user, "setedt_wait"), parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def edt_geturl(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do getedt command")
    with dbL:
        user = session.query(User).filter_by(id=message.from_user.id).first()
        if user.resources:
            await message.reply(user.resources, reply_markup=key)
        else:
            await message.reply(lang(user, "getedt_err"), reply_markup=key)


def load():
    logger.info("Load edt module")
    dp.register_message_handler(edt_cmd, lambda msg: msg.text.lower() == "edt")
    dp.register_inline_handler(inline_edt)
    dp.register_callback_query_handler(edt_query, posts_cb.filter(action=["day", "next", "week", "next week"]))
    dp.register_message_handler(edt_await, lambda msg: msg.text.lower() == "setedt")
    dp.register_message_handler(edt_geturl, commands="getedt")


def unload():
    logger.info("Unload edt module")
    dp.message_handlers.unregister(edt_cmd)
    dp.inline_query_handlers.unregister(inline_edt)
    dp.callback_query_handlers.unregister(edt_query)
    dp.message_handlers.unregister(edt_await)
    dp.message_handlers.unregister(edt_geturl)
