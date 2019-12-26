import datetime
from os.path import getmtime, isfile

import ics
import requests
from aiogram.utils import markdown
from ics.timeline import Timeline

URL = "http://adelb.univ-lyon1.fr/jsp/custom/modules/plannings/anonymous_cal.jsp"


class Calendar(ics.Calendar):
    def __init__(self, time: str, resources: int, url: str = URL, projectid: int = 4, pass_week: bool = True):
        super().__init__(self._get_calendar(url, resources, projectid))
        self.events = self._events(time, pass_week)
        self.timeline = Timeline(self)

    @staticmethod
    def _now():
        return datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)

    def _dates(self):
        now = self._now()
        return {
            "": [0, 0],
            "day": [0, 0],
            "next": [1, 1],
            "week": [-(now.isoweekday() - 1), 7 - now.isoweekday()],
            "next week": [7 - (now.isoweekday() - 1), 7 + (7 - now.isoweekday())]
        }

    def _url(self, url: str, resources: int, projectid: int):
        now = self._now()
        firstdate = now.date() - datetime.timedelta(days=now.weekday())
        lastdate = now.date() + datetime.timedelta(days=7+(7-now.isoweekday()))
        return f"{url}?resources={resources}&projectId={projectid}&calType=ical&firstDate={firstdate}&lastDate={lastdate}"

    def _get_calendar(self, url: str, resources: int, projectid: int):
        name = f"calendars/{resources}-{projectid}.ical"
        now = self._now().timestamp()
        if not isfile(name) or now-getmtime(name) < now-360:
            open(name, "w").write(requests.get(self._url(url, resources, projectid)).text)
        return open(name, "r").read()

    def _events(self, time: str, pass_week: bool):
        now = self._now()
        if now.isoweekday() in [6, 7] and pass_week:
            now += datetime.timedelta(days=(8 - now.isoweekday()))
        dates = self._dates()
        firstdate = now.date() + datetime.timedelta(days=dates[time][0])
        lastdate = now.date() + datetime.timedelta(days=dates[time][1])
        events = set()
        for e in self.events:
            if firstdate <= e.begin.date() and e.end.date() <= lastdate:
                events.add(Event(e))
        return events

    def __str__(self):
        msg = str()

        for e in list(self.timeline):
            msg += (str(e)[10:] if str(e.begin.date())[5:] in msg else str(e)) + "\n\n"

        if len(msg) == 0:
            msg += markdown.italic("but nobody came...")
        return msg


class Event(ics.Event):
    def __init__(self, event: ics.Event):
        super().__init__()
        for v in event.__dict__:
            setattr(self, v, event.__dict__[v])

        self.begin = self.begin.datetime.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
        self.end = self.end.datetime.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
        self.organizer = self.description.split('\n')[3]

    def __str__(self):
        return markdown.text(
            markdown.bold(f"<{str(self.begin.date())[5:]}>"),
            markdown.code(f"📓[{self.name}]:"),
            markdown.text(f"⌚{str(self.begin.time())[:-3]} -> {str(self.end.time())[:-3]}"),
            markdown.italic(f"📍{self.location} 👨‍🏫{self.organizer}"),
            sep="\n"
        )
