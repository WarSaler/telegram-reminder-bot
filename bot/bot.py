# bot.py

import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# --- Логирование ---
logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Читаем из окружения ---
BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID   = os.environ['CHAT_ID']

# --- Команды бота ---
def start(update: Update, context: CallbackContext):
    logger.info(f"/start от {update.effective_chat.id}")
    update.message.reply_text("Привет! Я напоминалка. Отправь /test для проверки.")

def test(update: Update, context: CallbackContext):
    logger.info(f"/test от {update.effective_chat.id}")
    update.message.reply_text("✅ Это тестовое напоминание!")

def send(update: Update, context: CallbackContext):
    text = ' '.join(context.args)
    logger.info(f"/send с текстом: {text}")
    if not text:
        update.message.reply_text("Использование: /send ТЕКСТ_СООБЩЕНИЯ")
    else:
        context.bot.send_message(chat_id=CHAT_ID, text=text)
        update.message.reply_text("Сообщение отправлено.")

# --- Автоматическое задание ---
def hourly_job(context: CallbackContext):
    logger.info("Выполняется ежечасное уведомление")
    context.bot.send_message(chat_id=CHAT_ID, text="⏰ Ежечасное напоминание")

# --- Точка входа ---
def main():
    logger.info("Запускаю бота…")
    updater = Updater(token=BOT_TOKEN, use_context=True)

    # Сбрасываем все вебхуки, чтобы не было конфликта getUpdates vs webhook
    updater.bot.delete_webhook()

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("test", test))
    dp.add_handler(CommandHandler("send", send))

    # Планируем: первое выполнение сразу, затем каждые 3600 сек
    updater.job_queue.run_repeating(hourly_job, interval=3600, first=0)

    # Запуск polling с очисткой старых апдейтов
    updater.start_polling(drop_pending_updates=True)
    logger.info("Polling начат, бот готов к работе")
    updater.idle()

if __name__ == "__main__":
    main()
