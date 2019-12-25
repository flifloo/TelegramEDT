import shelve
from base import User

with shelve.open("edt", writeback=True) as db:
    for u in db:
        nu = User(0, None)
        for v in db[u].__dict__:
            setattr(nu, v, db[u].__dict__[v])
        db[u] = nu
