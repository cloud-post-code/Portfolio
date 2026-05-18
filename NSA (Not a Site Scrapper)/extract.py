from bs4 import BeautifulSoup, NavigableString, Tag

_SKIP_TAGS = {"script", "style", "noscript", "head", "meta", "link", "iframe"}
_BLOCK_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "td", "th", "div", "section", "article",
    "blockquote", "pre", "footer", "header", "nav", "aside",
}


def extract_text(soup: BeautifulSoup) -> str:
    lines: list[str] = []

    def _walk(node: Tag | NavigableString) -> None:
        if isinstance(node, NavigableString):
            text = node.strip()
            if text:
                lines.append(text)
            return
        if node.name in _SKIP_TAGS:
            return
        if node.name in _BLOCK_TAGS and lines and lines[-1] != "":
            lines.append("")
        for child in node.children:
            _walk(child)
        if node.name in _BLOCK_TAGS:
            lines.append("")

    _walk(soup)

    merged: list[str] = []
    prev_blank = False
    for line in lines:
        if line == "":
            if not prev_blank:
                merged.append("")
            prev_blank = True
        else:
            merged.append(line)
            prev_blank = False

    return "\n".join(merged).strip()
