class UserDataManager:
    """Управляет данными пользовательских сессий для бота"""

    def __init__(self):
        self.user_data = {}  # Хранилище данных пользовательских сессий
        # Импортируем из конфига для поддержания единообразия
        from .config import COMPARE_MODEL_2

        self.COMPARE_MODEL_2 = COMPARE_MODEL_2

    def get_user_data(self, user_id):
        """
        Получает данные пользователя,
        создавая пустой словарь при их отсутствии
        """
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        return self.user_data[user_id]

    def set_compare_state(self, user_id, state):
        """Устанавливает состояние сравнения для пользователя"""
        user_data = self.get_user_data(user_id)
        user_data["compare_state"] = state

    def get_compare_state(self, user_id):
        """Получает состояние сравнения для пользователя"""
        user_data = self.get_user_data(user_id)
        return user_data.get("compare_state")

    def set_model_image(self, user_id, image_bytes):
        """Сохраняет изображение модели для пользователя"""
        user_data = self.get_user_data(user_id)
        user_data["model_image"] = image_bytes

    def get_model_image(self, user_id):
        """Получает сохраненное изображение модели для пользователя"""
        user_data = self.get_user_data(user_id)
        return user_data.get("model_image")

    def clear_model_image(self, user_id):
        """Очищает сохраненное изображение модели для пользователя"""
        if user_id in self.user_data and "model_image" in self.user_data[user_id]:
            del self.user_data[user_id]["model_image"]
            # Очищаем словарь данных пользователя, если он пуст
            if not self.user_data[user_id]:
                del self.user_data[user_id]
