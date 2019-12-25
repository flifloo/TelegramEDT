import datetime
import requests
from EDTcalendar import Calendar
from feedparser import parse
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Date

KFET_URL = "http://kfet.bdeinfo.org/orders"
Base = declarative_base()


def get_now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, unique=True)
    language = Column(String, default="")
    resources = Column(Integer)
    nt = Column(Boolean, default=False)
    nt_time = Column(Integer, default=20)
    nt_cooldown = Column(Integer, default=20)
    nt_last = Column(Date, default=get_now)
    kfet = Column(Integer, default=0)
    await_cmd = Column(String, default="")
    tomuss_rss = Column(String)
    tomuss_last = Column(String)

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
                res = 1 if cmds[str(self.kfet)] == "ok" else 2 if cmds[str(self.kfet)] == "ko" else 3
            elif get_now().hour >= 14:
                res = 3
        self.kfet = None if res else self.kfet
        return res

    def get_tomuss(self):
        entry = list()
        if self.tomuss_rss:
            entry = [e for e in parse(self.tomuss_rss).entries]
            if not self.tomuss_last:
                return entry
        tomuss_last = 0
        for i,e in enumerate(entry):
            if str(e) == self.tomuss_last:
                tomuss_last = i+1
                break
        return entry[tomuss_last:]

    def __repr__(self):
        return f"<User: {self.id}>"
