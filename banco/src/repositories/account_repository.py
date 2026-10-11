from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Account, AccountClass, AccountStatus, AccountStatusEvent, Company


class AccountRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_internal(self) -> list:
        return self.session.query(Account).filter(Account.company_id.is_(None)).order_by(Account.id).all()

    def get_by_key_and_client(self, account_key: str, client_id: int) -> Account:
        return (
            self.session.query(Account)
            .join(Company, Company.id == Account.company_id)
            .filter(Account.account_key == account_key.lower(), Company.client_id == client_id)
            .first()
        )

    def lock_by_key_and_client(self, account_key: str, client_id: int) -> Account:
        return (
            self.session.query(Account)
            .join(Company, Company.id == Account.company_id)
            .filter(Account.account_key == account_key.lower(), Company.client_id == client_id)
            .with_for_update(of=Account)
            .first()
        )

    def exists_for_company(self, company_id: int) -> bool:
        return self.session.query(Account.id).filter(Account.company_id == company_id).first() is not None

    def get_class(self, enumerator: str) -> AccountClass:
        return self.session.query(AccountClass).filter(AccountClass.enumerator == enumerator).first()

    def get_status(self, enumerator: str) -> AccountStatus:
        return self.session.query(AccountStatus).filter(AccountStatus.enumerator == enumerator).first()

    def try_create(self, account: Account) -> str:
        try:
            self.session.add(account)
            self.session.flush()
        except IntegrityError as error:
            self.session.rollback()
            return self._violated_constraint(error) or "unknown"
        return None

    @staticmethod
    def _violated_constraint(error: IntegrityError) -> str:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None)

    def change_status(self, account: Account, status: AccountStatus, reason: str = None) -> None:
        account.status = status
        self.session.add(
            AccountStatusEvent(
                account_id=account.id,
                status_id=status.id,
                reason=reason,
                event_datetime=datetime.now(timezone.utc),
            )
        )
        self.session.flush()
