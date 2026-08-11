# checkup.py
import flet as ft
from dashhome import open_main_dashboard
from help import help
from plyer import notification

def trigger_desktop_alert():
  notification.notify(
      title="Routine Check-Up",
      message="Please acknowledge immediately in the app",
      app_name="Safety App",
      timeout=10,
  )



def create_confirm_view(page: ft.Page):
  page.title = "Safety App - Routine Check"
  page.clean()

  def handle_ok(e):
    open_main_dashboard(page)

  def handle_help(e):
    help()

  ok_button = ft.ElevatedButton(
      content="I'm doing well!",
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
      ft.Text(f"Hi users_db[entered_user], this your routine checkup...", size=22, weight=ft.FontWeight.BOLD, color="blue"),
      ft.Container(height=10),
      ft.Text("How are you doing?", size=18),
      ft.Container(height=20),
      ok_button,
      ft.Container(height=10),
      help_button,
  )
  page.update()