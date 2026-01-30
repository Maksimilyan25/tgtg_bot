# package_release.py
import os
import shutil
import subprocess
import sys
from pathlib import Path

def create_release():
    """Создать готовый к распространению релиз"""
    print("Создание релиза FreeQwenApi...")
    
    # Пути
    base_dir = Path(__file__).parent
    dist_dir = base_dir / "dist"
    release_dir = base_dir / "FreeQwenApi_Release"
    
    # Очистка предыдущего релиза
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(exist_ok=True)
    
    # Копируем EXE файл
    exe_file = dist_dir / "FreeQwenApi.exe"
    if exe_file.exists():
        shutil.copy2(exe_file, release_dir)
        print(f"✓ Скопирован EXE файл")
    else:
        print("❌ EXE файл не найден. Сначала выполните сборку.")
        return
    
    # Файлы и папки для копирования
    items_to_copy = [
        "telegram_bot",
        "index.js", 
        "package.json",
        "node_modules",
        "uploads",
        "logs",
        "session",
        "README.md"
    ]
    
    # Копируем файлы и папки
    for item in items_to_copy:
        item_path = base_dir / item
        if item_path.exists():
            if item_path.is_file():
                shutil.copy2(item_path, release_dir)
                print(f"✓ Скопирован файл: {item}")
            else:
                shutil.copytree(item_path, release_dir / item, dirs_exist_ok=True)
                print(f"✓ Скопирована папка: {item}")
        else:
            print(f"⚠ Не найден: {item}")
    
    # Создаем необходимые папки если их нет
    (release_dir / "uploads").mkdir(exist_ok=True)
    (release_dir / "logs").mkdir(exist_ok=True)
    (release_dir / "session").mkdir(exist_ok=True)
    
    # Создаем конфигурационный файл
    create_config(release_dir)
    
    # Создаем README для пользователя
    create_user_readme(release_dir)
    
    print(f"\n✅ Релиз создан в папке: {release_dir}")
    print(f"Размер папки: {get_folder_size(release_dir) / 1024 / 1024:.2f} MB")
    
    # Создаем ZIP архив для распространения
    create_zip_archive(release_dir)

def create_config(release_dir):
    """Создать конфигурационный файл"""
    config_content = """# Конфигурация FreeQwenApi

# Настройки прокси сервера
PROXY_PORT=3000
PROXY_HOST=localhost

# Настройки бота
TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН_БОТА
ADMIN_IDS=123456789,987654321

# Настройки API
API_BASE_URL=http://localhost:3000/api
"""
    
    config_file = release_dir / "config.env"
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    print("✓ Создан конфигурационный файл config.env")

def create_user_readme(release_dir):
    """Создать README для пользователя"""
    readme_content = """# FreeQwenApi - Установка и запуск

## Требования
- Windows 7/8/10/11
- Python 3.8+ (уже включено в сборку)
- Node.js 16+ (необходимо установить отдельно)

## Установка Node.js
1. Скачайте Node.js с официального сайта: https://nodejs.org/
2. Установите, выбрав опцию "Add to PATH"

## Запуск программы
1. Скопируйте всю папку FreeQwenApi_Release на компьютер
2. Запустите файл `FreeQwenApi.exe`
3. При первом запуске программа установит необходимые зависимости

## Настройка
1. Откройте файл `config.env`
2. Укажите ваш TELEGRAM_BOT_TOKEN
3. Укажите ID администраторов через запятую

## Проверка работы
1. Прокси сервер: http://localhost:3000
2. Проверьте бота в Telegram

## Логи
- Логи прокси: папка `logs/`
- Логи бота: папка `telegram_bot/logs/`

## Поддержка
При возникновении проблем:
1. Проверьте, установлен ли Node.js
2. Проверьте файл config.env
3. Посмотрите логи в соответствующих папках
"""
    
    readme_file = release_dir / "ПРОЧТИ_МЕНЯ.txt"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("✓ Создано руководство пользователя")

def get_folder_size(folder):
    """Получить размер папки в байтах"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    return total_size

def create_zip_archive(release_dir):
    """Создать ZIP архив для распространения"""
    try:
        import zipfile
        
        zip_path = release_dir.parent / "FreeQwenApi_Release.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(release_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, release_dir.parent)
                    zipf.write(file_path, arcname)
        
        print(f"\n📦 Создан ZIP архив: {zip_path}")
        print(f"Размер архива: {os.path.getsize(zip_path) / 1024 / 1024:.2f} MB")
    except Exception as e:
        print(f"⚠ Не удалось создать ZIP архив: {e}")

if __name__ == "__main__":
    create_release()