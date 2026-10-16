if __package__:
    from .dashhome import create_schedule_view, open_main_dashboard
else:
    from dashhome import create_schedule_view, open_main_dashboard


__all__ = ["create_schedule_view", "open_main_dashboard"]
