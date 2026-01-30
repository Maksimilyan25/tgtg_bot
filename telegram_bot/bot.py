import sys
import os
import warnings

# Игнорируем все предупреждения UserWarning
warnings.filterwarnings("ignore", category=UserWarning)

# Устанавливаем кодировку UTF-8 для вывода без сложных оберток
if sys.platform == "win32":
    # Отключаем буферизацию для мгновенного вывода
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1, encoding='utf-8')

# Add the parent directory to sys.path so relative imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from telegram_bot.core.bot import TelegramBot


def run_bot():
    """Запуск бота"""
    bot = TelegramBot()
    bot.run()


if __name__ == "__main__":
    # Принудительно сбрасываем буфер вывода
    print("🚀 Запуск Telegram бота...", flush=True)
    run_bot()