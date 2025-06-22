import asyncio
from aiogram import Bot, Dispatcher
from db_connection import Database
from referral import router
import config

async def on_startup(bot: Bot):
    print("started")

async def on_shutdown(bot: Bot):
    print("closed")

async def main():
    db = Database()
    await db.connect()

    bot = Bot(token=config.TG_API_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())