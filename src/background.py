# background.py
from collections.abc import Callable, Mapping
from datetime import datetime, time, timedelta
import threading


def _is_within_waking_hours(current_time: time, wakeup_time: time, bedtime: time) -> bool:
    if wakeup_time == bedtime:
        return False
    if wakeup_time <= bedtime:
        return wakeup_time <= current_time <= bedtime
    return current_time >= wakeup_time or current_time <= bedtime


def _should_trigger_checkin(
    now: datetime,
    schedule: Mapping[str, time | None],
    last_alert_at: datetime | None,
) -> bool:
    wakeup_time = schedule.get("wakeup")
    bedtime = schedule.get("bedtime")
    if wakeup_time is None or bedtime is None:
        return False
    if not isinstance(wakeup_time, time) or not isinstance(bedtime, time):
        raise ValueError("Wake-up and bedtime values must be datetime.time instances.")
    if not _is_within_waking_hours(now.time(), wakeup_time, bedtime):
        return False
    return last_alert_at is None or now - last_alert_at >= timedelta(hours=1)


def run_safety_scheduler(
    get_user_schedule_func: Callable[[], Mapping[str, time | None]],
    trigger_alert_func: Callable[[], None],
    stop_event: threading.Event | None = None,
    poll_interval: float = 60,
) -> None:
    last_alert_at = None
    if stop_event is None:
        stop_event = threading.Event()

    while not stop_event.is_set():
        now = datetime.now()
        schedule = get_user_schedule_func()

        if _should_trigger_checkin(now, schedule, last_alert_at):
            trigger_alert_func()
            last_alert_at = now

        stop_event.wait(poll_interval)


_monitor_lock = threading.Lock()
_monitor_threads: dict[str, tuple[threading.Thread, threading.Event]] = {}


def start_background_monitor(
    get_schedule_callback: Callable[[], Mapping[str, time | None]],
    alert_callback: Callable[[], None],
    monitor_key: str | None = None,
) -> threading.Thread:
    with _monitor_lock:
        if monitor_key is not None:
            existing = _monitor_threads.get(monitor_key)
            if existing is not None and existing[0].is_alive():
                return existing[0]

        stop_event = threading.Event()
        monitor_thread = threading.Thread(
            target=run_safety_scheduler,
            args=(get_schedule_callback, alert_callback, stop_event),
            daemon=True,
        )
        if monitor_key is not None:
            _monitor_threads[monitor_key] = (monitor_thread, stop_event)
        monitor_thread.start()
        return monitor_thread


def stop_background_monitor(monitor_key: str) -> None:
    with _monitor_lock:
        monitor = _monitor_threads.pop(monitor_key, None)
    if monitor is not None:
        monitor[1].set()