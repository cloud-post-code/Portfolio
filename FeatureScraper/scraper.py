"""
scraper.py — fetch a URL and extract a rich structural summary for LLM analysis.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

from models import DataTable, Form, FormField, NavItem, PageStructure

_TIMEOUT = 20
_USER_AGENT = "Mozilla/5.0 (compatible; FeatureScraper/1.0)"

# Libraries whose CDN / npm names hint at tech stack
_LIB_HINTS: dict[str, str] = {
    "react": "React",
    "vue": "Vue.js",
    "angular": "Angular",
    "svelte": "Svelte",
    "next": "Next.js",
    "nuxt": "Nuxt.js",
    "stripe": "Stripe",
    "maps.googleapis": "Google Maps",
    "mapbox": "Mapbox",
    "firebase": "Firebase",
    "supabase": "Supabase",
    "auth0": "Auth0",
    "clerk": "Clerk",
    "sentry": "Sentry",
    "intercom": "Intercom",
    "segment": "Segment",
    "gtag": "Google Analytics",
    "analytics": "Analytics",
    "chartjs": "Chart.js",
    "d3": "D3.js",
    "recaptcha": "reCAPTCHA",
    "paypal": "PayPal",
    "socket.io": "WebSockets (socket.io)",
    "pusher": "Pusher/WebSockets",
    "algolia": "Algolia Search",
    "typeform": "Typeform",
    "hubspot": "HubSpot",
    "shopify": "Shopify",
    "wordpress": "WordPress",
    "wix": "Wix",
    "webflow": "Webflow",
}


def scrape(url: str) -> PageStructure:
    """Fetch *url* and return a structured summary of its features."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    resp = requests.get(
        url,
        timeout=_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
        allow_redirects=True,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title = _get_title(soup)
    meta_desc = _get_meta_description(soup)
    nav_items = _extract_nav(soup)
    forms = _extract_forms(soup)
    buttons = _extract_buttons(soup)
    tables = _extract_tables(soup)
    list_headings = _extract_list_headings(soup)
    external_scripts = _extract_scripts(resp.text)
    json_ld_types = _extract_json_ld_types(soup)
    visible_text = _extract_visible_text(soup)

    return PageStructure(
        url=url,
        title=title,
        meta_description=meta_desc,
        nav_items=nav_items,
        forms=forms,
        buttons=buttons,
        tables=tables,
        list_headings=list_headings,
        external_scripts=external_scripts,
        json_ld_types=json_ld_types,
        visible_text_snippet=visible_text[:4_000],
    )


def to_llm_text(ps: PageStructure) -> str:
    """Render a PageStructure as compact human-readable text for the LLM prompt."""
    lines: list[str] = [
        f"URL: {ps.url}",
        f"Title: {ps.title}",
        f"Meta description: {ps.meta_description or '(none)'}",
        "",
    ]

    if ps.nav_items:
        lines.append("## Navigation")
        for n in ps.nav_items:
            indent = "  " * n.depth
            lines.append(f"{indent}- [{n.text}]({n.href})")
        lines.append("")

    if ps.forms:
        lines.append("## Forms")
        for i, f in enumerate(ps.forms, 1):
            lines.append(
                f"Form {i}: action={f.action or '(self)'} method={f.method} hint={f.purpose_hint}"
            )
            lines.append(f"  Submit: {f.submit_text or '(unknown)'}")
            for ff in f.fields:
                req = " [required]" if ff.required else ""
                label = f" label='{ff.label}'" if ff.label else ""
                ph = f" placeholder='{ff.placeholder}'" if ff.placeholder else ""
                lines.append(f"  {ff.tag}[{ff.input_type}] name={ff.name}{label}{ph}{req}")
        lines.append("")

    if ps.buttons:
        lines.append("## Buttons / CTAs")
        lines.append(", ".join(ps.buttons[:30]))
        lines.append("")

    if ps.tables:
        lines.append("## Data Tables")
        for i, t in enumerate(ps.tables, 1):
            lines.append(f"Table {i} headers: {', '.join(t.headers)}")
            for row in t.sample_rows[:1]:
                lines.append(f"  Sample row: {', '.join(str(c) for c in row[:6])}")
        lines.append("")

    if ps.list_headings:
        lines.append("## List / Section Headings")
        lines.append(", ".join(ps.list_headings[:20]))
        lines.append("")

    if ps.external_scripts:
        lines.append("## Detected Libraries / Services")
        lines.append(", ".join(ps.external_scripts))
        lines.append("")

    if ps.json_ld_types:
        lines.append("## Structured Data Types (JSON-LD)")
        lines.append(", ".join(ps.json_ld_types))
        lines.append("")

    lines.append("## Visible Text Snippet")
    lines.append(ps.visible_text_snippet)

    return "\n".join(lines)


