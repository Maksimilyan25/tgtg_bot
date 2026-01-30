import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)

from telegram_bot.components.config import (
    TELEGRAM_BOT_TOKEN,
    LOGGING_FORMAT,
    LOGGING_LEVEL,
)
from telegram_bot.components.api_client import ApiClient
from telegram_bot.components.handlers import CommandHandlers
from telegram_bot.components.registration_handlers import (
    RegistrationHandlers,
)  # Импортируем RegistrationHandlers
from telegram_bot.components.image_processor import ImageProcessor
from telegram_bot.components.user_data_manager import UserDataManager
from telegram_bot.components.state_manager import StateManager

# Enable logging
logging.basicConfig(format=LOGGING_FORMAT, level=getattr(logging, LOGGING_LEVEL))

# Отключаем логирование HTTP-запросов от httpx и других библиотек
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        # Создаем Application с поддержкой конкурентной обработки
        self.app = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .concurrent_updates(True)  # Включаем конкурентную обработку обновлений
            .build()
        )

        # Initialize components
        self.api_client = ApiClient()
        self.user_data_manager = UserDataManager()
        self.image_processor = ImageProcessor()

        # Инициализируем RegistrationHandlers отдельно
        self.registration_handlers = RegistrationHandlers(
            self.api_client, self.user_data_manager
        )

        # Настраиваем связи между компонентами для поддержки индивидуальных прокси
        self.image_processor.set_registration_handlers(self.registration_handlers)

        # Передаем RegistrationHandlers в CommandHandlers
        self.command_handlers = CommandHandlers(
            self.api_client,
            self.user_data_manager,
            self.registration_handlers,  # Передаем экземпляр
        )

        # Проверяем соединение с прокси-сервером при запуске
        self.health_check_passed = False

        self.setup_handlers()

    def setup_handlers(self):
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.command_handlers.start))

        conv_handler = StateManager.get_conversation_handler(
            entry_points=[CallbackQueryHandler(self.command_handlers.button_callback)],
            states={
                StateManager.SEARCH_DEFECTS: [
                    MessageHandler(
                        filters.PHOTO | filters.Document.ALL,
                        lambda update, context: self.image_processor.handle_defects_image(
                            update, context, self.api_client
                        ),
                    ),
                    CallbackQueryHandler(
                        self.command_handlers.cancel_operation, pattern="^back_to_menu$"
                    ),
                ],
                StateManager.COMPARE_MODEL_1: [
                    MessageHandler(
                        filters.PHOTO | filters.Document.ALL,
                        self._handle_compare_model_1,
                    ),
                    CallbackQueryHandler(
                        self.command_handlers.cancel_operation, pattern="^back_to_menu$"
                    ),
                ],
                StateManager.COMPARE_MODEL_2: [
                    MessageHandler(
                        filters.PHOTO | filters.Document.ALL,
                        self._handle_compare_model_2,
                    ),
                    CallbackQueryHandler(
                        self.command_handlers.cancel_operation, pattern="^back_to_menu$"
                    ),
                ],
                StateManager.CUSTOM_PROMPT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        lambda update, context: self.image_processor.handle_custom_prompt(
                            update, context, self.api_client
                        ),
                    ),
                    CallbackQueryHandler(
                        self.command_handlers.cancel_operation, pattern="^back_to_menu$"
                    ),
                ],
                StateManager.ACCOUNT_MENU: [
                    CallbackQueryHandler(self.command_handlers.button_callback),
                ],
                StateManager.LIST_ACCOUNTS: [
                    CallbackQueryHandler(self.command_handlers.button_callback),
                    # Используем registration_handlers вместо _start_proxy
                    CallbackQueryHandler(
                        self.registration_handlers.start_proxy, pattern="^start_proxy$"
                    ),
                ],
                StateManager.ADD_ACCOUNT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        # Используем registration_handlers
                        self.registration_handlers.handle_add_account_response,
                    ),
                    CallbackQueryHandler(
                        self.command_handlers.button_callback,
                        pattern="^register$",
                    ),
                    CallbackQueryHandler(
                        self.registration_handlers.check_authentication_and_save_account,
                        pattern="^check_auth$",
                    ),
                ],
                StateManager.RELOGIN_ACCOUNT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        # Используем registration_handlers
                        self.registration_handlers.handle_relogin_account_choice,
                    ),
                    CallbackQueryHandler(
                        self.command_handlers.button_callback,
                        pattern="^register$",
                    ),
                    CallbackQueryHandler(
                        self.registration_handlers.handle_relogin_account_response,
                        pattern="^check_auth$",
                    ),
                ],
                StateManager.DELETE_ACCOUNT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        # Используем registration_handlers
                        self.registration_handlers.handle_account_deletion_choice,
                    ),
                    CallbackQueryHandler(
                        self.command_handlers.cancel_operation, pattern="^back_to_menu$"
                    ),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(
                    self.command_handlers.cancel_operation, pattern="^back_to_menu$"
                )
            ],
        )

        self.app.add_handler(conv_handler)

        # Callback query handler for inline buttons
        self.app.add_handler(
            CallbackQueryHandler(self.command_handlers.button_callback)
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.command_handlers.cancel_operation, pattern="^back_to_menu$"
            )
        )

        # Handle any other messages
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.command_handlers.handle_general_text,
            )
        )

    async def _handle_compare_model_1(self, update, context):
        """Wrapper method to handle first comparison image"""
        return await self.image_processor.handle_compare_model_1(
            update, context, self.user_data_manager
        )

    async def _handle_compare_model_2(self, update, context):
        """Wrapper method to handle second comparison image"""
        return await self.image_processor.handle_compare_model_2(
            update, context, self.api_client, self.user_data_manager
        )

    async def check_proxy_connection(self):
        """Проверка соединения с прокси-сервером Qwen - отключена для мультипользовательского режима"""
        # В мультипользовательском режиме прокси-серверы запускаются индивидуально для каждого пользователя
        # и не требуют проверки при старте бота
        self.health_check_passed = None  # None означает, что проверка не выполнялась
        logger.info(
            "Проверка соединения с прокси-сервером отключена для мультипользовательского режима"
        )

    def run(self):
        """Start the bot"""
        logger.info("Запуск бота...")

        if hasattr(self, "health_check_passed") and self.health_check_passed is True:
            logger.info("✅ Бот готов к работе. Прокси-сервер доступен.")
        elif hasattr(self, "health_check_passed") and self.health_check_passed is False:
            logger.warning(
                "⚠️ Бот запущен, но прокси-сервер недоступен. "
                "Некоторые функции могут быть ограничены."
            )
        else:
            logger.info(
                "🚀 Бот запущен в мультипользовательском режиме. "
                "Прокси-серверы будут запускаться индивидуально для каждого пользователя."
            )

        try:
            self.app.run_polling(
                allowed_updates=Update.ALL_TYPES, drop_pending_updates=True
            )
        except Exception as e:
            logger.error(f"Критическая ошибка при запуске polling: {e}", exc_info=True)
            raise
