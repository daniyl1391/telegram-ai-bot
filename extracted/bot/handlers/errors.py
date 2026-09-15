"""Global error handler.

The old bot had none: any exception inside a handler produced a silent traceback
in the logs while the user stared at a spinner forever.
"""
import html
import logging
import traceback

from telegram.error import Forbidden, BadRequest, NetworkError, TimedOut

from bot.config import ADMIN_USER_IDS
from bot.i18n import t

logger = logging.getLogger(__name__)


async def error_handler(update, context):
    error = context.error

    if isinstance(error, (NetworkError, TimedOut)):
        logger.warning("Transient network error: %s", error)
        return
    if isinstance(error, Forbidden):
        logger.info("Bot blocked by a user: %s", error)
        return
    if isinstance(error, BadRequest) and "not modified" in str(error).lower():
        return

    logger.error("Unhandled exception while processing an update", exc_info=error)

    lang = "fa"
    try:
        if update is not None and getattr(update, "effective_user", None):
            from bot.database import get_db
            lang = get_db().get_language(update.effective_user.id)
    except Exception:
        pass

    # Tell the user something went wrong instead of leaving them hanging.
    try:
        if update is not None and getattr(update, "callback_query", None):
            await update.callback_query.answer(t("generic_error", lang), show_alert=True)
        elif update is not None and getattr(update, "effective_message", None):
            await update.effective_message.reply_text(t("generic_error", lang))
    except Exception:
        logger.debug("Could not deliver the error notice to the user")

    # And report it to the admins so problems are visible in production.
    where = "unknown"
    try:
        if update is not None and getattr(update, "effective_user", None):
            where = "user %s" % update.effective_user.id
        if update is not None and getattr(update, "callback_query", None):
            where += " · %s" % update.callback_query.data
    except Exception:
        pass

    trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    for admin_id in ADMIN_USER_IDS:
        try:
            body = t("admin_notice_error", "en",
                     where=html.escape(where),
                     error=html.escape(trace[-1200:]))
            await context.bot.send_message(admin_id, body, parse_mode="HTML")
        except Exception:
            logger.debug("Could not report the error to admin %s", admin_id)
