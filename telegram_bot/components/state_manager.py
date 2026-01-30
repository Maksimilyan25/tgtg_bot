from telegram.ext import ConversationHandler


class StateManager:
    """Manages conversation states for the bot"""

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

    @staticmethod
    def get_conversation_handler(entry_points, states, fallbacks):
        """Creates a conversation handler with the provided states"""
        return ConversationHandler(
            entry_points=entry_points,
            states=states,
            fallbacks=fallbacks,
            per_chat=True,
            per_user=True,
            allow_reentry=True,
        )

    @staticmethod
    def get_search_defects_states(callback_handler, cancel_handler):
        """Returns states for search defects conversation"""
        return {StateManager.SEARCH_DEFECTS: [callback_handler, cancel_handler]}

    @staticmethod
    def get_compare_model_states(
        callback_handler_1, callback_handler_2, cancel_handler
    ):
        """Returns states for compare model conversation"""
        return {
            StateManager.COMPARE_MODEL_1: [callback_handler_1, cancel_handler],
            StateManager.COMPARE_MODEL_2: [callback_handler_2, cancel_handler],
        }

    @staticmethod
    def get_custom_prompt_states(callback_handler, cancel_handler):
        """Returns states for custom prompt conversation"""
        return {StateManager.CUSTOM_PROMPT: [callback_handler, cancel_handler]}
