from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, func

from models.base import Base
from models.payment_status import PaymentStatus


class PaymentTransition(Base):
    __tablename__ = "payment_transition"

    id = Column(Integer, primary_key=True)
    from_status_id = Column(Integer, ForeignKey(PaymentStatus.id), nullable=False)
    to_status_id = Column(Integer, ForeignKey(PaymentStatus.id), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("from_status_id", "to_status_id"),)
