# dashhome.py
import asyncio
import os
import re
from datetime import datetime, time
from typing import Callable, Sequence

import flet as ft
import requests

if __package__:
    from .database import save_users_db, users_db
    from .theme import (
        C,
        apply_theme,
        card,
        fmt_time,
        hero_gradient,
        icon_badge,
        is_dark,
        page_header,
        primary_button,
        set_dark,
    )
else:
    from database import save_users_db, users_db
    from theme import (
        C,
        apply_theme,
        card,
        fmt_time,
        hero_gradient,
        icon_badge,
        is_dark,
        page_header,
        primary_button,
        set_dark,
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


# Chat history per user, kept here so it survives theme changes and tab switches.
CHATS = {}
CHECKUP_INTRO_STORAGE_KEY = "cura_checkup_intro_shown"


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
):
    page.clean()
    page.overlay.clear()
    page.navigation_bar = None
    apply_theme(page)
    page.title = "Safety App - Schedule"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    saved = _user_dict(username)
    state = {
        "wakeup": fmt_time(saved.get("wakeup_time"), "07:00 AM"),
        "bedtime": fmt_time(saved.get("bedtime_time"), "10:00 PM"),
    }

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
        open_main_dashboard(page, username)

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
def _show_checkup_intro(page: ft.Page, username: str, start_index: int):
    page.clean()
    page.overlay.clear()
    apply_theme(page)
    page.title = "Safety App - Routine Check-Ups"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=24,
                content=ft.Column(
                    [
                        ft.Text(
                            "Routine check-ups",
                            size=28,
                            weight=ft.FontWeight.W_700,
                            color=C.INK,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Between your wake-up time and bedtime, the app will "
                            "check in once each hour. When a check-up appears, "
                            "let us know that you're okay or ask for help.",
                            size=16,
                            color=C.MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Taking you to your dashboard shortly...",
                            size=13,
                            color=C.MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
            ),
        )
    )
    page.update()

    async def continue_to_dashboard():
        await asyncio.sleep(5)
        _render_main_dashboard(page, username, start_index)

    page.run_task(continue_to_dashboard)


def open_main_dashboard(page: ft.Page, username: str = "", start_index: int = 0):
    async def show_intro_or_dashboard():
        intro_shown = await page.shared_preferences.get(CHECKUP_INTRO_STORAGE_KEY)
        if intro_shown is not True:
            saved = await page.shared_preferences.set(CHECKUP_INTRO_STORAGE_KEY, True)
            if not saved:
                raise RuntimeError("Could not save the check-up introduction status.")
            _show_checkup_intro(page, username, start_index)
            return
        _render_main_dashboard(page, username, start_index)

    page.run_task(show_intro_or_dashboard)


