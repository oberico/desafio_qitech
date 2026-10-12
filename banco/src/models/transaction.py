from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from models.base import Base
from models.transaction_status import TransactionStatus
from models.transaction_type import TransactionType


class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(Integer, primary_key=True)
    transaction_key = Column(CHAR(36), nullable=False)
    type_id = Column(Integer, ForeignKey(TransactionType.id), nullable=False)
    status_id = Column(Integer, ForeignKey(TransactionStatus.id), nullable=False)
    idempotency_key = Column(String(100), nullable=False)
    payload_hash = Column(CHAR(64), nullable=False)
    reverses_transaction_id = Column(Integer, ForeignKey("transaction.id"))
    settles_transaction_id = Column(Integer, ForeignKey("transaction.id"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("transaction_key"),
        UniqueConstraint("idempotency_key", name="uq_transaction_idempotency_key"),
        UniqueConstraint("reverses_transaction_id", name="uq_transaction_reverses"),
        UniqueConstraint("settles_transaction_id", name="uq_transaction_settles"),
    )

    type = relationship("TransactionType", lazy="selectin")
    status = relationship("TransactionStatus", lazy="selectin")
