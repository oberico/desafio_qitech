from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import ApiToken, Client


class ClientRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_key(self, client_key: str) -> Client:
        return self.session.query(Client).filter(Client.client_key == client_key.lower()).first()

    def list_newest_first(self, limit: int, before_id: int = None) -> list:
        query = self.session.query(Client)
        if before_id is not None:
            query = query.filter(Client.id < before_id)
        return query.order_by(Client.id.desc()).limit(limit).all()

    def get_by_id(self, client_id: int) -> Client:
        return self.session.query(Client).filter(Client.id == client_id).first()

    def get_by_active_token_hash(self, token_hash: str) -> Client:
        return (
            self.session.query(Client)
            .join(ApiToken, ApiToken.client_id == Client.id)
            .filter(ApiToken.token_hash == token_hash, ApiToken.revoked_at.is_(None))
            .first()
        )

    def exists_with_cpf(self, cpf: str) -> bool:
        return self.session.query(Client.id).filter(Client.cpf == cpf).first() is not None

    def exists_with_email(self, email: str) -> bool:
        return self.session.query(Client.id).filter(Client.email == email).first() is not None

    def try_create(self, client: Client, api_token: ApiToken) -> str:
        try:
            self.session.add(client)
            self.session.flush()
            api_token.client_id = client.id
            self.session.add(api_token)
            self.session.flush()
        except IntegrityError as error:
            self.session.rollback()
            return self._violated_constraint(error) or "unknown"
        return None

    @staticmethod
    def _violated_constraint(error: IntegrityError) -> str:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None)
