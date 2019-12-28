from asyncio import sleep

from TelegramEDT import modules_active
from TelegramEDT.edt_notif import notif as edt_notif
from TelegramEDT.kfet import notif as kfet_notif
from TelegramEDT.tomuss import notif as tomuss_notif


async def main():
    while True:
        if "edt_notif" in modules_active:
            await edt_notif()
        if "kfet" in modules_active:
            await kfet_notif()
        if "tomuss" in modules_active:
            await tomuss_notif()
        await sleep(30)
