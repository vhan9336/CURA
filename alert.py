# alert.py
import flet as ft
from dashhome import open_main_dashboard
from help import help
from plyer import notification


def trigger_desktop_alert():
  notification.notify(
      title="⚠️ Safety Check-Up",
      message="We detected a loud sound or trigger. Are you alright?",
      app_name="Safety App",
      timeout=10,
  )


def create_confirm_view(page: ft.Page, username: str = ""):
  page.title = "Safety App - Alert Check"
  page.clean()

  # Trigger the native desktop notification popup when this view opens
  trigger_desktop_alert()

  def handle_ok(e):
    open_main_dashboard(page, username)

  def handle_help(e):
    help()

  ok_button = ft.ElevatedButton(
      content="I'm Okay",
      color="white",
      bgcolor="blue",
      width=300,
      on_click=handle_ok,
  )

  help_button = ft.ElevatedButton(
      content="I need help",
      color="white",
      bgcolor="red",
      width=300,
      on_click=handle_help,
  )

  page.add(
      ft.Text(
          "⚠️ Loud noise or alert triggered!",
          size=22,
          weight=ft.FontWeight.BOLD,
          color="red",
      ),
      ft.Container(height=10),
      ft.Text("Are you alright?", size=18),
      ft.Container(height=20),
      ok_button,
      ft.Container(height=10),
      help_button,
  )
  page.update()