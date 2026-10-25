# dashhome.py
import calendar
import os
import re
from datetime import date, datetime, time
from typing import Callable, Sequence

import flet as ft
import requests

if __package__:
    from .database import get_checkin_history, save_users_db, users_db
    from .theme import (
        C,
        apply_theme,
        card,
        fmt_time,
        hero_gradient,
        icon_badge,
        logo_badge,
        page_header,
        primary_button,
        set_theme_rebuilder,
    )
else:
    from database import get_checkin_history, save_users_db, users_db
    from theme import (
        C,
        apply_theme,
        card,
        fmt_time,
        hero_gradient,
        icon_badge,
        logo_badge,
        page_header,
        primary_button,
        set_theme_rebuilder,
    )

ASSISTANT_API_URL = os.environ.get(
    "CURA_API_URL", "https://cura-assistant-api.onrender.com"
).strip().rstrip("/")


def _request_assistant_reply(messages: Sequence[dict[str, str]]) -> str:
    if not ASSISTANT_API_URL:
        raise RuntimeError("CURA_API_URL is not configured.")
    response = requests.post(
        f"{ASSISTANT_API_URL}/assistant/chat",
        json={"messages": list(messages)},
        timeout=35,
    )
    response.raise_for_status()
    response_data = response.json()
    reply = response_data.get("reply") if isinstance(response_data, dict) else None
    if not isinstance(reply, str) or not reply.strip():
        raise ValueError("Assistant server returned an invalid reply.")
    return reply.strip()


def _assistant_failure_message(
    error: requests.RequestException | ValueError,
) -> str:
    if isinstance(error, ValueError):
        return "The digital helper returned an invalid response. Please try again."

    if isinstance(error, requests.HTTPError):
        status_code = (
            error.response.status_code if error.response is not None else None
        )
        if status_code == 429:
            return "The digital helper is busy. Please wait a moment and try again."
        if status_code == 502:
            return (
                "The digital helper's AI provider couldn't complete the request. "
                "Please try again shortly."
            )
        if status_code == 503:
            return (
                "The digital helper service is temporarily unavailable. "
                "Please try again later."
            )
        if status_code is not None and status_code >= 500:
            return (
                f"The digital helper server returned an error (HTTP {status_code}). "
                "Please try again later."
            )
        if status_code is not None:
            return (
                f"The digital helper couldn't process the request (HTTP {status_code}). "
                "Please check your message and try again."
            )

    if isinstance(error, requests.Timeout):
        return "The digital helper took too long to respond. Please try again."
    if isinstance(error, requests.ConnectionError):
        return (
            "Couldn't connect to the digital helper. Check your internet connection "
            "and try again."
        )
    return "The digital helper request failed. Please try again."


# Chat history per user, kept here so it survives theme changes and tab switches.
CHATS = {}


