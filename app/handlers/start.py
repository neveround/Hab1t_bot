from aiogram import Router, types
from aiogram.filters import Command

from app.database import async_session_maker
from app.services import HabitService
from app.keyboards.inline import get_main_menu_keyboard


router = Router()


@router.message(Command("start"))
async def start_command(message: types.Message):
    async with async_session_maker() as session:
        service = HabitService(session)
        await service.register_user(
            message.from_user.id,
            message.from_user.username
        )

    await message.answer(
        "👋 Привет! Я бот для трекинга привычек.\n\n"
        "➕ Добавляй привычки\n"
        "✅ Отмечай выполнение\n"
        "🔥 Следи за сериями\n"
        "📊 Смотри статистику\n"
        "🔔 Получай напоминания\n\n"
        "Выбери действие:",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(lambda callback: callback.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Главное меню. Выбери действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()
