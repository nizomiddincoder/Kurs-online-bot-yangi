"""«Sozlash kerak» sahifasi: Railway'da kalit yetishmasa, 502 o'rniga shu sahifa ochiladi.

Xavfsizlik: sahifada faqat o'zgaruvchilar NOMI va bor/yo'qligi ko'rsatiladi, qiymatlari hech qachon.
"""
import html
import logging
from pathlib import Path

from aiohttp import web

from config import Config, REQUIRED_VARS, env_status

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"

HELP = {
    "BOT_TOKEN": "@BotFather bergan token (1234567890:AAH... ko'rinishida)",
    "ADMIN_IDS": "Sizning Telegram ID ingiz — @userinfobot ga yozib bilasiz. Bir nechta bo'lsa vergul bilan",
    "DATABASE_URL": "Aynan shunday yozing: ${{Postgres.DATABASE_URL}}",
    "ADMIN_PANEL_PASSWORD": "Panelga kirish paroli (kamida 12 belgi, harf va raqam)",
}
EXAMPLE = {
    "BOT_TOKEN": "1234567890:AAH...",
    "ADMIN_IDS": "123456789",
    "DATABASE_URL": "${{Postgres.DATABASE_URL}}",
    "ADMIN_PANEL_PASSWORD": "KuchliParol2026",
}
OK_ICON = '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
NO_ICON = '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'


def render(config: Config, reason: str) -> str:
    esc = html.escape
    status, others = env_status()
    rows = "".join(
        f'<div class="sys-line"><span><code>{name}</code></span>'
        f'<span class="pill {"ok" if ok else "bad"}">{OK_ICON if ok else NO_ICON}{"kiritilgan" if ok else "kiritilmagan"}</span></div>'
        f'<div class="help" style="margin:-6px 0 6px">{esc(HELP[name])}</div>'
        for name, ok in status.items()
    )
    missing = [n for n in REQUIRED_VARS if not status[n]]
    block = "\n".join(f"{n}={EXAMPLE[n]}" for n in (missing or REQUIRED_VARS))
    problems = "".join(f"<li>{esc(p)}</li>" for p in config.fatal + config.warnings)
    others_html = (
        f'<div class="fmsg"><div class="field-warn">{NO_ICON}<span>Railway\'da shunga o\'xshash, lekin boshqacha '
        f'yozilgan nom bor: <code>{esc(", ".join(others[:10]))}</code>. Nomni yuqoridagidek aniq yozing '
        f'(katta harflar, pastki chiziq bilan).</span></div></div>'
        if others else ""
    )
    return f"""<!doctype html>
<html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>AZAPRO — sozlash kerak</title>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/static/app.css">
<meta http-equiv="refresh" content="30">
</head><body>
<header class="topbar"><div class="brand"><img src="/static/favicon.svg" alt="">AZAPRO</div></header>
<main><div class="settings">
  <div class="page-head"><div>
    <div class="eyebrow">Bir marta sozlanadi</div>
    <h1>Sozlash kerak</h1>
    <p>{esc(reason)}</p>
  </div></div>

  <div class="card section">
    <h3>Nima yetishmayapti</h3>
    <ul style="margin:0;padding-left:18px">{problems}</ul>
  </div>

  <div class="card section">
    <h3>Railway Variables holati</h3>
    {rows}
    {others_html}
  </div>

  <div class="card dark section">
    <h3 style="color:var(--on-dark)">Qanday tuzataman?</h3>
    <ol style="color:var(--on-dark-muted);padding-left:18px;margin:0 0 14px">
      <li>Railway'da <b style="color:var(--on-dark)">bot servisini</b> bosing (Postgres blokini emas!).</li>
      <li><b style="color:var(--on-dark)">Variables → Raw Editor</b> ni oching.</li>
      <li>Quyidagi qatorlarni qo'shing va o'z qiymatlaringizni yozing (qo'shtirnoqsiz):</li>
    </ol>
    <pre style="background:var(--dark-2);color:var(--sage);padding:14px;border-radius:12px;overflow-x:auto;margin:0 0 14px">{esc(block)}</pre>
    <ol start="4" style="color:var(--on-dark-muted);padding-left:18px;margin:0">
      <li><b style="color:var(--on-dark)">Update Variables</b>, so'ng yuqorida chiqadigan <b style="color:var(--on-dark)">Deploy</b> tugmasini bosing.</li>
      <li>1–2 daqiqa kuting — bu sahifa o'zi yangilanadi va panel ochiladi.</li>
    </ol>
  </div>
</div></main>
</body></html>"""


def create_setup_app(config: Config, reason: str) -> web.Application:
    app = web.Application()

    async def page(request: web.Request) -> web.Response:
        return web.Response(text=render(config, reason), content_type="text/html", headers={"Cache-Control": "no-store"})

    async def health(request: web.Request) -> web.Response:
        return web.json_response({"ok": False, "mode": "setup"})

    app.router.add_static("/static", STATIC)
    app.router.add_get("/health", health)
    app.router.add_get("/{tail:.*}", page)
    return app


async def start_setup_web(config: Config, reason: str) -> web.AppRunner:
    runner = web.AppRunner(create_setup_app(config, reason), access_log=None)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", config.web_port).start()
    log.warning("«Sozlash kerak» sahifasi ochildi (port %s): %s", config.web_port, reason)
    return runner
