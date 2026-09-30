import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.middleware.audit import AuditMiddleware
from app.middleware.rate_limiter import limiter
from app.utils.errors import register_exception_handlers
from app.utils.logger import configure_logging
from app.routers import auth, dashboard, merchants, reports, statements, whatsapp_webhook

# aliased: plain `settings` here would shadow app.config.settings
from app.routers import settings as settings_router

configure_logging()

app = FastAPI(title="CredScore API", version="0.1.0")

# error tracking, on only when a dsn is configured
if settings.sentry_dsn:
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)
    except ImportError:
        logging.getLogger("credscore").warning(
            "sentry_dsn is set but sentry-sdk is not installed"
        )

# rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# consistent error json shape across the whole api
register_exception_handlers(app)

# one audit_logs row per successful mutation
app.add_middleware(AuditMiddleware)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(merchants.router, prefix="/api/v1/merchants", tags=["merchants"])
app.include_router(statements.router, prefix="/api/v1/statements", tags=["statements"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(whatsapp_webhook.router, prefix="/api/v1/webhooks/whatsapp", tags=["whatsapp"])

def _cors_origins() -> list[str]:
    if settings.cors_origins:
        return [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    return ["http://localhost:3000"] if settings.environment == "development" else []


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.environment}