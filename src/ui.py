# ui.py
import flet as ft
import threading

if __package__:
  from .dashhome import create_schedule_view
  from .database import users_db
  from .login import create_login_view
  from .register import create_register_view
  from .audio import start_listening
  from .background import start_background_monitor
  from .checkup import create_confirm_view
  from .alert import create_audio_alert_view
  from .theme import set_dark
else:
  from dashhome import create_schedule_view
  from database import users_db
  from login import create_login_view
  from register import create_register_view
  from audio import start_listening
  from background import start_background_monitor
  from checkup import create_confirm_view
  from alert import create_audio_alert_view
  from theme import set_dark


def main(page: ft.Page):
  page.vertical_alignment = ft.MainAxisAlignment.CENTER
  page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
  set_dark(False)
  page.window.width = 700
  page.window.height = 1300

  active_username: str | None = None

  # Function to initialize and start the background check-up monitor for a user
  def initialize_user_session(username: str):
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

  # Called once a user successfully logs in -> Starts background monitor & goes to schedule setup
  def handle_successful_login(username):
    nonlocal active_username
    active_username = username
    initialize_user_session(username)
    create_schedule_view(page, username)

  # Define navigation switch functions
  def go_to_login(e=None):
    create_login_view(page, handle_successful_login, go_to_register)

  def go_to_register(e=None):
    create_register_view(page, go_to_login)

  def go_to_audio_alert(username: str | None = None):
    target_username = username or active_username
    if target_username is not None:
      create_audio_alert_view(page, target_username)

  # Start the audio listener in a background thread
  audio_thread = threading.Thread(
      target=start_listening, args=(page, go_to_audio_alert), daemon=True
  )
  audio_thread.start()

  # Start the app on the registration screen by default
  go_to_register()


if __name__ == "__main__":
  ft.run(main)