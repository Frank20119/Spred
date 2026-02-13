import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
from telegram import ChatMember

USER_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN'] = '8317714320:AAGBBVJet8pJmqfMsfxCktyEJNgDA6_nZJw'


# ID группы с админами
ADMIN_GROUP_ID = -1003808434882  # Замените на свой ID группы

# Список забаненных пользователей (можно заменить на базу данных)
banned_users = set()

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

    # Если пользователь забанен, не обрабатывать его сообщение
    if user_id in banned_users:
        await update.message.reply_text("Вы заблокированы и не можете отправлять сообщения.")
        return

    # Формируем текст для админов
    full_text = text if text else caption
    admin_text = f"Новое сообщение от пользователя {user_id}:\n{full_text}\n\nОтветить: /reply_{user_id} <текст>"

    # Кнопки для админов
    keyboard = [
        [
            InlineKeyboardButton("Посмотреть профиль", url=f"tg://user?id={user_id}"),
            InlineKeyboardButton("Отправить в канал", callback_data=f"send_{update.message.message_id}_{user_id}"),
            InlineKeyboardButton("В бан", callback_data=f"ban_{user_id}")
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

# Функция для обработки callback запросов
async def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("send_"):
        try:
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

    elif query.data.startswith("ban_"):
        try:
            user_id = int(query.data.split('_')[1])

            # Добавляем пользователя в список забаненных
            banned_users.add(user_id)
            
            # Ограничиваем пользователя в чате
            await context.bot.restrict_chat_member(
                chat_id=ADMIN_GROUP_ID,
                user_id=user_id,
                permissions=ChatMember(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                )
            )

            await query.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"✅ Пользователь {user_id} заблокирован.")
        except Exception as e:
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"❌ Ошибка: {e}")

# Команда для вывода списка забаненных пользователей
async def banlist(update: Update, context: CallbackContext):
    if update.message.from_user.id not in [admin.id for admin in await context.bot.get_chat_administrators(ADMIN_GROUP_ID)]:
        await update.message.reply_text("У вас нет прав для просмотра банлиста.")
        return

    if banned_users:
        banned_text = "\n".join([str(user_id) for user_id in banned_users])
        await update.message.reply_text(f"Забаненные пользователи:\n{banned_text}")
    else:
        await update.message.reply_text("Список забаненных пользователей пуст.")

# Команда для разбанивания пользователя
async def unban(update: Update, context: CallbackContext):
    if len(context.args) < 1:
        await update.message.reply_text("Укажите username для разбанивания.")
        return

    username = context.args[0]
    user = await context.bot.get_chat_member(ADMIN_GROUP_ID, username)
    
    if user.user.id in banned_users:
        banned_users.remove(user.user.id)

        # Разбаниваем пользователя
        await context.bot.restrict_chat_member(
            chat_id=ADMIN_GROUP_ID,
            user_id=user.user.id,
            permissions=ChatMember(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )

        await update.message.reply_text(f"Пользователь {username} разбанен.")
    else:
        await update.message.reply_text(f"Пользователь {username} не найден в банлисте.")

def main():
    application = Application.builder().token(USER_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("banlist", banlist))
    application.add_handler(CommandHandler("unban", unban))

    application.add_handler(MessageHandler(filters.Chat(ADMIN_GROUP_ID) & filters.Regex(r'^/reply_'), handle_admin_reply))
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND & ~filters.Chat(ADMIN_GROUP_ID), handle_message))

    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()

if __name__ == '__main__':
    main()
