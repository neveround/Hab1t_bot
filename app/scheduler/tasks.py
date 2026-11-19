import logging
from datetime import date

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from config import config
from app.database import async_session_maker
from app.models import User
from app.services import HabitService


logger = logging.getLogger(__name__)


async def send_daily_reminders(bot: Bot):
    async with async_session_maker() as session:
        users = (await session.execute(select(User))).scalars().all()
        targets = []
        for user in users:
            service = HabitService(session)
            habits = await service.get_user_habits(user.id)
            if habits:
                names = "\n".join(f"• {habit.name}" for habit in habits)
                targets.append((user.telegram_id, names))

    for telegram_id, names in targets:
        try:
            await bot.send_message(
                telegram_id,
                "🌅 Доброе утро! Не забудь о своих привычках:\n\n" + names
            )
        except Exception:
            logger.exception("Не удалось отправить напоминание пользователю %s", telegram_id)


async def check_missed_habits(bot: Bot):
    today = date.today()
    async with async_session_maker() as session:
        users = (await session.execute(select(User))).scalars().all()
        targets = []
        for user in users:
            service = HabitService(session)
            habits = await service.get_user_habits(user.id)
            missing = []
            for habit in habits:
                record = await service.get_record_by_date(habit.id, today)
                if record is None:
                    missing.append(habit.name)
            if missing:
                targets.append((user.telegram_id, missing))

    for telegram_id, missing in targets:
        try:
            text = "\n".join(f"• {name}" for name in missing)
            await bot.send_message(
                telegram_id,
                "🌙 Сегодня ещё не отмечены эти привычки:\n\n" + text
            )
        except Exception:
            logger.exception("Не удалось отправить итог дня пользователю %s", telegram_id)


async def send_weekly_stats(bot: Bot):
    async with async_session_maker() as session:
        users = (await session.execute(select(User))).scalars().all()
        targets = []
        for user in users:
            service = HabitService(session)
            habits = await service.get_user_habits(user.id)
            if not habits:
                continue
            lines = []
            for habit in habits:
                stats = await service.get_habit_stats(habit.id, user.id)
                lines.append(
                    f"• {habit.name}: серия {stats['streak']} дн., "
                    f"выполнение за 30 дней {stats['completion_rate']}%"
                )
            targets.append((user.telegram_id, "\n".join(lines)))

    for telegram_id, report in targets:
        try:
            await bot.send_message(
                telegram_id,
                "📊 Твоя еженедельная статистика:\n\n" + report
            )
        except Exception:
            logger.exception("Не удалось отправить статистику пользователю %s", telegram_id)


def setup_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)
    scheduler.add_job(
        send_daily_reminders,
        CronTrigger(hour=9, minute=0, timezone=config.TIMEZONE),
        args=[bot],
        id="daily_reminders",
        replace_existing=True
    )
    scheduler.add_job(
        check_missed_habits,
        CronTrigger(hour=23, minute=0, timezone=config.TIMEZONE),
        args=[bot],
        id="check_missed",
        replace_existing=True
    )
    scheduler.add_job(
        send_weekly_stats,
        CronTrigger(day_of_week="sun", hour=20, minute=0, timezone=config.TIMEZONE),
        args=[bot],
        id="weekly_stats",
        replace_existing=True
    )
    return scheduler
