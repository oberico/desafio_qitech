from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from models.base import Base
from models.payout import Payout
from models.payout_status import PayoutStatus


class PayoutStatusEvent(Base):
    __tablename__ = "payout_status_event"

    id = Column(Integer, primary_key=True)
    payout_id = Column(Integer, ForeignKey(Payout.id), nullable=False)
    status_id = Column(Integer, ForeignKey(PayoutStatus.id), nullable=False)
    reason = Column(String(255))
    event_datetime = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
