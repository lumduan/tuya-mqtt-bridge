"""
app/ui/pages/add_device.py
Form to add a new Tuya device to the bridge.
"""
from nicegui import ui

from app.db.database import add_device, get_device
from app.bridge.manager import bridge_manager


def build():
    ui.label("Add Device").classes("text-2xl font-bold mb-4")

    with ui.card().classes("w-full max-w-lg"):
        device_id = ui.input("Device ID *", placeholder="abcdef1234567890abcd").classes("w-full")
        name = ui.input("Friendly Name *", placeholder="Living Room Plug").classes("w-full")
        ip = ui.input("Device IP *", placeholder="192.168.1.100").classes("w-full")
        key = ui.input("Local Key *", placeholder="abcdef1234567890").classes("w-full")

        with ui.row().classes("w-full gap-4"):
            version = ui.select(
                label="Protocol Version",
                options=["3.1", "3.2", "3.3", "3.4", "3.5"],
                value="3.3",
            ).classes("flex-1")
            persist = ui.checkbox("Persistent Connection", value=True)

        result_label = ui.label("").classes("text-sm mt-2")

        async def submit():
            # Validation
            errors = []
            if not device_id.value.strip():
                errors.append("Device ID is required")
            if not name.value.strip():
                errors.append("Name is required")
            if not ip.value.strip():
                errors.append("IP is required")
            if not key.value.strip():
                errors.append("Local Key is required")

            if errors:
                result_label.set_text(" | ".join(errors))
                result_label.classes("text-negative", remove="text-positive")
                return

            if get_device(device_id.value.strip()):
                result_label.set_text("Device ID already exists!")
                result_label.classes("text-negative", remove="text-positive")
                return

            try:
                device = add_device(
                    device_id=device_id.value.strip(),
                    name=name.value.strip(),
                    ip=ip.value.strip(),
                    key=key.value.strip(),
                    version=float(version.value),
                    persist=persist.value,
                )
                # Start poller immediately
                await bridge_manager.add_device_poller(device)

                result_label.set_text(f"✓ Device '{name.value}' added and polling started!")
                result_label.classes("text-positive", remove="text-negative")

                # Clear form
                for field in [device_id, name, ip, key]:
                    field.set_value("")

            except Exception as exc:
                result_label.set_text(f"Error: {exc}")
                result_label.classes("text-negative", remove="text-positive")

        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=lambda: ui.navigate.to("/")).props("flat")
            ui.button("Add Device", icon="add", on_click=submit).props("color=primary")
