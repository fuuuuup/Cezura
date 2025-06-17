import logging, json, os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import Text
from aiogram.types import Message
from aiogram.utils import executor

API_TOKEN = os.getenv("API_TOKEN")
DATA_FILE = 'cezura_data.json'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

def load_data():
    try:
        with open(DATA_FILE) as f: return json.load(f)
    except: return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=2)

def log_event(uid, event, comment):
    now = datetime.now().isoformat()
    d = load_data()
    d.setdefault(str(uid), []).append({"event":event,"time":now,"comment":comment})
    save_data(d)

def filter_count(entries, days, event=None):
    cutoff = datetime.now() - timedelta(days=days)
    return [e for e in entries if datetime.fromisoformat(e["time"])>=cutoff
            and (event is None or e["event"]==event)]

@dp.message_handler(commands=['start'])
@dp.message_handler(Text(equals='start', ignore_case=True))
async def cmd_start(m:Message):
    await m.reply("Бот Цезура готов.")

@dp.message_handler(Text(equals=['курила','сдержалась','не курила'], ignore_case=True))
async def cmd_event(m:Message):
    parts = m.text.split(' ',1)
    event = parts[0].lower()
    comment = parts[1] if len(parts)>1 else ''
    log_event(m.from_user.id, event, comment)
    await m.reply(f"Записано: {event}" + (f" — «{comment}»" if comment else ''))

@dp.message_handler(Text(equals='статистика', ignore_case=True))
async def cmd_stats(m:Message):
    entries = load_data().get(str(m.from_user.id),[])
    resp = ""
    for days,label in [(1,'Сегодня'),(7,'Неделя'),(30,'Месяц'),(180,'Полгода')]:
        cnt = len(filter_count(entries, days))
        resp += f"{label}: всего {cnt}\n"
    await m.reply(resp.strip())

@dp.message_handler(Text(equals='удали статистику', ignore_case=True))
async def cmd_clear(m:Message):
    d = load_data()
    d.pop(str(m.from_user.id), None)
    save_data(d)
    await m.reply("Статистика очищена.")

@dp.message_handler(Text(equals='подробно', ignore_case=True))
async def cmd_details(m:Message):
    entries = load_data().get(str(m.from_user.id),[])
    lines = []
    for e in entries:
        t = datetime.fromisoformat(e["time"]).strftime("%Y-%m-%d %H:%M")
        com = f" — {e['comment']}" if e['comment'] else ''
        lines.append(f"{t}: {e['event']}{com}")
    await m.reply("\n".join(lines) or "Пока нет данных.")

if __name__=='__main__':
    executor.start_polling(dp, skip_updates=True)
