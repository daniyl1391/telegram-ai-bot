"""Small keyless web-search/fetch service for research-style AI tools.

DuckDuckGo's HTML endpoint is used so the bot needs no additional search API
key. Results are treated as untrusted context: they are quoted into the model
prompt, never executed as instructions.
"""
import asyncio
import html
import re
from html.parser import HTMLParser
from urllib.parse import quote_plus, unquote, urljoin, urlparse

import aiohttp


class WebSearchError(Exception):
    pass


class _ResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self._current = None
        self._capture = None
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            self._current = {"title": "", "url": attrs.get("href") or "", "snippet": ""}
            self._capture = "title"
            self._buffer = []
        elif self._current and ("result__snippet" in classes or "result__snippet" in (attrs.get("class") or "")):
            self._capture = "snippet"
            self._buffer = []

    def handle_data(self, data):
        if self._current and self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag):
        if not self._current:
            return
        if self._capture == "title" and tag == "a":
            self._current["title"] = " ".join("".join(self._buffer).split())
            self._capture = None
        elif self._capture == "snippet" and tag in ("a", "div"):
            self._current["snippet"] = " ".join("".join(self._buffer).split())
            self._capture = None
        if self._current.get("title") and self._current.get("url") and self._current.get("snippet"):
            self.results.append(self._current)
            self._current = None
            self._capture = None
            self._buffer = []


def _clean_url(raw):
    raw = html.unescape(raw or "")
    if raw.startswith("//"):
        raw = "https:" + raw
    # DuckDuckGo redirects often contain uddg=<encoded destination>.
    parsed = urlparse(raw)
    if "duckduckgo.com" in parsed.netloc and parsed.query:
        from urllib.parse import parse_qs
        destination = parse_qs(parsed.query).get("uddg", [""])[0]
        if destination:
            raw = unquote(destination)
    return raw


async def search(query, limit=5, timeout_seconds=12):
    query = " ".join(str(query or "").split()).strip()
    if not query:
        raise WebSearchError("empty search query")
    url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query[:500])
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AI-Telegram-Research/1.0)"}
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise WebSearchError("search provider returned HTTP %s" % response.status)
                body = await response.text(errors="ignore")
    except asyncio.TimeoutError as exc:
        raise WebSearchError("search timed out") from exc
    except aiohttp.ClientError as exc:
        raise WebSearchError("search connection failed") from exc

    parser = _ResultParser()
    parser.feed(body)
    results = []
    seen = set()
    for item in parser.results:
        item["url"] = _clean_url(item["url"])
        if not item["url"].startswith(("http://", "https://")) or item["url"] in seen:
            continue
        seen.add(item["url"])
        results.append(item)
        if len(results) >= max(1, min(int(limit), 10)):
            break
    return results


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            value = " ".join(data.split())
            if value:
                self.parts.append(value)


async def fetch_text(url, max_chars=12000, timeout_seconds=15):
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise WebSearchError("only public http/https URLs are supported")
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AI-Telegram-Research/1.0)"}
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(str(url), allow_redirects=True) as response:
                if response.status >= 400:
                    raise WebSearchError("URL returned HTTP %s" % response.status)
                content_type = response.headers.get("content-type", "")
                if not any(kind in content_type for kind in ("text/", "html", "json", "xml")):
                    raise WebSearchError("URL is not a readable text page")
                body = await response.text(errors="ignore")
    except asyncio.TimeoutError as exc:
        raise WebSearchError("URL fetch timed out") from exc
    except aiohttp.ClientError as exc:
        raise WebSearchError("URL fetch connection failed") from exc
    parser = _TextParser()
    parser.feed(body)
    text = " ".join(parser.parts)
    return text[:max_chars] + ("\n[page truncated]" if len(text) > max_chars else "")


def format_sources(results):
    if not results:
        return "No reliable search results were returned. Say clearly that browsing found nothing."
    lines = []
    for index, item in enumerate(results, 1):
        lines.append("[%s] %s\nURL: %s\nSnippet: %s" % (
            index, item.get("title", "Untitled"), item.get("url", ""), item.get("snippet", "")))
    return "\n\n".join(lines)
