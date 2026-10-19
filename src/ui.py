# ui.py
import flet as ft
import asyncio
import threading
from datetime import time

if __package__:
  from .dashhome import create_schedule_view
  from .database import users_db
  from .login import create_login_view
  from .register import create_register_view
  from .audio import start_listening
  from .background import start_background_monitor, stop_background_monitor
  from .checkup import create_confirm_view
  from .alert import create_audio_alert_view
else:
  from dashhome import create_schedule_view
  from database import users_db
  from login import create_login_view
  from register import create_register_view
  from audio import start_listening
  from background import start_background_monitor, stop_background_monitor
  from checkup import create_confirm_view
  from alert import create_audio_alert_view


def main(page: ft.Page):
  page.vertical_alignment = ft.MainAxisAlignment.CENTER
  page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
  if page.platform.is_desktop():
    page.window.width = 700
    page.window.height = 1300

  active_username: str | None = None
  desktop_audio_stop_event: threading.Event | None = None
  mobile_monitor = None
  mobile_notifications_enabled = False
  mobile_watcher_started = False

  if not page.web and page.platform == ft.PagePlatform.ANDROID:
    from flet_cura_android import CuraAndroid

    mobile_monitor = CuraAndroid()
    page.services.append(mobile_monitor)

  def start_desktop_audio_monitor():
    nonlocal desktop_audio_stop_event
    if mobile_monitor is not None:
      return
    if desktop_audio_stop_event is not None and not desktop_audio_stop_event.is_set():
      return
    desktop_audio_stop_event = threading.Event()
    audio_thread = threading.Thread(
        target=start_listening,
        args=(page, go_to_audio_alert, desktop_audio_stop_event),
        daemon=True,
    )
    audio_thread.start()

  # Function to initialize and start the background check-up monitor for a user
  def initialize_user_session(username: str):
    def get_user_schedule():
      user_info = users_db.get(username, {})
      if not isinstance(user_info, dict):
        return {"wakeup": None, "bedtime": None}
      wakeup = user_info.get("wakeup_time")
      bedtime = user_info.get("bedtime_time")
      return {
          "wakeup": wakeup if isinstance(wakeup, time) else None,
          "bedtime": bedtime if isinstance(bedtime, time) else None,
      }

    async def show_hourly_checkup():
      create_confirm_view(page, username, on_logout=logout)

    def trigger_hourly_checkup():
      page.run_task(show_hourly_checkup)

    if mobile_monitor is None:
      start_background_monitor(
          get_user_schedule, trigger_hourly_checkup, monitor_key=username
      )
      start_desktop_audio_monitor()

  def show_mobile_notice(message: str):
    page.show_dialog(ft.SnackBar(content=ft.Text(message)))

  async def sync_mobile_schedule(wakeup, bedtime):
    if mobile_monitor is None:
      return
    if not mobile_notifications_enabled:
      show_mobile_notice(
          "Enable notifications in Android settings to receive scheduled check-ins."
      )
      return
    schedule = await mobile_monitor.schedule_checkins(wakeup, bedtime)
    if schedule.limitation:
      show_mobile_notice(schedule.limitation)

  async def handle_pending_mobile_events(username: str):
    if mobile_monitor is None or active_username != username:
      return
    if await mobile_monitor.consume_audio_alert():
      await mobile_monitor.consume_checkin()
      create_audio_alert_view(page, username, on_logout=logout)
    elif await mobile_monitor.consume_checkin():
      create_confirm_view(page, username, on_logout=logout)

  async def watch_mobile_events():
    while True:
      username = active_username
      if username is not None:
        await handle_pending_mobile_events(username)
      await asyncio.sleep(1)

  async def initialize_mobile_session(username: str):
    nonlocal mobile_notifications_enabled, mobile_watcher_started
    if mobile_monitor is None:
      return

    permissions = await mobile_monitor.request_permissions()
    if active_username != username:
      return
    mobile_notifications_enabled = permissions.notifications
    user_info = users_db.get(username, {})
    wakeup = user_info.get("wakeup_time") if isinstance(user_info, dict) else None
    bedtime = user_info.get("bedtime_time") if isinstance(user_info, dict) else None
    notices = []

    if not permissions.notifications:
      notices.append("Enable notifications to receive check-ins and sound alerts.")
    if not permissions.microphone:
      notices.append("Enable microphone access to monitor for loud sounds.")
    elif permissions.notifications:
      await mobile_monitor.start_monitoring()

    if (
      permissions.notifications
      and isinstance(wakeup, time)
      and isinstance(bedtime, time)
    ):
      await sync_mobile_schedule(wakeup, bedtime)

    if notices:
      show_mobile_notice(" ".join(notices))

    if not mobile_watcher_started:
      mobile_watcher_started = True
      page.run_task(watch_mobile_events)

  def logout():
    nonlocal active_username, desktop_audio_stop_event, mobile_notifications_enabled
    username = active_username
    if username is not None:
      stop_background_monitor(username)
    if desktop_audio_stop_event is not None:
      desktop_audio_stop_event.set()
      desktop_audio_stop_event = None
    active_username = None
    mobile_notifications_enabled = False

    monitor = mobile_monitor
    if monitor is not None:
      async def stop_mobile_session():
        await monitor.consume_audio_alert()
        await monitor.consume_checkin()
        await monitor.stop_monitoring()
        await monitor.cancel_checkins()

      page.run_task(stop_mobile_session)
    go_to_login()

  # Called once a user successfully logs in -> Starts background monitor & goes to schedule setup
  def handle_successful_login(username):
    nonlocal active_username
    active_username = username
    initialize_user_session(username)
    if mobile_monitor is not None:
      page.run_task(initialize_mobile_session, username)

    def on_schedule_saved(wakeup: time, bedtime: time) -> None:
      if mobile_monitor is None:
        stop_background_monitor(username)
        initialize_user_session(username)
      else:
        page.run_task(sync_mobile_schedule, wakeup, bedtime)

    create_schedule_view(
        page,
        username,
        on_schedule_saved=on_schedule_saved,
        on_logout=logout,
    )

  # Define navigation switch functions
  def go_to_login(e=None):
    create_login_view(page, handle_successful_login, go_to_register)

  def go_to_register(e=None):
    create_register_view(page, go_to_login)

  def go_to_audio_alert(username: str | None = None):
    target_username = username or active_username
    if target_username is not None:
      create_audio_alert_view(page, target_username, on_logout=logout)

  if mobile_monitor is not None and users_db:
    go_to_login()
  else:
    go_to_register()


if __name__ == "__main__":
  ft.run(main)