from asyncio import sleep

from TelegramEDT.edt_notif import notif


async def main():
    while True:
        await notif()
        await sleep(30)
