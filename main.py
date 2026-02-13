import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

USER_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

# ID группы с админами
ADMIN_GROUP_ID = -1003808434882  # Замените на свой ID группы

# Список забаненных пользователей (можно заменить на базу данных)
banned_users = set()

# Хранение ID сообщения для ответа
message_to_reply = {}

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
        await update.message.reply_text("❌ Вы заблокированы и не можете отправлять сообщения.")
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

# Функция для обработки callback запросов (например, для кнопки "В бан")
async def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data = query.data.split('_')
    action = data[0]

    # Параметры для действия
    orig_msg_id = None
    user_id = None

    if len(data) > 1:
        orig_msg_id = int(data[1]) if len(data) > 1 else None
    if len(data) > 2:
        user_id = int(data[2]) if len(data) > 2 else None

    if action == "send":
        try:
            if not orig_msg_id or not user_id:
                await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="❌ Ошибка: Не удалось получить данные для пересылки.")
                return

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
            if not user_id:
                await query.edit_message_reply_markup(reply_markup=None)
                await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="❌ Ошибка: Не удалось получить данные для бана.")
                return

            # Проверяем, является ли пользователь владельцем чата или администратором
            chat_member = await context.bot.get_chat_member(ADMIN_GROUP_ID, user_id)
            if chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                await query.edit_message_reply_markup(reply_markup=None)
                await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="❌ Невозможно заблокировать владельца или администратора.")
                return

            # Добавляем пользователя в список забаненных
            banned_users.add(user_id)

            # Кнопки не пропадают, обновим клавиатуру с кнопкой "Ответить"
            keyboard = [
                [
                    InlineKeyboardButton("Посмотреть профиль", url=f"tg://user?id={user_id}"),
                    InlineKeyboardButton("Отправить в канал", callback_data=f"send_{orig_msg_id}_{user_id}"),
                    InlineKeyboardButton("В бан", callback_data=f"ban_{user_id}"),
                    InlineKeyboardButton("Ответить", callback_data=f"reply_{orig_msg_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_reply_markup(reply_markup=reply_markup)
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"✅ Пользователь {user_id} заблокирован в боте и добавлен в банлист.")
        except Exception as e:
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"❌ Ошибка: {e}")

    elif action == "reply":
        try:
            if not orig_msg_id:
                await query.edit_message_reply_markup(reply_markup=None)
                await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="❌ Ошибка: Не удалось получить данные для ответа.")
                return

            # Сохраняем ID сообщения, на которое администратор должен ответить
            message_id = int(data[1])

            # Сохраняем сообщение для ответа
            message_to_reply[update.callback_query.from_user.id] = message_id

            await query.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="✅ Теперь вы можете использовать команду /reply для отправки ответа.")
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

    # Обрабатываем обычные сообщения от пользователей
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND & ~filters.Chat(ADMIN_GROUP_ID), handle_message))

    # Обрабатываем callback запросы
    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()

if __name__ == '__main__':
    main()



