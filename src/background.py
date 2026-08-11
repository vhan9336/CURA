# background.py
from datetime import datetime, time
import time as t
import threading


def run_safety_scheduler(get_user_schedule_func, trigger_alert_func):
    last_checked_hour = None
    while True:
        now = datetime.now()
        current_hour = now.hour
        current_time = now.time()

        schedule = get_user_schedule_func()

        # Retrieve user schedule set via dashhome.py widget
        wakeup_time = schedule.get("wakeup")
        bedtime = schedule.get("bedtime")

        # If the user hasn't configured a schedule yet, skip or use a safe default
        if wakeup_time is not None and bedtime is not None:
            if wakeup_time <= current_time <= bedtime:
                if last_checked_hour != current_hour:
                    last_checked_hour = current_hour
                    trigger_alert_func()

        print("Time logged")
        t.sleep(60)


def start_background_monitor(get_schedule_callback, alert_callback):
    monitor_thread = threading.Thread(
        target=run_safety_scheduler,
        args=(get_schedule_callback, alert_callback),
        daemon=True
    )
    monitor_thread.start()