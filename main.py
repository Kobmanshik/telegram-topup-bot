print("✅ CLEAN START — main.py точно используется")

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware

API_TOKEN = "7829191204:AAF3utRWorh8gVGp-JbLngiZlaog4F6gf7k"  # ← замени на свой
ADMIN_ID = 582761505           # ← замени на свой

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Главное меню
menu_kb = ReplyKeyboardMarkup(resize_keyboard=True)
menu_kb.add(KeyboardButton("💰 Заказать пополнение"))

# Клавиатура отмены
cancel_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
cancel_kb.add(KeyboardButton("❌ Отмена"))

class Form(StatesGroup):
    waiting_for_bank = State()
    waiting_for_amount = State()
    waiting_for_type = State()

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=menu_kb)

@dp.message_handler(lambda msg: msg.text == "💰 Заказать пополнение")
async def order_topup(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🏦 AdsCard", callback_data="bank:adscard"),
        InlineKeyboardButton("💳 Traffic.cards", callback_data="bank:trafficcards")
    )
    await message.answer("Выберите банк:", reply_markup=kb)
    await message.answer("❌ В любой момент нажмите 'Отмена', чтобы выйти", reply_markup=cancel_kb)
    await Form.waiting_for_bank.set()

@dp.callback_query_handler(lambda c: c.data.startswith("bank:"), state=Form.waiting_for_bank)
async def bank_selected(query: types.CallbackQuery, state: FSMContext):
    _, bank = query.data.split(":")
    await state.update_data(bank=bank)
    await query.message.answer("Введите сумму пополнения:", reply_markup=cancel_kb)
    await Form.waiting_for_amount.set()
    await query.answer()

@dp.message_handler(state=Form.waiting_for_amount)
async def get_amount(message: types.Message, state: FSMContext):
    amount = message.text.strip()
    await state.update_data(amount=amount)

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("⚡ Срочное", callback_data="type:urgent"),
        InlineKeyboardButton("🕘 Не срочное (до 21:00)", callback_data="type:normal")
    )

    await message.answer("Выберите тип пополнения:", reply_markup=kb)
    await message.answer("❌ В любой момент нажмите 'Отмена', чтобы выйти", reply_markup=cancel_kb)
    await Form.waiting_for_type.set()

@dp.callback_query_handler(lambda c: c.data.startswith("type:"), state=Form.waiting_for_type)
async def type_selected(query: types.CallbackQuery, state: FSMContext):
    _, topup_type = query.data.split(":")
    await state.update_data(topup_type=topup_type)
    await query.answer()

    user_id = query.from_user.id
    username = query.from_user.username or "нет username"

    data = await state.get_data()
    bank = data.get("bank", "не указан")
    amount = data.get("amount", "не указано")
    topup_type_text = "⚡ Срочное" if topup_type == "urgent" else "🕘 Не срочное (до 21:00)"

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Выполнено", callback_data=f"approve:{user_id}"),
        InlineKeyboardButton("❌ Отклонено", callback_data=f"decline:{user_id}")
    )

    await bot.send_message(
        ADMIN_ID,
        f"🔔 Новая заявка от @{username} (ID: {user_id})\n"
        f"🏦 Банк: {bank}\n"
        f"💳 Сумма: {amount}\n"
        f"📌 Тип: {topup_type_text}",
        reply_markup=kb
    )

    await query.message.answer("Ваша заявка отправлена администратору.", reply_markup=menu_kb)
    await state.finish()

@dp.callback_query_handler(lambda c: c.data and c.data.startswith(("approve", "decline")))
async def process_callback(query: types.CallbackQuery):
    action, user_id = query.data.split(":")
    user_id = int(user_id)

    if action == "approve":
        await bot.send_message(user_id, "✅ Ваша заявка была выполнена.")
        await query.message.edit_reply_markup(reply_markup=None)
        await query.answer("Отмечено как выполнено.")
    elif action == "decline":
        await bot.send_message(user_id, "❌ Ваша заявка была отклонена.")
        await query.message.edit_reply_markup(reply_markup=None)
        await query.answer("Отмечено как отклонено.")

# Обработка отмены
@dp.message_handler(lambda msg: msg.text == "❌ Отмена", state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Действие отменено. Возвращаю в главное меню ⤴️", reply_markup=menu_kb)

if __name__ == '__main__':
    executor.start_polling(dp)
