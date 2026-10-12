import os
from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from constants import BUSINESS_TIMEZONE, SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import AuthIdentityDTO, ClientDTO
from errors import (
    CpfAlreadyRegistered,
    EmailAlreadyRegistered,
    InvalidClientToken,
    InvalidCpf,
    InvalidFormat,
    UnderageClient,
    ValueOutOfRange,
)
from models import ApiToken, Client
from repositories import ClientRepository
from utils.age import age_on
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
        if age_on(birthdate, self._today()) < MINIMUM_AGE:
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

        violated_constraint = self.client_repository.try_create(client, ApiToken(token_hash=hash_token(token)))
        if violated_constraint is not None:
            raise CONSTRAINT_ERRORS[violated_constraint]()

        client_dto = ClientDTO.obj_to_dict(client)
        self.session.commit()
        return {**client_dto, "token": token}

    def authenticate(self, token: str) -> Client:
        client = self.client_repository.get_by_active_token_hash(hash_token(token)) if token else None
        if client is None:
            raise InvalidClientToken()
        return client

    def get_identity(self, token: str) -> dict:
        return AuthIdentityDTO.obj_to_dict(self.authenticate(token))

    def get_me(self, client_id: int) -> dict:
        return ClientDTO.obj_to_dict(self.client_repository.get_by_id(client_id))

    @staticmethod
    def _parse_birthdate(value: str) -> date:
        try:
            birthdate = date.fromisoformat(value)
        except ValueError:
            raise InvalidFormat("birthdate", f"birthdate: {value} is not a valid date", "esperado uma data válida no formato AAAA-MM-DD")
        if birthdate > ClientController._today():
            raise ValueOutOfRange("birthdate", f"birthdate: {value} cannot be in the future", "não pode estar no futuro")
        return birthdate

    @staticmethod
    def _today() -> date:
        return datetime.now(ZoneInfo(BUSINESS_TIMEZONE)).date()
