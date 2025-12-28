import os
import logging
from datetime import datetime
from typing import Dict, Optional
from enum import Enum
import asyncio

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from database import TodoDatabase

# Загруженка конфигурации
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
class States(Enum):
    WAITING_TASK_NAME = 1
    WAITING_TIMEZONE = 2
    WAITING_REMINDER_TIME = 3
    WAITING_EVERYDAY_TASK_NAME = 4
    WAITING_EVERYDAY_TIMEZONE = 5
    WAITING_EVERYDAY_REMINDER_TIME = 6

# Инициализация базы данных
db = TodoDatabase()

# Инициализация планировщика напоминаний
scheduler = AsyncIOScheduler()

# Эмодзи
EMOJIS = {
    "list": "📋",
    "add": "➕",
    "done": "✅",
    "pending": "⏳",
    "back": "◀️",
    "success": "🎉",
    "time": "⏰",
    "warning": "⚠️",
    "error": "❌",
    "info": "ℹ️",
    "delete": "🗑️"
}

async def send_reminder(user_id: int, task_name: str, application: Application) -> None:
    """Отправляет 5 напоминаний пользователю через 3 секунды"""
    try:
        for i in range(1, 6):
            text = f"{EMOJIS['time']} *Напоминание #{i} из 5!*\n\n📝 Задача: {task_name}\n\n{EMOJIS['success']} Пора сделать это дело!"
            await application.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"✓ Напоминание #{i} отправлено пользователю {user_id}: {task_name}")
            
            # Ждём 3 секунды перед следующим напоминанием (кроме последнего)
            if i < 5:
                await asyncio.sleep(3)
    except Exception as e:
        logger.error(f"✗ Ошибка при отправке напоминания: {e}")

async def schedule_reminder(user_id: int, task_name: str, reminder_time: str, timezone: str, application: Application) -> None:
    """Планирует напоминание на указанное время"""
    try:
        hour, minute = map(int, reminder_time.split(':'))
        
        # Создаём уникальный ID для работы
        job_id = f"reminder_{user_id}_{datetime.now().timestamp()}"
        
        # Планируем напоминание
        scheduler.add_job(
            send_reminder,
            CronTrigger(hour=hour, minute=minute, timezone=timezone),
            args=[user_id, task_name, application],
            id=job_id,
            name=f"Reminder: {task_name}"
        )
        
        logger.info(f"⏰ Напоминание запланировано для {user_id} на {reminder_time} ({timezone})")
    except Exception as e:
        logger.error(f"✗ Ошибка при планировании напоминания: {e}")

def get_timezone_buttons() -> list:
    """Возвращает кнопки со всеми доступными часовыми поясами"""
    # Получаем все часовые пояса из pytz
    timezones = pytz.common_timezones
    
    # Популярные пояса для быстрого доступа
    popular_zones = [
        'Europe/Moscow',      # GMT+3
        'Asia/Baku',          # GMT+4
        'Asia/Tashkent',      # GMT+5
        'Asia/Kolkata',       # GMT+5:30
        'Asia/Bangkok',       # GMT+7
        'Asia/Shanghai',      # GMT+8
        'Europe/London',      # GMT+0
        'Europe/Berlin',      # GMT+1
        'Europe/Istanbul',    # GMT+3
        'America/New_York',   # GMT-5
        'America/Los_Angeles',# GMT-8
        'Australia/Sydney',   # GMT+10
    ]
    
    buttons = []
    
    # Добавляем популярные пояса
    for tz in popular_zones:
        if tz in timezones:
            # Получаем текущий UTC offset
            now = datetime.now(pytz.timezone(tz))
            offset = now.strftime('%z')
            offset_formatted = f"{offset[:3]}:{offset[3:]}" if len(offset) > 3 else offset
            
            buttons.append([
                InlineKeyboardButton(f"{tz} ({offset_formatted})", 
                                   callback_data=f"tz_{tz}")
            ])
    
    # Добавляем кнопку для всех остальных поясов
    buttons.append([
        InlineKeyboardButton("📌 Все часовые пояса", 
                           callback_data="show_all_tz")
    ])
    
    buttons.append([
        InlineKeyboardButton(f"{EMOJIS['back']} Отмена", 
                           callback_data="back_to_main")
    ])
    
    return buttons

