import json
from EDTuser import User

LANG = ["en"]


def lang(user: User, message: str):
    language = user.language if user.language in LANG else LANG[0]
    return json.loads(open(f"Languages/{language}.json", "r").read())[message]
