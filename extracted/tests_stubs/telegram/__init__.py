"""Minimal `telegram` stand-in for offline tests."""


class InlineKeyboardButton:
    def __init__(self, text, callback_data=None, url=None):
        self.text = text
        self.callback_data = callback_data
        self.url = url

    def __repr__(self):
        return "Button(%r,%r)" % (self.text, self.callback_data)


class InlineKeyboardMarkup:
    def __init__(self, inline_keyboard):
        self.inline_keyboard = inline_keyboard

    def all_callback_data(self):
        out = []
        for row in self.inline_keyboard:
            for button in row:
                if button.callback_data:
                    out.append(button.callback_data)
        return out


class Update:
    def __init__(self, message=None, callback_query=None, effective_user=None):
        self.message = message
        self.callback_query = callback_query
        self._user = effective_user

    @property
    def effective_user(self):
        return self._user

    @property
    def effective_message(self):
        if self.message is not None:
            return self.message
        if self.callback_query is not None:
            return self.callback_query.message
        return None


class User:
    def __init__(self, id, first_name="Test", username="tester"):
        self.id = id
        self.first_name = first_name
        self.username = username


class Bot:
    pass


class LinkPreviewOptions:
    def __init__(self, is_disabled=None, url=None, prefer_small_media=None,
                 prefer_large_media=None, show_above_text=None):
        self.is_disabled = is_disabled
        self.url = url
