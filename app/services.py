from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Habit, Record


class HabitService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_user(self, telegram_id: int, username: Optional[str] = None) -> User:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            if username and user.username != username:
                user.username = username
                await self.session.commit()
            return user

        user = User(telegram_id=telegram_id, username=username)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create_habit(self, user_id: int, name: str, description: Optional[str] = None) -> Habit:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Название привычки не может быть пустым")
        habit = Habit(user_id=user_id, name=clean_name, description=description)
        self.session.add(habit)
        await self.session.commit()
        await self.session.refresh(habit)
        return habit

    async def get_user_habits(self, user_id: int, active_only: bool = True):
        query = select(Habit).where(Habit.user_id == user_id)
        if active_only:
            query = query.where(Habit.is_active.is_(True))
        result = await self.session.execute(query.order_by(Habit.created_at.desc()))
        return list(result.scalars().all())

    async def get_habit_by_id(self, habit_id: int, user_id: int) -> Optional[Habit]:
        result = await self.session.execute(
            select(Habit).where(
                and_(Habit.id == habit_id, Habit.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def update_habit_status(self, habit_id: int, user_id: int, is_active: bool) -> bool:
        habit = await self.get_habit_by_id(habit_id, user_id)
        if not habit:
            return False
        habit.is_active = is_active
        await self.session.commit()
        return True

    async def delete_habit(self, habit_id: int, user_id: int) -> bool:
        habit = await self.get_habit_by_id(habit_id, user_id)
        if not habit:
            return False
        await self.session.delete(habit)
        await self.session.commit()
        return True

    async def get_record_by_date(self, habit_id: int, record_date: date):
        result = await self.session.execute(
            select(Record).where(
                and_(Record.habit_id == habit_id, Record.date == record_date)
            )
        )
        return result.scalar_one_or_none()

    async def get_today_record(self, habit_id: int):
        return await self.get_record_by_date(habit_id, date.today())

    async def set_record(self, habit_id: int, user_id: int, is_done: bool, record_date=None) -> bool:
        record_date = record_date or date.today()
        habit = await self.get_habit_by_id(habit_id, user_id)
        if not habit:
            return False
        record = await self.get_record_by_date(habit_id, record_date)
        if record:
            record.is_done = is_done
        else:
            self.session.add(Record(
                habit_id=habit_id,
                date=record_date,
                is_done=is_done
            ))
        await self.session.commit()
        return True

    async def mark_done(self, habit_id: int, user_id: int, record_date=None) -> bool:
        return await self.set_record(habit_id, user_id, True, record_date)

    async def mark_skipped(self, habit_id: int, user_id: int, record_date=None) -> bool:
        return await self.set_record(habit_id, user_id, False, record_date)

    async def calculate_streak(self, habit_id: int) -> int:
        current = date.today()
        today_record = await self.get_record_by_date(habit_id, current)
        if not today_record or not today_record.is_done:
            current -= timedelta(days=1)

        streak = 0
        while True:
            record = await self.get_record_by_date(habit_id, current)
            if not record or not record.is_done:
                break
            streak += 1
            current -= timedelta(days=1)
        return streak

    async def get_completion_rate(self, habit_id: int, days: int = 30) -> float:
        if days <= 0:
            return 0.0
        today = date.today()
        start = today - timedelta(days=days - 1)
        result = await self.session.execute(
            select(func.count(Record.id)).where(
                and_(
                    Record.habit_id == habit_id,
                    Record.date >= start,
                    Record.date <= today,
                    Record.is_done.is_(True)
                )
            )
        )
        count = result.scalar_one()
        return round(count / days * 100, 1)

    async def get_habit_stats(self, habit_id: int, user_id: int):
        habit = await self.get_habit_by_id(habit_id, user_id)
        if not habit:
            return None
        result = await self.session.execute(
            select(func.count(Record.id)).where(
                and_(Record.habit_id == habit_id, Record.is_done.is_(True))
            )
        )
        return {
            "habit": habit,
            "streak": await self.calculate_streak(habit_id),
            "completion_rate": await self.get_completion_rate(habit_id),
            "total_done": result.scalar_one(),
            "created_at": habit.created_at
        }

    async def get_all_habits_with_today_status(self, user_id: int):
        habits = await self.get_user_habits(user_id)
        output = []
        today = date.today()
        for habit in habits:
            record = await self.get_record_by_date(habit.id, today)
            status = None if record is None else ("done" if record.is_done else "skipped")
            output.append({
                "habit": habit,
                "today_status": status,
                "streak": await self.calculate_streak(habit.id)
            })
        return output
