"""Web-muharrir HTML'ini Telegram qabul qiladigan HTML'ga aylantirish (xavfsiz)."""
import html
import re
from html.parser import HTMLParser

TAG_MAP = {
    "b": "b", "strong": "b", "i": "i", "em": "i", "u": "u", "ins": "u",
    "s": "s", "strike": "s", "del": "s", "code": "code", "pre": "pre",
    "blockquote": "blockquote", "a": "a", "tg-spoiler": "tg-spoiler",
}
BLOCK_TAGS = {"div", "p", "li", "h1", "h2", "h3", "h4", "h5", "h6"}
SAFE_URL = re.compile(r"^(https?://|tg://|mailto:)", re.I)


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[str | None] = []  # har bir ochilgan teg uchun: chiqarilgan teg yoki None

    def _newline(self):
        text = "".join(self.out)
        if text and not text.endswith("\n"):
            self.out.append("\n")

    skip = 0  # <script>/<style> ichidagi matn tashlab yuboriladi

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
            return
        attrs = dict(attrs)
        if tag == "br":
            self.out.append("\n")
            return
        if tag in BLOCK_TAGS:
            self._newline()
            self.stack.append(None)
            return
        if tag == "span" and "tg-spoiler" in (attrs.get("class") or ""):
            tag = "tg-spoiler"
        out = TAG_MAP.get(tag)
        if out == "a":
            href = (attrs.get("href") or "").strip()
            if not SAFE_URL.match(href):
                out = None
            else:
                self.out.append(f'<a href="{html.escape(href, quote=True)}">')
                self.stack.append("a")
                return
        if out:
            if out == "blockquote":
                self._newline()
            self.out.append(f"<{out}>")
        self.stack.append(out)

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
            return
        if tag == "br" or not self.stack:
            return
        out = self.stack.pop()
        if out:
            self.out.append(f"</{out}>")
            if out == "blockquote":
                self.out.append("\n")
        elif tag in BLOCK_TAGS:
            self._newline()

    def handle_data(self, data):
        if self.skip:
            return
        self.out.append(html.escape(data.replace(" ", " "), quote=False))

    def result(self) -> str:
        while self.stack:
            out = self.stack.pop()
            if out:
                self.out.append(f"</{out}>")
        text = "".join(self.out)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip("\n ")


def sanitize(raw_html: str) -> str:
    parser = _Sanitizer()
    parser.feed(raw_html or "")
    parser.close()
    return parser.result()


def plain_length(tg_html: str) -> int:
    """Telegram limitlari (caption 1024, matn 4096) teglarsiz hisoblanadi."""
    return len(html.unescape(re.sub(r"<[^>]+>", "", tg_html)))
