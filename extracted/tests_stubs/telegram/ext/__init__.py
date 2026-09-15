"""Minimal `telegram.ext` stand-in: records handler registrations."""


class ContextTypes:
    DEFAULT_TYPE = object


class BaseHandler:
    def __init__(self, callback, pattern=None, command=None, filters=None):
        self.callback = callback
        self.pattern = pattern
        self.command = command
        self.filters = filters


class CommandHandler(BaseHandler):
    def __init__(self, command, callback, **kw):
        super().__init__(callback, command=command)


class CallbackQueryHandler(BaseHandler):
    def __init__(self, callback, pattern=None, **kw):
        super().__init__(callback, pattern=pattern)


class MessageHandler(BaseHandler):
    def __init__(self, filters, callback, **kw):
        super().__init__(callback, filters=filters)


class _Filter:
    def __init__(self, name):
        self.name = name

    def __or__(self, other):
        return _Filter("%s|%s" % (self.name, getattr(other, "name", other)))

    def __and__(self, other):
        return _Filter("%s&%s" % (self.name, getattr(other, "name", other)))

    def __invert__(self):
        return _Filter("~%s" % self.name)

    def __repr__(self):
        return "filters.%s" % self.name


class _DocumentNS:
    ALL = _Filter("Document.ALL")


class filters:  # noqa: N801 - mirrors the real module's lowercase name
    TEXT = _Filter("TEXT")
    PHOTO = _Filter("PHOTO")
    COMMAND = _Filter("COMMAND")
    Document = _DocumentNS


class Application:
    def __init__(self, token=None):
        self.token = token
        self.handlers = []
        self.error_handlers = []

    def add_handler(self, handler, group=0):
        self.handlers.append(handler)

    def add_error_handler(self, handler):
        self.error_handlers.append(handler)

    def run_polling(self, **kwargs):  # pragma: no cover
        raise RuntimeError("run_polling must not be called from tests")

    @staticmethod
    def builder():
        return _Builder()


class _Builder:
    def __init__(self):
        self._token = None

    def token(self, token):
        self._token = token
        return self

    def build(self):
        return Application(self._token)
