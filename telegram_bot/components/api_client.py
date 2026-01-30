import aiohttp
import asyncio
import json
import logging
from .config import API_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)


class ApiClient:
    """Обрабатывает коммуникацию с AI proxy service"""

    def __init__(self):
        self.api_base_url = API_BASE_URL
        self.default_model = DEFAULT_MODEL

    def set_proxy_port(self, port: int):
        """Устанавливает порт прокси-сервера для клиента"""
        if port and port > 0:
            self.api_base_url = f"http://localhost:{port}"
            logger.info(f"Установлен порт прокси-сервера: {port}")

    async def upload_image(self, image_bytes):
        """Загружает изображение для получения URL"""
        try:
            image_bytes.seek(0)
            logger.info("Начало загрузки изображения на прокси-сервер")

            # Создаем form data для загрузки файла
            form_data = aiohttp.FormData()
            form_data.add_field(
                "file", image_bytes, content_type="image/jpeg", filename="image.jpg"
            )

            logger.info(f"Отправка изображения на {self.api_base_url}/api/files/upload")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/api/files/upload", data=form_data
                ) as response:
                    logger.info(f"Статус ответа от прокси: {response.status}")

                    response_text = await response.text()
                    logger.debug(f"Сырой ответ от сервера: {response_text}")

                    result = json.loads(response_text)
                    logger.info(f"JSON ответ получен")

                    if response.status != 200:
                        logger.error(
                            f"Ошибка загрузки изображения: статус {response.status}"
                        )
                        raise Exception(f"Ошибка API: статус {response.status}")

                    if (
                        "success" in result
                        and result["success"]
                        and "file" in result
                        and "url" in result["file"]
                    ):
                        image_url = result["file"]["url"]
                        logger.info(f"Изображение успешно загружено, URL: {image_url}")
                        return image_url
                    else:
                        logger.error(
                            "Ошибка загрузки изображения: неверный формат ответа"
                        )
                        raise Exception(
                            "Ошибка загрузки изображения: неверный формат ответа"
                        )
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети в upload_image: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка в upload_image: {e}", exc_info=True)
            raise

    async def _handle_api_response(self, response):
        """Обрабатывает ответ от API (проверяет тип ответа)"""
        if response.status != 200:
            error_text = await response.text()
            logger.error(f"Ошибка API: {response.status}, тело: {error_text}")
            raise Exception(f"Ошибка API: статус {response.status}")

        logger.info(f"Обработка ответа со статусом: {response.status}")

        # Получаем Content-Type
        content_type = response.headers.get("Content-Type", "").lower()
        logger.debug(f"Content-Type ответа: {content_type}")

        # Если это стриминг (SSE)
        if (
            "text/event-stream" in content_type
            or "application/x-ndjson" in content_type
        ):
            logger.info("Обнаружен стриминг-ответ (SSE)")
            return await self._handle_streaming_response(response)
        else:
            # Если это обычный JSON ответ
            logger.info("Обнаружен обычный JSON ответ")
            return await self._handle_json_response(response)

    async def _handle_json_response(self, response):
        """Обрабатывает обычный JSON ответ"""
        try:
            response_text = await response.text()
            logger.debug(
                f"Получен JSON ответ, первые 300 символов: {response_text[:300]}..."
            )

            result = json.loads(response_text)
            logger.info(f"JSON успешно распарсен, ключи: {list(result.keys())}")

            # Извлекаем текст из разных форматов ответов
            # Формат из логов: {"choices":[{"message":{"content":"..."}}]}
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                if "content" in message:
                    content = message["content"]
                    logger.info(
                        f"Извлечен контент из choices[0].message.content, длина: {len(content)}"
                    )
                    return content

            elif "response" in result:
                content = result["response"]
                logger.info(
                    f"Извлечен контент из поля 'response', длина: {len(content)}"
                )
                return content

            elif "message" in result and "content" in result["message"]:
                content = result["message"]["content"]
                logger.info(
                    f"Извлечен контент из поля 'message.content', длина: {len(content)}"
                )
                return content

            else:
                logger.warning(
                    f"Неизвестный формат ответа. Ключи: {list(result.keys())}"
                )
                # Попробуем найти content любым способом
                import re

                # Поиск любого поля с текстом
                json_str = json.dumps(result)
                if '"content":' in json_str:
                    match = re.search(r'"content":\s*"([^"]+)"', json_str)
                    if match:
                        content = match.group(1)
                        logger.info(
                            f"Найден content через regex, длина: {len(content)}"
                        )
                        return content

                logger.debug(f"Полный ответ для отладки: {result}")
                return "Не удалось получить результат от сервиса анализа."

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            logger.error(f"Сырой текст ответа: {response_text[:500]}")
            raise Exception(f"Ошибка парсинга ответа: {e}")
        except Exception as e:
            logger.error(f"Ошибка обработки JSON ответа: {e}", exc_info=True)
            raise

    async def _handle_streaming_response(self, response):
        """Обрабатывает стриминг-ответ (SSE формат)"""
        full_response = ""
        logger.info("Обработка стриминг-ответа (SSE)")

        async for line in response.content:
            if not line:
                continue

            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            # Обрабатываем строки формата SSE (Server-Sent Events)
            if line_str.startswith("data: "):
                data_line = line_str[6:]  # Убираем "data: "
                if data_line == "[DONE]":
                    logger.info("Получен маркер завершения стриминга [DONE]")
                    break

                try:
                    chunk_data = json.loads(data_line)

                    # Извлекаем текст из разных форматов ответов
                    if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                        delta = chunk_data["choices"][0].get("delta", {})
                        if "content" in delta:
                            content = delta["content"]
                            full_response += content
                            logger.debug(f"Получен стриминг-чанк: {content[:50]}...")
                    elif "response" in chunk_data:
                        content = chunk_data["response"]
                        full_response += content
                        logger.debug(
                            f"Получен стриминг-чанк (response): {content[:50]}..."
                        )
                except json.JSONDecodeError as json_error:
                    logger.warning(
                        f"Не удалось распарсить JSON в стриминге: {data_line[:100]}..."
                    )
                    continue

        logger.info(f"Собрано {len(full_response)} символов из стриминга")
        return (
            full_response
            if full_response
            else "Не удалось получить результат от сервиса анализа."
        )

    async def send_image_analysis(self, image_bytes, prompt):
        """Отправляет изображение и промт на анализ"""
        try:
            logger.info("Начало процесса отправки изображения на анализ")
            logger.debug(f"Текст запроса для анализа: {prompt}")

            # Сначала загружаем изображение для получения URL
            logger.info("Загрузка изображения на сервер...")
            image_url = await self.upload_image(image_bytes)
            logger.info(f"Изображение успешно загружено, URL: {image_url}")

            headers = {"Content-Type": "application/json"}

            # Данные запроса - БЕЗ stream: True (по логам прокси не поддерживает стриминг)
            data = {
                "message": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "image": image_url},
                ],
                "model": self.default_model,
                # НЕ добавляем "stream": True - прокси возвращает обычный JSON
            }

            logger.info(
                f"Отправка запроса на анализ изображения на {self.api_base_url}/api/chat"
            )
            logger.debug(f"Данные запроса: {data}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/api/chat",
                    json=data,
                    headers=headers,
                    timeout=120,
                ) as response:
                    return await self._handle_api_response(response)

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при отправке запроса на анализ: {e}")
            raise
        except asyncio.TimeoutError as e:
            logger.error(f"Таймаут при ожидании ответа от прокси-сервера: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в send_image_analysis: {e}", exc_info=True
            )
            raise

    async def send_image_comparison(self, model_image_bytes, item_image_bytes, prompt):
        """Отправляет два изображения на сравнение"""
        try:
            logger.info("Начало процесса сравнения двух изображений")

            # Загружаем оба изображения для получения URL
            logger.info("Загрузка эталонного изображения...")
            model_image_url = await self.upload_image(model_image_bytes)
            logger.info(f"Эталонное изображение загружено: {model_image_url}")

            logger.info("Загрузка изображения для сравнения...")
            item_image_url = await self.upload_image(item_image_bytes)
            logger.info(f"Изображение для сравнения загружено: {item_image_url}")

            headers = {"Content-Type": "application/json"}

            # Данные запроса - БЕЗ stream: True
            data = {
                "message": [
                    {
                        "type": "text",
                        "text": f"{prompt}\n\nЭталонное изображение:\nИзображение для сравнения:",
                    },
                    {"type": "image", "image": model_image_url},
                    {"type": "image", "image": item_image_url},
                ],
                "model": self.default_model,
                # НЕ добавляем "stream": True
            }

            logger.info(
                f"Отправка запроса на сравнение изображений на {self.api_base_url}/api/chat"
            )

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/api/chat",
                    json=data,
                    headers=headers,
                    timeout=120,
                ) as response:
                    return await self._handle_api_response(response)

        except Exception as e:
            logger.error(f"Ошибка в send_image_comparison: {e}")
            raise

    async def send_text_analysis(self, prompt):
        """Отправляет текстовый промт на анализ"""
        try:
            headers = {"Content-Type": "application/json"}

            # Данные запроса - БЕЗ stream: True
            data = {
                "message": prompt,
                "model": self.default_model,
                # НЕ добавляем "stream": True
            }

            logger.info(
                f"Отправка текстового запроса на {self.api_base_url}/api/chat "
                f"с моделью {self.default_model}"
            )

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/api/chat",
                    json=data,
                    headers=headers,
                    timeout=120,
                ) as response:
                    return await self._handle_api_response(response)

        except Exception as e:
            logger.error(f"Ошибка в send_text_analysis: {e}")
            raise
