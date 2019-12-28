from sqlalchemy.orm import scoped_session as ss


class scoped_session:
    def __init__(self, session_factory, scopefunc=None):
        self.scoped_session = ss(session_factory, scopefunc)

    def __enter__(self):
        return self.scoped_session

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.scoped_session.remove()
