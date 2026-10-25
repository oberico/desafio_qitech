from sqlalchemy import Column, DateTime, Integer, UniqueConstraint, func

from models.base import Base


class PayoutFee(Base):
    __tablename__ = "payout_fee"

    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False)
    fee_bps = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("version"),)
