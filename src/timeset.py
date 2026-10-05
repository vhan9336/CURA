# timeset.py
import flet as ft
from src.database import users_db


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
      page.open(wakeup_picker)
    else:
      wakeup_picker.open = True
      page.update()

  def open_bedtime(e):
    if hasattr(page, "open"):
      page.open(bedtime_picker)
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
    if username in users_db and isinstance(users_db[username], dict):
      users_db[username]["first_login"] = False
    open_main_dashboard(page, username)

  save_button = ft.ElevatedButton(
      content="Save Schedule",
      color="white",
      bgcolor="blue",
      width=300,
      on_click=save_schedule,
  )

  is_first_time = users_db.get(username, {}).get("first_login", True)

  if is_first_time:
    header_text = f"Welcome {username}! Before we start... Set Your Daily Schedule"
  else:
    header_text = "Edit Your Daily Schedule"

  page.add(
      ft.Text(header_text, size=20, weight=ft.FontWeight.BOLD),
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


# --- Main Dashboard Layout with Sidebar Tabs ---
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

  def on_rail_change(e):
    selected_index = e.control.selected_index
    if selected_index == 0:
      load_info_view()
    elif selected_index == 1:
      load_settings_view()

  sidebar = ft.NavigationRail(
      selected_index=0,
      label_type=ft.NavigationRailLabelType.ALL,
      min_width=100,
      min_extended_width=180,
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