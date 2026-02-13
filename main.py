import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

USER_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

# ID группы с админами
ADMIN_GROUP_ID = -1003808434882  # Замените на свой ID группы

# Функция для обработки команды /start (приветствие)
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        'Привет! Я бот для связи с администраторами. Напиши мне, и я отправлю твоё сообщение в группу администраторов.'
    )

# Функция для обработки сообщений от пользователей (текст, фото, видео)
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    caption = update.message.caption or ""
    text = update.message.text or ""

    # Формируем текст для админов
    full_text = text if text else caption
    admin_text = f"Новое сообщение от пользователя {user_id}:\n{full_text}\n\nОтветить: /reply_{user_id} <текст>"

    # Кнопки для админов
    keyboard = [
        [
            InlineKeyboardButton("Посмотреть профиль", url=f"tg://user?id={user_id}"),
            InlineKeyboardButton("Отправить в канал", callback_data=f"send_{update.message.message_id}_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message.text:
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_text, reply_markup=reply_markup)
    elif update.message.photo:
        await context.bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=update.message.photo[-1].file_id, caption=admin_text, reply_markup=reply_markup)
    elif update.message.video:
        await context.bot.send_video(chat_id=ADMIN_GROUP_ID, video=update.message.video.file_id, caption=admin_text, reply_markup=reply_markup)

    # Подтверждаем получение сообщения
    await update.message.reply_text("Ваше сообщение отправлено администраторам! 👍")

# Функция для обработки ответов от администраторов в группе
async def handle_admin_reply(update: Update, context: CallbackContext):
    if update.message.chat_id != ADMIN_GROUP_ID:
        return

    text = update.message.text
    if text and text.startswith('/reply_'):
        try:
            parts = text.split(' ', 1)
            command = parts[0]
            reply_text = parts[1] if len(parts) > 1 else ""

            user_id = int(command.replace('/reply_', ''))

            if not reply_text:
                await update.message.reply_text("Пожалуйста, напишите текст ответа после команды. Пример: /reply_12345 Привет!")
                return

            # Добавляем никнейм в ответ
            user_name = update.message.from_user.username or "Аноним"
            reply_message = f"Ответ от {user_name}:\n\n{reply_text}"

            # Отправляем ответ пользователю через Bot 1
            await context.bot.send_message(chat_id=user_id, text=reply_message)
            await update.message.reply_text(f"Ответ отправлен пользователю {user_id}.")
        except (ValueError, IndexError):
            await update.message.reply_text("Ошибка в формате команды. Используйте /reply_ID текст")
        except Exception as e:
            await update.message.reply_text(f"Не удалось отправить сообщение: {e}")

# Функция для обработки callback запросов
async def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("send_"):
        try:
            # Парсим данные: send_messageID_userID
            parts = query.data.split('_')
            orig_msg_id = int(parts[1])
            user_id = int(parts[2])
            
            # Пересылаем исходное сообщение пользователя в канал
            await context.bot.copy_message(
                chat_id='@swd_prk',
                from_chat_id=user_id,
                message_id=orig_msg_id
            )
            
            await query.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="✅ Оригинальное сообщение пользователя отправлено в канал!")
        except Exception as e:
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"❌ Ошибка: {e}")

def main():
    application = Application.builder().token(USER_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    application.add_handler(MessageHandler(filters.Chat(ADMIN_GROUP_ID) & filters.Regex(r'^/reply_'), handle_admin_reply))

    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND & ~filters.Chat(ADMIN_GROUP_ID), handle_message))

    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()

if __name__ == '__main__':
    main()
