from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, func

from models.base import Base
from models.payout import Payout
from models.payout_result import PayoutResult


class PayoutAttempt(Base):
    __tablename__ = "payout_attempt"

    id = Column(Integer, primary_key=True)
    payout_id = Column(Integer, ForeignKey(Payout.id), nullable=False)
    result_id = Column(Integer, ForeignKey(PayoutResult.id), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("payout_id", "attempt_number"),)
