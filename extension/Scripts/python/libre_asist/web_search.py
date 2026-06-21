"""Web search backends for the AI assistant.

Default backend: DuckDuckGo HTML endpoint (no API key required, stdlib only).
Returns a list of {"title", "url", "snippet"} dicts.

    from web_search import search
    results = search("precio del dolar hoy", max_results=5, timeout=15)
"""

import re
import urllib.parse
import urllib.request


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

RESULT_RE = re.compile(
    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>'
    r'.*?'
    r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)
TAG_RE = re.compile(r"<[^>]+>")
ENTITY_RE = re.compile(r"&(amp|lt|gt|quot|apos|#39|#x27);")
ENTITY_MAP = {
    "amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'",
    "#39": "'", "#x27": "'",
}


def _decode_ddg_url(href):
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    if "uddg=" in href:
        m = re.search(r"uddg=([^&]+)", href)
        if m:
            return urllib.parse.unquote(m.group(1))
    return href


def _strip_tags(html):
    text = TAG_RE.sub(" ", html)
    text = ENTITY_RE.sub(lambda m: ENTITY_MAP.get(m.group(1), m.group(0)), text)
    return re.sub(r"\s+", " ", text).strip()


def search(query, max_results=5, timeout=15):
    """Search DuckDuckGo HTML and return up to max_results items.

    Each item is {"title": str, "url": str, "snippet": str}.
    On failure returns an empty list; errors are not raised to the caller
    so the AI model can fall back to its own knowledge.
    """
    if not query or not query.strip():
        return []
    q = urllib.parse.quote_plus(query.strip())
    url = "https://html.duckduckgo.com/html/?q=" + q
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    results = []
    for href, title_html, snippet_html in RESULT_RE.findall(html):
        if "ad_domain=" in href:
            continue
        url_real = _decode_ddg_url(href)
        if not url_real or not url_real.startswith("http"):
            continue
        if "duckduckgo.com" in url_real:
            continue
        results.append({
            "title": _strip_tags(title_html),
            "url": url_real,
            "snippet": _strip_tags(snippet_html),
        })
        if len(results) >= max_results:
            break
    return results


def format_results(results):
    """Format results into a plain-text block for the model."""
    if not results:
        return "No se encontraron resultados."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append("[" + str(i) + "] " + r.get("title", ""))
        lines.append("    URL: " + r.get("url", ""))
        snip = r.get("snippet", "")
        if snip:
            lines.append("    " + snip)
        lines.append("")
    return "\n".join(lines).strip()


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "python language"
    out = search(q, max_results=5, timeout=15)
    print(format_results(out))
