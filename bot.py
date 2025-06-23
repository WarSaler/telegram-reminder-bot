# bot.py

import os
import logging
import threading
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.error import Conflict

# ============= НАСТРОЙКИ =============

# Расписание: для каждого уведомления указываем время (HH:MM) и HTML-текст
SCHEDULE = [
    # В 20:50 — переключить депозиты из таблицы API deposits
    {
        "time": "20:50",
        "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1095733793">Переключить депозиты из таблицы API deposits</a>'
    },
    # В 20:50 — уведомление в Авто методы о выключении BDT_rocket_gb
    {
        "time": "20:50",
        "text": (
            "📢 <b>Авто методы:</b>\n"
            "Выключили BDT_rocket_gb на сайте\n"
            "@jurxis @nii_med @gnxt_monitoring @Lika_mbt @Vikgmbt"
        )
    },
    # В 21:55 — выключить метод выплат Khalti_birpay
    {
        "time": "21:55",
        "text": (
            '❌ <a href="https://mostbet2.com/admin/payout-route/list?filter%5Bcurrency%5D%5Btype%5D=&filter%5BpayoutMethod%5D%5Bvalue%5D=khalti_birpay">'
            "Выключить метод выплат Khalti_birpay в админке</a>"
        )
    },
    # В 22:20 — переключение депозитов BDT
    {
        "time": "22:20",
        "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение депозитов BDT</a>'
    },
    # В 02:45 — переключение депозитов BDT
    {
        "time": "02:45",
        "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение депозитов BDT</a>'
    },
    # Выключить депозиты и выплаты агента Naji_MAD
    {
        "time": "03:00",
        "text": (
            '⚠️ <a href="https://docs.google.com/spreadsheets/d/1bmnhijfGGcA9Vp1Zkw07JoOFCE6IJk0U/edit?pli=1&gid=1749528799">'
            "Выключить депозиты и выплаты агента Naji_MAD</a>"
        )
    },
    # Включить API депозиты по BDT
    {
        "time": "03:05",
        "text": '✅ <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1095733793">Включить API депозиты по BDT</a>'
    },
    # Выключить депозиты BDT (таймслот до 3:00 GMT+3)
    {
        "time": "02:50",
        "text": '⏲️ Выключить депозиты BDT (таймслот до 3:00 GMT+3)'
    },
    # Включить депозиты BDT_rocket_gb в админке + уведомление в Авто методы
    {
        "time": "03:10",
        "text": (
            '🔄 <a href="https://mostbet2.com/admin/app/paymentroute/list?filter%5BpaymentMethod%5D%5Bvalue%5D=rocket_gb">'
            "Включить депозиты BDT_rocket_gb в админке</a>\n"
            "📢 Авто методы: Включили BDT_rocket_gb на сайте @jurxis @nii_med @gnxt_monitoring @Lika_mbt @Vikgmbt"
        )
    },
    # В 06:20 — выключить реквизиты и выплаты шифтовых агентов Индии
    {
        "time": "06:20",
        "text": '🔒 <a href="https://docs.google.com/spreadsheets/d/1J89GcldOX_xfqxNVhzhcjIGmuQ40Y01QsoMbJWDstCU/edit?pli=1&gid=2063840569">Выключить реквизиты и выплаты шифтовых агентов Индии</a>'
    },
    # В 11:20 — переключение депозитов BDT
    {
        "time": "11:20",
        "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение депозитов BDT</a>'
    },
    # В 18:20 — переключение депозитов BDT
    {
        "time": "18:20",
        "text": '🔄 <a href="https://docs.google.com/spreadsheets/d/1LggaqDZjPwGGj7Mqher4D6mHhgmhL1Ed/edit?pli=1&gid=1393952854">Сделать переключение депозитов BDT</a>'
    },
    # В 10:00 — регулярная выгрузка из Greenback
    {
        "time": "10:00",
        "text": (
            '📊 <a href="https://new.admgrnb.com/greenback/payment-orders">'
            "Регулярная выгрузка! До 12:00 МСК выгрузка аппрувнутых депозитов из Greenback</a>"
        )
    },
    # В 10:00 (по понедельникам) — 3 выгрузки Шамилю
    {
        "time": "10:00",
        "text": (
            '🗓️ <b>По понедельникам до 12:00 МСК:</b> отправляем Шамилю 3 выгрузки\n'
            '<a href="https://confluence.dats.tech/pages/viewpage.action?pageId=760321781">'
            "Ссылка на инструкцию</a>"
        )
    },
]

# Остальные константы
BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID   = os.environ['CHAT_ID']
PORT      = int(os.environ.get("PORT", "8000"))

# ====== Логирование и HTTP-сервер (для Render) ======
logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def run_http_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    logger.info(f"HTTP healthcheck listening on port {PORT}")
    server.serve_forever()

# ====== Error-handler для игнорирования конфликтов ======
def error_handler(update: Update, context: CallbackContext):
    err = context.error
    if isinstance(err, Conflict):
        return  # просто молча игнорим
    logger.error("Необработанная ошибка", exc_info=err)

# ====== Команды бота ======
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Я бот-напоминалка.")

def test(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Тестовое напоминание!")

# ====== Планирование уведомлений из SCHEDULE ======
def schedule_notifications(job_queue):
    for item in SCHEDULE:
        hh, mm = map(int, item["time"].split(":"))
        text = item["text"]
        # каждый день в заданное время
        job_queue.run_daily(
            callback=lambda ctx, m=text: ctx.bot.send_message(
                chat_id=CHAT_ID,
                text=m,
                parse_mode=ParseMode.HTML
            ),
            time=datetime.time(hh, mm),
        )
    logger.info("Все уведомления запланированы согласно SCHEDULE")

# ====== Точка входа ======
def main():
    # 1) Старт HTTP healthcheck
    threading.Thread(target=run_http_server, daemon=True).start()

    # 2) Инициализация бота
    updater = Updater(token=BOT_TOKEN, use_context=True)
    updater.bot.delete_webhook()

    dp = updater.dispatcher
    dp.add_error_handler(error_handler)
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("test", test))

    # 3) Планируем все ваши напоминания
    schedule_notifications(updater.job_queue)

    # 4) Запускаем polling
    updater.start_polling(drop_pending_updates=True)
    logger.info("Polling начат, бот готов к работе")
    updater.idle()

if __name__ == "__main__":
    main()
