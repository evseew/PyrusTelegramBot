#!/usr/bin/env python3
"""
Telegram бот для уведомлений из Pyrus
Этап 5: Регистрация пользователей, админ-команды, реальная отправка
"""
import asyncio
import os
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
import httpx
from dotenv import load_dotenv

# Telegram Bot API
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes,
    filters
)
from telegram.error import TelegramError, RetryAfter, TimedOut

# Наши модули
from .db import db
from .utils import normalize_phone_e164

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
QUEUE_TOP_N = int(os.getenv("QUEUE_TOP_N", "10"))

# Pyrus API
PYRUS_API_URL = os.getenv("PYRUS_API_URL", "https://api.pyrus.com/v4/")
PYRUS_LOGIN = os.getenv("PYRUS_LOGIN")
PYRUS_SECURITY_KEY = os.getenv("PYRUS_SECURITY_KEY")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class PyrusTelegramBot:
    """Основной класс Telegram бота для Pyrus уведомлений"""
    
    def __init__(self):
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN должен быть установлен в .env")
        
        self.application = Application.builder().token(BOT_TOKEN).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков команд"""
        
        # Пользовательские команды
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("whoami", self.cmd_whoami))
        self.application.add_handler(CommandHandler("link", self.cmd_link))
        
        # Админские команды
        self.application.add_handler(CommandHandler("enable_all", self.cmd_enable_all))
        self.application.add_handler(CommandHandler("disable_all", self.cmd_disable_all))
        self.application.add_handler(CommandHandler("users", self.cmd_users))
        self.application.add_handler(CommandHandler("queue", self.cmd_queue))
        
        # Обработка контактов
        self.application.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
        
        # Обработка ошибок
        self.application.add_error_handler(self.error_handler)
    
    # === ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ===
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - регистрация пользователя"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        logger.info(f"Команда /start от пользователя {user.username} (chat_id: {chat_id})")
        
        # Проверяем, зарегистрирован ли уже пользователь
        existing_user = db.get_user_by_telegram_id(chat_id)
        if existing_user:
            await update.message.reply_text(
                f"🎉 Вы уже зарегистрированы!\n\n"
                f"👤 {existing_user.full_name or f'User {existing_user.user_id}'}\n"
                f"🆔 Pyrus ID: {existing_user.user_id}\n"
                f"📱 Телефон: {existing_user.phone or 'не указан'}\n\n"
                f"Используйте /whoami для просмотра информации."
            )
            return
        
        # Просим отправить контакт для регистрации
        contact_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Отправить номер телефона", request_contact=True)]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        
        await update.message.reply_text(
            "👋 Добро пожаловать в бот уведомлений Pyrus!\n\n"
            "Для регистрации нажмите кнопку ниже, чтобы отправить свой номер телефона. "
            "Мы найдём ваш аккаунт в Pyrus и свяжем с этим чатом.\n\n"
            "🔒 Ваш номер используется только для поиска в Pyrus.",
            reply_markup=contact_keyboard
        )
    
    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка полученного контакта"""
        contact = update.message.contact
        chat_id = update.effective_chat.id
        
        logger.info(f"Получен контакт {contact.phone_number} от chat_id {chat_id}")
        
        # Убираем клавиатуру
        await update.message.reply_text(
            "📞 Получен номер телефона, проверяю в Pyrus...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        try:
            # Нормализуем телефон
            normalized_phone = normalize_phone_e164(contact.phone_number)
            if not normalized_phone:
                await update.message.reply_text(
                    "❌ Не удалось обработать номер телефона. Попробуйте ещё раз с /start"
                )
                return
            
            # Ищем пользователя в Pyrus
            pyrus_user = await self._find_user_in_pyrus(normalized_phone)
            if not pyrus_user:
                await update.message.reply_text(
                    f"❌ Пользователь с номером {normalized_phone} не найден в Pyrus.\n\n"
                    f"Убедитесь, что:\n"
                    f"• Номер указан в вашем профиле Pyrus\n"
                    f"• Вы являетесь активным пользователем системы\n\n"
                    f"Или обратитесь к администратору для ручной привязки через /link"
                )
                return
            
            # Сохраняем пользователя в БД
            user_record = db.upsert_user(
                user_id=pyrus_user['id'],
                telegram_id=chat_id,
                phone=normalized_phone,
                full_name=pyrus_user.get('full_name')
            )
            
            # Логируем событие
            db.log_event("user_registered", {
                "user_id": pyrus_user['id'],
                "telegram_id": chat_id,
                "phone": normalized_phone,
                "full_name": pyrus_user.get('full_name')
            })
            
            user_name = pyrus_user.get('full_name') or f"User {pyrus_user['id']}"
            await update.message.reply_text(
                f"✅ Регистрация завершена!\n\n"
                f"👤 {user_name}\n"
                f"🆔 Pyrus ID: {pyrus_user['id']}\n"
                f"📱 Телефон: {normalized_phone}\n\n"
                f"Теперь вы будете получать уведомления о просроченных задачах."
            )
            
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя {chat_id}: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при регистрации. Попробуйте позже или обратитесь к администратору."
            )
    
    async def cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /whoami - информация о текущем пользователе"""
        chat_id = update.effective_chat.id
        
        user = db.get_user_by_telegram_id(chat_id)
        if not user:
            await update.message.reply_text(
                "❌ Вы не зарегистрированы. Используйте /start для регистрации."
            )
            return
        
        await update.message.reply_text(
            f"👤 Информация о вашем аккаунте:\n\n"
            f"🆔 Pyrus ID: {user.user_id}\n"
            f"👨‍💼 Имя: {user.full_name or 'не указано'}\n"
            f"📱 Телефон: {user.phone or 'не указан'}\n"
            f"🗓 Обновлён: {user.updated_at.strftime('%d.%m.%Y %H:%M') if user.updated_at else 'неизвестно'}"
        )
    
    async def cmd_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /link <user_id> - ручная привязка"""
        chat_id = update.effective_chat.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите Pyrus user_id. Пример: /link 12345"
            )
            return
        
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат user_id. Укажите число. Пример: /link 12345"
            )
            return
        
        try:
            # Проверяем, не занят ли уже этот user_id
            existing_user = db.get_user(user_id)
            if existing_user and existing_user.telegram_id != chat_id:
                await update.message.reply_text(
                    f"❌ Pyrus user_id {user_id} уже привязан к другому Telegram аккаунту."
                )
                return
            
            # Сохраняем привязку
            user_record = db.upsert_user(
                user_id=user_id,
                telegram_id=chat_id,
                full_name=f"User {user_id} (manual link)"
            )
            
            # Логируем событие
            db.log_event("user_linked_manual", {
                "user_id": user_id,
                "telegram_id": chat_id
            })
            
            await update.message.reply_text(
                f"✅ Привязка создана!\n\n"
                f"🆔 Pyrus ID: {user_id}\n"
                f"📱 Telegram: {chat_id}\n\n"
                f"Теперь вы будете получать уведомления для этого пользователя."
            )
            
        except Exception as e:
            logger.error(f"Ошибка ручной привязки {user_id} -> {chat_id}: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при создании привязки. Попробуйте позже."
            )
    
    # === АДМИНСКИЕ КОМАНДЫ ===
    
    def _is_admin(self, chat_id: int) -> bool:
        """Проверка прав администратора"""
        return chat_id in ADMIN_IDS
    
    async def cmd_enable_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /enable_all - включить сервис уведомлений"""
        chat_id = update.effective_chat.id
        
        if not self._is_admin(chat_id):
            await update.message.reply_text("❌ Доступно только администраторам.")
            return
        
        try:
            db.settings_set('service_enabled', 'true')
            db.log_event("service_enabled", {"admin_chat_id": chat_id})
            
            await update.message.reply_text(
                "✅ Сервис уведомлений ВКЛЮЧЁН\n\n"
                "📬 Воркер будет отправлять уведомления по расписанию"
            )
            
        except Exception as e:
            logger.error(f"Ошибка включения сервиса админом {chat_id}: {e}")
            await update.message.reply_text("❌ Ошибка при включении сервиса.")
    
    async def cmd_disable_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /disable_all - отключить сервис уведомлений"""
        chat_id = update.effective_chat.id
        
        if not self._is_admin(chat_id):
            await update.message.reply_text("❌ Доступно только администраторам.")
            return
        
        try:
            db.settings_set('service_enabled', 'false')
            db.log_event("service_disabled", {"admin_chat_id": chat_id})
            
            await update.message.reply_text(
                "⏸️ Сервис уведомлений ОТКЛЮЧЁН\n\n"
                "📥 Очередь продолжает наполняться, но сообщения не отправляются"
            )
            
        except Exception as e:
            logger.error(f"Ошибка отключения сервиса админом {chat_id}: {e}")
            await update.message.reply_text("❌ Ошибка при отключении сервиса.")
    
    async def cmd_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /users - список зарегистрированных пользователей"""
        chat_id = update.effective_chat.id
        
        if not self._is_admin(chat_id):
            await update.message.reply_text("❌ Доступно только администраторам.")
            return
        
        try:
            users = db.get_all_users()
            
            if not users:
                await update.message.reply_text("📭 Нет зарегистрированных пользователей")
                return
            
            lines = ["👥 Зарегистрированные пользователи:\n"]
            
            for i, user in enumerate(users, 1):
                lines.append(
                    f"{i}. {user.full_name or f'User {user.user_id}'}\n"
                    f"   🆔 Pyrus: {user.user_id} | TG: {user.telegram_id}\n"
                    f"   📱 {user.phone or 'телефон не указан'}"
                )
            
            message = "\n\n".join(lines)
            
            # Если сообщение слишком длинное, разбиваем
            if len(message) > 4000:
                message = message[:4000] + f"\n\n... и ещё {len(users) - 10} пользователей"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Ошибка получения списка пользователей админом {chat_id}: {e}")
            await update.message.reply_text("❌ Ошибка при получении списка пользователей.")
    
    async def cmd_queue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /queue - топ пользователей с максимальной просрочкой"""
        chat_id = update.effective_chat.id
        
        if not self._is_admin(chat_id):
            await update.message.reply_text("❌ Доступно только администраторам.")
            return
        
        try:
            stats = db.get_queue_stats(QUEUE_TOP_N)
            
            if not stats:
                await update.message.reply_text("📭 Очередь уведомлений пуста")
                return
            
            lines = [f"📊 ТОП-{QUEUE_TOP_N} просрочек:\n"]
            
            for i, stat in enumerate(stats, 1):
                hours = int(stat['max_hours_overdue'])
                lines.append(
                    f"{i}) {stat['full_name']} — макс просрочка: {hours} ч, задач: {stat['task_count']}"
                )
            
            message = "\n".join(lines)
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики очереди админом {chat_id}: {e}")
            await update.message.reply_text("❌ Ошибка при получении статистики очереди.")
    
    # === ИНТЕГРАЦИЯ С PYRUS API ===
    
    async def _find_user_in_pyrus(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Поиск пользователя в Pyrus по номеру телефона
        
        Args:
            phone: Номер телефона в формате E.164
            
        Returns:
            Словарь с данными пользователя или None
        """
        try:
            # Получаем access_token
            access_token = await self._get_pyrus_access_token()
            if not access_token:
                logger.error("Не удалось получить access_token для Pyrus API")
                return None
            
            # Ищем пользователя по телефону
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{PYRUS_API_URL}members",
                    headers=headers,
                    params={"mobile_phone": phone}
                )
                
                if response.status_code != 200:
                    logger.error(f"Ошибка поиска пользователя в Pyrus: {response.status_code} {response.text}")
                    return None
                
                data = response.json()
                members = data.get('members', [])
                
                if not members:
                    logger.info(f"Пользователь с телефоном {phone} не найден в Pyrus")
                    return None
                
                # Возвращаем первого найденного пользователя
                member = members[0]
                return {
                    'id': member['id'],
                    'full_name': f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
                }
                
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя в Pyrus: {e}")
            return None
    
    async def _get_pyrus_access_token(self) -> Optional[str]:
        """
        Получение access_token для Pyrus API
        
        Returns:
            Access token или None в случае ошибки
        """
        if not PYRUS_LOGIN or not PYRUS_SECURITY_KEY:
            logger.error("PYRUS_LOGIN или PYRUS_SECURITY_KEY не установлены")
            return None
        
        try:
            auth_data = {
                "login": PYRUS_LOGIN,
                "security_key": PYRUS_SECURITY_KEY
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{PYRUS_API_URL}auth",
                    json=auth_data
                )
                
                if response.status_code != 200:
                    logger.error(f"Ошибка авторизации в Pyrus: {response.status_code} {response.text}")
                    return None
                
                data = response.json()
                return data.get('access_token')
                
        except Exception as e:
            logger.error(f"Ошибка при получении access_token: {e}")
            return None
    
    # === ОТПРАВКА УВЕДОМЛЕНИЙ ===
    
    async def send_notification(self, telegram_id: int, message: str, retries: int = 3) -> bool:
        """
        Отправка уведомления с обработкой ошибок и ретраями
        
        Args:
            telegram_id: ID чата получателя
            message: Текст сообщения
            retries: Количество попыток
            
        Returns:
            True если сообщение отправлено, False иначе
        """
        for attempt in range(retries):
            try:
                await self.application.bot.send_message(
                    chat_id=telegram_id,
                    text=message,
                    parse_mode='HTML'
                )
                return True
                
            except RetryAfter as e:
                # Rate limiting - ждём указанное время
                wait_time = e.retry_after
                logger.warning(f"Rate limit для {telegram_id}, ждём {wait_time}с")
                await asyncio.sleep(wait_time)
                
            except TimedOut:
                # Таймаут - ждём и пробуем снова
                wait_time = [1, 3, 9][attempt] if attempt < 3 else 9
                logger.warning(f"Таймаут для {telegram_id}, попытка {attempt + 1}/{retries}, ждём {wait_time}с")
                await asyncio.sleep(wait_time)
                
            except TelegramError as e:
                # Другие ошибки Telegram
                logger.error(f"Ошибка Telegram при отправке {telegram_id}: {e}")
                if "chat not found" in str(e).lower() or "blocked" in str(e).lower():
                    # Пользователь заблокировал бота - не ретраим
                    return False
                
                wait_time = [1, 3, 9][attempt] if attempt < 3 else 9
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                # Неожиданные ошибки
                logger.error(f"Неожиданная ошибка при отправке {telegram_id}: {e}")
                wait_time = [1, 3, 9][attempt] if attempt < 3 else 9
                await asyncio.sleep(wait_time)
        
        # Все попытки исчерпаны
        logger.error(f"Не удалось отправить сообщение {telegram_id} после {retries} попыток")
        return False
    
    # === ОБРАБОТКА ОШИБОК ===
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Общий обработчик ошибок"""
        logger.error(f"Ошибка в боте: {context.error}")
        
        # Логируем в БД
        db.log_event("bot_error", {
            "error": str(context.error),
            "update": str(update) if update else None
        })
    
    # === ЗАПУСК ===
    
    async def start_polling(self):
        """Запуск бота в режиме long polling"""
        logger.info("🚀 Запуск Telegram бота...")
        logger.info(f"👥 Админы: {ADMIN_IDS}")
        
        try:
            # Инициализируем бота
            await self.application.initialize()
            await self.application.start()
            
            # Запускаем polling
            await self.application.updater.start_polling()
            
            logger.info("✅ Telegram бот запущен и слушает обновления")
            
            # Держим процесс активным
            await self.application.updater.idle()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {e}")
            raise
        finally:
            await self.application.stop()
    
    def stop(self):
        """Остановка бота"""
        logger.info("🛑 Остановка Telegram бота...")


# Глобальный экземпляр бота
bot = PyrusTelegramBot()


# Функция для запуска из внешних модулей
async def run_bot():
    """Запуск бота"""
    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки")
        bot.stop()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка бота: {e}")
        bot.stop()


# Точка входа
if __name__ == "__main__":
    print("🤖 Запуск Telegram бота для уведомлений Pyrus")
    print("=" * 50)
    asyncio.run(run_bot())
