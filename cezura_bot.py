import logging
import json
from datetime import datetime
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
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_event(user_id, event, comment):
    now = datetime.now().isoformat(timespec="seconds")
    data = load_data()
    data.setdefault(str(user_id), []).append({
        "event": event,
        "comment": comment,
        "time": now
    })
    save_data(data)

@dp.message_handler(lambda m: m.text and m.text.lower().startswith("курил"))
async def handle_kuril(message: types.Message):
    parts = message.text.split(maxsplit=1)
    comment = parts[1].strip() if len(parts) > 1 else ""
    log_event(message.from_user.id, "курил", comment)
    await message.reply(f"Отмечено 'курил'.{ ' Комментарий: ' + comment if comment else '' }")

@dp.message_handler(lambda m: m.text and m.text.lower().startswith("удержался"))
async def handle_resist(message: types.Message):
    parts = message.text.split(maxsplit=1)
    comment = parts[1].strip() if len(parts) > 1 else ""
    log_event(message.from_user.id, "удержался", comment)
    await message.reply(f"Отмечено 'удержался'.{ ' Комментарий: ' + comment if comment else '' }")

@dp.message_handler(lambda m: m.text and m.text.lower().startswith("статистика"))
async def show_stats(message: types.Message):
    data = load_data().get(str(message.from_user.id), [])
    today = datetime.now().date()
    summary = {"курил": 0, "удержался": 0}
    comments = []
    for entry in data:
        dt = datetime.fromisoformat(entry["time"])
        if dt.date() == today:
            summary[entry["event"]] = summary.get(entry["event"], 0) + 1
            if entry["comment"]:
                comments.append(f"{entry['event']}: {entry['comment']}")
    resp = f"Сегодня:\nКурил: {summary['курил']}\nУдержался: {summary['удержался']}"
    if comments:
        resp += "\nКомментарии:\n" + "\n".join(comments)
    await message.reply(resp)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
