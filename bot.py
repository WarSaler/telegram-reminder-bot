# bot.py

import os
import logging
import threading
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from zoneinfo import ZoneInfo

from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.error import Conflict

# ========== Настройка логирования ==========
logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== Переменные окружения ==========
BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID   = os.environ['CHAT_ID']
PORT      = int(os.environ.get("PORT", "8000"))

# ========== HTTP-healthcheck для Render ==========
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_http_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    logger.info(f"HTTP healthcheck listening on port {PORT}")
    server.serve_forever()

# ========== Расписание ==========
# Время в формате "HH:MM" и HTML-текст (с вшитыми ссылками)
SCHEDULE = [
    { "time": "20:50", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1095733793">Переключить депозиты из таблицы API deposits</a>' },
    { "time": "20:50", "text": '📢 <b>Авто методы:</b>\nВыключили BDT_rocket_gb на сайте\n@jurxis @nii_med @gnxt_monitoring @Lika_mbt @Vikgmbt' },
    { "time": "21:55", "text": '❌ <a href="https://mostbet2.com/admin/payout-route/list?filter%5BpayoutMethod%5D%5Bvalue%5D=khalti_birpay">Выключить метод выплат Khalti_birpay в админке</a>' },
    { "time": "22:20", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение депозитов BDT</a>' },
    { "time": "02:45", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение депозитов BDT</a>' },
    { "time": "03:00", "text": '⚠️ <a href="https://docs.google.com/spreadsheets/d/1bmnhijfGGcA9Vp1Zkw07JoOFCE6IJk0U/edit?pli=1&gid=1749528799">Выключить депозиты и выплаты агента Naji_MAD</a>' },
    { "time": "03:05", "text": '✅ <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1095733793">Включить API депозиты по BDT</a>' },
    { "time": "02:50", "text": '⏲️ Выключить депозиты BDT (таймслот до 3:00 GMT+3)' },
    { "time": "03:10", "text": '🔄 <a href="https://mostbet2.com/admin/app/paymentroute/list?filter%5BpaymentMethod%5D%5Bvalue%5D=rocket_gb">Включить депозиты BDT_rocket_gb в админке</a>\n📢 Авто методы: Включили BDT_rocket_gb на сайте @jurxis @nii_med @gnxt_monitoring @Lika_mbt @Vikgmbt' },
    { "time": "06:20", "text": '🔒 <a href="https://docs.google.com/spreadsheets/d/1J89GcldOX_xfqxNVhzhcjIGmuQ40Y01QsoMbJWDstCU/edit?pli=1&gid=2063840569">Выключить реквизиты и выплаты шифтовых агентов Индии</a>' },
    { "time": "11:20", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение депозитов BDT</a>' },
    { "time": "18:20", "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение депозитов BDT</a>' },
    { "time": "10:00", "text": '📊 <a href="https://new.admgrnb.com/greenback/payment-orders">Регулярная выгрузка! До 12:00 МСК выгрузка аппрувнутых депозитов из Greenback</a>' },
    { "time": "10:00", "text": '🗓️ <b>По понедельникам до 12:00 МСК:</b> отправляем Шамилю 3 выгрузки\n<a href="https://confluence.dats.tech/pages/viewpage.action?pageId=760321781">Ссылка на инструкцию</a>' },
]

# ========== Error-handler ==========
def error_handler(update: Update, context: CallbackContext):
    err = context.error
    if isinstance(err, Conflict):
        return
    logger.error("Необработанная ошибка", exc_info=err)

# ========== Команды ==========
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Я бот-напоминалка.")

def test(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Тестовое напоминание!")

def next_notification(update: Update, context: CallbackContext):
    msk = ZoneInfo("Europe/Moscow")
    now = datetime.datetime.now(msk)
    best_delta, best = None, None
    for item in SCHEDULE:
        hh, mm = map(int, item["time"].split(":"))
        run_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if run_dt < now:
            run_dt += datetime.timedelta(days=1)
        delta = run_dt - now
        if best is None or delta < best_delta:
            best_delta, best = delta, item
    send_time = (now + best_delta).strftime("%Y-%m-%d %H:%M")
    update.message.reply_text(
        f"📅 Ближайшее уведомление в {send_time}:\n{best['text']}",
        parse_mode=ParseMode.HTML
    )

def all_notifications(update: Update, context: CallbackContext):
    msk = ZoneInfo("Europe/Moscow")
    now = datetime.datetime.now(msk)
    today = now.date()
    today_items = []
    for item in SCHEDULE:
        hh, mm = map(int, item["time"].split(":"))
        dt = datetime.datetime.combine(today, datetime.time(hh, mm), tzinfo=msk)
        today_items.append((dt.time(), item["text"]))
    today_items.sort(key=lambda x: (x[0].hour, x[0].minute))
    if not today_items:
        update.message.reply_text("Нет запланированных уведомлений на сегодня.")
        return
    lines = ["📅 <b>Уведомления на сегодня:</b>"]
    for t, text in today_items:
        lines.append(f"{t.strftime('%H:%M')} — {text}")
    update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

# ========== Планирование ==========
def schedule_notifications(job_queue):
    msk = ZoneInfo("Europe/Moscow")
    for item in SCHEDULE:
        hh, mm = map(int, item["time"].split(":"))
        text = item["text"]
        job_queue.run_daily(
            callback=lambda ctx, m=text: ctx.bot.send_message(
                chat_id=CHAT_ID, text=m, parse_mode=ParseMode.HTML
            ),
            time=datetime.time(hour=hh, minute=mm, tzinfo=msk),
        )
    logger.info("Все уведомления запланированы согласно SCHEDULE")

# ========== Main ==========
def main():
    # HTTP-healthcheck
    threading.Thread(target=run_http_server, daemon=True).start()

    updater = Updater(token=BOT_TOKEN, use_context=True)
    updater.bot.delete_webhook()
    dp = updater.dispatcher
    dp.add_error_handler(error_handler)

    # Регистрируем команды
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("test", test))
    dp.add_handler(CommandHandler("next", next_notification))
    dp.add_handler(CommandHandler("all", all_notifications))

    # Планируем
    schedule_notifications(updater.job_queue)

    # Запуск polling
    updater.start_polling(drop_pending_updates=True)
    logger.info("Polling начат, бот готов к работе")
    updater.idle()

if __name__ == "__main__":
    main()
