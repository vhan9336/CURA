import unittest
import asyncio
from datetime import datetime, time, timedelta
from types import ModuleType, SimpleNamespace
from typing import cast
from unittest.mock import Mock, patch

import flet as ft

from src import alert, audio, background, checkup, theme


class PlatformNotificationTests(unittest.TestCase):
    def test_android_screens_do_not_require_plyer(self):
        page = cast(
            ft.Page,
            SimpleNamespace(platform=SimpleNamespace(is_desktop=lambda: False)),
        )

        with patch.dict("sys.modules", {"plyer": None}):
            checkup.trigger_desktop_alert(page)
            alert.trigger_desktop_alert(page)

    def test_desktop_screens_keep_plyer_notifications(self):
        notify = Mock()
        plyer = ModuleType("plyer")
        setattr(plyer, "notification", SimpleNamespace(notify=notify))
        page = cast(
            ft.Page,
            SimpleNamespace(platform=SimpleNamespace(is_desktop=lambda: True)),
        )

        with patch.dict("sys.modules", {"plyer": plyer}):
            checkup.trigger_desktop_alert(page)
            alert.trigger_desktop_alert(page)

        self.assertEqual(notify.call_count, 2)


class SystemThemeTests(unittest.TestCase):
    def test_app_theme_follows_device_brightness(self):
        page = SimpleNamespace(platform_brightness=ft.Brightness.DARK, update=Mock())

        theme.apply_theme(page)

        self.assertEqual(page.theme_mode, ft.ThemeMode.SYSTEM)
        self.assertTrue(theme.is_dark())
        self.assertEqual(page.bgcolor, theme.DARK["BG"])

        theme.set_theme_rebuilder(page, lambda: theme.apply_theme(page))
        page.platform_brightness = ft.Brightness.LIGHT
        page.on_platform_brightness_change(None)

        self.assertFalse(theme.is_dark())
        self.assertEqual(page.bgcolor, theme.LIGHT["BG"])


class WakingHoursTests(unittest.TestCase):
    def test_same_day_window_includes_endpoints(self):
        wakeup = time(7)
        bedtime = time(22)

        self.assertFalse(
            background._is_within_waking_hours(time(6, 59), wakeup, bedtime)
        )
        self.assertTrue(
            background._is_within_waking_hours(time(7), wakeup, bedtime)
        )
        self.assertTrue(
            background._is_within_waking_hours(time(22), wakeup, bedtime)
        )
        self.assertFalse(
            background._is_within_waking_hours(time(22, 1), wakeup, bedtime)
        )

    def test_overnight_window_wraps_midnight(self):
        wakeup = time(22)
        bedtime = time(6)

        self.assertTrue(
            background._is_within_waking_hours(time(23), wakeup, bedtime)
        )
        self.assertTrue(
            background._is_within_waking_hours(time(5, 59), wakeup, bedtime)
        )
        self.assertFalse(
            background._is_within_waking_hours(time(12), wakeup, bedtime)
        )

    def test_equal_wakeup_and_bedtime_is_not_a_waking_window(self):
        self.assertFalse(
            background._is_within_waking_hours(time(8), time(8), time(8))
        )

    def test_checkin_requires_complete_schedule_and_hourly_spacing(self):
        now = datetime(2026, 10, 16, 8)
        schedule = {"wakeup": time(7), "bedtime": time(22)}

        self.assertFalse(
            background._should_trigger_checkin(
                now, {"wakeup": None, "bedtime": time(22)}, None
            )
        )
        self.assertTrue(background._should_trigger_checkin(now, schedule, None))
        self.assertFalse(
            background._should_trigger_checkin(
                now, schedule, datetime(2026, 10, 16, 7, 1)
            )
        )
        self.assertTrue(
            background._should_trigger_checkin(
                now, schedule, datetime(2026, 10, 16, 7)
            )
        )
        self.assertFalse(
            background._should_trigger_checkin(
                datetime(2026, 10, 16, 22, 1), schedule, None
            )
        )
        overnight = {"wakeup": time(22), "bedtime": time(6)}
        self.assertTrue(
            background._should_trigger_checkin(
                datetime(2026, 10, 17, 5, 30), overnight, None
            )
        )

    def test_monitor_start_is_idempotent_for_same_key(self):
        class FakeThread:
            instances = []

            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.started = False
                self.instances.append(self)

            def is_alive(self):
                return self.started

            def start(self):
                self.started = True

        key = "monitor-start-test"
        background.stop_background_monitor(key)
        FakeThread.instances.clear()

        with patch.object(background.threading, "Thread", FakeThread):
            first = background.start_background_monitor(
                lambda: {}, lambda: None, monitor_key=key
            )
            second = background.start_background_monitor(
                lambda: {}, lambda: None, monitor_key=key
            )
            background.stop_background_monitor(key)

        self.assertIs(first, second)
        self.assertEqual(len(FakeThread.instances), 1)
        self.assertTrue(first.kwargs["args"][2].is_set())

    def test_scheduler_loop_triggers_only_during_waking_hours(self):
        schedule = {"wakeup": time(7), "bedtime": time(22)}
        for now, expected_count in (
            (datetime(2026, 10, 16, 8), 1),
            (datetime(2026, 10, 16, 22, 1), 0),
        ):
            stop_event = background.threading.Event()
            alerts = []

            def stop_after_poll(interval):
                stop_event.set()
                return True

            with (
                patch.object(background, "datetime") as clock,
                patch.object(stop_event, "wait", side_effect=stop_after_poll),
            ):
                clock.now.side_effect = [now - timedelta(hours=1), now]
                background.run_safety_scheduler(
                    lambda: schedule, lambda: alerts.append(now), stop_event
                )

            self.assertEqual(len(alerts), expected_count)

    def test_scheduler_waits_an_hour_before_first_checkin(self):
        schedule = {"wakeup": time(7), "bedtime": time(22)}
        now_values = iter(
            [
                datetime(2026, 10, 16, 8),
                datetime(2026, 10, 16, 8),
                datetime(2026, 10, 16, 8, 59),
                datetime(2026, 10, 16, 9),
            ]
        )
        stop_event = background.threading.Event()
        alerts = []
        poll_count = 0

        def stop_after_three_polls(_):
            nonlocal poll_count
            poll_count += 1
            if poll_count == 3:
                stop_event.set()
            return True

        with (
            patch.object(background, "datetime") as clock,
            patch.object(stop_event, "wait", side_effect=stop_after_three_polls),
        ):
            clock.now.side_effect = lambda: next(now_values)
            background.run_safety_scheduler(
                lambda: schedule,
                lambda: alerts.append("check-in"),
                stop_event,
            )

        self.assertEqual(alerts, ["check-in"])


