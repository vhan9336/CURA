# main.py
import flet as ft
from src.background import start_background_monitor
from src.checkup import create_confirm_view
from src.database import users_db


def initialize_user_session(page: ft.Page, username: str):
    def get_user_schedule():
        user_info = users_db.get(username, {})
        return {
            "wakeup": user_info.get("wakeup_time"),
            "bedtime": user_info.get("bedtime_time"),
        }

    async def show_hourly_checkup():
        create_confirm_view(page, username)

    def trigger_hourly_checkup():
        page.run_task(show_hourly_checkup)

    start_background_monitor(
        get_user_schedule, trigger_hourly_checkup, monitor_key=username
    )


def open_main_dashboard(page: ft.Page, username: str = ""):
    page.clean()
    page.title = "Safety App - Dashboard"

    # Initialize and start the background check-up monitor for this user session
    initialize_user_session(page, username)

    # Rest of your dashboard setup...
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START

    page.add(
        ft.Text(f"Welcome back, {username}!", size=24, weight=ft.FontWeight.BOLD),
        ft.Container(height=10),
        ft.Text("Your dashboard is active and monitoring.", size=16),
    )
    page.update()


def main(page: ft.Page):
    open_main_dashboard(page, username="TestUser")


if __name__ == "__main__":
    ft.app(target=main)