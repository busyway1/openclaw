"""
Web page fetching and search tools.

Reference: openclaw web-fetch.ts, web-search.ts patterns
- TTL-based caching
- SSRF protection
- Content extraction
"""

from langchain_core.tools import tool
from urllib.parse import urlparse
import time
import re
import ipaddress
from typing import Optional

# Cache configuration (openclaw pattern)
_fetch_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

# Limits
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
DEFAULT_MAX_CHARS = 50000
MAX_SEARCH_RESULTS = 10

# SSRF protection: blocked hosts/IPs
BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "[::1]",
}

BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),      # Private
    ipaddress.ip_network("172.16.0.0/12"),   # Private
    ipaddress.ip_network("192.168.0.0/16"),  # Private
    ipaddress.ip_network("127.0.0.0/8"),     # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
]


def _is_ssrf_blocked(url: str) -> bool:
    """Check if URL is blocked for SSRF protection."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""

        # Check blocked hosts
        if host.lower() in BLOCKED_HOSTS:
            return True

        # Check if host is an IP address in blocked ranges
        try:
            ip = ipaddress.ip_address(host)
            for network in BLOCKED_IP_RANGES:
                if ip in network:
                    return True
        except ValueError:
            pass  # Not an IP address, continue

        return False
    except Exception:
        return True  # Block on parse error


def _get_cached(url: str) -> Optional[str]:
    """Get cached content if valid."""
    if url in _fetch_cache:
        content, timestamp = _fetch_cache[url]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            return content
        else:
            del _fetch_cache[url]
    return None


def _set_cache(url: str, content: str) -> None:
    """Cache content with timestamp."""
    _fetch_cache[url] = (content, time.time())


def _extract_text(html: str) -> str:
    """Extract readable text from HTML (BeautifulSoup)."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe", "form"]):
            tag.decompose()

        # Get text
        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # Remove excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text

    except ImportError:
        # Fallback: basic regex extraction
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def _get_title(html: str) -> str:
    """Extract page title from HTML."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else "(no title)"
    except Exception:
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        return match.group(1).strip() if match else "(no title)"


@tool
def fetch_webpage(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """
    Fetch a webpage and return its text content.

    Args:
        url: The URL to fetch
        max_chars: Maximum characters to return (default: 50,000)

    Returns:
        Page title, URL, and extracted text content

    Examples:
        - fetch_webpage("https://python.org")
        - fetch_webpage("https://docs.langchain.com", max_chars=100000)

    Security:
        - SSRF protection blocks localhost and internal IPs
        - 5-minute cache prevents excessive requests
    """
    try:
        import requests

        # Validate URL
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # SSRF protection
        if _is_ssrf_blocked(url):
            return f"Error: URL blocked for security reasons (internal/private address): {url}"

        # Check cache
        cached = _get_cached(url)
        if cached:
            return f"(cached)\n\n{cached}"

        # Fetch
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=30,
            allow_redirects=True,
            stream=True,
        )
        response.raise_for_status()

        # Check content length
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > MAX_CONTENT_LENGTH:
            return f"Error: Page too large ({int(content_length) // 1024 // 1024}MB). Maximum: 5MB"

        # Get content
        html = response.text[:MAX_CONTENT_LENGTH]

        # Extract title and text
        title = _get_title(html)
        text = _extract_text(html)

        # Truncate if needed
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n... (truncated at {max_chars} characters)"

        # Format result
        result = f"Title: {title}\nURL: {response.url}\n\n{text}"

        # Cache result
        _set_cache(url, result)

        return result

    except ImportError:
        return "Error: 'requests' library not installed. Run: pip install requests beautifulsoup4"
    except requests.exceptions.Timeout:
        return f"Error: Request timed out for: {url}"
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to: {url}"
    except requests.exceptions.HTTPError as e:
        return f"Error: HTTP {e.response.status_code} for: {url}"
    except Exception as e:
        return f"Error fetching webpage: {type(e).__name__}: {str(e)}"


@tool
def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo and return results.

    Args:
        query: Search query
        num_results: Number of results (1-10, default: 5)

    Returns:
        Formatted search results with titles, URLs, and snippets

    Examples:
        - web_search("Python LangChain tutorial")
        - web_search("PWC AI consulting", num_results=10)

    Note:
        Uses DuckDuckGo (no API key required)
    """
    try:
        from duckduckgo_search import DDGS

        # Validate num_results
        num_results = max(1, min(num_results, MAX_SEARCH_RESULTS))

        # Search
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))

        if not results:
            return f"No results found for: {query}"

        # Format results
        output = [f"Search results for: {query}\n"]

        for i, result in enumerate(results, 1):
            title = result.get("title", "(no title)")
            url = result.get("href", result.get("link", "(no url)"))
            snippet = result.get("body", result.get("snippet", "(no description)"))

            output.append(f"{i}. {title}")
            output.append(f"   URL: {url}")
            output.append(f"   {snippet}")
            output.append("")

        return "\n".join(output)

    except ImportError:
        return "Error: 'duckduckgo-search' library not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"Error searching: {type(e).__name__}: {str(e)}"


@tool
def clear_web_cache() -> str:
    """
    Clear the webpage fetch cache.

    Returns:
        Number of cached entries cleared
    """
    count = len(_fetch_cache)
    _fetch_cache.clear()
    return f"Cleared {count} cached entries"