class AudioAlertTests(unittest.TestCase):
    def test_rms_measurement_uses_all_audio_samples(self):
        samples = [0.05, -0.05, 0.05, -0.05]

        rms, peak = audio._audio_levels(samples)

        self.assertAlmostEqual(rms, 0.05)
        self.assertAlmostEqual(peak, 0.05)

    def test_lower_rms_threshold_detects_sustained_noise(self):
        rms, peak = audio._audio_levels([0.045, -0.045] * 512)

        self.assertLess(rms, 0.05)
        self.assertTrue(audio._should_trigger_audio_alert(rms, peak, False))

    def test_short_high_peak_is_detected_but_small_click_is_not(self):
        sharp_noise = [0.0] * 1023 + [0.8]
        smaller_click = [0.0] * 1023 + [0.6]
        small_click = [0.0] * 1023 + [0.3]
        sharp_rms, sharp_peak = audio._audio_levels(sharp_noise)
        smaller_rms, smaller_peak = audio._audio_levels(smaller_click)
        click_rms, click_peak = audio._audio_levels(small_click)

        self.assertTrue(
            audio._should_trigger_audio_alert(sharp_rms, sharp_peak, False)
        )
        self.assertFalse(
            audio._should_trigger_audio_alert(smaller_rms, smaller_peak, False)
        )
        self.assertFalse(
            audio._should_trigger_audio_alert(click_rms, click_peak, False)
        )

    def test_audio_detector_rejects_quiet_sustained_background_noise(self):
        rms, peak = audio._audio_levels([0.03, -0.03] * 512)

        self.assertFalse(audio._should_trigger_audio_alert(rms, peak, False))
        louder_rms, louder_peak = audio._audio_levels([0.05, -0.05] * 512)
        self.assertTrue(
            audio._should_trigger_audio_alert(louder_rms, louder_peak, False)
        )

    def test_detector_latches_until_signal_is_quiet(self):
        rms, peak = audio._audio_levels([0.08, -0.08] * 512)

        self.assertTrue(audio._should_trigger_audio_alert(rms, peak, False))
        self.assertFalse(audio._should_trigger_audio_alert(rms, peak, True))
        quiet_rms, _ = audio._audio_levels([0.005, -0.005] * 512)
        self.assertLessEqual(quiet_rms, audio.RESET_THRESHOLD)

    def test_audio_detection_dispatches_to_dedicated_alert_route(self):
        class FakePage:
            def run_task(self, task):
                asyncio.run(task())

        calls = []
        page = FakePage()

        audio._dispatch_audio_alert(page, lambda: calls.append("audio"))

        self.assertEqual(calls, ["audio"])

    def test_audio_listener_stops_when_session_is_ended(self):
        stop_event = background.threading.Event()

        class InputStream:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.closed = False

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.closed = True

        stream = InputStream()
        stream_factory = Mock(return_value=stream)

        def stop_after_sleep(milliseconds):
            self.assertEqual(milliseconds, 100)
            stop_event.set()

        sounddevice = SimpleNamespace(
            InputStream=stream_factory,
            sleep=stop_after_sleep,
        )
        with patch.dict("sys.modules", {"sounddevice": sounddevice}):
            audio.start_listening(
                SimpleNamespace(run_task=lambda task: None),
                lambda: None,
                stop_event,
            )

        self.assertTrue(stream.closed)
        self.assertTrue(stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
