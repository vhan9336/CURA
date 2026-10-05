# dashhome.py
import os
import re
from datetime import datetime

import flet as ft
from openai import OpenAI

from database import users_db

# ---------------------------------------------------------------------------
# AI client  (key now comes from an environment variable, never from source)
#   Windows:   setx GROQ_API_KEY "your-new-key"
#   macOS/Lin: export GROQ_API_KEY="your-new-key"
# ---------------------------------------------------------------------------
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY", "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"),
)

SYSTEM_PROMPT = """
You are an embedded digital health companion for this Safety and Check-Up Application.
Your ONLY purpose is to help the user with tasks relevant to this app's purpose:
1. Explaining how the app's features work (e.g., routine check-ups, background monitoring, schedule settings).
2. Guiding them on how to update their wakeup/bedtime schedule or emergency contacts.
3. Helping them locate nearby pharmacies or urgent care centers when requested.
4. "Giving mental health tips when needed and acting as a therapeutic companion"

Strict Guidelines:
- If a user asks about unrelated topics (e.g., coding help, general trivia, history, recipes, or creative writing), politely decline and remind them that you are here to assist with their safety app usage and health resources.
- Always maintain a supportive, clear, and concise tone.
"""

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
PRIMARY = ft.Colors.TEAL_700
PRIMARY_SOFT = ft.Colors.TEAL_50
INK = ft.Colors.BLUE_GREY_900
MUTED = ft.Colors.BLUE_GREY_500
SURFACE = ft.Colors.WHITE
BACKGROUND = "#F4F7F7"


def apply_theme(page: ft.Page):
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BACKGROUND
    page.padding = 0


def card(content, bgcolor=SURFACE, padding=18, on_click=None):
    """A soft rounded surface used for all grouped content."""
    return ft.Container(
        content=content,
        bgcolor=bgcolor,
        padding=padding,
        border_radius=16,
        on_click=on_click,
        shadow=ft.BoxShadow(
            blur_radius=14,
            color=ft.Colors.with_opacity(0.06, ft.Colors.BLACK),
            offset=ft.Offset(0, 3),
        ),
    )


def page_header(title: str, subtitle: str = ""):
    controls = [ft.Text(title, size=26, weight=ft.FontWeight.W_700, color=INK)]
    if subtitle:
        controls.append(ft.Text(subtitle, size=14, color=MUTED))
    return ft.Column(controls, spacing=4)


def icon_badge(icon, color=PRIMARY, bg=PRIMARY_SOFT):
    return ft.Container(
        content=ft.Icon(icon, color=color, size=22),
        bgcolor=bg,
        width=44,
        height=44,
        border_radius=12,
        alignment=ft.Alignment(0, 0),
    )


def primary_button(text, on_click, icon=None, expand=False):
    return ft.FilledButton(
        content=text,
        icon=icon,
        on_click=on_click,
        expand=expand,
        height=50,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=14),
            bgcolor=PRIMARY,
            color=ft.Colors.WHITE,
        ),
    )


