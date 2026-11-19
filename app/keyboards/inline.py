from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить привычку", callback_data="add_habit")
    builder.button(text="📋 Мои привычки", callback_data="my_habits")
    builder.button(text="📅 Сегодня", callback_data="today")
    builder.button(text="📊 Статистика", callback_data="stats")
    builder.adjust(1)
    return builder.as_markup()


def get_habits_list_keyboard(habits):
    builder = InlineKeyboardBuilder()
    for habit in habits:
        builder.button(text=f"📌 {habit.name[:45]}", callback_data=f"habit_{habit.id}")
    builder.button(text="⬅️ В меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_habit_markup(habit_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Выполнено", callback_data=f"done_{habit_id}")
    builder.button(text="⏭ Пропустить", callback_data=f"skip_{habit_id}")
    builder.button(text="🗑 Удалить", callback_data=f"delete_confirm_{habit_id}")
    builder.button(text="⬅️ К привычкам", callback_data="my_habits")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def get_delete_habit_keyboard(habit_id: int):
    return get_habit_markup(habit_id)


def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_menu")]
    ])
