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

# --- Хендлеры записи ---
@dp.message_handler(lambda msg: msg.text.lower().startswith("курила"))
async def kurila(message: types.Message):
    log_event(message.from_user.id, message.text)
    await message.reply("Записано — курила.")

@dp.message_handler(lambda msg: msg.text.lower().startswith("удержалась"))
async def ud(message: types.Message):
    log_event(message.from_user.id, message.text)
    await message.reply("Молодец — удержалась.")

# --- Универсальная функция отчета ---
def build_report(data, start_time, detailed=True):
    filtered = [
        e for e in data
        if datetime.fromisoformat(e["time"]) >= start_time
    ]
    kurila = [e for e in filtered if e["event"].lower().startswith("курила")]
    ud = [e for e in filtered if e["event"].lower().startswith("удержалась")]

    lines = [
        f"Курила: {len(kurila)}",
        f"Удержалась: {len(ud)}"
    ]

    if filtered and detailed:
        lines.append("Комментарии:")
        for e in filtered:
            t = datetime.fromisoformat(e["time"]).strftime('%d.%m %H:%M')
            lines.append(f" {t} — {e['event']}")

    return "\n".join(lines)

# --- Статистика: только день подробно, остальное кратко ---
@dp.message_handler(lambda msg: msg.text.lower() == "статистика")
async def stats_main(message: types.Message):
    data = load_data().get(str(message.from_user.id), [])
    if not data:
        await message.reply("Пока ничего не записано.")
        return

    now = datetime.utcnow() + timedelta(hours=3)
    periods = {
        "Сегодня": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "7 дней": now - timedelta(days=7),
        "30 дней": now - timedelta(days=30),
        "180 дней": now - timedelta(days=180),
    }

    msg_lines = []

    for label, start_time in periods.items():
        detailed = (label == "Сегодня")
        msg_lines.append(f"📅 *{label}*:")
        msg_lines.append(build_report(data, start_time, detailed=detailed))
        msg_lines.append("")

    await message.reply("\n".join(msg_lines), parse_mode="Markdown")

# --- Команды для развёрнутой статистики ---
@dp.message_handler(lambda msg: msg.text.lower() in ("статистика неделя", "статистика месяц", "статистика полгода"))
async def stats_extended(message: types.Message):
    periods = {
        "статистика неделя": ("📅 Подробная статистика за 7 дней", timedelta(days=7)),
        "статистика месяц": ("📅 Подробная статистика за 30 дней", timedelta(days=30)),
        "статистика полгода": ("📅 Подробная статистика за 180 дней", timedelta(days=180)),
    }

    key = message.text.lower()
    title, delta = periods[key]

    data = load_data().get(str(message.from_user.id), [])
    if not data:
        await message.reply("Пока ничего не записано.")
        return

    start_time = (datetime.utcnow() + timedelta(hours=3)) - delta
    report = build_report(data, start_time, detailed=True)
    await message.reply(f"*{title}*\n\n{report}", parse_mode="Markdown")

# --- Сброс данных ---
@dp.message_handler(lambda msg: msg.text.lower().startswith("сброс"))
async def reset(message: types.Message):
    d = load_data()
    if str(message.from_user.id) in d:
        del d[str(message.from_user.id)]
        save_data(d)
        await message.reply("Все записи удалены.")
    else:
        await message.reply("Нечего удалять — записей не было.")

# --- Напоминалка в 21:00 по МСК ---
async def daily_check():
    while True:
        now = datetime.utcnow() + timedelta(hours=3)
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
                    pass
            await asyncio.sleep(60)
        else:
            await asyncio.sleep(20)

# --- Запуск ---
if __name__ == "__main__":
    Thread(target=run_flask).start()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.delete_webhook(drop_pending_updates=True))
    loop.create_task(daily_check())
    executor.start_polling(dp, skip_updates=True)
