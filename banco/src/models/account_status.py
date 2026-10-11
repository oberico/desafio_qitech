from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func

from models.base import Base


class AccountStatus(Base):
    __tablename__ = "account_status"

    CREATED = "created"
    ACTIVE = "active"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    CLOSED = "closed"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)
