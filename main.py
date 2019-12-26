import asyncio

from aiogram.utils import executor

from TelegramEDT import notif, dp

loop = asyncio.get_event_loop()
loop.create_task(notif())
loop.create_task(executor.start_polling(dp, skip_updates=True))
loop.run_forever()
