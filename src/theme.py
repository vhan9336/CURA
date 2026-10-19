# theme.py
"""Shared look & feel for every screen, with light and dark palettes."""
from collections.abc import Callable

import flet as ft

LIGHT = dict(
    BG="#F4F7F5",
    SURFACE="#FFFFFF",
    INK="#142B29",
    MUTED="#637875",
    PRIMARY="#14786C",
    PRIMARY_SOFT="#E6F3EF",
    ON_PRIMARY=ft.Colors.WHITE,
    BORDER="#E0E9E5",
    HERO_A="#168777",
    HERO_B="#07574F",
    HERO_TEXT="#E4F6F1",
    ERROR=ft.Colors.RED_700,
    OK=ft.Colors.GREEN_700,
    SHADOW=0.07,
)

DARK = dict(
    BG="#0B1514",
    SURFACE="#14211F",
    INK="#EAF3F0",
    MUTED="#9BB0AA",
    PRIMARY="#73D5C0",
    PRIMARY_SOFT="#1B3A34",
    ON_PRIMARY="#04201E",
    BORDER="#283B37",
    HERO_A="#146F62",
    HERO_B="#0A463F",
    HERO_TEXT="#E4F6F1",
    ERROR=ft.Colors.RED_300,
    OK=ft.Colors.GREEN_300,
    SHADOW=0.35,
)


class C:
    """Current palette. Read at call time (C.INK), never at import time."""


_state = {"dark": False}
_theme_rebuilders: dict[int, Callable[[], None]] = {}


def _load(palette: dict):
    for key, value in palette.items():
        setattr(C, key, value)


_load(LIGHT)


def set_dark(flag: bool):
    _state["dark"] = bool(flag)
    _load(DARK if flag else LIGHT)


def is_dark() -> bool:
    return _state["dark"]


def logo_asset() -> str:
    return "logo-dark.png" if is_dark() else "logo-light.png"


def set_theme_rebuilder(page: ft.Page, rebuild: Callable[[], None]) -> None:
    _theme_rebuilders[id(page)] = rebuild


def logo_badge(size: int, radius: int) -> ft.Container:
    return ft.Container(
        content=ft.Image(
            src=logo_asset(),
            width=80,
            height=80,
            fit=ft.BoxFit.CONTAIN,
            border_radius=9,
        ),
        width=size,
        height=size,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        alignment=ft.Alignment.CENTER,
    )


def apply_theme(page: ft.Page):
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)
    page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)
    set_dark(page.platform_brightness == ft.Brightness.DARK)
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.bgcolor = C.BG
    page.padding = 0

    def on_platform_brightness_change(_):
        next_dark = page.platform_brightness == ft.Brightness.DARK
        if next_dark == is_dark():
            return
        set_dark(next_dark)
        rebuild = _theme_rebuilders.get(id(page))
        if rebuild is not None:
            rebuild()
        else:
            page.bgcolor = C.BG
            page.update()

    page.on_platform_brightness_change = on_platform_brightness_change


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
def card(content, bgcolor=None, padding=18, on_click=None, gradient=None):
    return ft.Container(
        content=content,
        bgcolor=None if gradient else (bgcolor or C.SURFACE),
        gradient=gradient,
        padding=padding,
        border_radius=22,
        animate=ft.Animation(240, ft.AnimationCurve.EASE_OUT),
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
    controls = [ft.Text(title, size=28, weight=ft.FontWeight.W_700, color=C.INK)]
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
    badge = logo_badge(84, 22)
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