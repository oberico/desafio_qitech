from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, func

from models.account import Account
from models.base import Base
from models.transaction import Transaction


class Entry(Base):
    __tablename__ = "entry"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey(Transaction.id), nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    currency = Column(String(3), nullable=False, server_default="brl")
    debit_minor = Column(BigInteger, nullable=False, server_default="0")
    credit_minor = Column(BigInteger, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp())

    __table_args__ = (
        CheckConstraint(
            "(debit_minor > 0 AND credit_minor = 0) OR (debit_minor = 0 AND credit_minor > 0)",
            name="ck_entry_one_side",
        ),
    )