async def show_timezone_selector(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает селектор часовых поясов"""
    query = update.callback_query
    await query.answer()
    
    text = f"""{EMOJIS['add']} *Добавить новую задачу*

Шаг 2️⃣ из 3️⃣

Выбери свой часовой пояс:

{EMOJIS['info']} Если твоего пояса нет в списке, нажми "Все часовые пояса" """
    
    keyboard = get_timezone_buttons()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)
    
    return States.WAITING_TIMEZONE.value

async def show_all_timezones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает все доступные часовые пояса в виде списка"""
    query = update.callback_query
    await query.answer()
    
    # Отправляем сообщение с просьбой написать часовой пояс
    text = f"""{EMOJIS['info']} *Введи название часового пояса*

Вот некоторые примеры:
• Europe/Moscow
• Europe/London
• Europe/Berlin
• Asia/Baku
• Asia/Shanghai
• America/New_York
• America/Los_Angeles
• Australia/Sydney

_Полный список доступен на https://en.wikipedia.org/wiki/List_of_tz_database_time_zones_

{EMOJIS['info']} Напиши название пояса (например: Europe/Moscow)"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['back']} Отмена", 
                            callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)
    
    # Сохраняем состояние
    context.user_data['waiting_for_custom_tz'] = True
    
    return States.WAITING_TIMEZONE.value

async def handle_unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для текстовых сообщений вне диалогов"""
    text = f"""🤔 *Я не понял команду*

Используй команду /start, чтобы вернуться в главное меню.

Или выбери действие:"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['back']} Главное меню", 
                            callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, 
                                   parse_mode=ParseMode.MARKDOWN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    text = f"""🤖 *Добро пожаловать в To-Do Bot!*

Привет, {user_name}! {EMOJIS['success']}

Здесь ты можешь управлять своими задачами и получать напоминания.

Выбери нужное действие:"""
    
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['pending']} Активные задачи", 
                               callback_data="pending_tasks"),
            InlineKeyboardButton(f"{EMOJIS['done']} Завершённые", 
                               callback_data="completed_tasks")
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['add']} Добавить новую задачу", 
                               callback_data="add_task")
        ],
        [
            InlineKeyboardButton("📝 Simple Todo список", 
                               callback_data="simple_todo_menu")
        ],
        [
            InlineKeyboardButton("🔔 Ежедневное напоминание", 
                               callback_data="everyday_reminder_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, 
                                   parse_mode=ParseMode.MARKDOWN)

async def pending_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает активные задачи"""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    todos = db.get_pending_todos(user_id)
    
    if not todos:
        text = f"{EMOJIS['list']} *Активные задачи*\n\n🎊 У тебя нет активных задач! Все дела завершены!"
        keyboard = [
            [InlineKeyboardButton(f"{EMOJIS['back']} Назад в меню", 
                                callback_data="back_to_main")]
        ]
    else:
        text = f"{EMOJIS['list']} *Активные задачи* ({len(todos)})\n\n"
        for i, todo in enumerate(todos, 1):
            reminder = todo.get('reminder_time', 'N/A')
            text += f"{i}. {todo['task']}\n   {EMOJIS['time']} Напоминание: {reminder}\n\n"
        
        keyboard = []
        for todo in todos:
            text_button = f"✓ {todo['task'][:20]}..." if len(todo['task']) > 20 else f"✓ {todo['task']}"
            keyboard.append([
                InlineKeyboardButton(text_button, 
                                   callback_data=f"complete_{todo['id']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton(f"{EMOJIS['back']} Назад в меню", 
                                callback_data="back_to_main")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)

async def completed_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает завершённые задачи"""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    todos = db.get_completed_todos(user_id)
    
    if not todos:
        text = f"{EMOJIS['done']} *Завершённые задачи*\n\n📪 У тебя ещё нет завершённых задач. Начни с чего-нибудь!"
        keyboard = [
            [InlineKeyboardButton(f"{EMOJIS['back']} Назад в меню", 
                                callback_data="back_to_main")]
        ]
    else:
        text = f"{EMOJIS['done']} *Завершённые задачи* ({len(todos)})\n\n"
        for i, todo in enumerate(todos, 1):
            created = todo.get('created_at', 'N/A')
            text += f"{i}. ~~{todo['task']}~~\n   📅 {created[:10]}\n\n"
        
        keyboard = []
        for todo in todos:
            text_button = f"🗑️ {todo['task'][:20]}..." if len(todo['task']) > 20 else f"🗑️ {todo['task']}"
            keyboard.append([
                InlineKeyboardButton(text_button, 
                                   callback_data=f"delete_{todo['id']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton(f"{EMOJIS['back']} Назад в меню", 
                                callback_data="back_to_main")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)

async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало добавления новой задачи"""
    query = update.callback_query
    await query.answer()
    
    text = f"""{EMOJIS['add']} *Добавить новую задачу*

Шаг 1️⃣ из 3️⃣

Назови мне свою задачу. Напиши её описание:

_Пример: "Купить молоко и хлеб"_"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['back']} Отмена", 
                            callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)
    
    # Очищаем флаг если есть
    context.user_data.pop('waiting_for_custom_tz', None)
    
    return States.WAITING_TASK_NAME.value

async def task_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение названия задачи"""
    user_id = update.effective_user.id
    task_name = update.message.text
    
    # Сохраняем название в контексте
    context.user_data['task_name'] = task_name
    
    text = f"""{EMOJIS['add']} *Добавить новую задачу*

Шаг 2️⃣ из 3️⃣

Спасибо! Теперь укажи свой часовой пояс."""
    
    keyboard = get_timezone_buttons()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, 
                                   parse_mode=ParseMode.MARKDOWN)
    
    return States.WAITING_TIMEZONE.value

async def timezone_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение часового пояса"""
    user_id = update.effective_user.id
    timezone_str = update.message.text.strip()
    
    # Проверяем, валиден ли часовой пояс
    try:
        pytz.timezone(timezone_str)
        context.user_data['timezone'] = timezone_str
    except pytz.exceptions.UnknownTimeZoneError:
        await update.message.reply_text(
            f"{EMOJIS['error']} *Неправильный часовой пояс!*\n\n"
            f"Пожалуйста, используй корректное название, например:\n"
            f"• Europe/Moscow\n"
            f"• Asia/Baku\n"
            f"• America/New_York",
            parse_mode=ParseMode.MARKDOWN
        )
        return States.WAITING_TIMEZONE.value
    
    text = f"""{EMOJIS['add']} *Добавить новую задачу*

Шаг 3️⃣ из 3️⃣

Отлично! Твой часовой пояс: *{timezone_str}* ✓

Теперь укажи, когда ты хочешь получить напоминание о этой задаче?

*Примеры:*
• 09:00 (9 утра)
• 14:30 (2:30 дня)
• 23:59 (11:59 вечера)

{EMOJIS['info']} Напиши время в формате ЧЧ:МММ (24-часовой формат)"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['back']} Отмена", 
                            callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, 
                                   parse_mode=ParseMode.MARKDOWN)
    
    return States.WAITING_REMINDER_TIME.value