def _render_main_dashboard(page: ft.Page, username: str = "", start_index: int = 0):
    user_info = _user_dict(username)
    set_dark(bool(user_info.get("dark_mode", False)))

    page.clean()
    page.overlay.clear()
    apply_theme(page)
    page.title = "Safety App - Dashboard"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START

    content_area = ft.Container(padding=ft.Padding(20, 20, 20, 0), expand=True)

    chat_state = CHATS.setdefault(username, {"transcript": [], "api": []})
    transcript = chat_state["transcript"]  # (sender, text, is_user)
    api_history = chat_state["api"]  # {"role": ..., "content": ...}

    # ----- Home ------------------------------------------------------------
    def load_info_view():
        def feature(icon, title, body):
            return ft.Row(
                [
                    icon_badge(icon),
                    ft.Column(
                        [
                            ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=C.INK),
                            ft.Text(body, size=13, color=C.MUTED),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )

        content_area.content = ft.Column(
            [
                page_header("Welcome", "Your safety net when reaching help is hard."),
                card(
                    ft.Column(
                        [
                            ft.Text("870,000", size=42, weight=ft.FontWeight.W_800, color=ft.Colors.WHITE),
                            ft.Text(
                                "people pass away unnoticed each year because they couldn't "
                                "reach help in time. This app is here to change that.",
                                size=14,
                                color=C.HERO_TEXT,
                            ),
                        ],
                        spacing=6,
                    ),
                    gradient=hero_gradient(),
                    padding=24,
                ),
                card(
                    ft.Column(
                        [
                            feature(
                                ft.Icons.EVENT_AVAILABLE_OUTLINED,
                                "Routine check-ups",
                                "Regular check-ins based on your wake-up and bedtime.",
                            ),
                            feature(
                                ft.Icons.GRAPHIC_EQ,
                                "Background monitoring",
                                "Listens for sudden changes in volume to notice when something is wrong.",
                            ),
                            feature(
                                ft.Icons.CONTACT_PHONE_OUTLINED,
                                "Emergency contacts",
                                "People we reach out to if you can't respond.",
                            ),
                        ],
                        spacing=18,
                    )
                ),
                ft.Container(height=8),
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
        )
        page.update()

    # ----- Settings --------------------------------------------------------
    settings_error = ft.Text(size=13, color=C.ERROR)

    def toggle_dark(e):
        value = bool(e.control.value)
        set_dark(value)
        if not isinstance(users_db.get(username), dict):
            users_db[username] = {}
        users_db[username]["dark_mode"] = value
        try:
            save_users_db(users_db)
        except OSError:
            users_db[username]["dark_mode"] = not value
            set_dark(not value)
            e.control.value = not value
            settings_error.value = "Could not save this setting. Please try again."
            page.update()
            return
        open_main_dashboard(page, username, start_index=1)

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

        content_area.content = ft.Column(
            [
                page_header("Settings", "Your account and check-in details."),
                card(
                    ft.Row(
                        [
                            icon_badge(ft.Icons.DARK_MODE_OUTLINED),
                            ft.Column(
                                [
                                    ft.Text("Dark mode", size=15, weight=ft.FontWeight.W_600, color=C.INK),
                                    ft.Text("Easier on the eyes at night", size=12, color=C.MUTED),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Switch(value=is_dark(), on_change=toggle_dark),
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
                            info_row(ft.Icons.SHIELD_OUTLINED, "Contact 1", info.get("e_contact1", "N/A")),
                            info_row(ft.Icons.SHIELD_OUTLINED, "Contact 2", info.get("e_contact2", "N/A")),
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
                                on_click=lambda e: create_schedule_view(page, username),
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
                                "The app listens in the background only to detect abrupt changes "
                                "in volume. Audio is never stored and conversations are never listened to.",
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
                settings_error,
                ft.Container(height=8),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )
        page.update()

    # ----- Resources -------------------------------------------------------
    def load_resource_view():
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
                            on_click=lambda e: page.launch_url(link),
                            style=ft.ButtonStyle(color=C.PRIMARY),
                        ),
                    ],
                    spacing=8,
                ),
                padding=14,
            )

        content_area.content = ft.Column(
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
                    "https://www.mentalhealth.org.uk/explore-mental-health/a-z-topics/loneliness",
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
            except (requests.RequestException, ValueError):
                if typing_row in chat_list.controls:
                    chat_list.controls.remove(typing_row)
                if api_history and api_history[-1]["role"] == "user":
                    api_history.pop()
                add_message(
                    "System",
                    "Couldn't reach the assistant. Check your connection and try again.",
                    False,
                )

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

        content_area.content = ft.Column(
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
    views = [load_info_view, load_settings_view, load_resource_view, load_chat_view]

    def on_nav_change(e):
        views[e.control.selected_index]()

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
                icon=ft.Icons.EXPLORE_OUTLINED, selected_icon=ft.Icons.EXPLORE, label="Resources"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.CHAT_BUBBLE_OUTLINE, selected_icon=ft.Icons.CHAT_BUBBLE, label="Helper"
            ),
        ],
    )

    page.add(ft.SafeArea(expand=True, content=content_area))
    views[start_index]()
    page.update()