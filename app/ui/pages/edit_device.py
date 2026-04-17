"""
app/ui/pages/edit_device.py
Edit and delete a device.
"""
from nicegui import ui

from app.db.database import get_device, update_device, delete_device
from app.bridge.manager import bridge_manager


def build(device_id: str):
    device = get_device(device_id)
    if not device:
        ui.label(f"Device '{device_id}' not found.").classes("text-negative")
        ui.button("Back", on_click=lambda: ui.navigate.to("/")).props("outline")
        return

    ui.label(f"Edit Device — {device.name}").classes("text-2xl font-bold mb-4")

    with ui.card().classes("w-full max-w-lg"):
        ui.label(f"ID: {device.device_id}").classes("text-xs text-gray-400 mb-2")

        name = ui.input("Friendly Name *", value=device.name).classes("w-full")
        ip = ui.input("Device IP *", value=device.ip).classes("w-full")
        key = ui.input("Local Key *", value=device.key).classes("w-full")

        with ui.row().classes("w-full gap-4"):
            version = ui.select(
                label="Protocol Version",
                options=["3.1", "3.2", "3.3", "3.4", "3.5"],
                value=str(device.version),
            ).classes("flex-1")
            persist = ui.checkbox("Persistent Connection", value=device.persist)

        enabled = ui.checkbox("Enable Polling", value=device.enabled)

        result_label = ui.label("").classes("text-sm mt-2")

        async def save():
            try:
                update_device(
                    device_id,
                    name=name.value.strip(),
                    ip=ip.value.strip(),
                    key=key.value.strip(),
                    version=float(version.value),
                    persist=persist.value,
                    enabled=enabled.value,
                )
                updated = get_device(device_id)
                await bridge_manager.reload_device(device_id, updated)

                result_label.set_text("✓ Saved and poller restarted.")
                result_label.classes("text-positive", remove="text-negative")
            except Exception as exc:
                result_label.set_text(f"Error: {exc}")
                result_label.classes("text-negative", remove="text-positive")

        async def confirm_delete():
            with ui.dialog() as dialog, ui.card():
                ui.label(f"Delete '{device.name}'?").classes("text-lg font-bold")
                ui.label("This will stop polling and remove it from the database.").classes("text-sm text-gray-500")
                with ui.row().classes("justify-end gap-2 mt-4"):
                    ui.button("Cancel", on_click=dialog.close).props("flat")
                    async def do_delete():
                        await bridge_manager.remove_device_poller(device_id)
                        delete_device(device_id)
                        dialog.close()
                        ui.navigate.to("/")
                    ui.button("Delete", on_click=do_delete).props("color=negative")
            dialog.open()

        with ui.row().classes("justify-between mt-4"):
            ui.button("Delete", icon="delete", on_click=confirm_delete).props("color=negative flat")
            with ui.row().classes("gap-2"):
                ui.button("Cancel", on_click=lambda: ui.navigate.to("/")).props("flat")
                ui.button("Save Changes", icon="save", on_click=save).props("color=primary")
