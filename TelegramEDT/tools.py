from aiogram import types
from aiogram.types import ParseMode
from aiogram.utils import markdown
from aiogram.utils.exceptions import MessageIsTooLong

from TelegramEDT import ADMIN_ID, bot, dbL, key, log_date, logger, session, check_id
from TelegramEDT.base import User


async def get_id(message: types.Message):
    check_id(message.from_user)
    await message.chat.do(types.ChatActions.TYPING)
    logger.info(f"{message.from_user.username} do getid command")
    await message.reply(message.from_user.id, reply_markup=key)


async def get_logs(message: types.Message):
    check_id(message.from_user)
    logger.info(f"{message.from_user.username} do getlog command")
    if message.from_user.id == ADMIN_ID:
        try:
            int(message.text[9:])
        except ValueError:
            await message.chat.do(types.ChatActions.UPLOAD_DOCUMENT)
            await message.reply_document(types.InputFile(f"logs/{log_date}.log"), caption=f"The {log_date} logs",
                                         reply_markup=key)
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
                await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)
            except MessageIsTooLong:
                await message.reply(markdown.bold("Too much logs ! ❌"), reply_markup=key)


async def get_db(message: types.Message):
    check_id(message.from_user)
    logger.info(f"{message.from_user.username} do getdb command")
    if message.from_user.id == ADMIN_ID:
        with dbL:
            users = dict()
            for u in session.query(User).all():
                users[u] = u.__dict__
            msg = markdown.text(
                markdown.italic("db:"),
                markdown.code(users),
                sep="\n"
            )
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def eval_cmd(message: types.Message):
    check_id(message.from_user)
    logger.info(f"{message.from_user.username} do eval command")
    if message.from_user.id == ADMIN_ID:
        msg = markdown.text(
            markdown.italic("eval:"),
            markdown.code(eval(message.text[6:])),
            sep="\n"
        )
        await message.reply(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=key)


async def errors(*args, **partial_data):
    if "This Session's transaction has been rolled back due to a previous exception during flush" in args:
        session.rollback()
    msg = markdown.text(
        markdown.bold("⚠️ An error occurred:"),
        markdown.code(args),
        markdown.code(partial_data),
        sep="\n"
    )
    await bot.send_message(ADMIN_ID, msg, parse_mode=ParseMode.MARKDOWN)
