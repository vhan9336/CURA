# dashhome.py
import flet as ft
from database import users_db
from datetime import datetime
from openai import OpenAI

# Initialize your Groq/OpenAI client
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="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"
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


def create_schedule_view(page: ft.Page, username: str = ""):
    page.clean()
    page.title = "Safety App - Schedule Settings"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    wakeup_field = ft.TextField(
        label="Wakeup Time", value="07:00 AM", width=300, read_only=True
    )
    bedtime_field = ft.TextField(
        label="Bedtime", value="10:00 PM", width=300, read_only=True
    )
    status_text = ft.Text("", size=16)

    def handle_wakeup_change(e):
        if wakeup_picker.value:
            wakeup_field.value = wakeup_picker.value.strftime("%I:%M %p")
            page.update()

    def handle_bedtime_change(e):
        if bedtime_picker.value:
            bedtime_field.value = bedtime_picker.value.strftime("%I:%M %p")
            page.update()

    wakeup_picker = ft.TimePicker(
        confirm_text="Confirm",
        help_text="Select Wakeup Time",
        on_change=handle_wakeup_change,
    )
    bedtime_picker = ft.TimePicker(
        confirm_text="Confirm",
        help_text="Select Bedtime",
        on_change=handle_bedtime_change,
    )

    page.overlay.extend([wakeup_picker, bedtime_picker])

    def open_wakeup(e):
        if hasattr(page, "open"):
            page.run_task(page.open, wakeup_picker)  # Safely runs the coroutine synchronously
        else:
            wakeup_picker.open = True
            page.update()

    def open_bedtime(e):
        if hasattr(page, "open"):
            page.run_task(page.open, bedtime_picker)  # Safely runs the coroutine synchronously
        else:
            bedtime_picker.open = True
            page.update()

    wakeup_button = ft.ElevatedButton(
        content="Select Wakeup Time",
        icon="wb_sunny",
        width=300,
        on_click=open_wakeup,
    )
    bedtime_button = ft.ElevatedButton(
        content="Select Bedtime",
        icon="nightlight",
        width=300,
        on_click=open_bedtime,
    )

    def save_schedule(e):
        try:
            wakeup_obj = datetime.strptime(wakeup_field.value, "%I:%M %p").time()
            bedtime_obj = datetime.strptime(bedtime_field.value, "%I:%M %p").time()

            if username not in users_db:
                users_db[username] = {}

            users_db[username]["wakeup_time"] = wakeup_obj
            users_db[username]["bedtime_time"] = bedtime_obj

        except Exception as ex:
            print(f"Error saving schedule times: {ex}")

        open_main_dashboard(page, username)

    save_button = ft.ElevatedButton(
        content="Save Schedule",
        color="white",
        bgcolor="blue",
        width=300,
        on_click=save_schedule,
    )

    page.add(
        ft.Text("Set Your Daily Schedule", size=24, weight=ft.FontWeight.BOLD),
        ft.Container(height=10),
        wakeup_field,
        wakeup_button,
        ft.Container(height=10),
        bedtime_field,
        bedtime_button,
        ft.Container(height=10),
        save_button,
        status_text,
    )
    page.update()


