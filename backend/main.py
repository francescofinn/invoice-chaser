from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import settings
from routers import clients, dashboard, invoices, operator, webhooks
from services.scheduler import start_scheduler, stop_scheduler


def create_app(*, start_scheduler_on_startup: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if start_scheduler_on_startup:
            start_scheduler()
        yield
        if start_scheduler_on_startup:
            stop_scheduler()

    app = FastAPI(title="Invoice Chaser API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(clients.router, prefix="/clients", tags=["clients"])
    app.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
    app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
    app.include_router(operator.router, prefix="/operator", tags=["operator"])
    app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

    return app


app = create_app()
