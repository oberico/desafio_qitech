from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import ApiToken, Client


class ClientRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

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

    def create(self, client: Client, api_token: ApiToken) -> None:
        self.session.add(client)
        self.session.flush()
        api_token.client_id = client.id
        self.session.add(api_token)
        self.session.flush()

    @staticmethod
    def violated_constraint(error: IntegrityError) -> str:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None)
