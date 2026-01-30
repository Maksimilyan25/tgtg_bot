import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
API_BASE_URL = os.getenv(
    "API_BASE_URL", "http://localhost:3264"
)  # Default API base URL
DEFAULT_MODEL = "qwen-max-latest"

# Logging configuration
LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOGGING_LEVEL = "INFO"

# States for conversation
SEARCH_DEFECTS = 0
COMPARE_MODEL_1 = 1
COMPARE_MODEL_2 = 2
CUSTOM_PROMPT = 3
ACCOUNT_MENU = 4
LIST_ACCOUNTS = 5
ADD_ACCOUNT = 6
RELOGIN_ACCOUNT = 7
DELETE_ACCOUNT = 8
