# background.py
from datetime import datetime, time, timedelta
import time as t
import threading


def _is_within_waking_hours(current_time: time, wakeup_time: time, bedtime: time) -> bool:
    if wakeup_time <= bedtime:
        return wakeup_time <= current_time <= bedtime
    return current_time >= wakeup_time or current_time <= bedtime


def run_safety_scheduler(get_user_schedule_func, trigger_alert_func):
    last_alert_at = None
    while True:
        now = datetime.now()
        current_time = now.time()

        schedule = get_user_schedule_func()

        wakeup_time = schedule.get("wakeup")
        bedtime = schedule.get("bedtime")

        if wakeup_time is not None and bedtime is not None:
            if _is_within_waking_hours(current_time, wakeup_time, bedtime):
                if last_alert_at is None or now - last_alert_at >= timedelta(hours=1):
                    last_alert_at = now
                    trigger_alert_func()

        t.sleep(60)


def start_background_monitor(get_schedule_callback, alert_callback):
    monitor_thread = threading.Thread(
        target=run_safety_scheduler,
        args=(get_schedule_callback, alert_callback),
        daemon=True
    )
    monitor_thread.start()