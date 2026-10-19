# register_page.py
import flet as ft

if __package__:
    from .database import hash_password, save_users_db, users_db
    from .theme import (
        C,
        apply_theme,
        auth_banner,
        card,
        primary_button,
        set_theme_rebuilder,
        text_field,
    )
else:
    from database import hash_password, save_users_db, users_db
    from theme import (
        C,
        apply_theme,
        auth_banner,
        card,
        primary_button,
        set_theme_rebuilder,
        text_field,
    )


def create_register_view(
    page: ft.Page,
    on_switch_to_login,
    initial_values: dict[str, str] | None = None,
):
    page.clean()
    page.overlay.clear()
    page.navigation_bar = None
    apply_theme(page)
    page.title = "CURA - Create account"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

    form_width = min((page.width or 440) - 40, 420)

    status_text = ft.Text("", size=13, text_align=ft.TextAlign.CENTER)

    username_field = text_field("Username", ft.Icons.PERSON_OUTLINE, autofocus=True)
    email_field = text_field("Email", ft.Icons.MAIL_OUTLINE, keyboard_type=ft.KeyboardType.EMAIL)
    number_field = text_field("Phone number", ft.Icons.PHONE_OUTLINED, keyboard_type=ft.KeyboardType.PHONE)
    e_contact1 = text_field("Emergency contact #1", ft.Icons.SHIELD_OUTLINED, keyboard_type=ft.KeyboardType.PHONE)
    e_contact2 = text_field("Emergency contact #2", ft.Icons.SHIELD_OUTLINED, keyboard_type=ft.KeyboardType.PHONE)
    password_field = text_field("Password", ft.Icons.LOCK_OUTLINE, password=True)

    def show_error(message: str):
        status_text.value = message
        status_text.color = C.ERROR
        page.update()

    def handle_register(e):
        entered_user = username_field.value
        entered_email = email_field.value
        entered_phone_number = number_field.value
        entered_econtact1 = e_contact1.value
        entered_econtact2 = e_contact2.value
        entered_pass = password_field.value

        if not entered_user or not entered_pass:
            show_error("Please fill in username and password.")
        elif not entered_user.isalpha():
            show_error("Please enter a valid username (letters only, no numbers)!")
        elif entered_user in users_db:
            show_error("Username already exists!")
        elif entered_phone_number and not entered_phone_number.isdigit():
            show_error("Please enter a valid phone number containing digits only!")
        elif entered_econtact1 and not entered_econtact1.isdigit():
            show_error("Please enter a valid Emergency Contact 1 containing digits only!")
        elif entered_econtact2 and not entered_econtact2.isdigit():
            show_error("Please enter a valid Emergency Contact 2 containing digits only!")
        else:
            users_db[entered_user] = {
                "password": hash_password(entered_pass),
                "email": entered_email,
                "phone": entered_phone_number,
                "e_contact1": entered_econtact1,
                "e_contact2": entered_econtact2,
            }
            try:
                save_users_db(users_db)
            except OSError as error:
                users_db.pop(entered_user, None)
                show_error(f"Could not save account data: {error}")
                return
            status_text.value = "Registration successful! Redirecting..."
            status_text.color = C.OK
            page.update()
            on_switch_to_login()

    password_field.on_submit = handle_register
    if initial_values:
        username_field.value = initial_values.get("username", "")
        email_field.value = initial_values.get("email", "")
        number_field.value = initial_values.get("phone", "")
        e_contact1.value = initial_values.get("contact1", "")
        e_contact2.value = initial_values.get("contact2", "")
        password_field.value = initial_values.get("password", "")

    set_theme_rebuilder(
        page,
        lambda: create_register_view(
            page,
            on_switch_to_login,
            {
                "username": username_field.value or "",
                "email": email_field.value or "",
                "phone": number_field.value or "",
                "contact1": e_contact1.value or "",
                "contact2": e_contact2.value or "",
                "password": password_field.value or "",
            },
        ),
    )

    def section_label(text: str, hint: str = ""):
        controls = [ft.Text(text, size=15, weight=ft.FontWeight.W_600, color=C.INK)]
        if hint:
            controls.append(ft.Text(hint, size=12, color=C.MUTED))
        return ft.Column(controls, spacing=2)

    form = card(
        ft.Column(
            [
                section_label("Account"),
                username_field,
                password_field,
                ft.Container(height=4),
                section_label("Contact details"),
                email_field,
                number_field,
                ft.Container(height=4),
                section_label(
                    "Emergency contacts",
                    "People we'll reach out to if you can't respond. Digits only.",
                ),
                e_contact1,
                e_contact2,
                ft.Container(height=4),
                ft.Row([primary_button("Create account", handle_register, expand=True)]),
                status_text,
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        padding=24,
    )

    page.add(
        ft.Column(
            [
                auth_banner(
                    "Create your CURA account",
                    "A personal safety companion, set up your way.",
                ),
                ft.Container(height=20),
                ft.Row(
                    [ft.Container(content=form, width=form_width)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.TextButton(
                            content="Already have an account? Log in",
                            on_click=on_switch_to_login,
                            style=ft.ButtonStyle(color=C.PRIMARY),
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=16),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    )
    page.update()