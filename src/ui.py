# ui.py
import flet as ft
import threading
from src.dashhome import create_schedule_view
from src.database import users_db
from src.login import create_login_view
from src.register import create_register_view
from src.alert import create_confirm_view
from src.audio import start_listening
from src.background import start_background_monitor
from src.checkup import create_confirm_view


def main(page: ft.Page):
  page.vertical_alignment = ft.MainAxisAlignment.CENTER
  page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
  page.theme_mode = ft.ThemeMode.DARK
  page.window.width = 400
  page.window.height = 800

  # Function to initialize and start the background check-up monitor for a user
  def initialize_user_session(username: str):
    def get_user_schedule():
      user_info = users_db.get(username, {})
      return {
          "wakeup": user_info.get("wakeup_time"),
          "bedtime": user_info.get("bedtime_time"),
      }

    def trigger_hourly_checkup():
      # Change from page.run_task to directly invoking or executing on the page view
      create_confirm_view(page, username)

    start_background_monitor(get_user_schedule, trigger_hourly_checkup)

  # Called once a user successfully logs in -> Starts background monitor & goes to schedule setup
  def handle_successful_login(username):
    initialize_user_session(username)
    create_schedule_view(page, username)

  # Define navigation switch functions
  def go_to_login(e=None):
    create_login_view(page, handle_successful_login, go_to_register)

  def go_to_register(e=None):
    create_register_view(page, go_to_login)

  # Function to navigate to the checkup alert view manually iZf needed
  def go_to_confirm(username=""):
    create_confirm_view(page, username)

  # Store reference on page so background tasks can trigger it
  page.go_to_confirm = go_to_confirm

  # Start the audio listener in a background thread
  audio_thread = threading.Thread(
      target=start_listening, args=(page,), daemon=True
  )
  audio_thread.start()

  # Start the app on the registration screen by default
  go_to_register()


if __name__ == "__main__":
  ft.run(main)