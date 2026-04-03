from __future__ import annotations

import time

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.database import init_database
from app.routers import account_routes, auth_routes, group_routes, pages
from app.websocket_manager import ConnectionManager


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="PolKhol")
    resolved_settings = settings or Settings.from_env()
    app.state.settings = resolved_settings
    app.state.ws_manager = ConnectionManager()
    app.state.asset_version = str(int(time.time()))

    init_database(resolved_settings.database_url)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(pages.router)
    app.include_router(auth_routes.router)
    app.include_router(account_routes.router)
    app.include_router(group_routes.router)
    return app


app = create_app()