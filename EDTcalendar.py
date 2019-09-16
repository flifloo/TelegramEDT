import datetime
import ics
import requests
from ics.timeline import Timeline
from aiogram.utils import markdown


class Calendar(ics.Calendar):
    def __init__(self, url: list, firstdate: datetime.date, lastdate: datetime.date):
        super().__init__(requests.get(
            f"{url[0]}?resources={url[1]}&projectId={url[2]}&calType=ical&firstDate={firstdate}&lastDate={lastdate}"
        ).text)
        events = set()
        for e in self.events:
            events.add(Event(e))
        self.events = events

        self.timeline = Timeline(self)


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
