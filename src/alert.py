# alert.py
import flet as ft

if __package__:
  from .dashhome import open_main_dashboard
  from .help import help
  from .theme import C, apply_theme, card, primary_button
else:
  from dashhome import open_main_dashboard
  from help import help
  from theme import C, apply_theme, card, primary_button


def trigger_desktop_alert(page: ft.Page):
  if page.platform is None or not page.platform.is_desktop():
    return

  from plyer import notification

  notify = notification.notify
  if not callable(notify):
    raise RuntimeError("Desktop notifications are not available on this device.")
  notify(
      title="⚠️ Safety Check-Up",
      message="We detected a loud sound or trigger. Are you alright?",
      app_name="Safety App",
      timeout=10,
  )


def create_audio_alert_view(page: ft.Page, username: str = ""):
  page.title = "Safety App - Loud Noise Alert"
  page.clean()
  page.overlay.clear()
  page.navigation_bar = None
  apply_theme(page)
  status_text = ft.Text("", size=14, color=C.ERROR, text_align=ft.TextAlign.CENTER)

  def handle_ok(e):
    open_main_dashboard(page, username)

  def handle_help(e):
    status_text.value = help()
    page.update()

  page.add(
      ft.SafeArea(
          expand=True,
          content=ft.Container(
              alignment=ft.Alignment.CENTER,
              padding=24,
              content=card(
                  ft.Column(
                      [
                          ft.Text(
                              "We detected a loud or concerning sound.",
                              size=22,
                              weight=ft.FontWeight.W_700,
                              color=C.INK,
                              text_align=ft.TextAlign.CENTER,
                          ),
                          ft.Text(
                              "Are you safe? Let us know if you need help.",
                              size=18,
                              color=C.MUTED,
                              text_align=ft.TextAlign.CENTER,
                          ),
                          primary_button("I'm okay", handle_ok, expand=True),
                          ft.OutlinedButton(
                              content="I need help",
                              on_click=handle_help,
                              style=ft.ButtonStyle(
                                  color=C.ERROR,
                                  shape=ft.RoundedRectangleBorder(radius=14),
                              ),
                              expand=True,
                              height=52,
                          ),
                          status_text,
                      ],
                      horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                      spacing=16,
                  ),
                  padding=24,
              ),
          ),
      ),
  )
  page.update()
  trigger_desktop_alert(page)


create_confirm_view = create_audio_alert_view