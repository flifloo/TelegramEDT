from asyncio import sleep

from TelegramEDT import modules
from TelegramEDT.edt_notif import notif as edt_notif
from TelegramEDT.kfet import notif as kfet_notif
from TelegramEDT.tomuss import notif as tomuss_notif


async def main():
    while True:
        if "edt_notif" in modules:
            await edt_notif()
        if "kfet" in modules:
            await kfet_notif()
        if "tomuss" in modules:
            await tomuss_notif()
        await sleep(30)
