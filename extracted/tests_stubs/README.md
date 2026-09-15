# tests_stubs

Minimal stand-ins for `telegram` and `aiohttp`, used **only** by `tests.py` and
**only** when the real packages are not installed (e.g. a bare CI container
without network access). If the real libraries are importable, they win and these
files are never touched. Nothing in `bot/` or `main.py` imports from here.
