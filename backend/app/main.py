from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.middleware.rate_limiter import limiter
from app.utils.errors import register_exception_handlers
from app.routers import auth, dashboard, merchants, reports, statements, whatsapp_webhook

# aliased: plain `settings` here would shadow app.config.settings
from app.routers import settings as settings_router

app = FastAPI(title="CredScore API", version="0.1.0")

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Consistent error JSON shape across the whole API
register_exception_handlers(app)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(merchants.router, prefix="/api/v1/merchants", tags=["merchants"])
app.include_router(statements.router, prefix="/api/v1/statements", tags=["statements"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(whatsapp_webhook.router, prefix="/api/v1/webhooks/whatsapp", tags=["whatsapp"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.environment}