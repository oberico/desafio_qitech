from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import relationship

from models.base import Base
from models.client import Client


class ApiToken(Base):
    __tablename__ = "api_token"

    id = Column(Integer, primary_key=True)
    token_hash = Column(CHAR(64), nullable=False)
    client_id = Column(Integer, ForeignKey(Client.id), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("token_hash"),)

    client = relationship("Client", foreign_keys=[client_id], lazy="selectin")
