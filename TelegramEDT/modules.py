from importlib import import_module

from aiogram.types import Message

from TelegramEDT import ADMIN_ID, dp, logger

logger = logger.getChild("modules")


def load_module(module: str) -> bool:
    try:
        module = import_module(f"TelegramEDT.{module}")
    except ModuleNotFoundError:
        logger.error(f"Fail to load module {module}, module not found !")
        return False
    else:
        try:
            module.load()
        except AttributeError:
            logger.error(f"Fail to load module {module}, no load function !")
            return False
    return True


def unload_module(module: str) -> bool:
    try:
        module = import_module(f"TelegramEDT.{module}")
    except ModuleNotFoundError:
        logger.error(f"Fail to unload module {module}, module not found !")
        return False
    else:
        try:
            module.unload()
        except AttributeError:
            logger.error(f"Fail to unload module {module}, no unload function !")
            return False
    return True


async def load_cmd(message: Message):
    logger.info(f"{message.from_user.username} do load command")
    if message.from_user.id == ADMIN_ID:
        module = message.text[6:]
        if load_module(module):
            msg = f"Module {module} loaded !"
        else:
            msg = f"Fail to load module {module} !"

        await message.reply(msg)


async def unload_cmd(message: Message):
    logger.info(f"{message.from_user.username} do unload command")
    if message.from_user.id == ADMIN_ID:
        module = message.text[8:]
        if unload_module(module):
            msg = f"Module {module} unloaded !"
        else:
            msg = f"Fail to unload module {module} !"

        await message.reply(msg)


def load():
    logger.info("Load modules module")
    dp.register_message_handler(load_cmd, commands="load")
    dp.register_message_handler(unload_cmd, commands="unload")


def unload():
    logger.info("Unload tools module")
    dp.message_handlers.unregister(load_cmd)
    dp.message_handlers.unregister(unload_cmd)
