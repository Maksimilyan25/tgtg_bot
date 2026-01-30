"""
Модуль для обработки регистрации и управления аккаунтами в Telegram-боте.

Содержит все обработчики, связанные с:
- Добавлением аккаунтов
- Просмотром списка аккаунтов
- Перелогинированием аккаунтов
- Удаление аккаунтов
- Запуском прокси
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from .browser_manager import BrowserManager
from .config import (
    ACCOUNT_MENU,
    ADD_ACCOUNT,
    DELETE_ACCOUNT,
    RELOGIN_ACCOUNT,
)

logger = logging.getLogger(__name__)


class RegistrationHandlers:
    """Обработчики для регистрации и управления аккаунтами"""

    def __init__(self, api_client, user_data_manager, browser_manager=None):
        self.api_client = api_client
        self.user_data_manager = user_data_manager
        self.browser_manager = browser_manager or BrowserManager()
        self.proxy_processes = {}  # user_id -> {'process': process, 'port': port}
        self.proxy_ports_in_use = set()
        self.base_port = 3260  # Базовый порт для распределения

    async def show_account_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Показывает меню управления аккаунтами"""
        query = update.callback_query
        if query is None:
            return ConversationHandler.END

        user_id = query.from_user.id
        username = query.from_user.username or "Unknown"

        await query.answer()
        logger.info(
            f"Received callback query 'register' from user {user_id} (@{username})"
        )

        keyboard = [
            [InlineKeyboardButton("📝 Добавить аккаунт", callback_data="add_account")],
            [
                InlineKeyboardButton(
                    "📋 Список аккаунтов", callback_data="list_accounts"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Перелогинить аккаунт", callback_data="relogin_account"
                )
            ],
            [InlineKeyboardButton("️ Удалить аккаунт", callback_data="delete_account")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🔐 Меню управления аккаунтами Qwen:\n\nВыберите действие:",
            reply_markup=reply_markup,
        )
        logger.info(f"Sent account management menu to user {user_id}")
        return ACCOUNT_MENU

    async def _run_node_script(
        self, script_name: str, args: Optional[List[str]] = None
    ) -> Optional[dict]:
        """Запускает Node.js скрипт и возвращает результат в виде словаря"""
        if args is None:
            args = []

        try:
            result = subprocess.run(
                ["node", f"scripts/{script_name}.js"] + args,
                capture_output=True,
                text=True,
                cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
            )
            if result.returncode != 0:
                logger.error(f"Ошибка при выполнении {script_name}.js: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "output": result.stdout.strip(),
                }

            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                # Если вывод не в формате JSON, возвращаем как текст
                return {
                    "success": True,
                    "output": result.stdout.strip(),
                    "raw_output": result.stdout.strip(),
                }
        except Exception as e:
            logger.error(f"Исключение при выполнении {script_name}.js: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _load_tokens_for_user(telegram_user_id: int) -> Optional[dict]:
        """Загружает токен для конкретного пользователя Telegram из его индивидуальной директории"""
        try:
            base_path = Path(__file__).parent.parent.parent
            telegram_account_dir = (
                base_path / "session" / "accounts" / f"telegram_{telegram_user_id}"
            )

            if not telegram_account_dir.exists():
                logger.warning(
                    f"Директория для пользователя Telegram {telegram_user_id} не найдена"
                )
                return None

            token_file = telegram_account_dir / "token.txt"
            info_file = telegram_account_dir / "account_info.json"

            if not token_file.exists():
                logger.warning(
                    f"Файл токена для пользователя Telegram {telegram_user_id} не найден"
                )
                return None

            # Загружаем токен
            with open(token_file, "r", encoding="utf-8") as tf:
                token = tf.read().strip()

            # Загружаем дополнительную информацию
            account_info = {}
            if info_file.exists():
                with open(info_file, "r", encoding="utf-8") as f:
                    account_info = json.load(f)

            return {
                "id": f"telegram_{telegram_user_id}",
                "token": token,
                "current_token": token,
                "telegram_user_id": telegram_user_id,
                **account_info,
            }
        except Exception as e:
            logger.error(
                f"Ошибка при загрузке токена для пользователя {telegram_user_id}: {e}"
            )
            return None

    @staticmethod
    def _load_tokens_from_json() -> list:
        """Загружает токены из tokens.json и возвращает список аккаунтов. Статический метод для использования другим модулями
        Используется для совместимости с Node.js частью и для общего списка аккаунтов"""
        try:
            tokens_path = (
                Path(__file__).parent.parent.parent / "session" / "tokens.json"
            )
            if not tokens_path.exists():
                return []

            with open(tokens_path, "r", encoding="utf-8") as f:
                tokens = json.load(f)

            # Загружаем дополнительную информацию из файлов аккаунтов
            base_path = Path(__file__).parent.parent.parent
            accounts_path = base_path / "session" / "accounts"
            for token in tokens:
                account_dir = accounts_path / token["id"]
                if account_dir.exists():
                    token_file = account_dir / "token.txt"
                    if token_file.exists():
                        with open(token_file, "r", encoding="utf-8") as tf:
                            token["current_token"] = tf.read().strip()

            return tokens
        except Exception as e:
            logger.error(f"Ошибка при загрузке токенов: {e}")
            return []

    @staticmethod
    def _format_status(token) -> str:
        """Форматирует статус токена. Статический метод для использования другим модулями"""
        if token.get("invalid"):
            return "❌ Недействителен"

        if token.get("resetAt"):
            reset_time = datetime.fromisoformat(token["resetAt"]).timestamp() * 1000
            if reset_time > time.time() * 1000:
                return "⏳ Ожидание сброса"

        return "✅ OK"

    def _get_available_port(self) -> int:
        """Находит и возвращает доступный порт для прокси-сервера"""
        port = self.base_port
        while port < self.base_port + 100:  # Ищем в диапазоне 100 портов
            if port not in self.proxy_ports_in_use and not self._check_port_available(
                port
            ):
                return port
            port += 1
        return 3264  # Возвращаем порт по умолчанию, если не нашли доступный

    def _start_proxy_server(self, user_id: int) -> bool:
        """Запускает прокси-сервер в фоновом режиме для конкретного пользователя"""
        try:
            logger.info(f"Запуск прокси-сервера для пользователя {user_id}...")

            # Определяем путь к index.js
            base_dir = Path(__file__).parent.parent.parent
            index_js_path = base_dir / "index.js"

            if not index_js_path.exists():
                logger.error(f"Файл index.js не найден: {index_js_path}")
                return False

            # Находим доступный порт для пользователя
            port = self._get_available_port()
            logger.info(f"Используем порт {port} для пользователя {user_id}")

            # Создаем процесс с переменной окружения для неинтерактивного режима
            env = os.environ.copy()
            env["NON_INTERACTIVE"] = "true"
            env["PORT"] = str(port)  # Устанавливаем порт для сервера

            # Запускаем процесс без stdin, если не требуется интерактивный ввод
            process = subprocess.Popen(
                ["node", str(index_js_path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=str(base_dir),
                encoding="utf-8",
                env=env,
            )

            # Запускаем поток для логирования stdout и stderr
            def log_output(stream, stream_name):
                try:
                    for line in stream:
                        if line.strip():
                            logger.info(
                                f"Proxy {user_id} {stream_name}: {line.strip()}"
                            )
                except Exception as e:
                    logger.error(
                        f"Ошибка при чтении {stream_name} для пользователя {user_id}: {e}"
                    )

            import threading

            stdout_thread = threading.Thread(
                target=log_output,
                args=(process.stdout, "stdout"),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=log_output,
                args=(process.stderr, "stderr"),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()

            # Сохраняем информацию о процессе
            self.proxy_processes[user_id] = {
                "process": process,
                "port": port,
                "stdout_thread": stdout_thread,
                "stderr_thread": stderr_thread,
            }
            self.proxy_ports_in_use.add(port)

            # Ждем запуска сервера (таймаут 30 секунд)
            start_time = time.time()
            while time.time() - start_time < 30:
                # Проверяем, запустился ли сервер
                if self._check_port_available(port):
                    logger.info(
                        f"Прокси-сервер успешно запущен на порту {port} для пользователя {user_id}"
                    )
                    return True

                # Проверяем, не завершился ли процесс с ошибкой
                if process.poll() is not None:
                    logger.error(
                        f"Прокси-сервер для пользователя {user_id} завершился с кодом: {process.poll()}"
                    )
                    stdout, stderr = process.communicate()
                    logger.error(f"Proxy {user_id} stdout:\n{stdout}")
                    logger.error(f"Proxy {user_id} stderr:\n{stderr}")
                    self._stop_proxy_server_for_user(user_id)
                    return False

                time.sleep(1)

            logger.error(
                f"Таймаут при запуске прокси-сервера для пользователя {user_id}"
            )
            self._stop_proxy_server_for_user(user_id)
            return False

        except Exception as e:
            logger.error(
                f"Ошибка при запуске прокси-сервера для пользователя {user_id}: {e}",
                exc_info=True,
            )
            self._stop_proxy_server_for_user(user_id)
            return False

    def _check_port_available(self, port: int) -> bool:
        """Проверяет, доступен ли порт"""
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            logger.debug(f"Проверка порта {port}: результат connect_ex = {result}")
            return result == 0
        except Exception as e:
            logger.error(f"Ошибка при проверке порта {port}: {e}")
            return False

    def _stop_proxy_server_for_user(self, user_id: int):
        """Останавливает прокси-сервер для конкретного пользователя"""
        if user_id in self.proxy_processes:
            process_info = self.proxy_processes[user_id]
            logger.info(f"Остановка прокси-сервера для пользователя {user_id}...")
            try:
                if process_info["process"].poll() is None:
                    process_info["process"].terminate()
                    try:
                        process_info["process"].wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process_info["process"].kill()
            except Exception as e:
                logger.error(
                    f"Ошибка при остановке прокси-сервера для пользователя {user_id}: {e}"
                )

            # Удаляем порт из множества используемых
            if user_id in self.proxy_processes:
                port = self.proxy_processes[user_id]["port"]
                self.proxy_ports_in_use.discard(port)
                del self.proxy_processes[user_id]
            logger.info(f"Прокси-сервер для пользователя {user_id} остановлен")

    def _stop_proxy_server(self):
        """Останавливает все прокси-серверы (для обратной совместимости)"""
        logger.info("Остановка всех прокси-серверов...")
        for user_id in list(self.proxy_processes.keys()):
            self._stop_proxy_server_for_user(user_id)
        self.proxy_processes = {}
        self.proxy_ports_in_use = set()

    async def _get_proxy_status_for_user(self, user_id: int) -> bool:
        """Проверяет статус прокси-сервера для конкретного пользователя"""
        if user_id not in self.proxy_processes:
            return False

        port = self.proxy_processes[user_id]["port"]
        return self._check_port_available(port)

    async def _check_proxy_health_for_user(self, user_id: int) -> bool:
        """Проверяет доступность прокси-сервера для конкретного пользователя"""
        try:
            if user_id not in self.proxy_processes:
                logger.warning(f"Прокси-сервер для пользователя {user_id} не найден")
                return False

            port = self.proxy_processes[user_id]["port"]
            logger.info(
                f"Проверка health check прокси-сервера для пользователя {user_id} на порту {port}..."
            )

            # Увеличиваем время ожидания перед проверкой health check
            await asyncio.sleep(10)  # Дополнительное время на инициализацию сервера

            # Сначала проверяем доступность порта
            if not self._check_port_available(port):
                logger.warning(f"Порт {port} недоступен для пользователя {user_id}")
                return False

            # Проверяем health check endpoint
            import aiohttp

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"http://localhost:{port}/api/status",
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 200:
                            health_data = await response.json()
                            logger.info(
                                f"Health check для пользователя {user_id} пройден успешно"
                            )
                            return True
                        else:
                            logger.warning(
                                f"Health check для пользователя {user_id} вернул статус {response.status}"
                            )
                            return False
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Таймаут при проверке health check для пользователя {user_id} (увеличено до 30 секунд)"
                    )
                    return False
                except Exception as e:
                    logger.warning(
                        f"Ошибка при проверке health check для пользователя {user_id}: {str(e)}"
                    )
                    return False

        except Exception as e:
            logger.error(
                f"Ошибка при проверке доступности прокси для пользователя {user_id}: {e}"
            )
            return False

    async def start_proxy(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Запускает прокси-сервер Qwen API с использованием токена текущего пользователя"""
        query = update.callback_query
        if query is None:
            logger.warning("Получен пустой callback_query в start_proxy")
            return

        telegram_user_id = query.from_user.id
        username = query.from_user.username or "Unknown"
        logger.info(f"Запуск прокси для пользователя {telegram_user_id} (@{username})")

        try:
            await query.edit_message_text(
                "🚀 Запуск прокси-сервера Qwen API...\n"
                "Пожалуйста, подождите, это может занять до 30 секунд."
            )
        except Exception as edit_error:
            logger.error(f"Ошибка при редактировании сообщения: {edit_error}")
            return

        try:
            # Загружаем токен для текущего пользователя Telegram
            user_token = self._load_tokens_for_user(telegram_user_id)

            if not user_token:
                logger.warning(f"Не найден токен для пользователя {telegram_user_id}")
                await query.edit_message_text(
                    "❌ У вас нет сохраненного аккаунта для запуска прокси.\n"
                    "Пожалуйста, добавьте аккаунт сначала.",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                    ),
                )
                return

            # Проверяем статус токена
            token_status = self._format_status(user_token)
            if token_status != "✅ OK":
                logger.warning(
                    f"Токен пользователя {telegram_user_id} не активен: {token_status}"
                )
                await query.edit_message_text(
                    f"❌ Ваш токен не активен ({token_status}).\n"
                    "Попробуйте перелогиниться или добавьте новый аккаунт.",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                    ),
                )
                return

            # Проверяем, не запущен ли уже прокси-сервер для этого пользователя
            if await self._get_proxy_status_for_user(telegram_user_id):
                port = self.proxy_processes[telegram_user_id]["port"]
                logger.info(
                    f"Прокси-сервер уже запущен для пользователя {telegram_user_id} на порту {port}"
                )
                await query.edit_message_text(
                    f"✅ Прокси-сервер уже запущен и доступен!\n"
                    f"Сервер доступен по адресу: http://localhost:{port}\n\n"
                    "Соединение с Qwen API установлено.",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "🔙 Назад к аккаунтам", callback_data="register"
                                ),
                                InlineKeyboardButton(
                                    "🏠 Главное меню", callback_data="back_to_menu"
                                ),
                            ]
                        ]
                    ),
                )
                return

            # Запускаем прокси-сервер в отдельном потоке
            await query.edit_message_text(
                "⏳ Запускаю прокси-сервер...\n" "Это может занять несколько секунд."
            )

            # Обновляем tokens.json с токеном текущего пользователя
            # для совместимости с Node.js частью
            self._update_tokens_json_for_user(user_token)

            # Запускаем прокси-сервер для конкретного пользователя
            proxy_started = await asyncio.to_thread(
                self._start_proxy_server, telegram_user_id
            )

            if proxy_started:
                logger.info(
                    f"Прокси-сервер успешно запущен для пользователя {telegram_user_id}"
                )

                # Даем серверу время на полную инициализацию
                await asyncio.sleep(3)

                # Проверяем health check для конкретного пользователя
                health_ok = await self._check_proxy_health_for_user(telegram_user_id)

                if health_ok:
                    port = self.proxy_processes[telegram_user_id]["port"]
                    await query.edit_message_text(
                        "✅ Прокси-сервер Qwen API успешно запущен!\n"
                        "Теперь вы можете использовать функции анализа изображений.",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        "🔙 Назад к аккаунтам", callback_data="register"
                                    ),
                                    InlineKeyboardButton(
                                        "🏠 Главное меню", callback_data="back_to_menu"
                                    ),
                                ]
                            ]
                        ),
                    )
                else:
                    await query.edit_message_text(
                        "⚠️ Прокси-сервер запущен, но health check не пройден.\n"
                        "Попробуйте перезапустить прокси или проверьте логи.",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        "🔙 Назад", callback_data="register"
                                    )
                                ]
                            ]
                        ),
                    )
            else:
                logger.error(
                    f"Не удалось запустить прокси-сервер для пользователя {telegram_user_id}"
                )
                await query.edit_message_text(
                    "❌ Не удалось запустить прокси-сервер.\n"
                    "Убедитесь, что:\n"
                    "1. Node.js установлен и доступен\n"
                    "2. Нет конфликтов портов",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                    ),
                )

        except Exception as e:
            logger.error(f"Критическая ошибка при запуске прокси: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Ошибка при запуске прокси. Попробуйте позже.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                ),
            )

    def _update_tokens_json_for_user(self, user_token: dict) -> bool:
        """Обновляет tokens.json для использования токена текущего пользователя"""
        try:
            tokens_path = (
                Path(__file__).parent.parent.parent / "session" / "tokens.json"
            )

            # Создаем список с единственным токеном пользователя
            tokens = [
                {
                    "id": user_token["id"],
                    "token": user_token["current_token"],
                    "invalid": False,
                    "resetAt": None,
                }
            ]

            # Сохраняем обновленный список
            with open(tokens_path, "w", encoding="utf-8") as f:
                json.dump(tokens, f, indent=2, ensure_ascii=False)

            logger.info(
                f"Файл tokens.json обновлен для пользователя {user_token['telegram_user_id']}"
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении tokens.json для пользователя: {e}")
            return False

    async def _check_proxy_health(self) -> bool:
        """Проверяет доступность прокси-сервера Qwen API с помощью health check"""
        try:
            logger.info("Проверка health check прокси-сервера...")

            # Увеличиваем время ожидания перед проверкой health check
            await asyncio.sleep(10)  # Дополнительное время на инициализацию сервера

            # Сначала проверяем доступность порта
            if not self._check_port_available(3264):
                logger.warning("Порт 3264 недоступен")
                return False

            # Проверяем health check endpoint
            import aiohttp

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        "http://localhost:3264/api/status",
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 200:
                            health_data = await response.json()
                            logger.info("Health check пройден успешно")
                            return True
                        else:
                            logger.warning(
                                f"Health check вернул статус {response.status}"
                            )
                            return False
                except asyncio.TimeoutError:
                    logger.warning(
                        "Таймаут при проверке health check (увеличено до 30 секунд)"
                    )
                    return False
                except Exception as e:
                    logger.warning(f"Ошибка при проверке health check: {str(e)}")
                    return False

        except Exception as e:
            logger.error(f"Ошибка при проверке доступности прокси: {e}")
            return False

    async def show_account_list(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Показывает список аккаунтов пользователю - только его собственный аккаунт"""
        query = update.callback_query
        if query is None:
            return

        telegram_user_id = query.from_user.id
        logger.info(f"Показываем список аккаунтов для пользователя {telegram_user_id}")

        # Загружаем ТОЛЬКО токен текущего пользователя
        user_token = self._load_tokens_for_user(telegram_user_id)

        if not user_token:
            await query.edit_message_text(
                "Список аккаунтов: (пусто)",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                ),
            )
            return

        # Формируем список аккаунтов (только один - собственный)
        account_lines = []
        status = self._format_status(user_token)
        account_lines.append(f"1 | {user_token['id']} | {status}")

        # Подсчитываем активные аккаунты (всегда 1 или 0)
        active_count = 1 if status == "✅ OK" else 0
        total_count = 1

        account_text = (
            "📋 Список аккаунтов:\n\n"
            f"Активных аккаунтов: {active_count} из {total_count}\n\n"
            + "\n".join(account_lines)
        )

        # Проверяем, запущен ли прокси-сервер для этого пользователя
        proxy_status = "❌ Не запущен"
        port_info = ""
        if await self._get_proxy_status_for_user(telegram_user_id):
            port = self.proxy_processes[telegram_user_id]["port"]
            proxy_status = "✅ Запущен"
            port_info = f" на порту {port}"

        keyboard = [
            [
                InlineKeyboardButton(
                    f"🚀 Подключить прокси ({proxy_status}){port_info}",
                    callback_data="start_proxy",
                )
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="register")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(account_text, reply_markup=reply_markup)

    async def show_accounts_for_deletion(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Показывает список аккаунтов для удаления (включая собственный аккаунт пользователя)"""
        query = update.callback_query
        if query is None:
            return

        telegram_user_id = query.from_user.id
        logger.info(
            f"Показываем список аккаунтов для удаления пользователю {telegram_user_id}"
        )

        # Загружаем токен текущего пользователя
        user_token = self._load_tokens_for_user(telegram_user_id)
        account_lines = []
        account_ids = []

        # Всегда добавляем собственный аккаунт пользователя
        if user_token:
            status = self._format_status(user_token)
            account_lines.append(f"1 | {user_token['id']} | {status}")
            account_ids.append(user_token["id"])

        # Пробуем получить список аккаунтов из Node.js скрипта (для обратной совместимости)
        accounts_result = await self._run_node_script("auth", ["--list", "--json"])
        if accounts_result and accounts_result.get("success", True):
            if isinstance(accounts_result.get("accounts"), list):
                for account in accounts_result["accounts"]:
                    if account["id"] != user_token["id"]:  # Избегаем дублирования
                        account_lines.append(
                            f"{len(account_lines) + 1} | {account['id']} | "
                            f"{account.get('status', '✅ OK')}"
                        )
                        account_ids.append(account["id"])
            elif isinstance(accounts_result.get("output"), str):
                accounts_output = accounts_result["output"]
                for line in accounts_output.split("\n"):
                    if "|" in line and not line.startswith("Список аккаунтов:"):
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 2 and parts[1] != user_token["id"]:
                            account_id = parts[1]
                            account_lines.append(line.strip())
                            account_ids.append(account_id)

        if not account_lines:
            await query.edit_message_text(
                "Нет доступных аккаунтов для удаления.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                ),
            )
            return

        if context.user_data is not None:
            context.user_data["account_ids_for_deletion"] = account_ids

        account_text = (
            "Выберите аккаунт для удаления:\n\n"
            + "\n".join([f"{i+1}. {line}" for i, line in enumerate(account_lines)])
            + "\n\nВведите номер аккаунта для удаления:"
        )

        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="register")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(account_text, reply_markup=reply_markup)

    async def start_add_account_process(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Запускает процесс добавления аккаунта через браузер"""
        query = update.callback_query
        if query is None:
            return ConversationHandler.END

        await query.edit_message_text(
            "🔄 Запускается процесс добавления аккаунта...\n"
            "Браузер откроется для авторизации. После завершения "
            "авторизации вернитесь в Telegram и нажмите кнопку ниже.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✅ Готово", callback_data="check_auth")]]
            ),
        )

        # Инициализируем браузер и начинаем процесс авторизации
        try:
            success = await self.browser_manager.initialize(visible=True)
            if not success:
                raise Exception("Не удалось инициализировать браузер")

            auth_success = await self.browser_manager.start_authentication()
            if not auth_success:
                raise Exception("Не удалось начать процесс авторизации")

            logger.info("Браузер открыт для авторизации")

            # Сохраняем информацию о процессе в user_data
            if context.user_data is not None:
                context.user_data["browser_process"] = {
                    "type": "add_account",
                    "manager": self.browser_manager,
                }

        except Exception as e:
            logger.error(f"Ошибка при запуске браузера: {e}")
            await self.browser_manager.close()
            await query.edit_message_text(
                "❌ Не удалось запустить браузер. Попробуйте позже.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                ),
            )
            return ConversationHandler.END

        return ADD_ACCOUNT

    async def handle_add_account_response(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Обработка нажатия 'Готово' после запуска авторизации"""
        query = update.callback_query
        if query is None:
            return ADD_ACCOUNT
        try:
            await query.answer()

            # Отправляем сообщение с кнопкой "Готово" для проверки авторизации
            await query.edit_message_text(
                "🔄 Браузер должен был открыться для авторизации.\n"
                "После завершения авторизации нажмите кнопку ниже.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("✅ Готово", callback_data="check_auth")]]
                ),
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке callback query: {e}")
            # Пробуем отправить просто текстовое сообщение в случае ошибки
            if query.message:
                await query.message.reply_text(
                    "🔄 Браузер открыт для авторизации. Вернитесь в бот "
                    "и нажмите /start для проверки статуса."
                )
            else:
                logger.error("Не удалось отправить сообщение: query.message is None")
        return ADD_ACCOUNT

    async def check_authentication_and_save_account(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Проверка завершения авторизации и сохранение аккаунта"""
        query = update.callback_query
        if query is None:
            return ConversationHandler.END

        # Проверяем, есть ли активный процесс браузера
        if context.user_data is None or "browser_process" not in context.user_data:
            await query.edit_message_text(
                "❌ Сессия авторизации не найдена. Начните процесс заново.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                ),
            )
            return ConversationHandler.END

        browser_data = context.user_data["browser_process"]
        browser_manager = browser_data["manager"]

        # Определяем тип операции
        is_relogin = browser_data.get("type") == "relogin_account"
        account_id = browser_data.get("account_id") if is_relogin else None

        try:
            # Показываем процесс проверки
            await query.edit_message_text(
                "⏳ Проверка завершения авторизации...\n"
                "Подождите, идет проверка статуса авторизации."
            )

            logger.info("Пользователь подтвердил завершение авторизации. Подождите...")

            # Проверяем, завершена ли авторизация
            is_authenticated = await browser_manager.wait_for_auth_completion(
                timeout=60
            )

            if is_authenticated:
                logger.info("Авторизация подтверждена.")

                if is_relogin and account_id:
                    # Сохраняем обновленный токен для существующего аккаунта
                    success = await browser_manager.save_account(
                        account_id, is_relogin=True
                    )
                else:
                    # Получаем telegram_id пользователя, который сделал запрос
                    user_id = query.from_user.id
                    # Создаем ID аккаунта на основе telegram_id
                    account_id = f"telegram_{user_id}"

                    # Дополнительная проверка токена перед сохранением
                    if not browser_manager.auth_token:
                        raise Exception("Токен не был получен")

                    # Сохраняем аккаунт в директорию пользователя
                    success = await browser_manager.save_account(
                        account_id, telegram_user_id=user_id
                    )

                    if success:
                        await browser_manager.close()
                        if context.user_data is not None:
                            del context.user_data["browser_process"]

                        # Подсчитываем количество аккаунтов
                        base_path = Path(__file__).parent.parent.parent
                        accounts_path = base_path / "session" / "accounts"
                        account_count = len(list(accounts_path.glob("*")))

                        logger.info("Сессия сохранена")
                        logger.info("Токен авторизации успешно извлечен")
                        logger.info("Токен авторизации сохранен")
                        logger.info("Сессия сохранена успешно!")
                        logger.info(
                            f"Аккаунт '{account_id}' добавлен. "
                            f"Всего аккаунтов: {account_count}"
                        )
                        logger.info("Браузер закрыт")

                        await query.edit_message_text(
                            f"✅ Авторизация выполнена успешно!\n"
                            f"Аккаунт '{account_id}' добавлен. "
                            f"Всего аккаунтов: {account_count}\n"
                            f"Токен успешно извлечен и сохранен",
                            reply_markup=InlineKeyboardMarkup(
                                [
                                    [
                                        InlineKeyboardButton(
                                            "🔙 Назад к аккаунтам",
                                            callback_data="register",
                                        )
                                    ]
                                ]
                            ),
                        )
                    else:
                        raise Exception("Не удалось сохранить аккаунт")
            else:
                raise Exception("Авторизация не завершена")

        except Exception as e:
            logger.error(f"Ошибка при завершении авторизации: {e}")
            await browser_manager.close()
            if context.user_data is not None and "browser_process" in context.user_data:
                del context.user_data["browser_process"]

            await query.edit_message_text(
                "❌ Ошибка при завершении авторизации. Попробуйте снова.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                ),
            )

        return ConversationHandler.END

    async def start_relogin_account_process(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Запускает процесс перелогинирования аккаунта через браузер"""
        query = update.callback_query
        if query is None:
            return ConversationHandler.END

        # Получаем список аккаунтов для выбора
        accounts_output = await self._run_node_script("auth", ["--list"])
        if accounts_output is None:
            await query.edit_message_text(
                "❌ Не удалось получить список аккаунтов. Попробуйте позже.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                ),
            )
            return ConversationHandler.END

        # Парсим вывод скрипта для получения информации об аккаунтах
        account_lines = []
        account_ids = []

        # Проверяем, является ли результат словарем с данными
        if isinstance(accounts_output, dict) and accounts_output.get("accounts"):
            # Если результат уже в формате JSON с распарсенными данными
            for account in accounts_output.get("accounts", []):
                status = account.get("status", "✅ OK")
                account_line = f"{len(account_lines) + 1} | {account['id']} | {status}"
                account_lines.append(account_line)
                account_ids.append(account["id"])
        elif isinstance(accounts_output.get("output"), str):
            # Парсим текстовый вывод скрипта
            accounts_output_text = accounts_output["output"]
            for line in accounts_output_text.split("\n"):
                if "|" in line and not line.startswith("Список аккаунтов:"):
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2:
                        account_id = parts[1]
                        account_lines.append(line.strip())
                        account_ids.append(account_id)

        if not account_lines:
            await query.edit_message_text(
                "Нет доступных аккаунтов для перелогинирования.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                ),
            )
            return ConversationHandler.END

        # Сохраняем список аккаунтов для последующего выбора
        if context.user_data is not None:
            context.user_data["account_ids_for_relogin"] = account_ids

        account_text = (
            "Выберите аккаунт для перелогинирования:\n\n"
            + "\n".join([f"{i+1}. {line}" for i, line in enumerate(account_lines)])
            + "\n\nВведите номер аккаунта для перелогинирования:"
        )

        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="register")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(account_text, reply_markup=reply_markup)

        return RELOGIN_ACCOUNT

    async def handle_relogin_account_choice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Обработка выбора аккаунта для перелогинирования"""
        if update.message is None:
            return ConversationHandler.END

        text = update.message.text
        if text is None:
            return ConversationHandler.END

        if (
            context.user_data is None
            or "account_ids_for_relogin" not in context.user_data
        ):
            await update.message.reply_text(
                "Сессия устарела. Пожалуйста, начните процесс заново.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                ),
            )
            return ConversationHandler.END

        try:
            choice = int(text.strip())
            account_ids = context.user_data["account_ids_for_relogin"]

            if choice < 1 or choice > len(account_ids):
                raise ValueError("Неверный выбор")

            account_id = account_ids[choice - 1]

            # Сохраняем выбранный аккаунт для перелогинирования
            if context.user_data is not None:
                context.user_data["relogin_account_id"] = account_id

            # Запускаем браузер для перелогинирования
            await update.message.reply_text(
                "🔄 Запускается процесс перелогинирования аккаунта...\n"
                "Браузер откроется для повторной авторизации. После "
                "завершения авторизации вернитесь в Telegram и нажмите 'Готово'."
            )

            # Инициализируем браузер и начинаем процесс авторизации
            try:
                success = await self.browser_manager.initialize(visible=True)
                if not success:
                    raise Exception("Не удалось инициализировать браузер")

                auth_success = await self.browser_manager.start_authentication()
                if not auth_success:
                    raise Exception("Не удалось начать процесс авторизации")

                logger.info(
                    f"Браузер открыт для перелогинирования аккаунта {account_id}"
                )

                # Сохраняем информацию о процессе в user_data
                if context.user_data is not None:
                    context.user_data["browser_process"] = {
                        "type": "relogin_account",
                        "account_id": account_id,
                        "manager": self.browser_manager,
                    }

            except Exception as e:
                logger.error(f"Ошибка при запуске браузера: {e}")
                await self.browser_manager.close()
                await update.message.reply_text(
                    "❌ Не удалось запустить браузер. Попробуйте позже.",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                    ),
                )
                return ConversationHandler.END

            return RELOGIN_ACCOUNT

        except (ValueError, IndexError):
            await update.message.reply_text(
                "Неверный выбор. Пожалуйста, введите номер из списка.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Отмена", callback_data="register")]]
                ),
            )
            return RELOGIN_ACCOUNT

    async def handle_relogin_account_response(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Обработка завершения перелогинирования аккаунта"""
        # Используем тот же метод, что и для проверки авторизации
        # Режим перелогинирования определится автоматически по контексту
        return await self.check_authentication_and_save_account(update, context)

    async def handle_account_deletion_choice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Обработка выбора аккаунта для удаления (с поддержкой изолированных аккаунтов)"""
        if update.message is None:
            return ConversationHandler.END

        text = update.message.text
        telegram_user_id = update.message.from_user.id
        await update.message.reply_text("⏳ Удаление аккаунта...")

        if (
            context.user_data is None
            or "account_ids_for_deletion" not in context.user_data
        ):
            await update.message.reply_text(
                "Сессия устарела. Пожалуйста, начните процесс заново.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                ),
            )
            return ConversationHandler.END

        try:
            choice = int(text.strip())
            account_ids = context.user_data["account_ids_for_deletion"]

            if choice < 1 or choice > len(account_ids):
                raise ValueError("Неверный выбор")

            account_id = account_ids[choice - 1]
            logger.info(
                f"Попытка удалить аккаунт {account_id} пользователем {telegram_user_id}"
            )

            # Проверяем, является ли это собственным аккаунтом пользователя (изолированный)
            if account_id == f"telegram_{telegram_user_id}":
                logger.info(
                    f"Удаляем изолированный аккаунт пользователя {telegram_user_id}"
                )
                # Удаляем директорию пользователя
                try:
                    base_path = Path(__file__).parent.parent.parent
                    account_dir = base_path / "session" / "accounts" / account_id
                    if account_dir.exists():
                        import shutil

                        shutil.rmtree(account_dir)
                        logger.info(f"Директория {account_dir} удалена успешно")
                    else:
                        logger.warning(f"Директория {account_dir} не найдена")

                    # Удаляем из tokens.json (если есть)
                    result = await self._run_node_script(
                        "auth", ["--remove", account_id, "--force"]
                    )
                    if result and result.get("success"):
                        logger.info(f"Аккаунт {account_id} удалён из tokens.json")
                    else:
                        logger.warning(
                            f"Аккаунт {account_id} не найден в tokens.json или ошибка удаления"
                        )

                    await update.message.reply_text(
                        f"✅ Аккаунт {account_id} успешно удалён!",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        "🔙 Назад к аккаунтам", callback_data="register"
                                    ),
                                    InlineKeyboardButton(
                                        "🏠 Главное меню", callback_data="back_to_menu"
                                    ),
                                ]
                            ]
                        ),
                    )
                    return ConversationHandler.END

                except Exception as e:
                    logger.error(
                        f"Ошибка при удалении директории аккаунта {account_id}: {e}"
                    )
                    await update.message.reply_text(
                        f"❌ Не удалось удалить аккаунт: {str(e)}",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        "🔙 Назад", callback_data="register"
                                    )
                                ]
                            ]
                        ),
                    )
                    return ConversationHandler.END

            # Для обычных аккаунтов (из tokens.json) используем Node.js скрипт
            result = await self._run_node_script(
                "auth", ["--remove", account_id, "--force"]
            )
            if result and result.get("success"):
                await update.message.reply_text(
                    f"✅ Аккаунт {account_id} успешно удалён!",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "🔙 Назад к аккаунтам", callback_data="register"
                                ),
                                InlineKeyboardButton(
                                    "🏠 Главное меню", callback_data="back_to_menu"
                                ),
                            ]
                        ]
                    ),
                )
            else:
                error_msg = (
                    result.get("error", "Неизвестная ошибка")
                    if result
                    else "Не удалось получить ответ от сервера"
                )
                await update.message.reply_text(
                    f"❌ Не удалось удалить аккаунт: {error_msg}",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🔙 Назад", callback_data="register")]]
                    ),
                )

        except (ValueError, IndexError):
            await update.message.reply_text(
                "Неверный выбор. Пожалуйста, введите номер из списка.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Отмена", callback_data="register")]]
                ),
            )
            return DELETE_ACCOUNT

        return ConversationHandler.END

    async def handle_text_input(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Обработка текстового ввода в контексте регистрационных процессов"""
        if update.message is None:
            return ConversationHandler.END

        text = update.message.text

        # Если это выбор аккаунта для удаления
        if context.user_data and context.user_data.get("account_ids_for_deletion"):
            return await self.handle_account_deletion_choice(update, context)

        # Если это выбор аккаунта для перелогинирования
        if context.user_data and context.user_data.get("account_ids_for_relogin"):
            return await self.handle_relogin_account_choice(update, context)

        return ConversationHandler.END

    def cleanup(self):
        """Очистка ресурсов при завершении работы"""
        self._stop_proxy_server()
        logger.info("Регистрационные обработчики очищены")