# ── Private helpers ─────────────────────────────────────────────────────────────

def _get_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else ""


def _get_meta_description(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    if tag and isinstance(tag, Tag):
        return tag.get("content", "").strip()
    tag = soup.find("meta", property="og:description")
    if tag and isinstance(tag, Tag):
        return tag.get("content", "").strip()
    return ""


def _extract_nav(soup: BeautifulSoup) -> list[NavItem]:
    """Pull nav links from <nav>, <header>, or roles=navigation."""
    items: list[NavItem] = []
    seen: set[str] = set()

    containers = soup.find_all(["nav", "header"]) or [soup]
    for container in containers:
        for a in container.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"].strip()
            if not text or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            key = (text.lower(), href)
            if key in seen:
                continue
            seen.add(key)
            # rough depth: if inside a dropdown/submenu
            depth = 1 if a.find_parent(class_=re.compile(r"sub|drop|child|nested", re.I)) else 0
            items.append(NavItem(text=text, href=href, depth=depth))
            if len(items) >= 40:
                break
        if len(items) >= 40:
            break

    return items


def _extract_forms(soup: BeautifulSoup) -> list[Form]:
    forms: list[Form] = []
    for form_tag in soup.find_all("form"):
        action = form_tag.get("action", "").strip()
        method = form_tag.get("method", "get").upper()
        fields: list[FormField] = []

        for el in form_tag.find_all(["input", "select", "textarea"]):
            if not isinstance(el, Tag):
                continue
            tag_name = el.name
            input_type = el.get("type", "text") if tag_name == "input" else tag_name
            if input_type in ("hidden", "submit", "button", "reset", "image"):
                continue
            name = el.get("name", el.get("id", "")).strip()
            placeholder = el.get("placeholder", "").strip()
            required = el.has_attr("required") or el.get("aria-required") == "true"

            # Try to find associated label
            label_text = ""
            el_id = el.get("id")
            if el_id:
                lbl = soup.find("label", attrs={"for": el_id})
                if lbl:
                    label_text = lbl.get_text(strip=True)
            if not label_text:
                parent_lbl = el.find_parent("label")
                if parent_lbl:
                    label_text = parent_lbl.get_text(strip=True).replace(
                        el.get_text(strip=True), ""
                    ).strip()

            fields.append(
                FormField(
                    tag=tag_name,
                    input_type=str(input_type),
                    name=name,
                    placeholder=placeholder,
                    label=label_text,
                    required=required,
                )
            )

        # Guess form purpose from action URL, id, class, or nearby heading
        form_id = form_tag.get("id", "") + " " + " ".join(form_tag.get("class", []))
        purpose_hint = _guess_form_purpose(action, form_id, fields)

        # Find submit button text
        submit_text = ""
        for btn in form_tag.find_all(["button", "input"]):
            btype = btn.get("type", "submit")
            if btype in ("submit", "button"):
                submit_text = btn.get_text(strip=True) or btn.get("value", "")
                if submit_text:
                    break

        forms.append(
            Form(
                action=action,
                method=method,
                purpose_hint=purpose_hint,
                fields=fields,
                submit_text=submit_text,
            )
        )

    return forms


def _guess_form_purpose(action: str, class_id: str, fields: list[FormField]) -> str:
    combined = (action + " " + class_id).lower()
    field_names = " ".join(f.name + " " + f.placeholder + " " + f.label for f in fields).lower()
    everything = combined + " " + field_names

    checks = [
        (["login", "signin", "sign-in", "log-in"], "login"),
        (["register", "signup", "sign-up", "create-account", "create_account"], "registration"),
        (["forgot", "reset-password", "reset_password"], "password reset"),
        (["search", "query", "q="], "search"),
        (["contact", "message", "inquiry", "enquiry"], "contact"),
        (["subscribe", "newsletter", "email"], "newsletter/subscribe"),
        (["checkout", "payment", "billing", "order"], "checkout/payment"),
        (["profile", "account", "settings", "preferences"], "profile/settings"),
        (["review", "rating", "comment", "feedback"], "review/feedback"),
        (["upload", "import", "file"], "file upload"),
        (["invite", "referral"], "invite/referral"),
    ]
    for keywords, label in checks:
        if any(kw in everything for kw in keywords):
            return label
    return "general"


def _extract_buttons(soup: BeautifulSoup) -> list[str]:
    texts: list[str] = []
    seen: set[str] = set()
    for el in soup.find_all(["button", "a"]):
        if el.name == "a":
            cls = " ".join(el.get("class", []))
            if not re.search(r"btn|button|cta", cls, re.I):
                continue
        text = el.get_text(strip=True)
        if text and text.lower() not in seen and len(text) <= 60:
            seen.add(text.lower())
            texts.append(text)
    return texts[:40]


def _extract_tables(soup: BeautifulSoup) -> list[DataTable]:
    tables: list[DataTable] = []
    for tbl in soup.find_all("table"):
        headers: list[str] = []
        for th in tbl.find_all("th"):
            h = th.get_text(strip=True)
            if h:
                headers.append(h)
        if not headers:
            continue
        sample_rows: list[list[str]] = []
        for tr in tbl.find_all("tr")[1:3]:
            row = [td.get_text(strip=True) for td in tr.find_all("td")]
            if row:
                sample_rows.append(row)
        tables.append(DataTable(headers=headers, sample_rows=sample_rows))
    return tables


def _extract_list_headings(soup: BeautifulSoup) -> list[str]:
    """Collect headings that precede lists — often hints about feature sections."""
    headings: list[str] = []
    seen: set[str] = set()
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = tag.get_text(strip=True)
        if not text or text.lower() in seen or len(text) > 100:
            continue
        # check if followed soon by ul/ol or if it's inside a section with lists
        sibling = tag.find_next_sibling()
        if sibling and sibling.name in ("ul", "ol", "div", "section"):
            seen.add(text.lower())
            headings.append(text)
    return headings[:30]


def _extract_scripts(html: str) -> list[str]:
    """Detect known libraries from <script src=...> and inline script bodies."""
    found: set[str] = set()
    src_re = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)
    for src in src_re.findall(html):
        src_lower = src.lower()
        for key, label in _LIB_HINTS.items():
            if key in src_lower and label not in found:
                found.add(label)

    # Also scan inline scripts for telltale globals
    inline_re = re.compile(r"window\.__([A-Z_]+)|[\"'](gtag|fbq|_hsq|mixpanel|amplitude)[\"']")
    for m in inline_re.finditer(html):
        token = (m.group(1) or m.group(2) or "").lower()
        for key, label in _LIB_HINTS.items():
            if key in token and label not in found:
                found.add(label)

    return sorted(found)


def _extract_json_ld_types(soup: BeautifulSoup) -> list[str]:
    types: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict):
                t = data.get("@type")
                if t:
                    types.append(t if isinstance(t, str) else str(t))
            elif isinstance(data, list):
                for item in data:
                    t = item.get("@type") if isinstance(item, dict) else None
                    if t:
                        types.append(t if isinstance(t, str) else str(t))
        except (json.JSONDecodeError, AttributeError):
            pass
    return list(set(types))


def _extract_visible_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "svg", "head"]):
        tag.decompose()
    return re.sub(r"\s{2,}", " ", soup.get_text(separator=" ")).strip()
