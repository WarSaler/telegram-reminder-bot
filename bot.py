import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
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

# — HTTP-healthcheck для Render —
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

# — Error-handler: глушим только Conflict —
def error_handler(update, context):
    err = context.error
    if isinstance(err, Conflict):
        logger.warning("Conflict при getUpdates — игнорирую старый экземпляр.")
    else:
        logger.error("Необработанная ошибка", exc_info=err)

# — Команды бота —
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Отправь /test для проверки.")

def test(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Тестовое напоминание!")

def send(update: Update, context: CallbackContext):
    text = ' '.join(context.args)
    if not text:
        update.message.reply_text("Использование: /send ТЕКСТ_СООБЩЕНИЯ")
    else:
        context.bot.send_message(chat_id=CHAT_ID, text=text)
        update.message.reply_text("Сообщение отправлено.")

# — Автоматическое ежечасное напоминание —
def hourly_job(context: CallbackContext):
    context.bot.send_message(chat_id=CHAT_ID, text="⏰ Ежечасное напоминание")

# — Точка входа —
def main():
    # 1) Запускаем HTTP-сервер в фоне
    threading.Thread(target=run_http_server, daemon=True).start()

    # 2) Инициализируем телеграм-бота
    updater = Updater(token=BOT_TOKEN, use_context=True)
    updater.bot.delete_webhook()
    dp = updater.dispatcher
    dp.add_error_handler(error_handler)

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("test", test))
    dp.add_handler(CommandHandler("send", send))
    updater.job_queue.run_repeating(hourly_job, interval=3600, first=0)

    # 3) Запускаем polling
    updater.start_polling(drop_pending_updates=True)
    logger.info("Polling начат, бот готов к работе")
    updater.idle()

if __name__ == "__main__":
    main()
