"""
app/ui/pages/dashboard.py
Dashboard — live device status cards with auto-refresh.
"""
import json
from nicegui import ui

from app.db.database import get_all_devices
from app.bridge.manager import bridge_manager


def status_color(device) -> str:
    if not device.enabled:
        return "grey"
    return "positive" if device.is_online else "negative"


def status_label(device) -> str:
    if not device.enabled:
        return "Disabled"
    return "Online" if device.is_online else "Offline"


def build():
    ui.label("Device Dashboard").classes("text-2xl font-bold mb-4")

    # Stats row
    with ui.row().classes("w-full gap-4 mb-6"):
        devices = get_all_devices()
        total = len(devices)
        online = sum(1 for d in devices if d.is_online and d.enabled)
        offline = sum(1 for d in devices if not d.is_online and d.enabled)
        disabled = sum(1 for d in devices if not d.enabled)

        for label, value, color in [
            ("Total Devices", total, "primary"),
            ("Online", online, "positive"),
            ("Offline", offline, "negative"),
            ("Disabled", disabled, "grey"),
        ]:
            with ui.card().classes("flex-1 text-center"):
                ui.label(str(value)).classes(f"text-4xl font-bold text-{color}")
                ui.label(label).classes("text-sm text-gray-500")

    # Device cards grid
    cards_container = ui.element("div").classes(
        "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full"
    )

    def refresh_cards():
        cards_container.clear()
        devices = get_all_devices()
        with cards_container:
            for device in devices:
                _device_card(device)

    def _device_card(device):
        dps = {}
        if device.last_status:
            try:
                dps = json.loads(device.last_status)
            except Exception:
                pass

        with ui.card().classes("w-full"):
            with ui.row().classes("items-center justify-between w-full"):
                ui.label(device.name).classes("text-lg font-semibold")
                ui.badge(status_label(device), color=status_color(device))

            ui.separator()

            with ui.grid(columns=2).classes("w-full text-sm gap-1"):
                ui.label("IP").classes("text-gray-500")
                ui.label(device.ip)
                ui.label("Version").classes("text-gray-500")
                ui.label(str(device.version))
                ui.label("Last Seen").classes("text-gray-500")
                ui.label(
                    device.last_seen.strftime("%H:%M:%S") if device.last_seen else "Never"
                )

            if dps:
                ui.separator()
                ui.label("DPS State").classes("text-xs text-gray-500 mt-1")
                with ui.row().classes("flex-wrap gap-1 mt-1"):
                    for k, v in list(dps.items())[:8]:  # show first 8
                        ui.chip(f"{k}: {v}", color="blue-grey").classes("text-xs")

            with ui.row().classes("justify-end mt-2 gap-2"):
                ui.button(
                    icon="edit",
                    on_click=lambda d=device: ui.navigate.to(f"/devices/edit/{d.device_id}"),
                ).props("flat round size=sm")

    refresh_cards()

    # Auto-refresh every 10s
    ui.timer(10.0, refresh_cards)

    with ui.row().classes("mt-4"):
        ui.button("Refresh Now", icon="refresh", on_click=refresh_cards).props("outline")
