from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from models.base import Base
from models.transaction import Transaction
from models.transaction_status import TransactionStatus


class TransactionStatusEvent(Base):
    __tablename__ = "transaction_status_event"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey(Transaction.id), nullable=False)
    status_id = Column(Integer, ForeignKey(TransactionStatus.id), nullable=False)
    reason = Column(String(255))
    event_datetime = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
