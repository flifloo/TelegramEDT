import datetime
import ics
import requests
from ics.timeline import Timeline
from aiogram.utils import markdown

URL = "http://adelb.univ-lyon1.fr/jsp/custom/modules/plannings/anonymous_cal.jsp"


class Calendar(ics.Calendar):
    def __init__(self, time: str, resources: int, url: str = URL, projectid: int = 4, pass_week: bool = True):
        super().__init__(requests.get(self._url(time, [url, resources, projectid], pass_week)).text)
        events = set()
        for e in self.events:
            events.add(Event(e))
        self.events = events
        self.timeline = Timeline(self)

    def _url(self, time: str, url: list, pass_week: bool):
        now = datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None)
        if now.isoweekday() in [6, 7] and pass_week:
            now += datetime.timedelta(days=(7 - (now.isoweekday() - 1)))

        dates = {
            "": [0, 0],
            "day": [0, 0],
            "next": [1, 1],
            "week": [-(now.isoweekday() - 1), 7 - now.isoweekday()],
            "next week": [7 - (now.isoweekday() - 1), 7 + (7 - now.isoweekday())]
        }
        firstdate = now.date() + datetime.timedelta(days=dates[time][0])
        lastdate = now.date() + datetime.timedelta(days=dates[time][1])
        return f"{url[0]}?resources={url[1]}&projectId={url[2]}&calType=ical&firstDate={firstdate}&lastDate={lastdate}"

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
            markdown.text(f"⌚️ {str(self.begin.time())[:-3]} -> {str(self.end.time())[:-3]}"),
            markdown.italic(f"📍 {self.location} 👨‍🏫 {self.organizer}"),
            sep="\n"
        )
