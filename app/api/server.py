# -*- coding: utf-8 -*-
"""سرور FastAPI - نقطه تجمیع همه سرویس‌ها + سرو‌کردن فرانت‌اند React

- مسیرهای API: /api/v1/*  (هر بخش یک سرویس مستقل برای نرم‌افزارهای دیگر)
- مستندات تعاملی: /api/docs (Swagger) و /api/redoc
- فرانت‌اند: سرو‌کردن بیلد React از frontend/dist (یا app/web_static در بسته پرتابل)
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app import __version__, db, integration
from app import config as _config
from app.config import APP_NAME, frontend_dist_candidates
from app.security import RATE_LIMITER
from app.api.routers import (admin, advisor, auth, chat, deadlines, integration_v1,
                             integrations, processes, regulations, rules, tickets)
from app.widget_assets import DEMO_HTML, WIDGET_JS


def _find_frontend() -> Path | None:
    for c in frontend_dist_candidates():
        if (c / "index.html").exists():
            return c
    return None


def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        version=__version__,
        description="زیرسیستم «دستیار آموزشی و آیین‌نامه‌ای دانشجو۳۶۰» - "
                    "هر بخش به‌صورت سرویس API مستقل در دسترس سایر نرم‌افزارهاست؛ "
                    "سامانه‌های دیگر (پژوهشیار، برنامه‌ریز، ...) با X-API-Key از "
                    "/api/v1/integration/v1 مصرف می‌کنند و چت‌بات با widget.js نصب می‌شود.",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS (توکن در هدر Bearer است؛ کوکی استفاده نمی‌شود)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # ---------- محدودسازی نرخ عمومی (ضد سوءاستفاده) ----------
    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/"):
            ip = request.client.host if request.client else "?"
            if not RATE_LIMITER.allow(f"http:{ip}", 300, window_s=60):
                return JSONResponse({"detail": "تعداد درخواست‌ها بیش از حد مجاز است"},
                                    status_code=429)
        return await call_next(request)

    # ---------- نگاشت خطاهای لایه سرویس به کدهای HTTP ----------
    @app.exception_handler(PermissionError)
    async def perm_err(request, exc: PermissionError):
        return JSONResponse({"detail": str(exc)}, status_code=403)

    @app.exception_handler(ValueError)
    async def value_err(request, exc: ValueError):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(LookupError)
    async def lookup_err(request, exc: LookupError):
        return JSONResponse({"detail": str(exc) or "یافت نشد"}, status_code=404)

    @app.exception_handler(RequestValidationError)
    async def val_err(request, exc: RequestValidationError):
        return JSONResponse({"detail": "داده ارسالی نامعتبر است", "errors": exc.errors()},
                            status_code=422)

    # ---------- سرویس‌ها ----------
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(regulations.router, prefix="/api/v1")
    app.include_router(rules.router, prefix="/api/v1")
    app.include_router(advisor.router, prefix="/api/v1")
    app.include_router(processes.router, prefix="/api/v1")
    app.include_router(deadlines.router, prefix="/api/v1")
    app.include_router(tickets.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(integrations.router, prefix="/api/v1")
    app.include_router(integration_v1.router, prefix="/api/v1")

    # ---------- ثبت فراخوانی سرویس‌های سایر سامانه‌ها ----------
    @app.middleware("http")
    async def integration_log_mw(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/v1/integration/v1/"):
            t0 = time.perf_counter()
            response = await call_next(request)
            system = getattr(request.state, "int_system", None)
            if system:
                conn = db.connect(_config.db_path())
                try:
                    integration.log_call(conn, system, path, response.status_code,
                                         int((time.perf_counter() - t0) * 1000),
                                         request.client.host if request.client else "")
                finally:
                    conn.close()
            return response
        return await call_next(request)

    # ---------- چت‌بات قابل نصب در سایر سامانه‌ها ----------
    @app.get("/api/v1/integration/widget.js", include_in_schema=False)
    @app.get("/widget.js", include_in_schema=False)
    def widget_js():
        return Response(WIDGET_JS, media_type="application/javascript",
                        headers={"Cache-Control": "no-cache"})

    @app.get("/integration-demo", include_in_schema=False,
             summary="صفحه آزمایشی نصب چت‌بات در یک سامانه دیگر (نمونه پژوهشیار)")
    def integration_demo(request: Request):
        key = request.query_params.get("key", "")
        conn = db.connect(_config.db_path())
        try:
            system = integration.verify_key(conn, key)
        finally:
            conn.close()
        if not system:
            return HTMLResponse("<html dir=\"rtl\" lang=\"fa\"><body style=\"font-family:Tahoma;"
                                "background:#05070f;color:#fda4af;padding:40px;\">"
                                "<h3>کلید نامعتبر است</h3><p>این صفحه باید با پارامتر «?key=کلید سامانه متصل» باز شود. "
                                "کلیدها در «سامانه‌های متصل» مدیریت می‌شوند.</p></body></html>", 403)
        return HTMLResponse(DEMO_HTML.replace("__KEY__", key))

    @app.get("/api/health", include_in_schema=False)
    def health():
        return {"ok": True, "app": APP_NAME, "version": __version__}

    # ---------- فرانت‌اند (بیلد React) ----------
    dist = _find_frontend()
    if dist:
        _MT = {".woff2": "font/woff2", ".woff": "font/woff", ".css": "text/css",
               ".js": "text/javascript", ".html": "text/html"}

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str, request: Request):
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "یافت نشد"}, status_code=404)
            f = dist / full_path
            gw = request.query_params.get("XTransformPort")
            # حالت پیش‌نمایش پشت درگاه: تزریق پارامتر درگاه به URLهای asset/فونت
            if gw and full_path.endswith(".css") and full_path and f.is_file():
                css = f.read_text(encoding="utf-8")
                css = re.sub(r'url\(("|\')?(/fonts/[^)"\']+)',
                             lambda m: f'url({m.group(1) or ""}{m.group(2)}?XTransformPort={gw}', css)
                return Response(css, media_type="text/css")
            if full_path and f.is_file():
                ext = full_path.rsplit(".", 1)[-1].lower()
                if f".{ext}" in _MT:
                    return FileResponse(f, media_type=_MT[f".{ext}"])
                return FileResponse(f)
            if gw:
                html = (dist / "index.html").read_text(encoding="utf-8")
                html = re.sub(r'(src|href)="(/(?:assets|fonts)/[^"]+)"',
                              lambda m: f'{m.group(1)}="{m.group(2)}?XTransformPort={gw}"', html)
                return HTMLResponse(html)
            return FileResponse(dist / "index.html")
    else:
        @app.get("/", include_in_schema=False)
        def root_hint():
            return JSONResponse({
                "app": APP_NAME,
                "hint": "بیلد فرانت‌اند یافت نشد. دستورات docs/06-install.md را ببینید.",
                "api_docs": "/api/docs",
            })

    return app


app = create_app()
