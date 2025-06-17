import logging
import json
from datetime import datetime, timedelta
import os
import threading
from flask import Flask, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = os.getenv("API_TOKEN")
DATA_FILE = 'cezura_data.json'

# Flask-контейнер для HTTP-запросов
app = Flask(__name__)
@app.route("/healthz")
def healthz():
    return "OK", 200

@app.route("/stats/<int:user_id>")
def http_user_stats(user_id):
    data = load_data().get(str(user_id), [])
    return jsonify(data)

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def log_event(user_id, event, comment=None):
    now = datetime.now().isoformat(timespec="seconds")
    rec = {"event": event, "time": now}
    if comment:
        rec["comment"] = comment
    data = load_data()
    data.setdefault(str(user_id), []).append(rec)
    save_data(data)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# Обработка сообщений без слеша команд
@dp.message_handler(lambda m: m.text.lower().startswith("курила"))
async def handle_smoke(message: types.Message):
    parts = message.text.split(maxsplit=1)
    comment = parts[1].strip() if len(parts)>1 else None
    log_event(message.from_user.id, 'курила', comment)
    await message.reply("Отмечено: курила" + (f", комментарий: {comment}" if comment else ""))

@dp.message_handler(lambda m: m.text.lower().startswith("удержалась") or m.text.lower().startswith("сдержалась") or m.text.lower().startswith("не курила"))
async def handle_resist(message: types.Message):
    parts = message.text.split(maxsplit=1)
    comment = parts[1].strip() if len(parts)>1 else None
    # нормализуем событие
    event = 'удержалась' if message.text.lower().startswith("удержалась") else (
        'сдержалась' if message.text.lower().startswith("сдержалась") else 'не курила')
    log_event(message.from_user.id, event, comment)
    await message.reply(f"Отмечено: {event}" + (f", комментарий: {comment}" if comment else ""))

@dp.message_handler(lambda m: m.text.lower().startswith("статистика"))
async def show_stats(message: types.Message):
    data = load_data().get(str(message.from_user.id), [])
    now = datetime.now()
    periods = {
        "день": now - timedelta(days=1),
        "неделя": now - timedelta(days=7),
        "месяц": now - timedelta(days=30),
        "полгода": now - timedelta(days=182),
    }
    summary = {}
    for name, cutoff in periods.items():
        cnt = sum(1 for e in data if datetime.fromisoformat(e["time"]) > cutoff)
        summary[name] = cnt
    text = "\n".join(f"За {k}: {v}" for k,v in summary.items())
    await message.reply(text)

@dp.message_handler(lambda m: m.text.lower().startswith("удалить статистику"))
async def delete_stats(message: types.Message):
    data = load_data()
    if str(message.from_user.id) in data:
        del data[str(message.from_user.id)]
        save_data(data)
        await message.reply("Вся статистика удалена.")
    else:
        await message.reply("Статистика пуста.")

def run_bot():
    executor.start_polling(dp, skip_updates=True)

if __name__ == '__main__':
    # Запускаем Flask и polling в отдельных потоках
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8000))), daemon=True).start()
    run_bot()
