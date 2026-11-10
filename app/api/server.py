# -*- coding: utf-8 -*-
"""سرور FastAPI - نقطه تجمیع همه سرویس‌ها + سرو‌کردن فرانت‌اند React

- مسیرهای API: /api/v1/*  (هر بخش یک سرویس مستقل برای نرم‌افزارهای دیگر)
- مستندات تعاملی: /api/docs (Swagger) و /api/redoc
- فرانت‌اند: سرو‌کردن بیلد React از frontend/dist (یا app/web_static در بسته پرتابل)
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import APP_NAME, frontend_dist_candidates
from app.security import RATE_LIMITER
from app.api.routers import admin, advisor, auth, chat, deadlines, processes, regulations, rules, tickets


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
                    "هر بخش به‌صورت سرویس API مستقل در دسترس سایر نرم‌افزارهاست.",
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

    @app.get("/api/health", include_in_schema=False)
    def health():
        return {"ok": True, "app": APP_NAME, "version": __version__}

    # ---------- فرانت‌اند (بیلد React) ----------
    dist = _find_frontend()
    if dist:
        if (dist / "assets").exists():
            app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "یافت نشد"}, status_code=404)
            f = dist / full_path
            if full_path and f.is_file():
                return FileResponse(f)
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
