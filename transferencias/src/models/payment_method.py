from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func

from models.base import Base


class PaymentMethod(Base):
    __tablename__ = "payment_method"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    fee_bps = Column(Integer, nullable=False)
    release_window_hours = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)
