from dataclasses import dataclass
from datetime import time
from typing import Literal, cast

import flet as ft

__all__ = ["CuraAndroid", "PermissionStatus", "ScheduleStatus"]


@dataclass(frozen=True)
class PermissionStatus:
    microphone: bool
    notifications: bool


@dataclass(frozen=True)
class ScheduleStatus:
    scheduled: bool
    accuracy: Literal["inexact", "disabled"]
    limitation: str


@ft.control("CuraAndroid")
class CuraAndroid(ft.Service):
    """Android-only CURA foreground microphone and local check-in service."""

    async def request_permissions(self) -> PermissionStatus:
        result = cast(dict[str, bool], await self._invoke_method("requestPermissions"))
        return PermissionStatus(
            microphone=result.get("microphone", False),
            notifications=result.get("notifications", False),
        )

    async def start_monitoring(self) -> None:
        """Start microphone capture while the app is foregrounded."""
        await self._invoke_method("startMonitoring")

    async def stop_monitoring(self) -> None:
        await self._invoke_method("stopMonitoring")

    async def microphone_level_dbfs(self) -> float | None:
        """Return the latest native RMS level in dBFS, or None if inactive."""
        level = await self._invoke_method("microphoneLevel")
        return float(level) if level is not None else None

    async def consume_audio_alert(self) -> bool:
        """Return and clear a loud-sound event captured by Android."""
        return bool(await self._invoke_method("consumeAudioAlert"))

    async def consume_checkin(self) -> bool:
        """Return and clear a scheduled check-in notification tap."""
        return bool(await self._invoke_method("consumeCheckin"))

    async def schedule_checkins(
        self, wake_time: time, bed_time: time
    ) -> ScheduleStatus:
        result = cast(
            dict[str, bool | str],
            await self._invoke_method(
                "scheduleCheckins",
                {
                    "wake": _format_time(wake_time),
                    "bed": _format_time(bed_time),
                },
            ),
        )
        accuracy = "inexact" if result.get("scheduled") else "disabled"
        return ScheduleStatus(
            scheduled=bool(result.get("scheduled", False)),
            accuracy=accuracy,
            limitation=str(result.get("limitation", "")),
        )

    async def cancel_checkins(self) -> None:
        await self._invoke_method("cancelCheckins")


def _format_time(value: time) -> str:
    if value.tzinfo is not None:
        raise ValueError("Wake and bed times must be local wall-clock times.")
    return f"{value.hour:02d}:{value.minute:02d}"
