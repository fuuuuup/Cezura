import logging, json, os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from flask import Flask
from threading import Thread

# --- Flask server to keep web service alive ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Бот работает"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# --- Telegram Bot Logic ---
API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)
DATA_FILE = 'cezura_data.json'

def load_data():
    try:
        with open(DATA_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_data(d): json.dump(d, open(DATA_FILE,'w'), indent=2)

def log_event(user_id, event):
    now = datetime.now().isoformat()
    d = load_data()
    d.setdefault(str(user_id), []).append({"event": event, "time": now})
    save_data(d)

@dp.message_handler(lambda msg: msg.text.lower().startswith("курила"))
async def kurila(message: types.Message):
    log_event(message.from_user.id, "курила")
    await message.reply("Записано — курила.")

@dp.message_handler(lambda msg: msg.text.lower().startswith("удержалась"))
async def ud(message: types.Message):
    log_event(message.from_user.id, "удержалась")
    await message.reply("Молодец — удержалась.")

@dp.message_handler(lambda msg: msg.text.lower().startswith("статистика"))
async def stats(message: types.Message):
    arr = load_data().get(str(message.from_user.id), [])
    cnt = sum(1 for e in arr if e["event"] in ("курила","удержалась"))
    await message.reply(f"Всего сегодня: {cnt} раз.")

if __name__ == "__main__":
    # Запускаем Flask в фоновом потоке
    Thread(target=run_flask).start()
    # Запускаем бота
    executor.start_polling(dp, skip_updates=True)
