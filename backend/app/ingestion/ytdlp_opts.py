import os
import shutil
import tempfile
from typing import Dict, Optional

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_RUNTIME_COOKIE_PATH = os.path.join(tempfile.gettempdir(), 'youtube_cookies.txt')


def resolve_youtube_cookies() -> Optional[str]:
    """Return a writable path to a YouTube cookies file, or None.

    Order: YOUTUBE_COOKIES env var (file contents, for hosts without file
    mounts), YOUTUBE_COOKIES_PATH, then youtube_cookies.txt next to the backend.
    yt-dlp writes refreshed cookies back to the file, so the result is always
    a copy in a writable temp location.
    """
    content = os.getenv('YOUTUBE_COOKIES')
    if content and content.strip():
        # Env vars often collapse newlines/tabs; restore them if needed.
        content = content.replace('\\n', '\n').replace('\\t', '\t')
        with open(_RUNTIME_COOKIE_PATH, 'w', encoding='utf-8') as f:
            f.write(content if content.endswith('\n') else content + '\n')
        return _RUNTIME_COOKIE_PATH

    candidates = [
        os.getenv('YOUTUBE_COOKIES_PATH'),
        '/app/youtube_cookies.txt',
        '/etc/secrets/youtube_cookies.txt',
        os.path.join(_BACKEND_DIR, 'youtube_cookies.txt'),
    ]
    for path in candidates:
        if path and os.path.isfile(path) and os.path.getsize(path) > 0:
            shutil.copyfile(path, _RUNTIME_COOKIE_PATH)
            return _RUNTIME_COOKIE_PATH
    return None


def build_ydl_opts(extra: Optional[Dict] = None) -> Dict:
    """Base yt-dlp options shared by metadata and transcript extraction."""
    opts: Dict = {
        'quiet': True,
        'no_warnings': True,
        'remote_components': ['ejs:github'],
    }

    deno = os.getenv('DENO_PATH') or shutil.which('deno') or '/root/.deno/bin/deno'
    if os.path.exists(deno):
        opts['js_runtimes'] = {'deno': {'path': deno}}

    cookies = resolve_youtube_cookies()
    if cookies:
        opts['cookiefile'] = cookies
    else:
        print("WARNING: no YouTube cookies found; YouTube may block this IP as a bot")

    proxy = os.getenv('YTDLP_PROXY')
    if proxy:
        opts['proxy'] = proxy

    if extra:
        opts.update(extra)
    return opts