def _user_dict(username: str) -> dict:
    data = users_db.get(username)
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Schedule screen
# ---------------------------------------------------------------------------
def create_schedule_view(
    page: ft.Page,
    username: str = "",
    on_schedule_saved: Callable[[time, time], None] | None = None,
    on_logout: Callable[[], None] | None = None,
    initial_values: dict[str, str] | None = None,
):
    page.clean()
    page.overlay.clear()
    page.navigation_bar = None
    apply_theme(page)
    page.title = "CURA - Daily schedule"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    saved = _user_dict(username)
    state = {
        "wakeup": fmt_time(saved.get("wakeup_time"), "07:00 AM"),
        "bedtime": fmt_time(saved.get("bedtime_time"), "10:00 PM"),
    }
    if initial_values:
        state.update(initial_values)
    set_theme_rebuilder(
        page,
        lambda: create_schedule_view(
            page,
            username,
            on_schedule_saved,
            on_logout,
            dict(state),
        ),
    )

    wakeup_text = ft.Text(state["wakeup"], size=30, weight=ft.FontWeight.W_700, color=C.INK)
    bedtime_text = ft.Text(state["bedtime"], size=30, weight=ft.FontWeight.W_700, color=C.INK)

    def on_wakeup(e):
        if wakeup_picker.value:
            state["wakeup"] = wakeup_picker.value.strftime("%I:%M %p")
            wakeup_text.value = state["wakeup"]
            page.update()

    def on_bedtime(e):
        if bedtime_picker.value:
            state["bedtime"] = bedtime_picker.value.strftime("%I:%M %p")
            bedtime_text.value = state["bedtime"]
            page.update()

    wakeup_picker = ft.TimePicker(
        confirm_text="Confirm", help_text="Select wake-up time", on_change=on_wakeup
    )
    bedtime_picker = ft.TimePicker(
        confirm_text="Confirm", help_text="Select bedtime", on_change=on_bedtime
    )
    page.overlay.extend([wakeup_picker, bedtime_picker])

    def open_picker(picker):
        def handler(e):
            if hasattr(page, "open"):
                page.run_task(page.open, picker)
            else:
                picker.open = True
                page.update()
        return handler

    def time_tile(icon, label, time_text, picker):
        return card(
            ft.Row(
                [
                    icon_badge(icon),
                    ft.Column(
                        [ft.Text(label, size=13, color=C.MUTED), time_text],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.EDIT_OUTLINED, color=C.MUTED, size=20),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=open_picker(picker),
        )

    def save_schedule(e):
        try:
            wakeup_obj = datetime.strptime(state["wakeup"], "%I:%M %p").time()
            bedtime_obj = datetime.strptime(state["bedtime"], "%I:%M %p").time()
        except ValueError:
            schedule_error.value = "Choose valid wake-up and bedtime values."
            page.update()
            return
        if wakeup_obj == bedtime_obj:
            schedule_error.value = "Wake-up time and bedtime must be different."
            page.update()
            return
        if not isinstance(users_db.get(username), dict):
            users_db[username] = {}
        previous_info = dict(users_db[username])
        users_db[username]["wakeup_time"] = wakeup_obj
        users_db[username]["bedtime_time"] = bedtime_obj
        try:
            save_users_db(users_db)
        except OSError:
            users_db[username] = previous_info
            schedule_error.value = "Could not save your schedule. Please try again."
            page.update()
            return
        if on_schedule_saved is not None:
            on_schedule_saved(wakeup_obj, bedtime_obj)
        open_main_dashboard(page, username, on_logout=on_logout)

    schedule_error = ft.Text(size=13, color=C.ERROR)
    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Container(
                padding=24,
                expand=True,
                content=ft.Column(
                    [
                        ft.Container(height=16),
                        page_header(
                            "Your daily schedule",
                            "We'll check in around the times you're normally awake.",
                        ),
                        ft.Container(height=8),
                        time_tile(ft.Icons.WB_SUNNY_OUTLINED, "Wake-up time", wakeup_text, wakeup_picker),
                        time_tile(ft.Icons.NIGHTLIGHT_OUTLINED, "Bedtime", bedtime_text, bedtime_picker),
                        ft.Container(height=8),
                        ft.Row([primary_button("Save schedule", save_schedule, expand=True)]),
                        schedule_error,
                    ],
                    spacing=14,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
        )
    )
    page.update()


# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------
def open_main_dashboard(
    page: ft.Page,
    username: str = "",
    start_index: int = 0,
    on_logout: Callable[[], None] | None = None,
):
    _render_main_dashboard(page, username, start_index, on_logout)


def _render_main_dashboard(
    page: ft.Page,
    username: str = "",
    start_index: int = 0,
    on_logout: Callable[[], None] | None = None,
):
    page.clean()
    page.overlay.clear()
    apply_theme(page)
    page.title = "CURA"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START

    content_area = ft.Container(padding=ft.Padding(20, 20, 20, 0), expand=True)
    view_switcher = ft.AnimatedSwitcher(
        content=ft.Container(),
        duration=260,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
        transition=ft.AnimatedSwitcherTransition.FADE,
        expand=True,
    )
    content_area.content = view_switcher

    chat_state = CHATS.setdefault(username, {"transcript": [], "api": []})
    transcript = chat_state["transcript"]  # (sender, text, is_user)
    api_history = chat_state["api"]  # {"role": ..., "content": ...}

    # ----- Home ------------------------------------------------------------
    def load_info_view():
        info = _user_dict(username)
        wake = fmt_time(info.get("wakeup_time"), "not set")
        bedtime = fmt_time(info.get("bedtime_time"), "not set")

        def feature(icon, title, body, accent=C.PRIMARY):
            return card(
                ft.Row(
                    [
                        icon_badge(icon, color=accent, bg=C.PRIMARY_SOFT),
                        ft.Column(
                            [
                                ft.Text(
                                    title,
                                    size=16,
                                    weight=ft.FontWeight.W_600,
                                    color=C.INK,
                                ),
                                ft.Text(body, size=13, color=C.MUTED),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                    ],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=16,
            )

        view_switcher.content = ft.Column(
            [
                ft.Row(
                    [
                        logo_badge(60, 18),
                        ft.Column(
                            [
                                ft.Text(
                                    "CURA",
                                    size=14,
                                    weight=ft.FontWeight.W_700,
                                    color=C.PRIMARY,
                                ),
                                ft.Text(
                                    f"Welcome back, {username or 'there'}",
                                    size=22,
                                    weight=ft.FontWeight.W_700,
                                    color=C.INK,
                                ),
                            ],
                            spacing=2,
                        ),
                    ],
                    spacing=14,
                ),
                card(
                    ft.Column(
                        [
                            ft.Text(
                                "A little more peace of mind.",
                                size=24,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.WHITE,
                            ),
                            ft.Text(
                                "CURA checks in during your waking hours and can alert you "
                                "after a loud sound. You stay in control, every step of the way.",
                                size=14,
                                color=C.HERO_TEXT,
                            ),
                        ],
                        spacing=10,
                    ),
                    gradient=hero_gradient(),
                    padding=22,
                ),
                card(
                    ft.Column(
                        [
                            ft.Text(
                                "Your daily check-in window",
                                size=16,
                                weight=ft.FontWeight.W_600,
                                color=C.INK,
                            ),
                            ft.Row(
                                [
                                    icon_badge(ft.Icons.WB_SUNNY_OUTLINED),
                                    ft.Text(wake, size=15, color=C.INK, expand=True),
                                    ft.Icon(
                                        ft.Icons.ARROW_FORWARD,
                                        size=16,
                                        color=C.MUTED,
                                    ),
                                    ft.Text(bedtime, size=15, color=C.INK),
                                ],
                                spacing=10,
                            ),
                            ft.Text(
                                "Routine check-ins happen about once an hour in this window.",
                                size=13,
                                color=C.MUTED,
                            ),
                            ft.OutlinedButton(
                                content="Review my schedule",
                                icon=ft.Icons.EDIT_OUTLINED,
                                on_click=lambda e: create_schedule_view(
                                    page, username, on_logout=on_logout
                                ),
                            ),
                        ],
                        spacing=12,
                    )
                ),
                ft.Text(
                    "HOW CURA SUPPORTS YOU",
                    size=12,
                    weight=ft.FontWeight.W_700,
                    color=C.MUTED,
                ),
                feature(
                    ft.Icons.EVENT_AVAILABLE_OUTLINED,
                    "Hourly check-ins",
                    "Choose your wake-up time and bedtime. Overnight schedules work too.",
                ),
                feature(
                    ft.Icons.GRAPHIC_EQ,
                    "Sound-level alerts",
                    "CURA notices unusually loud sound and asks if you're okay; it does not "
                    "record audio or recognize speech.",
                    accent=C.ERROR,
                ),
                feature(
                    ft.Icons.SHIELD_OUTLINED,
                    "Your support details",
                    "Emergency contact details stay on this device for reference. CURA "
                    "doesn't automatically message or call anyone.",
                ),
                feature(
                    ft.Icons.HISTORY_OUTLINED,
                    "A private check-in history",
                    "See the days you responded to routine and sound check-ins.",
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.LOCK_OUTLINE,
                                color=C.PRIMARY,
                                size=20,
                            ),
                            ft.Text(
                                "Audio is analyzed on your device and is never saved.",
                                size=13,
                                color=C.INK,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                    ),
                    bgcolor=C.PRIMARY_SOFT,
                    padding=16,
                    border_radius=18,
                ),
                ft.Container(height=8),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        page.update()

    # ----- Check-in history -----------------------------------------------
    def load_history_view():
        history_error = ""
        try:
            entries = get_checkin_history(username)
        except ValueError as error:
            entries = []
            history_error = f"Your saved history could not be read: {error}"

        events_by_day: dict[date, list[dict[str, str]]] = {}
        for entry in entries:
            event_time = datetime.fromisoformat(entry["at"])
            if event_time.tzinfo is not None:
                event_time = event_time.astimezone()
            events_by_day.setdefault(event_time.date(), []).append(entry)

        for day_events in events_by_day.values():
            day_events.sort(
                key=lambda event: datetime.fromisoformat(event["at"]).timestamp()
            )

        state = {"month": date.today().replace(day=1), "selected": date.today()}
        month_label = ft.Text(
            size=17, weight=ft.FontWeight.W_600, color=C.INK
        )
        month_grid = ft.Column(spacing=4)
        selected_events = ft.Column(spacing=10)
        selected_title = ft.Text(
            size=16, weight=ft.FontWeight.W_600, color=C.INK
        )
        count_text = ft.Text(size=14, color=C.MUTED)

        def show_selected_day():
            selected = state["selected"]
            selected_title.value = f"{selected.strftime('%A, %B')} {selected.day}"
            day_events = events_by_day.get(selected, [])
            selected_events.controls = []
            if not day_events:
                selected_events.controls.append(
                    ft.Text("No check-ins recorded for this day.", color=C.MUTED)
                )
            else:
                for event in day_events:
                    event_time = datetime.fromisoformat(event["at"])
                    selected_events.controls.append(
                        ft.Row(
                            [
                                icon_badge(
                                    ft.Icons.EVENT_AVAILABLE_OUTLINED
                                    if event["kind"] == "routine"
                                    else ft.Icons.GRAPHIC_EQ,
                                    color=C.PRIMARY,
                                    bg=C.PRIMARY_SOFT,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Routine check-in"
                                            if event["kind"] == "routine"
                                            else "Sound check-in",
                                            weight=ft.FontWeight.W_600,
                                            color=C.INK,
                                        ),
                                        ft.Text(
                                            event_time.astimezone().strftime(
                                                "%I:%M %p"
                                            ),
                                            size=13,
                                            color=C.MUTED,
                                        ),
                                    ],
                                    spacing=2,
                                ),
                            ],
                            spacing=12,
                        )
                    )
            count_text.value = (
                f"{len(entries)} check-in"
                f"{'' if len(entries) == 1 else 's'} saved on this device"
            )
            page.update()

        def build_calendar():
            first_day = state["month"]
            month_label.value = first_day.strftime("%B %Y")
            month_grid.controls = [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                weekday,
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=C.MUTED,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            width=38,
                            alignment=ft.Alignment(0, 0),
                        )
                        for weekday in ("S", "M", "T", "W", "T", "F", "S")
                    ],
                    spacing=2,
                )
            ]
            weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(
                first_day.year, first_day.month
            )
            for week in weeks:
                day_controls = []
                for day_number in week:
                    if day_number == 0:
                        day_controls.append(ft.Container(width=38, height=44))
                        continue
                    current_day = first_day.replace(day=day_number)
                    has_events = current_day in events_by_day
                    selected = current_day == state["selected"]

                    def select_day(e, day=current_day):
                        state["selected"] = day
                        build_calendar()
                        show_selected_day()

                    day_controls.append(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        str(day_number),
                                        size=13,
                                        color=C.PRIMARY if selected else C.INK,
                                        weight=(
                                            ft.FontWeight.W_700
                                            if selected or has_events
                                            else ft.FontWeight.W_400
                                        ),
                                    ),
                                    ft.Container(
                                        width=5,
                                        height=5,
                                        border_radius=3,
                                        bgcolor=C.PRIMARY if has_events else None,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=1,
                            ),
                            width=38,
                            height=44,
                            border=ft.Border.all(
                                1, C.PRIMARY if selected else C.BORDER
                            ),
                            border_radius=12,
                            bgcolor=C.PRIMARY_SOFT if selected else C.SURFACE,
                            on_click=select_day,
                        )
                    )
                month_grid.controls.append(ft.Row(day_controls, spacing=2))

        def change_month(offset: int):
            current = state["month"]
            month_index = current.month - 1 + offset
            year = current.year + month_index // 12
            month = month_index % 12 + 1
            state["month"] = date(year, month, 1)
            build_calendar()
            page.update()

        history_error_text = ft.Text(
            history_error, size=13, color=C.ERROR
        )
        view_switcher.content = ft.Column(
            [
                page_header("Check-in history", "A private record saved on this device."),
                card(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.CHEVRON_LEFT,
                                        tooltip="Previous month",
                                        on_click=lambda e: change_month(-1),
                                    ),
                                    month_label,
                                    ft.IconButton(
                                        icon=ft.Icons.CHEVRON_RIGHT,
                                        tooltip="Next month",
                                        on_click=lambda e: change_month(1),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            month_grid,
                            ft.Text(
                                "Filled days include a check-in you responded to.",
                                size=12,
                                color=C.MUTED,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=16,
                ),
                card(
                    ft.Column(
                        [
                            selected_title,
                            selected_events,
                            ft.Divider(color=C.BORDER),
                            count_text,
                        ],
                        spacing=12,
                    )
                ),
                history_error_text,
                ft.Container(height=8),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        build_calendar()
        show_selected_day()

    # ----- Settings --------------------------------------------------------
    settings_error = ft.Text(size=13, color=C.ERROR)

    def load_settings_view():
        def info_row(icon, label, value):
            return ft.Row(
                [
                    ft.Icon(icon, color=C.MUTED, size=20),
                    ft.Column(
                        [
                            ft.Text(label, size=12, color=C.MUTED),
                            ft.Text(str(value), size=15, color=C.INK, selectable=True),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                ],
                spacing=14,
            )

        def section_title(text):
            return ft.Text(text, size=15, weight=ft.FontWeight.W_600, color=C.INK)

        info = _user_dict(username)
        wake = fmt_time(info.get("wakeup_time"), "Not set")
        bed = fmt_time(info.get("bedtime_time"), "Not set")
        contact1_field = ft.TextField(
            label="Emergency contact 1 (+country code)",
            value=str(info.get("e_contact1", "")),
            keyboard_type=ft.KeyboardType.PHONE,
            prefix_icon=ft.Icons.SHIELD_OUTLINED,
        )
        contact2_field = ft.TextField(
            label="Emergency contact 2 (+country code)",
            value=str(info.get("e_contact2", "")),
            keyboard_type=ft.KeyboardType.PHONE,
            prefix_icon=ft.Icons.SHIELD_OUTLINED,
        )

        def save_emergency_contacts(e):
            contact1 = (contact1_field.value or "").strip()
            contact2 = (contact2_field.value or "").strip()
            for contact in (contact1, contact2):
                if contact and not re.fullmatch(r"\+[1-9]\d{7,14}", contact):
                    settings_error.value = "Use international phone format, e.g. +14155550123."
                    page.update()
                    return
            previous = dict(info)
            info["e_contact1"] = contact1
            info["e_contact2"] = contact2
            if not isinstance(users_db.get(username), dict):
                users_db[username] = {}
            users_db[username].update(
                {"e_contact1": contact1, "e_contact2": contact2}
            )
            try:
                save_users_db(users_db)
            except OSError:
                for key in ("e_contact1", "e_contact2"):
                    if key in previous:
                        info[key] = previous[key]
                    else:
                        info.pop(key, None)
                settings_error.value = "Could not save emergency contacts. Please try again."
                page.update()
                return
            settings_error.value = "Emergency contacts saved."
            settings_error.color = C.OK
            load_settings_view()

        view_switcher.content = ft.Column(
            [
                page_header("Settings", "Your account and check-in details."),
                card(
                    ft.Row(
                        [
                            icon_badge(ft.Icons.BRIGHTNESS_6_OUTLINED),
                            ft.Column(
                                [
                                    ft.Text("Appearance", size=15, weight=ft.FontWeight.W_600, color=C.INK),
                                    ft.Text("Follows your device's light or dark theme", size=12, color=C.MUTED),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=14,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                ),
                card(
                    ft.Column(
                        [
                            section_title("Account"),
                            info_row(ft.Icons.PERSON_OUTLINE, "Username", username or "N/A"),
                            info_row(ft.Icons.MAIL_OUTLINE, "Email", info.get("email", "N/A")),
                            info_row(ft.Icons.PHONE_OUTLINED, "Phone", info.get("phone", "N/A")),
                        ],
                        spacing=16,
                    )
                ),
                card(
                    ft.Column(
                        [
                            section_title("Emergency contacts"),
                            ft.Text(
                                "CURA sends an SMS to these contacts only when you tap ‘I need help’. Include + and your country code.",
                                size=12,
                                color=C.MUTED,
                            ),
                            contact1_field,
                            contact2_field,
                            ft.OutlinedButton(
                                content="Save emergency contacts",
                                icon=ft.Icons.SAVE_OUTLINED,
                                on_click=save_emergency_contacts,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                            ),
                        ],
                        spacing=16,
                    )
                ),
                card(
                    ft.Column(
                        [
                            section_title("Daily schedule"),
                            info_row(ft.Icons.WB_SUNNY_OUTLINED, "Wake-up", wake),
                            info_row(ft.Icons.NIGHTLIGHT_OUTLINED, "Bedtime", bed),
                            ft.OutlinedButton(
                                content="Edit schedule",
                                icon=ft.Icons.EDIT_OUTLINED,
                                on_click=lambda e: create_schedule_view(
                                    page, username, on_logout=on_logout
                                ),
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                            ),
                        ],
                        spacing=16,
                    )
                ),
                card(
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.LOCK_OUTLINE, color=C.PRIMARY, size=20),
                            ft.Text(
                                "Sound levels are analyzed on this device only. Audio is never "
                                "recorded or uploaded.",
                                size=12,
                                color=C.INK,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    bgcolor=C.PRIMARY_SOFT,
                    padding=16,
                ),
                ft.Container(
                    content=ft.OutlinedButton(
                        content="Log out",
                        icon=ft.Icons.LOGOUT,
                        on_click=(
                            (lambda e: on_logout())
                            if on_logout is not None
                            else None
                        ),
                        disabled=on_logout is None,
                        style=ft.ButtonStyle(
                            color=C.ERROR,
                            shape=ft.RoundedRectangleBorder(radius=14),
                        ),
                        expand=True,
                    ),
                    padding=ft.Padding(0, 8, 0, 8),
                ),
                settings_error,
                ft.Container(height=8),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )
        page.update()

    # ----- Resources -------------------------------------------------------
    def load_resource_view():
        async def open_article(url):
            chrome_opener = getattr(page, "_cura_open_in_chrome", None)
            if chrome_opener is not None:
                await chrome_opener(url)
            else:
                await page.launch_url(url)

        def resource_card(image_url, title, description, link):
            return card(
                ft.Column(
                    [
                        ft.Container(
                            content=ft.Image(
                                src=image_url,
                                height=140,
                                fit=ft.BoxFit.COVER,
                                width=float("inf"),
                            ),
                            border_radius=12,
                            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        ),
                        ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=C.INK),
                        ft.Text(description, size=13, color=C.MUTED),
                        ft.TextButton(
                            content="Read article",
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e: page.run_task(open_article, link),
                            style=ft.ButtonStyle(color=C.PRIMARY),
                        ),
                    ],
                    spacing=8,
                ),
                padding=14,
            )

        view_switcher.content = ft.Column(
            [
                page_header(
                    "Resources",
                    "Social isolation is a leading cause of unnoticed deaths. These can help.",
                ),
                resource_card(
                    "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=600&auto=format&fit=crop&q=60",
                    "Understanding social isolation",
                    "What isolation is, why it matters, and approaches that help people reconnect.",
                    "https://www.cdc.gov/social-connectedness/data-research/promising-approaches/index.html",
                ),
                resource_card(
                    "https://fastly.picsum.photos/id/13/2500/1667.jpg?hmac=SoX9UoHhN8HyklRA4A3vcCWJMVtiBXUg0W4ljWTor7s",
                    "Coping with loneliness",
                    "Practical ways to cope with loneliness and build connections.",
                    "https://www.mentalhealth.org.uk/explore-mental-health/loneliness/help-and-advice",
                ),
                resource_card(
                    "https://images.unsplash.com/photo-1511632765486-a01980e01a18?w=600&auto=format&fit=crop&q=60",
                    "Tips for staying connected",
                    "Ideas for keeping in touch, finding shared activities, and building supportive relationships.",
                    "https://www.nia.nih.gov/health/loneliness-and-social-isolation/loneliness-and-social-isolation-tips-staying-connected",
                ),
                resource_card(
                    "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&auto=format&fit=crop&q=60",
                    "How isolation can affect health",
                    "Learn how loneliness and social isolation can affect mental and physical health.",
                    "https://www.cdc.gov/social-connectedness/risk-factors/index.html",
                ),
                resource_card(
                    "https://images.unsplash.com/photo-1517486808906-6ca8b3f04846?w=600&auto=format&fit=crop&q=60",
                    "Building stronger social connections",
                    "The U.S. Surgeon General’s guidance on strengthening connection in our lives and communities.",
                    "https://www.hhs.gov/surgeongeneral/reports-and-publications/connection/index.html",
                ),
                resource_card(
                    "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=600&auto=format&fit=crop&q=60",
                    "Loneliness and mental health: CDC findings",
                    "CDC research describes how loneliness and limited social support relate to mental health challenges.",
                    "https://www.cdc.gov/mmwr/volumes/73/wr/mm7324a1.htm",
                ),
                ft.Container(height=8),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )
        page.update()

    # ----- Chat ------------------------------------------------------------
    def load_chat_view():
        bubble_width = min((page.width or 400) * 0.75, 320)

        chat_list = ft.ListView(
            expand=True, spacing=10, auto_scroll=True, padding=ft.Padding(0, 8, 0, 8)
        )

        def build_bubble(sender: str, text: str, is_user: bool):
            if is_user:
                radius = ft.BorderRadius(18, 18, 18, 4)
                bg, fg = C.PRIMARY, C.ON_PRIMARY
                label_color = ft.Colors.with_opacity(0.75, C.ON_PRIMARY)
                shadow = None
            else:
                radius = ft.BorderRadius(18, 18, 4, 18)
                bg, fg, label_color = C.SURFACE, C.INK, C.MUTED
                shadow = ft.BoxShadow(
                    blur_radius=10,
                    color=ft.Colors.with_opacity(C.SHADOW, ft.Colors.BLACK),
                    offset=ft.Offset(0, 2),
                )
            return ft.Row(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(sender, size=11, weight=ft.FontWeight.W_600, color=label_color),
                                ft.Text(text, size=14, selectable=True, color=fg),
                            ],
                            tight=True,
                            spacing=3,
                        ),
                        bgcolor=bg,
                        padding=ft.Padding(14, 10, 14, 10),
                        border_radius=radius,
                        width=bubble_width,
                        shadow=shadow,
                    )
                ],
                alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,
            )

        typing_row = ft.Row(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.ProgressRing(width=14, height=14, stroke_width=2),
                            ft.Text("Thinking...", size=13, color=C.MUTED),
                        ],
                        spacing=10,
                        tight=True,
                    ),
                    bgcolor=C.SURFACE,
                    padding=ft.Padding(14, 10, 14, 10),
                    border_radius=18,
                )
            ]
        )

        def add_message(sender, text, is_user):
            transcript.append((sender, text, is_user))
            chat_list.controls.append(build_bubble(sender, text, is_user))
            page.update()

        def ask_ai(prompt_text: str):
            add_message("You", prompt_text, True)
            api_history.append({"role": "user", "content": prompt_text})

            if not ASSISTANT_API_URL:
                api_history.pop()
                add_message(
                    "System",
                    "The digital helper is not configured for this installation yet.",
                    False,
                )
                return

            chat_list.controls.append(typing_row)
            page.update()

            try:
                ai_reply = _request_assistant_reply(api_history[-12:])
                ai_reply = re.sub(r"<think>.*?</think>", "", ai_reply, flags=re.DOTALL)
                ai_reply = re.sub(r"<thinking>.*?</thinking>", "", ai_reply, flags=re.DOTALL).strip()

                api_history.append({"role": "assistant", "content": ai_reply})
                if typing_row in chat_list.controls:
                    chat_list.controls.remove(typing_row)
                add_message("Digital Helper", ai_reply, False)
            except (requests.RequestException, ValueError) as error:
                if typing_row in chat_list.controls:
                    chat_list.controls.remove(typing_row)
                if api_history and api_history[-1]["role"] == "user":
                    api_history.pop()
                add_message("System", _assistant_failure_message(error), False)

        def send_message(e):
            prompt_text = user_input.value.strip()
            if not prompt_text:
                return
            user_input.value = ""
            page.run_task(user_input.focus)
            ask_ai(prompt_text)

        def suggestion(text):
            return ft.Container(
                content=ft.Text(text, size=13, color=C.PRIMARY),
                bgcolor=C.PRIMARY_SOFT,
                padding=ft.Padding(14, 8, 14, 8),
                border_radius=20,
                on_click=lambda e: ask_ai(text),
            )

        user_input = ft.TextField(
            hint_text="Type a message...",
            expand=True,
            border_radius=24,
            filled=True,
            bgcolor=C.SURFACE,
            border_color=C.BORDER,
            focused_border_color=C.PRIMARY,
            content_padding=ft.Padding(18, 12, 18, 12),
            on_submit=send_message,
        )
        send_button = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=C.ON_PRIMARY,
            bgcolor=C.PRIMARY,
            tooltip="Send message",
            on_click=send_message,
        )

        if transcript:
            for sender, text, is_user in transcript:
                chat_list.controls.append(build_bubble(sender, text, is_user))
        else:
            chat_list.controls.append(
                ft.Column(
                    [
                        ft.Text(
                            "Hi, I'm here to help with the app, find nearby care, "
                            "or just talk. What's on your mind?",
                            size=14,
                            color=C.MUTED,
                        ),
                        ft.Row(
                            [
                                suggestion("How do check-ups work?"),
                                suggestion("Find a pharmacy"),
                                suggestion("I'm feeling stressed"),
                            ],
                            wrap=True,
                            spacing=8,
                            run_spacing=8,
                        ),
                    ],
                    spacing=12,
                )
            )

        view_switcher.content = ft.Column(
            [
                page_header("Digital helper"),
                chat_list,
                ft.Row(
                    [user_input, send_button],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
            ],
            expand=True,
            spacing=8,
        )
        page.update()

    # ----- Navigation ------------------------------------------------------
    views = [
        load_info_view,
        load_settings_view,
        load_history_view,
        load_resource_view,
        load_chat_view,
    ]

    selected_tab = {"index": start_index}

    def on_nav_change(e):
        selected_tab["index"] = e.control.selected_index
        views[selected_tab["index"]]()

    page.navigation_bar = ft.NavigationBar(
        selected_index=start_index,
        bgcolor=C.SURFACE,
        indicator_color=C.PRIMARY_SOFT,
        on_change=on_nav_change,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="Home"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="Settings"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.HISTORY_OUTLINED,
                selected_icon=ft.Icons.HISTORY,
                label="History",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.EXPLORE_OUTLINED,
                selected_icon=ft.Icons.EXPLORE,
                label="Resources",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.CHAT_BUBBLE_OUTLINE, selected_icon=ft.Icons.CHAT_BUBBLE, label="Helper"
            ),
        ],
    )

    page.add(ft.SafeArea(expand=True, content=content_area))
    views[start_index]()
    page.update()
    set_theme_rebuilder(
        page,
        lambda: _render_main_dashboard(
            page, username, selected_tab["index"], on_logout
        ),
    )
