# login.py
import flet as ft

if __package__:
    from .database import users_db, verify_password
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
    from database import users_db, verify_password
    from theme import (
        C,
        apply_theme,
        auth_banner,
        card,
        primary_button,
        set_theme_rebuilder,
        text_field,
    )


def create_login_view(
    page: ft.Page,
    on_success_callback,
    on_switch_to_register,
    initial_values: dict[str, str] | None = None,
):
    page.clean()
    page.overlay.clear()
    page.navigation_bar = None
    apply_theme(page)
    page.title = "CURA - Log in"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

    form_width = min((page.width or 440) - 40, 420)

    log_status = ft.Text("", size=13, text_align=ft.TextAlign.CENTER)
    log_username = text_field("Username", ft.Icons.PERSON_OUTLINE, autofocus=True)
    log_password = text_field("Password", ft.Icons.LOCK_OUTLINE, password=True)

    def handle_login(e):
        entered_user = log_username.value
        entered_pass = log_password.value

        user_data = users_db.get(entered_user)
        if (
            user_data
            and isinstance(user_data, dict)
            and verify_password(entered_pass or "", user_data.get("password"))
        ):
            log_status.value = "Login successful! Loading dashboard..."
            log_status.color = C.OK
            page.update()
            on_success_callback(entered_user)
        else:
            log_status.value = "Invalid username or password."
            log_status.color = C.ERROR
            page.update()

    log_password.on_submit = handle_login
    if initial_values:
        log_username.value = initial_values.get("username", "")
        log_password.value = initial_values.get("password", "")

    set_theme_rebuilder(
        page,
        lambda: create_login_view(
            page,
            on_success_callback,
            on_switch_to_register,
            {
                "username": log_username.value or "",
                "password": log_password.value or "",
            },
        ),
    )

    form = card(
        ft.Column(
            [
                ft.Text("Log in", size=20, weight=ft.FontWeight.W_700, color=C.INK),
                ft.Text(
                    "You'll stay signed in on this device until you choose Log out.",
                    size=13,
                    color=C.MUTED,
                ),
                log_username,
                log_password,
                ft.Container(height=2),
                ft.Row([primary_button("Log in", handle_login, expand=True)]),
                log_status,
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        padding=24,
    )

    page.add(
        ft.Column(
            [
                auth_banner(
                    "Welcome back",
                    "A little more peace of mind, one check-in at a time.",
                ),
                ft.Container(height=20),
                ft.Row(
                    [ft.Container(content=form, width=form_width)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.TextButton(
                            content="Don't have an account? Register",
                            on_click=on_switch_to_register,
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
