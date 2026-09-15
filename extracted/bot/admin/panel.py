"""Privileged operations.

This module existed before but nothing ever imported it, so "add a model from
the panel" was decorative. It is now the single write path used by
handlers/admin.py, and every function re-checks admin rights itself: defence in
depth, so a future caller cannot bypass the guard by accident.

Functions are intentionally synchronous -- the old versions were declared async
while containing no awaits at all.
"""
import logging

from bot.database import get_db
from bot.security import is_admin

logger = logging.getLogger(__name__)


class PermissionDenied(Exception):
    pass


def _require_admin(user_id):
    if not is_admin(user_id):
        logger.warning("PermissionDenied: user_id=%s attempted a privileged op", user_id)
        raise PermissionDenied("user %s is not an admin" % user_id)


def add_ai_model(actor_id, name, api_url, api_key, model_id, make_default=False):
    _require_admin(actor_id)
    pk = get_db().add_ai_model(name, api_url, api_key, model_id, make_default=make_default)
    logger.info("admin %s added AI model %r (pk=%s)", actor_id, name, pk)
    return pk


def update_ai_model(actor_id, model_pk, **fields):
    _require_admin(actor_id)
    get_db().update_ai_model(model_pk, **fields)
    logger.info("admin %s updated model pk=%s fields=%s",
                actor_id, model_pk, sorted(fields))


def delete_ai_model(actor_id, model_pk):
    _require_admin(actor_id)
    get_db().delete_ai_model(model_pk)
    logger.info("admin %s deleted model pk=%s", actor_id, model_pk)


def set_default_ai_model(actor_id, model_pk):
    _require_admin(actor_id)
    name = get_db().set_default_ai_model(model_pk)
    logger.info("admin %s set default model to %r", actor_id, name)
    return name


def add_product(actor_id, name, description, price, duration_days, messages_count=0):
    _require_admin(actor_id)
    pid = get_db().create_product(name, description, price, duration_days, messages_count)
    logger.info("admin %s created product %r (id=%s)", actor_id, name, pid)
    return pid


def update_product(actor_id, product_id, **fields):
    _require_admin(actor_id)
    get_db().update_product(product_id, **fields)
    logger.info("admin %s updated product id=%s fields=%s",
                actor_id, product_id, sorted(fields))


def delete_product(actor_id, product_id):
    _require_admin(actor_id)
    get_db().delete_product(product_id)
    logger.info("admin %s deleted product id=%s", actor_id, product_id)


def set_setting(actor_id, key, value):
    _require_admin(actor_id)
    get_db().set_setting(key, value)
    logger.info("admin %s set setting %s", actor_id, key)


def set_user_quota(actor_id, user_id, limit):
    _require_admin(actor_id)
    from bot.services.subscription import subscription_manager
    sub = subscription_manager.set_quota(user_id, limit)
    logger.info("admin %s set quota of user %s to %s", actor_id, user_id, limit)
    return sub


def set_user_banned(actor_id, user_id, banned):
    _require_admin(actor_id)
    if is_admin(user_id):
        raise PermissionDenied("cannot ban an admin")
    get_db().set_banned(user_id, banned)
    logger.info("admin %s %s user %s", actor_id, "banned" if banned else "unbanned", user_id)