def open_main_dashboard(page: ft.Page, username: str = ""):
    page.clean()
    page.title = "Safety App - Dashboard"

    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START

    content_area = ft.Container(
        content=ft.Text("", size=20),
        padding=20,
        expand=True,
    )

    user_info = (
        users_db.get(username, {})
        if isinstance(users_db.get(username), dict)
        else {}
    )

    def load_resource_view():
        content_area.content = ft.Column([
            ft.Text("Helpful Resources & Articles", size=24, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            ft.Text(
                "The leading cause of unnoticed deaths is social isolation. "
                "If you find yourself in these situations, here are some resources that will help:",
                size=16,
                width=350,
            ),
            ft.Container(height=15),
            ft.Container(
                content=ft.Image(
                    src="https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=600&auto=format&fit=crop&q=60",
                    width=300,
                    height=150,
                    fit=ft.BoxFit.COVER,
                ),
                border_radius=10,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ),
            ft.Container(height=10),
            ft.TextButton(
                content=ft.Text("🔗 Understanding Social Isolation (Article)", size=15, color=ft.Colors.BLUE),
                on_click=lambda e: page.launch_url(
                    "https://www.cdc.gov/social-connectedness/data-research/promising-approaches/index.html")
            ),
            ft.Container(height=15),
            ft.Container(
                content=ft.Image(
                    src="https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=600&auto=format&fit=crop&q=60",
                    width=300,
                    height=150,
                    fit=ft.BoxFit.COVER,
                ),
                border_radius=10,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ),
            ft.Container(height=10),
            ft.TextButton(
                content=ft.Text("🔗 Coping with Loneliness and Building Connections", size=15, color=ft.Colors.BLUE),
                on_click=lambda e: page.launch_url(
                    "https://www.mentalhealth.org.uk/explore-mental-health/a-z-topics/loneliness")
            ),
        ], scroll=ft.ScrollMode.AUTO)
        page.update()

    def load_info_view():
        content_area.content = ft.Column([
            ft.Text("Safety App Overview", size=24, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            ft.Text(
                "Welcome to App! On average, about 870,000 people pass away"
                " unnoticed each year due to not being able to reach help in time."
                " This app changes that - this app is your safety net for when you"
                " are struggling to reach help.",
                size=16,
                width=350,
            ),
        ])
        page.update()

    def load_settings_view():
        content_area.content = ft.Column([
            ft.Text("Account Settings & Info", size=24, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            ft.Text(f"Username: {username}", size=16),
            ft.Text(f"Email: {user_info.get('email', 'N/A')}", size=16),
            ft.Text(f"Phone Number: {user_info.get('phone', 'N/A')}", size=16),
            ft.Text(
                f"Emergency Contact 1: {user_info.get('e_contact1', 'N/A')}",
                size=16,
            ),
            ft.Text(
                f"Emergency Contact 2: {user_info.get('e_contact2', 'N/A')}",
                size=16,
            ),
            ft.Container(height=20),
            ft.ElevatedButton(
                content="Edit Schedule",
                on_click=lambda e: create_schedule_view(page, username),
            ),
            ft.Container(height=10),
            ft.Text(
                "This app continuously records background audio to detect abrupt "
                "changes in volume. This is not a threat to your safety in any way "
                "and we don't store recorded audio nor listen to conversations.",
                size=12,
                color=ft.Colors.GREY_700,
            ),
        ])
        page.update()

    def load_chat_view():
        chat_list = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=True,
            padding=10,
        )

        def add_message(sender: str, text: str, is_user: bool):
            bg_color = ft.Colors.BLUE_50 if is_user else ft.Colors.GREY_200
            align = ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START

            message_bubble = ft.Row(
                [
                    ft.Container(
                        content=ft.Column([
                            ft.Text(sender, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                            ft.Text(text, size=14, selectable=True)
                        ], tight=True),
                        bgcolor=bg_color,
                        padding=12,
                        border_radius=12,
                        width=350
                    )
                ],
                alignment=align,
            )
            chat_list.controls.append(message_bubble)
            page.update()

        def send_message(e):
            prompt_text = user_input.value.strip()
            if not prompt_text:
                return

            add_message("You", prompt_text, is_user=True)
            user_input.value = ""
            user_input.focus()
            page.update()

            try:
                response = client.chat.completions.create(
                    model="qwen/qwen3.6-27b",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt_text}
                    ],
                    temperature=0.3
                )
                ai_reply = response.choices[0].message.content

                # FIX: Clean out the model's markdown thinking blocks before displaying
                import re
                ai_reply = re.sub(r"<think>.*?</think>", "", ai_reply, flags=re.DOTALL)
                ai_reply = re.sub(r"<thinking>.*?</thinking>", "", ai_reply, flags=re.DOTALL)
                ai_reply = ai_reply.strip()  # Remove residual leading/trailing whitespaces

                add_message("Digital Helper", ai_reply, is_user=False)
            except Exception as ex:
                add_message("System", f"Error connecting to AI: {ex}", is_user=False)

        user_input = ft.TextField(
            hint_text="Ask about app features or medical resources...",
            expand=True,
            border_radius=20,
            filled=True,
            on_submit=send_message
        )

        send_button = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=ft.Colors.BLUE,
            tooltip="Send message",
            on_click=send_message,
        )

        input_row = ft.Row([user_input, send_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        content_area.content = ft.Column([
            ft.Text("Digital Health Helper", size=24, weight=ft.FontWeight.BOLD),
            ft.Container(height=5),
            chat_list,
            ft.Divider(height=1),
            input_row
        ], expand=True)
        page.update()

    def on_rail_change(e):
        selected_index = e.control.selected_index
        if selected_index == 0:
            load_info_view()
        elif selected_index == 1:
            load_settings_view()
        elif selected_index == 2:
            load_resource_view()
        elif selected_index == 3:
            load_chat_view()

    sidebar = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=75,
        min_extended_width=125,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.INFO_OUTLINE,
                selected_icon=ft.Icons.INFO,
                label="Info",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="Settings",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SEARCH,
                selected_icon=ft.Icons.SEARCH,
                label="Resources",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SMART_TOY_OUTLINED,
                selected_icon=ft.Icons.SMART_TOY,
                label="Digital Helper",
            ),
        ],
        on_change=on_rail_change,
    )

    main_layout = ft.Row(
        [sidebar, ft.VerticalDivider(width=1), content_area],
        expand=True,
    )

    page.add(main_layout)
    load_info_view()
    page.update()