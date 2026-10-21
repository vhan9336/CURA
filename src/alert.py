import asyncio
import flet as ft
from collections.abc import Callable

if __package__:
    from .database import record_checkin, users_db
    from .dashhome import open_main_dashboard
    from .help import help
    from .theme import (
        C,
        apply_theme,
        card,
        logo_badge,
        primary_button,
        set_theme_rebuilder,
    )
else:
    from database import record_checkin, users_db
    from dashhome import open_main_dashboard
    from help import help
    from theme import (
        C,
        apply_theme,
        card,
        logo_badge,
        primary_button,
        set_theme_rebuilder,
    )


def trigger_desktop_alert(page: ft.Page):
    if page.platform is None or not page.platform.is_desktop():
        return

    from plyer import notification

    notify = notification.notify
    if not callable(notify):
        raise RuntimeError("Desktop notifications are not available on this device.")
    notify(
        title="CURA Sound Check-In",
        message="A loud sound was detected. Are you okay?",
        app_name="CURA",
        timeout=10,
    )


def create_audio_alert_view(
    page: ft.Page,
    username: str = "",
    on_logout: Callable[[], None] | None = None,
    initial_responded: bool = False,
    initial_status: str = "",
):
    page.title = "CURA - Sound Check-In"
    page.clean()
    page.overlay.clear()
    page.navigation_bar = None
    apply_theme(page)
    status_text = ft.Text(
        initial_status, size=14, color=C.ERROR, text_align=ft.TextAlign.CENTER
    )
    responded = initial_responded
    help_requested = False

    set_theme_rebuilder(
        page,
        lambda: create_audio_alert_view(
            page, username, on_logout, responded, status_text.value or ""
        ),
    )

    def record_response() -> bool:
        nonlocal responded
        if responded:
            return True
        try:
            record_checkin(username, "sound")
        except (OSError, ValueError) as error:
            status_text.value = f"Couldn't save your response: {error}"
            page.update()
            return False
        responded = True
        return True

    def handle_ok(e):
        if record_response():
            open_main_dashboard(page, username, on_logout=on_logout)

    def handle_help(e):
        nonlocal help_requested
        if help_requested:
            return
        if record_response():
            help_requested = True
            info = users_db.get(username, {})
            contacts = [
                str(info.get(key, ""))
                for key in ("e_contact1", "e_contact2")
                if isinstance(info, dict) and info.get(key)
            ]
            status_text.value = "Sending an SMS alert to your emergency contacts…"
            status_text.color = C.MUTED
            help_button.disabled = True
            page.update()
            page.run_task(send_help_alert, username, contacts)

    async def send_help_alert(alert_username: str, contacts: list[str]):
        status_text.value = await asyncio.to_thread(
            help, alert_username, "sound", contacts
        )
        status_text.color = C.ERROR
        page.update()

    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=24,
                expand=True,
                content=card(
                    ft.Column(
                        [
                            ft.Container(
                                content=ft.Row(
                                    [
                                        logo_badge(60, 18),
                                        ft.Column(
                                            [
                                                ft.Text(
                                                    "SOUND CHECK-IN",
                                                    size=12,
                                                    weight=ft.FontWeight.W_700,
                                                    color=C.ERROR,
                                                ),
                                                ft.Text(
                                                    "A loud sound was picked up",
                                                    size=13,
                                                    color=C.MUTED,
                                                ),
                                            ],
                                            spacing=3,
                                        ),
                                    ],
                                    spacing=12,
                                ),
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Container(height=8),
                            ft.Text(
                                "We heard something loud.\nAre you safe?",
                                size=29,
                                weight=ft.FontWeight.W_700,
                                color=C.INK,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "This alert is based on sound level only. "
                                "CURA does not record or interpret conversations.",
                                size=14,
                                color=C.MUTED,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Container(height=6),
                            primary_button(
                                "I'm safe",
                                handle_ok,
                                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                                expand=True,
                            ),
                            (help_button := ft.OutlinedButton(
                                content="I need help",
                                icon=ft.Icons.SUPPORT_AGENT,
                                on_click=handle_help,
                                style=ft.ButtonStyle(
                                    color=C.ERROR,
                                    shape=ft.RoundedRectangleBorder(radius=16),
                                ),
                                expand=True,
                                height=54,
                            )),
                            status_text,
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        spacing=16,
                    ),
                    padding=26,
                ),
            ),
        ),
    )
    page.update()
    trigger_desktop_alert(page)


create_confirm_view = create_audio_alert_view
