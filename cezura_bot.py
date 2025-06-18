import logging, json, os, asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from flask import Flask
from threading import Thread

# --- Flask для Render Web Service ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Бот работает"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# --- Telegram Bot ---
API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)
DATA_FILE = 'cezura_data.json'

# --- Работа с файлом ---
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_data(d):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

def log_event(user_id, event_text):
    now = datetime.utcnow() + timedelta(hours=3)  # МСК
    d = load_data()
    d.setdefault(str(user_id), []).append({
        "event": event_text.strip(),
        "time": now.isoformat()
    })
    save_data(d)

# --- Обработка сообщений ---
@dp.message_handler(lambda msg: msg.text.lower().startswith("курила"))
async def kurila(message: types.Message):
    log_event(message.from_user.id, message.text)
    await message.reply("Записано — курила.")

@dp.message_handler(lambda msg: msg.text.lower().startswith("удержалась"))
async def ud(message: types.Message):
    log_event(message.from_user.id, message.text)
    await message.reply("Молодец — удержалась.")

@dp.message_handler(lambda msg: msg.text.lower().startswith("статистика"))
async def stats(message: types.Message):
    data = load_data().get(str(message.from_user.id), [])
    if not data:
        await message.reply("Пока ничего не записано.")
        return

    now = datetime.utcnow() + timedelta(hours=3)
    periods = {
        "сегодня": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "7 дней": now - timedelta(days=7),
        "30 дней": now - timedelta(days=30),
        "180 дней": now - timedelta(days=180),
    }

    report = []

    for label, start_time in periods.items():
        filtered = [
            e for e in data
            if datetime.fromisoformat(e["time"]) >= start_time
        ]
        kurila = [e for e in filtered if e["event"].lower().startswith("курила")]
        ud = [e for e in filtered if e["event"].lower().startswith("удержалась")]

        report.append(f"📅 *{label.capitalize()}*:")
        report.append(f" Курила: {len(kurila)}")
        report.append(f" Удержалась: {len(ud)}")

        if filtered:
            report.append(" Комментарии:")
            for e in filtered:
                t = datetime.fromisoformat(e["time"]).strftime('%d.%m %H:%M')
                report.append(f"  {t} — {e['event']}")

        report.append("")

    await message.reply("\n".join(report), parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text.lower().startswith("сброс"))
async def reset(message: types.Message):
    d = load_data()
    if str(message.from_user.id) in d:
        del d[str(message.from_user.id)]
        save_data(d)
        await message.reply("Все записи удалены.")
    else:
        await message.reply("Нечего удалять — записей не было.")

# --- Напоминалка в 21:00 МСК ---
async def daily_check():
    while True:
        now = datetime.utcnow() + timedelta(hours=3)  # МСК
        if now.hour == 21 and now.minute == 0:
            data = load_data()
            for user_id_str, events in data.items():
                user_events = [
                    (datetime.fromisoformat(e["time"]), e["event"])
                    for e in events
                ]
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                yesterday = today - timedelta(days=1)

                count_today = sum(1 for dt, ev in user_events if dt >= today and ev.lower().startswith("курила"))
                count_yesterday = sum(1 for dt, ev in user_events if yesterday <= dt < today and ev.lower().startswith("курила"))

                # Сообщение
                if count_today == 0:
                    msg = "🎉 Ты не курила ни разу сегодня. Это сильно. Ты — крепкая."
                elif count_today < count_yesterday:
                    msg = f"👍 Сегодня меньше, чем вчера ({count_today} vs {count_yesterday}). Вот это настрой!"
                elif count_today > count_yesterday:
                    msg = f"💡 Сегодня получилось чуть больше ({count_today} vs {count_yesterday}). Ничего. Завтра — шанс изменить."
                else:
                    msg = f"➖ Сегодня столько же, сколько вчера ({count_today}). Иногда это тоже результат. Просто продолжай."

                try:
                    await bot.send_message(int(user_id_str), msg)
                except:
                    pass  # вдруг юзер заблокировал бота

            await asyncio.sleep(60)
        else:
            await asyncio.sleep(20)

# --- Запуск ---
if __name__ == "__main__":
    Thread(target=run_flask).start()
    loop = asyncio.get_event_loop()
    loop.create_task(daily_check())
    executor.start_polling(dp, skip_updates=True)
