"""
app/main.py
Application entrypoint — starts the bridge and serves the NiceGUI UI.
"""
import asyncio
import logging
import sys

from nicegui import app as nicegui_app, ui

from app.config import config
from app.db.database import init_db
from app.bridge.manager import bridge_manager
from app.ui.pages import dashboard, add_device, edit_device

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Lifecycle ─────────────────────────────────────────────────────────────────

@nicegui_app.on_startup
async def startup():
    # init_db() is also called when app.db.database is imported, so the schema is
    # already there by now. Kept here because it is idempotent and this is where a
    # reader looks for it.
    init_db()
    try:
        await bridge_manager.start()
    except Exception:
        logger.exception("Bridge failed to start — the UI is still available")
    logger.info("Application started")


@nicegui_app.on_shutdown
async def shutdown():
    await bridge_manager.stop()
    logger.info("Application stopped")


# ── Layout helper ─────────────────────────────────────────────────────────────

def page_layout(title: str):
    """Shared nav header injected into every page."""
    with ui.header(elevated=True).classes("bg-primary text-white items-center"):
        ui.button(icon="home", on_click=lambda: ui.navigate.to("/")).props("flat color=white round")
        ui.label(config.ui.title).classes("text-lg font-bold flex-1 text-center")
        ui.button(
            icon="add_circle",
            on_click=lambda: ui.navigate.to("/devices/add"),
        ).props("flat color=white round")

    with ui.left_drawer(value=True).classes("bg-grey-1"):
        ui.label("Navigation").classes("text-xs text-gray-500 px-4 pt-4 pb-2")
        with ui.list():
            ui.item("Dashboard", on_click=lambda: ui.navigate.to("/")).classes("cursor-pointer")
            ui.item("Add Device", on_click=lambda: ui.navigate.to("/devices/add")).classes("cursor-pointer")

    ui.label(title).classes("sr-only")  # accessibility


# ── Routes ────────────────────────────────────────────────────────────────────

@ui.page("/")
def index():
    page_layout("Dashboard")
    with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
        dashboard.build()


@ui.page("/devices/add")
def page_add_device():
    page_layout("Add Device")
    with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
        add_device.build()


@ui.page("/devices/edit/{device_id}")
def page_edit_device(device_id: str):
    page_layout("Edit Device")
    with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
        edit_device.build(device_id)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        host=config.ui.host,
        port=config.ui.port,
        title=config.ui.title,
        reload=False,          # disable in production / container
        show=False,
    )
