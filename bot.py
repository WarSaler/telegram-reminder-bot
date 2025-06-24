# bot.py

import os
import logging
import threading
import time
import datetime
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytz
import requests
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.error import Conflict

# — Настройка логирования —
logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# — Переменные окружения —
BOT_TOKEN  = os.environ['BOT_TOKEN']
PORT       = int(os.environ.get("PORT", "8000"))
BASE_URL   = os.environ.get("BASE_URL")          # например https://telegram-reminder-bot-j9mc.onrender.com/
CHATS_FILE = 'chats.json'

# — Московская зона —
MSK = pytz.timezone("Europe/Moscow")

# — Ваше боевое расписание —
SCHEDULE = [
    { "time": "20:50", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1095733793">Переключить депозиты из таблицы API deposits</a>' },
    { "time": "20:50", "text": '📢 <b>Авто методы:</b>\nВыключить депозиты BDT_rocket_gb в админке (либо попросить коллегу) Выключили BDT_rocket_gb на сайте\n@jurxis @nii_med @gnxt_monitoring @Lika_mbt @Vikgmbt' },
    { "time": "21:55", "text": '❌ <a href="https://mostbet2.com/admin/payout-route/list?filter%5BpayoutMethod%5D%5Bvalue%5D=khalti_birpay">Выключить метод выплат Khalti_birpay в админке</a>' },
    { "time": "22:20", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение депозитов BDT</a>' },
    { "time": "02:45", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение ручных депозитов BDT</a>' },
    { "time": "02:50", "text": '⚠️ <a href="https://docs.google.com/spreadsheets/d/1bmnhijfGGcA9Vp1Zkw07JoOFCE6IJk0U/edit?pli=1&gid=1749528799">Выключить депозиты и выплаты агента Naji_MAD</a>' },
    { "time": "02:55", "text": '✅ <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1095733793">Включить API депозиты по BDT</a>' },
    { "time": "02:55", "text": '🔄 <a href="https://mostbet2.com/admin/app/paymentroute/list?filter%5BpaymentMethod%5D%5Bvalue%5D=rocket_gb">Включить депозиты BDT_rocket_gb в админке</a>\n📢 Авто методы: Включили BDT_rocket_gb на сайте\n@jurxis @nii_med @gnxt_monitoring @Lika_mbt @Vikgmbt' },
    { "time": "06:20", "text": '🔒 <a href="https://docs.google.com/spreadsheets/d/1J89GcldOX_xfqxNVhzhcjIGmuQ40Y01QsoMbJWDstCU/edit?pli=1&gid=2063840569">Выключить реквизиты и выплаты шифтовых агентов Индии</a>' },
    { "time": "11:20", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение депозитов BDT</a>' },
    { "time": "18:20", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение депозитов BDT</a>' },
    { "time": "10:00", "text": '📊 <a href="https://new.admgrnb.com/greenback/payment-orders">Регулярная выгрузка! До 12:00 МСК выгрузка аппрувнутых депозитов из Greenback</a>' },
    { "time": "10:00", "text": '🗓️ <b>По понедельникам до 12:00 МСК:</b> отправляем Шамилю 3 выгрузки\n<a href="https://confluence.dats.tech/pages/viewpage.action?pageId=760321781">Ссылка на инструкцию</a>' },
]

# — HTTP-healthcheck для Render —
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_http_server():
    HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever()

# — Keep-alive, чтобы контейнер не спал —
def keep_alive():
    if not BASE_URL:
        logger.warning("BASE_URL не задан, keep-alive отключён")
        return
    while True:
        try:
            requests.get(BASE_URL, timeout=5)
            logger.info("Keep-alive pinged %s", BASE_URL)
        except Exception as e:
            logger.warning("Keep-alive failed: %s", e)
        time.sleep(300)

# — Работа с файлом чатов —
def load_chats():
    try:
        with open(CHATS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_chats(chats):
    with open(CHATS_FILE, 'w') as f:
        json.dump(chats, f)

# — Рассылка сообщения во все сохранённые чаты —
def broadcast(text: str, context: CallbackContext):
    chats = load_chats()
    for chat_id in chats:
        try:
            context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error("Не удалось отправить в %s: %s", chat_id, e)

# — Игнорируем только Conflict —
def error_handler(update: Update, context: CallbackContext):
    if isinstance(context.error, Conflict):
        return
    logger.error("Необработанная ошибка", exc_info=context.error)

# — Команды —
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    chats = load_chats()
    if chat_id not in chats:
        chats.append(chat_id)
        save_chats(chats)
        logger.info("Добавлен чат %s", chat_id)
    update.message.reply_text("✅ Бот активирован в этом чате.")

def test(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Тестовое напоминание!")

def next_notification(update: Update, context: CallbackContext):
    now = datetime.datetime.now(MSK)
    best, best_delta = None, None
    for item in SCHEDULE:
        hh, mm = map(int, item["time"].split(":"))
        run_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if run_dt < now:
            run_dt += datetime.timedelta(days=1)
        delta = run_dt - now
        if best_delta is None or delta < best_delta:
            best, best_delta = item, delta
    send_time = (now + best_delta).strftime("%Y-%m-%d %H:%M")
    update.message.reply_text(
        f"📅 Ближайшее уведомление в {send_time}:\n{best['text']}",
        parse_mode=ParseMode.HTML
    )

def all_notifications(update: Update, context: CallbackContext):
    today_items = []
    for item in SCHEDULE:
        hh, mm = map(int, item["time"].split(":"))
        today_items.append((datetime.time(hh, mm), item["text"]))
    today_items.sort(key=lambda x: (x[0].hour, x[0].minute))
    lines = ["📅 <b>Уведомления на сегодня (MSK):</b>"]
    for t, txt in today_items:
        lines.append(f"{t.strftime('%H:%M')} — {txt}")
    update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

# — Планируем «боевые» уведомления —
def schedule_notifications(job_queue):
    job_queue.scheduler.configure(timezone=MSK)
    for item in SCHEDULE:
        hh, mm = map(int, item["time"].split(":"))
        text = item["text"]
        if "По понедельникам" in text:
            job_queue.run_daily(
                callback=lambda ctx, m=text: broadcast(m, ctx),
                time=datetime.time(hour=hh, minute=mm),
                days=(0,),
            )
        else:
            job_queue.run_daily(
                callback=lambda ctx, m=text: broadcast(m, ctx),
                time=datetime.time(hour=hh, minute=mm),
            )
    logger.info("Все уведомления запланированы согласно SCHEDULE")

# — Точка входа —
def main():
    # Запускаем HTTP-сервер и keep-alive
    threading.Thread(target=run_http_server, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()

    # Инициализируем бота
    updater = Updater(token=BOT_TOKEN, use_context=True)
    updater.bot.delete_webhook()
    dp = updater.dispatcher
    dp.add_error_handler(error_handler)

    # Регистрируем команды
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("test", test))
    dp.add_handler(CommandHandler("next", next_notification))
    dp.add_handler(CommandHandler("all", all_notifications))

    # Планируем рассылку
    schedule_notifications(updater.job_queue)

    # (Удалено: тестовое ежечасное уведомление run_repeating)

    # Запускаем polling
    updater.start_polling(drop_pending_updates=True)
    logger.info("Polling начат, бот готов к работе")
    updater.idle()

if __name__ == "__main__":
    main()
