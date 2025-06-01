
import os
import json
import sqlite3
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.markdown import bold
from aiogram.dispatcher.filters import CommandStart
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

TOKEN ="7565097268:AAEFdCBoYfIziGEqV7557A_TjR7j2LHTMCQ"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

dp.middleware.setup(LoggingMiddleware())

class Broadcast(StatesGroup):
    waiting_for_text = State()
    waiting_for_media = State()

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🚀 Старт — пройти мини-курс", web_app=types.WebAppInfo(url=config["course_link"])),
        InlineKeyboardButton("⚡ Пропустить — сразу к бонусу", callback_data="skip_course")
    )

    await message.answer(
    "🎯 Сегодня раздаю по 25.000₽ — безвозвратно!\n\n"
    "📈 Врывайся в марафон по лесенке 💸\n\n"
    "👇 Жми «СТАРТ» и забирай бонус",
    reply_markup=keyboard
)

@dp.callback_query_handler(lambda c: c.data == "skip_course")
async def skip_course(callback_query: types.CallbackQuery):
    bonus_keyboard = InlineKeyboardMarkup(row_width=1)
    bonus_keyboard.add(
        InlineKeyboardButton("🎰 Забрать бонус", url=config["ref_link"]),
        InlineKeyboardButton("🎡 Крутить бонусное колесо", web_app=types.WebAppInfo(url=config["wheel_link"]))
    )
    await bot.send_message(
    callback_query.from_user.id,
    "*🎁 Лови бонус +500% к депозиту!*\n\n"
    "*🔑 Промокод:* `BLANCE`\n"
    "Активируй при регистрации и получи максимум!",
    parse_mode=ParseMode.MARKDOWN,
    reply_markup=bonus_keyboard
)


    channel_keyboard = InlineKeyboardMarkup(row_width=1)
    channel_keyboard.add(
        InlineKeyboardButton("📡 Забрать кэф 12", url=config["channel_link"])
    )
    await bot.send_message(
    callback_query.from_user.id,
    "*📢 Сегодня в канале дико жаркий экспресс!*\n\n"
    "*🔥 Кэф 12 — ограничен по времени*\n"
    "Если не подпишешься сейчас — можешь навсегда упустить шанс заработать!\n\n"
    "Жми кнопку ниже и лови ставку дня 👇",
    parse_mode=ParseMode.MARKDOWN,
    reply_markup=channel_keyboard
)



@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
    if message.from_user.id == config["admin_id"]:
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("📊 Статистика", callback_data="show_stats"),
            InlineKeyboardButton("📢 Рассылка", callback_data="send_broadcast")
        )
        await message.answer("Добро пожаловать в панель администратора!", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "show_stats")
async def show_stats(callback_query: types.CallbackQuery):
    if callback_query.from_user.id == config["admin_id"]:
        con = sqlite3.connect("database/user.db")
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE ref_link IS NOT NULL")
        registered_users = cur.fetchone()[0]
        con.close()
        await bot.send_message(callback_query.from_user.id,
            f"👥 Всего пользователей: {total_users}\n✅ Зарегистрировано по реферальной ссылке: {registered_users}")

@dp.callback_query_handler(lambda c: c.data == "send_broadcast")
async def send_broadcast(callback_query: types.CallbackQuery):
    if callback_query.from_user.id == config["admin_id"]:
        await bot.send_message(callback_query.from_user.id, "Отправьте текст для рассылки:")
        await Broadcast.waiting_for_text.set()

@dp.message_handler(state=Broadcast.waiting_for_text, content_types=types.ContentTypes.TEXT)
async def broadcast_text(msg: types.Message, state: FSMContext):
    await state.update_data(text=msg.text)
    await msg.answer("📎 Прикрепите медиа (фото/видео/документ), или отправьте /skip, чтобы пропустить")
    await Broadcast.waiting_for_media.set()

@dp.message_handler(lambda msg: msg.text == "/skip", state=Broadcast.waiting_for_media)
async def skip_media(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    con = sqlite3.connect("database/user.db")
    cur = con.cursor()
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()
    for user in users:
        try:
            await bot.send_message(user[0], data["text"])
        except:
            continue
    await msg.answer("✅ Рассылка завершена.")
    await state.finish()

@dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.VIDEO, types.ContentType.DOCUMENT], state=Broadcast.waiting_for_media)
async def handle_media(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    con = sqlite3.connect("database/user.db")
    cur = con.cursor()
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()
    for user in users:
        try:
            if msg.content_type == types.ContentType.PHOTO:
                await bot.send_photo(user[0], msg.photo[-1].file_id, caption=data["text"])
            elif msg.content_type == types.ContentType.VIDEO:
                await bot.send_video(user[0], msg.video.file_id, caption=data["text"])
            elif msg.content_type == types.ContentType.DOCUMENT:
                await bot.send_document(user[0], msg.document.file_id, caption=data["text"])
        except:
            continue
    await msg.answer("✅ Рассылка с медиа завершена.")
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
