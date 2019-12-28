import asyncio

from aiogram.utils import executor

from TelegramEDT import dp
from TelegramEDT.loop import main

loop = asyncio.get_event_loop()
loop.create_task(main())
loop.create_task(executor.start_polling(dp, skip_updates=True))
loop.run_forever()
