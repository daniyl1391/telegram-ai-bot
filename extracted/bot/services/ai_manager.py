"""AI provider integration.

Fixes versus the old implementation:

* The old payload was {"message": ..., "model": ...} and it read
  data["response"]. No mainstream provider speaks that shape, so AI chat could
  never have worked against OpenAI, OpenRouter, Groq, Anthropic-compatible
  proxies or anything else. We now send the OpenAI chat-completions format and
  parse every common response shape.
* The old code cached db.get_ai_models() once at import, so a model added from
  the panel stayed invisible until a restart. Models are now read per request.
* No retry existed. We retry on timeouts, connection errors and 429/5xx with
  exponential backoff, and rotate through multiple API keys.
* Conversation history is kept per user so the chat has context.
"""
import time
import asyncio
import logging

from bot.database import get_db

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 522, 524}


class AIError(Exception):
    """Raised with a short, user-presentable detail string."""


def _split_keys(raw):
    """One model row may hold several comma/newline separated API keys."""
    if not raw:
        return []
    parts = [p.strip() for p in str(raw).replace("\n", ",").split(",")]
    return [p for p in parts if p]


def _extract_reply(data):
    """Pull the assistant text out of whatever the provider returned."""
    if data is None:
        return None
    if isinstance(data, str):
        return data.strip() or None
    if not isinstance(data, dict):
        return None

    # OpenAI / OpenRouter / Groq / Together / most proxies
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, list):  # multimodal content blocks
                    text = "".join(
                        b.get("text", "") for b in content if isinstance(b, dict)
                    )
                    if text.strip():
                        return text.strip()
                if isinstance(content, str) and content.strip():
                    return content.strip()
            for key in ("text", "delta"):
                value = first.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, dict) and isinstance(value.get("content"), str):
                    return value["content"].strip()

    # Anthropic native
    content = data.get("content")
    if isinstance(content, list):
        text = "".join(b.get("text", "") for b in content if isinstance(b, dict))
        if text.strip():
            return text.strip()

    # Google Gemini native
    candidates = data.get("candidates")
    if isinstance(candidates, list) and candidates:
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        if text.strip():
            return text.strip()

    # Simple custom APIs
    for key in ("response", "output_text", "answer", "reply", "result", "message", "text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            inner = value.get("content") or value.get("text")
            if isinstance(inner, str) and inner.strip():
                return inner.strip()
    return None


def _extract_error(status, data, body_text):
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or err.get("type")
            if msg:
                return "HTTP %s: %s" % (status, str(msg)[:180])
        if isinstance(err, str):
            return "HTTP %s: %s" % (status, err[:180])
        if data.get("detail"):
            return "HTTP %s: %s" % (status, str(data["detail"])[:180])
    return "HTTP %s: %s" % (status, (body_text or "")[:180] or "empty response")


class AIManager:
    def __init__(self):
        # Per-user rolling conversation history: {user_id: [(role, content), ...]}
        self._history = {}

    # ------------------------------------------------------------- model access
    def list_models(self, only_active=True):
        return get_db().get_ai_models(only_active=only_active)

    def resolve_model(self, model_pk=None, name=None):
        db = get_db()
        if model_pk is not None:
            model = db.get_ai_model(model_pk)
            if model and model["status"]:
                return model
        if name:
            model = db.get_ai_model_by_name(name)
            if model and model["status"]:
                return model
        configured = db.get_setting("default_ai_model")
        if configured:
            model = db.get_ai_model_by_name(configured)
            if model and model["status"]:
                return model
        return db.get_default_ai_model()

    # ---------------------------------------------------------------- history
    def get_history(self, user_id):
        return list(self._history.get(user_id, []))

    def clear_history(self, user_id):
        self._history.pop(user_id, None)

    def _remember(self, user_id, role, content, max_turns):
        if max_turns <= 0:
            self._history.pop(user_id, None)
            return
        bucket = self._history.setdefault(user_id, [])
        bucket.append((role, content))
        # keep the last max_turns * 2 entries (user + assistant pairs)
        limit = max_turns * 2
        if len(bucket) > limit:
            del bucket[: len(bucket) - limit]

    def _build_messages(self, user_id, prompt, system_prompt, max_turns):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        for role, content in self._history.get(user_id, [])[-max_turns * 2:] if max_turns else []:
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})
        return messages

    # ------------------------------------------------------------------- call
    async def _post(self, session_factory, url, headers, payload, timeout_s):
        import aiohttp

        timeout = aiohttp.ClientTimeout(total=timeout_s)
        async with session_factory(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                body_text = await resp.text()
                data = None
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    pass
                return resp.status, data, body_text

    async def _request(self, model, messages, timeout_s, max_retries, session_factory=None):
        import aiohttp

        if session_factory is None:
            session_factory = aiohttp.ClientSession

        keys = _split_keys(model.get("api_key")) or [""]
        payload = {
            "model": model.get("model_id"),
            "messages": messages,
        }
        last_error = "unknown error"
        attempt = 0
        total_attempts = max(1, max_retries) * len(keys)

        for key_index, api_key in enumerate(keys):
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = "Bearer %s" % api_key
                # Some providers (Anthropic, Azure) want their own header names.
                headers["x-api-key"] = api_key
                headers["api-key"] = api_key
            for retry in range(max(1, max_retries)):
                attempt += 1
                try:
                    status, data, body_text = await self._post(
                        session_factory, model["api_url"], headers, payload, timeout_s
                    )
                except asyncio.TimeoutError:
                    last_error = "timeout after %ss" % timeout_s
                except aiohttp.ClientError as exc:
                    last_error = "connection error: %s" % str(exc)[:120]
                except Exception as exc:  # never let a provider crash a handler
                    last_error = "%s: %s" % (type(exc).__name__, str(exc)[:120])
                else:
                    if 200 <= status < 300:
                        reply = _extract_reply(data)
                        if reply:
                            return reply
                        last_error = "provider returned no usable text"
                        break  # a 2xx with junk body will not improve on retry
                    last_error = _extract_error(status, data, body_text)
                    if status in (401, 403) and key_index + 1 < len(keys):
                        logger.warning("AI key #%s rejected, rotating", key_index + 1)
                        break  # try the next key
                    if status not in RETRYABLE_STATUS:
                        break

                if attempt < total_attempts:
                    backoff = min(2 ** retry, 8)
                    logger.info("AI retry %s/%s in %ss (%s)",
                                attempt, total_attempts, backoff, last_error)
                    await asyncio.sleep(backoff)

        raise AIError(last_error)

    async def chat(self, user_id, prompt, model_pk=None, session_factory=None):
        """Send `prompt` and return the assistant reply. Raises AIError."""
        db = get_db()
        model = self.resolve_model(model_pk=model_pk)
        if not model:
            raise AIError("no active model configured")

        timeout_s = db.get_int_setting("ai_timeout_seconds", 45)
        max_retries = db.get_int_setting("ai_max_retries", 3)
        max_turns = db.get_int_setting("ai_max_history", 8)
        system_prompt = db.get_setting("ai_system_prompt") or ""

        messages = self._build_messages(user_id, prompt, system_prompt, max_turns)
        started = time.monotonic()
        try:
            reply = await self._request(
                model, messages, timeout_s, max_retries, session_factory
            )
        except AIError:
            db.log_ai_usage(user_id, model["name"], ok=False)
            raise
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info("AI ok user=%s model=%s %sms", user_id, model["name"], elapsed_ms)

        self._remember(user_id, "user", prompt, max_turns)
        self._remember(user_id, "assistant", reply, max_turns)
        db.log_ai_usage(user_id, model["name"], ok=True)
        return reply, model["name"]

    async def test_connection(self, model_pk, session_factory=None):
        """Used by the admin panel's "Test connection" button."""
        db = get_db()
        model = db.get_ai_model(model_pk)
        if not model:
            return False, "model not found", 0
        timeout_s = db.get_int_setting("ai_timeout_seconds", 45)
        messages = [{"role": "user", "content": "Reply with the single word: OK"}]
        started = time.monotonic()
        try:
            reply = await self._request(model, messages, timeout_s, 1, session_factory)
        except AIError as exc:
            return False, str(exc), int((time.monotonic() - started) * 1000)
        return True, reply[:120], int((time.monotonic() - started) * 1000)


ai_manager = AIManager()
