import datetime
import requests
from EDTcalendar import Calendar

KFET_URL = "https://kfet.bdeinfo.org/?page=api_commandes"


def get_now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)


class User:
    def __init__(self, user_id: int, language: str):
        self.id = user_id
        self.language = language
        self.resources = None
        self.nt = False
        self.nt_time = 20
        self.nt_cooldown = 20
        self.nt_last = get_now()
        self.kfet = None

    def calendar(self, time: str = "", pass_week: bool = False):
        return Calendar(time, self.resources, pass_week=pass_week)

    def get_notif(self):
        if self.resources and self.nt:
            now = get_now()
            c = self.calendar(pass_week=False)
            for e in c.timeline:
                if 0 < (e.begin - now).total_seconds() // 60 <= self.nt_time and \
                        0 < (now - self.nt_last).total_seconds() // 60 >= self.nt_cooldown:
                    self.nt_last = get_now()
                    return e
            return None

    def get_kfet(self):
        res = None
        if self.kfet:
            cmds = requests.get(KFET_URL).json()
            if cmds and str(self.kfet) in cmds:
                res = 1 if cmds[str(self.kfet)]["statut"] == "T" else 2
            elif get_now().hour >= 14:
                res = 3
        self.kfet = None if res else self.kfet
        return res
