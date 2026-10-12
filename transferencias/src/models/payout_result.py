from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func

from models.base import Base


class PayoutResult(Base):
    __tablename__ = "payout_result"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)

    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