async def timezone_button_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик нажатия на кнопку выбора часового пояса"""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    # Извлекаем название часового пояса
    timezone_str = query.data.replace("tz_", "")
    
    # Сохраняем в контексте
    context.user_data['timezone'] = timezone_str
    
    text = f"""{EMOJIS['add']} *Добавить новую задачу*

Шаг 3️⃣ из 3️⃣

Отлично! Твой часовой пояс: *{timezone_str}* ✓

Теперь укажи, когда ты хочешь получить напоминание о этой задаче?

*Примеры:*
• 09:00 (9 утра)
• 14:30 (2:30 дня)
• 23:59 (11:59 вечера)

{EMOJIS['info']} Напиши время в формате ЧЧ:МММ (24-часовой формат)"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['back']} Отмена", 
                            callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)
    
    return States.WAITING_REMINDER_TIME.value

async def reminder_time_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение времени напоминания"""
    user_id = update.effective_user.id
    reminder_time = update.message.text.strip()
    
    # Валидация времени
    try:
        datetime.strptime(reminder_time, "%H:%M")
    except ValueError:
        await update.message.reply_text(
            f"{EMOJIS['error']} *Неправильный формат времени!*\n\n"
            f"Пожалуйста, используй формат: ЧЧ:МММ\n"
            f"Пример: 09:30 или 14:00",
            parse_mode=ParseMode.MARKDOWN
        )
        return States.WAITING_REMINDER_TIME.value
    
    # Получаем данные из контекста
    task_name = context.user_data.get('task_name')
    timezone = context.user_data.get('timezone')
    
    # Добавляем задачу в базу данных
    success = db.add_todo(user_id, task_name, timezone, reminder_time)
    
    if success:
        # Планируем напоминание
        await schedule_reminder(user_id, task_name, reminder_time, timezone, context.application)
        
        text = f"""{EMOJIS['success']} *Отлично! Задача добавлена!*

