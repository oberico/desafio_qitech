from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func

from models.base import Base


class AccountClass(Base):
    __tablename__ = "account_class"

    ASSET = "asset"
    LIABILITY = "liability"
    REVENUE = "revenue"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)
