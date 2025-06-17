import logging
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import os

API_TOKEN = os.getenv("API_TOKEN")
DATA_FILE = 'cezura_data.json'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_event(user_id, event, comment=None):
    now = datetime.now().isoformat(timespec="seconds")
    data = load_data()
    entry = {"event": event, "time": now}
    if comment:
        entry["comment"] = comment
    data.setdefault(str(user_id), []).append(entry)
    save_data(data)

# Команда или текст "курила" + комментарий
@dp.message_handler(lambda msg: msg.text and msg.text.lower().startswith("курила"))
async def handle_smoke(message: types.Message):
    parts = message.text.split(maxsplit=1)
    comment = parts[1] if len(parts) > 1 else None
    log_event(message.from_user.id, 'курила', comment)
    await message.reply("Записано: курила" + (f" — {comment}" if comment else ""))

@dp.message_handler(lambda msg: msg.text and msg.text.lower().startswith("удержалась"))
async def handle_resist(message: types.Message):
    parts = message.text.split(maxsplit=1)
    comment = parts[1] if len(parts) > 1 else None
    log_event(message.from_user.id, 'удержалась', comment)
    await message.reply("Записано: удержалась" + (f" — {comment}" if comment else ""))

@dp.message_handler(lambda msg: msg.text and msg.text.lower() in ["статистика", "stats"])
async def show_stats(message: types.Message):
    data = load_data().get(str(message.from_user.id), [])
    now = datetime.now()
    periods = {
        "сегодня": now - timedelta(days=1),
        "неделю": now - timedelta(weeks=1),
        "месяц": now - timedelta(days=30),
        "полгода": now - timedelta(days=182),
    }
    summary = {p: {"курила": 0, "удержалась": 0} for p in periods}
    for entry in data:
        t = datetime.fromisoformat(entry["time"])
        for period, since in periods.items():
            if t >= since:
                summary[period][entry["event"]] += 1
    text = "Статистика:\n"
    for period, counts in summary.items():
        text += f"За {period}: курила {counts['курила']}, удержалась {counts['удержалась']}\n"
    await message.reply(text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