*Задача:* {task_name}
*Напоминание:* {reminder_time}
*Часовой пояс:* {timezone}

{EMOJIS['info']} Ты получишь напоминание в указанное время! ⏰"""
        
        keyboard = [
            [
                InlineKeyboardButton(f"{EMOJIS['add']} Добавить ещё", 
                                   callback_data="add_task"),
                InlineKeyboardButton(f"{EMOJIS['back']} В меню", 
                                   callback_data="back_to_main")
            ]
        ]
    else:
        text = f"{EMOJIS['error']} *Ошибка при добавлении задачи!*\n\nПопробуй ещё раз."
        keyboard = [
            [InlineKeyboardButton(f"{EMOJIS['back']} Вернуться", 
                                callback_data="back_to_main")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, 
                                   parse_mode=ParseMode.MARKDOWN)
    
    # Очищаем пользовательские данные
    context.user_data.clear()
    
    return ConversationHandler.END

async def simple_todo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню простых todos"""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    todos = db.get_simple_todos(user_id)
    
    if not todos:
        text = f"📝 *Simple Todo Список*\n\n✨ У тебя нет простых todos! Добавь свой первый!"
        keyboard = [
            [InlineKeyboardButton("➕ Добавить todo", 
                                callback_data="simple_todo_add")],
            [InlineKeyboardButton(f"{EMOJIS['back']} Назад в меню", 
                                callback_data="back_to_main")]
        ]
    else:
        completed = sum(1 for t in todos if t['completed'])
        text = f"📝 *Simple Todo Список* ({len(todos)})\n\n"
        text += f"✅ Завершено: {completed}/{len(todos)}\n\n"
        
        for i, todo in enumerate(todos, 1):
            status = "✅" if todo['completed'] else "⏳"
            text += f"{status} {i}. {todo['task']}\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить todo", 
                                callback_data="simple_todo_add")]
        ]
        
        # Добавляем кнопки для каждого todo
        for todo in todos:
            if todo['completed']:
                action = "🗑️"
                callback = f"simple_todo_delete_{todo['id']}"
            else:
                action = "✓"
                callback = f"simple_todo_complete_{todo['id']}"
            
            text_button = f"{action} {todo['task'][:20]}..." if len(todo['task']) > 20 else f"{action} {todo['task']}"
            keyboard.append([
                InlineKeyboardButton(text_button, callback_data=callback)
            ])
        
        keyboard.append([
            InlineKeyboardButton(f"{EMOJIS['back']} Назад в меню", 
                                callback_data="back_to_main")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)

async def simple_todo_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало добавления простого todo"""
    query = update.callback_query
    await query.answer()
    
    text = f"""📝 *Добавить Simple Todo*

Напиши название своего простого todo:

_Пример: "Позвонить маме"_"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['back']} Отмена", 
                            callback_data="simple_todo_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)
    
    # Возвращаем состояние ожидания текста для простого todo
    return 2

async def simple_todo_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение текста для простого todo"""
    user_id = update.effective_user.id
    todo_text = update.message.text
    
    # Добавляем todo в базу
    success = db.add_simple_todo(user_id, todo_text)
    
    if success:
        text = f"✅ *Todo добавлен!*\n\n📝 {todo_text}\n\n{EMOJIS['success']} Добавлен в список!"
    else:
        text = f"{EMOJIS['error']} Ошибка при добавлении todo"
    
    keyboard = [
        [InlineKeyboardButton("📝 Мои todos", 
                            callback_data="simple_todo_menu")],
        [InlineKeyboardButton(f"{EMOJIS['back']} Главное меню", 
                            callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, 
                                   parse_mode=ParseMode.MARKDOWN)
    
    # Завершаем ConversationHandler
    return ConversationHandler.END

async def simple_todo_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отмечает простой todo как завершённый"""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    todo_id = int(callback_data.replace("simple_todo_complete_", ""))
    
    success = db.complete_simple_todo(user_id, todo_id)
    
    if success:
        await query.answer(f"✅ Todo завершён!", show_alert=False)
        await simple_todo_menu(update, context)
    else:
        await query.answer(f"{EMOJIS['error']} Ошибка", show_alert=True)

async def simple_todo_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет простой todo"""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    todo_id = int(callback_data.replace("simple_todo_delete_", ""))
    
    success = db.delete_simple_todo(user_id, todo_id)
    
    if success:
        await query.answer(f"🗑️ Todo удалён!", show_alert=False)
        await simple_todo_menu(update, context)
    else:
        await query.answer(f"{EMOJIS['error']} Ошибка", show_alert=True)

async def everyday_reminder_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню ежедневных напоминаний"""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    reminders = db.get_everyday_reminders(user_id)
    
    if not reminders:
        text = f"🔔 *Ежедневные напоминания*\n\n✨ У тебя нет ежедневных напоминаний! Добавь своё первое!"
        keyboard = [
            [InlineKeyboardButton("➕ Добавить напоминание", 
                                callback_data="everyday_reminder_add")],
            [InlineKeyboardButton(f"{EMOJIS['back']} Назад в меню", 
                                callback_data="back_to_main")]
        ]
    else:
        active = sum(1 for r in reminders if r['active'])
        text = f"🔔 *Ежедневные напоминания* ({len(reminders)})\n\n"
        text += f"✅ Активных: {active}/{len(reminders)}\n\n"
        
        for i, reminder in enumerate(reminders, 1):
            status = "🔔" if reminder['active'] else "🔕"
            text += f"{status} {i}. {reminder['task']}\n"
            text += f"   ⏰ {reminder['reminder_time']} ({reminder['timezone']})\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить напоминание", 
                                callback_data="everyday_reminder_add")]
        ]
        
        # Добавляем кнопки для каждого напоминания
        for reminder in reminders:
            status = "🔕" if reminder['active'] else "✅"
            action = "Выключить" if reminder['active'] else "Включить"
            text_button = f"{status} {reminder['task'][:20]}..." if len(reminder['task']) > 20 else f"{status} {reminder['task']}"
            keyboard.append([
                InlineKeyboardButton(text_button, 
                                   callback_data=f"everyday_reminder_delete_{reminder['id']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton(f"{EMOJIS['back']} Назад в меню", 
                                callback_data="back_to_main")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)

async def everyday_reminder_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало добавления ежедневного напоминания"""
    query = update.callback_query
    await query.answer()
    
    text = f"""{EMOJIS['add']} *Добавить ежедневное напоминание*

Шаг 1️⃣ из 3️⃣

Назови своё напоминание. Напиши его описание:

_Пример: "Пить воду"_"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['back']} Отмена", 
                            callback_data="everyday_reminder_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)
    
    return States.WAITING_EVERYDAY_TASK_NAME.value

async def everyday_task_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение названия для ежедневного напоминания"""
    user_id = update.effective_user.id
    task_name = update.message.text
    
    # Сохраняем название в контексте
    context.user_data['everyday_task_name'] = task_name
    
    text = f"""{EMOJIS['add']} *Добавить ежедневное напоминание*

Шаг 2️⃣ из 3️⃣

Спасибо! Теперь укажи свой часовой пояс."""
    
    keyboard = get_timezone_buttons()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, 
                                   parse_mode=ParseMode.MARKDOWN)
    
    return States.WAITING_EVERYDAY_TIMEZONE.value

async def everyday_timezone_button_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик нажатия на кнопку выбора часового пояса для ежедневного напоминания"""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    # Извлекаем название часового пояса
    timezone_str = query.data.replace("tz_", "")
    
    # Сохраняем в контексте
    context.user_data['everyday_timezone'] = timezone_str
    
    text = f"""{EMOJIS['add']} *Добавить ежедневное напоминание*

Шаг 3️⃣ из 3️⃣

Отлично! Твой часовой пояс: *{timezone_str}* ✓

Теперь укажи, когда ты хочешь получать напоминания каждый день?

*Примеры:*
• 09:00 (9 утра)
• 14:30 (2:30 дня)
• 23:59 (11:59 вечера)

{EMOJIS['info']} Напиши время в формате ЧЧ:МММ (24-часовой формат)"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['back']} Отмена", 
                            callback_data="everyday_reminder_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)
    
    return States.WAITING_EVERYDAY_REMINDER_TIME.value

async def everyday_timezone_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение часового пояса для ежедневного напоминания (текстовый вариант)"""
    user_id = update.effective_user.id
    timezone_str = update.message.text.strip()
    
    # Проверяем, валиден ли часовой пояс
    try:
        pytz.timezone(timezone_str)
        context.user_data['everyday_timezone'] = timezone_str
    except pytz.exceptions.UnknownTimeZoneError:
        await update.message.reply_text(
            f"{EMOJIS['error']} *Неправильный часовой пояс!*\n\n"
            f"Пожалуйста, используй корректное название, например:\n"
            f"• Europe/Moscow\n"
            f"• Asia/Baku\n"
            f"• America/New_York",
            parse_mode=ParseMode.MARKDOWN
        )
        return States.WAITING_EVERYDAY_TIMEZONE.value
    
    text = f"""{EMOJIS['add']} *Добавить ежедневное напоминание*

Шаг 3️⃣ из 3️⃣

Отлично! Твой часовой пояс: *{timezone_str}* ✓

Теперь укажи, когда ты хочешь получать напоминания каждый день?

*Примеры:*
• 09:00 (9 утра)
• 14:30 (2:30 дня)
• 23:59 (11:59 вечера)

{EMOJIS['info']} Напиши время в формате ЧЧ:МММ (24-часовой формат)"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['back']} Отмена", 
                            callback_data="everyday_reminder_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, 
                                   parse_mode=ParseMode.MARKDOWN)
    
    return States.WAITING_EVERYDAY_REMINDER_TIME.value

async def everyday_reminder_time_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение времени для ежедневного напоминания"""
    user_id = update.effective_user.id
    reminder_time = update.message.text.strip()
    
    # Валидация времени
    try:
        datetime.strptime(reminder_time, "%H:%M")
    except ValueError:
        await update.message.reply_text(
            f"{EMOJIS['error']} *Неправильный формат времени!*\n\n"
            f"Пожалуйста, используй формат: ЧЧ:МММ\n"
            f"Пример: 09:30 или 14:00",
            parse_mode=ParseMode.MARKDOWN
        )
        return States.WAITING_EVERYDAY_REMINDER_TIME.value
    
    # Получаем данные из контекста
    task_name = context.user_data.get('everyday_task_name')
    timezone = context.user_data.get('everyday_timezone')
    
    # Добавляем ежедневное напоминание в базу данных
    success = db.add_everyday_reminder(user_id, task_name, timezone, reminder_time)
    
    if success:
        # Планируем напоминание
        await schedule_reminder(user_id, task_name, reminder_time, timezone, context.application)
        
        text = f"""{EMOJIS['success']} *Отлично! Ежедневное напоминание добавлено!*

*Напоминание:* {task_name}
*Время:* {reminder_time} каждый день
*Часовой пояс:* {timezone}

{EMOJIS['info']} Ты будешь получать 5 сообщений в это время! ⏰"""
        
        keyboard = [
            [
                InlineKeyboardButton("➕ Добавить ещё", 
                                   callback_data="everyday_reminder_add"),
                InlineKeyboardButton("🔔 Мои напоминания", 
                                   callback_data="everyday_reminder_menu")
            ],
            [
                InlineKeyboardButton(f"{EMOJIS['back']} В меню", 
                                   callback_data="back_to_main")
            ]
        ]
    else:
        text = f"{EMOJIS['error']} *Ошибка при добавлении напоминания!*\n\nПопробуй ещё раз."
        keyboard = [
            [InlineKeyboardButton(f"{EMOJIS['back']} Вернуться", 
                                callback_data="everyday_reminder_menu")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, 
                                   parse_mode=ParseMode.MARKDOWN)
    
    # Очищаем пользовательские данные
    context.user_data.pop('everyday_task_name', None)
    context.user_data.pop('everyday_timezone', None)
    
    return ConversationHandler.END

async def everyday_reminder_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет ежедневное напоминание"""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    reminder_id = int(callback_data.replace("everyday_reminder_delete_", ""))
    
    success = db.delete_everyday_reminder(user_id, reminder_id)
    
    if success:
        await query.answer(f"🗑️ Напоминание удалено!", show_alert=False)
        await everyday_reminder_menu(update, context)
    else:
        await query.answer(f"{EMOJIS['error']} Ошибка", show_alert=True)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возвращение в главное меню"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_name = query.from_user.first_name
    
    text = f"""🤖 *Главное меню*

Привет, {user_name}! {EMOJIS['success']}

Выбери нужное действие:"""
    
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['pending']} Активные задачи", 
                               callback_data="pending_tasks"),
            InlineKeyboardButton(f"{EMOJIS['done']} Завершённые", 
                               callback_data="completed_tasks")
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['add']} Добавить новую задачу", 
                               callback_data="add_task")
        ],
        [
            InlineKeyboardButton("📝 Simple Todo список", 
                               callback_data="simple_todo_menu")
        ],
        [
            InlineKeyboardButton("🔔 Ежедневное напоминание", 
                               callback_data="everyday_reminder_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, 
                                 parse_mode=ParseMode.MARKDOWN)
    
    return ConversationHandler.END

async def complete_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отмечает задачу как завершённую"""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    # Извлекаем ID задачи из callback_data
    callback_data = query.data
    todo_id = int(callback_data.replace("complete_", ""))
    
    # Отмечаем как завершённую
    success = db.complete_todo(user_id, todo_id)
    
    if success:
        await query.answer(f"{EMOJIS['success']} Задача завершена!", show_alert=False)
        # Обновляем список активных задач
        await pending_tasks(update, context)
    else:
        await query.answer(f"{EMOJIS['error']} Ошибка при завершении задачи", show_alert=True)

async def delete_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет задачу"""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    # Извлекаем ID задачи из callback_data
    callback_data = query.data
    todo_id = int(callback_data.replace("delete_", ""))
    
    # Удаляем задачу
    success = db.delete_todo(user_id, todo_id)
    
    if success:
        await query.answer(f"{EMOJIS['delete']} Задача удалена!", show_alert=False)
        # Обновляем список завершённых задач
        await completed_tasks(update, context)
    else:
        await query.answer(f"{EMOJIS['error']} Ошибка при удалении задачи", show_alert=True)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена добавления задачи"""
    query = update.callback_query
    if query:
        await query.answer()
        await back_to_main(update, context)
    return ConversationHandler.END

def main():
    """Запуск бота"""
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Запускаем планировщик напоминаний
    scheduler.start()
    
    # Регистрируем функцию для корректного завершения
    async def stop_scheduler(app):
        scheduler.shutdown()
    
    application.post_stop = stop_scheduler
    
    # Обработчик ConversationHandler для добавления задачи
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_task_start, pattern="^add_task$")
        ],
        states={
            States.WAITING_TASK_NAME.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, task_name_received),
                CallbackQueryHandler(cancel, pattern="^back_to_main$")
            ],
            States.WAITING_TIMEZONE.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, timezone_received),
                CallbackQueryHandler(show_all_timezones, pattern="^show_all_tz$"),
                CallbackQueryHandler(timezone_button_selected, pattern="^tz_"),
                CallbackQueryHandler(cancel, pattern="^back_to_main$")
            ],
            States.WAITING_REMINDER_TIME.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reminder_time_received),
                CallbackQueryHandler(cancel, pattern="^back_to_main$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^back_to_main$"),
            CommandHandler("start", start)
        ],
        per_message=False
    )
    
    # ConversationHandler для добавления simple todo
    simple_todo_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(simple_todo_menu, pattern="^simple_todo_menu$"),
            CallbackQueryHandler(simple_todo_add_start, pattern="^simple_todo_add$")
        ],
        states={
            2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, simple_todo_text_received),
                CallbackQueryHandler(simple_todo_menu, pattern="^simple_todo_menu$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(simple_todo_menu, pattern="^simple_todo_menu$"),
            CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
        ],
        per_message=False
    )
    
    # ConversationHandler для ежедневных напоминаний
    everyday_reminder_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(everyday_reminder_menu, pattern="^everyday_reminder_menu$"),
            CallbackQueryHandler(everyday_reminder_add_start, pattern="^everyday_reminder_add$")
        ],
        states={
            States.WAITING_EVERYDAY_TASK_NAME.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, everyday_task_name_received),
                CallbackQueryHandler(everyday_reminder_menu, pattern="^everyday_reminder_menu$")
            ],
            States.WAITING_EVERYDAY_TIMEZONE.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, everyday_timezone_received),
                CallbackQueryHandler(everyday_timezone_button_selected, pattern="^tz_"),
                CallbackQueryHandler(everyday_reminder_menu, pattern="^everyday_reminder_menu$")
            ],
            States.WAITING_EVERYDAY_REMINDER_TIME.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, everyday_reminder_time_received),
                CallbackQueryHandler(everyday_reminder_menu, pattern="^everyday_reminder_menu$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(everyday_reminder_menu, pattern="^everyday_reminder_menu$"),
            CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
        ],
        per_message=False
    )
    
    # Обработчики команд и кнопок
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(simple_todo_handler)
    application.add_handler(everyday_reminder_handler)
    application.add_handler(CallbackQueryHandler(pending_tasks, pattern="^pending_tasks$"))
    application.add_handler(CallbackQueryHandler(completed_tasks, pattern="^completed_tasks$"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    application.add_handler(CallbackQueryHandler(complete_todo, pattern="^complete_"))
    application.add_handler(CallbackQueryHandler(delete_todo, pattern="^delete_"))
    application.add_handler(CallbackQueryHandler(simple_todo_complete, pattern="^simple_todo_complete_"))
    application.add_handler(CallbackQueryHandler(simple_todo_delete, pattern="^simple_todo_delete_"))
    application.add_handler(CallbackQueryHandler(everyday_reminder_delete, pattern="^everyday_reminder_delete_"))
    
    # Обработчик для неизвестных текстовых сообщений (должен быть последним)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown_message))
    
    # Запуск бота
    logger.info("🤖 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
