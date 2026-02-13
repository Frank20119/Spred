import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

USER_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

# ID группы с админами
ADMIN_GROUP_ID = -1003808434882  # Замените на свой ID группы

# Список забаненных пользователей (можно заменить на базу данных)
banned_users = set()

# Функция для проверки, является ли пользователь администратором
async def is_admin(user_id: int, context: CallbackContext) -> bool:
    admins = await context.bot.get_chat_administrators(ADMIN_GROUP_ID)
    return user_id in [admin.user.id for admin in admins]

# Функция для обработки команды /start (приветствие)
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        'Привет! Я бот для связи с администраторами. Напиши мне, и я отправлю твоё сообщение в группу администраторов.'
    )

# Функция для обработки сообщений от пользователей (текст, фото, видео)
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id if update.message.from_user else None
    caption = update.message.caption or ""
    text = update.message.text or ""

    if user_id is None:
        return  # Игнорируем сообщения без пользователя

    # Если пользователь забанен, не обрабатывать его сообщение
    if user_id in banned_users:
        await update.message.reply_text("Вы заблокированы и не можете отправлять сообщения.")
        return

    # Формируем текст для админов
    full_text = text if text else caption
    admin_text = f"Новое сообщение от пользователя {user_id}:\n{full_text}\n\nОтветить: используйте команду /reply <user_id> <text>."

    # Кнопки для админов
    keyboard = [
        [
            InlineKeyboardButton("Посмотреть профиль", url=f"tg://user?id={user_id}"),
            InlineKeyboardButton("Отправить в канал", callback_data=f"send_{update.message.message_id}_{user_id}"),
            InlineKeyboardButton("В бан", callback_data=f"ban_{user_id}"),
            InlineKeyboardButton("Ответить", callback_data=f"reply_{update.message.message_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение в группу администраторов
    if update.message.text:
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_text, reply_markup=reply_markup)
    elif update.message.photo:
        await context.bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=update.message.photo[-1].file_id, caption=admin_text, reply_markup=reply_markup)
    elif update.message.video:
        await context.bot.send_video(chat_id=ADMIN_GROUP_ID, video=update.message.video.file_id, caption=admin_text, reply_markup=reply_markup)

    # Подтверждаем получение сообщения
    await update.message.reply_text("Ваше сообщение отправлено администраторам! 👍")

# Функция для обработки команды /reply
async def reply(update: Update, context: CallbackContext):
    # Проверка, что только администратор может отправить ответ
    if not await is_admin(update.message.from_user.id, context):
        await update.message.reply_text("❌ Вы не являетесь администратором и не можете отправлять ответ.")
        return

    # Проверка на наличие аргументов (ID пользователя и текста ответа)
    if len(context.args) < 2:
        await update.message.reply_text("❌ Пожалуйста, укажите user_id и текст ответа. Пример: /reply 12345 Привет!")
        return

    # Получаем user_id и текст ответа
    user_id = int(context.args[0])
    reply_text = " ".join(context.args[1:])

    # Отправляем ответ пользователю
    try:
        await context.bot.send_message(chat_id=user_id, text=reply_text)
        await update.message.reply_text(f"Ответ отправлен пользователю {user_id}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке ответа: {e}")

# Функция для обработки callback запросов (например, для кнопки "В бан")
async def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data = query.data.split('_')
    action = data[0]

    if action == "send":
        try:
            orig_msg_id = int(data[1])
            user_id = int(data[2])
            
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

    elif action == "ban":
        try:
            user_id = int(data[1])

            # Проверка, является ли текущий пользователь администратором
            if not await is_admin(update.callback_query.from_user.id, context):  # Исправлено: используем callback_query
                await query.edit_message_reply_markup(reply_markup=None)
                await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="❌ Вы не являетесь администратором и не можете банить пользователей.")
                return

            # Добавляем пользователя в список забаненных
            banned_users.add(user_id)

            # Ограничиваем пользователя в чате (в бан)
            await context.bot.restrict_chat_member(
                chat_id=ADMIN_GROUP_ID,
                user_id=user_id,
                permissions=ChatPermissions(
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

    elif action == "reply":
        try:
            # Получаем информацию о сообщении, на которое администратор должен ответить
            original_message = query.message.reply_to_message
            if original_message:
                user_id = original_message.from_user.id
                await context.bot.send_message(chat_id=user_id, text="Ваш ответ от администратора.")
                await query.edit_message_reply_markup(reply_markup=None)
                await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"Администратор подготовил ответ пользователю {user_id}.")
            else:
                await query.edit_message_reply_markup(reply_markup=None)
                await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="❌ Не удалось найти сообщение для ответа.")
        except Exception as e:
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"❌ Ошибка: {e}")

# Команда для вывода списка забаненных пользователей
async def banlist(update: Update, context: CallbackContext):
    # Проверка, что только администратор может видеть банлист
    if not await is_admin(update.message.from_user.id, context):
        await update.message.reply_text("❌ У вас нет прав для просмотра банлиста.")
        return

    if banned_users:
        banned_text = "\n".join([str(user_id) for user_id in banned_users])
        await update.message.reply_text(f"Забаненные пользователи:\n{banned_text}")
    else:
        await update.message.reply_text("Список забаненных пользователей пуст.")

# Команда для разбанивания пользователя
async def unban(update: Update, context: CallbackContext):
    # Проверка, что только администратор может разбанить
    if not await is_admin(update.message.from_user.id, context):
        await update.message.reply_text("❌ Вы не являетесь администратором, и не можете разбанивать пользователей.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("❌ Укажите username для разбанивания.")
        return

    username = context.args[0]
    try:
        user = await context.bot.get_chat_member(ADMIN_GROUP_ID, username)
        if user.user.id in banned_users:
            banned_users.remove(user.user.id)

            # Разблокируем пользователя
            await context.bot.restrict_chat_member(
                chat_id=ADMIN_GROUP_ID,
                user_id=user.user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )

            await update.message.reply_text(f"Пользователь {username} разбанен.")
        else:
            await update.message.reply_text(f"Пользователь {username} не найден в банлисте.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

def main():
    application = Application.builder().token(USER_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("banlist", banlist))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("reply", reply))  # Добавлена команда /reply для ответа на сообщения

    # Обрабатываем обычные сообщения от пользователей
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND & ~filters.Chat(ADMIN_GROUP_ID), handle_message))

    # Обрабатываем callback запросы
    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()

if __name__ == '__main__':
    main()
