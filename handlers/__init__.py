from aiogram import Router


def get_routers() -> list[Router]:
    # Tartib muhim: yuqoridagi router birinchi tekshiriladi
    from handlers import (
        admin, admin_payments, admin_settings, chat_ids, common, errors, fallback, join_requests, menu, payment, start,
        support, webinar,
    )

    return [
        errors.router,
        common.router,         # «Bekor qilish» har doim ishlaydi
        chat_ids.router,       # kanal ID sini bilish (forward)
        webinar.router,        # kod so'z, taklif, /stats /broadcast /export /hot
        start.router,          # ro'yxatdan o'tish
        menu.router,           # menyu tugmalari (joriy holatni tozalaydi)
        support.router,        # admin bilan bog'lanish, AI agent
        join_requests.router,
        admin_payments.router,
        admin_settings.router,
        admin.router,
        payment.router,
        fallback.router,
    ]
