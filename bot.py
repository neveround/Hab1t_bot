import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from app.database import init_db, close_db
from app.handlers.start import router as start_router
from app.handlers.habits import router as habits_router
from app.scheduler.tasks import setup_scheduler


logging.basicConfig(level=logging.INFO)


async def main():
    await init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(habits_router)

    scheduler = setup_scheduler(bot)
    scheduler.start()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
