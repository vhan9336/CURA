# login.py
import flet as ft
from src.database import users_db


def create_login_view(page: ft.Page, on_success_callback, on_switch_to_register):
  page.title = "Safety App - Login"
  page.clean()

  log_status = ft.Text("", size=16)
  log_username = ft.TextField(label="Username", width=300, autofocus=True)
  log_password = ft.TextField(
      label="Password", password=True, can_reveal_password=True, width=300
  )

  def handle_login(e):
    entered_user = log_username.value
    entered_pass = log_password.value

    user_data = users_db.get(entered_user)
    if user_data and isinstance(user_data, dict) and user_data.get("password") == entered_pass:
      log_status.value = "Login Successful! Loading dashboard..."
      log_status.color = "green"
      page.update()
      on_success_callback(entered_user)
    else:
      log_status.value = "Invalid username or password."
      log_status.color = "red"
      page.update()

  login_button = ft.ElevatedButton(
      content="Log In", color="white", bgcolor="blue", width=300, on_click=handle_login
  )

  register_switch_button = ft.TextButton(
      content="Don't have an account? Register", on_click=on_switch_to_register
  )

  page.add(
      ft.Text("Welcome Back", size=24, weight=ft.FontWeight.BOLD),
      ft.Container(height=10),
      log_username,
      log_password,
      ft.Container(height=10),
      login_button,
      register_switch_button,
      log_status,
  )
  page.update()