# main.py
import sys
import os
import subprocess
import threading
import time
import signal


def run_node_server():
    """Запуск Node.js сервера (прокси)"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run([sys.executable, "-m", "nodeenv", "venv_node"], check=True)

    # Активируем Node.js окружение и запускаем сервер
    if sys.platform == "win32":
        activate_cmd = "venv_node\\Scripts\\activate && npm start"
    else:
        activate_cmd = "source venv_node/bin/activate && npm start"

    subprocess.run(activate_cmd, shell=True, check=True)


def run_telegram_bot():
    """Запуск Telegram бота"""
    bot_path = os.path.join(os.path.dirname(__file__), "telegram_bot")
    os.chdir(bot_path)

    # Устанавливаем зависимости Python для бота
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True
    )

    # Запускаем бота
    subprocess.run([sys.executable, "bot.py"], check=True)


def main():
    """Главная функция запуска"""
    print("Запуск системы...")

    # Создаем потоки для одновременного запуска
    node_thread = threading.Thread(target=run_node_server, daemon=True)
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)

    node_thread.start()
    time.sleep(5)  # Даем время на запуск сервера

    bot_thread.start()

    # Ждем завершения (или прерывания)
    try:
        node_thread.join()
        bot_thread.join()
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
        sys.exit(0)


if __name__ == "__main__":
    main()
