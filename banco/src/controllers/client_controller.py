import os
from datetime import date
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import ClientDTO
from errors import (
    CpfAlreadyRegistered,
    EmailAlreadyRegistered,
    InvalidClientToken,
    InvalidCpf,
    InvalidSchema,
    UnderageClient,
)
from models import ApiToken, Client
from repositories import ClientRepository
from utils.cpf import is_valid_cpf
from utils.schema_handler import validate_json
from utils.token import generate_token, hash_token

POST_CLIENTS_SCHEMA = os.path.join(SCHEMAS_DIR, "post_clients.json")
MINIMUM_AGE = 18
CONSTRAINT_ERRORS = {
    "client_cpf_key": CpfAlreadyRegistered,
    "client_email_key": EmailAlreadyRegistered,
}


class ClientController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.client_repository = ClientRepository(session)

    def create(self, payload: dict) -> dict:
        validate_json(payload, POST_CLIENTS_SCHEMA)
        birthdate = self._parse_birthdate(payload["birthdate"])

        if not is_valid_cpf(payload["cpf"]):
            raise InvalidCpf(payload["cpf"])
        if self._age_on(birthdate, date.today()) < MINIMUM_AGE:
            raise UnderageClient()
        if self.client_repository.exists_with_cpf(payload["cpf"]):
            raise CpfAlreadyRegistered()
        if self.client_repository.exists_with_email(payload["email"]):
            raise EmailAlreadyRegistered()

        token = generate_token()
        client = Client(
            client_key=str(uuid4()),
            cpf=payload["cpf"],
            name=payload["name"],
            birthdate=birthdate,
            email=payload["email"],
        )

        try:
            self.client_repository.create(client, ApiToken(token_hash=hash_token(token)))
        except IntegrityError as error:
            self.session.rollback()
            raise self._conflict_error(error) from error

        client_dto = ClientDTO.obj_to_dict(client)
        self.session.commit()
        return {**client_dto, "token": token}

    def authenticate(self, token: str) -> Client:
        client = self.client_repository.get_by_active_token_hash(hash_token(token)) if token else None
        if client is None:
            raise InvalidClientToken()
        return client

    def get_me(self, client_id: int) -> dict:
        return ClientDTO.obj_to_dict(self.client_repository.get_by_id(client_id))

    @staticmethod
    def _parse_birthdate(value: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise InvalidSchema(f"birthdate: {value} is not a valid date")

    @staticmethod
    def _age_on(birthdate: date, today: date) -> int:
        had_birthday = (today.month, today.day) >= (birthdate.month, birthdate.day)
        return today.year - birthdate.year - (0 if had_birthday else 1)

    def _conflict_error(self, error: IntegrityError):
        error_class = CONSTRAINT_ERRORS.get(self.client_repository.violated_constraint(error))
        if error_class is None:
            return error
        return error_class()
