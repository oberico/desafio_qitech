import os
from uuid import uuid4

from constants import SCHEMAS_DIR
from controllers.base_controller import BaseController
from dtos import CompanyDTO
from errors import CnpjAlreadyRegistered, CompanyNotFound, InvalidCnpj
from models import Company
from repositories import CompanyRepository
from utils.cnpj import is_valid_cnpj
from utils.schema_handler import validate_json

POST_COMPANIES_SCHEMA = os.path.join(SCHEMAS_DIR, "post_companies.json")
CONSTRAINT_ERRORS = {"company_cnpj_key": CnpjAlreadyRegistered}


class CompanyController(BaseController):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.company_repository = CompanyRepository(session)

    def create(self, payload: dict, client_id: int) -> dict:
        validate_json(payload, POST_COMPANIES_SCHEMA)

        if not is_valid_cnpj(payload["cnpj"]):
            raise InvalidCnpj(payload["cnpj"])
        if self.company_repository.exists_with_cnpj(payload["cnpj"]):
            raise CnpjAlreadyRegistered()

        company = Company(
            company_key=str(uuid4()),
            cnpj=payload["cnpj"],
            legal_name=payload["legal_name"],
            client_id=client_id,
        )

        violated_constraint = self.company_repository.try_create(company)
        if violated_constraint is not None:
            raise CONSTRAINT_ERRORS[violated_constraint]()

        company_dto = CompanyDTO.obj_to_dict(company)
        self.session.commit()
        return company_dto

    def get_by_key(self, company_key: str, client_id: int) -> dict:
        company = self.company_repository.get_by_key_and_client(company_key, client_id)
        if company is None:
            raise CompanyNotFound(company_key)
        return CompanyDTO.obj_to_dict(company)
