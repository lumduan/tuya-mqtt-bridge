"""
app/ui/components/device_card.py
Reusable device status card component.
"""
import json
from nicegui import ui


def device_card(device):
    """Render a status card for a single device."""
    dps = {}
    if device.last_status:
        try:
            dps = json.loads(device.last_status)
        except Exception:
            pass

    color = "grey" if not device.enabled else ("positive" if device.is_online else "negative")
    label = "Disabled" if not device.enabled else ("Online" if device.is_online else "Offline")

    with ui.card().classes("w-full"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label(device.name).classes("text-lg font-semibold")
            ui.badge(label, color=color)

        ui.separator()

        with ui.grid(columns=2).classes("w-full text-sm gap-1"):
            ui.label("IP").classes("text-gray-500")
            ui.label(device.ip)
            ui.label("Version").classes("text-gray-500")
            ui.label(str(device.version))
            ui.label("Last Seen").classes("text-gray-500")
            ui.label(device.last_seen.strftime("%H:%M:%S") if device.last_seen else "Never")

        if dps:
            ui.separator()
            ui.label("DPS State").classes("text-xs text-gray-500 mt-1")
            with ui.row().classes("flex-wrap gap-1 mt-1"):
                for k, v in list(dps.items())[:8]:
                    ui.chip(f"{k}: {v}", color="blue-grey").classes("text-xs")

        with ui.row().classes("justify-end mt-2"):
            ui.button(
                icon="edit",
                on_click=lambda d=device: ui.navigate.to(f"/devices/edit/{d.device_id}"),
            ).props("flat round size=sm")
