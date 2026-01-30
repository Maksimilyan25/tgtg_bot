# handlers.py - обновленная версия с улучшенным логированием

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from telegram_bot.components.state_manager import StateManager
from .registration_handlers import RegistrationHandlers

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Основные обработчики команд и кнопок бота"""

    def __init__(self, api_client, user_data_manager, registration_handlers=None):
        self.api_client = api_client
        self.user_data_manager = user_data_manager
        self.registration_handlers = registration_handlers or RegistrationHandlers(
            api_client, user_data_manager
        )

    def _ensure_user_directory(self, user_id: int) -> None:
        """Создает директорию для пользователя при первом запуске"""
        try:
            # Импортируем здесь, чтобы избежать циклического импорта
            from pathlib import Path

            # Путь к директории для пользователя в формате session/accounts/telegram_id/
            user_dir = (
                Path(__file__).parent.parent.parent
                / "session"
                / "accounts"
                / f"telegram_{user_id}"
            )
            user_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Создана директория для пользователя {user_id}: {user_dir}")
        except Exception as e:
            logger.error(
                f"Ошибка при создании директории для пользователя {user_id}: {e}"
            )

    async def start(self, update, context):
        """Отправка приветственного сообщения и главного меню"""
        if update.message is None:
            return

        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        logger.info(f"Received /start command from user {user_id} (@{username})")

        # Создаем директорию для пользователя при первом запуске
        self._ensure_user_directory(user_id)

        # Очищаем состояние пользователя при старте
        if context.user_data:
            logger.debug(f"Очищаем user_data для пользователя {user_id}")
            context.user_data.clear()

        keyboard = [
            [InlineKeyboardButton("🔍 Поиск дефектов", callback_data="search_defects")],
            [
                InlineKeyboardButton(
                    "📋 Сравнение с макетом", callback_data="compare_model"
                )
            ],
            [InlineKeyboardButton("💬 Кастомный промт", callback_data="custom_prompt")],
            [InlineKeyboardButton("📝 Регистрация", callback_data="register")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = (
            "Привет! 👋\n\n"
            "Я бот для анализа изображений. Выберите одну из опций ниже:"
        )

        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def button_callback(self, update, context):
        """Обработка inline кнопок"""
        query = update.callback_query
        if query is None:
            logger.warning("Received callback query with None query object")
            return ConversationHandler.END

        user_id = query.from_user.id
        username = query.from_user.username or "Unknown"

        await query.answer()
        logger.info(
            f"Received callback query '{query.data}' "
            f"from user {user_id} (@{username})"
        )

        # Обработка основных функций бота
        if query.data == "search_defects":
            logger.info(
                f"User {user_id} selected defect search. Setting state to SEARCH_DEFECTS"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 Отмена", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "📸 Загрузите фото для поиска дефектов.", reply_markup=reply_markup
            )
            logger.info(f"Sent defect search prompt to user {user_id}")
            # Возвращаем состояние для ConversationHandler
            return StateManager.SEARCH_DEFECTS

        elif query.data == "compare_model":
            logger.info(
                f"User {user_id} selected model comparison. Setting state to COMPARE_MODEL_1"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 Отмена", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "📸 Загрузите эталонное фото (макет).", reply_markup=reply_markup
            )
            self.user_data_manager.set_compare_state(user_id, "waiting_for_model")
            logger.info(f"Sent model comparison prompt to user {user_id}")
            return StateManager.COMPARE_MODEL_1

        elif query.data == "custom_prompt":
            logger.info(
                f"User {user_id} selected custom prompt. Setting state to CUSTOM_PROMPT"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 Отмена", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "✏️ Введите ваш текстовый запрос.", reply_markup=reply_markup
            )
            logger.info(f"Sent custom prompt prompt to user {user_id}")
            return StateManager.CUSTOM_PROMPT

        # Перенаправляем все регистрационные обработки в RegistrationHandlers
        elif query.data in [
            "register",
            "add_account",
            "list_accounts",
            "relogin_account",
            "delete_account",
            "start_proxy",
            "check_auth",
            "back_to_menu",
        ]:
            logger.info(f"Routing callback '{query.data}' to registration handlers")
            return await self._handle_registration_callbacks(
                update, context, query.data
            )

        # Обработка отмены
        elif query.data == "cancel":
            logger.info(f"User {user_id} cancelled operation")
            return await self.cancel_operation(update, context)

        else:
            logger.warning(f"Unknown callback data: {query.data} from user {user_id}")
            return ConversationHandler.END

    async def _handle_registration_callbacks(self, update, context, callback_data):
        """Маршрутизация регистрационных коллбэков"""
        handlers_map = {
            "register": self.registration_handlers.show_account_menu,
            "add_account": self.registration_handlers.start_add_account_process,
            "list_accounts": self.registration_handlers.show_account_list,
            "relogin_account": self.registration_handlers.start_relogin_account_process,
            "delete_account": self.registration_handlers.show_accounts_for_deletion,
            "start_proxy": self.registration_handlers.start_proxy,
            "check_auth": self.registration_handlers.check_authentication_and_save_account,
            "back_to_menu": self.cancel_operation,
        }

        handler = handlers_map.get(callback_data)
        if handler:
            logger.debug(
                f"Calling handler {handler.__name__ if hasattr(handler, '__name__') else handler}"
            )
            return await handler(update, context)

        logger.warning(f"No handler found for callback_data: {callback_data}")
        return ConversationHandler.END

    async def cancel_operation(self, update, context):
        """Отмена текущей операции и возврат в главное меню"""
        query = update.callback_query
        if query is None:
            logger.warning("Cancel operation called without callback query")
            return ConversationHandler.END

        user_id = query.from_user.id
        username = query.from_user.username or "Unknown"

        await query.answer()
        logger.info(f"Received cancel operation from user {user_id} (@{username})")
        logger.debug(f"Clearing context.user_data: {context.user_data}")

        # Очищаем состояние пользователя
        if context.user_data:
            context.user_data.clear()

        keyboard = [
            [InlineKeyboardButton("🔍 Поиск дефектов", callback_data="search_defects")],
            [
                InlineKeyboardButton(
                    "📋 Сравнение с макетом", callback_data="compare_model"
                )
            ],
            [InlineKeyboardButton("💬 Кастомный промт", callback_data="custom_prompt")],
            [InlineKeyboardButton("📝 Регистрация", callback_data="register")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "Привет! 👋\n\n"
            "Я бот для анализа изображений. Выберите одну из опций ниже:",
            reply_markup=reply_markup,
        )
        logger.info(f"Returned user {user_id} to main menu after cancellation")

        return ConversationHandler.END

    async def handle_general_text(self, update, context):
        """Обработка текстовых сообщений"""
        if update.message is None:
            logger.warning("handle_general_text called without message")
            return

        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        text = update.message.text

        logger.info(
            f"Получено текстовое сообщение от пользователя "
            f"{user_id} (@{username}): {text}"
        )
        logger.debug(f"Context.user_data: {context.user_data}")
        logger.debug(f"Message ID: {update.message.message_id}")

        # Проверяем, относится ли сообщение к регистрационным процессам
        if context.user_data and (
            context.user_data.get("account_ids_for_deletion")
            or context.user_data.get("account_ids_for_relogin")
        ):
            logger.info(
                f"Text input belongs to registration process for user {user_id}"
            )
            # Перенаправляем в регистрационные обработчики
            return await self.registration_handlers.handle_text_input(update, context)

        # Если нет активной беседы, предлагаем начать заново
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск дефектов", callback_data="search_defects")],
            [
                InlineKeyboardButton(
                    "📋 Сравнение с макетом", callback_data="compare_model"
                )
            ],
            [InlineKeyboardButton("💬 Кастомный промт", callback_data="custom_prompt")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Привет! 👋\n\n"
            "Я бот для анализа изображений. Выберите одну из опций ниже:",
            reply_markup=reply_markup,
        )
        logger.info(f"Отправлено главное меню пользователю {user_id}")

        return ConversationHandler.END
