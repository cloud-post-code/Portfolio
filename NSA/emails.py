import re

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
)

_JUNK_DOMAINS = frozenset(
    {
        "example.com", "yourdomain.com", "domain.com", "email.com",
        "sentry.io", "wix.com", "wordpress.com", "squarespace.com",
        "shopify.com", "webflow.io",
    }
)

_JUNK_PREFIXES = frozenset(
    {
        "noreply", "no-reply", "donotreply", "do-not-reply",
        "unsubscribe", "bounce", "mailer-daemon",
    }
)

# Matches US/international phone numbers in common formats
_PHONE_RE = re.compile(
    r"(?<!\d)"                          # not preceded by a digit
    r"(?:\+?1[\s\-.]?)?"               # optional country code +1
    r"(?:\(?\d{3}\)?[\s\-.]?)"         # area code
    r"\d{3}[\s\-.]?\d{4}"              # local number
    r"(?!\d)",                          # not followed by a digit
)

_JUNK_PHONE_PATTERNS = re.compile(
    r"^(?:000|111|123|555|800|888|900|999)"
)


def extract_emails(text: str) -> list[str]:
    found: set[str] = set()
    for match in _EMAIL_RE.finditer(text):
        email = match.group(0).lower()
        local, domain = email.split("@", 1)
        if domain in _JUNK_DOMAINS:
            continue
        if local in _JUNK_PREFIXES:
            continue
        if re.search(r"\.(png|jpe?g|gif|svg|webp|css|js)$", email):
            continue
        found.add(email)
    return sorted(found)


def extract_phones(text: str) -> list[str]:
    found: set[str] = set()
    for match in _PHONE_RE.finditer(text):
        raw = match.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        # Discard if too short / too long or starts with junk pattern
        if len(digits) < 10 or len(digits) > 11:
            continue
        local = digits[-10:]
        if _JUNK_PHONE_PATTERNS.match(local):
            continue
        # Normalise to (XXX) XXX-XXXX
        normalised = f"({local[0:3]}) {local[3:6]}-{local[6:10]}"
        found.add(normalised)
    return sorted(found)
