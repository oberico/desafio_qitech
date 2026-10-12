from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Company


class CompanyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_newest_first(self, limit: int, before_id: int = None) -> list:
        query = self.session.query(Company)
        if before_id is not None:
            query = query.filter(Company.id < before_id)
        return query.order_by(Company.id.desc()).limit(limit).all()

    def get_by_key_and_client(self, company_key: str, client_id: int) -> Company:
        return (
            self.session.query(Company)
            .filter(Company.company_key == company_key.lower(), Company.client_id == client_id)
            .first()
        )

    def lock_by_key_and_client(self, company_key: str, client_id: int) -> Company:
        return (
            self.session.query(Company)
            .filter(Company.company_key == company_key.lower(), Company.client_id == client_id)
            .with_for_update()
            .first()
        )

    def exists_with_cnpj(self, cnpj: str) -> bool:
        return self.session.query(Company.id).filter(Company.cnpj == cnpj).first() is not None

    def try_create(self, company: Company) -> str:
        try:
            self.session.add(company)
            self.session.flush()
        except IntegrityError as error:
            self.session.rollback()
            return self._violated_constraint(error) or "unknown"
        return None

    @staticmethod
    def _violated_constraint(error: IntegrityError) -> str:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None)
