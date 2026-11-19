from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from app.database import async_session_maker
from app.services import HabitService
from app.keyboards.inline import (
    get_main_menu_keyboard,
    get_habits_list_keyboard,
    get_habit_markup
)


router = Router()


class AddHabitStates(StatesGroup):
    name = State()
    description = State()


async def get_registered_user_id(telegram_id: int, username=None):
    async with async_session_maker() as session:
        service = HabitService(session)
        user = await service.register_user(telegram_id, username)
        return user.id


@router.callback_query(F.data == "add_habit")
async def add_habit_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddHabitStates.name)
    await callback.message.edit_text("✏️ Введи название новой привычки:")
    await callback.answer()


@router.message(AddHabitStates.name)
async def add_habit_name(message: types.Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не должно быть пустым. Попробуй ещё раз:")
        return
    if len(name) > 150:
        await message.answer("Название слишком длинное. Максимум 150 символов:")
        return
    await state.update_data(name=name)
    await state.set_state(AddHabitStates.description)
    await message.answer("Добавь описание или отправь '-' для пропуска:")


@router.message(AddHabitStates.description)
async def add_habit_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    description = (message.text or "").strip()
    if description == "-":
        description = None

    async with async_session_maker() as session:
        service = HabitService(session)
        user = await service.register_user(
            message.from_user.id,
            message.from_user.username
        )
        habit = await service.create_habit(user.id, data["name"], description)

    await state.clear()
    await message.answer(
        f"✅ Привычка «{habit.name}» создана!",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data == "my_habits")
async def show_my_habits(callback: types.CallbackQuery):
    async with async_session_maker() as session:
        service = HabitService(session)
        user = await service.register_user(callback.from_user.id, callback.from_user.username)
        habits = await service.get_user_habits(user.id)

        if not habits:
            text = "📭 Пока нет активных привычек. Добавь первую!"
            markup = get_main_menu_keyboard()
        else:
            lines = []
            for habit in habits:
                streak = await service.calculate_streak(habit.id)
                lines.append(f"• <b>{habit.name}</b> — серия: {streak} дн.")
            text = "📋 <b>Мои привычки:</b>\n\n" + "\n".join(lines)
            markup = get_habits_list_keyboard(habits)

    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("habit_"))
async def view_habit_detail(callback: types.CallbackQuery):
    try:
        habit_id = int(callback.data.split("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный номер привычки", show_alert=True)
        return

    async with async_session_maker() as session:
        service = HabitService(session)
        user = await service.get_user_by_telegram_id(callback.from_user.id)
        habit = await service.get_habit_by_id(habit_id, user.id) if user else None
        if habit:
            streak = await service.calculate_streak(habit.id)
            stats = await service.get_habit_stats(habit.id, user.id)

    if not habit:
        await callback.answer("Привычка не найдена", show_alert=True)
        return

    text = (
        f"📌 <b>{habit.name}</b>\n\n"
        f"📝 Описание: {habit.description or 'Нет описания'}\n"
        f"📅 Создана: {habit.created_at:%d.%m.%Y}\n"
        f"🔥 Серия: {streak} дней\n"
        f"📈 Выполнение за 30 дней: {stats['completion_rate']}%\n\n"
        "Выбери действие:"
    )
    await callback.message.edit_text(text, reply_markup=get_habit_markup(habit_id))
    await callback.answer()


@router.callback_query(F.data == "today")
async def show_today_habits(callback: types.CallbackQuery):
    async with async_session_maker() as session:
        service = HabitService(session)
        user = await service.register_user(callback.from_user.id, callback.from_user.username)
        habits = await service.get_user_habits(user.id)
        lines = []
        unmarked = []
        for habit in habits:
            record = await service.get_today_record(habit.id)
            if record is None:
                status = "❓ не отмечено"
                unmarked.append(habit)
            elif record.is_done:
                status = "✅ выполнено"
            else:
                status = "⏭ пропущено"
            lines.append(f"• <b>{habit.name}</b> — {status}")

        if habits:
            text = "📅 <b>Привычки на сегодня:</b>\n\n" + "\n".join(lines)
            markup = get_habits_list_keyboard(unmarked) if unmarked else get_main_menu_keyboard()
            if not unmarked:
                text += "\n\n🎉 Все привычки отмечены!"
        else:
            text = "📭 Пока нет привычек. Добавь первую!"
            markup = get_main_menu_keyboard()

    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("done_"))
async def mark_done(callback: types.CallbackQuery):
    habit_id = int(callback.data.split("_", 1)[1])
    async with async_session_maker() as session:
        service = HabitService(session)
        user = await service.get_user_by_telegram_id(callback.from_user.id)
        success = await service.mark_done(habit_id, user.id) if user else False

    await callback.answer("✅ Привычка выполнена!" if success else "Не удалось отметить привычку", show_alert=not success)
    await show_today_habits(callback)


@router.callback_query(F.data.startswith("skip_"))
async def mark_skipped(callback: types.CallbackQuery):
    habit_id = int(callback.data.split("_", 1)[1])
    async with async_session_maker() as session:
        service = HabitService(session)
        user = await service.get_user_by_telegram_id(callback.from_user.id)
        success = await service.mark_skipped(habit_id, user.id) if user else False

    await callback.answer("⏭ Привычка отмечена как пропущенная" if success else "Не удалось отметить привычку", show_alert=not success)
    await show_today_habits(callback)


@router.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    async with async_session_maker() as session:
        service = HabitService(session)
        user = await service.get_user_by_telegram_id(callback.from_user.id)
        habits = await service.get_user_habits(user.id) if user else []
        rows = []
        for habit in habits:
            stats = await service.get_habit_stats(habit.id, user.id)
            rows.append(
                f"• <b>{habit.name}</b>\n"
                f"  🔥 Серия: {stats['streak']} дн.\n"
                f"  📈 За 30 дней: {stats['completion_rate']}%\n"
                f"  ✅ Всего выполнено: {stats['total_done']}"
            )

    text = "📊 <b>Статистика</b>\n\n" + ("\n\n".join(rows) if rows else "Пока нет данных.")
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("delete_confirm_"))
async def delete_habit(callback: types.CallbackQuery):
    habit_id = int(callback.data.rsplit("_", 1)[1])
    async with async_session_maker() as session:
        service = HabitService(session)
        user = await service.get_user_by_telegram_id(callback.from_user.id)
        success = await service.delete_habit(habit_id, user.id) if user else False

    if success:
        await callback.answer("🗑 Привычка удалена")
        await show_my_habits(callback)
    else:
        await callback.answer("Не удалось удалить привычку", show_alert=True)


@router.message(Command("cancel"))
async def cancel_add(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_menu_keyboard())
