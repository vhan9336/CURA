# theme.py
"""Shared look & feel for every screen, with light and dark palettes."""
import flet as ft

LIGHT = dict(
    BG="#F3F7F7",
    SURFACE="#FFFFFF",
    INK=ft.Colors.BLUE_GREY_900,
    MUTED=ft.Colors.BLUE_GREY_500,
    PRIMARY=ft.Colors.TEAL_700,
    PRIMARY_SOFT=ft.Colors.TEAL_50,
    ON_PRIMARY=ft.Colors.WHITE,
    BORDER=ft.Colors.BLUE_GREY_100,
    HERO_A=ft.Colors.TEAL_600,
    HERO_B=ft.Colors.TEAL_900,
    HERO_TEXT=ft.Colors.TEAL_50,
    ERROR=ft.Colors.RED_700,
    OK=ft.Colors.GREEN_700,
    SHADOW=0.07,
)

DARK = dict(
    BG="#0E1414",
    SURFACE="#172020",
    INK="#E8F0F0",
    MUTED="#93A8A8",
    PRIMARY=ft.Colors.TEAL_300,
    PRIMARY_SOFT="#14322F",
    ON_PRIMARY="#04201E",
    BORDER="#2B3A3A",
    HERO_A=ft.Colors.TEAL_800,
    HERO_B="#0B3B38",
    HERO_TEXT=ft.Colors.TEAL_50,
    ERROR=ft.Colors.RED_300,
    OK=ft.Colors.GREEN_300,
    SHADOW=0.35,
)


class C:
    """Current palette. Read at call time (C.INK), never at import time."""


_state = {"dark": False}


def _load(palette: dict):
    for key, value in palette.items():
        setattr(C, key, value)


_load(LIGHT)


def set_dark(flag: bool):
    _state["dark"] = bool(flag)
    _load(DARK if flag else LIGHT)


def is_dark() -> bool:
    return _state["dark"]


def apply_theme(page: ft.Page):
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)
    page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)
    page.theme_mode = ft.ThemeMode.DARK if is_dark() else ft.ThemeMode.LIGHT
    page.bgcolor = C.BG
    page.padding = 0


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
def card(content, bgcolor=None, padding=18, on_click=None, gradient=None):
    return ft.Container(
        content=content,
        bgcolor=None if gradient else (bgcolor or C.SURFACE),
        gradient=gradient,
        padding=padding,
        border_radius=18,
        on_click=on_click,
        shadow=ft.BoxShadow(
            blur_radius=16,
            color=ft.Colors.with_opacity(C.SHADOW, ft.Colors.BLACK),
            offset=ft.Offset(0, 4),
        ),
    )


def hero_gradient():
    return ft.LinearGradient(
        begin=ft.Alignment(-1, -1),
        end=ft.Alignment(1, 1),
        colors=[C.HERO_A, C.HERO_B],
    )


def page_header(title: str, subtitle: str = ""):
    controls = [ft.Text(title, size=26, weight=ft.FontWeight.W_700, color=C.INK)]
    if subtitle:
        controls.append(ft.Text(subtitle, size=14, color=C.MUTED))
    return ft.Column(controls, spacing=4)


def icon_badge(icon, color=None, bg=None):
    return ft.Container(
        content=ft.Icon(icon, color=color or C.PRIMARY, size=22),
        bgcolor=bg or C.PRIMARY_SOFT,
        width=44,
        height=44,
        border_radius=14,
        alignment=ft.Alignment(0, 0),
    )


def primary_button(text, on_click, icon=None, expand=False):
    return ft.FilledButton(
        content=text,
        icon=icon,
        on_click=on_click,
        expand=expand,
        height=52,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=14),
            bgcolor=C.PRIMARY,
            color=C.ON_PRIMARY,
        ),
    )


def text_field(label, icon=None, password=False, autofocus=False, keyboard_type=None):
    kwargs = {}
    if keyboard_type is not None:
        kwargs["keyboard_type"] = keyboard_type
    return ft.TextField(
        label=label,
        prefix_icon=icon,
        password=password,
        can_reveal_password=password,
        autofocus=autofocus,
        filled=True,
        bgcolor=C.SURFACE,
        border_radius=14,
        border_color=C.BORDER,
        focused_border_color=C.PRIMARY,
        content_padding=ft.Padding(16, 14, 16, 14),
        **kwargs,
    )


def auth_banner(title: str, subtitle: str):
    """Gradient header used at the top of the login and register screens."""
    badge = ft.Container(
        content=ft.Icon(ft.Icons.SHIELD_OUTLINED, color=ft.Colors.WHITE, size=34),
        width=68,
        height=68,
        border_radius=22,
        bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.WHITE),
        alignment=ft.Alignment(0, 0),
    )
    return ft.Container(
        gradient=hero_gradient(),
        border_radius=ft.BorderRadius(0, 0, 32, 32),
        padding=ft.Padding(24, 24, 24, 36),
        content=ft.SafeArea(
            content=ft.Column(
                [
                    badge,
                    ft.Container(height=6),
                    ft.Text(title, size=28, weight=ft.FontWeight.W_800, color=ft.Colors.WHITE),
                    ft.Text(subtitle, size=14, color=C.HERO_TEXT, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            )
        ),
    )


def fmt_time(value, default: str) -> str:
    try:
        return value.strftime("%I:%M %p")
    except Exception:
        return default