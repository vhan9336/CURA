# register_page.py
import flet as ft
from src.database import users_db


def create_register_view(page: ft.Page, on_switch_to_login):
  page.title = "Safety App - Register"
  page.clean()

  status_text = ft.Text("", size=16)

  username_field = ft.TextField(label="Username", width=300, autofocus=True)
  email_field = ft.TextField(label="Email", width=300)
  number_field = ft.TextField(label="Phone Number", width=300)
  e_contact1 = ft.TextField(label="Emergency Contact #1", width=300)
  e_contact2 = ft.TextField(label="Emergency Contact #2", width=300)
  password_field = ft.TextField(
      label="Password", password=True, can_reveal_password=True, width=300
  )

  def handle_register(e):
      print("Register button clicked!")
      entered_user = username_field.value
      entered_email = email_field.value
      entered_phone_number = number_field.value
      entered_econtact1 = e_contact1.value
      entered_econtact2 = e_contact2.value
      entered_pass = password_field.value

      if not entered_user or not entered_pass:
          status_text.value = "Please fill in username and password."
          status_text.color = "red"
          page.update()
      elif not entered_user.isalpha():
          status_text.value = "Please enter a valid username (letters only, no numbers)!"
          status_text.color = "red"
          page.update()
      elif entered_user in users_db:
          status_text.value = "Username already exists!"
          status_text.color = "red"
          page.update()
      elif entered_phone_number and not entered_phone_number.isdigit():
          status_text.value = "Please enter a valid phone number containing digits only!"
          status_text.color = "red"
          page.update()
      elif entered_econtact1 and not entered_econtact1.isdigit():
          status_text.value = "Please enter a valid Emergency Contact 1 containing digits only!"
          status_text.color = "red"
          page.update()
      elif entered_econtact2 and not entered_econtact2.isdigit():
          status_text.value = "Please enter a valid Emergency Contact 2 containing digits only!"
          status_text.color = "red"
          page.update()
      else:
          users_db[entered_user] = {
              "password": entered_pass,
              "email": entered_email,
              "phone": entered_phone_number,
              "e_contact1": entered_econtact1,
              "e_contact2": entered_econtact2,
          }
          status_text.value = "Registration Successful! Redirecting..."
          status_text.color = "green"
          page.update()
          on_switch_to_login()

  register_button = ft.ElevatedButton(
      content="Register",
      color="white",
      bgcolor="green",
      width=300,
      on_click=handle_register,
  )


  login_switch_button = ft.TextButton(
      content="Already have an account? Log In", on_click=on_switch_to_login
  )

  page.add(
      ft.Text("Create Account", size=24, weight=ft.FontWeight.BOLD),
      ft.Container(height=10),
      username_field,
      email_field,
      number_field,
      e_contact1,
      e_contact2,
      password_field,
      ft.Container(height=10),
      register_button,
      login_switch_button,
      status_text,
  )
  page.update()