"""First-run introduction to CURA's main features."""

import flet as ft

if __package__:
    from .theme import C, apply_theme, card, primary_button, set_theme_rebuilder
else:
    from theme import C, apply_theme, card, primary_button, set_theme_rebuilder


SLIDES = (
    (
        ft.Icons.SCHEDULE_OUTLINED,
        "Routine check-ins",
        "Choose your usual wake-up and bedtime. CURA can check in about once an hour while you are awake.",
    ),
    (
        ft.Icons.VOLUME_UP_OUTLINED,
        "Loud-sound alerts",
        "CURA can ask if you're okay after a very loud sound. It measures sound levels; it does not record audio or identify specific sounds.",
    ),
    (
        ft.Icons.CONTACTS_OUTLINED,
        "Your safety details",
        "Keep your emergency contacts and daily schedule together, and review the check-ins you have answered.",
    ),
    (
        ft.Icons.LOCK_OUTLINE,
        "You stay in control",
        "Your account details stay on this device. Audio is analyzed on-device and is never saved or uploaded.",
    ),
)


def create_app_intro(page: ft.Page, on_complete):
    """Show a skippable, four-step feature walkthrough."""
    state = {"index": 0}

    def render():
        page.clean()
        page.overlay.clear()
        apply_theme(page)
        page.title = "CURA - Welcome"
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        set_theme_rebuilder(page, render)

        icon, title, body = SLIDES[state["index"]]
        last_slide = state["index"] == len(SLIDES) - 1

        def previous(_):
            if state["index"] > 0:
                state["index"] -= 1
                render()

        def next_slide(_):
            if last_slide:
                on_complete()
            else:
                state["index"] += 1
                render()

        dots = ft.Row(
            [
                ft.Container(
                    width=22 if index == state["index"] else 8,
                    height=8,
                    border_radius=8,
                    bgcolor=C.PRIMARY if index == state["index"] else C.BORDER,
                )
                for index in range(len(SLIDES))
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=7,
        )

        page.add(
            ft.SafeArea(
                expand=True,
                content=ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    padding=24,
                    content=ft.Column(
                        [
                            ft.Text("WELCOME TO CURA", size=12, weight=ft.FontWeight.W_700, color=C.PRIMARY),
                            card(
                                ft.Column(
                                    [
                                        ft.Container(
                                            content=ft.Icon(icon, size=38, color=C.PRIMARY),
                                            width=84,
                                            height=84,
                                            border_radius=26,
                                            bgcolor=C.PRIMARY_SOFT,
                                            alignment=ft.Alignment.CENTER,
                                        ),
                                        ft.Text(
                                            title,
                                            size=25,
                                            weight=ft.FontWeight.W_700,
                                            color=C.INK,
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                        ft.Text(
                                            body,
                                            size=15,
                                            color=C.MUTED,
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=18,
                                ),
                                padding=28,
                            ),
                            dots,
                            ft.Text(
                                f"{state['index'] + 1} of {len(SLIDES)}",
                                size=12,
                                color=C.MUTED,
                            ),
                            ft.Row(
                                [
                                    ft.TextButton(
                                        "Back",
                                        on_click=previous,
                                        disabled=state["index"] == 0,
                                    ),
                                    ft.Container(expand=True),
                                    ft.TextButton(
                                        "Skip", on_click=lambda e: on_complete()
                                    ),
                                    primary_button(
                                        "Get started" if last_slide else "Next",
                                        next_slide,
                                        icon=ft.Icons.CHECK if last_slide else ft.Icons.ARROW_FORWARD,
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=20,
                        width=min((page.width or 440) - 40, 460),
                    ),
                ),
            )
        )
        page.update()

    render()
