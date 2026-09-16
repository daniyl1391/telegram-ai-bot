"""Fast, resilient AI provider integration with streaming and usage metering."""
import asyncio
import contextvars
import json
import logging
import time

from bot.database import get_db
from bot.capabilities import enabled as capability_enabled, value_for_user

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 522, 524}


class AIError(Exception):
    """Raised with a short, user-presentable detail string."""


class AIStreamUnsupported(Exception):
    """Provider/client cannot stream; the caller transparently falls back."""


def _split_keys(raw):
    if not raw:
        return []
    parts = [p.strip() for p in str(raw).replace("\n", ",").split(",")]
    return [p for p in parts if p]


def _extract_reply(data):
    """Pull assistant text out of OpenAI, Anthropic, Gemini and custom shapes."""
    if data is None:
        return None
    if isinstance(data, str):
        return data.strip() or None
    if not isinstance(data, dict):
        return None

    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, list):
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
                if isinstance(value, dict):
                    inner = value.get("content") or value.get("text")
                    if isinstance(inner, str) and inner.strip():
                        return inner.strip()

    content = data.get("content")
    if isinstance(content, list):
        text = "".join(b.get("text", "") for b in content if isinstance(b, dict))
        if text.strip():
            return text.strip()

    candidates = data.get("candidates")
    if isinstance(candidates, list) and candidates:
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        if text.strip():
            return text.strip()

    for key in ("response", "output_text", "answer", "reply", "result", "message", "text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            inner = value.get("content") or value.get("text")
            if isinstance(inner, str) and inner.strip():
                return inner.strip()
    return None


def _extract_delta(data):
    """Extract one text fragment from a streaming SSE event."""
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        first = choices[0]
        delta = first.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
            return delta["content"]
        if isinstance(first.get("text"), str):
            return first["text"]
        message = first.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
    return None


def _extract_usage(data):
    if not isinstance(data, dict):
        return {}
    usage = data.get("usage") or data.get("usageMetadata") or {}
    if not isinstance(usage, dict):
        return {}
    prompt = usage.get("prompt_tokens", usage.get("promptTokenCount", 0)) or 0
    completion = usage.get("completion_tokens", usage.get("candidatesTokenCount", 0)) or 0
    total = usage.get("total_tokens", usage.get("totalTokenCount", 0)) or 0
    try:
        prompt, completion, total = int(prompt), int(completion), int(total)
    except (TypeError, ValueError):
        return {}
    return {"prompt_tokens": prompt, "completion_tokens": completion,
            "total_tokens": total or prompt + completion}


def estimate_tokens(value):
    """Provider-independent fallback when a provider omits usage metadata."""
    if isinstance(value, list):
        total = 0
        for item in value:
            if isinstance(item, dict) and item.get("type") == "image_url":
                total += 1000  # conservative vision-image estimate
            elif isinstance(item, dict):
                total += estimate_tokens(item.get("text", ""))
        return max(1, total)
    text = str(value or "")
    return max(1, (len(text) + 3) // 4)


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


async def _maybe_await(callback, value):
    if callback is None:
        return
    result = callback(value)
    if hasattr(result, "__await__"):
        await result


class AIManager:
    def __init__(self):
        self._history = {}
        self._last_usage = {}
        self._stream_callback = contextvars.ContextVar("ai_stream_callback", default=None)
        self._key_rotation = contextvars.ContextVar("ai_key_rotation", default=True)

    # ------------------------------------------------------------- model access
    @staticmethod
    def _scope_allows(model, scope):
        scope = str(scope or "all").strip()
        if not scope or scope.lower() in ("all", "*"):
            return True
        allowed = {part.strip().lower() for part in scope.replace("\n", ",").split(",") if part.strip()}
        return any(str(model.get(key, "")).lower() in allowed for key in ("id", "name", "model_id"))

    def is_model_allowed(self, user_id, model):
        sub = get_db().get_subscription(user_id)
        if not capability_enabled(user_id, "model_scope"):
            return True
        return self._scope_allows(model, (sub or {}).get("model_scope", "all"))

    def list_models(self, only_active=True, user_id=None):
        models = get_db().get_ai_models(only_active=only_active)
        if user_id is None:
            return models
        sub = get_db().get_subscription(user_id)
        if not capability_enabled(user_id, "model_scope"):
            return models
        scope = (sub or {}).get("model_scope", "all")
        return [m for m in models if self._scope_allows(m, scope)]

    def resolve_model(self, model_pk=None, name=None, user_id=None):
        db = get_db()
        candidates = []
        if model_pk is not None:
            candidates.append(db.get_ai_model(model_pk))
        if name:
            candidates.append(db.get_ai_model_by_name(name))
        configured = db.get_setting("default_ai_model")
        if configured:
            candidates.append(db.get_ai_model_by_name(configured))
        candidates.append(db.get_default_ai_model())
        for model in candidates:
            if model and model.get("status") and (user_id is None or self.is_model_allowed(user_id, model)):
                return model
        return None

    # ---------------------------------------------------------------- history
    def get_history(self, user_id):
        return list(self._history.get(user_id, []))

    def clear_history(self, user_id):
        self._history.pop(user_id, None)

    @staticmethod
    def _history_safe(content):
        if not isinstance(content, list):
            return content
        safe = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "image_url":
                safe.append({"type": "text", "text": "[image attached in a previous turn]"})
            elif isinstance(item.get("text"), str):
                safe.append({"type": "text", "text": item["text"]})
        return safe or "[attachment]"

    def _remember(self, user_id, role, content, max_turns):
        if max_turns <= 0:
            self._history.pop(user_id, None)
            return
        bucket = self._history.setdefault(user_id, [])
        bucket.append((role, self._history_safe(content)))
        limit = max_turns * 2
        if len(bucket) > limit:
            del bucket[: len(bucket) - limit]

    def _build_messages(self, user_id, prompt, system_prompt, max_turns):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if max_turns:
            for role, content in self._history.get(user_id, [])[-max_turns * 2:]:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})
        return messages

    # ------------------------------------------------------------------- calls
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

    def _payload(self, model, messages, stream=False):
        db = get_db()
        payload = {"model": model.get("model_id"), "messages": messages}
        output_tokens = db.get_int_setting("ai_max_output_tokens", 2048)
        if output_tokens > 0:
            payload["max_tokens"] = output_tokens
        if stream:
            payload["stream"] = True
        return payload

    @staticmethod
    def _headers(api_key):
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = "Bearer %s" % api_key
            headers["x-api-key"] = api_key
            headers["api-key"] = api_key
        return headers

    async def _request_standard(self, model, messages, timeout_s, max_retries, session_factory=None,
                                allow_key_rotation=True):
        import aiohttp
        if session_factory is None:
            session_factory = aiohttp.ClientSession
        keys = _split_keys(model.get("api_key")) or [""]
        if not allow_key_rotation:
            keys = keys[:1]
        payload = self._payload(model, messages)
        last_error = "unknown error"
        total_attempts = max(1, max_retries) * len(keys)
        attempt = 0
        for key_index, api_key in enumerate(keys):
            headers = self._headers(api_key)
            for retry in range(max(1, max_retries)):
                attempt += 1
                try:
                    status, data, body_text = await self._post(
                        session_factory, model["api_url"], headers, payload, timeout_s)
                except asyncio.TimeoutError:
                    last_error = "timeout after %ss" % timeout_s
                except aiohttp.ClientError as exc:
                    last_error = "connection error: %s" % str(exc)[:120]
                except Exception as exc:
                    last_error = "%s: %s" % (type(exc).__name__, str(exc)[:120])
                else:
                    if 200 <= status < 300:
                        reply = _extract_reply(data)
                        if reply:
                            self._request_usage = _extract_usage(data)
                            return reply
                        last_error = "provider returned no usable text"
                        break
                    last_error = _extract_error(status, data, body_text)
                    if status in (401, 403) and key_index + 1 < len(keys):
                        logger.warning("AI key #%s rejected, rotating", key_index + 1)
                        break
                    if status not in RETRYABLE_STATUS:
                        break
                if attempt < total_attempts:
                    backoff = min(2 ** retry, 8)
                    logger.info("AI retry %s/%s in %ss (%s)", attempt, total_attempts, backoff, last_error)
                    await asyncio.sleep(backoff)
        raise AIError(last_error)

    async def _request_stream(self, model, messages, timeout_s, max_retries, callback,
                              allow_key_rotation=True):
        """Read OpenAI-compatible SSE and emit deltas as soon as they arrive."""
        import aiohttp
        keys = _split_keys(model.get("api_key")) or [""]
        if not allow_key_rotation:
            keys = keys[:1]
        payload = self._payload(model, messages, stream=True)
        last_error = "unknown error"
        total_attempts = max(1, max_retries) * len(keys)
        attempt = 0
        for key_index, api_key in enumerate(keys):
            for retry in range(max(1, max_retries)):
                attempt += 1
                try:
                    timeout = aiohttp.ClientTimeout(total=timeout_s)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.post(model["api_url"], json=payload,
                                                headers=self._headers(api_key)) as resp:
                            if not (200 <= resp.status < 300):
                                body = await resp.text()
                                data = None
                                try:
                                    data = json.loads(body)
                                except Exception:
                                    pass
                                last_error = _extract_error(resp.status, data, body)
                                if resp.status in (401, 403) and key_index + 1 < len(keys):
                                    break
                                if resp.status not in RETRYABLE_STATUS:
                                    raise AIError(last_error)
                            else:
                                content = getattr(resp, "content", None)
                                if content is None or not hasattr(content, "iter_any"):
                                    raise AIStreamUnsupported()
                                buffer = b""
                                pieces = []
                                usage = {}
                                async for chunk in content.iter_any():
                                    if not chunk:
                                        continue
                                    buffer += chunk
                                    while b"\n" in buffer:
                                        raw, buffer = buffer.split(b"\n", 1)
                                        line = raw.decode("utf-8", errors="ignore").strip()
                                        if not line.startswith("data:"):
                                            continue
                                        payload_text = line[5:].strip()
                                        if payload_text == "[DONE]":
                                            continue
                                        try:
                                            event = json.loads(payload_text)
                                        except json.JSONDecodeError:
                                            continue
                                        usage.update(_extract_usage(event))
                                        delta = _extract_delta(event)
                                        if delta:
                                            pieces.append(delta)
                                            await _maybe_await(callback, delta)
                                        # A provider may ignore stream=true and send JSON.
                                        if not delta and not pieces:
                                            full = _extract_reply(event)
                                            if full:
                                                pieces.append(full)
                                                await _maybe_await(callback, full)
                                if buffer.strip().startswith(b"data:"):
                                    try:
                                        event = json.loads(buffer.split(b":", 1)[1].strip())
                                        usage.update(_extract_usage(event))
                                        delta = _extract_delta(event) or _extract_reply(event)
                                        if delta:
                                            pieces.append(delta)
                                            await _maybe_await(callback, delta)
                                    except Exception:
                                        pass
                                if pieces:
                                    self._request_usage = usage
                                    return "".join(pieces).strip()
                                raise AIStreamUnsupported()
                except AIStreamUnsupported:
                    raise
                except asyncio.TimeoutError:
                    last_error = "timeout after %ss" % timeout_s
                except aiohttp.ClientError as exc:
                    last_error = "connection error: %s" % str(exc)[:120]
                except AIError:
                    raise
                except Exception as exc:
                    last_error = "%s: %s" % (type(exc).__name__, str(exc)[:120])
                if attempt < total_attempts:
                    backoff = min(2 ** retry, 8)
                    await asyncio.sleep(backoff)
        raise AIError(last_error)

    async def _request(self, model, messages, timeout_s, max_retries, session_factory=None,
                       allow_key_rotation=None):
        if allow_key_rotation is None:
            allow_key_rotation = self._key_rotation.get()
        callback = self._stream_callback.get()
        if callback is not None and session_factory is None and get_db().get_bool_setting("ai_streaming", True):
            try:
                return await self._request_stream(model, messages, timeout_s, max_retries, callback,
                                                   allow_key_rotation=allow_key_rotation)
            except AIStreamUnsupported:
                logger.info("Provider did not support streaming; falling back to JSON response")
        return await self._request_standard(model, messages, timeout_s, max_retries, session_factory,
                                             allow_key_rotation=allow_key_rotation)

    async def chat(self, user_id, prompt, model_pk=None, session_factory=None,
                   stream_callback=None, extra_instruction=None):
        db = get_db()
        model = self.resolve_model(model_pk=model_pk, user_id=user_id)
        if not model:
            raise AIError("no active model configured for this subscription")
        timeout_s = db.get_int_setting("ai_timeout_seconds", 45)
        max_retries = db.get_int_setting("ai_max_retries", 3)
        max_turns = db.get_int_setting("ai_max_history", 8)
        max_turns = min(max_turns, int(value_for_user(user_id, "max_history") or 0))
        if not capability_enabled(user_id, "conversation_memory"):
            max_turns = 0
        system_prompt = db.get_setting("ai_system_prompt") or ""
        if extra_instruction:
            system_prompt = (system_prompt + "\n\n" + str(extra_instruction)).strip()
        messages = self._build_messages(user_id, prompt, system_prompt, max_turns)
        started = time.monotonic()
        self._request_usage = {}
        token = self._stream_callback.set(stream_callback)
        rotation_token = self._key_rotation.set(capability_enabled(user_id, "key_rotation"))
        try:
            candidates = [model]
            if capability_enabled(user_id, "provider_fallback"):
                for candidate in self.list_models(user_id=user_id):
                    if candidate["id"] != model["id"]:
                        candidates.append(candidate)
            last_error = None
            for index, candidate in enumerate(candidates):
                self._request_usage = {}
                try:
                    reply = await self._request(candidate, messages, timeout_s, max_retries, session_factory)
                    model = candidate
                    break
                except AIError as exc:
                    last_error = exc
                    db.log_ai_usage(user_id, candidate["name"], ok=False,
                                    input_type="image" if isinstance(prompt, list) else "text")
                    if index + 1 < len(candidates):
                        logger.warning("AI model %s failed; trying fallback model", candidate["name"])
            else:
                raise last_error or AIError("all configured AI models failed")
        finally:
            self._stream_callback.reset(token)
            self._key_rotation.reset(rotation_token)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        usage = dict(self._request_usage or {})
        if not usage:
            usage = {"prompt_tokens": estimate_tokens(prompt),
                     "completion_tokens": estimate_tokens(reply),
                     "total_tokens": estimate_tokens(prompt) + estimate_tokens(reply),
                     "estimated": True}
        self._last_usage[user_id] = usage
        self._remember(user_id, "user", prompt, max_turns)
        self._remember(user_id, "assistant", reply, max_turns)
        db.log_ai_usage(user_id, model["name"], ok=True,
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                        latency_ms=elapsed_ms,
                        input_type="image" if isinstance(prompt, list) else "text")
        logger.info("AI ok user=%s model=%s %sms tokens=%s", user_id, model["name"],
                    elapsed_ms, usage.get("total_tokens", 0))
        return reply, model["name"]

    def last_usage(self, user_id):
        return dict(self._last_usage.get(user_id) or {})

    async def test_connection(self, model_pk, session_factory=None):
        db = get_db()
        model = db.get_ai_model(model_pk)
        if not model:
            return False, "model not found", 0
        timeout_s = db.get_int_setting("ai_timeout_seconds", 45)
        messages = [{"role": "user", "content": "Reply with the single word: OK"}]
        started = time.monotonic()
        try:
            reply = await self._request_standard(model, messages, timeout_s, 1, session_factory)
        except AIError as exc:
            return False, str(exc), int((time.monotonic() - started) * 1000)
        return True, reply[:120], int((time.monotonic() - started) * 1000)


ai_manager = AIManager()
