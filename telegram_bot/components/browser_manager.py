"""
Модуль для управления браузером через Playwright для авторизации в Qwen
Этот модуль заменяет Node.js скрипты и обеспечивает прямой запуск браузера
из Telegram бота без зависимости от Node.js
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class BrowserManager:
    """Класс для управления браузером и процессами авторизации"""

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_authenticated = False
        self.auth_token = None

        # Пути для сохранения сессий
        self.session_path = Path(__file__).parent.parent.parent / "session"
        self.accounts_path = self.session_path / "accounts"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Создает необходимые директории для сессий"""
        self.session_path.mkdir(exist_ok=True)
        self.accounts_path.mkdir(exist_ok=True)

    async def initialize(self, visible: bool = True):
        """Инициализация браузера"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=not visible, slow_mo=50 if visible else 0
            )

            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )

            # Устанавливаем увеличенные таймауты
            self.context.set_default_navigation_timeout(120000)
            self.context.set_default_timeout(120000)

            logger.info("Браузер успешно инициализирован")
            return True
        except Exception as e:
            logger.error(f"Ошибка при инициализации браузера: {e}")
            return False

    async def start_authentication(self) -> bool:
        """Начинает процесс авторизации"""
        if not self.context:
            logger.error("Браузер не инициализирован")
            return False

        try:
            self.page = await self.context.new_page()

            # Открываем страницу авторизации
            await self.page.goto(
                "https://chat.qwen.ai/auth?action=signin", wait_until="domcontentloaded"
            )

            logger.info(
                "Открыта страница авторизации. Ожидание действий пользователя..."
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при открытии страницы авторизации: {e}")
            return False

    async def check_authentication(self) -> bool:
        """Проверяет, завершена ли авторизация"""
        if not self.page:
            return False

        try:
            # Проверяем наличие элементов авторизации
            login_container = await self.page.locator(".login-container").count()
            if login_container == 0:
                # Авторизация завершена, извлекаем токен
                await self.page.goto(
                    "https://chat.qwen.ai/", wait_until="domcontentloaded"
                )
                await asyncio.sleep(2)  # Ждем загрузки

                # Пробуем извлечь токен из localStorage
                token = await self.page.evaluate(
                    """() => {
                    return localStorage.getItem('accessToken') ||
                           localStorage.getItem('token') ||
                           JSON.parse(localStorage.getItem('persist:root') || '{}').user?.token;
                }"""
                )

                if token:
                    # Убираем кавычки, если они есть
                    if (
                        isinstance(token, str)
                        and token.startswith('"')
                        and token.endswith('"')
                    ):
                        token = token[1:-1]
                    elif (
                        isinstance(token, str)
                        and token.startswith("'")
                        and token.endswith("'")
                    ):
                        token = token[1:-1]

                    self.auth_token = token
                    self.is_authenticated = True
                    logger.info("Авторизация успешно завершена, токен получен")
                    return True
                else:
                    logger.warning("Авторизация не обнаружена - токен не найден")
                    return False
            else:
                logger.info("Авторизация не завершена - обнаружены элементы входа")
                return False

        except Exception as e:
            logger.error(f"Ошибка при проверке авторизации: {e}")
            return False

    async def _update_tokens_json(self, account_id: str) -> bool:
        """Обновляет файл tokens.json для синхронизации с Node.js частью"""
        try:
            tokens_path = self.session_path / "tokens.json"

            # Загружаем текущие токены
            tokens = []
            if tokens_path.exists():
                with open(tokens_path, "r", encoding="utf-8") as f:
                    tokens = json.load(f)

            # Проверяем, есть ли уже такой аккаунт
            account_exists = any(t["id"] == account_id for t in tokens)

            # Получаем текущий токен из файла
            token_file = self.accounts_path / account_id / "token.txt"
            if not token_file.exists():
                logger.error(f"Файл токена для аккаунта {account_id} не найден")
                return False

            with open(token_file, "r", encoding="utf-8") as f:
                current_token = f.read().strip()

            if not account_exists:
                # Добавляем новый аккаунт
                tokens.append(
                    {
                        "id": account_id,
                        "token": current_token,
                        "invalid": False,
                        "resetAt": None,
                    }
                )
            else:
                # Обновляем существующий аккаунт
                for token in tokens:
                    if token["id"] == account_id:
                        token["token"] = current_token
                        token["invalid"] = False
                        token["resetAt"] = None
                        break

            # Сохраняем обновленный список
            with open(tokens_path, "w", encoding="utf-8") as f:
                json.dump(tokens, f, indent=2, ensure_ascii=False)

            logger.info(f"Файл tokens.json обновлен для аккаунта {account_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении tokens.json: {e}")
            return False

    async def save_account(
        self,
        account_id: str,
        is_relogin: bool = False,
        telegram_user_id: Optional[int] = None,
    ) -> bool:
        """Сохраняет аккаунт с полученным токеном

        Args:
            account_id: ID аккаунта
            is_relogin: Флаг перелогинивания (обновления токена)
            telegram_user_id: ID пользователя Telegram (если это аккаунт Telegram)
        """
        if not self.auth_token:
            logger.error("Токен не получен, сохранение аккаунта невозможно")
            return False

        try:
            # Создаем директорию для аккаунта
            account_dir = self.accounts_path / account_id
            account_dir.mkdir(exist_ok=True)

            # Сохраняем токен
            token_file = account_dir / "token.txt"
            with open(token_file, "w", encoding="utf-8") as f:
                f.write(self.auth_token)

            # Сохраняем информацию об аккаунте
            account_info = {
                "id": account_id,
                "token": self.auth_token,
                "last_updated": int(time.time()),
            }

            # Добавляем информацию о Telegram пользователе, если это аккаунт Telegram
            if telegram_user_id is not None:
                account_info["telegram_user_id"] = telegram_user_id
                # Создаем символическую ссылку для удобного доступа
                telegram_account_dir = (
                    self.accounts_path / f"telegram_{telegram_user_id}"
                )
                if not telegram_account_dir.exists():
                    try:
                        telegram_account_dir.symlink_to(account_dir)
                    except (OSError, NotImplementedError) as e:
                        # В Windows symlink может не поддерживаться, создаем копию
                        import shutil

                        if telegram_account_dir.exists():
                            shutil.rmtree(telegram_account_dir)
                        shutil.copytree(account_dir, telegram_account_dir)

            info_file = account_dir / "account_info.json"
            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(account_info, f, indent=2)

            # Обновляем файл tokens.json для синхронизации с Node.js
            await self._update_tokens_json(account_id)

            if is_relogin:
                logger.info(f"Токен аккаунта {account_id} успешно обновлен")
            else:
                logger.info(f"Аккаунт {account_id} успешно сохранен")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении аккаунта: {e}")
            return False

    async def close(self):
        """Закрывает браузер"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

            logger.info("Браузер успешно закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии браузера: {e}")

    async def wait_for_auth_completion(self, timeout: int = 300) -> bool:
        """Ожидает завершения авторизации с таймаутом"""
        try:
            # Проверяем каждые 5 секунд
            for _ in range(timeout // 5):
                if await self.check_authentication():
                    return True
                await asyncio.sleep(5)

            return False
        except Exception as e:
            logger.error(f"Ошибка при ожидании авторизации: {e}")
            return False
