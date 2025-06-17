import logging, json, os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text

API_TOKEN = os.getenv("API_TOKEN")
DATA_FILE = 'cezura_data.json'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def load_data():
    try:
        return json.load(open(DATA_FILE, 'r'))
    except:
        return {}

def save_data(data):
    json.dump(data, open(DATA_FILE, 'w'), indent=2)

def log_event(u_id, event, comment=None):
    now = datetime.now().isoformat()
    d = load_data()
    key = str(u_id)
    d.setdefault(key, []).append({"event": event, "time": now, "comment": comment})
    save_data(d)

@dp.message_handler(Text(equals=['курила', 'удержалась', 'сдержалась', 'не курила'], ignore_case=True))
async def handle_event(msg: types.Message):
    text = msg.text.lower()
    comment = None
    parts = text.split(' ', 1)
    if len(parts) == 2:
        text, comment = parts[0], parts[1].strip()
    log_event(msg.from_user.id, text, comment)
    await msg.reply(f"Записано: *{text}*{f' ({comment})' if comment else ''}", parse_mode='Markdown')

@dp.message_handler(Text(equals='статистика', ignore_case=True))
async def show_stats(msg: types.Message):
    uid = str(msg.from_user.id)
    all_data = load_data().get(uid, [])
    now = datetime.now()
    buckets = {
      'день': now - timedelta(days=1),
      'неделя': now - timedelta(days=7),
      'месяц': now - timedelta(days=30),
      'полгода': now - timedelta(days=182),
    }
    resp = []
    for label, since in buckets.items():
        cnt = [e for e in all_data if datetime.fromisoformat(e['time']) >= since]
        resp.append(f"{label.capitalize()}: {len(cnt)}")
    # Детальная статистика
    detail = "\n".join(
      f"{e['time'][:10]} – {e['event']}{': ' + e['comment'] if e.get('comment') else ''}"
      for e in all_data[-20:]
    )
    await msg.reply("📊 Статистика:\n" + "\n".join(resp) + "\n\nПоследние события:\n" + detail)

@dp.message_handler(Text(equals='удалить статистику', ignore_case=True))
async def clear_stats(msg: types.Message):
    d = load_data()
    d.pop(str(msg.from_user.id), None)
    save_data(d)
    await msg.reply("✅ Вся статистика удалена.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