def fmt_time(value, default: str) -> str:
    """users_db stores datetime.time objects; show them as '07:00 AM'."""
    try:
        return value.strftime("%I:%M %p")
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Schedule screen
# ---------------------------------------------------------------------------
def create_schedule_view(page: ft.Page, username: str = ""):
    page.clean()
    page.navigation_bar = None
    apply_theme(page)
    page.title = "Safety App - Schedule"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    saved = users_db.get(username, {}) if isinstance(users_db.get(username), dict) else {}
    state = {
        "wakeup": fmt_time(saved.get("wakeup_time"), "07:00 AM"),
        "bedtime": fmt_time(saved.get("bedtime_time"), "10:00 PM"),
    }

    wakeup_text = ft.Text(state["wakeup"], size=30, weight=ft.FontWeight.W_700, color=INK)
    bedtime_text = ft.Text(state["bedtime"], size=30, weight=ft.FontWeight.W_700, color=INK)

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
                        [ft.Text(label, size=13, color=MUTED), time_text],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.EDIT_OUTLINED, color=MUTED, size=20),
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
            if username not in users_db or not isinstance(users_db[username], dict):
                users_db[username] = {}
            users_db[username]["wakeup_time"] = wakeup_obj
            users_db[username]["bedtime_time"] = bedtime_obj
        except Exception as ex:
            print(f"Error saving schedule times: {ex}")
        open_main_dashboard(page, username)

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
def open_main_dashboard(page: ft.Page, username: str = ""):
    page.clean()
    apply_theme(page)
    page.title = "Safety App - Dashboard"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START

    user_info = (
        users_db.get(username, {}) if isinstance(users_db.get(username), dict) else {}
    )

    content_area = ft.Container(padding=ft.Padding(20, 20, 20, 0), expand=True)

    # Chat history lives here so it survives switching tabs.
    transcript = []  # list of (sender, text, is_user)
    api_history = []  # list of {"role": ..., "content": ...}

    # ----- Info ------------------------------------------------------------
    def load_info_view():
        def feature(icon, title, body):
            return ft.Row(
                [
                    icon_badge(icon),
                    ft.Column(
                        [
                            ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=INK),
                            ft.Text(body, size=13, color=MUTED),
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
                            ft.Text(
                                "870,000",
                                size=40,
                                weight=ft.FontWeight.W_800,
                                color=ft.Colors.WHITE,
                            ),
                            ft.Text(
                                "people pass away unnoticed each year because they couldn't "
                                "reach help in time. This app is here to change that.",
                                size=14,
                                color=ft.Colors.TEAL_50,
                            ),
                        ],
                        spacing=6,
                    ),
                    bgcolor=PRIMARY,
                    padding=22,
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
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
        )
        page.update()

    # ----- Settings --------------------------------------------------------
    def load_settings_view():
        def info_row(icon, label, value):
            return ft.Row(
                [
                    ft.Icon(icon, color=MUTED, size=20),
                    ft.Column(
                        [
                            ft.Text(label, size=12, color=MUTED),
                            ft.Text(str(value), size=15, color=INK, selectable=True),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                ],
                spacing=14,
            )

        wake = fmt_time(user_info.get("wakeup_time"), "Not set")
        bed = fmt_time(user_info.get("bedtime_time"), "Not set")

        content_area.content = ft.Column(
            [
                page_header("Settings", "Your account and check-in details."),
                card(
                    ft.Column(
                        [
                            info_row(ft.Icons.PERSON_OUTLINE, "Username", username or "N/A"),
                            info_row(ft.Icons.MAIL_OUTLINE, "Email", user_info.get("email", "N/A")),
                            info_row(ft.Icons.PHONE_OUTLINED, "Phone", user_info.get("phone", "N/A")),
                        ],
                        spacing=16,
                    )
                ),
                card(
                    ft.Column(
                        [
                            ft.Text("Emergency contacts", size=15, weight=ft.FontWeight.W_600, color=INK),
                            info_row(ft.Icons.SHIELD_OUTLINED, "Contact 1", user_info.get("e_contact1", "N/A")),
                            info_row(ft.Icons.SHIELD_OUTLINED, "Contact 2", user_info.get("e_contact2", "N/A")),
                        ],
                        spacing=16,
                    )
                ),
                card(
                    ft.Column(
                        [
                            ft.Text("Daily schedule", size=15, weight=ft.FontWeight.W_600, color=INK),
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
                            ft.Icon(ft.Icons.LOCK_OUTLINE, color=PRIMARY, size=20),
                            ft.Text(
                                "The app listens in the background only to detect abrupt changes "
                                "in volume. Audio is never stored and conversations are never listened to.",
                                size=12,
                                color=INK,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    bgcolor=PRIMARY_SOFT,
                    padding=16,
                ),
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
                        ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=INK),
                        ft.Text(description, size=13, color=MUTED),
                        ft.TextButton(
                            content="Read article",
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e: page.launch_url(link),
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

        chat_list = ft.ListView(expand=True, spacing=10, auto_scroll=True, padding=ft.Padding(0, 8, 0, 8))

        def build_bubble(sender: str, text: str, is_user: bool):
            return ft.Row(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(sender, size=11, weight=ft.FontWeight.W_600,
                                        color=ft.Colors.TEAL_50 if is_user else MUTED),
                                ft.Text(text, size=14, selectable=True,
                                        color=ft.Colors.WHITE if is_user else INK),
                            ],
                            tight=True,
                            spacing=3,
                        ),
                        bgcolor=PRIMARY if is_user else SURFACE,
                        padding=ft.Padding(14, 10, 14, 10),
                        border_radius=ft.BorderRadius(18, 18, 4 if is_user else 18, 18 if is_user else 4),
                        width=bubble_width,
                        shadow=None if is_user else ft.BoxShadow(
                            blur_radius=8,
                            color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
                            offset=ft.Offset(0, 2),
                        ),
                    )
                ],
                alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,
            )

        typing_row = ft.Row(
            [
                ft.Container(
                    content=ft.Row(
                        [ft.ProgressRing(width=14, height=14, stroke_width=2),
                         ft.Text("Thinking...", size=13, color=MUTED)],
                        spacing=10,
                        tight=True,
                    ),
                    bgcolor=SURFACE,
                    padding=ft.Padding(14, 10, 14, 10),
                    border_radius=18,
                )
            ]
        )

        def add_message(sender, text, is_user, remember=True):
            if remember:
                transcript.append((sender, text, is_user))
            chat_list.controls.append(build_bubble(sender, text, is_user))
            page.update()

        def ask_ai(prompt_text: str):
            add_message("You", prompt_text, True)
            api_history.append({"role": "user", "content": prompt_text})

            chat_list.controls.append(typing_row)
            page.update()

            try:
                response = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + api_history[-12:],
                    temperature=0.3,
                )
                ai_reply = response.choices[0].message.content or ""
                ai_reply = re.sub(r"<think>.*?</think>", "", ai_reply, flags=re.DOTALL)
                ai_reply = re.sub(r"<thinking>.*?</thinking>", "", ai_reply, flags=re.DOTALL).strip()

                api_history.append({"role": "assistant", "content": ai_reply})
                chat_list.controls.remove(typing_row)
                add_message("Digital Helper", ai_reply, False)
            except Exception as ex:
                if typing_row in chat_list.controls:
                    chat_list.controls.remove(typing_row)
                if api_history and api_history[-1]["role"] == "user":
                    api_history.pop()
                add_message(
                    "System",
                    f"Couldn't reach the assistant. Check your connection and try again. ({ex})",
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
                content=ft.Text(text, size=13, color=PRIMARY),
                bgcolor=PRIMARY_SOFT,
                padding=ft.Padding(14, 8, 14, 8),
                border_radius=20,
                on_click=lambda e: ask_ai(text),
            )

        user_input = ft.TextField(
            hint_text="Type a message...",
            expand=True,
            border_radius=24,
            filled=True,
            bgcolor=SURFACE,
            border_color=ft.Colors.TRANSPARENT,
            content_padding=ft.Padding(18, 12, 18, 12),
            on_submit=send_message,
        )
        send_button = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=ft.Colors.WHITE,
            bgcolor=PRIMARY,
            tooltip="Send message",
            on_click=send_message,
        )

        # Restore earlier messages, or show a friendly starting point.
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
                            color=MUTED,
                        ),
                        ft.Row(
                            [
                                suggestion("How do check-ups work?"),
                                suggestion("Find a pharmacy"),
                            ],
                            wrap=True,
                            spacing=8,
                            run_spacing=8,
                        ),
                        ft.Row(
                            [suggestion("I'm feeling stressed")],
                            wrap=True,
                        ),
                    ],
                    spacing=12,
                )
            )

        content_area.content = ft.Column(
            [
                page_header("Digital helper"),
                chat_list,
                ft.Row([user_input, send_button], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
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
        selected_index=0,
        bgcolor=SURFACE,
        indicator_color=PRIMARY_SOFT,
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
    load_info_view()
    page.update()