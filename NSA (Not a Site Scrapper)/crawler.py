import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from emails import extract_emails, extract_phones
from extract import extract_text
from models import CrawledPage, CrawlResult

_TIMEOUT = 10
_MAX_PAGES = 12
_USER_AGENT = (
    "Mozilla/5.0 (compatible; NotASiteScrapper/1.0; +https://github.com/local)"
)
_PRIORITY_PATH_FRAGMENTS = (
    "about", "team", "company", "services", "products", "solutions",
    "contact", "pricing", "mission", "vision", "story", "who-we-are",
)
_ABOUT_FRAGMENTS = ("about", "company", "mission", "vision", "story", "who-we-are")

_SKIP_EXTENSIONS = re.compile(
    r"\.(pdf|docx?|xlsx?|pptx?|zip|tar|gz|png|jpe?g|gif|svg|webp|mp4|mp3|woff2?)$",
    re.IGNORECASE,
)


def _same_domain(base: str, url: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc


def _priority_score(url: str) -> int:
    path = urlparse(url).path.lower()
    for i, frag in enumerate(_PRIORITY_PATH_FRAGMENTS):
        if frag in path:
            return len(_PRIORITY_PATH_FRAGMENTS) - i
    return 0


def _normalise(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(fragment="", query="").geturl().rstrip("/")


def _is_about_page(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(frag in path for frag in _ABOUT_FRAGMENTS)


def _discover_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    links = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        full = _normalise(urljoin(base_url, href))
        if _same_domain(base_url, full) and not _SKIP_EXTENSIONS.search(full):
            links.add(full)
    return list(links)


def crawl(url: str, *, max_pages: int = _MAX_PAGES) -> CrawlResult:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    result = CrawlResult(base_url=url)
    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT

    visited: set[str] = set()
    queue: list[str] = [_normalise(url)]
    all_emails: set[str] = set()
    all_phones: set[str] = set()

    while queue and len(result.pages) < max_pages:
        queue.sort(key=_priority_score, reverse=True)
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        try:
            resp = session.get(current, timeout=_TIMEOUT, allow_redirects=True)
            status = resp.status_code
            if status != 200:
                result.errors.append(f"{current} → HTTP {status}")
                continue

            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            text = extract_text(soup)
            emails = extract_emails(resp.text)
            phones = extract_phones(resp.text)
            all_emails.update(emails)
            all_phones.update(phones)

            result.pages.append(
                CrawledPage(
                    url=current,
                    title=title,
                    raw_html=resp.text,
                    text=text,
                    status_code=status,
                )
            )

            # Capture first about-type page found
            if not result.about_url and _is_about_page(current):
                result.about_url = current
                result.about_text = text

            for link in _discover_links(soup, current):
                if link not in visited and link not in queue:
                    queue.append(link)

        except Exception as exc:
            result.errors.append(f"{current} → {exc}")

    result.emails = sorted(all_emails)
    result.phones = sorted(all_phones)
    return result
