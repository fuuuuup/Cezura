import logging
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils import executor
import os

API_TOKEN = os.getenv("API_TOKEN")
DATA_FILE = 'cezura_data.json'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def log_event(user_id, event):
    now = datetime.now().isoformat(timespec="seconds")
    data = load_data()
    data.setdefault(str(user_id), []).append({"event": event, "time": now})
    save_data(data)

@dp.message_handler(commands=['start'])
async def send_welcome(message: Message):
    await message.reply("Бот Цезура готов. Пиши /курил или /удержался, чтобы отмечать события.")

@dp.message_handler(commands=['курил'])
async def log_smoke(message: Message):
    log_event(message.from_user.id, 'курил')

@dp.message_handler(commands=['удержался'])
async def log_resist(message: Message):
    log_event(message.from_user.id, 'удержался')
    await message.reply("Отлично! Ты молодец.")

@dp.message_handler(commands=['статистика'])
async def show_stats(message: Message):
    data = load_data().get(str(message.from_user.id), [])
    today = datetime.now().date()
    summary = {"курил": 0, "удержался": 0}
    for entry in data:
        entry_time = datetime.fromisoformat(entry["time"])
        if entry_time.date() == today:
            summary[entry["event"]] += 1
    await message.reply(f"Сегодня:\nКурил: {summary['курил']}\nУдержался: {summary['удержался']}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
