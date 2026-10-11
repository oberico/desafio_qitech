from sqlalchemy.orm import Session

from database import Context, get_context


class BaseController:
    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    @property
    def context(self) -> Context:
        return get_context()
