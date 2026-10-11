from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from models.base import Base
from models.payment import Payment
from models.payment_status import PaymentStatus


class PaymentStatusEvent(Base):
    __tablename__ = "payment_status_event"

    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey(Payment.id), nullable=False)
    status_id = Column(Integer, ForeignKey(PaymentStatus.id), nullable=False)
    reason = Column(String(255))
    event_datetime = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
