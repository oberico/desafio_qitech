from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func

from models.base import Base


class Origin(Base):
    __tablename__ = "origin"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)

    GATEWAY = "gateway"
    TAP_TO_PAY = "tap_to_pay"
