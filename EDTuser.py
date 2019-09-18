from EDTcalendar import Calendar
import datetime


class User:
    def __init__(self, user_id: int, language: str):
        self.id = user_id
        self.language = language
        self.resources = None
        self.nt = False
        self.nt_time = 20
        self.nt_cooldown = 20
        self.nt_last = datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)

    def calendar(self, time: str = "", pass_week: bool = False):
        return Calendar(time, self.resources, pass_week=pass_week)
