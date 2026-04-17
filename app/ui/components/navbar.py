"""
app/ui/components/navbar.py
Navigation bar component.
"""
from nicegui import ui

from app.config import config


def navbar():
    """Render the top navigation header and left drawer."""
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
