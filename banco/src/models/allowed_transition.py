from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, func

from models.base import Base
from models.transaction_status import TransactionStatus
from models.transaction_type import TransactionType


class AllowedTransition(Base):
    __tablename__ = "allowed_transition"

    id = Column(Integer, primary_key=True)
    type_id = Column(Integer, ForeignKey(TransactionType.id), nullable=False)
    from_status_id = Column(Integer, ForeignKey(TransactionStatus.id), nullable=False)
    to_status_id = Column(Integer, ForeignKey(TransactionStatus.id), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("type_id", "from_status_id", "to_status_id"),)
