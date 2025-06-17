import asyncio
import json
from datetime import datetime
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.utils.markdown import hbold

API_TOKEN = os.getenv("API_TOKEN")
DATA_FILE = "cezura_data.json"

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def log_event(user_id, event):
    now = datetime.now().isoformat(timespec="seconds")
    data = load_data()
    data.setdefault(str(user_id), []).append({"event": event, "time": now})
    save_data(data)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Бот Цезура готов. Пиши /курил или /удержался, чтобы отмечать события.")

@dp.message(Command("курил"))
async def cmd_kuril(message: Message):
    log_event(message.from_user.id, "курил")

@dp.message(Command("удержался"))
async def cmd_uderzhalsya(message: Message):
    log_event(message.from_user.id, "удержался")
    await message.answer("Отлично! Ты молодец.")

@dp.message(Command("статистика"))
async def cmd_stats(message: Message):
    data = load_data().get(str(message.from_user.id), [])
    today = datetime.now().date()
    summary = {"курил": 0, "удержался": 0}
    for entry in data:
        entry_time = datetime.fromisoformat(entry["time"])
        if entry_time.date() == today:
            summary[entry["event"]] += 1
    await message.answer(
        f"{hbold('Сегодня')}:
Курил: {summary['курил']}
Удержался: {summary['удержался']}"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())