import logging
import aiohttp
import asyncio
from io import BytesIO
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handles image processing operations for the bot"""

    def __init__(self):
        self.registration_handlers = None

    def set_registration_handlers(self, registration_handlers):
        """Устанавливает ссылку на registration_handlers для доступа к информации о прокси"""
        self.registration_handlers = registration_handlers

    async def download_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Download image from the update message"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"

        try:
            logger.info(
                f"Начало загрузки изображения для пользователя {user_id} (@{username})"
            )
            logger.debug(
                f"Тип сообщения: {'photo' if update.message.photo else 'document if document' if update.message.document else 'None'}"
            )

            # Get the image
            photo = None
            if update.message.photo:
                photo = update.message.photo[-1]  # Highest quality
                logger.debug(f"Используем фото: {photo.file_id}")
            elif update.message.document:
                # Check if document is an image
                if (
                    update.message.document.mime_type
                    and "image" in update.message.document.mime_type
                ):
                    photo = update.message.document
                    logger.debug(f"Используем документ-изображение: {photo.file_id}")
                else:
                    logger.warning(
                        f"Документ не является изображением: {update.message.document.mime_type}"
                    )
                    return None
            else:
                logger.error("В сообщении нет ни фото, ни документа")
                return None

            if not photo:
                logger.error("Не удалось определить фото или документ-изображение")
                return None

            logger.debug(f"Идентификатор файла: {photo.file_id}")
            logger.debug(
                f"Размер файла: {photo.file_size if hasattr(photo, 'file_size') else 'N/A'}"
            )

            # Download the image
            file = await context.bot.get_file(photo.file_id)

            # Read image content
            image_bytes = BytesIO()
            await file.download_to_memory(image_bytes)
            image_bytes.seek(0)

            return image_bytes
        except Exception as e:
            logger.error(f"Ошибка при загрузке изображения: {e}", exc_info=True)
            logger.error(f"Тип ошибки: {type(e)}")
            raise

    async def handle_defects_image(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, api_client
    ):
        """Handle image upload for defect detection"""
        user_id = update.effective_user.id

        # Устанавливаем индивидуальный порт прокси для пользователя
        if (
            self.registration_handlers
            and user_id in self.registration_handlers.proxy_processes
        ):
            port = self.registration_handlers.proxy_processes[user_id]["port"]
            api_client.set_proxy_port(port)

        try:
            # Download the image
            logger.info(f"Загрузка изображения для пользователя {user_id}")
            image_bytes = await self.download_image(update, context)
            if image_bytes is None:
                logger.error(
                    f"Не удалось загрузить изображение для пользователя {user_id}"
                )
                await update.message.reply_text(
                    "Не удалось загрузить изображение. Попробуйте отправить другое."
                )
                from telegram.ext import ConversationHandler

                return ConversationHandler.END

            prompt = (
                "Просканируй предмет на изображении и найди на нем дефекты. "
                "Опиши каждый дефект, укажи его расположение и тип."
            )

            # Send waiting message to user
            if update.message:
                waiting_message = await update.message.reply_text(
                    "⏳ Анализ изображения... Пожалуйста, подождите."
                )
            else:
                waiting_message = None

            try:
                # Используем create_task для асинхронной обработки без блокировки
                async def process_image():
                    try:
                        result = await api_client.send_image_analysis(
                            image_bytes, prompt
                        )
                        logger.info(
                            f"Получен результат анализа дефектов для пользователя {user_id}"
                        )

                        if waiting_message:
                            try:
                                await context.bot.edit_message_text(
                                    chat_id=waiting_message.chat_id,
                                    message_id=waiting_message.message_id,
                                    text=f"Результат анализа:\n{result}",
                                )
                                logger.info(
                                    f"Результат анализа отправлен пользователю {user_id}"
                                )
                            except Exception as edit_error:
                                logger.error(
                                    f"Ошибка при редактировании сообщения: {edit_error}"
                                )
                                if update.message:
                                    await update.message.reply_text(
                                        f"Результат анализа:\n{result}"
                                    )
                        else:
                            if update.message:
                                await update.message.reply_text(
                                    f"Результат анализа:\n{result}"
                                )
                                logger.info(
                                    f"Результат анализа отправлен пользователю {user_id}"
                                )

                        # Send back to menu
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "🔙 В главное меню", callback_data="back_to_menu"
                                )
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await update.message.reply_text(
                            "Выберите следующее действие:", reply_markup=reply_markup
                        )
                        logger.info(
                            f"Предложено вернуться в главное меню пользователю {user_id}"
                        )

                    except Exception as analysis_error:
                        logger.error(
                            f"Ошибка при анализе изображения для пользователя {user_id}: "
                            f"{analysis_error}",
                            exc_info=True,
                        )
                        # Обновляем сообщение об ошибке если оно существует
                        if waiting_message:
                            try:
                                await context.bot.edit_message_text(
                                    chat_id=waiting_message.chat_id,
                                    message_id=waiting_message.message_id,
                                    text="❌ Ошибка при анализе изображения. Попробуйте снова.",
                                )
                            except Exception as edit_error:
                                logger.error(
                                    f"Ошибка при редактировании сообщения об ошибке: {edit_error}"
                                )
                                if update.message:
                                    await update.message.reply_text(
                                        "❌ Ошибка при анализе изображения. Попробуйте снова."
                                    )
                        else:
                            if update.message:
                                await update.message.reply_text(
                                    "❌ Ошибка при анализе изображения. Попробуйте снова."
                                )

                # Запускаем обработку в фоновом режиме
                asyncio.create_task(process_image())

            except Exception as task_error:
                logger.error(f"Ошибка при создании задачи: {task_error}")
                if update.message:
                    await update.message.reply_text(
                        "❌ Ошибка при запуске анализа. Попробуйте снова."
                    )

        except aiohttp.ClientError as e:
            logger.error(
                f"Ошибка сети при анализе дефектов для пользователя {user_id}: {e}"
            )
            logger.error(f"Тип ошибки: {type(e)}")
            if update.message:
                await update.message.reply_text(
                    "Произошла ошибка сети при анализе изображения. "
                    "Проверьте соединение с сервером."
                )
        except asyncio.TimeoutError as e:
            logger.error(
                f"Таймаут при анализе дефектов для пользователя {user_id}: {e}"
            )
            if update.message:
                await update.message.reply_text(
                    "Превышено время ожидания ответа от сервера. Попробуйте позже."
                )
        except Exception as e:
            logger.error(
                f"Ошибка при анализе дефектов для пользователя {user_id}: {e}",
                exc_info=True,
            )
            if update.message and not isinstance(
                e, (aiohttp.ClientError, asyncio.TimeoutError)
            ):
                await update.message.reply_text(
                    "Произошла ошибка при анализе изображения. Попробуйте снова."
                )

        from telegram.ext import ConversationHandler

        logger.info(f"Завершение основного потока обработки для пользователя {user_id}")
        return ConversationHandler.END

    async def handle_compare_model_1(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data_manager
    ):
        """Handle first image upload for comparison (model image)"""
        if not update.message:
            logger.error("В обновлении отсутствует объект message")
            return

        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"

        try:
            logger.info(
                f"Starting first comparison image processing for user {user_id} (@{username})"
            )
            # Download the image
            image_bytes = await self.download_image(update, context)

            # Store the model image
            user_data_manager.set_model_image(user_id, image_bytes)
            logger.info(f"Stored model image for user {user_id}")

            # Ask for the second image
            if update.message:
                await update.message.reply_text(
                    "📸 Теперь загрузите фото исследуемого предмета для сравнения.\n\n"
                    "Для отмены нажмите /start"
                )
                logger.info(f"Prompted user {user_id} for second comparison image")

        except Exception as e:
            logger.error(
                f"Error in handling first comparison image for user {user_id}: {e}"
            )
            if update.message:
                await update.message.reply_text(
                    "Произошла ошибка при обработке изображения. Попробуйте снова."
                )
            from telegram.ext import ConversationHandler

            return ConversationHandler.END

        return user_data_manager.COMPARE_MODEL_2

    async def handle_compare_model_2(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        api_client,
        user_data_manager,
    ):
        """Handle second image upload for comparison (item image)"""
        if not update.message:
            logger.error("В обновлении отсутствует объект message")
            return

        user_id = update.effective_user.id

        # Устанавливаем индивидуальный порт прокси для пользователя
        if (
            self.registration_handlers
            and user_id in self.registration_handlers.proxy_processes
        ):
            port = self.registration_handlers.proxy_processes[user_id]["port"]
            api_client.set_proxy_port(port)
        username = update.effective_user.username or "Unknown"

        try:
            logger.info(
                f"Starting second comparison image processing for user {user_id} (@{username})"
            )
            # Download the image
            image_bytes = await self.download_image(update, context)

            # Get stored model image
            model_image = user_data_manager.get_model_image(user_id)
            if not model_image:
                logger.warning(f"No model image found for user {user_id}")
                await update.message.reply_text(
                    "Произошла ошибка. Пожалуйста, начните сначала."
                )
                from telegram.ext import ConversationHandler

                return ConversationHandler.END

            # Send waiting message to user
            waiting_message = await update.message.reply_text(
                "⏳ Сравнение изображений... Пожалуйста, подождите."
            )

            try:
                # Используем create_task для асинхронной обработки без блокировки
                async def process_comparison():
                    try:
                        # Send both images to proxy for comparison
                        logger.info(f"Sending images for comparison for user {user_id}")
                        result = await api_client.send_image_comparison(
                            model_image,
                            image_bytes,
                            "Сравни эти два изображения и укажи все различия между ними.",
                        )
                        logger.info(f"Received comparison result for user {user_id}")

                        # Send result back to user
                        await update.message.reply_text(
                            f"Результат сравнения:\n{result}"
                        )
                        logger.info(f"Sent comparison result to user {user_id}")

                        # Send back to menu
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "🔙 В главное меню", callback_data="back_to_menu"
                                )
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await update.message.reply_text(
                            "Выберите следующее действие:", reply_markup=reply_markup
                        )

                    except Exception as comparison_error:
                        logger.error(
                            f"Error in image comparison for user {user_id}: {comparison_error}"
                        )
                        if update.message:
                            await update.message.reply_text(
                                "Произошла ошибка при сравнении изображений. Попробуйте снова."
                            )

                # Запускаем обработку в фоновом режиме
                asyncio.create_task(process_comparison())

            except Exception as task_error:
                logger.error(f"Ошибка при создании задачи сравнения: {task_error}")
                if update.message:
                    await update.message.reply_text(
                        "❌ Ошибка при запуске сравнения. Попробуйте снова."
                    )

        except Exception as e:
            logger.error(f"Error in image comparison setup for user {user_id}: {e}")
            if update.message:
                await update.message.reply_text(
                    "Произошла ошибка при подготовке сравнения изображений. Попробуйте снова."
                )

        # Clean up stored data
        user_data_manager.clear_model_image(user_id)

        from telegram.ext import ConversationHandler

        return ConversationHandler.END

    async def handle_custom_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, api_client
    ):
        """Handle custom text prompt"""
        if not update.message or not update.message.text:
            logger.error("В обновлении отсутствует текстовое сообщение")
            return

        user_id = update.effective_user.id

        # Устанавливаем индивидуальный порт прокси для пользователя
        if (
            self.registration_handlers
            and user_id in self.registration_handlers.proxy_processes
        ):
            port = self.registration_handlers.proxy_processes[user_id]["port"]
            api_client.set_proxy_port(port)
        username = update.effective_user.username or "Unknown"
        prompt = update.message.text

        logger.info(
            f"Received custom prompt from user {user_id} (@{username}): {prompt}"
        )

        # Send waiting message
        if update.message:
            waiting_message = await update.message.reply_text("⏳ Ожидайте ответ...")
        else:
            waiting_message = None

        try:
            # Используем create_task для асинхронной обработки без блокировки
            async def process_prompt():
                try:
                    # Send prompt to proxy
                    logger.info(f"Sending custom prompt to API for user {user_id}")
                    result = await api_client.send_text_analysis(prompt)
                    logger.info(f"Received custom prompt result for user {user_id}")

                    # Edit the waiting message with the result
                    await context.bot.edit_message_text(
                        chat_id=waiting_message.chat_id,
                        message_id=waiting_message.message_id,
                        text=f"Результат:\n{result}",
                    )
                    logger.info(f"Sent custom prompt result to user {user_id}")

                    # Send back to menu
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "🔙 В главное меню", callback_data="back_to_menu"
                            )
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text(
                        "Выберите следующее действие:", reply_markup=reply_markup
                    )

                except Exception as e:
                    logger.error(f"Error in custom prompt for user {user_id}: {e}")
                    # Edit the waiting message with error if it exists
                    if waiting_message:
                        try:
                            await context.bot.edit_message_text(
                                chat_id=waiting_message.chat_id,
                                message_id=waiting_message.message_id,
                                text="Произошла ошибка при обработке запроса. Попробуйте снова.",
                            )
                        except Exception as edit_error:
                            logger.error(
                                f"Ошибка при редактировании сообщения: {edit_error}"
                            )
                            if update.message:
                                await update.message.reply_text(
                                    "Произошла ошибка при обработке запроса. Попробуйте снова."
                                )

            # Запускаем обработку в фоновом режиме
            asyncio.create_task(process_prompt())

        except Exception as task_error:
            logger.error(
                f"Ошибка при создании задачи для кастомного промта: {task_error}"
            )
            if update.message:
                await update.message.reply_text(
                    "❌ Ошибка при запуске обработки запроса. Попробуйте снова."
                )

        from telegram.ext import ConversationHandler

        return ConversationHandler.END
