# bot.py

import os
import logging
import threading
import time
import datetime
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
BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID   = os.environ['CHAT_ID']
PORT      = int(os.environ.get("PORT", "8000"))
BASE_URL  = os.environ.get("BASE_URL")  # для keep-alive пинга

# — Московская зона для планировщика —
MSK = pytz.timezone("Europe/Moscow")

# — Ваше боевое расписание (MSK) —
SCHEDULE = [
    { "time": "20:50", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPw...">Переключить депозиты из таблицы API deposits</a>' },
    { "time": "20:50", "text": '📢 <b>Авто методы:</b>\nВыключили BDT_rocket_gb на сайте\n@jurxis @nii_med @gnxt_monitoring @Lika_mbt @Vikgmbt' },
    { "time": "21:55", "text": '❌ <a href="https://mostbet2.com/admin/...">Выключить метод выплат Khalti_birpay в админке</a>' },
    { "time": "22:20", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPw...">Сделать переключение депозитов BDT</a>' },
    { "time": "02:45", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPw...">Сделать переключение депозитов BDT</a>' },
    { "time": "03:00", "text": '⚠️ <a href="https://docs.google.com/spreadsheets/d/1bmnhijfGG...">Выключить депозиты и выплаты агента Naji_MAD</a>' },
    { "time": "03:05", "text": '✅ <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPw...">Включить API депозиты по BDT</a>' },
    { "time": "02:50", "text": '⏲️ Выключить депозиты BDT (до 03:00 GMT+3)' },
    { "time": "03:10", "text": '🔄 <a href="https://mostbet2.com/admin/...">Включить депозиты BDT_rocket_gb в админке</a>\n📢 Авто методы: Включили BDT_rocket_gb на сайте\n@jurxis @nii_med @gnxt_monitoring @Lika_mbt @Vikgmbt' },
    { "time": "06:20", "text": '🔒 <a href="https://docs.google.com/spreadsheets/d/1J89GcldOX...">Выключить реквизиты и выплаты шифтовых агентов Индии</a>' },
    { "time": "11:20", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPw...">Сделать переключение депозитов BDT</a>' },
    { "time": "18:20", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPw...">Сделать переключение депозитов BDT</a>' },
    { "time": "10:00", "text": '📊 <a href="https://new.admgrnb.com/greenback/payment-orders">Регулярная выгрузка! До 12:00 МСК выгрузка аппрувнутых депозитов из Greenback</a>' },
    { "time": "10:00", "text": '🗓️ <b>По понедельникам до 12:00 МСК:</b> отправляем Шамилю 3 выгрузки\n<a href="https://confluence.dats.tech/pages/...">Ссылка на инструкцию</a>' },
]

# — HTTP-healthcheck для Render —
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_http_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    logger.info(f"HTTP healthcheck listening on port {PORT}")
    server.serve_forever()

# — Keep-alive: пингуем свой BASE_URL раз в 5 минут —
def keep_alive():
    if not BASE_URL:
        logger.warning("BASE_URL not set, keep-alive thread disabled")
        return
    while True:
        try:
            requests.get(BASE_URL, timeout=5)
            logger.info("Keep-alive pinged %s", BASE_URL)
        except Exception as e:
            logger.warning("Keep-alive failed: %s", e)
        time.sleep(300)

# — Error-handler: игнорим только Conflict —
def error_handler(update: Update, context: CallbackContext):
    if isinstance(context.error, Conflict):
        return
    logger.error("Необработанная ошибка", exc_info=context.error)

# — Команды бота —
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Я бот-напоминалка.")

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
    today = datetime.datetime.now(MSK).date()
    items = []
    for item in SCHEDULE:
        hh, mm = map(int, item["time"].split(":"))
        items.append((datetime.time(hh, mm), item["text"]))
    items.sort(key=lambda x: (x[0].hour, x[0].minute))
    lines = ["📅 <b>Уведомления на сегодня (MSK):</b>"]
    for t, txt in items:
        lines.append(f"{t.strftime('%H:%M')} — {txt}")
    update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

# — Планирование боевых уведомлений —
def schedule_notifications(job_queue):
    job_queue.scheduler.configure(timezone=MSK)
    for item in SCHEDULE:
        hh, mm = map(int, item["time"].split(":"))
        text = item["text"]
        job_queue.run_daily(
            callback=lambda ctx, m=text: ctx.bot.send_message(
                chat_id=CHAT_ID, text=m, parse_mode=ParseMode.HTML
            ),
            time=datetime.time(hour=hh, minute=mm),
        )
    logger.info("Все уведомления запланированы согласно SCHEDULE")

# — Точка входа —
def main():
    # 1) HTTP-healthcheck
    threading.Thread(target=run_http_server, daemon=True).start()
    # 2) Keep-alive пинги
    threading.Thread(target=keep_alive, daemon=True).start()

    # 3) Инициализация бота
    updater = Updater(token=BOT_TOKEN, use_context=True)
    updater.bot.delete_webhook()
    dp = updater.dispatcher
    dp.add_error_handler(error_handler)

    # 4) Регистрируем команды
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("test", test))
    dp.add_handler(CommandHandler("next", next_notification))
    dp.add_handler(CommandHandler("all", all_notifications))

    # 5) Планируем боевые уведомления
    schedule_notifications(updater.job_queue)

    # 6) Запуск polling
    updater.start_polling(drop_pending_updates=True)
    logger.info("Polling начат, бот готов к работе")
    updater.idle()

if __name__ == "__main__":
    main()
